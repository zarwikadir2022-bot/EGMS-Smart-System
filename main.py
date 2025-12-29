import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px

# --- 1. إعداد قاعدة البيانات الشاملة (v22) ---
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
    site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True)
    worker_name = Column(String(100)); hours = Column(Float); hourly_rate = Column(Float)
    specialization = Column(String(100)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True)
    incident = Column(String(100)); notes = Column(Text); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class LabLog(Base):
    __tablename__ = 'lab_logs'
    id = Column(Integer, primary_key=True)
    test_name = Column(String(100)); result = Column(String(100)); status = Column(String(50))
    site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_final_v22.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي ---
LANG = {
    "العربية": {
        "title": "منظومة EGMS الرقمية", "login": "تسجيل الدخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "role_safe": "مسؤول السلامة", "role_lab": "مسؤول المختبر",
        "role_worker": "مسؤول العمال", "role_store": "مسؤول المخزن", "role_work": "مسؤول الأشغال",
        "save": "حفظ", "dash": "لوحة التحكم", "map": "الخريطة", "add_site": "إدارة الحضائر"
    },
    "Français": {
        "title": "Système Digital EGMS", "login": "Connexion", "user": "ID", "pwd": "Pass",
        "role_dir": "Directeur", "role_safe": "Sécurité", "role_lab": "Labo",
        "role_worker": "RH", "role_store": "Stock", "role_work": "Travaux",
        "save": "Enregistrer", "dash": "Dashboard", "map": "Carte", "add_site": "Sites"
    }
}

st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐", ["Français", "العربية"])
T = LANG[sel_lang]

def get_sites():
    session = Session(); s = session.query(Site).all(); session.close()
    return {x.name: (x.lat, x.lon) for x in s}

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state:
    st.title(T["login"])
    u = st.text_input(T["user"]); p = st.text_input(T["pwd"], type="password")
    if st.button("🚀"):
        # خريطة الدخول مع معرفات ثابتة (Admin, Safety, Lab, Labor, Store, Work)
        access = {
            "admin": ("egms2025", "Admin"),
            "safety": ("safe2025", "Safety"),
            "labo": ("lab2025", "Lab"),
            "labor": ("labor2025", "Labor"),
            "magaza": ("store2025", "Store"),
            "work": ("work2025", "Work")
        }
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role_id": access[u][1]})
            st.rerun()
        else: st.error("خطأ في البيانات")
else:
    role_id = st.session_state.get("role_id")
    st.sidebar.markdown(f"👤 **{role_id}**")
    if st.sidebar.button("Logout / خروج"): st.session_state.clear(); st.rerun()
    
    all_sites = get_sites()

    # --- 4. واجهة المدير العام ---
    if role_id == "Admin":
        st.title(T["dash"])
        tabs = st.tabs([T["map"], "المخزن", "العمال", "الأشغال", "السلامة", "المختبر", T["add_site"]])
        session = Session()
        with tabs[0]: # الخريطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')
            else: st.info("الخريطة فارغة")
        with tabs[6]: # إضافة المواقع
            with st.form("site_f"):
                n = st.text_input("اسم الحضيرة"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("إضافة"):
                    session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
        session.close()

    # --- 5. واجهة مسؤول الأشغال (التي كانت تظهر فارغة) ---
    elif role_id == "Work":
        st.header(f"🏗️ {T['role_work']}")
        if not all_sites:
            st.warning("⚠️ يجب على المدير إضافة حضيرة أولاً")
        else:
            with st.form("work_form"):
                s_choice = st.selectbox("اختر الحضيرة", list(all_sites.keys()))
                prog = st.slider("نسبة الإنجاز %", 0, 100)
                note = st.text_area("ملاحظات العمل اليومية")
                if st.form_submit_button(T["save"]):
                    session = Session(); lat, lon = all_sites[s_choice]
                    session.add(WorkLog(site=s_choice, progress=prog, notes=note, lat=lat, lon=lon))
                    session.commit(); session.close(); st.success("✅ تم إرسال تقرير الأشغال بنجاح")

    # --- 6. واجهة مسؤول العمال ---
    elif role_id == "Labor":
        st.header(f"👷 {T['role_worker']}")
        if not all_sites: st.warning("يجب إضافة حضيرة أولاً")
        else:
            with st.form("labor_f"):
                name = st.text_input("اسم العامل"); h = st.number_input("الساعات"); r = st.number_input("الكلفة")
                s_choice = st.selectbox("الموقع", list(all_sites.keys()))
                if st.form_submit_button(T["save"]):
                    session = Session(); session.add(WorkerLog(worker_name=name, hours=h, hourly_rate=r, site=s_choice))
                    session.commit(); session.close(); st.success("✅ تم الحفظ")

    # --- 7. واجهة مسؤول المخزن ---
    elif role_id == "Store":
        st.header(f"📦 {T['role_store']}")
        with st.form("store_f"):
            item = st.text_input("المادة"); qty = st.number_input("الكمية"); t_type = st.radio("النوع", ["Entry", "Exit"])
            s_choice = st.selectbox("الموقع", list(all_sites.keys()) if all_sites else ["No Sites"])
            if st.form_submit_button(T["save"]):
                session = Session(); session.add(StoreLog(item=item, qty=qty, trans_type=t_type, site=s_choice))
                session.commit(); session.close(); st.success("✅ تم التحديث")
