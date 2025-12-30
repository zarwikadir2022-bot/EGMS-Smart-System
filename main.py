import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime

# --- 1. هيكلة قاعدة البيانات المتطورة (v65) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True)

class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True)
    holdings = relationship("HandoverLog", back_populates="worker")

class InventoryItem(Base): # سجل المواد والمعدات الكلي
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True)
    unit = Column(String(50)); total_qty = Column(Float, default=0.0)

class StoreLog(Base): # سجل الحركات التاريخي (دخول/خروج/تآكل)
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True); item_name = Column(String(100))
    qty = Column(Float); type = Column(String(50)) # Entry, Exit, Waste (تآكل)
    site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)
    recipient = Column(String(100), nullable=True) # اسم المستلم إن وجد

class HandoverLog(Base): # سجل العُهدة الحالية (النشطة فقط)
    __tablename__ = 'handover_logs'
    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey('worker_profiles.id'))
    item_name = Column(String(100)); qty = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    worker = relationship("WorkerProfile", back_populates="holdings")

engine = create_engine('sqlite:///egms_inventory_v65.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))

# --- 2. واجهة التطبيق ---
st.set_page_config(page_title="EGMS Pro Inventory v65", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.title("🏗️ نظام الجرد الاحترافي - EGMS")
    u = st.text_input("User"); p = st.text_input("Pass", type="password")
    if st.button("دخول"):
        acc = {"admin": ("egms2025", "Admin"), "magaza": ("store2025", "Store")}
        if u in acc and p == acc[u][0]:
            st.session_state.update({"logged_in": True, "role": acc[u][1]})
            st.rerun()
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.success(f"المستخدم: {role}")
    if st.sidebar.button("خروج"): st.session_state.clear(); st.rerun()

    # --- 3. واجهة المدير (Admin) - الرقابة والجرد ---
    if role == "Admin":
        st.title("📊 لوحة الرقابة المركزية")
        tabs = st.tabs(["📦 الجرد العام", "👷 عُهد العمال", "🏚️ الهالك والتآكل", "⚙️ الإعدادات"])
        
        with tabs[0]: # الجرد العام
            df_inv = pd.read_sql(session.query(InventoryItem).statement, session.bind)
            st.subheader("مخزون الشركة الفعلي")
            st.dataframe(df_inv, use_container_width=True)

        with tabs[1]: # عُهد العمال
            st.subheader("البحث عن المعدات الموجودة حالياً لدى العمال")
            df_hand = pd.read_sql(session.query(HandoverLog).statement, session.bind)
            if not df_hand.empty:
                st.dataframe(df_hand, use_container_width=True)
            else: st.info("لا توجد عُهد مفتوحة حالياً.")

        with tabs[2]: # الهالك والتآكل
            st.subheader("تقرير المواد والمعدات التالفة")
            df_waste = pd.read_sql(session.query(StoreLog).filter(StoreLog.type == "Waste").statement, session.bind)
            st.dataframe(df_waste, use_container_width=True)

        with tabs[3]: # الإعدادات
            st.subheader("تعريف البيانات الأساسية")
            c1, c2 = st.columns(2)
            with c1:
                with st.form("add_item"):
                    it = st.text_input("اسم المعدة/المادة الجديدة")
                    un = st.selectbox("الوحدة", ["قطعة", "كغ", "طن", "متر", "لتر", "صندوق"])
                    if st.form_submit_button("إضافة للمخزن"):
                        session.add(InventoryItem(name=it, unit=un)); session.commit(); st.rerun()
            with c2:
                with st.form("add_worker"):
                    wn = st.text_input("اسم العامل الجديد")
                    if st.form_submit_button("إضافة عامل"):
                        session.add(WorkerProfile(name=wn)); session.commit(); st.rerun()

    # --- 4. واجهة مسؤول المغازة (Store) - العمليات الميدانية ---
    elif role == "Store":
        st.title("📦 مركز إدارة العمليات - المغازة")
        m_tabs = st.tabs(["📥 دخول سلع", "🤝 تسليم عُهدة", "🔙 استرجاع عُهدة", "⚠️ تسجيل تآكل/هالك"])

        items = session.query(InventoryItem).all()
        workers = session.query(WorkerProfile).all()

        with m_tabs[0]: # دخول سلع
            with st.form("entry"):
                it_ch = st.selectbox("المادة", [i.name for i in items])
                qty = st.number_input("الكمية المشتراة/الداخلة", min_value=0.1)
                if st.form_submit_button("تسجيل دخول"):
                    item = session.query(InventoryItem).filter_by(name=it_ch).first()
                    item.total_qty += qty
                    session.add(StoreLog(item_name=it_ch, qty=qty, type="Entry"))
                    session.commit(); st.success("تم التحديث")

        with m_tabs[1]: # تسليم عُهدة
            with st.form("handover"):
                it_ch = st.selectbox("المعدة/المادة المسلمة", [i.name for i in items])
                w_ch = st.selectbox("اسم المستلم (العامل)", [w.name for w in workers])
                qty = st.number_input("الكمية المسلمة", min_value=0.1)
                if st.form_submit_button("تأكيد التسليم"):
                    item = session.query(InventoryItem).filter_by(name=it_ch).first()
                    if item.total_qty >= qty:
                        item.total_qty -= qty
                        worker = session.query(WorkerProfile).filter_by(name=w_ch).first()
                        session.add(HandoverLog(worker_id=worker.id, item_name=it_ch, qty=qty))
                        session.add(StoreLog(item_name=it_ch, qty=qty, type="Exit", recipient=w_ch))
                        session.commit(); st.success(f"تم التسليم لـ {w_ch}")
                    else: st.error("الكمية في المخزن غير كافية!")

        with m_tabs[2]: # استرجاع عُهدة
            st.subheader("الأدوات الموجودة في الميدان حالياً")
            hand_logs = session.query(HandoverLog).all()
            if hand_logs:
                for log in hand_logs:
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"👷 {log.worker.name} لديه {log.qty} {log.item_name}")
                    if c2.button("استرجاع", key=log.id):
                        item = session.query(InventoryItem).filter_by(name=log.item_name).first()
                        item.total_qty += log.qty
                        session.delete(log)
                        session.commit(); st.rerun()

        with m_tabs[3]: # تسجيل تآكل/هالك
            with st.form("waste"):
                it_ch = st.selectbox("المادة التالفة", [i.name for i in items])
                qty = st.number_input("الكمية التالفة", min_value=0.1)
                note = st.text_area("سبب التلف (تآكل، كسر، رطوبة...)")
                if st.form_submit_button("تسجيل كـ هالك"):
                    item = session.query(InventoryItem).filter_by(name=it_ch).first()
                    if item.total_qty >= qty:
                        item.total_qty -= qty
                        session.add(StoreLog(item_name=it_ch, qty=qty, type="Waste"))
                        session.commit(); st.success("تم تسجيل الهالك وتحديث المخزن")

    Session.remove()
