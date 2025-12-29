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

# --- 1. بناء هيكل البيانات الموحد (v52) ---
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

# إعداد المحرك مع خاصية لضمان عدم انفصال البيانات (v52)
engine = create_engine('sqlite:///egms_final_v52.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
# استخدام expire_on_commit=False لحل مشكلة DetachedInstanceError
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. واجهة البرنامج ---
st.set_page_config(page_title="EGMS Enterprise v52", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.title("🏗️ EGMS Digital ERP v52")
    u = st.text_input("User"); p = st.text_input("Pass", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store")}
        if u in acc and p == acc[u][0]: st.session_state.update({"logged_in": True, "role": acc[u][1]}); st.rerun()
        else: st.error("Login Error")
else:
    role = st.session_state["role"]
    session = Session()
    st.sidebar.header(f"👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    all_sites = session.query(Site).all()
    
    if role == "Admin":
        st.title("💼 لوحة التحكم الشاملة")
        tabs = st.tabs(["📍 الخريطة", "🏗️ متابعة الأشغال", "👷 العمال والرواتب", "📦 المخزن", "⚙️ الإعدادات"])

        with tabs[2]: # العمال والرواتب
            with st.form("admin_hr"):
                nm = st.text_input("اسم العامل"); rt = st.number_input("سعر الساعة"); pl = st.text_area("الخطة")
                if st.form_submit_button("حفظ العامل"):
                    session.add(WorkerProfile(name=nm, hourly_rate=rt, work_plan=pl))
                    session.commit(); st.rerun()
            df_p = pd.read_sql(session.query(WorkerProfile).statement, session.bind)
            st.dataframe(df_p, use_container_width=True)

        with tabs[4]: # الإعدادات
            with st.form("admin_site"):
                sn = st.text_input("اسم الموقع"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.2)
                if st.form_submit_button("إضافة الموقع"):
                    session.add(Site(name=sn, lat=la, lon=lo)); session.commit(); st.rerun()
            if all_sites:
                with st.form("admin_task"):
                    sid = st.selectbox("الموقع", [s.id for s in all_sites], format_func=lambda x: next(s.name for s in all_sites if s.id == x))
                    tn = st.text_input("المهمة"); tu = st.selectbox("الوحدة", ["m3", "m2", "Kg"]); tq = st.number_input("الكمية")
                    if st.form_submit_button("إضافة المهمة"):
                        session.add(SiteTask(site_id=sid, task_name=tn, unit=tu, target_qty=tq)); session.commit(); st.success("تم")

    elif role == "Labor": # واجهة مسؤول العمال (تم حل مشكلة DetachedInstanceError ✅)
        st.header("👷 تسجيل ساعات العمال")
        profs = session.query(WorkerProfile).all()
        sites = [s.name for s in session.query(Site).all()]
        if profs and sites:
            with st.form("labor_form"):
                w_choice = st.selectbox("اختر العامل", profs, format_func=lambda x: x.name)
                st.info(f"📋 خطة العمل: {w_choice.work_plan}")
                hrs = st.number_input("الساعات", min_value=0.5, step=0.5)
                si = st.selectbox("الموقع", sites)
                if st.form_submit_button("تأكيد التسجيل"):
                    session.add(WorkerLog(worker_id=w_choice.id, hours=hrs, site=si))
                    session.commit(); st.success("✅ تم")
        else: st.warning("يجب إضافة عمال ومواقع أولاً")

    elif role == "Magaza": # واجهة مسؤول المخزن (تم حل مشكلة زر الحفظ المفقود ✅)
        st.header("📦 إدارة المغازة والمواد")
        sites = [s.name for s in session.query(Site).all()]
        if sites:
            with st.form("store_form"):
                item = st.text_input("اسم المادة")
                unit = st.selectbox("الوحدة", ["كيس", "طن", "كغ", "متر"])
                qty = st.number_input("الكمية", min_value=0.1)
                t_type = st.radio("نوع العملية", ["Entry", "Exit"])
                si = st.selectbox("الموقع", sites)
                if st.form_submit_button("حفظ بيانات المخزن"):
                    session.add(StoreLog(item=item, unit=unit, qty=qty, trans_type=t_type, site=si))
                    session.commit(); st.success("✅ تم تسجيل المادة بنجاح")
        else: st.warning("يجب إضافة مواقع أولاً")

    elif role == "Work": # واجهة مسؤول الأشغال
        st.header("🏗️ تقرير الإنجاز")
        if all_sites:
            s_ch = st.selectbox("الموقع", all_sites, format_func=lambda x: x.name)
            tasks = session.query(SiteTask).filter_by(site_id=s_ch.id).all()
            if tasks:
                with st.form("work_form"):
                    tk = st.selectbox("المهمة", tasks, format_func=lambda x: x.task_name)
                    qd = st.number_input("الكمية المنجزة")
                    im = st.file_uploader("📸 صورة", type=['jpg', 'png'])
                    if st.form_submit_button("إرسال التقرير"):
                        img_b = im.read() if im else None
                        session.add(TaskLog(task_id=tk.id, qty_done=qd, notes="", image=img_b))
                        session.commit(); st.success("تم!")

    # إغلاق الجلسة عند نهاية الطلب
    Session.remove()
