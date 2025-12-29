import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# --- 1. إعداد قاعدة البيانات الشاملة (v24) ---
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

# إنشاء محرك قاعدة البيانات
engine = create_engine('sqlite:///egms_final_v24.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي ---
LANG = {
    "العربية": {
        "title": "منظومة EGMS المتكاملة v24", "login": "تسجيل الدخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "role_safe": "مسؤول السلامة", "role_lab": "مسؤول المختبر",
        "role_worker": "مسؤول العمال", "role_store": "مسؤول المخزن", "role_work": "مسؤول الأشغال",
        "save": "حفظ", "dash": "لوحة التحكم المركزية", "map": "الخريطة", "add_site": "إدارة الحضائر"
    },
    "Français": {
        "title": "Système Global EGMS v24", "login": "Connexion", "user": "ID", "pwd": "Pass",
        "role_dir": "Directeur", "role_safe": "Sécurité", "role_lab": "Labo",
        "role_worker": "RH", "role_store": "Stock", "role_work": "Travaux",
        "save": "Enregistrer", "dash": "Tableau de Bord", "map": "Carte", "add_site": "Sites"
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
    if st.button("🚀 Enter"):
        access = {"admin": ("egms2025", "Admin"), "safety": ("safe2025", "Safety"), "labo": ("lab2025", "Lab"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store"), "work": ("work2025", "Work")}
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role_id": access[u][1]})
            st.rerun()
        else: st.error("Error")
else:
    role_id = st.session_state.get("role_id")
    st.sidebar.markdown(f"👤 **{role_id}**")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    
    all_sites = get_sites()

    # --- 4. واجهة المدير العام (عرض كافة البيانات) ---
    if role_id == "Admin":
        st.title(T["dash"])
        tabs = st.tabs([T["map"], "📦 المخزن", "👷 العمال", "🏗️ الأشغال", "🛡️ السلامة", "🧪 المختبر", T["add_site"]])
        session = Session()

        with tabs[0]: # الخريطة
            df_sites = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_sites.empty: st.map(df_sites, latitude='lat', longitude='lon')
            else: st.info("الخريطة فارغة")

        with tabs[1]: # بيانات المخزن
            st.subheader("سجل تحركات المخزن")
            df_store = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_store.empty: st.dataframe(df_store, use_container_width=True)
            else: st.info("لا توجد بيانات مخزن حالياً")

        with tabs[2]: # بيانات العمال
            st.subheader("سجل العمال والرواتب")
            df_worker = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_worker.empty: 
                df_worker['Total TND'] = df_worker['hours'] * df_worker['hourly_rate']
                st.dataframe(df_worker, use_container_width=True)
            else: st.info("لا توجد بيانات عمال حالياً")

        with tabs[3]: # بيانات الأشغال
            st.subheader("تقارير تقدم الأشغال")
            df_work = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_work.empty: st.dataframe(df_work, use_container_width=True)
            else: st.info("لا توجد تقارير ميدانية")

        with tabs[4]: # بيانات السلامة
            st.subheader("تقارير الحوادث والسلامة")
            df_safe = pd.read_sql(session.query(SafetyLog).statement, session.bind)
            if not df_safe.empty: st.table(df_safe)
            else: st.info("لا توجد تقارير سلامة")

        with tabs[5]: # بيانات المختبر
            st.subheader("نتائج اختبارات المختبر")
            df_lab = pd.read_sql(session.query(LabLog).statement, session.bind)
            if not df_lab.empty: st.dataframe(df_lab, use_container_width=True)
            else: st.info("لا توجد نتائج مختبر")

        with tabs[6]: # إضافة المواقع
            with st.form("site_f"):
                n = st.text_input("اسم الحضيرة"); la = st.number_input("Lat", value=36.0, format="%.6f"); lo = st.number_input("Lon", value=10.0, format="%.6f")
                if st.form_submit_button("إضافة"):
                    try:
                        session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.success("Done!"); st.rerun()
                    except IntegrityError: session.rollback(); st.error("Exists!")
        session.close()

    # --- 5. واجهات المسؤولين (لإدخال البيانات) ---
    elif not all_sites:
        st.warning("⚠️ يجب على المدير إضافة حضيرة أولاً من حسابه.")
    
    elif role_id == "Labor":
        st.header("تسجيل العمال")
        with st.form("l_f"):
            name = st.text_input("Name"); hours = st.number_input("Hours"); rate = st.number_input("Rate"); s_choice = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session(); session.add(WorkerLog(worker_name=name, hours=hours, hourly_rate=rate, site=s_choice)); session.commit(); session.close(); st.success("✅")

    elif role_id == "Store":
        st.header("المخزن")
        with st.form("s_f"):
            item = st.text_input("Item"); qty = st.number_input("Qty"); t_type = st.radio("Type", ["Entry", "Exit"]); s_choice = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session(); session.add(StoreLog(item=item, qty=qty, trans_type=t_type, site=s_choice)); session.commit(); session.close(); st.success("✅")

    elif role_id == "Safety":
        st.header("السلامة")
        with st.form("safe_f"):
            inc = st.selectbox("Type", ["Normal", "Accident", "Risk"]); note = st.text_area("Notes"); s_choice = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session(); session.add(SafetyLog(incident=inc, notes=note, site=s_choice)); session.commit(); session.close(); st.success("✅")

    elif role_id == "Lab":
        st.header("المختبر")
        with st.form("lab_f"):
            t_name = st.text_input("Test"); res = st.text_input("Result"); stat = st.selectbox("Status", ["مطابق", "غير مطابق"]); s_choice = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session(); session.add(LabLog(test_name=t_name, result=res, status=stat, site=s_choice)); session.commit(); session.close(); st.success("✅")

    elif role_id == "Work":
        st.header("الأشغال")
        with st.form("w_f"):
            s_choice = st.selectbox("Site", list(all_sites.keys())); prog = st.slider("%", 0, 100); note = st.text_area("Notes")
            if st.form_submit_button(T["save"]):
                session = Session(); lat, lon = all_sites[s_choice]; session.add(WorkLog(site=s_choice, progress=prog, notes=note, lat=lat, lon=lon)); session.commit(); session.close(); st.success("✅")
