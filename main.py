import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px

# --- 1. إعداد قاعدة البيانات الشاملة (v20) ---
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
engine = create_engine('sqlite:///egms_final_v20.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي الشامل ---
LANG = {
    "العربية": {
        "title": "منظومة EGMS المتكاملة", "login": "تسجيل الدخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "role_safe": "مسؤول السلامة", "role_lab": "مسؤول المختبر",
        "role_worker": "مسؤول العمال", "role_store": "مسؤول المخزن", "role_work": "مسؤول الأشغال",
        "save": "حفظ البيانات", "dash": "لوحة التحكم", "map": "الخريطة", "add_site": "إدارة الحضائر"
    },
    "Français": {
        "title": "EGMS Global System", "login": "Connexion", "user": "ID", "pwd": "Pass",
        "role_dir": "Directeur", "role_safe": "Sécurité", "role_lab": "Labo",
        "role_worker": "RH / Ouvriers", "role_store": "Magasinier", "role_work": "Travaux",
        "save": "Enregistrer", "dash": "Dashboard", "map": "Carte", "add_site": "Gestion Sites"
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
    if st.button("🚀 Enter"):
        # خريطة الحسابات والأدوار
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
        else: st.error("خطأ في بيانات الدخول")
else:
    role = st.session_state.get("role")
    st.sidebar.markdown(f"👤 **{role}**")
    if st.sidebar.button("Logout / خروج"): st.session_state.clear(); st.rerun()
    
    all_sites = get_sites()

    # --- 4. واجهة المدير العام ---
    if role == T["role_dir"]:
        st.title(T["dash"])
        tabs = st.tabs([T["map"], "المخزن", "العمال والرواتب", "السلامة", "المختبر", T["add_site"]])
        session = Session()

        with tabs[5]: # إدارة المواقع
            st.subheader(T["add_site"])
            with st.form("site_f"):
                n = st.text_input("اسم الحضيرة"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button(T["save"]):
                    if n not in all_sites:
                        session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.success("Site Added!"); st.rerun()
                    else: st.warning("الموقع موجود مسبقاً")
        
        with tabs[0]: # الخريطة
            df_w = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_w.empty: st.map(df_w)
            else: st.info("لا توجد بيانات جغرافية")
        
        with tabs[2]: # العمال للمدير
            df_worker = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            st.dataframe(df_worker)

        session.close()

    # --- 5. فحص وجود مواقع أولاً ---
    elif not all_sites:
        st.warning("⚠️ يرجى من المدير إضافة مواقع (حضائر) أولاً ليتمكن المسؤولون من إدخال البيانات.")

    # --- 6. واجهة مسؤول العمال (التي كانت ناقصة) ---
    elif role == T["role_worker"]:
        st.header(f"👷 {T['role_worker']}")
        with st.form("worker_f"):
            name = st.text_input("اسم العامل (Nom de l'ouvrier)")
            h = st.number_input("ساعات العمل (Heures)", min_value=0.5, step=0.5)
            r = st.number_input("كلفة الساعة (Tarif Horaire)", min_value=0.0)
            spec = st.selectbox("التخصص (Spécialité)", ["بناء", "عامل", "كهربائي", "حداد", "دهان"])
            s_choice = st.selectbox("الموقع (Chantier)", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session()
                session.add(WorkerLog(worker_name=name, hours=h, hourly_rate=r, specialization=spec, site=s_choice))
                session.commit(); session.close(); st.success("✅ تم تسجيل بيانات العامل بنجاح")

    # --- 7. واجهة مسؤول المخزن ---
    elif role == T["role_store"]:
        st.header(f"📦 {T['role_store']}")
        with st.form("store_f"):
            item = st.text_input("المادة (Article)")
            qty = st.number_input("الكمية (Quantité)", min_value=0.1)
            t_type = st.radio("النوع (Type)", ["Entry (دخول)", "Exit (خروج)"])
            s_choice = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session()
                session.add(StoreLog(item=item, qty=qty, trans_type=t_type, site=s_choice))
                session.commit(); session.close(); st.success("✅ تم تحديث المخزن")

    # --- 8. واجهة مسؤول السلامة ---
    elif role == T["role_safe"]:
        st.header(f"🛡️ {T['role_safe']}")
        with st.form("safe_f"):
            inc = st.selectbox("الحادث", ["عادي", "حادث شغل", "خطر محتمل"])
            note = st.text_area("التفاصيل")
            s_choice = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session()
                session.add(SafetyLog(incident=inc, notes=note, site=s_choice))
                session.commit(); session.close(); st.success("✅ تم إرسال تقرير السلامة")

    # --- 9. واجهة مسؤول المختبر ---
    elif role == T["role_lab"]:
        st.header(f"🧪 {T['role_lab']}")
        with st.form("lab_f"):
            test = st.text_input("نوع الاختبار")
            res = st.text_input("النتيجة")
            stat = st.selectbox("الحالة", ["مطابق", "غير مطابق"])
            s_choice = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session()
                session.add(LabLog(test_name=test, result=res, status=stat, site=s_choice))
                session.commit(); session.close(); st.success("✅ تم تسجيل نتيجة المختبر")
