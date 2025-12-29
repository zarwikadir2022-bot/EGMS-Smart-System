import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px

# --- 1. إعداد قاعدة البيانات (نسخة v19) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True) # هذا هو سبب الخطأ (يمنع التكرار)
    lat = Column(Float); lon = Column(Float)

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

# إنشاء محرك قاعدة البيانات
engine = create_engine('sqlite:///egms_final_v19.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي ---
LANG = {
    "العربية": {
        "title": "منظومة EGMS الذكية", "login": "تسجيل الدخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "role_safe": "مسؤول السلامة", "role_lab": "مسؤول المختبر",
        "role_worker": "مسؤول العمال", "role_store": "مسؤول المخزن", "role_work": "الأشغال الميدانية",
        "save": "حفظ البيانات", "dash": "لوحة التحكم", "map": "الخريطة", "add_site": "إدارة الحضائر"
    },
    "Français": {
        "title": "EGMS Smart System", "login": "Connexion", "user": "ID", "pwd": "Pass",
        "role_dir": "Directeur", "role_safe": "Sécurité", "role_lab": "Labo",
        "role_worker": "RH", "role_store": "Stock", "role_work": "Travaux",
        "save": "Enregistrer", "dash": "Dashboard", "map": "Carte", "add_site": "Gestion Sites"
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
    if st.sidebar.button("Logout / خروج"): st.session_state.clear(); st.rerun()
    
    all_sites = get_sites()

    # --- 4. واجهة المدير (إصلاح مشكلة إضافة الموقع) ---
    if role == T["role_dir"]:
        st.title(T["dash"])
        tabs = st.tabs([T["map"], "المخزن", "العمال", "السلامة", "المختبر", T["add_site"]])
        
        with tabs[5]: # تبويب إدارة المواقع
            st.subheader(T["add_site"])
            with st.form("site_secure_form"):
                n = st.text_input("اسم الحضيرة الجديد")
                c1, c2 = st.columns(2)
                la = c1.number_input("Lat", value=36.0, format="%.6f")
                lo = c2.number_input("Lon", value=10.0, format="%.6f")
                if st.form_submit_button(T["save"]):
                    if n:
                        session = Session()
                        # فحص هل الموقع موجود مسبقاً قبل الإضافة
                        exists = session.query(Site).filter_by(name=n).first()
                        if exists:
                            st.warning(f"الموقع '{n}' موجود بالفعل في النظام!")
                            session.close()
                        else:
                            try:
                                session.add(Site(name=n, lat=la, lon=lo))
                                session.commit()
                                st.success("✅ تم إضافة الموقع بنجاح!")
                                session.close()
                                st.rerun()
                            except Exception as e:
                                st.error("حدث خطأ تقني أثناء الحفظ")
                                session.rollback()
                    else: st.error("يرجى إدخال اسم للموقع")

        with tabs[0]: # الخريطة
            session = Session()
            df_w = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_w.empty: st.map(df_w)
            else: st.info("لا توجد بيانات جغرافية حالياً")
            session.close()

    # --- 5. واجهات المسؤولين ---
    elif not all_sites:
        st.warning("يجب على المدير إضافة موقع (حضيرة) أولاً قبل البدء")
    
    # واجهة المختبر (Lab)
    elif role == T["role_lab"]:
        st.header("نتائج المختبر")
        with st.form("lab_f"):
            test = st.text_input("نوع الاختبار")
            res = st.text_input("النتيجة")
            stat = st.selectbox("الحالة", ["مطابق", "غير مطابق"])
            s_choice = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button(T["save"]):
                session = Session()
                session.add(LabLog(test_name=test, result=res, status=stat, site=s_choice))
                session.commit(); session.close(); st.success("✅ تم تسجيل النتيجة")

    # واجهة السلامة (Safety)
    elif role == T["role_safe"]:
        st.header("تقرير السلامة")
        with st.form("safe_f"):
            inc = st.selectbox("الحادث", ["عادي", "حادث شغل", "خطر محتمل"])
            note = st.text_area("التفاصيل")
            if st.form_submit_button(T["save"]):
                session = Session()
                session.add(SafetyLog(incident=inc, notes=note))
                session.commit(); session.close(); st.success("✅ تم الحفظ")
