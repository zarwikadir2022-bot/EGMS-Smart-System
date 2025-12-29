import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# --- 1. إعدادات قاعدة البيانات والمواقع ---
Base = declarative_base()
class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True)
    site = Column(String(100)); progress = Column(Float); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    lat = Column(Float); lon = Column(Float)

engine = create_engine('sqlite:///egms_final.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# إحداثيات المواقع في تونس
SITES_DATA = {
    "Fouchana (فوشانة)": (36.6897, 10.1244),
    "Sousse (سوسة)": (35.8256, 10.6084),
    "Sfax (صفاقس)": (34.7406, 10.7603),
    "Bizerte (بنزرت)": (37.2744, 9.8739)
}

# --- 2. القاموس اللغوي المطور ---
LANG = {
    "العربية": {
        "title": "نظام EGMS الرقمي", "dash": "لوحة التحكم", "report": "تقرير ميداني جديد",
        "site": "اختر الموقع", "prog": "نسبة الإنجاز %", "notes": "ملاحظات تقنية",
        "save": "إرسال التقرير", "history": "سجل الأشغال", "map": "خريطة المواقع"
    },
    "Français": {
        "title": "Système Digital EGMS", "dash": "Tableau de Bord", "report": "Nouveau Rapport",
        "site": "Choisir le Site", "prog": "Avancement %", "notes": "Observations",
        "save": "Envoyer", "history": "Historique", "map": "Cartographie"
    }
}

st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐 Langue/اللغة", ["Français", "العربية"])
T = LANG[sel_lang]

# التحقق من الدخول (نفس الكود السابق)
if "logged_in" not in st.session_state:
    st.title("🔐 Login / دخول")
    u = st.text_input("User")
    p = st.text_input("Pass", type="password")
    if st.button("Enter"):
        if u == "admin" and p == "egms2025":
            st.session_state["logged_in"] = True
            st.rerun()
else:
    # --- واجهة النظام الحقيقية ---
    st.sidebar.markdown(f"### 🏗️ EGMS Digital")
    
    tab1, tab2 = st.tabs([T["report"], T["dash"]])

    # التبويب الأول: إدخال البيانات
    with tab1:
        with st.form("report_form"):
            site_name = st.selectbox(T["site"], list(SITES_DATA.keys()))
            progress_val = st.slider(T["prog"], 0, 100)
            note_val = st.text_area(T["notes"])
            if st.form_submit_button(T["save"]):
                session = Session()
                lat, lon = SITES_DATA[site_name]
                new_entry = WorkLog(site=site_name, progress=progress_val, notes=note_val, lat=lat, lon=lon)
                session.add(new_entry)
                session.commit()
                session.close()
                st.success("✅ Done / تم الحفظ")

    # التبويب الثاني: عرض البيانات والخريطة
    with tab2:
        session = Session()
        df = pd.read_sql(session.query(WorkLog).statement, session.bind)
        session.close()

        if not df.empty:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader(T["map"])
                st.map(df, latitude='lat', longitude='lon', size='progress')
            with col2:
                st.subheader(T["history"])
                st.dataframe(df[['site', 'progress', 'timestamp']].tail(10))
        else:
            st.warning("No data yet / لا توجد بيانات بعد")

    if st.sidebar.button("Logout"):
        del st.session_state["logged_in"]; st.rerun()
