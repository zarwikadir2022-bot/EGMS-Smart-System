import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import plotly.express as px
from sqlalchemy.exc import IntegrityError

# --- 1. التنسيق الجمالي الاحترافي (Advanced CSS) ---
st.set_page_config(page_title="EGMS Platinum ERP", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #004a99; }
    div.stMetric { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-top: 5px solid #004a99; }
    .stButton>button { border-radius: 10px; height: 3em; background-color: #004a99; color: white; font-weight: bold; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #003366; transform: translateY(-2px); }
    .main-header { font-family: 'Arial'; color: #1a1a1a; text-align: center; padding: 20px; background: white; border-radius: 15px; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك قاعدة البيانات المتكامل ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True); site = Column(String(100)); progress = Column(Float); notes = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow)

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True); name = Column(String(100)); hours = Column(Float); rate = Column(Float); spec = Column(String(50)); site = Column(String(100)); date = Column(DateTime, default=datetime.utcnow)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True); item = Column(String(100)); unit = Column(String(50)); qty = Column(Float); type = Column(String(20)); site = Column(String(100)); date = Column(DateTime, default=datetime.utcnow)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True); incident = Column(String(100)); notes = Column(Text); site = Column(String(100)); date = Column(DateTime, default=datetime.utcnow)

class LabLog(Base):
    __tablename__ = 'lab_logs'
    id = Column(Integer, primary_key=True); test = Column(String(100)); res = Column(String(100)); site = Column(String(100)); date = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_platinum_v43.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 3. نظام الدخول المتعدد ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.markdown("<div class='main-header'><h1>🏗️ EGMS ENTERPRISE PORTAL</h1><p>نظام الإدارة الرقمية المتكامل لشركات المقاولات</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("LOGIN"):
                acc = {"admin": ("egms2025", "Admin"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store"), "work": ("work2025", "Work"), "safety": ("safe2025", "Safety"), "labo": ("lab2025", "Lab")}
                if u in acc and p == acc[u][0]:
                    st.session_state.update({"logged_in": True, "role": acc[u][1]}); st.rerun()
                else: st.error("⚠️ Invalid Credentials")
else:
    role = st.session_state["role"]
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/4333/4333609.png", width=100) # شعار الشركة الافتراضي
    st.sidebar.markdown(f"### 👤 {role}")
    if st.sidebar.button("LOGOUT"): st.session_state.clear(); st.rerun()
    
    session = Session()
    all_sites = {x.name: (x.lat, x.lon) for x in session.query(Site).all()}

    # --- 4. واجهة المدير العام (Admin Dashboard) ---
    if role == "Admin":
        st.markdown("<div class='main-header'><h2>📊 Executive Dashboard</h2></div>", unsafe_allow_html=True)
        
        # مؤشرات الأداء (Top Cards)
        df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
        df_p = pd.read_sql(session.query(WorkLog).statement, session.bind)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("عدد المواقع", len(all_sites))
        c2.metric("إجمالي الرواتب", f"{(df_w['hours'] * df_w['rate']).sum():,.0f} TND" if not df_w.empty else "0")
        c3.metric("متوسط الإنجاز", f"{df_p['progress'].mean():.1f}%" if not df_p.empty else "0%")
        c4.metric("حالة الخوادم", "Online ✅")

        tabs = st.tabs(["📍 الخريطة", "👷 الموارد البشرية", "📦 المخازن", "🏗️ تقارير الأشغال", "🛡️ السلامة & المختبر", "⚙️ الإعدادات"])

        with tabs[0]:
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')

        with tabs[1]: # تحليل العمال
            if not df_w.empty:
                df_w['cost'] = df_w['hours'] * df_w['rate']
                fig = px.bar(df_w, x='name', y='cost', color='site', title="تحليل تكاليف العمال")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_w, use_container_width=True)

        with tabs[2]: # المخزن الذكي
            st.subheader("📦 رصيد المواد المتوفر")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                df_st['net'] = df_st.apply(lambda x: x['qty'] if x['type'] == "Entry" else -x['qty'], axis=1)
                st.table(df_st.groupby(['item', 'unit'])['net'].sum().reset_index())
                st.dataframe(df_st)

        with tabs[3]: # الأشغال
            df_work = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_work.empty: st.dataframe(df_work, use_container_width=True)

        with tabs[5]: # الإعدادات
            with st.form("site_f"):
                n = st.text_input("اسم الحضيرة"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("إضافة"):
                    try: session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
                    except: session.rollback(); st.error("Exists!")

    # --- 5. واجهات المسؤولين الستة (ضمان عدم التعارض) ---
    elif not all_sites: st.warning("⚠️ يجب إضافة مواقع أولاً.")
    
    elif role == "Store":
        st.header("📦 بوابة إدارة المخازن")
        with st.form("s"):
            i = st.text_input("اسم المادة"); u = st.selectbox("وحدة القيس", ["كغ", "طن", "كيس", "لتر", "متر"])
            q = st.number_input("الكمية"); ty = st.radio("نوع العملية", ["Entry", "Exit"]); s = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session.add(StoreLog(item=i, unit=u, qty=q, type=ty, site=s)); session.commit(); st.success("✅")

    elif role == "Labor":
        st.header("👷 بوابة الموارد البشرية")
        with st.form("l"):
            nm = st.text_input("اسم العامل"); h = st.number_input("الساعات"); r = st.number_input("السعر"); s = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session.add(WorkerLog(name=nm, hours=h, rate=r, site=s)); session.commit(); st.success("✅")

    elif role == "Work":
        st.header("🏗️ بوابة تقارير الأشغال")
        with st.form("w"):
            s = st.selectbox("الموقع", list(all_sites.keys())); p = st.slider("% الإنجاز", 0, 100); n = st.text_area("ملاحظات")
            if st.form_submit_button("إرسال"):
                session.add(WorkLog(site=s, progress=p, notes=n)); session.commit(); st.success("✅")

    session.close()
