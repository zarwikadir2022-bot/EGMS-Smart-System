import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px
from sqlalchemy.exc import IntegrityError

# --- 1. إعداد قاعدة البيانات الشاملة ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True); site = Column(String(100)); progress = Column(Float); notes = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow); lat = Column(Float); lon = Column(Float)

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
    id = Column(Integer, primary_key=True); test_name = Column(String(100)); result = Column(String(100)); status = Column(String(50)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

# محرك قاعدة البيانات - نسخة v40
engine = create_engine('sqlite:///egms_final_v40.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. واجهة الدخول ---
st.set_page_config(page_title="EGMS Enterprise v40", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.title("🏗️ نظام EGMS الرقمي - تسجيل الدخول")
    u = st.text_input("اسم المستخدم")
    p = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        access = {
            "admin": ("egms2025", "Admin"),
            "magaza": ("store2025", "Store"),
            "labor": ("labor2025", "Labor"),
            "work": ("work2025", "Work"),
            "safety": ("safe2025", "Safety"),
            "labo": ("lab2025", "Lab")
        }
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role": access[u][1]})
            st.rerun()
        else: st.error("⚠️ خطأ في البيانات")
else:
    role = st.session_state.get("role")
    st.sidebar.markdown(f"### 👤 المستخدم: {role}")
    if st.sidebar.button("خروج"):
        st.session_state.clear(); st.rerun()
    
    session = Session()
    all_sites = [s.name for s in session.query(Site).all()]

    # --- 3. واجهة المدير (Admin) ---
    if role == "Admin":
        st.title("💼 لوحة تحكم المدير العام")
        t = st.tabs(["📍 الخارطة", "🏗️ الأشغال", "👷 العمال", "📦 المخزن", "🛡️ السلامة & المختبر", "⚙️ الإعدادات"])

        with t[0]: # الخارطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')
            else: st.info("لا توجد مواقع مضافة.")

        with t[1]: # الأشغال
            df_work = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_work.empty: st.dataframe(df_work.sort_values(by='timestamp', ascending=False), use_container_width=True)
            else: st.info("لا توجد تقارير.")

        with t[2]: # العمال
            df_labor = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_labor.empty:
                df_labor['التكلفة'] = df_labor['hours'] * df_labor['hourly_rate']
                st.dataframe(df_labor, use_container_width=True)
                st.metric("إجمالي ميزانية الرواتب", f"{df_labor['التكلفة'].sum():,.2f} TND")

        with t[3]: # المخزن
            df_store = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_store.empty:
                df_store['net'] = df_store.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                st.table(df_store.groupby(['item', 'unit'])['net'].sum().reset_index())

        with t[5]: # الإعدادات (تصحيح الخطأ 105 ✅)
            st.subheader("⚙️ إدارة الحضائر")
            with st.form("site_add"):
                n = st.text_input("اسم الحضيرة")
                if st.form_submit_button("حفظ"):
                    try:
                        session.add(Site(name=n, lat=36.0, lon=10.0)); session.commit(); st.rerun()
                    except: st.error("موجود مسبقاً")
            
            if all_sites:
                s_to_del = st.selectbox("حذف موقع", all_sites)
                if st.button("تأكيد الحذف"):
                    session.query(Site).filter_by(name=s_to_del).delete()
                    session.commit(); st.rerun()
            else:
                st.info("لا توجد مواقع مسجلة حالياً.")

    # --- 4. واجهات المسؤولين ---
    elif not all_sites:
        st.warning("⚠️ يرجى إضافة مواقع من حساب المدير أولاً.")
    
    elif role == "Work":
        st.header("🏗️ تقرير الأشغال")
        with st.form("w_f"):
            s = st.selectbox("الموقع", all_sites); p = st.slider("%", 0, 100); n = st.text_area("ملاحظات")
            if st.form_submit_button("إرسال"):
                session.add(WorkLog(site=s, progress=p, notes=n)); session.commit(); st.success("✅")

    elif role == "Store":
        st.header("📦 المغازة")
        with st.form("s_f"):
            i = st.text_input("المادة"); u = st.selectbox("الوحدة", ["كغ", "طن", "كيس"]); q = st.number_input("الكمية")
            t_t = st.radio("العملية", ["Entry", "Exit"]); s = st.selectbox("الموقع", all_sites)
            if st.form_submit_button("حفظ"):
                session.add(StoreLog(item=i, unit=u, qty=q, trans_type=t_t, site=s)); session.commit(); st.success("✅")

    elif role == "Labor":
        st.header("👷 العمال")
        with st.form("l_f"):
            nm = st.text_input("الاسم"); h = st.number_input("ساعات"); r = st.number_input("سعر الساعة"); s = st.selectbox("الموقع", all_sites)
            if st.form_submit_button("حفظ"):
                session.add(WorkerLog(worker_name=nm, hours=h, hourly_rate=r, site=s)); session.commit(); st.success("✅")

    session.close()
