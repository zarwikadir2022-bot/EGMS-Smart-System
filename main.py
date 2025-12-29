import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px # مكتبة الرسوم البيانية

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
    item = Column(String(100)); unit = Column(String(50)); qty = Column(Float)
    price = Column(Float); trans_type = Column(String(20)); site = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow); user_name = Column(String(50))

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True)
    incident = Column(String(100)); notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow); user_name = Column(String(50))

engine = create_engine('sqlite:///egms_final_v6.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

SITES_DATA = {
    "Fouchana (فوشانة)": (36.6897, 10.1244),
    "Sousse (سوسة)": (35.8256, 10.6084),
    "Sfax (صفاقس)": (34.7406, 10.7603),
    "Bizerte (بنزرت)": (37.2744, 9.8739)
}

# --- 2. القاموس اللغوي ---
LANG = {
    "العربية": {
        "title": "نظام EGMS الذكي", "login": "دخول", "user": "المستخدم", "pwd": "الرمز",
        "role_dir": "المدير العام", "role_store": "مسؤول المغازة", "role_safety": "مسؤول السلامة",
        "store_tab": "إدارة المخزن", "safety_tab": "الأمن", "dash": "لوحة التحكم",
        "site": "الموقع", "save": "حفظ", "item": "المادة", "qty": "الكمية", "unit": "الوحدة",
        "price": "السعر", "total": "الرصيد المتوفر", "chart_title": "مخطط استهلاك المواد",
        "in": "دخول", "out": "خروج", "map": "الخريطة"
    },
    "Français": {
        "title": "Système Intelligent EGMS", "login": "Login", "user": "Identifiant", "pwd": "Pass",
        "role_dir": "Directeur", "role_store": "Magasinier", "role_safety": "Sécurité",
        "store_tab": "Stock", "safety_tab": "Sécurité", "dash": "Dashboard",
        "site": "Site", "save": "Enregistrer", "item": "Article", "qty": "Quantité", "unit": "Unité",
        "price": "Prix", "total": "Stock Actuel", "chart_title": "Analyse de Consommation",
        "in": "Entrée", "out": "Sortie", "map": "Cartographie"
    }
}

st.set_page_config(page_title="EGMS Smart System", layout="wide")
sel_lang = st.sidebar.selectbox("🌐", ["Français", "العربية"])
T = LANG[sel_lang]

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state:
    st.title(T["login"])
    u = st.text_input(T["user"]); p = st.text_input(T["pwd"], type="password")
    if st.button("🚀"):
        access = {"admin": ("egms2025", T["role_dir"]), "magaza": ("store2025", T["role_store"]), "safety": ("safe2025", T["role_safety"])}
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role": access[u][1], "user_id": u})
            st.rerun()
else:
    role = st.session_state.get("role")
    st.sidebar.write(f"👤 {role}")
    if st.sidebar.button("Logout"):
        st.session_state.clear(); st.rerun()

    # --- 4. واجهة المدير (مع الرسوم البيانية) ---
    if role == T["role_dir"]:
        tab_map, tab_stock, tab_safe = st.tabs([T["map"], T["store_tab"], T["safety_tab"]])
        session = Session()
        
        with tab_stock:
            df_s = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_s.empty:
                # منطق الحساب
                df_s['val'] = df_s.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                summary = df_s.groupby(['item', 'unit']).agg({'val': 'sum'}).reset_index()
                summary.columns = [T["item"], T["unit"], T["total"]]
                
                # --- الرسوم البيانية التفاعلية ---
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.subheader(T["chart_title"])
                    fig = px.bar(summary, x=T["item"], y=T["total"], color=T["item"], 
                                 title=T["total"] + " (Bar Chart)")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_chart2:
                    st.subheader("Distribution / التوزيع")
                    fig2 = px.pie(summary, names=T["item"], values=T["total"], hole=0.3)
                    st.plotly_chart(fig2, use_container_width=True)

                st.dataframe(summary, use_container_width=True)
            else:
                st.info("No data.")

        with tab_map:
            df_w = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_w.empty: st.map(df_w, latitude='lat', longitude='lon', size='progress')
            
        with tab_safe:
            df_safe = pd.read_sql(session.query(SafetyLog).statement, session.bind)
            st.warning("⚠️")
            st.table(df_safe)
        session.close()

    # --- 5. واجهة مسؤول المغازة ---
    elif role == T["role_store"]:
        st.header(T["store_tab"])
        with st.form("stock"):
            col1, col2 = st.columns(2)
            with col1:
                item = st.text_input(T["item"])
                qty = st.number_input(T["qty"], min_value=0.0)
                unit = st.selectbox(T["unit"], ["Kg", "Ton", "Sacs", "Mètres", "Pièces"])
            with col2:
                price = st.number_input(T["price"], min_value=0.0)
                t_type = st.radio("Mouvement", [T["in"], T["out"]])
                site = st.selectbox(T["site"], list(SITES_DATA.keys()))
            
            if st.form_submit_button(T["save"]):
                final_type = "Entry" if t_type == T["in"] else "Exit"
                session = Session()
                new_item = StoreLog(item=item, unit=unit, qty=qty, price=price, trans_type=final_type, site=site, user_name=st.session_state["user_id"])
                session.add(new_item); session.commit(); session.close()
                st.success("✅")

    elif role == T["role_safety"]:
        st.header(T["safety_tab"]); # كود السلامة كما هو
