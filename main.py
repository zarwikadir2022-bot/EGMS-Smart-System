import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# --- 1. إعداد قاعدة البيانات ---
Base = declarative_base()

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True)
    site = Column(String(100)); progress = Column(Float); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    lat = Column(Float); lon = Column(Float); user_name = Column(String(50))

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True)
    item = Column(String(100)); qty = Column(Float); site = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow); user_name = Column(String(50))

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True)
    incident = Column(String(100)); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow); user_name = Column(String(50))

# إنشاء المحرك وقاعدة البيانات
engine = create_engine('sqlite:///egms_final_system.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# بيانات المواقع
SITES_DATA = {
    "Fouchana (فوشانة)": (36.6897, 10.1244),
    "Sousse (سوسة)": (35.8256, 10.6084),
    "Sfax (صفاقس)": (34.7406, 10.7603),
    "Bizerte (بنزرت)": (37.2744, 9.8739)
}

# --- 2. القاموس اللغوي ---
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

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state:
    st.markdown(f"<h2 style='text-align:center;'>{T['login']}</h2>", unsafe_allow_html=True)
    u = st.text_input(T["user"])
    p = st.text_input(T["pwd"], type="password")
    
    if st.button("🚀 Enter"):
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
            st.error("Error / خطأ")
else:
    role = st.session_state["role"]
    st.sidebar.write(f"👤 {role}")
    if st.sidebar.button("Logout / خروج"):
        del st.session_state["logged_in"]; st.rerun()

    # --- 4. الواجهات حسب الصلاحيات ---

    # أ. المدير العام (يطلع على كل شيء في تبويبات)
    if role == T["role_dir"]:
        st.title(T["dash"])
        # تم تصحيح القوس هنا بعناية:
        tab_map, tab_stock, tab_safe = st.tabs([T["map"], T["store_tab"], T["safety_tab"]])
        
        session = Session()
        with tab_map:
            df_work = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_work.empty:
                st.map(df_work, latitude='lat', longitude='lon', size='progress')
                st.dataframe(df_work)
            else:
                st.info("No work reports yet.")
        
        with tab_stock:
            df_stock = pd.read_sql(session.query(StoreLog).statement, session.bind)
            st.dataframe(df_stock)
            
        with tab_safe:
            df_safe = pd.read_sql(session.query(SafetyLog).statement, session.bind)
            st.warning(T["safety_tab"])
            st.table(df_safe)
        session.close()

    # ب. مسؤول المغازة
    elif role == T["role_store"]:
        st.header(T["store_tab"])
        with st.form("stock_form"):
            item = st.text_input(T["item"])
            qty = st.number_input(T["qty"], min_value=0.0)
            site_store = st.selectbox(T["site"], list(SITES_DATA.keys()))
            if st.form_submit_button(T["save"]):
                session = Session()
                new_item = StoreLog(item=item, qty=qty, site=site_store, user_name=st.session_state["user_id"])
                session.add(new_item); session.commit(); session.close()
                st.success("✅ Enregistré avec succès / تم الحفظ")

    # ج. مسؤول السلامة
    elif role == T["role_safety"]:
        st.header(T["safety_tab"])
        with st.form("safety_form"):
            inc = st.selectbox(T["incident"], ["Normal", "Accident", "Risque/Risk"])
            note = st.text_area("Details")
            if st.form_submit_button(T["save"]):
                session = Session()
                new_safe = SafetyLog(incident=inc, notes=note, user_name=st.session_state["user_id"])
                session.add(new_safe); session.commit(); session.close()
                st.error("⚠️ Alerte envoyée au siège / تم إرسال التنبيه للإدارة")
