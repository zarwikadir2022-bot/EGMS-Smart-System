import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px

# --- 1. هيكلة قاعدة البيانات (v75) ---
Base = declarative_base()

class InventoryItem(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); unit = Column(String(50)); total_qty = Column(Float, default=0.0)

class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); work_plan = Column(Text)

class HandoverLog(Base):
    __tablename__ = 'handover_logs'
    id = Column(Integer, primary_key=True); worker_name = Column(String(100)); item_name = Column(String(100)); qty = Column(Float); timestamp = Column(DateTime, default=datetime.utcnow)

class TransactionHistory(Base):
    __tablename__ = 'transaction_history'
    id = Column(Integer, primary_key=True); item_name = Column(String(100)); qty = Column(Float); type = Column(String(50)); person = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

# الاتصال بقاعدة بيانات جديدة ومستقرة
DB_URL = "sqlite:///egms_v75_final.db"
engine = create_engine(DB_URL, connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))

# --- 2. التصميم الجمالي ---
st.set_page_config(page_title="EGMS ERP v75", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    h1, h2 { color: #003366; }
    div[data-testid="metric-container"] {
        background-color: white; border-radius: 10px; padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-left: 5px solid #003366;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;'>🏗️ EGMS Digital ERP v75</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        u = st.text_input("Username"); p = st.text_input("Password", type="password")
        if st.button("دخول"):
            acc = {"admin": ("egms2025", "Admin"), "magaza": ("store2025", "Store")}
            if u in acc and p == acc[u][0]:
                st.session_state.update({"logged_in": True, "role": acc[u][1]})
                st.rerun()
            else: st.error("❌ بيانات خاطئة")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.markdown(f"### 👤 {role}")
    if st.sidebar.button("تسجيل الخروج"): st.session_state.clear(); st.rerun()

    # جلب البيانات الحالية
    df_inv = pd.read_sql(session.query(InventoryItem).statement, session.bind)
    df_hist = pd.read_sql(session.query(TransactionHistory).statement, session.bind)
    df_workers = pd.read_sql(session.query(WorkerProfile).statement, session.bind)
    
    if not df_hist.empty:
        df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'])

    # --- واجهة المدير ---
    if role == "Admin":
        st.title("📊 لوحة القيادة العامة")
        
        # عرض الحالة إذا كانت المنظومة فارغة
        if df_inv.empty and df_workers.empty:
            st.warning("⚠️ المنظومة فارغة حالياً لأنها قاعدة بيانات جديدة. يرجى الدخول بحساب 'magaza' لإضافة العمال والمواد.")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("المواد بالمخزن", len(df_inv))
        m2.metric("عدد العمال", len(df_workers))
        m3.metric("عمليات اليوم", len(df_hist) if not df_hist.empty else 0)

        tabs = st.tabs(["📈 التحليلات", "📋 الجرد التفصيلي"])
        with tabs[0]:
            if not df_inv.empty:
                st.plotly_chart(px.bar(df_inv, x='name', y='total_qty', title="رصيد المخزن"), use_container_width=True)
            else: st.info("لا توجد رسوم بيانية للعرض؛ قم بإضافة بيانات أولاً.")

    # --- واجهة المغازة ---
    elif role == "Store":
        st.title("📦 عمليات المغازة")
        m_tabs = st.tabs(["📥 تسجيل مواد", "👷 إدارة العمال", "🤝 تسليم عُهدة", "🔙 استرجاع"])
        
        with m_tabs[0]: # تسجيل المواد
            with st.form("entry_v75"):
                it = st.text_input("اسم المادة"); un = st.selectbox("الوحدة", ["كيس", "قطعة", "كغ"])
                qt = st.number_input("الكمية", min_value=0.1)
                if st.form_submit_button("حفظ"):
                    exist = session.query(InventoryItem).filter_by(name=it).first()
                    if exist: exist.total_qty += qt
                    else: session.add(InventoryItem(name=it, unit=un, total_qty=qt))
                    session.add(TransactionHistory(item_name=it, qty=qt, type="Entry", person="Store"))
                    session.commit(); st.success("✅ تم التسجيل"); st.rerun()

        with m_tabs[1]: # إدارة العمال
            with st.form("worker_v75"):
                wn = st.text_input("اسم العامل"); wp = st.text_area("خطة العمل")
                if st.form_submit_button("إضافة عامل"):
                    session.add(WorkerProfile(name=wn, work_plan=wp))
                    session.commit(); st.success("✅ تم الإضافة"); st.rerun()
            st.dataframe(df_workers, use_container_width=True)

        with m_tabs[2]: # تسليم عُهدة
            if not df_inv.empty and not df_workers.empty:
                with st.form("handover_v75"):
                    item_sel = st.selectbox("المادة/المعدة", df_inv['name'])
                    worker_sel = st.selectbox("العامل المستلم", df_workers['name'])
                    qty_sel = st.number_input("الكمية", min_value=1.0)
                    if st.form_submit_button("تأكيد التسليم"):
                        item_obj = session.query(InventoryItem).filter_by(name=item_sel).first()
                        if item_obj.total_qty >= qty_sel:
                            item_obj.total_qty -= qty_sel
                            session.add(HandoverLog(worker_name=worker_sel, item_name=item_sel, qty=qty_sel))
                            session.add(TransactionHistory(item_name=item_sel, qty=qty_sel, type="Handover", person=worker_sel))
                            session.commit(); st.success("✅ تم التسليم"); st.rerun()
                        else: st.error("الكمية غير كافية!")
            else: st.warning("يجب إضافة مواد وعمال أولاً.")

    Session.remove()
