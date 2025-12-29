import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import io

# --- 1. بناء هيكل البيانات الموحد والاحترافي ---
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

# إعداد قاعدة البيانات v62
engine = create_engine('sqlite:///egms_v62_final.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. محرك تقارير PDF المحمي ---
def generate_pdf_v62(site_obj, session):
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

# --- 3. واجهة البرنامج الرئيسية ---
st.set_page_config(page_title="EGMS Enterprise ERP v62", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;'>🏗️ EGMS Digital ERP</h1>", unsafe_allow_html=True)
    u_in = st.text_input("Username")
    p_in = st.text_input("Password", type="password")
    if st.button("LOGIN"):
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
    
    # --- 4. واجهة المدير (Admin Hub) ---
    if role == "Admin":
        st.title("💼 Command & Analytics Hub")
        tabs = st.tabs(["📊 التحليلات", "📍 الخريطة", "🏗️ الإنجاز", "👷 العمال", "📦 المخزن", "⚙️ الإعدادات"])

        with tabs[0]: # التحليلات (Analytics)
            st.subheader("📊 تحليل بيانات المشاريع")
            df_labor = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            df_profs = pd.read_sql(session.query(WorkerProfile).statement, session.bind)
            if not df_labor.empty and not df_profs.empty:
                df_hr = pd.merge(df_labor, df_profs, left_on='worker_id', right_on='id')
                df_hr['Cost'] = df_hr['hours'] * df_hr['hourly_rate']
                st.plotly_chart(px.pie(df_hr, values='Cost', names='site', title="ميزانية الرواتب"), use_container_width=True)

        with tabs[1]: # الخريطة (Map)
            st.subheader("📍 التواجد الجغرافي للمشاريع")
            df_map = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_map.empty: st.map(df_map, latitude='lat', longitude='lon')

        with tabs[2]: # الإنجاز والصور (Progress)
            st.subheader("🏗️ تقارير الميدان الموثقة")
            for site in all_sites:
                with st.expander(f"موقع: {site.name}"):
                    for tk in site.tasks:
                        done = sum(l.qty_done for l in tk.logs); p = (done/tk.target_qty)*100 if tk.target_qty > 0 else 0
                        c1, c2 = st.columns([2, 1])
                        c1.write(f"**{tk.task_name}**: {done}/{tk.target_qty} {tk.unit}")
                        c1.progress(min(p/100, 1.0))
                        last_log = session.query(TaskLog).filter(TaskLog.task_id == tk.id, TaskLog.image != None).order_by(TaskLog.timestamp.desc()).first()
                        if last_log: c2.image(last_log.image, use_container_width=True)

        with tabs[3]: # العمال (Workers)
            st.subheader("👷 الموارد البشرية")
            with st.form("admin_hr"):
                n = st.text_input("الاسم الكامل"); r = st.number_input("سعر الساعة"); pl = st.text_area("خطة العمل")
                if st.form_submit_button("حفظ الملف"):
                    session.add(WorkerProfile(name=n, hourly_rate=r, work_plan=pl)); session.commit(); st.rerun()
            st.dataframe(pd.read_sql(session.query(WorkerProfile).statement, session.bind), use_container_width=True)

        with tabs[4]: # المخزن (Inventory)
            st.subheader("📦 رصيد المخزن الفعلي")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                df_st['net'] = df_st.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                balance = df_st.groupby(['item', 'unit', 'site'])['net'].sum().reset_index()
                st.table(balance.rename(columns={'net': 'الرصيد المتاح'}))

        with tabs[5]: # الإعدادات والتقارير (Setup)
            if all_sites:
                s_rep = st.selectbox("تقرير PDF للحضيرة", all_sites, format_func=lambda x: x.name)
                if st.button("Generate PDF Report"):
                    pdf_bytes = generate_pdf_v62(s_rep, session)
                    st.download_button("Download Report", pdf_bytes, f"{s_rep.name}.pdf", "application/pdf")
            st.divider()
            with st.form("site_f"):
                sn = st.text_input("Site Name"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("إضافة حضيرة"):
                    session.add(Site(name=sn, lat=la, lon=lo)); session.commit(); st.rerun()
            if all_sites:
                with st.form("task_f"):
                    sid = st.selectbox("الحضيرة", [s.id for s in all_sites], format_func=lambda x: next(s.name for s in all_sites if s.id == x))
                    tn = st.text_input("اسم المرحلة"); tu = st.selectbox("الوحدة", ["m3", "m2", "Kg"]); tq = st.number_input("الكمية")
                    if st.form_submit_button("إضافة مهمة"):
                        session.add(SiteTask(site_id=sid, task_name=tn, unit=tu, target_qty=tq)); session.commit(); st.rerun()

    # --- 5. واجهة مسؤول المغازة (Store) ---
    elif role == "Store":
        st.header("📦 إدارة المغازة والمواد")
        if all_sites:
            with st.form("store_v62"):
                it = st.text_input("المادة"); un = st.selectbox("الوحدة", ["كيس", "طن", "كغ"])
                qt = st.number_input("الكمية"); tp = st.radio("العملية", ["Entry", "Exit"]); si = st.selectbox("الموقع", [s.name for s in all_sites])
                if st.form_submit_button("حفظ في المخزن"):
                    session.add(StoreLog(item=it, unit=un, qty=qt, trans_type=tp, site=si)); session.commit(); st.success("تم الحفظ!")

    # --- 6. واجهة مسؤول العمال (Labor) ---
    elif role == "Labor":
        st.header("👷 سجل ساعات العمال")
        profs = session.query(WorkerProfile).all()
        if profs and all_sites:
            with st.form("labor_v62"):
                w = st.selectbox("العامل", profs, format_func=lambda x: x.name)
                st.info(f"📋 الخطة: {w.work_plan}")
                h = st.number_input("الساعات", min_value=0.5); s = st.selectbox("الموقع", [s.name for s in all_sites])
                if st.form_submit_button("تسجيل الحضور"):
                    session.add(WorkerLog(worker_id=w.id, hours=h, site=s)); session.commit(); st.success("تم!")

    # --- 7. واجهة مسؤول الأشغال (Work) ---
    elif role == "Work":
        st.header("🏗️ تقرير الإنجاز الميداني")
        if all_sites:
            s_ch = st.selectbox("الحضيرة", all_sites, format_func=lambda x: x.name)
            tasks = session.query(SiteTask).filter_by(site_id=s_ch.id).all()
            if tasks:
                with st.form("work_v62"):
                    tk = st.selectbox("المرحلة", tasks, format_func=lambda x: x.task_name)
                    qd = st.number_input("الكمية المنجزة اليوم")
                    im = st.file_uploader("📸 صورة التوثيق", type=['jpg', 'png'])
                    if st.form_submit_button("إرسال التقرير"):
                        img_b = im.read() if im else None
                        session.add(TaskLog(task_id=tk.id, qty_done=qd, notes="", image=img_b)); session.commit(); st.success("تم الإرسال!")

    Session.remove()
