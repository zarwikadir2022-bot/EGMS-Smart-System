import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import google.generativeai as genai

# --- 1. قاموس اللغات (Translations Dictionary) ---
LANG = {
    "العربية": {
        "title": "نظام EGMS الرقمي",
        "login": "تسجيل الدخول",
        "user": "اسم المستخدم",
        "pwd": "كلمة المرور",
        "btn_login": "دخول آمن",
        "role_dir": "مدير",
        "role_field": "مسؤول ميداني",
        "dash": "لوحة القيادة الاستراتيجية",
        "map": "الخارطة التفاعلية للمشاريع",
        "report": "إرسال تقرير جديد",
        "site": "الموقع",
        "prog": "نسبة الإنجاز",
        "notes": "الملاحظات",
        "send": "إرسال البيانات",
        "ai_title": "✨ نصيحة المستشار الذكي",
        "logout": "تسجيل الخروج"
    },
    "Français": {
        "title": "Système Numérique EGMS",
        "login": "Connexion",
        "user": "Identifiant",
        "pwd": "Mot de passe",
        "btn_login": "Connexion Sécurisée",
        "role_dir": "Directeur",
        "role_field": "Agent Terrain",
        "dash": "Tableau de Bord Stratégique",
        "map": "Cartographie des Projets",
        "report": "Nouveau Rapport de Chantier",
        "site": "Site de Travail",
        "prog": "Avancement (%)",
        "notes": "Observations",
        "send": "Envoyer le Rapport",
        "ai_title": "✨ Conseil de l'IA",
        "logout": "Déconnexion"
    }
}

# --- 2. إعداد قاعدة البيانات ---
Base = declarative_base()
class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True)
    site = Column(String(100)); progress = Column(Float); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_name = Column(String(100)); lat = Column(Float); lon = Column(Float)

engine = create_engine('sqlite:///egms_bilingual.db')
Base.metadata.all_all(engine)
Session = sessionmaker(bind=engine)

# --- 3. واجهة البرنامج الموحدة ---
st.set_page_config(page_title="EGMS Digital", layout="wide")

# اختيار اللغة في القائمة الجانبية
selected_lang = st.sidebar.selectbox("🌐 Langue / اللغة", ["Français", "العربية"])
T = LANG[selected_lang]

# محرك الذكاء الاصطناعي ثنائي اللغة
def get_ai_advice(data, lang):
    if "GEMINI_API_KEY" not in st.secrets: return "..."
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"Role: Expert Consultant for EGMS Construction Tunisia. Analyze this data: {data}. " \
             f"Provide advice in {lang} about engineering, law, or finance."
    response = model.generate_content(prompt)
    return response.text

# --- 4. منطق الدخول والواجهات ---
if "logged_in" not in st.session_state:
    st.markdown(f"<h1 style='text-align:center;'>{T['login']}</h1>", unsafe_allow_html=True)
    u = st.text_input(T['user'])
    p = st.text_input(T['pwd'], type="password")
    if st.button(T['btn_login']):
        if u == "admin": 
            st.session_state["logged_in"] = True
            st.session_state["role"] = T['role_dir']
            st.rerun()

if st.session_state.get("logged_in"):
    st.sidebar.write(f"👤 {st.session_state['role']}")
    if st.sidebar.button(T['logout']):
        del st.session_state["logged_in"]; st.rerun()

    if st.session_state["role"] == T['role_dir']:
        st.title(f"📊 {T['dash']}")
        session = Session(); df = pd.read_sql(session.query(WorkLog).statement, session.bind); session.close()
        
        if not df.empty:
            st.info(f"**{T['ai_title']}:**\n\n" + get_ai_advice(df.tail(3).to_string(), selected_lang))
            st.subheader(T['map'])
            st.map(df, latitude='lat', longitude='lon', size='progress')
            st.dataframe(df)
    else:
        st.header(T['report'])
        with st.form("f"):
            s = st.selectbox(T['site'], ["Fouchana", "Sousse", "Sfax"])
            pr = st.slider(T['prog'], 0, 100)
            nt = st.text_area(T['notes'])
            if st.form_submit_button(T['send']):
                # حفظ البيانات (نفس المنطق السابق)
                st.success("✅ OK")