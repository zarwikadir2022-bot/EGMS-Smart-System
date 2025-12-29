import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import plotly.express as px
from sqlalchemy.exc import IntegrityError

# --- 1. إعداد قاعدة البيانات الشاملة (v32) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True); site = Column(String(100)); progress = Column(Float); notes = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow); lat = Column(Float); lon = Column(Float)

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True); worker_name = Column(String(100)); hours = Column(Float); hourly_rate = Column(Float); specialization = Column(String(100)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True)
    item = Column(String(100))
    unit = Column(String(50)) # حقل وحدة القيس الجديد
    qty = Column(Float)
    trans_type = Column(String(20))
    site = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True); incident = Column(String(100)); notes = Column(Text); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class LabLog(Base):
    __tablename__ = 'lab_logs'
    id = Column(Integer, primary_key=True); test_name = Column(String(100)); result = Column(String(100)); status = Column(String(50)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

# إنشاء محرك قاعدة البيانات (نسخة جديدة v32 لضمان تحديث الجداول)
engine = create_engine('sqlite:///egms_final_v32.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. الإعدادات ---
st.set_page_config(page_title="EGMS Enterprise v32", layout="wide")
sel_lang = st.sidebar.selectbox("🌐 Language", ["العربية", "Français"])

def get_sites():
    session = Session(); s = session.query(Site).all(); session.close()
    return {x.name: (x.lat, x.lon) for x in s}

# --- 3. نظام الدخول المتعدد ---
if "logged_in" not in st.session_state:
    st.title("🏗️ EGMS Digital ERP v32")
    u = st.text_input("المستخدم (User)"); p = st.text_input("الرمز (Pass)", type="password")
    if st.button("🚀 دخول"):
        access = {
            "admin": ("egms2025", "Admin"),
            "magaza": ("store2025", "Store"),
            "labor": ("labor2025", "Labor"),
            "work": ("work2025", "Work"),
            "safety": ("safe2025", "Safety"),
            "labo": ("lab2025", "Lab")
        }
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role_id": access[u][1]}); st.rerun()
        else: st.error("خطأ في البيانات!")
else:
    role_id = st.session_state.get("role_id")
    st.sidebar.success(f"المستخدم: {role_id}")
    if st.sidebar.button("خروج"): st.session_state.clear(); st.rerun()
    
    session = Session()
    all_sites = {x.name: (x.lat, x.lon) for x in session.query(Site).all()}

    # --- 4. واجهة المدير (Admin) ---
    if role_id == "Admin":
        tabs = st.tabs(["📍 الخريطة", "📦 المخزن", "👷 العمال", "🏗️ الأشغال", "🛡️ السلامة & المختبر", "⚙️ الإعدادات"])
        
        with tabs[0]: # الخريطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')
        
        with tabs[1]: # المخزن (مع وحدة القيس)
            st.subheader("📦 سجل المخزن وتوافر المواد")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty: st.dataframe(df_st, use_container_width=True)
            else: st.info("لا توجد بيانات مخزن")

        with tabs[2]: # العمال
            st.subheader("👷 ميزانية الموارد البشرية")
            df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_w.empty: st.dataframe(df_w, use_container_width=True)

        with tabs[6 if len(tabs)>6 else 5]: # الإعدادات
            with st.form("add_site"):
                n = st.text_input("اسم الموقع الجديد"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("إضافة"):
                    try: session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
                    except IntegrityError: session.rollback(); st.error("الموقع موجود مسبقاً")

    # --- 5. واجهة مسؤول المغازة (Store) ---
    elif role_id == "Store":
        st.header("📦 إدارة المخزن (المغازة)")
        if not all_sites: st.warning("يجب إضافة مواقع من حساب المدير أولاً")
        else:
            with st.form("store_form"):
                item = st.text_input("اسم المادة (Désignation)")
                unit = st.selectbox("وحدة القيس (Unité)", ["كغ (Kg)", "طن (Tonne)", "لتر (Litre)", "متر (Mètre)", "كيس (Sac)", "قطعة (Pièce)"])
                qty = st.number_input("الكمية (Quantité)", min_value=0.1)
                t_type = st.radio("نوع العملية", ["Entry (دخول)", "Exit (خروج)"])
                s_choice = st.selectbox("الموقع", list(all_sites.keys()))
                if st.form_submit_button("حفظ السجل"):
                    session.add(StoreLog(item=item, unit=unit, qty=qty, trans_type=t_type, site=s_choice))
                    session.commit(); st.success("✅ تم تسجيل المادة بنجاح")

    # --- 6. واجهة مسؤول العمال (Labor) ---
    elif role_id == "Labor":
        st.header("👷 إدارة شؤون العمال")
        if not all_sites: st.warning("يجب إضافة مواقع أولاً")
        else:
            with st.form("labor_form"):
                name = st.text_input("اسم العامل")
                spec = st.selectbox("التخصص", ["بناء", "مساعد", "كهربائي", "حداد", "سائق"])
                h = st.number_input("عدد الساعات", min_value=1.0)
                r = st.number_input("كلفة الساعة (د.ت)")
                s_choice = st.selectbox("الموقع", list(all_sites.keys()))
                if st.form_submit_button("حفظ"):
                    session.add(WorkerLog(worker_name=name, hours=h, hourly_rate=r, specialization=spec, site=s_choice))
                    session.commit(); st.success("✅ تم تسجيل بيانات العامل")

    # --- 7. واجهة مسؤول الأشغال (Work) ---
    elif role_id == "Work":
        st.header("🏗️ تقارير الإنجاز الميداني")
        with st.form("work_f"):
            s_choice = st.selectbox("الموقع", list(all_sites.keys()))
            prog = st.slider("نسبة الإنجاز %", 0, 100)
            note = st.text_area("ملاحظات")
            if st.form_submit_button("إرسال التقرير"):
                session.add(WorkLog(site=s_choice, progress=prog, notes=note, lat=all_sites[s_choice][0], lon=all_sites[s_choice][1]))
                session.commit(); st.success("✅")

    session.close()
