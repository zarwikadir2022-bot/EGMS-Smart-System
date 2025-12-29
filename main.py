import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import plotly.express as px
from PIL import Image
import io

# --- 1. إعداد قاعدة البيانات الشاملة (v47) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)
    tasks = relationship("SiteTask", back_populates="site_obj", cascade="all, delete-orphan")

class SiteTask(Base):
    __tablename__ = 'site_tasks'
    id = Column(Integer, primary_key=True); site_id = Column(Integer, ForeignKey('sites.id'))
    task_name = Column(String(100)); unit = Column(String(50)); target_qty = Column(Float)
    site_obj = relationship("Site", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task_obj", cascade="all, delete-orphan")

class TaskLog(Base):
    __tablename__ = 'task_logs'
    id = Column(Integer, primary_key=True); task_id = Column(Integer, ForeignKey('site_tasks.id'))
    qty_done = Column(Float); notes = Column(Text); image = Column(LargeBinary) # حقل الصورة الجديد
    timestamp = Column(DateTime, default=datetime.utcnow)
    task_obj = relationship("SiteTask", back_populates="logs")

# الجداول الأخرى (HR والمخزن)
class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'; id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); hourly_rate = Column(Float); work_plan = Column(Text)
class WorkerLog(Base):
    __tablename__ = 'worker_logs'; id = Column(Integer, primary_key=True); worker_id = Column(Integer, ForeignKey('worker_profiles.id')); hours = Column(Float); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)
class StoreLog(Base):
    __tablename__ = 'store_logs'; id = Column(Integer, primary_key=True); item = Column(String(100)); unit = Column(String(50)); qty = Column(Float); trans_type = Column(String(20)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_visual_v47.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. التنسيق والواجهة ---
st.set_page_config(page_title="EGMS Visual ERP v47", layout="wide")
st.markdown("""<style> .main-header { text-align: center; padding: 20px; background: white; border-radius: 15px; border-bottom: 5px solid #004a99; box-shadow: 0 2px 4px rgba(0,0,0,0.1); } .stImage > img { border-radius: 10px; transition: 0.3s; } .stImage > img:hover { transform: scale(1.02); } </style>""", unsafe_allow_html=True)

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.markdown("<div class='main-header'><h1>🏗️ EGMS DIGITAL ERP</h1><p>التوثيق البصري وإدارة الكميات v47</p></div>", unsafe_allow_html=True)
    u = st.text_input("Username"); p = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store")}
        if u in acc and p == acc[u][0]: st.session_state.update({"logged_in": True, "role": acc[u][1]}); st.rerun()
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.markdown(f"### 👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    # --- 4. واجهة المدير (المراقبة البصرية) ---
    if role == "Admin":
        st.markdown("<div class='main-header'><h2>📊 مركز المراقبة والتحليل البصري</h2></div>", unsafe_allow_html=True)
        t = st.tabs(["🏗️ متابعة الإنجاز بالصور", "👷 العمال", "📦 المخزن", "⚙️ الإعدادات & المهام"])

        with t[0]: # متابعة الإنجاز مع الصور
            tasks = session.query(SiteTask).all()
            if tasks:
                for task in tasks:
                    total_done = sum(log.qty_done for log in task.logs)
                    prog = (total_done / task.target_qty) * 100
                    with st.expander(f"📍 {task.site_obj.name} | {task.task_name} ({prog:.1f}%)"):
                        col_txt, col_img = st.columns([2, 1])
                        with col_txt:
                            st.write(f"**المطلوب:** {task.target_qty} {task.unit}")
                            st.write(f"**المنجز:** {total_done} {task.unit}")
                            st.progress(min(prog/100, 1.0))
                            # عرض الملاحظات الأخيرة
                            for log in task.logs[-3:]: # آخر 3 ملاحظات
                                st.caption(f"📅 {log.timestamp.strftime('%Y-%m-%d')} | 📝 {log.notes}")
                        with col_img:
                            # عرض آخر صورة تم رفعها لهذه المرحلة
                            last_log_with_img = session.query(TaskLog).filter(TaskLog.task_id == task.id, TaskLog.image != None).order_by(TaskLog.timestamp.desc()).first()
                            if last_log_with_img:
                                st.image(last_log_with_img.image, caption="أحدث صورة من الموقع", use_container_width=True)
                            else: st.info("لا توجد صور")
            else: st.info("لا توجد مهام معرفة.")

        with t[3]: # الإعدادات والمهام
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("إضافة حضيرة")
                n = st.text_input("اسم الحضيرة"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.button("حفظ الحضيرة"):
                    try: session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
                    except: st.error("موجودة!")
            with col2:
                st.subheader("تعريف مرحلة عمل")
                sites = session.query(Site).all()
                if sites:
                    with st.form("task_f"):
                        s_id = st.selectbox("الحضيرة", [s.id for s in sites], format_func=lambda x: next(s.name for s in sites if s.id == x))
                        tn = st.text_input("اسم المرحلة"); tu = st.selectbox("الوحدة", ["m3", "m2", "Tonne", "Sac"]); tq = st.number_input("الكمية")
                        if st.form_submit_button("حفظ المرحلة"):
                            session.add(SiteTask(site_id=s_id, task_name=tn, unit=tu, target_qty=tq)); session.commit(); st.rerun()

    # --- 5. واجهة مسؤول الأشغال (رفع الصور) ---
    elif role == "Work":
        st.header("🏗️ تقرير الإنجاز اليومي + صورة")
        sites = session.query(Site).all()
        if sites:
            s_choice = st.selectbox("اختر الحضيرة", sites, format_func=lambda x: x.name)
            tasks = session.query(SiteTask).filter_by(site_id=s_choice.id).all()
            if tasks:
                with st.form("work_report"):
                    task_choice = st.selectbox("المرحلة", tasks, format_func=lambda x: x.task_name)
                    qty = st.number_input(f"الكمية المنجزة اليوم ({task_choice.unit})", min_value=0.1)
                    note = st.text_area("وصف العمل المنجز")
                    uploaded_file = st.file_uploader("📸 التقط صورة أو ارفع صورة للعمل المنجز", type=['jpg', 'png', 'jpeg'])
                    
                    if st.form_submit_button("إرسال التقرير الموثق"):
                        img_bytes = None
                        if uploaded_file:
                            img_bytes = uploaded_file.getvalue()
                        session.add(TaskLog(task_id=task_choice.id, qty_done=qty, notes=note, image=img_bytes))
                        session.commit(); st.success("✅ تم إرسال التقرير بنجاح مع الصورة!")
            else: st.warning("لا توجد مهام لهذه الحضيرة.")

    session.close()
