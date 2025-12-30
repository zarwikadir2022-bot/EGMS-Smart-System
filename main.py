import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px

# --- 1. هيكلة قاعدة البيانات (v74) ---
Base = declarative_base()

class InventoryItem(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    unit = Column(String(50))
    total_qty = Column(Float, default=0.0)

class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    work_plan = Column(Text)

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
    type = Column(String(50)) 
    person = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)

# الاتصال بالقاعدة مع خاصية التزامن لـ Streamlit
DB_URL = "sqlite:///egms_v74_stable.db"
engine = create_engine(DB_URL, connect_args={'check_same_thread': False})

# محاولة إنشاء الجداول بأمان
try:
    Base.metadata.create_all(engine)
except Exception as e:
    st.error(f"Database Error: {e}")

session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. إعدادات التصميم الجذاب ---
st.set_page_config(page_title="EGMS Stable v74", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border-radius: 10px; padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #003366;
    }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #003366; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. نظام الدخول والواجهات ---
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;'>🏗️ EGMS Digital ERP</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        u = st.text_input("اسم المستخدم"); p = st.text_input("كلمة المرور", type="password")
        if st.button("دخول"):
            acc = {"admin": ("egms2025", "Admin"), "magaza": ("store2025", "Store")}
            if u in acc and p == acc[u][0]:
                st.session_state.update({"logged_in": True, "role": acc[u][1]})
                st.rerun()
            else: st.error("❌ خطأ في الدخول")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.markdown(f"### 👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    # جلب البيانات
    df_inv = pd.read_sql(session.query(InventoryItem).statement, session.bind)
    df_hist = pd.read_sql(session.query(TransactionHistory).statement, session.bind)
    if not df_hist.empty: df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'])
    
    df_workers = pd.read_sql(session.query(WorkerProfile).statement, session.bind)

    if role == "Admin":
        st.markdown("<h2>📊 لوحة تحكم المدير</h2>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي المواد", len(df_inv))
        m2.metric("العمال", len(df_workers))
        
        today_ops = 0
        if not df_hist.empty:
            today_ops = len(df_hist[df_hist['timestamp'].dt.date == datetime.now().date()])
        m3.metric("عمليات اليوم", today_ops)
        m4.metric("العُهد", len(session.query(HandoverLog).all()))
        
        tabs = st.tabs(["📈 التحليلات", "📋 الجرد الحي", "📄 التقارير"])
        with tabs[0]:
            if not df_inv.empty:
                col1, col2 = st.columns(2)
                col1.plotly_chart(px.bar(df_inv, x='name', y='total_qty', color='name', title="رصيد المخزن"), use_container_width=True)
                if not df_hist.empty:
                    col2.plotly_chart(px.pie(df_hist, names='type', title="توزيع العمليات"), use_container_width=True)

    elif role == "Store":
        st.markdown("<h2>📦 مركز العمليات - المغازة</h2>", unsafe_allow_html=True)
        m_tabs = st.tabs(["📥 تسجيل سلع", "👷 العمال", "🤝 تسليم عُهدة", "🔙 استرجاع", "📤 استيراد"])
        
        with m_tabs[0]:
            with st.form("entry_v74"):
                it_name = st.text_input("اسم المادة")
                it_unit = st.selectbox("الوحدة", ["وحدة", "كغ", "كيس", "لتر", "متر مربع", "متر مكعب"])
                it_qty = st.number_input("الكمية", min_value=0.1)
                if st.form_submit_button("حفظ"):
                    exist = session.query(InventoryItem).filter_by(name=it_name).first()
                    if exist: exist.total_qty += it_qty
                    else: session.add(InventoryItem(name=it_name, unit=it_unit, total_qty=it_qty))
                    session.add(TransactionHistory(item_name=it_name, qty=it_qty, type="Entry", person="Store"))
                    session.commit(); st.success("✅ تم بنجاح"); st.rerun()

    Session.remove()
