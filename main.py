import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px
import io

# --- 1. بناء هيكل قاعدة البيانات (v68) ---
Base = declarative_base()

class InventoryItem(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    unit = Column(String(50))
    total_qty = Column(Float, default=0.0)

class HandoverLog(Base):
    __tablename__ = 'handover_logs'
    id = Column(Integer, primary_key=True)
    worker_name = Column(String(100))
    item_name = Column(String(100))
    qty = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class TransactionHistory(Base):
    __tablename__ = 'transaction_history'
    id = Column(Integer, primary_key=True)
    item_name = Column(String(100))
    qty = Column(Float)
    type = Column(String(50)) # Entry, Handover, Return, Waste
    person = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_v68_final.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. واجهة البرنامج ---
st.set_page_config(page_title="EGMS Smart Import v68", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;'>🏗️ EGMS Digital ERP v68</h1>", unsafe_allow_html=True)
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "magaza": ("store2025", "Store")}
        if u in acc and p == acc[u][0]:
            st.session_state.update({"logged_in": True, "role": acc[u][1]})
            st.rerun()
        else: st.error("Access Denied")
else:
    role = st.session_state["role"]
    session = Session()
    st.sidebar.success(f"Role: {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    all_items = session.query(InventoryItem).all()
    
    # --- 3. واجهة المدير (Admin) ---
    if role == "Admin":
        st.title("📊 لوحة الرقابة والتحليل الإحصائي")
        tabs = st.tabs(["📈 التحليلات", "📋 الجرد الحي", "📄 التقارير"])
        # (أكواد المدير تظل كما هي لعرض الرسوم والجرد...)
        df_inv = pd.read_sql(session.query(InventoryItem).statement, session.bind)
        df_hist = pd.read_sql(session.query(TransactionHistory).statement, session.bind)
        with tabs[0]:
            if not df_inv.empty: st.plotly_chart(px.bar(df_inv, x='name', y='total_qty', title="رصيد المخزن"))
        with tabs[1]:
            st.dataframe(df_inv, use_container_width=True)

    # --- 4. واجهة مسؤول المغازة (Store) - مع ميزة الاستيراد الجديدة ✅ ---
    elif role == "Store":
        st.title("📦 مركز العمليات - مسؤول المغازة")
        m_tabs = st.tabs(["📥 تسجيل/تعريف", "🤝 تسليم عُهدة", "🔙 استرجاع", "⚠️ تآكل", "📤 استيراد CSV"])

        with m_tabs[4]: # قسم استيراد CSV الجديد
            st.subheader("استيراد سجلات خارجية (CSV)")
            st.info("يجب أن يحتوي الملف على الأعمدة: item_name, qty, unit, type (Entry أو Waste)")
            
            uploaded_file = st.file_uploader("اختر ملف CSV", type="csv")
            if uploaded_file is not None:
                df_upload = pd.read_csv(uploaded_file)
                st.write("معاينة البيانات قبل الرفع:")
                st.dataframe(df_upload)
                
                if st.button("تأكيد استيراد البيانات وتحديث الجرد"):
                    try:
                        count = 0
                        for index, row in df_upload.iterrows():
                            # معالجة كل سطر في الملف
                            it_name = row['item_name']
                            it_qty = float(row['qty'])
                            it_unit = row['unit']
                            it_type = row['type']
                            
                            # تحديث المخزن الرئيسي
                            exist = session.query(InventoryItem).filter_by(name=it_name).first()
                            if exist:
                                if it_type == "Entry": exist.total_qty += it_qty
                                elif it_type == "Waste": exist.total_qty -= it_qty
                            else:
                                if it_type == "Entry":
                                    session.add(InventoryItem(name=it_name, unit=it_unit, total_qty=it_qty))
                            
                            # إضافة للسجل التاريخي
                            session.add(TransactionHistory(item_name=it_name, qty=it_qty, type=it_type, person="CSV Import"))
                            count += 1
                        
                        session.commit()
                        st.success(f"✅ تم استيراد {count} سجل بنجاح وتحديث المخزن!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"حدث خطأ أثناء الاستيراد: {e}")

        # (بقية تبويبات الإدخال اليدوي تظل كما هي...)
        with m_tabs[0]:
            with st.form("manual_entry"):
                item_n = st.text_input("اسم المادة")
                qty_n = st.number_input("الكمية", min_value=0.1)
                if st.form_submit_button("حفظ"):
                    exist = session.query(InventoryItem).filter_by(name=item_n).first()
                    if exist: exist.total_qty += qty_n
                    else: session.add(InventoryItem(name=item_n, unit="قطعة", total_qty=qty_n))
                    session.add(TransactionHistory(item_name=item_n, qty=qty_n, type="Entry", person="Store"))
                    session.commit(); st.success("تم الحفظ")

    Session.remove()
