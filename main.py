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

# --- 1. بناء هيكل البيانات الموحد (v51) ---
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

engine = create_engine('sqlite:///egms_final_v51.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. محرك تقارير PDF ---
def generate_pdf(site_obj, session):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(190, 10, f"EGMS Progress Report: {site_obj.name}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12); pdf.cell(190, 10, "Task Completion:", ln=True)
    for t in site_obj.tasks:
        done = sum(l.qty_done for l in t.logs); prog = (done/t.target_qty)*100 if t.target_qty > 0 else 0
        pdf.set_font("Arial", size=10); pdf.cell(190, 7, f"- {t.task_name}: {done}/{t.target_qty} {t.unit} ({prog:.1f}%)", ln=True)
    return pdf.output()

# --- 3. واجهة البرنامج ---
st.set_page_config(page_title="EGMS Full ERP v51", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.title("🏗️ EGMS Digital ERP v51")
    u = st.text_input("Username"); p = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store")}
        if u in acc and p == acc[u][0]: st.session_state.update({"logged_in": True, "role": acc[u][1]}); st.rerun()
        else: st.error("Login Error")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.header(f"👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    all_sites = session.query(Site).all()
    
    # --- 4. واجهة المدير (Admin) ---
    if role == "Admin":
        st.title("💼 لوحة التحكم الشاملة")
        tabs = st.tabs(["📍 الخريطة", "🏗️ متابعة الأشغال", "👷 العمال والرواتب", "📦 المخزن", "📄 تقارير PDF", "⚙️ الإعدادات"])

        with tabs[2]: # العمال والرواتب (تم التأكد من الكود هنا ✅)
            st.subheader("👷 إدارة الموارد البشرية والرواتب")
            with st.form("hr_admin_form"):
                col1, col2 = st.columns(2)
                nm = col1.text_input("اسم العامل الجديد")
                rt = col2.number_input("سعر الساعة (د.ت)", min_value=0.0)
                pl = st.text_area("خطة العمل / المهام المسندة")
                if st.form_submit_button("حفظ ملف العامل"):
                    session.add(WorkerProfile(name=nm, hourly_rate=rt, work_plan=pl))
                    session.commit(); st.success("✅ تم حفظ العامل"); st.rerun()

            st.write("---")
            df_profs = pd.read_sql(session.query(WorkerProfile).statement, session.bind)
            df_logs = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            
            if not df_logs.empty and not df_profs.empty:
                df_merged = pd.merge(df_logs, df_profs, left_on='worker_id', right_on='id')
                df_merged['Total (TND)'] = df_merged['hours'] * df_merged['hourly_rate']
                st.write("سجل الرواتب والحضور:")
                st.dataframe(df_merged[['name', 'hours', 'hourly_rate', 'Total (TND)', 'site', 'timestamp']], use_container_width=True)
                st.metric("إجمالي المصاريف البشرية", f"{df_merged['Total (TND)'].sum():,.2f} TND")
            else: st.info("لا توجد سجلات رواتب حتى الآن.")

        with tabs[5]: # الإعدادات
            st.subheader("إضافة مواقع ومهام")
            with st.form("site_f"):
                sn = st.text_input("اسم الموقع"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.2)
                if st.form_submit_button("حفظ الموقع"):
                    session.add(Site(name=sn, lat=la, lon=lo)); session.commit(); st.rerun()
            if all_sites:
                with st.form("task_f"):
                    sid = st.selectbox("الموقع", [s.id for s in all_sites], format_func=lambda x: next(s.name for s in all_sites if s.id == x))
                    tn = st.text_input("اسم المهمة"); tu = st.selectbox("الوحدة", ["m3", "m2", "Kg"]); tq = st.number_input("الكمية")
                    if st.form_submit_button("إضافة المهمة"):
                        session.add(SiteTask(site_id=sid, task_name=tn, unit=tu, target_qty=tq)); session.commit(); st.success("تم")

    # --- 5. واجهة مسؤول العمال (Labor Account) - تم الإصلاح هنا ✅ ---
    elif role == "Labor":
        st.header("👷 تسجيل ساعات العمل اليومية")
        profs = session.query(WorkerProfile).all()
        sites = [s.name for s in session.query(Site).all()]
        
        if not profs:
            st.warning("⚠️ لا يوجد عمال مسجلين في النظام. اطلب من المدير إضافتهم.")
        elif not sites:
            st.warning("⚠️ لا توجد مواقع مضافة حالياً.")
        else:
            with st.form("labor_entry_form"):
                w_choice = st.selectbox("اختر العامل", profs, format_func=lambda x: x.name)
                # عرض خطة العمل تلقائياً
                st.info(f"📋 خطة عمل {w_choice.name}: {w_choice.work_plan}")
                
                hrs = st.number_input("عدد الساعات المنجزة اليوم", min_value=0.5, step=0.5)
                si = st.selectbox("موقع العمل", sites)
                
                if st.form_submit_button("تأكيد تسجيل الساعات"):
                    session.add(WorkerLog(worker_id=w_choice.id, hours=hrs, site=si))
                    session.commit()
                    st.success(f"✅ تم تسجيل {hrs} ساعة بنجاح للعامل {w_choice.name}")

    # واجهة الأشغال والمغازة...
    elif role == "Work":
        st.header("🏗️ تقرير الإنجاز")
        if all_sites:
            s_ch = st.selectbox("الموقع", all_sites, format_func=lambda x: x.name)
            tasks = session.query(SiteTask).filter_by(site_id=s_ch.id).all()
            with st.form("w_log"):
                tk = st.selectbox("المهمة", tasks, format_func=lambda x: x.task_name)
                qd = st.number_input("الكمية المنجزة اليوم")
                im = st.file_uploader("📸 صورة التوثيق", type=['jpg', 'png'])
                if st.form_submit_button("إرسال"):
                    img_b = im.read() if im else None
                    session.add(TaskLog(task_id=tk.id, qty_done=qd, notes="", image=img_b)); session.commit(); st.success("تم!")

    session.close()
