
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
    timestamp = Column(DateTime, default=datetime.utcnow)
    lat = Column(Float); lon = Column(Float)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True)
    item = Column(String(100)); unit = Column(String(50)); qty = Column(Float)
    trans_type = Column(String(20)); site = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True)
    incident = Column(String(100)); notes = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow)

class EquipmentLog(Base):
    __tablename__ = 'equipment_logs'
    id = Column(Integer, primary_key=True)
    machine_name = Column(String(100)); work_hours = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_final_v11.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي ---
LANG = {
    "العربية": {
        "title": "نظام EGMS الرقمي", "login": "دخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "dash": "لوحة القيادة", "add_site": "إدارة المواقع",
        "map": "الخريطة", "stock": "المخزن", "equip": "المعدات", "safe": "الأمن",
        "report": "تقرير الإنجاز", "save": "حفظ", "item": "المادة", "qty": "الكمية"
    },
    "Français": {
        "title": "EGMS Digital System", "login": "Connexion", "user": "ID", "pwd": "Pass",
        "role_dir": "Directeur", "dash": "Dashboard", "add_site": "Gestion des Sites",
        "map": "Carte", "stock": "Stock", "equip": "Engins", "safe": "Sécurité",
        "report": "Rapport Travaux", "save": "Enregistrer", "item": "Article", "qty": "Quantité"
    }
}

st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐", ["Français", "العربية"])
T = LANG[sel_lang]

def get_sites_dict():
    session = Session()
    s = session.query(Site).all()
    session.close()
    return {x.name: (x.lat, x.lon) for x in s}

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state:
    st.title(T["login"])
    u = st.text_input(T["user"]); p = st.text_input(T["pwd"], type="password")
    if st.button("🚀 Enter"):
        access = {"admin": ("egms2025", T["role_dir"]), "magaza": ("store2025", "Store"), "safety": ("safe2025", "Safety"), "equip": ("equip2025", "Equip"), "work": ("work2025", "Work")}
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role": access[u][1]})
            st.rerun()
else:
    role = st.session_state.get("role")
    st.sidebar.write(f"👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    all_sites = get_sites_dict()

    # --- 4. واجهة المدير ---
    if role == T["role_dir"]:
        st.title(T["dash"])
        tab_map, tab_stock, tab_sites = st.tabs([T["map"], T["stock"], T["add_site"]])
        
        with tab_sites:
            st.subheader(T["add_site"])
            with st.form("site_f"):
                n = st.text_input("Site Name / اسم الموقع")
                c1, c2 = st.columns(2)
                la = c1.number_input("Lat", value=36.0, format="%.6f")
                lo = c2.number_input("Lon", value=10.0, format="%.6f")
                if st.form_submit_button(T["save"]):
                    session = Session()
                    session.add(Site(name=n, lat=la, lon=lo))
                    session.commit(); session.close(); st.success("Site Added!"); st.rerun()

        with tab_stock:
            session = Session()
            df_s = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_s.empty:
                df_s['val'] = df_s.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                summary = df_s.groupby('item').agg({'val': 'sum'}).reset_index()
                st.plotly_chart(px.bar(summary, x='item', y='val', title="Inventory Levels"), use_container_width=True)
            else: st.info("No stock data yet.")
            session.close()

        with tab_map:
            session = Session()
            df_w = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_w.empty:
                st.map(df_w, latitude='lat', longitude='lon')
                st.dataframe(df_w)
            else: st.info("No work reports (map points) yet.")
            session.close()

    # --- 5. واجهات المسؤولين ---
    elif not all_sites:
        st.warning("Admin must add a Site first! / يجب على المدير إضافة موقع أولاً")
    else:
        # واجهة تقارير العمل (لتغذية الخريطة)
        if role == "Work":
            st.header(T["report"])
            with st.form("w_f"):
                s_choice = st.selectbox("Site", list(all_sites.keys()))
                prog = st.slider("Progress %", 0, 100)
                note = st.text_area("Notes")
                if st.form_submit_button(T["save"]):
                    session = Session()
                    lat, lon = all_sites[s_choice]
                    session.add(WorkLog(site=s_choice, progress=prog, notes=note, lat=lat, lon=lon))
                    session.commit(); session.close(); st.success("Report Sent!")

        # واجهة المغازة (لتغذية المخزون)
        elif role == "Store":
            st.header(T["stock"])
            with st.form("s_f"):
                item = st.text_input(T["item"])
                qty = st.number_input(T["qty"], min_value=0.1)
                t_type = st.radio("Type", ["Entry", "Exit"])
                if st.form_submit_button(T["save"]):
                    session = Session()
                    session.add(StoreLog(item=item, qty=qty, trans_type=t_type))
                    session.commit(); session.close(); st.success("Saved!")
