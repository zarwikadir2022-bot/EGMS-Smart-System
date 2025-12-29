import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import io

# --- 1. بناء هيكل البيانات الموحد (v60) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)
    tasks = relationship("SiteTask", back_populates="site_obj", cascade="all, delete-orphan")

class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); hourly_rate = Column(Float); work_plan = Column(Text)
    logs = relationship("WorkerLog", back_populates="profile")

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True); worker_id = Column(Integer, ForeignKey('worker_profiles.id')); hours = Column(Float); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)
    profile = relationship("WorkerProfile", back_populates="logs")

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True); item = Column(String(100)); unit = Column(String(50)); qty = Column(Float); trans_type = Column(String(20)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class SiteTask(Base):
    __tablename__ = 'site_tasks'
    id = Column(Integer, primary_key=True); site_id = Column(Integer, ForeignKey('sites.id')); task_name = Column(String(100)); unit = Column(String(50)); target_qty = Column(Float)
    site_obj = relationship("Site", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task_obj", cascade="all, delete-orphan")

class TaskLog(Base):
    __tablename__ = 'task_logs'
    id = Column(Integer, primary_key=True); task_id = Column(Integer, ForeignKey('site_tasks.id')); qty_done = Column(Float); notes = Column(Text); image = Column(LargeBinary); timestamp = Column(DateTime, default=datetime.utcnow)
    task_obj = relationship("SiteTask", back_populates="logs")

engine = create_engine('sqlite:///egms_v60_final.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. محرك تقارير PDF ---
def generate_pdf_v60(site_obj, session):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    s_name = site_obj.name.encode('ascii', 'ignore').decode('ascii') or "Site"
    pdf.cell(190, 10, f"EGMS Report: {s_name}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    for t in site_obj.tasks:
        done = sum(l.qty_done for l in t.logs)
        p = (done/t.target_qty)*100 if t.target_qty > 0 else 0
        t_name = t.task_name.encode('ascii', 'ignore').decode('ascii') or "Task"
        pdf.cell(190, 8, f"- {t_name}: {done}/{t.target_qty} {t.unit} ({p:.1f}%)", ln=True)
    return pdf.output()

# --- 3. واجهة البرنامج ---
st.set_page_config(page_title="EGMS Enterprise v60", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.title("🏗️ EGMS Digital ERP v60")
    u_in = st.text_input("Username")
    p_in = st.text_input("Password", type="password")
    if st.button("Login"):
        acc = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store")}
        if u_in in acc and p_in == acc[u_in][0]:
            st.session_state.update({"logged_in": True, "role": acc[u_in][1]})
            st.rerun()
        else: st.error("Access Denied")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.success(f"Role: {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    all_sites = session.query(Site).all()
    
    if role == "Admin":
        st.title("💼 Admin Command Hub")
        tabs = st.tabs(["📊 التحليلات", "📍 الخريطة", "🏗️ متابعة الإنجاز", "👷 العمال", "📦 المخزن", "⚙️ الإعدادات"])

        with tabs[0]: # التحليلات
            df_labor = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            df_profs = pd.read_sql(session.query(WorkerProfile).statement, session.bind)
            if not df_labor.empty and not df_profs.empty:
                df_hr = pd.merge(df_labor, df_profs, left_on='worker_id', right_on='id')
                df_hr['Cost'] = df_hr['hours'] * df_hr['hourly_rate']
                st.plotly_chart(px.pie(df_hr, values='Cost', names='site', title="ميزانية الرواتب"))

        with tabs[3]: # العمال
            st.subheader("إدارة الموارد البشرية")
            with st.form("admin_hr_v60"):
                n = st.text_input("Name"); r = st.number_input("Rate"); pl = st.text_area("Plan")
                if st.form_submit_button("Save Worker"):
                    session.add(WorkerProfile(name=n, hourly_rate=r, work_plan=pl)); session.commit(); st.rerun()
            st.dataframe(pd.read_sql(session.query(WorkerProfile).statement, session.bind), use_container_width=True)

        with tabs[4]: # المخزن (تم الإصلاح هنا ✅)
            st.subheader("📦 رصيد المخزن الفعلي في الحضائر")
            df_store = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_store.empty:
                # حساب الرصيد الصافي (Entry - Exit)
                df_store['net'] = df_store.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                balance = df_store.groupby(['item', 'unit', 'site'])['net'].sum().reset_index()
                st.table(balance.rename(columns={'net': 'الكمية المتوفرة', 'item': 'المادة', 'site': 'الموقع'}))
                st.write("سجل حركات المخزن التفصيلي:")
                st.dataframe(df_store[['item', 'qty', 'trans_type', 'site', 'timestamp']], use_container_width=True)
            else:
                st.info("لا توجد بيانات في المخزن حالياً. اطلب من مسؤول المغازة تسجيل الدخول.")

        with tabs[5]: # الإعدادات
            with st.form("site_setup"):
                sn = st.text_input("Site Name"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("Save Site"):
                    session.add(Site(name=sn, lat=la, lon=lo)); session.commit(); st.rerun()

    elif role == "Store": # واجهة مسؤول المغازة
        st.header("📦 إدارة المغازة")
        if all_sites:
            with st.form("store_f60"):
                it = st.text_input("المادة"); un = st.selectbox("الوحدة", ["كيس", "طن", "كغ"]); qt = st.number_input("الكمية")
                tp = st.radio("نوع العملية", ["Entry", "Exit"]); si = st.selectbox("الموقع", [s.name for s in all_sites])
                if st.form_submit_button("حفظ"):
                    session.add(StoreLog(item=it, unit=un, qty=qt, trans_type=tp, site=si)); session.commit(); st.success("Saved!")

    Session.remove()
