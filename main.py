import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px
from sqlalchemy.exc import IntegrityError

# --- 1. إعداد قاعدة البيانات الشاملة (v33) ---
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
    id = Column(Integer, primary_key=True); item = Column(String(100)); unit = Column(String(50)); qty = Column(Float); trans_type = Column(String(20)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True); incident = Column(String(100)); notes = Column(Text); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class LabLog(Base):
    __tablename__ = 'lab_logs'
    id = Column(Integer, primary_key=True); test_name = Column(String(100)); result = Column(String(100)); status = Column(String(50)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_final_v33.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. الإعدادات ---
st.set_page_config(page_title="EGMS Smart ERP v33", layout="wide")
if "logged_in" not in st.session_state:
    st.title("🏗️ EGMS Digital ERP v33")
    u = st.text_input("المستخدم"); p = st.text_input("الرمز", type="password")
    if st.button("🚀 Login"):
        access = {"admin": ("egms2025", "Admin"), "magaza": ("store2025", "Store"), "labor": ("labor2025", "Labor"), "work": ("work2025", "Work"), "safety": ("safe2025", "Safety"), "labo": ("lab2025", "Lab")}
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role_id": access[u][1]}); st.rerun()
else:
    role_id = st.session_state.get("role_id")
    st.sidebar.success(f"مرحباً: {role_id}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    
    session = Session()
    all_sites = {x.name: (x.lat, x.lon) for x in session.query(Site).all()}

    # --- 3. واجهة المدير (Admin) ---
    if role_id == "Admin":
        tabs = st.tabs(["📍 الخريطة", "🏗️ الأشغال", "📦 المخزن", "👷 العمال", "🛡️ السلامة & المختبر", "⚙️ الإعدادات"])
        
        with tabs[0]: # الخريطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')

        with tabs[1]: # الأشغال (تم الإصلاح هنا ✅)
            st.subheader("🏗️ تقارير إنجاز الحضائر الميدانية")
            df_work = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_work.empty:
                st.dataframe(df_work.sort_values(by='timestamp', ascending=False), use_container_width=True)
            else: st.info("لا توجد تقارير أشغال مصلة بعد.")

        with tabs[2]: # المخزن + تنبيه النقص
            st.subheader("📦 حالة المخزون")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                # تنبيه النقص
                low_stock = df_st[df_st['qty'] < 10]
                if not low_stock.empty:
                    st.error(f"⚠️ تنبيه: نقص في المواد التالية: {', '.join(low_stock['item'].unique())}")
                st.dataframe(df_st, use_container_width=True)

        with tabs[3]: # العمال
            st.subheader("👷 سجل العمال")
            df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_w.empty: st.dataframe(df_w, use_container_width=True)

        with tabs[5]: # الإعدادات
            st.subheader("إضافة حضيرة")
            with st.form("add_s"):
                n = st.text_input("اسم الحضيرة"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("حفظ"):
                    try: session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
                    except IntegrityError: session.rollback(); st.error("موجود مسبقاً")

    # --- 4. واجهة مسؤول المغازة (Store) ---
    elif role_id == "Store":
        st.header("📦 واجهة المغازة")
        with st.form("st_f"):
            item = st.text_input("المادة"); unit = st.selectbox("الوحدة", ["كغ", "طن", "كيس", "لتر", "متر"])
            qty = st.number_input("الكمية", min_value=0.1); t_type = st.radio("العملية", ["Entry", "Exit"])
            s_choice = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session.add(StoreLog(item=item, unit=unit, qty=qty, trans_type=t_type, site=s_choice))
                session.commit(); st.success("✅ تم التسجيل")

    # --- 5. واجهة مسؤول العمال (Labor) ---
    elif role_id == "Labor":
        st.header("👷 واجهة العمال")
        with st.form("lb_f"):
            name = st.text_input("اسم العامل"); h = st.number_input("الساعات"); r = st.number_input("الكلفة")
            s_choice = st.selectbox("الموقع", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session.add(WorkerLog(worker_name=name, hours=h, hourly_rate=r, site=s_choice))
                session.commit(); st.success("✅ تم التسجيل")

    # --- 6. واجهة مسؤول الأشغال (Work) ---
    elif role_id == "Work":
        st.header("🏗️ واجهة الأشغال")
        with st.form("wk_f"):
            s_choice = st.selectbox("الحضيرة", list(all_sites.keys()))
            prog = st.slider("نسبة الإنجاز %", 0, 100); note = st.text_area("ملاحظات")
            if st.form_submit_button("إرسال التقرير"):
                session.add(WorkLog(site=s_choice, progress=prog, notes=note, lat=all_sites[s_choice][0], lon=all_sites[s_choice][1]))
                session.commit(); st.success("✅ تم إرسال التقرير للمدير")
    
    session.close()
