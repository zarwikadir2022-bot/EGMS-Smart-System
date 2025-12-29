import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import io
from PIL import Image

# --- 1. إعدادات قاعدة البيانات (v49) ---
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

engine = create_engine('sqlite:///egms_royal_v49.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. دالة توليد تقرير PDF ---
def create_pdf(site_name, session):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, f"EGMS Construction Report: {site_name}", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    # قسم المهام
    site_obj = session.query(Site).filter_by(name=site_name).first()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, "1. Project Progress & Tasks", ln=True)
    pdf.set_font("Arial", size=10)
    for task in site_obj.tasks:
        total_done = sum(log.qty_done for log in task.logs)
        pdf.cell(190, 7, f"- {task.task_name}: {total_done}/{task.target_qty} {task.unit}", ln=True)
        # إضافة الصورة الأخيرة إذا وجدت
        last_img = session.query(TaskLog).filter(TaskLog.task_id == task.id, TaskLog.image != None).order_by(TaskLog.timestamp.desc()).first()
        if last_img:
            img = Image.open(io.BytesIO(last_img.image))
            img_path = f"temp_{task.id}.png"
            img.save(img_path)
            pdf.image(img_path, x=150, y=pdf.get_y()-7, w=30)
    pdf.ln(5)
    return pdf.output()

# --- 3. واجهة المستخدم ---
st.set_page_config(page_title="EGMS Royal ERP v49", layout="wide")

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🏗️ EGMS DIGITAL ERP - LOGIN")
    u = st.text_input("Username"); p = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store")}
        if u in acc and p == acc[u][0]:
            st.session_state.update({"logged_in": True, "role": acc[u][1]}); st.rerun()
        else: st.error("Invalid Login")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.header(f"Role: {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    all_sites = session.query(Site).all()
    
    if role == "Admin":
        st.title("💼 Executive Dashboard v49")
        tabs = st.tabs(["📊 Reports & PDF", "👷 Human Resources", "📦 Inventory", "⚙️ Setup"])

        with tabs[0]: # التقارير وتحميل الـ PDF
            if all_sites:
                sel_site = st.selectbox("Select Site for Report", [s.name for s in all_sites])
                if st.button("📄 Generate & Preview PDF"):
                    pdf_data = create_pdf(sel_site, session)
                    st.download_button(label="📥 Download PDF Report", data=pdf_data, file_name=f"Report_{sel_site}.pdf", mime="application/pdf")
            else: st.info("No sites available.")

        with tabs[1]: # إدارة العمال
            st.subheader("Manage Workers")
            with st.form("hr_form"):
                wn = st.text_input("Worker Name"); wr = st.number_input("Hourly Rate (TND)")
                if st.form_submit_button("Save Profile"):
                    session.add(WorkerProfile(name=wn, hourly_rate=wr)); session.commit(); st.rerun()
            st.dataframe(pd.read_sql(session.query(WorkerProfile).statement, session.bind), use_container_width=True)

        with tabs[3]: # الإعدادات
            st.subheader("System Configuration")
            with st.form("site_form"):
                sn = st.text_input("Site Name"); sla = st.number_input("Lat", value=36.0); slo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("Add Site"):
                    try: session.add(Site(name=sn, lat=sla, lon=slo)); session.commit(); st.rerun()
                    except: st.error("Duplicate Site Name")
            if all_sites:
                st.divider()
                with st.form("task_form"):
                    sid = st.selectbox("Site", [s.id for s in all_sites], format_func=lambda x: next(s.name for s in all_sites if s.id == x))
                    tn = st.text_input("Task Name"); tu = st.selectbox("Unit", ["m3", "m2", "Kg", "Sac"]); tq = st.number_input("Target Qty")
                    if st.form_submit_button("Add Task Phase"):
                        session.add(SiteTask(site_id=sid, task_name=tn, unit=tu, target_qty=tq)); session.commit(); st.success("Task Added")

    # واجهة العمال (Labor)
    elif role == "Labor":
        st.header("👷 Labor Daily Logs")
        profiles = session.query(WorkerProfile).all()
        if profiles and all_sites:
            with st.form("labor_log"):
                w = st.selectbox("Worker", profiles, format_func=lambda x: x.name)
                h = st.number_input("Hours Worked"); s = st.selectbox("Site", [s.name for s in all_sites])
                if st.form_submit_button("Log Hours"):
                    session.add(WorkerLog(worker_id=w.id, hours=h, site=s)); session.commit(); st.success("Logged!")

    # واجهة الأشغال (Work)
    elif role == "Work":
        st.header("🏗️ Field Progress Report")
        if all_sites:
            s_choice = st.selectbox("Site", all_sites, format_func=lambda x: x.name)
            site_tasks = session.query(SiteTask).filter_by(site_id=s_choice.id).all()
            if site_tasks:
                with st.form("work_log"):
                    tk = st.selectbox("Task Phase", site_tasks, format_func=lambda x: x.task_name)
                    qd = st.number_input(f"Qty Done ({tk.unit})"); note = st.text_area("Notes")
                    img = st.file_uploader("📸 Evidence Photo", type=['jpg', 'png'])
                    if st.form_submit_button("Submit Report"):
                        img_b = img.read() if img else None
                        session.add(TaskLog(task_id=tk.id, qty_done=qd, notes=note, image=img_b)); session.commit(); st.success("Submitted!")

    session.close()
