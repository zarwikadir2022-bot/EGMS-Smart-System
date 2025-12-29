import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import io

# --- 1. بناء هيكل البيانات الموحد (v56) ---
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

# إعداد المحرك v56
engine = create_engine('sqlite:///egms_final_v56.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. محرك تقارير PDF الآمن ---
def generate_safe_pdf_v56(site_obj, session):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    safe_site_name = site_obj.name.encode('ascii', 'ignore').decode('ascii') or "Project Site"
    pdf.cell(190, 10, f"EGMS Report: {safe_site_name}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    for t in site_obj.tasks:
        done = sum(l.qty_done for l in t.logs)
        safe_task = t.task_name.encode('ascii', 'ignore').decode('ascii') or "Phase"
        pdf.cell(190, 7, f"- {safe_task}: {done}/{t.target_qty} {t.unit}", ln=True)
    return pdf.output()

# --- 3. واجهة البرنامج ---
st.set_page_config(page_title="EGMS Business Analytics v56", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;'>🏗️ EGMS Digital ERP & Analytics</h1>", unsafe_allow_html=True)
    u_in = st.text_input("Username")
    p_in = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store")}
        if u_in in acc and p_in == acc[u_in][0]:
            st.session_state.update({"logged_in": True, "role": acc[u_in][1]})
            st.rerun()
        else: st.error("Login Failed")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.success(f"Connected: {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    all_sites = session.query(Site).all()
    
    # --- 4. واجهة المدير (Command & Analytics) ---
    if role == "Admin":
        st.title("💼 Command Center & Data Insights")
        
        # بطاقات ملخص البيانات (KPI Cards)
        c1, c2, c3 = st.columns(3)
        c1.metric("المواقع النشطة", len(all_sites))
        
        tabs = st.tabs(["📊 التحليلات", "📍 الخريطة", "🏗️ الإنجاز", "👷 العمال", "📦 المخزن", "⚙️ الإعدادات"])

        with tabs[0]: # تبويب التحليلات الجديد ✅
            st.subheader("📈 رؤى البيانات (Data Insights)")
            
            # 1. تحليل تكاليف العمال
            df_labor_logs = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            df_profiles = pd.read_sql(session.query(WorkerProfile).statement, session.bind)
            
            if not df_labor_logs.empty and not df_profiles.empty:
                df_hr = pd.merge(df_labor_logs, df_profiles, left_on='worker_id', right_on='id')
                df_hr['Total Cost'] = df_hr['hours'] * df_hr['hourly_rate']
                
                fig_pie = px.pie(df_hr, values='Total Cost', names='site', title="توزيع ميزانية الرواتب حسب الموقع")
                st.plotly_chart(fig_pie, use_container_width=True)
            
            # 2. تحليل تقدم الأشغال
            df_tasks = pd.read_sql(session.query(SiteTask).statement, session.bind)
            if not df_tasks.empty:
                # حساب الإنجاز لكل مهمة
                task_data = []
                for t in session.query(SiteTask).all():
                    done = sum(l.qty_done for l in t.logs)
                    task_data.append({"المرحلة": t.task_name, "المنجز": done, "المستهدف": t.target_qty})
                
                df_prog = pd.DataFrame(task_data)
                fig_bar = px.bar(df_prog, x='المرحلة', y=['المنجز', 'المستهدف'], barmode='group', title="مقارنة الإنجاز الفعلي مقابل المستهدف")
                st.plotly_chart(fig_bar, use_container_width=True)

        with tabs[1]: # الخريطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')

        with tabs[2]: # الإنجاز بالصور
            for s in all_sites:
                with st.expander(f"تحديثات موقع: {s.name}"):
                    for tk in s.tasks:
                        done = sum(l.qty_done for l in tk.logs)
                        st.write(f"**{tk.task_name}**: {done}/{tk.target_qty} {tk.unit}")
                        st.progress(min(done/tk.target_qty, 1.0) if tk.target_qty > 0 else 0)

        with tabs[5]: # الإعدادات
            st.subheader("إضافة مواقع ومهام")
            with st.form("site_v56"):
                sn = st.text_input("Site Name"); la = st.number_input("Lat", value=36.5); lo = st.number_input("Lon", value=10.2)
                if st.form_submit_button("Save Site"):
                    session.add(Site(name=sn, lat=la, lon=lo)); session.commit(); st.rerun()

    # --- 5. واجهة مسؤول المغازة (Store) - تم التأكد من الربط ✅ ---
    elif role == "Store":
        st.header("📦 إدارة المغازة")
        if all_sites:
            with st.form("store_f56"):
                item = st.text_input("المادة"); unit = st.selectbox("الوحدة", ["كيس", "طن", "كغ"])
                qty = st.number_input("الكمية"); t_type = st.radio("النوع", ["Entry", "Exit"])
                s_name = st.selectbox("الموقع", [s.name for s in all_sites])
                if st.form_submit_button("حفظ"):
                    session.add(StoreLog(item=item, unit=unit, qty=qty, trans_type=t_type, site=s_name))
                    session.commit(); st.success("Data Saved!")
        else: st.warning("Please add sites first.")

    # --- 6. واجهة مسؤول العمال (Labor) ---
    elif role == "Labor":
        st.header("👷 سجل العمال اليومي")
        profs = session.query(WorkerProfile).all()
        if profs and all_sites:
            with st.form("labor_f56"):
                w = st.selectbox("العامل", profs, format_func=lambda x: x.name)
                h = st.number_input("الساعات"); s = st.selectbox("الموقع", [s.name for s in all_sites])
                if st.form_submit_button("تسجيل"):
                    session.add(WorkerLog(worker_id=w.id, hours=h, site=s))
                    session.commit(); st.success("Logged!")

    Session.remove()
