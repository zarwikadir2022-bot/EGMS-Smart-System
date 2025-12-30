import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px

# --- 1. هيكلة قاعدة البيانات (v73) ---
Base = declarative_base()

class InventoryItem(Base):
    __tablename__ = 'inventory'; id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); unit = Column(String(50)); total_qty = Column(Float, default=0.0)

class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'; id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); work_plan = Column(Text)

class HandoverLog(Base):
    __tablename__ = 'handover_logs'; id = Column(Integer, primary_key=True); worker_name = Column(String(100)); item_name = Column(String(100)); qty = Column(Float); timestamp = Column(DateTime, default=datetime.utcnow)

class TransactionHistory(Base):
    __tablename__ = 'transaction_history'; id = Column(Integer, primary_key=True); item_name = Column(String(100)); qty = Column(Float); type = Column(String(50)); person = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_v73_final.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. إعدادات الجمالية CSS ---
st.set_page_config(page_title="EGMS Smart ERP v73", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3 { color: #003366; font-family: 'Segoe UI', sans-serif; }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05); border-left: 5px solid #003366;
    }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #003366; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. تسجيل الدخول ---
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
            else: st.error("❌ البيانات غير صحيحة")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.markdown(f"## 👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    # جلب وتحويل البيانات (إصلاح خطأ Datetime)
    df_inv = pd.read_sql(session.query(InventoryItem).statement, session.bind)
    df_hist = pd.read_sql(session.query(TransactionHistory).statement, session.bind)
    if not df_hist.empty:
        df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp']) # التعديل الجوهري هنا ✅

    df_workers = pd.read_sql(session.query(WorkerProfile).statement, session.bind)
    handover_count = len(session.query(HandoverLog).all())

    if role == "Admin":
        st.markdown("<h2>📊 لوحة القيادة العامة</h2>", unsafe_allow_html=True)
        
        # البطاقات الإحصائية (Metrics)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي المواد", len(df_inv))
        m2.metric("العمال المسجلين", len(df_workers))
        
        # حساب عمليات اليوم بأمان
        if not df_hist.empty:
            today_count = len(df_hist[df_hist['timestamp'].dt.date == datetime.now().date()])
        else: today_count = 0
        
        m3.metric("عمليات اليوم", today_count)
        m4.metric("العُهد المفتوحة", handover_count)
        
        tabs = st.tabs(["📈 التحليلات", "📋 سجلات الجرد", "📄 التقارير"])
        with tabs[0]:
            if not df_inv.empty:
                c_a, c_b = st.columns(2)
                c_a.plotly_chart(px.bar(df_inv, x='name', y='total_qty', color='name', template="plotly_white", title="مستويات المخزن"), use_container_width=True)
                if not df_hist.empty:
                    c_b.plotly_chart(px.pie(df_hist, names='type', hole=0.3, title="توزيع العمليات الميدانية"), use_container_width=True)

    elif role == "Store":
        st.markdown("<h2>📦 مركز عمليات المغازة</h2>", unsafe_allow_html=True)
        m_tabs = st.tabs(["📥 تسجيل سلع", "👷 إدارة العمال", "🤝 تسليم عُهدة", "🔙 استرجاع عُهدة", "📤 استيراد CSV"])
        
        with m_tabs[0]: # تسجيل مواد
            with st.form("entry_form"):
                it_name = st.text_input("اسم المادة")
                it_unit = st.selectbox("الوحدة", ["وحدة", "كغ", "كيس", "لتر", "متر مربع", "متر مكعب"])
                it_qty = st.number_input("الكمية", min_value=0.1)
                if st.form_submit_button("حفظ"):
                    exist = session.query(InventoryItem).filter_by(name=it_name).first()
                    if exist: exist.total_qty += it_qty
                    else: session.add(InventoryItem(name=it_name, unit=it_unit, total_qty=it_qty))
                    session.add(TransactionHistory(item_name=it_name, qty=it_qty, type="Entry", person="Store"))
                    session.commit(); st.success("✅ تم التحديث"); st.rerun()

        with m_tabs[1]: # إضافة عمال
            with st.form("worker_form"):
                wn = st.text_input("اسم العامل الجديد"); wp = st.text_area("خطة العمل")
                if st.form_submit_button("إضافة"):
                    session.add(WorkerProfile(name=wn, work_plan=wp)); session.commit(); st.success("تم!"); st.rerun()

        with m_tabs[2]: # تسليم عُهدة
            if not df_inv.empty and not df_workers.empty:
                with st.form("hand_form"):
                    item_sel = st.selectbox("المعدات", df_inv['name'])
                    worker_sel = st.selectbox("العامل", df_workers['name'])
                    qty_sel = st.number_input("الكمية", min_value=1.0)
                    if st.form_submit_button("تسليم"):
                        # (منطق التسليم المعتاد...)
                        item_obj = session.query(InventoryItem).filter_by(name=item_sel).first()
                        if item_obj.total_qty >= qty_sel:
                            item_obj.total_qty -= qty_sel
                            session.add(HandoverLog(worker_name=worker_sel, item_name=item_sel, qty=qty_sel))
                            session.add(TransactionHistory(item_name=item_sel, qty=qty_sel, type="Handover", person=worker_sel))
                            session.commit(); st.success("تم!"); st.rerun()

    Session.remove()
