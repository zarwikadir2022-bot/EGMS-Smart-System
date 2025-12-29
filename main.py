import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px

# --- 1. إعداد قاعدة البيانات الشاملة ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    lat = Column(Float); lon = Column(Float)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True)
    site = Column(String(100)); progress = Column(Float); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow); lat = Column(Float); lon = Column(Float)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True)
    item = Column(String(100)); unit = Column(String(50)); qty = Column(Float)
    trans_type = Column(String(20)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True)
    worker_name = Column(String(100)); hours = Column(Float); hourly_rate = Column(Float)
    specialization = Column(String(100)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True)
    incident = Column(String(100)); notes = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow)

class LabLog(Base): # جدول المختبر الجديد
    __tablename__ = 'lab_logs'
    id = Column(Integer, primary_key=True)
    test_name = Column(String(100)); result = Column(String(100)); status = Column(String(50))
    site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_mega_system_v17.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي ---
LANG = {
    "العربية": {
        "title": "نظام EGMS المتكامل", "login": "دخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "role_safe": "مسؤول السلامة", "role_lab": "مسؤول المختبر",
        "add_site": "إدارة المواقع", "map": "الخريطة", "stock": "المخزن", "worker": "العمالة",
        "save": "حفظ", "safety_tab": "الأمن والسلامة", "lab_tab": "نتائج المختبر"
    },
    "Français": {
        "title": "Système Intégré EGMS", "login": "Connexion", "user": "ID", "pwd": "Pass",
        "role_dir": "Directeur", "role_safe": "Sécurité", "role_lab": "Laboratoire",
        "add_site": "Sites", "map": "Carte", "stock": "Stock", "worker": "RH",
        "save": "Enregistrer", "safety_tab": "Sécurité", "lab_tab": "Labo"
    }
}

st.set_page_config(page_title="EGMS Mega System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐", ["Français", "العربية"])
T = LANG[sel_lang]

def get_sites():
    session = Session()
    s = session.query(Site).all()
    session.close()
    return {x.name: (x.lat, x.lon) for x in s}

# --- 3. نظام الصلاحيات ودخول المستخدمين ---
if "logged_in" not in st.session_state:
    st.title(T["login"])
    u = st.text_input(T["user"]); p = st.text_input(T["pwd"], type="password")
    if st.button("🚀"):
        # تم هنا استرجاع كافة الأدوار المفقودة
        access = {
            "admin": ("egms2025", T["role_dir"]),
            "safety": ("safe2025", "Safety"),
            "labo": ("lab2025", "Lab"),
            "magaza": ("store2025", "Store"),
            "labor": ("labor2025", "Labor"),
            "work": ("work2025", "Work")
        }
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role": access[u][1]})
            st.rerun()
        else: st.error("Error / خطأ")
else:
    role = st.session_state.get("role")
    st.sidebar.write(f"👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    
    all_sites = get_sites()

    # --- 4. واجهة المدير (ترى كل شيء) ---
    if role == T["role_dir"]:
        st.title(T["title"])
        tabs = st.tabs([T["map"], T["stock"], T["worker"], T["safety_tab"], T["lab_tab"], T["add_site"]])
        session = Session()

        with tabs[0]: # الخريطة
            df_w = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_w.empty: st.map(df_w)

        with tabs[1]: # المخزن
            df_s = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_s.empty: st.dataframe(df_s)

        with tabs[3]: # السلامة للمدير
            df_safe = pd.read_sql(session.query(SafetyLog).statement, session.bind)
            st.warning(T["safety_tab"])
            st.table(df_safe)

        with tabs[4]: # المختبر للمدير
            df_lab = pd.read_sql(session.query(LabLog).statement, session.bind)
            st.success(T["lab_tab"])
            st.dataframe(df_lab)

        with tabs[5]: # إدارة المواقع
            with st.form("site_f"):
                n = st.text_input("Site Name"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button(T["save"]):
                    session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
        session.close()

    # --- 5. واجهة مسؤول السلامة ---
    elif role == "Safety":
        st.header(T["safety_tab"])
        with st.form("safety_f"):
            inc = st.selectbox("Type", ["Normal", "Accident", "Risk"])
            note = st.text_area("Details")
            if st.form_submit_button(T["save"]):
                session = Session()
                session.add(SafetyLog(incident=inc, notes=note))
                session.commit(); session.close(); st.success("Saved!")

    # --- 6. واجهة مسؤول المختبر ---
    elif role == "Lab":
        st.header(T["lab_tab"])
        with st.form("lab_f"):
            t_name = st.text_input("اسم الاختبار (مثلاً: ضغط الخرسانة)")
            res = st.text_input("النتيجة")
            stat = st.selectbox("الحالة", ["مطابق (Conforme)", "غير مطابق (Non-conforme)"])
            s_choice = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session()
                session.add(LabLog(test_name=t_name, result=res, status=stat, site=s_choice))
                session.commit(); session.close(); st.success("Saved!")

    # واجهات (Store, Labor, Work) تستمر بنفس النمط...
