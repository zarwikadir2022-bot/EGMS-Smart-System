import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px

# --- 1. إعداد قاعدة البيانات (نسخة جديدة v18 لتفادي الخطأ) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True)
    site = Column(String(100)); progress = Column(Float); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow); lat = Column(Float); lon = Column(Float)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True)
    item = Column(String(100)); qty = Column(Float); trans_type = Column(String(20))
    timestamp = Column(DateTime, default=datetime.utcnow)

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True)
    worker_name = Column(String(100)); hours = Column(Float); hourly_rate = Column(Float)
    specialization = Column(String(100)); site = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True)
    incident = Column(String(100)); notes = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow)

class LabLog(Base):
    __tablename__ = 'lab_logs'
    id = Column(Integer, primary_key=True)
    test_name = Column(String(100)); result = Column(String(100)); status = Column(String(50))
    site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

# تغيير اسم الملف هنا يحل مشكلة OperationalError
engine = create_engine('sqlite:///egms_final_v18.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي ---
LANG = {
    "العربية": {
        "title": "نظام EGMS المتكامل", "login": "دخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "role_safe": "مسؤول السلامة", "role_lab": "مسؤول المختبر",
        "role_worker": "مسؤول العمال", "role_store": "مسؤول المغازة", "role_work": "الأشغال",
        "save": "حفظ", "dash": "لوحة التحكم", "map": "الخريطة", "stock": "المخزن", "lab": "المختبر", "safe": "السلامة"
    },
    "Français": {
        "title": "Système Global EGMS", "login": "Connexion", "user": "ID", "pwd": "Pass",
        "role_dir": "Directeur", "role_safe": "Sécurité", "role_lab": "Labo",
        "role_worker": "RH", "role_store": "Stock", "role_work": "Travaux",
        "save": "Enregistrer", "dash": "Dashboard", "map": "Carte", "stock": "Stock", "lab": "Labo", "safe": "Sécurité"
    }
}

st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐", ["Français", "العربية"])
T = LANG[sel_lang]

def get_sites():
    session = Session(); s = session.query(Site).all(); session.close()
    return {x.name: (x.lat, x.lon) for x in s}

# --- 3. نظام الدخول المتعدد ---
if "logged_in" not in st.session_state:
    st.title(T["login"])
    u = st.text_input(T["user"]); p = st.text_input(T["pwd"], type="password")
    if st.button("🚀"):
        # تعريف كافة الأدوار وكلمات المرور
        access = {
            "admin": ("egms2025", T["role_dir"]),
            "safety": ("safe2025", T["role_safe"]),
            "labo": ("lab2025", T["role_lab"]),
            "labor": ("labor2025", T["role_worker"]),
            "magaza": ("store2025", T["role_store"]),
            "work": ("work2025", T["role_work"])
        }
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role": access[u][1]})
            st.rerun()
        else: st.error("خطأ في البيانات")
else:
    role = st.session_state.get("role")
    st.sidebar.write(f"👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    
    all_sites = get_sites()

    # --- 4. واجهة المدير (رؤية شاملة) ---
    if role == T["role_dir"]:
        st.title(T["dash"])
        tabs = st.tabs([T["map"], T["stock"], "العمال والرواتب", T["safe"], T["lab"], "إدارة المواقع"])
        session = Session()

        with tabs[4]: # تبويب المختبر للمدير
            df_l = pd.read_sql(session.query(LabLog).statement, session.bind)
            st.success("نتائج المختبر")
            st.dataframe(df_l)

        with tabs[3]: # تبويب السلامة للمدير
            df_s = pd.read_sql(session.query(SafetyLog).statement, session.bind)
            st.warning("تقارير السلامة")
            st.table(df_s)

        with tabs[5]: # إدارة المواقع
            with st.form("site_f"):
                n = st.text_input("Site Name"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button(T["save"]):
                    session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
        session.close()

    # --- 5. واجهات المسؤولين المخصصة ---
    elif not all_sites:
        st.warning("يجب على المدير إضافة موقع أولاً")
    
    # واجهة السلامة
    elif role == T["role_safe"]:
        st.header(T["safe"])
        with st.form("safe_f"):
            inc = st.selectbox("Type", ["Normal", "Accident", "Risk"])
            note = st.text_area("Notes")
            if st.form_submit_button(T["save"]):
                session = Session(); session.add(SafetyLog(incident=inc, notes=note)); session.commit(); session.close(); st.success("✅")

    # واجهة المختبر
    elif role == T["role_lab"]:
        st.header(T["lab"])
        with st.form("lab_f"):
            test = st.text_input("الاختبار"); res = st.text_input("النتيجة"); s_choice = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session(); session.add(LabLog(test_name=test, result=res, site=s_choice)); session.commit(); session.close(); st.success("✅")

    # واجهة العمال
    elif role == T["role_worker"]:
        st.header("تسجيل العمال")
        with st.form("worker_f"):
            name = st.text_input("Name"); hours = st.number_input("Hours"); rate = st.number_input("Rate"); s_choice = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session(); session.add(WorkerLog(worker_name=name, hours=hours, hourly_rate=rate, site=s_choice)); session.commit(); session.close(); st.success("✅")
