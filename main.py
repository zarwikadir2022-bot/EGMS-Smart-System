import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# --- 1. إعداد قاعدة البيانات الهجين (إضافة جداول المغازة والسلامة) ---
Base = declarative_base()

class WorkLog(Base): # سجل الإنجاز
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True)
    site = Column(String(100)); progress = Column(Float); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    lat = Column(Float); lon = Column(Float); user_name = Column(String(50))

class StoreLog(Base): # سجل المغازة
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True)
    item = Column(String(100)); qty = Column(Float); site = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow); user_name = Column(String(50))

class SafetyLog(Base): # سجل السلامة
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True)
    incident = Column(String(100)); severity = Column(String(50)); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow); user_name = Column(String(50))

engine = create_engine('sqlite:///egms_enterprise.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# إحداثيات المواقع التونسية
SITES_DATA = {
    "Fouchana (فوشانة)": (36.6897, 10.1244),
    "Sousse (سوسة)": (35.8256, 10.6084),
    "Sfax (صفاقس)": (34.7406, 10.7603),
    "Bizerte (بنزرت)": (37.2744, 9.8739)
}

# --- 2. القاموس اللغوي للأدوار الجديدة ---
LANG = {
    "العربية": {
        "title": "نظام EGMS الرقمي", "login": "دخول النظام", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "role_store": "مسؤول المغازة", "role_safety": "مسؤول السلامة",
        "report": "تقرير الإنجاز", "store_tab": "حركة المخزن", "safety_tab": "أمن الورشة",
        "dash": "لوحة القيادة", "site": "الموقع", "prog": "نسبة الإنجاز %", "save": "حفظ البيانات",
        "item": "المعدة/المادة", "qty": "الكمية", "incident": "نوع التنبيه", "map": "خريطة الأشغال"
    },
    "Français": {
        "title": "EGMS Enterprise Digital", "login": "Accès Système", "user": "Identifiant", "pwd": "Pass",
        "role_dir": "Directeur Général", "role_store": "Gestionnaire Stock", "role_safety": "Responsable Sécurité",
        "report": "Rapport Avancement", "store_tab": "Gestion Stock", "safety_tab": "Sécurité Chantier",
        "dash": "Tableau de Bord", "site": "Site de travail", "prog": "Avancement %", "save": "Enregistrer",
        "item": "Article/Matériel", "qty": "Quantité", "incident": "Type d'alerte", "map": "Cartographie"
    }
}

st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐 Langue/اللغة", ["Français", "العربية"])
T = LANG[sel_lang]

# --- 3. نظام إدارة الجلسة والدخول ---
if "logged_in" not in st.session_state:
    st.markdown(f"<h2 style='text-align:center;'>{T['login']}</h2>", unsafe_allow_html=True)
    u = st.text_input(T["user"])
    p = st.text_input(T["pwd"], type="password")
    
    if st.button("🚀 Enter"):
        # تعريف المستخدمين وصلاحياتهم
        access_list = {
            "admin": ("egms2025", T["role_dir"]),
            "magaza": ("store2025", T["role_store"]),
            "safety": ("safe2025", T["role_safety"])
        }
        if u in access_list and p == access_list[u][0]:
            st.session_state["logged_in"] = True
            st.session_state["role"] = access_list[u][1]
            st.session_state["user_id"] = u
            st.rerun()
        else:
            st.error("Error / خطأ في البيانات")
else:
    # --- 4. واجهة المستخدم بناءً على الدور (RBAC) ---
    role = st.session_state["role"]
    st.sidebar.markdown(f"### 🏗️ EGMS Digital\n**{role}**")
    
    # خيار الخروج
    if st.sidebar.button("Logout / خروج"):
        del st.session_state["logged_in"]; st.rerun()

    # --- أ- واجهة المدير (Directeur) ---
    if role == T["role_dir"]:
        tab_map, tab_stock, tab_safe = st.tabs([T["map"], T["store_tab"], T
