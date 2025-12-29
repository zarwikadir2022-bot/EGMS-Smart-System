import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import io
from PIL import Image

# --- 1. بناء هيكل البيانات الموحد (v54) ---
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

# إعداد المحرك (v54 - Gold)
engine = create_engine('sqlite:///egms_gold_v54.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. محرك التقارير PDF (إصلاح توافق الصور) ---
def generate_pdf_v54(site_obj, session):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, f"EGMS Project Report: {site_obj.name}", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, "Task Progression:", ln=True)
    for t in site_obj.tasks:
        done = sum(l.qty_done for l in t.logs)
        prog = (done/t.target_qty)*100 if t.target_qty > 0 else 0
        pdf.set_font("Arial", size=10)
        pdf.cell(190, 7, f"- {t.task_name}: {done}/{t.target_qty} {t.unit} ({prog:.1f}%)", ln=True)
    return pdf.output()

# --- 3. واجهة البرنامج الرسومية ---
st.set_page_config(page_title="EGMS Gold ERP v54", layout="wide")

# CSS لإضفاء طابع رسمي
st.markdown("""
    <style>
    .stApp { background-color: #f9fbff; }
    .main-header { text-align: center; color: #004a99; border-bottom: 3px solid #004a99; padding-bottom: 10px; margin-bottom: 20px; }
    div.stMetric { background-color: white; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 class='main-header'>🏗️ EGMS Digital ERP</h1>", unsafe_allow_html=True)
    u_in = st.text_input("Username")
    p_in = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store")}
        if u_in in acc and p_in == acc[u_in][0]:
            st.session_state.update({"logged_in": True, "role": acc[u_in][1]})
            st.rerun()
        else: st.error("Access Denied")
else:
    role = st.session_state["role"]
    session = Session()
    st.sidebar.success(f"Connected as: {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    all_sites = session.query(Site).all()
    
    # --- 4. واجهة المدير (Admin Control Center) ---
    if role == "Admin":
        st.markdown("<h2 class='main-header'>💼 Central Command Center</h2>", unsafe_allow_html=True)
        tabs = st.tabs(["📍 الخريطة", "🏗️ متابعة الإنجاز الموثق", "👷 العمال والرواتب", "📦 المخزن", "📄 التقارير PDF", "⚙️ الإعدادات"])
        
        with tabs[0]: # الخريطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')
            else: st.info("No sites added yet.")

        with tabs[1]: # متابعة الإنجاز بالصور (تم الربط الكامل ✅)
            if all_sites:
                for site in all_sites:
                    with st.expander(f"حضيرة: {site.name}"):
                        for tk in site.tasks:
                            done = sum(l.qty_done for l in tk.logs)
                            p = (done/tk.target_qty)*100 if tk.target_qty > 0 else 0
                            c1, c2 = st.columns([2, 1])
                            c1.write(f"**{tk.task_name}**: {done}/{tk.target_qty} {tk.unit}")
                            c1.progress(min(p/100, 1.0))
                            last_img = session.query(TaskLog).filter(TaskLog.task_id == tk.id, TaskLog.image != None).order_by(TaskLog.timestamp.desc()).first()
                            if last_img: c2.image(last_img.image, use_container_width=True)
            else: st.info("Waiting for field data...")

        with tabs[2]: # العمال والرواتب
            st.subheader("إدارة ملفات العمال")
            with st.form("admin_hr_v54"):
                c1, c2 = st.columns(2)
                nm = c1.text_input("اسم العامل"); rt = c2.number_input("سعر الساعة (TND)")
                pl = st.text_area("خطة العمل")
                if st.form_submit_button("إضافة/تعديل العامل"):
                    session.add(WorkerProfile(name=nm, hourly_rate=rt, work_plan=pl))
                    session.commit(); st.rerun()
            df_wlogs = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_wlogs.empty: st.dataframe(df_wlogs, use_container_width=True)

        with tabs[3]: # المخزن
            st.subheader("رصيد المواد الحالي")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                df_st['net'] = df_st.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                st.table(df_st.groupby(['item', 'unit'])['net'].sum().reset_index().rename(columns={'net':'الكمية الحالية'}))

        with tabs[4]: # PDF
            if all_sites:
                s_report = st.selectbox("Select Project for PDF", all_sites, format_func=lambda x: x.name)
                if st.button("Generate Official PDF"):
                    pdf_bytes = generate_pdf_v54(s_report, session)
                    st.download_button("Download Report", pdf_bytes, f"{s_report.name}.pdf", "application/pdf")

        with tabs[5]: # الإعدادات
            st.subheader("تعريف الحضائر والمراحل")
            with st.form("site_v54"):
                n = st.text_input("اسم الموقع الجديد"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.2)
                if st.form_submit_button("حفظ الموقع"):
                    session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
            if all_sites:
                with st.form("task_v54"):
                    sid = st.selectbox("Site", [s.id for s in all_sites], format_func=lambda x: next(s.name for s in all_sites if s.id == x))
                    tn = st.text_input("المرحلة"); tu = st.selectbox("الوحدة", ["m3", "m2", "Kg", "Sac"]); tq = st.number_input("الكمية")
                    if st.form_submit_button("إضافة المرحلة"):
                        session.add(SiteTask(site_id=sid, task_name=tn, unit=tu, target_qty=tq)); session.commit(); st.success("Task Added")

    # --- 5. واجهات المسؤولين (Store, Labor, Work) ---
    elif role == "Store": # واجهة المخزن (تم التأكد من زر الحفظ ✅)
        st.header("📦 إدارة المغازة")
        if all_sites:
            with st.form("store_f54"):
                i = st.text_input("المادة"); u = st.selectbox("الوحدة", ["كيس", "طن", "كغ", "متر"]); q = st.number_input("الكمية")
                t = st.radio("العملية", ["Entry", "Exit"]); s = st.selectbox("الموقع", [s.name for s in all_sites])
                if st.form_submit_button("حفظ العملية"):
                    session.add(StoreLog(item=i, unit=u, qty=q, trans_type=t, site=s))
                    session.commit(); st.success("Saved!")
        else: st.warning("No sites available.")

    elif role == "Labor": # واجهة العمال (تم التأكد من خطة العمل ✅)
        st.header("👷 تسجيل الساعات")
        profs = session.query(WorkerProfile).all()
        if profs and all_sites:
            with st.form("labor_f54"):
                w = st.selectbox("العامل", profs, format_func=lambda x: x.name)
                st.info(f"📋 الخطة: {w.work_plan}")
                h = st.number_input("عدد الساعات", min_value=0.5, step=0.5)
                s = st.selectbox("الموقع", [s.name for s in all_sites])
                if st.form_submit_button("تأكيد الحضور"):
                    session.add(WorkerLog(worker_id=w.id, hours=h, site=s))
                    session.commit(); st.success("Logged!")

    elif role == "Work": # واجهة الأشغال (تم التأكد من رفع الصور ✅)
        st.header("🏗️ تقرير الإنجاز")
        if all_sites:
            s_ch = st.selectbox("الحضيرة", all_sites, format_func=lambda x: x.name)
            tasks = session.query(SiteTask).filter_by(site_id=s_ch.id).all()
            if tasks:
                with st.form("work_f54"):
                    tk = st.selectbox("المرحلة", tasks, format_func=lambda x: x.task_name)
                    qd = st.number_input("الكمية المنجزة")
                    im = st.file_uploader("📸 صورة التوثيق", type=['jpg', 'png'])
                    if st.form_submit_button("إرسال"):
                        img_b = im.read() if im else None
                        session.add(TaskLog(task_id=tk.id, qty_done=qd, notes="", image=img_b))
                        session.commit(); st.success("Submitted!")

    Session.remove()
