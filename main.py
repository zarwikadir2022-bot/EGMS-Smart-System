import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px
from sqlalchemy.exc import IntegrityError

# --- 1. الإعدادات الجمالية (Custom CSS) ---
st.set_page_config(page_title="EGMS Professional ERP", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. هيكلة قاعدة البيانات (v34) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True); name = Column(String(100)); hours = Column(Float); rate = Column(Float); spec = Column(String(50)); site = Column(String(100)); date = Column(DateTime, default=datetime.utcnow)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True); item = Column(String(100)); unit = Column(String(50)); qty = Column(Float); type = Column(String(20)); site = Column(String(100)); date = Column(DateTime, default=datetime.utcnow)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True); site = Column(String(100)); progress = Column(Float); notes = Column(Text); date = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_pro_v34.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 3. محرك الأمان والدخول ---
if "logged_in" not in st.session_state:
    st.title("🏗️ EGMS Digital Portal")
    with st.container():
        u = st.text_input("Username"); p = st.text_input("Password", type="password")
        if st.button("Sign In"):
            access = {"admin": ("egms2025", "Admin"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store"), "work": ("work2025", "Work")}
            if u in access and p == access[u][0]:
                st.session_state.update({"logged_in": True, "role": access[u][1]}); st.rerun()
else:
    role = st.session_state.get("role")
    st.sidebar.markdown(f"### 👤 {role}")
    if st.sidebar.button("Log Out"): st.session_state.clear(); st.rerun()
    
    session = Session()
    all_sites = {x.name: (x.lat, x.lon) for x in session.query(Site).all()}

    # --- 4. لوحة تحكم المدير (الاحترافية) ---
    if role == "Admin":
        st.title("💼 EGMS Executive Dashboard")
        t1, t2, t3, t4, t5 = st.tabs(["📍 الخريطة", "👷 الموارد البشرية", "📦 المخازن", "🏗️ سير الأشغال", "⚙️ الإعدادات"])

        with t1: # الخريطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')

        with t2: # العمال
            st.subheader("تحليل القوى العاملة")
            df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_w.empty:
                df_w['cost'] = df_w['hours'] * df_w['rate']
                c1, c2 = st.columns([1, 2])
                c1.metric("إجمالي الرواتب", f"{df_w['cost'].sum():,.2f} TND")
                c2.plotly_chart(px.bar(df_w, x='name', y='cost', color='site', title="تكلفة العمال حسب الموقع"), use_container_width=True)
                st.dataframe(df_w, use_container_width=True)

        with t3: # المخزن (حساب الرصيد التلقائي)
            st.subheader("إدارة المخزون الذكي")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                # منطق حساب الرصيد (الداخل - الخارج)
                df_st['actual_qty'] = df_st.apply(lambda x: x['qty'] if x['type'] == "Entry" else -x['qty'], axis=1)
                balance = df_st.groupby(['item', 'unit'])['actual_qty'].sum().reset_index()
                st.table(balance.rename(columns={'actual_qty': 'الرصيد المتاح'}))
                st.dataframe(df_st)

        with t4: # الأشغال
            st.subheader("متابعة الإنجاز الميداني")
            df_work = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_work.empty:
                fig = px.line(df_work, x='date', y='progress', color='site', title="منحنى تقدم الأشغال")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_work)

        with t5: # الإعدادات
            with st.form("site_f"):
                n = st.text_input("اسم الحضيرة"); la = st.number_input("Lat", value=36.5); lo = st.number_input("Lon", value=10.2)
                if st.form_submit_button("إضافة الموقع"):
                    try: session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
                    except: session.rollback(); st.error("خطأ")

    # --- 5. واجهة المغازة ---
    elif role == "Store":
        st.header("📦 إدارة المخزون والمواد")
        with st.form("st"):
            item = st.text_input("المادة"); unit = st.selectbox("الوحدة", ["كغ", "طن", "كيس", "لتر", "قطعة"])
            qty = st.number_input("الكمية", min_value=0.1); t_type = st.radio("العملية", ["Entry", "Exit"])
            s = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session.add(StoreLog(item=item, unit=unit, qty=qty, type=t_type, site=s))
                session.commit(); st.success("✅ تم التحديث")

    # --- 6. واجهة العمال ---
    elif role == "Labor":
        st.header("👷 تسجيل بيانات العمال")
        with st.form("lb"):
            name = st.text_input("اسم العامل"); h = st.number_input("الساعات"); r = st.number_input("السعر")
            spec = st.selectbox("التخصص", ["بناء", "مساعد", "فني"])
            s = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session.add(WorkerLog(name=name, hours=h, rate=r, spec=spec, site=s))
                session.commit(); st.success("✅")

    # --- 7. واجهة الأشغال ---
    elif role == "Work":
        st.header("🏗️ تحديث سير الأشغال")
        with st.form("wk"):
            s = st.selectbox("الموقع", list(all_sites.keys())); prog = st.slider("%", 0, 100); n = st.text_area("Notes")
            if st.form_submit_button("إرسال التقرير"):
                session.add(WorkLog(site=s, progress=prog, notes=n))
                session.commit(); st.success("✅")

    session.close()
