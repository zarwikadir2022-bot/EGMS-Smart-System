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

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True)
    worker_name = Column(String(100)); hours = Column(Float)
    hourly_rate = Column(Float); specialization = Column(String(100))
    site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True)
    item = Column(String(100)); unit = Column(String(50)); qty = Column(Float)
    trans_type = Column(String(20)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True)
    site = Column(String(100)); progress = Column(Float); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow); lat = Column(Float); lon = Column(Float)

engine = create_engine('sqlite:///egms_final_v16.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي ---
LANG = {
    "العربية": {
        "title": "نظام EGMS الرقمي", "login": "دخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "worker_tab": "ميزانية العمالة", "stock_tab": "المخزن",
        "add_site": "إدارة المواقع", "site_name": "اسم الحضيرة", "map": "الخريطة",
        "save": "حفظ", "download": "تحميل التقرير", "archive_btn": "أرشفة ومسح البيانات",
        "confirm_msg": "أوافق على مسح البيانات", "success_arch": "تمت الأرشفة بنجاح"
    },
    "Français": {
        "title": "Système Digital EGMS", "login": "Connexion", "user": "ID", "pwd": "Pass",
        "role_dir": "Directeur", "worker_tab": "Budget RH", "stock_tab": "Stock",
        "add_site": "Gestion des Sites", "site_name": "Nom du Chantier", "map": "Carte",
        "save": "Enregistrer", "download": "Télécharger", "archive_btn": "Archiver et Réinitialiser",
        "confirm_msg": "Je confirme la suppression", "success_arch": "Archivé avec succès"
    }
}

st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐", ["Français", "العربية"])
T = LANG[sel_lang]

def get_sites():
    session = Session()
    s = session.query(Site).all()
    session.close()
    return {x.name: (x.lat, x.lon) for x in s}

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state:
    st.title(T["login"])
    u = st.text_input(T["user"]); p = st.text_input(T["pwd"], type="password")
    if st.button("🚀"):
        # صلاحيات الدخول
        access = {"admin": ("egms2025", T["role_dir"]), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store"), "work": ("work2025", "Work")}
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role": access[u][1]})
            st.rerun()
else:
    role = st.session_state.get("role")
    st.sidebar.write(f"👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    
    all_sites = get_sites()

    # --- 4. واجهة المدير (بإضافة خيار المواقع المفقود) ---
    if role == T["role_dir"]:
        st.title(f"🏗️ {T['title']}")
        # تمت إعادة تبويب إدارة المواقع هنا:
        tab_map, tab_workers, tab_stock, tab_sites = st.tabs([T["map"], T["worker_tab"], T["stock_tab"], T["add_site"]])
        
        session = Session()
        
        with tab_sites: # الجزء الذي كان مفقوداً
            st.subheader(T["add_site"])
            with st.form("site_form"):
                name = st.text_input(T["site_name"])
                c1, c2 = st.columns(2)
                la = c1.number_input("Lat", value=36.0, format="%.6f")
                lo = c2.number_input("Lon", value=10.0, format="%.6f")
                if st.form_submit_button(T["save"]):
                    session.add(Site(name=name, lat=la, lon=lo))
                    session.commit(); st.success("✅ Site Added!"); st.rerun()
            
            st.write("---")
            if all_sites:
                st.write("Current Sites / المواقع الحالية")
                st.table(pd.DataFrame([{"Site": k, "Lat": v[0], "Lon": v[1]} for k, v in all_sites.items()]))

        with tab_map:
            df_m = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_m.empty: st.map(df_m)
            else: st.info("No data for map.")

        with tab_workers:
            df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_w.empty:
                df_w['Total'] = df_w['hours'] * df_w['hourly_rate']
                st.metric("Total TND", f"{df_w['Total'].sum():,.2f}")
                st.download_button("📥 Download Payroll", data=df_w.to_csv().encode('utf-8-sig'), file_name="payroll.csv")
                st.dataframe(df_w)
            else: st.info("Empty Log")

        with tab_stock:
            df_s = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_s.empty:
                st.dataframe(df_s)
            else: st.info("Empty Stock")
        
        session.close()

    # --- 5. واجهات الموظفين ---
    elif not all_sites:
        st.warning("Admin must add a site first!")
    else:
        # مثال: واجهة مسؤول العمال
        if role == "Labor":
            st.header(T["worker_tab"])
            with st.form("l_f"):
                n = st.text_input("Worker Name")
                h = st.number_input("Hours", min_value=1.0)
                r = st.number_input("Rate", min_value=0.0)
                s = st.selectbox("Site", list(all_sites.keys()))
                if st.form_submit_button(T["save"]):
                    session = Session()
                    session.add(WorkerLog(worker_name=n, hours=h, hourly_rate=r, site=s))
                    session.commit(); session.close(); st.success("Saved!")
