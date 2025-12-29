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

# --- 1. بناء هيكل البيانات الموحد (v50) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)
    tasks = relationship("SiteTask", back_populates="site_obj", cascade="all, delete-orphan")

class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); hourly_rate = Column(Float); spec = Column(String(50))
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

engine = create_engine('sqlite:///egms_total_v50.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. محرك تقارير PDF المطور ---
def generate_pdf(site_obj, session):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(190, 10, f"EGMS Progress Report: {site_obj.name}", ln=True, align='C')
    pdf.set_font("Arial", size=10); pdf.cell(190, 10, f"Date: {datetime.now().date()}", ln=True, align='C'); pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(190, 10, "Project Tasks Status:", ln=True)
    for t in site_obj.tasks:
        done = sum(l.qty_done for l in t.logs); prog = (done/t.target_qty)*100 if t.target_qty > 0 else 0
        pdf.set_font("Arial", size=10); pdf.cell(190, 7, f"- {t.task_name}: {done}/{t.target_qty} {t.unit} ({prog:.1f}%)", ln=True)
    return pdf.output()

# --- 3. واجهة البرنامج ---
st.set_page_config(page_title="EGMS Total ERP v50", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.title("🏗️ EGMS Digital ERP v50")
    u = st.text_input("User"); p = st.text_input("Pass", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store")}
        if u in acc and p == acc[u][0]: st.session_state.update({"logged_in": True, "role": acc[u][1]}); st.rerun()
        else: st.error("Login Error")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.header(f"👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    all_sites = session.query(Site).all()
    
    if role == "Admin":
        st.title("💼 لوحة التحكم الشاملة - EGMS")
        tabs = st.tabs(["📍 الخريطة", "🏗️ متابعة الأشغال", "👷 العمال & الرواتب", "📦 المخزن", "📄 تقارير PDF", "⚙️ الإعدادات"])

        with tabs[0]: # الخريطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')
            else: st.info("لا توجد حضائر.")

        with tabs[1]: # متابعة الأشغال مع الصور
            tasks = session.query(SiteTask).all()
            for tk in tasks:
                done = sum(l.qty_done for l in tk.logs); prog = (done/tk.target_qty)*100 if tk.target_qty > 0 else 0
                with st.expander(f"📍 {tk.site_obj.name} - {tk.task_name} ({prog:.1f}%)"):
                    c1, c2 = st.columns([2, 1])
                    c1.write(f"المنجز: {done} / {tk.target_qty} {tk.unit}"); c1.progress(min(prog/100, 1.0))
                    last_log = session.query(TaskLog).filter(TaskLog.task_id == tk.id, TaskLog.image != None).order_by(TaskLog.timestamp.desc()).first()
                    if last_log: c2.image(last_log.image, caption="آخر توثيق", use_container_width=True)

        with tabs[2]: # العمال
            st.subheader("إدارة الموارد البشرية")
            with st.form("hr"):
                c1, c2 = st.columns(2); nm = c1.text_input("اسم العامل"); rt = c2.number_input("سعر الساعة")
                if st.form_submit_button("إضافة ملف عامل"):
                    session.add(WorkerProfile(name=nm, hourly_rate=rt)); session.commit(); st.rerun()
            df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_w.empty: st.dataframe(df_w, use_container_width=True)

        with tabs[3]: # المخزن
            st.subheader("رصيد المواد")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                df_st['net'] = df_st.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                st.table(df_st.groupby(['item', 'unit'])['net'].sum().reset_index())

        with tabs[4]: # التقارير
            st.subheader("توليد تقارير PDF الرسمية")
            if all_sites:
                sel_s = st.selectbox("اختر الحضيرة", all_sites, format_func=lambda x: x.name)
                if st.button("توليد التقرير"):
                    pdf_data = generate_pdf(sel_s, session)
                    st.download_button("تحميل PDF", pdf_data, f"{sel_s.name}_Report.pdf", "application/pdf")

        with tabs[5]: # الإعدادات
            st.subheader("إعداد الحضائر والمهام")
            with st.form("site"):
                n = st.text_input("اسم الحضيرة الجديد"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("حفظ الحضيرة"):
                    session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
            if all_sites:
                with st.form("task"):
                    sid = st.selectbox("اختر الحضيرة لتعريف مرحلة", [s.id for s in all_sites], format_func=lambda x: next(s.name for s in all_sites if s.id == x))
                    tn = st.text_input("المرحلة (مثال: حفر)"); tu = st.selectbox("الوحدة", ["m3", "m2", "Kg"]); tq = st.number_input("المستهدف")
                    if st.form_submit_button("إضافة المرحلة"):
                        session.add(SiteTask(site_id=sid, task_name=tn, unit=tu, target_qty=tq)); session.commit(); st.rerun()

    # واجهات الموظفين (Work, Labor, Store) تتبع نفس النمط السابق لضمان استقرار الإدخال...
    elif role == "Work":
        st.header("🏗️ تقرير الإنجاز الميداني")
        if all_sites:
            s_ch = st.selectbox("الحضيرة", all_sites, format_func=lambda x: x.name)
            site_tasks = session.query(SiteTask).filter_by(site_id=s_ch.id).all()
            if site_tasks:
                with st.form("w_log"):
                    tk = st.selectbox("المرحلة", site_tasks, format_func=lambda x: x.task_name)
                    qd = st.number_input(f"الكمية المنجزة ({tk.unit})"); im = st.file_uploader("📸 صورة", type=['jpg', 'png'])
                    if st.form_submit_button("إرسال"):
                        img_b = im.read() if im else None
                        session.add(TaskLog(task_id=tk.id, qty_done=qd, notes="", image=img_b)); session.commit(); st.success("تم!")
    
    session.close()
