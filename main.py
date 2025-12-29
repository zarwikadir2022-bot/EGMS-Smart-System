import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import plotly.express as px
from sqlalchemy.exc import IntegrityError

# --- 1. إعداد قاعدة البيانات ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True); site = Column(String(100)); progress = Column(Float); notes = Column(Text); timestamp = Column(DateTime, default=datetime.utcnow); lat = Column(Float); lon = Column(Float)

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True); worker_name = Column(String(100)); hours = Column(Float); hourly_rate = Column(Float); specialization = Column(String(100)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True); item = Column(String(100)); qty = Column(Float); trans_type = Column(String(20)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True); incident = Column(String(100)); notes = Column(Text); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class LabLog(Base):
    __tablename__ = 'lab_logs'
    id = Column(Integer, primary_key=True); test_name = Column(String(100)); result = Column(String(100)); status = Column(String(50)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_final_v31.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. الإعدادات ---
st.set_page_config(page_title="EGMS Enterprise ERP", layout="wide")
sel_lang = st.sidebar.selectbox("🌐 Language", ["العربية", "Français"])

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state:
    st.title("🏗️ EGMS Digital ERP v31")
    u = st.text_input("User"); p = st.text_input("Pass", type="password")
    if st.button("🚀 Login"):
        access = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store"), "safety": ("safe2025", "Safety"), "labo": ("lab2025", "Lab")}
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role_id": access[u][1]}); st.rerun()
        else: st.error("خطأ!")
else:
    role_id = st.session_state.get("role_id")
    st.sidebar.success(f"Role: {role_id}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    
    session = Session()
    all_sites = {x.name: (x.lat, x.lon) for x in session.query(Site).all()}

    # --- 4. واجهة المدير (Admin) ---
    if role_id == "Admin":
        st.title("📊 لوحة التحكم المركزية")
        # تمت إضافة تبويب الخريطة هنا في البداية
        tabs = st.tabs(["📍 الخريطة", "🏆 لوحة الشرف", "🔮 التوقعات", "👷 العمال", "📦 المخزن", "🛡️ السلامة & المختبر", "⚙️ الإعدادات"])

        with tabs[0]: # تبويب الخريطة
            st.subheader("خريطة الحضائر والمواقع")
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty:
                st.map(df_s, latitude='lat', longitude='lon')
                st.dataframe(df_s[['name', 'lat', 'lon']], use_container_width=True)
            else: st.info("الخريطة فارغة. أضف مواقع من تبويب الإعدادات.")

        with tabs[1]: # لوحة الشرف
            st.header("🏆 التميز والإنتاجية")
            c1, c2 = st.columns(2)
            df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_w.empty:
                top_w = df_w.groupby('worker_name')['hours'].sum().idxmax()
                with c1: st.metric("أنشط عامل", top_w, f"{df_w.groupby('worker_name')['hours'].sum().max()} ساعة")
            df_p = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_p.empty:
                best_s = df_p.groupby('site')['progress'].max().idxmax()
                with c2: st.metric("أفضل حضيرة إنجازاً", best_s)

        with tabs[2]: # التوقعات
            st.header("🔮 الذكاء الزمني")
            if not df_p.empty:
                df_p['timestamp'] = pd.to_datetime(df_p['timestamp'])
                for s_name in df_p['site'].unique():
                    data = df_p[df_p['site'] == s_name].sort_values('timestamp')
                    if len(data) >= 2:
                        days = (data['timestamp'].iloc[-1] - data['timestamp'].iloc[0]).days or 1
                        speed = data['progress'].iloc[-1] / days
                        if speed > 0:
                            rem = (100 - data['progress'].iloc[-1]) / speed
                            finish = datetime.now() + timedelta(days=int(rem))
                            st.success(f"📍 **{s_name}**: التسليم المتوقع في **{finish.date()}**")

        with tabs[3]: # العمال
            st.subheader("سجل الموارد البشرية")
            if not df_w.empty:
                df_w['cost'] = df_w['hours'] * df_w['hourly_rate']
                st.dataframe(df_w, use_container_width=True)
                st.plotly_chart(px.bar(df_w, x='worker_name', y='cost', color='site'))

        with tabs[4]: # المخزن
            st.subheader("سجل تحركات السلع")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            st.dataframe(df_st, use_container_width=True)

        with tabs[5]: # السلامة والمختبر
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("🛡️ السلامة")
                st.table(pd.read_sql(session.query(SafetyLog).statement, session.bind))
            with col_b:
                st.subheader("🧪 المختبر")
                st.dataframe(pd.read_sql(session.query(LabLog).statement, session.bind))

        with tabs[6]: # الإعدادات
            st.subheader("⚙️ التحكم في النظام")
            with st.form("add_s"):
                n = st.text_input("اسم الحضيرة"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("إضافة"):
                    try:
                        session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
                    except IntegrityError: session.rollback(); st.error("موجود مسبقاً")
            if st.button("🔴 مسح السجلات وإعادة التصفير"):
                session.query(WorkLog).delete(); session.query(WorkerLog).delete(); session.query(StoreLog).delete(); session.commit(); st.rerun()

    # --- 5. واجهات المسؤولين ---
    elif not all_sites: st.warning("يجب إضافة مواقع أولاً")
    elif role_id == "Work":
        st.header("🏗️ تقرير الأشغال")
        with st.form("wf"):
            s = st.selectbox("Site", list(all_sites.keys())); p = st.slider("%", 0, 100); n = st.text_area("Note")
            if st.form_submit_button("حفظ"):
                session.add(WorkLog(site=s, progress=p, notes=n, lat=all_sites[s][0], lon=all_sites[s][1])); session.commit(); st.success("✅")
    # (بقية واجهات المسؤولين Labor, Store, Safety, Lab تتبع نفس النمط...)
    session.close()
