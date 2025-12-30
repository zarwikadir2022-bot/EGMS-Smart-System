import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px

# --- 1. هيكلة قاعدة البيانات المتطورة (v69) ---
Base = declarative_base()

class InventoryItem(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    unit = Column(String(50)) # وحدة القيس
    total_qty = Column(Float, default=0.0)

class WorkerProfile(Base): # سجل العمال وخططهم
    __tablename__ = 'worker_profiles'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    work_plan = Column(Text) # خطة العمل

class HandoverLog(Base): # العُهد النشطة
    __tablename__ = 'handover_logs'
    id = Column(Integer, primary_key=True)
    worker_name = Column(String(100))
    item_name = Column(String(100))
    qty = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class TransactionHistory(Base): # السجل الدائم
    __tablename__ = 'transaction_history'
    id = Column(Integer, primary_key=True)
    item_name = Column(String(100))
    qty = Column(Float)
    type = Column(String(50)) # Entry, Handover, Return, Waste
    person = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_final_v69.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))

# --- 2. واجهة التطبيق ---
st.set_page_config(page_title="EGMS Pro v69", layout="wide")

# قائمة وحدات القيس المطلوبة
UNITS_LIST = ["وحدة", "كغ", "كيس", "لتر", "متر مربع", "متر مكعب"]

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;'>🏗️ EGMS Digital ERP v69</h1>", unsafe_allow_html=True)
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "magaza": ("store2025", "Store")}
        if u in acc and p == acc[u][0]:
            st.session_state.update({"logged_in": True, "role": acc[u][1]})
            st.rerun()
        else: st.error("Access Denied")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.success(f"Connected: {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    all_items = session.query(InventoryItem).all()
    all_workers = session.query(WorkerProfile).all()

    # --- 3. واجهة المدير (Admin) ---
    if role == "Admin":
        st.title("📊 رقابة الإدارة والتحليل")
        tabs = st.tabs(["📉 التحليلات", "📦 الجرد التفصيلي", "👷 إدارة العمال"])

        with tabs[2]: # إدارة العمال
            st.subheader("تعريف العمال وخطط العمل")
            with st.form("add_worker"):
                wn = st.text_input("اسم العامل الكامل")
                wp = st.text_area("خطة العمل الموكلة له")
                if st.form_submit_button("حفظ ملف العامل"):
                    session.add(WorkerProfile(name=wn, work_plan=wp))
                    session.commit(); st.success("تم الحفظ"); st.rerun()
            st.dataframe(pd.read_sql(session.query(WorkerProfile).statement, session.bind), use_container_width=True)

        with tabs[1]: # الجرد
            df_inv = pd.read_sql(session.query(InventoryItem).statement, session.bind)
            st.dataframe(df_inv, use_container_width=True)

    # --- 4. واجهة مسؤول المغازة (Store) ---
    elif role == "Store":
        st.title("📦 مركز العمليات - المغازة")
        m_tabs = st.tabs(["📥 تسجيل/تعريف سلع", "🤝 تسليم عُهدة", "🔙 استرجاع عُهدة", "📤 استيراد CSV"])

        with m_tabs[0]: # تسجيل دخول سلع مع الوحدات الجديدة ✅
            with st.form("entry_v69"):
                st.subheader("إضافة مواد للمخزن")
                existing_names = [i.name for i in all_items]
                name_mode = st.radio("الوضع", ["مادة موجودة", "تعريف مادة جديدة"])
                
                if name_mode == "مادة موجودة" and existing_names:
                    item_n = st.selectbox("المادة", existing_names)
                    unit_n = session.query(InventoryItem).filter_by(name=item_n).first().unit
                    st.info(f"الوحدة المسجلة: {unit_n}")
                else:
                    item_n = st.text_input("اسم المادة الجديدة")
                    unit_n = st.selectbox("وحدة القيس", UNITS_LIST)
                
                qty_n = st.number_input("الكمية", min_value=0.1)
                if st.form_submit_button("تأكيد الدخول"):
                    exist = session.query(InventoryItem).filter_by(name=item_n).first()
                    if exist: exist.total_qty += qty_n
                    else: session.add(InventoryItem(name=item_n, unit=unit_n, total_qty=qty_n))
                    session.add(TransactionHistory(item_name=item_n, qty=qty_n, type="Entry", person="Store"))
                    session.commit(); st.success("✅ تم التحديث"); st.rerun()

        with m_tabs[1]: # تسليم عُهدة مع اسم العامل وخطته ✅
            st.subheader("تسليم معدات/مواد لعامل")
            if all_items and all_workers:
                with st.form("handover_v69"):
                    it_h = st.selectbox("المعدات", [i.name for i in all_items])
                    w_obj = st.selectbox("العامل المستلم", all_workers, format_func=lambda x: x.name)
                    st.warning(f"خطة عمل العامل: {w_obj.work_plan}") # عرض خطة العمل فوراً
                    qty_h = st.number_input("الكمية", min_value=1.0)
                    if st.form_submit_button("تأكيد تسليم العُهدة"):
                        item = session.query(InventoryItem).filter_by(name=it_h).first()
                        if item.total_qty >= qty_h:
                            item.total_qty -= qty_h
                            session.add(HandoverLog(worker_name=w_obj.name, item_name=it_h, qty=qty_h))
                            session.add(TransactionHistory(item_name=it_h, qty=qty_h, type="Handover", person=w_obj.name))
                            session.commit(); st.success(f"تم التسليم لـ {w_obj.name}"); st.rerun()
                        else: st.error("المخزن لا يكفي!")
            else: st.info("يرجى التأكد من إضافة عمال ومواد أولاً.")

        with m_tabs[2]: # استرجاع عُهدة
            h_logs = session.query(HandoverLog).all()
            if h_logs:
                for log in h_logs:
                    c1, c2 = st.columns([3, 1])
                    c1.warning(f"عُهدة: {log.worker_name} لديه ({log.qty}) {log.item_name}")
                    if c2.button("استرجاع", key=log.id):
                        item = session.query(InventoryItem).filter_by(name=log.item_name).first()
                        item.total_qty += log.qty
                        session.add(TransactionHistory(item_name=log.item_name, qty=log.qty, type="Return", person=log.worker_name))
                        session.delete(log)
                        session.commit(); st.rerun()
            else: st.info("لا توجد عُهد مفتوحة حالياً.")

    Session.remove()
