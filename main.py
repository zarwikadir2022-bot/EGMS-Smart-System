import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px
from sqlalchemy.exc import IntegrityError

# --- 1. إعداد قاعدة البيانات (هيكل ثابت وموحد) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True); site = Column(String(100)); progress = Column(Float); notes = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow)

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True); worker_name = Column(String(100)); hours = Column(Float); hourly_rate = Column(Float); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True); item = Column(String(100)); unit = Column(String(50)); qty = Column(Float); trans_type = Column(String(20)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True); incident = Column(String(100)); notes = Column(Text); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class LabLog(Base):
    __tablename__ = 'lab_logs'
    id = Column(Integer, primary_key=True); test_name = Column(String(100)); result = Column(String(100)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

# محرك قاعدة البيانات - استخدام اسم جديد لضمان التحديث v41
engine = create_engine('sqlite:///egms_final_v41.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. نظام الدخول الصارم ---
st.set_page_config(page_title="EGMS Enterprise ERP", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🏗️ نظام EGMS الرقمي - تسجيل الدخول")
    user = st.text_input("اسم المستخدم")
    passwd = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        access = {
            "admin": ("egms2025", "Admin"),
            "magaza": ("store2025", "Store"),
            "labor": ("labor2025", "Labor"),
            "work": ("work2025", "Work"),
            "safety": ("safe2025", "Safety"),
            "labo": ("lab2025", "Lab")
        }
        if user in access and passwd == access[user][0]:
            st.session_state["logged_in"] = True
            st.session_state["role"] = access[user][1]
            st.rerun()
        else:
            st.error("بيانات الدخول غير صحيحة")
else:
    # --- 3. الواجهة الرئيسية بعد الدخول ---
    role = st.session_state["role"]
    st.sidebar.success(f"المستخدم: {role}")
    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.clear()
        st.rerun()
    
    session = Session()
    all_sites = [s.name for s in session.query(Site).all()]

    # --- 4. واجهة المدير (Admin) - ضمان عرض كل الجداول ---
    if role == "Admin":
        st.title("💼 لوحة تحكم المدير العام")
        tabs = st.tabs(["📍 الخارطة", "🏗️ الأشغال", "👷 العمال", "📦 المخزن", "🛡️ السلامة & المختبر", "⚙️ الإعدادات"])

        with tabs[0]: # الخارطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')
            else: st.info("لا توجد مواقع.")

        with tabs[1]: # الأشغال
            st.subheader("🏗️ تقارير سير الأشغال")
            df_work = pd.read_sql(session.query(WorkLog).statement, session.bind)
            st.dataframe(df_work, use_container_width=True)

        with tabs[2]: # العمال
            st.subheader("👷 سجل العمال والرواتب")
            df_labor = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_labor.empty:
                df_labor['التكلفة'] = df_labor['hours'] * df_labor['hourly_rate']
                st.dataframe(df_labor, use_container_width=True)
                st.metric("إجمالي الرواتب", f"{df_labor['التكلفة'].sum()} TND")

        with tabs[3]: # المخزن
            st.subheader("📦 رصيد المخزن")
            df_store = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_store.empty:
                df_store['net'] = df_store.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                st.table(df_store.groupby(['item', 'unit'])['net'].sum().reset_index())
                st.dataframe(df_store)

        with tabs[4]: # سلامة ومختبر
            st.write("تقارير السلامة:")
            st.dataframe(pd.read_sql(session.query(SafetyLog).statement, session.bind))
            st.write("تقارير المختبر:")
            st.dataframe(pd.read_sql(session.query(LabLog).statement, session.bind))

        with tabs[5]: # الإعدادات
            st.subheader("⚙️ إدارة المواقع")
            with st.form("add_site"):
                n = st.text_input("اسم الموقع"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("إضافة"):
                    try:
                        session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
                    except: session.rollback(); st.error("الموقع موجود مسبقاً")
            
            if all_sites:
                s_del = st.selectbox("حذف موقع", all_sites)
                if st.button("حذف نهائي"):
                    session.query(Site).filter_by(name=s_del).delete(); session.commit(); st.rerun()

    # --- 5. واجهات المسؤولين (ضمان عدم الاختفاء) ---
    elif not all_sites:
        st.warning("⚠️ يرجى من المدير إضافة مواقع أولاً.")
    
    elif role == "Work":
        st.header("🏗️ واجهة الأشغال")
        with st.form("w"):
            s = st.selectbox("الموقع", all_sites); p = st.slider("%", 0, 100); n = st.text_area("ملاحظات")
            if st.form_submit_button("إرسال"):
                session.add(WorkLog(site=s, progress=p, notes=n)); session.commit(); st.success("✅")

    elif role == "Store":
        st.header("📦 واجهة المخزن")
        with st.form("s"):
            i = st.text_input("المادة"); u = st.selectbox("الوحدة", ["كغ", "طن", "كيس"]); q = st.number_input("الكمية")
            t = st.radio("النوع", ["Entry", "Exit"]); s = st.selectbox("الموقع", all_sites)
            if st.form_submit_button("حفظ"):
                session.add(StoreLog(item=i, unit=u, qty=q, trans_type=t, site=s)); session.commit(); st.success("✅")

    elif role == "Labor":
        st.header("👷 واجهة العمال")
        with st.form("l"):
            nm = st.text_input("الاسم"); h = st.number_input("ساعات"); r = st.number_input("سعر"); s = st.selectbox("الموقع", all_sites)
            if st.form_submit_button("حفظ"):
                session.add(WorkerLog(worker_name=nm, hours=h, hourly_rate=r, site=s)); session.commit(); st.success("✅")

    session.close()
