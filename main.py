import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import google.generativeai as genai

# --- 1. CONFIGURATION ---
Base = declarative_base()

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True)
    site = Column(String(100))
    progress = Column(Float)
    notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_name = Column(String(100))
    lat = Column(Float)
    lon = Column(Float)

# التصحيح هنا: التأكد من اسم قاعدة البيانات واستخدام create_all
engine = create_engine('sqlite:///egms_final_v2.db')
Base.metadata.create_all(engine) # السطر الذي كان فيه الخطأ
Session = sessionmaker(bind=engine)

# --- 2. TRANSLATIONS ---
LANG = {
    "العربية": {
        "title": "نظام EGMS الرقمي", "login": "تسجيل الدخول", "user": "المستخدم", "pwd": "الرمز",
        "btn": "دخول", "dash": "لوحة التحكم", "site": "الموقع", "prog": "الإنجاز", "send": "إرسال"
    },
    "Français": {
        "title": "EGMS Digital", "login": "Connexion", "user": "Identifiant", "pwd": "Pass",
        "btn": "Entrer", "dash": "Tableau de bord", "site": "Site", "prog": "Avancement", "send": "Envoyer"
    }
}

# --- 3. UI ---
st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐 Langue", ["Français", "العربية"])
T = LANG[sel_lang]

if "logged_in" not in st.session_state:
    st.title(T["login"])
    u = st.text_input(T["user"])
    p = st.text_input(T["pwd"], type="password")
    if st.button(T["btn"]):
        if u == "admin" and p == "egms2025":
            st.session_state["logged_in"] = True
            st.rerun()
else:
    st.sidebar.success(f"Connected: Admin")
    st.title(f"🏗️ {T['title']}")
    
    if st.sidebar.button("Logout / خروج"):
        del st.session_state["logged_in"]
        st.rerun()

    st.subheader(T["dash"])
    st.info("Système EGMS opérationnel / نظام EGMS جاهز للعمل")
