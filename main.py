import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px

# --- 1. إعداد قاعدة البيانات ---
Base = declarative_base()

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
    incident = Column(String(100)); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class EquipmentLog(Base):
    __tablename__ = 'equipment_logs'
    id = Column(Integer, primary_key=True)
    machine_name = Column(String(100)); work_hours = Column(Float); fuel_qty = Column(Float)
    machine_status = Column(String(50)); faults = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_final_v8.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي ---
LANG = {
    "العربية": {
        "title": "نظام EGMS الرقمي", "login": "دخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "role_store": "مسؤول المغازة", "role_safety": "مسؤول السلامة", "role_equip": "مسؤول المعدات",
        "dash": "لوحة القيادة", "alerts": "تنبيهات النظام العاجلة", "save": "حفظ",
        "map": "الخريطة", "stock": "المخزن", "equip": "المعدات", "safe": "الأمن"
    },
    "Français": {
        "title": "Système Digital EGMS", "login": "Connexion", "user": "Identifiant", "pwd": "Pass",
        "role_dir": "Directeur", "role_store": "Magasinier", "role_safety": "Sécurité", "role_equip": "Gestionnaire Engins",
        "dash": "Tableau de Bord", "alerts": "Alertes Système Critiques", "save": "Enregistrer",
        "map": "Carte", "stock": "Stock", "equip": "Engins", "safe": "Sécurité"
    }
}

st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐", ["Français", "العربية"])
T = LANG[sel_lang]

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state:
    st.title(T["login"])
    u = st.text_input(T["user"]); p = st.text_input(T["pwd"], type="password")
    if st.button("🚀 Enter"):
        access = {"admin": ("egms2025", T["role_dir"]), "magaza": ("store2025", T["role_store"]), 
                  "safety": ("safe2025", T["role_safety"]), "equip": ("equip2025", T["role_equip"])}
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role": access[u][1], "user_id": u})
            st.rerun()
else:
    role = st.session_state.get("role")
    st.sidebar.write(f"👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    # --- 4. واجهة المدير (مع نظام التنبيهات) ---
    if role == T["role_dir"]:
        st.title(f"🏗️ {T['dash']}")
        
        # --- قسم التنبيهات الذكية (Smart Alerts Section) ---
        st.subheader(f"⚠️ {T['alerts']}")
        session = Session()
        
        # 1. فحص تجاوز ساعات عمل المعدات (> 250 ساعة)
        overworked_machines = session.query(EquipmentLog).filter(EquipmentLog.work_hours > 250).all()
        for m in overworked_machines:
            st.error(f"🚨 **تنبيه صيانة:** الآلة ({m.machine_name}) تجاوزت {m.work_hours} ساعة عمل! (يجب تغيير الزيت)")

        # 2. فحص حوادث السلامة
        critical_incidents = session.query(SafetyLog).filter(SafetyLog.incident.in_(['Accident', 'Risque/Risk'])).all()
        for inc in critical_incidents:
            st.warning(f"⚠️ **تنبيه أمني:** تم تسجيل ({inc.incident}) في موقع العمل! الملاحظات: {inc.notes}")

        # 3. فحص نقص المخزون (< 10 وحدات)
        df_stock = pd.read_sql(session.query(StoreLog).statement, session.bind)
        if not df_stock.empty:
            df_stock['val'] = df_stock.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
            summary = df_stock.groupby('item').agg({'val': 'sum'}).reset_index()
            low_stock = summary[summary['val'] < 10]
            for _, row in low_stock.iterrows():
                st.info(f"📦 **تنبيه مخزن:** المادة ({row['item']}) أوشكت على النفاد! الكمية المتبقية: {row['val']}")
        
        # --- التبويبات العادية ---
        tab_map, tab_stock, tab_equip = st.tabs([T["map"], T["stock"], T["equip"]])
        with tab_stock:
            st.plotly_chart(px.bar(summary, x='item', y='val', color='item', title="Stock Levels"), use_container_width=True)
        # (بقية الكود الخاص بالخرائط والمعدات...)
        session.close()

    # --- 5. واجهات المسؤولين (الإدخال) ---
    elif role == T["role_equip"]:
        st.header("إدارة المعدات")
        with st.form("equip_form"):
            m_name = st.text_input("اسم الآلة")
            h_work = st.number_input("ساعات العمل الحالية", min_value=0.0)
            m_status = st.selectbox("حالة الآلة", ["Bon État", "Panne"])
            if st.form_submit_button(T["save"]):
                session = Session()
                new_e = EquipmentLog(machine_name=m_name, work_hours=h_work, machine_status=m_status)
                session.add(new_e); session.commit(); session.close()
                st.success("تم الحفظ")
    
    # واجهات المغازة و السلامة تتبع نفس المنطق...
