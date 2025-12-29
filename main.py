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

engine = create_engine('sqlite:///egms_final_v15.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. القاموس اللغوي (تم تصحيح الفصلة هنا) ---
LANG = {
    "العربية": {
        "title": "نظام EGMS الرقمي", 
        "login": "دخول", 
        "user": "المستخدم", 
        "pwd": "الرمز",
        "role_dir": "المدير العام", 
        "worker_tab": "ميزانية العمالة", 
        "stock_tab": "المخزن",
        "download": "تحميل التقرير قبل المسح", 
        "archive_btn": "أرشفة ومسح البيانات نهائياً",
        "confirm_msg": "أوافق على مسح كافة البيانات المسجلة", 
        "success_arch": "تمت أرشفة البيانات وتصفير السجل بنجاح"
    },
    "Français": {
        "title": "Système Digital EGMS", 
        "login": "Connexion", 
        "user": "ID", 
        "pwd": "Pass",
        "role_dir": "Directeur", 
        "worker_tab": "Budget RH", 
        "stock_tab": "Stock",
        "download": "Télécharger avant suppression", 
        "archive_btn": "Archiver et Réinitialiser",
        "confirm_msg": "Je confirme la suppression définitive", 
        "success_arch": "Données archivées avec succès"
    }
}

st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐", ["Français", "العربية"])
T = LANG[sel_lang]

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state:
    st.title(T["login"])
    u = st.text_input(T["user"])
    p = st.text_input(T["pwd"], type="password")
    if st.button("🚀"):
        if u == "admin" and p == "egms2025":
            st.session_state.update({"logged_in": True, "role": T["role_dir"]})
            st.rerun()
else:
    role = st.session_state.get("role")
    st.sidebar.write(f"👤 {role}")
    if st.sidebar.button("Logout"): 
        st.session_state.clear()
        st.rerun()

    # --- 4. واجهة المدير ---
    if role == T["role_dir"]:
        st.title(f"🏗️ {T['title']}")
        tab_workers, tab_stock = st.tabs([T["worker_tab"], T["stock_tab"]])
        
        session = Session()
        
        with tab_workers:
            df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_w.empty:
                df_w['Total'] = df_w['hours'] * df_w['hourly_rate']
                st.metric("إجمالي الرواتب", f"{df_w['Total'].sum():,.2f} TND")
                
                csv = df_w.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label=f"📥 {T['download']}", data=csv, file_name="payroll_backup.csv", mime="text/csv")
                
                st.divider()
                st.warning("⚠️ منطقة خطرة: مسح البيانات لا يمكن الرجوع عنه")
                confirm = st.checkbox(T["confirm_msg"])
                if st.button(T["archive_btn"], disabled=not confirm):
                    session.query(WorkerLog).delete()
                    session.commit()
                    st.success(T["success_arch"])
                    st.rerun()
                
                st.dataframe(df_w, use_container_width=True)
            else: 
                st.info("السجل فارغ حالياً")

        with tab_stock:
            df_s = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_s.empty:
                csv_s = df_s.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 تحميل سجل المخزن", data=csv_s, file_name="stock_backup.csv")
                
                if st.checkbox("تأكيد مسح سجل المخزن"):
                    if st.button("تصفير المخزن"):
                        session.query(StoreLog).delete()
                        session.commit()
                        st.rerun()
                st.dataframe(df_s, use_container_width=True)
            else:
                st.info("المخزن فارغ")
        
        session.close()
