import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px
import io

# --- 1. بناء هيكل قاعدة البيانات (v67) ---
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

engine = create_engine('sqlite:///egms_v67_final.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. واجهة البرنامج ---
st.set_page_config(page_title="EGMS Field Control v67", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;'>🏗️ EGMS Digital ERP v67</h1>", unsafe_allow_html=True)
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
    
    # --- 3. واجهة المدير (Admin) - رقابة وتحليل فقط ---
    if role == "Admin":
        st.title("📊 لوحة الرقابة الإدارية والتحليل")
        tabs = st.tabs(["📈 التحليلات البصرية", "📋 الجرد العام والحي", "📄 استخراج التقارير"])

        with tabs[0]: # التحليلات
            df_inv = pd.read_sql(session.query(InventoryItem).statement, session.bind)
            if not df_inv.empty:
                st.plotly_chart(px.bar(df_inv, x='name', y='total_qty', title="مستويات المخزون الحالية"), use_container_width=True)
            
            df_hist = pd.read_sql(session.query(TransactionHistory).statement, session.bind)
            if not df_hist.empty:
                st.plotly_chart(px.pie(df_hist, names='type', title="توزيع العمليات الميدانية"), use_container_width=True)

        with tabs[1]: # الجرد
            st.subheader("الجرد الحي للمعدات والمواد")
            st.dataframe(df_inv, use_container_width=True)
            st.subheader("سجل الحركات التاريخي")
            st.dataframe(df_hist, use_container_width=True)

        with tabs[2]: # التقارير
            st.subheader("تصدير البيانات للتحليل (Excel/CSV)")
            if not df_hist.empty:
                csv = df_hist.to_csv(index=False).encode('utf-8')
                st.download_button("📥 تحميل التقرير الكامل", csv, "EGMS_Report_v67.csv", "text/csv")

    # --- 4. واجهة مسؤول المغازة (Store) - التحكم الكامل في المدخلات ---
    elif role == "Store":
        st.title("📦 مركز العمليات - مسؤول المغازة")
        m_tabs = st.tabs(["📥 تسجيل/تعريف سلع", "🤝 تسليم عُهدة", "🔙 استرجاع عُهدة", "⚠️ تسجيل تآكل"])

        with m_tabs[0]: # تسجيل أو تعريف سلع جديدة
            st.subheader("إضافة مادة جديدة أو تسجيل دخول كمية")
            with st.form("entry_f_v67"):
                # خيار للاختيار من الموجود أو كتابة اسم جديد
                existing_names = [i.name for i in all_items]
                name_mode = st.radio("نوع الإدخال", ["مادة موجودة مسبقاً", "تعريف مادة/معدة جديدة"])
                
                if name_mode == "مادة موجودة مسبقاً" and existing_names:
                    item_n = st.selectbox("اختر المادة", existing_names)
                    unit_n = session.query(InventoryItem).filter_by(name=item_n).first().unit
                else:
                    item_n = st.text_input("اسم المادة/المعدة الجديدة")
                    unit_n = st.selectbox("وحدة القيس", ["قطعة", "كغ", "متر", "لتر", "طن"])
                
                qty_n = st.number_input("الكمية", min_value=0.1)
                
                if st.form_submit_button("حفظ الحركات"):
                    if not item_n:
                        st.error("يرجى إدخال اسم المادة")
                    else:
                        exist = session.query(InventoryItem).filter_by(name=item_n).first()
                        if exist:
                            exist.total_qty += qty_n
                        else:
                            session.add(InventoryItem(name=item_n, unit=unit_n, total_qty=qty_n))
                        
                        session.add(TransactionHistory(item_name=item_n, qty=qty_n, type="Entry", person="Store"))
                        session.commit()
                        st.success(f"تم تسجيل {qty_n} من {item_n} بنجاح!")
                        st.rerun()

        with m_tabs[1]: # تسليم عُهدة
            if all_items:
                with st.form("handover_f_v67"):
                    it_h = st.selectbox("المادة المراد تسليمها", [i.name for i in all_items])
                    w_name = st.text_input("اسم العامل المستلم")
                    qty_h = st.number_input("الكمية المسلمة", min_value=1.0)
                    if st.form_submit_button("تأكيد التسليم"):
                        item_obj = session.query(InventoryItem).filter_by(name=it_h).first()
                        if item_obj.total_qty >= qty_h:
                            item_obj.total_qty -= qty_h
                            session.add(HandoverLog(worker_name=w_name, item_name=it_h, qty=qty_h))
                            session.add(TransactionHistory(item_name=it_h, qty=qty_h, type="Handover", person=w_name))
                            session.commit()
                            st.success("تم تسجيل العُهدة بنجاح")
                        else: st.error("المخزون لا يكفي")
            else: st.info("المخزن فارغ")

        with m_tabs[2]: # استرجاع عُهدة
            h_logs = session.query(HandoverLog).all()
            if h_logs:
                for log in h_logs:
                    c1, c2 = st.columns([3, 1])
                    c1.warning(f"عُهدة: {log.worker_name} لديه ({log.qty}) {log.item_name}")
                    if c2.button("استرجاع", key=log.id):
                        item_obj = session.query(InventoryItem).filter_by(name=log.item_name).first()
                        item_obj.total_qty += log.qty
                        session.add(TransactionHistory(item_name=log.item_name, qty=log.qty, type="Return", person=log.worker_name))
                        session.delete(log)
                        session.commit()
                        st.rerun()
            else: st.info("لا توجد عُهد مفتوحة حالياً")

        with m_tabs[3]: # تآكل
            if all_items:
                with st.form("waste_f_v67"):
                    it_w = st.selectbox("المادة التالفة", [i.name for i in all_items])
                    qty_w = st.number_input("الكمية التالفة", min_value=0.1)
                    if st.form_submit_button("تسجيل كـ تآكل"):
                        item_obj = session.query(InventoryItem).filter_by(name=it_w).first()
                        if item_obj.total_qty >= qty_w:
                            item_obj.total_qty -= qty_w
                            session.add(TransactionHistory(item_name=it_w, qty=qty_w, type="Waste", person="Store"))
                            session.commit()
                            st.success("تم تسجيل التآكل وتحديث المخزن")
                        else: st.error("الكمية غير متوفرة")

    Session.remove()
