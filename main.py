import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import plotly.express as px
from sqlalchemy.exc import IntegrityError

# --- 1. الإعدادات الجمالية والهوية البصرية ---
st.set_page_config(page_title="EGMS Ultimate ERP v45", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    div.stMetric { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 5px solid #004a99; }
    .stButton>button { border-radius: 10px; height: 3em; background-color: #004a99; color: white; font-weight: bold; width: 100%; transition: 0.3s; }
    .main-header { text-align: center; padding: 20px; background: white; border-radius: 15px; margin-bottom: 25px; border-bottom: 4px solid #004a99; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. هيكلة قاعدة البيانات المتطورة ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)

class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); hourly_rate = Column(Float); work_plan = Column(Text); specialization = Column(String(100))
    logs = relationship("WorkerLog", back_populates="profile")

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True); worker_id = Column(Integer, ForeignKey('worker_profiles.id')); hours = Column(Float); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)
    profile = relationship("WorkerProfile", back_populates="logs")

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True); item = Column(String(100)); unit = Column(String(50)); qty = Column(Float); trans_type = Column(String(20)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True); site = Column(String(100)); progress = Column(Float); notes = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow)

# محرك القاعدة v45
engine = create_engine('sqlite:///egms_final_v45.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 3. نظام الدخول والحماية ---
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.markdown("<div class='main-header'><h1>🏗️ EGMS DIGITAL ERP</h1><p>الإصدار البلاتيني الموحد v45</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        u = st.text_input("User"); p = st.text_input("Pass", type="password")
        if st.button("LOGIN"):
            acc = {"admin": ("egms2025", "Admin"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store"), "work": ("work2025", "Work")}
            if u in acc and p == acc[u][0]:
                st.session_state.update({"logged_in": True, "role": acc[u][1]}); st.rerun()
            else: st.error("Invalid Credentials")
else:
    role = st.session_state["role"]
    st.sidebar.markdown(f"### 👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    
    session = Session()
    all_sites = {x.name: (x.lat, x.lon) for x in session.query(Site).all()}

    # --- 4. واجهة المدير العام (Admin Hub) ---
    if role == "Admin":
        st.markdown("<div class='main-header'><h2>📊 لوحة تحكم القيادة والتحليل</h2></div>", unsafe_allow_html=True)
        
        # 1. جلب البيانات للتحليل
        df_labor_logs = pd.read_sql(session.query(WorkerLog).statement, session.bind)
        df_profiles = pd.read_sql(session.query(WorkerProfile).statement, session.bind)
        df_progress = pd.read_sql(session.query(WorkLog).statement, session.bind)
        
        # 2. البطاقات الإحصائية
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("عدد المواقع", len(all_sites))
        
        total_payroll = 0
        if not df_labor_logs.empty:
            merged = pd.merge(df_labor_logs, df_profiles, left_on='worker_id', right_on='id')
            total_payroll = (merged['hours'] * merged['hourly_rate']).sum()
        m2.metric("إجمالي الرواتب", f"{total_payroll:,.0f} TND")
        
        avg_prog = df_progress['progress'].mean() if not df_progress.empty else 0
        m3.metric("متوسط الإنجاز", f"{avg_prog:.1f}%")
        m4.metric("حالة النظام", "نشط ✅")

        tabs = st.tabs(["📍 الخريطة", "👷 إدارة العمال (HR)", "📦 المخزون", "🏗️ سير الأشغال", "⚙️ الإعدادات"])

        with tabs[0]: # الخريطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')

        with tabs[1]: # HR المتقدم
            st.subheader("إدارة ملفات العمال (Profile Management)")
            with st.form("add_worker"):
                col_a, col_b = st.columns(2)
                wn = col_a.text_input("اسم العامل الجديد")
                wr = col_b.number_input("سعر الساعة (TND)")
                wp = st.text_area("خطة العمل والمهام")
                if st.form_submit_button("حفظ الملف الشخصي"):
                    try:
                        session.add(WorkerProfile(name=wn, hourly_rate=wr, work_plan=wp))
                        session.commit(); st.success("تم الحفظ"); st.rerun()
                    except: session.rollback(); st.error("الاسم موجود مسبقاً")
            st.write("العمال المسجلون:")
            st.dataframe(df_profiles, use_container_width=True)

        with tabs[2]: # المخزن
            st.subheader("📦 رصيد المواد المتاح")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                df_st['net'] = df_st.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                st.table(df_st.groupby(['item', 'unit'])['net'].sum().reset_index().rename(columns={'net':'الكمية'}))

        with tabs[4]: # الإعدادات وتصدير البيانات
            st.subheader("⚙️ إعدادات النظام")
            if st.button("📥 تحميل كافة البيانات (Excel)"):
                st.info("هذه الميزة ستقوم بتصدير الجداول للتحليل الخارجي")
                st.download_button("تحميل سجل العمال", df_labor_logs.to_csv(), "workers.csv")
                st.download_button("تحميل سجل الأشغال", df_progress.to_csv(), "progress.csv")

    # --- 5. واجهة مسؤول العمال (Labor) ---
    elif role == "Labor":
        st.header("👷 تسجيل ساعات العمل اليومية")
        profiles = session.query(WorkerProfile).all()
        if not profiles: st.warning("يجب على المدير تسجيل العمال أولاً.")
        else:
            with st.form("l_log"):
                w_choice = st.selectbox("اسم العامل", [p.name for p in profiles])
                h = st.number_input("الساعات", min_value=0.5)
                s = st.selectbox("الموقع", list(all_sites.keys()))
                if st.form_submit_button("تسجيل"):
                    p_obj = session.query(WorkerProfile).filter_by(name=w_choice).first()
                    session.add(WorkerLog(worker_id=p_obj.id, hours=h, site=s))
                    session.commit(); st.success("✅ تم التسجيل")

    # --- 6. واجهة مسؤول المغازة (Store) ---
    elif role == "Store":
        st.header("📦 إدارة المغازة")
        with st.form("st_f"):
            item = st.text_input("المادة"); unit = st.selectbox("الوحدة", ["كيس", "طن", "كغ", "متر"])
            qty = st.number_input("الكمية"); t = st.radio("العملية", ["Entry", "Exit"])
            s = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session.add(StoreLog(item=item, unit=unit, qty=qty, trans_type=t, site=s))
                session.commit(); st.success("✅")

    # --- 7. واجهة مسؤول الأشغال (Work) ---
    elif role == "Work":
        st.header("🏗️ تقرير الإنجاز الميداني")
        with st.form("wk_f"):
            s = st.selectbox("الموقع", list(all_sites.keys()))
            p = st.slider("% الإنجاز", 0, 100); n = st.text_area("ملاحظات")
            if st.form_submit_button("إرسال"):
                session.add(WorkLog(site=s, progress=p, notes=n))
                session.commit(); st.success("✅")

    session.close()
