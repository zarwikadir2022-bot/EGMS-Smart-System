import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px

# --- 1. إعداد قاعدة البيانات ---
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
    price = Column(Float); trans_type = Column(String(20)); site = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True)
    incident = Column(String(100)); notes = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow)

class EquipmentLog(Base):
    __tablename__ = 'equipment_logs'
    id = Column(Integer, primary_key=True)
    machine_name = Column(String(100)); work_hours = Column(Float); machine_status = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_final_stable.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي ---
LANG = {
    "العربية": {
        "title": "نظام EGMS الرقمي", "login": "دخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "dash": "لوحة القيادة", "alerts": "التنبيهات العاجلة",
        "add_site": "إضافة موقع حضيرة", "site_name": "اسم الموقع", "save": "حفظ",
        "map": "الخريطة", "stock": "المخزن", "equip": "المعدات", "safe": "الأمن",
        "item": "المادة", "qty": "الكمية", "total": "الرصيد المتوفر", "in": "دخول", "out": "خروج"
    },
    "Français": {
        "title": "EGMS Digital System", "login": "Connexion", "user": "ID", "pwd": "Pass",
        "role_dir": "Directeur", "dash": "Dashboard", "alerts": "Alertes Critiques",
        "add_site": "Ajouter un Site", "site_name": "Nom du Site", "save": "Enregistrer",
        "map": "Carte", "stock": "Stock", "equip": "Engins", "safe": "Sécurité",
        "item": "Article", "qty": "Quantité", "total": "Stock Actuel", "in": "Entrée", "out": "Sortie"
    }
}

st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐", ["Français", "العربية"])
T = LANG[sel_lang]

# دالة جلب المواقع
def get_sites():
    session = Session()
    s = session.query(Site).all()
    session.close()
    return {x.name: (x.lat, x.lon) for x in s}

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state:
    st.title(T["login"])
    u = st.text_input(T["user"]); p = st.text_input(T["pwd"], type="password")
    if st.button("🚀 Enter"):
        access = {"admin": ("egms2025", T["role_dir"]), "magaza": ("store2025", "Store"), "safety": ("safe2025", "Safety"), "equip": ("equip2025", "Equip")}
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role": access[u][1], "u_id": u})
            st.rerun()
else:
    role = st.session_state.get("role")
    st.sidebar.write(f"👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    # --- 4. واجهة المدير (إدارة المواقع + الرقابة) ---
    if role == T["role_dir"]:
        st.title(T["dash"])
        
        # قسم التنبيهات
        session = Session()
        st.subheader(T["alerts"])
        # تنبيه المعدات
        over_h = session.query(EquipmentLog).filter(EquipmentLog.work_hours > 250).all()
        for m in over_h: st.error(f"🚨 {m.machine_name}: {m.work_hours}H - Maintenance Required!")
        
        tab_map, tab_sites, tab_stock = st.tabs([T["map"], T["add_site"], T["stock"]])
        
        with tab_sites:
            with st.form("site_form"):
                n = st.text_input(T["site_name"])
                c1, c2 = st.columns(2)
                la = c1.number_input("Lat", value=36.0, format="%.6f")
                lo = c2.number_input("Lon", value=10.0, format="%.6f")
                if st.form_submit_button(T["save"]):
                    new_s = Site(name=n, lat=la, lon=lo)
                    session.add(new_s); session.commit(); st.success("Site Added!")
        
        with tab_stock:
            df_s = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_s.empty:
                df_s['val'] = df_s.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                summary
