import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px
from sqlalchemy.exc import IntegrityError

# --- 1. إعداد قاعدة البيانات ---
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

engine = create_engine('sqlite:///egms_final_v37.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. واجهة الدخول ---
st.set_page_config(page_title="EGMS Business ERP v37", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.title("🏗️ بوابة EGMS الرقمية")
    u = st.text_input("اسم المستخدم")
    p = st.text_input("كلمة المرور", type="password")
    if st.button("تسجيل الدخول"):
        access = {"admin": ("egms2025", "Admin"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store"), "work": ("work2025", "Work")}
        if u in access and p == access[u][0]:
            st.session_state["logged_in"] = True
            st.session_state["role"] = access[u][1]
            st.rerun()
        else: st.error("⚠️ بيانات خاطئة")
else:
    role = st.session_state.get("role")
    st.sidebar.markdown(f"### 👤 {role}")
    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.clear(); st.rerun()
    
    session = Session()

    # --- 3. واجهة المدير (Admin) ---
    if role == "Admin":
        st.title("💼 لوحة الإدارة والتحليل")
        
        # ميزة التصفية بالتاريخ في الجانب
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 تصفية التقارير")
        start_date = st.sidebar.date_input("من تاريخ", datetime.now().date())
        
        tabs = st.tabs(["📍 الخريطة", "👷 العمال", "📦 المخزن", "🏗️ الأشغال", "⚙️ الإعدادات"])

        with tabs[0]: # الخريطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')

        with tabs[1]: # العمال + بحث بالتاريخ
            df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_w.empty:
                df_w['date'] = pd.to_datetime(df_w['date']).dt.date
                filtered_w = df_w[df_w['date'] >= start_date]
                st.subheader(f"سجل العمال منذ {start_date}")
                st.dataframe(filtered_w, use_container_width=True)

        with tabs[2]: # المخزن (الرصيد الصافي)
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                df_st['actual_qty'] = df_st.apply(lambda x: x['qty'] if x['type'] == "Entry" else -x['qty'], axis=1)
                balance = df_st.groupby(['item', 'unit'])['actual_qty'].sum().reset_index()
                st.table(balance.rename(columns={'actual_qty': 'الرصيد المتاح حالياً'}))

        with tabs[4]: # الإعدادات (تم تصحيح الخطأ هنا ✅)
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("➕ إضافة حضيرة")
                with st.form("add_site"):
                    n = st.text_input("اسم الموقع"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                    if st.form_submit_button("إضافة"):
                        try: session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
                        except: session.rollback(); st.error("الموقع موجود")
            with c2:
                st.subheader("🗑️ حذف حضيرة")
                sites = [s.name for s in session.query(Site).all()]
                if sites:
                    s_to_del = st.selectbox("اختر الموقع للحذف", sites)
                    if st.button("تأكيد الحذف"):
                        session.query(Site).filter_by(name=s_to_del).delete() # تم التصحيح
                        session.commit(); st.rerun()

    # --- 4. واجهات المسؤولين ---
    else:
        st.header(f"🛠️ بوابة {role}")
        sites_list = [s.name for s in session.query(Site).all()]
        if not sites_list: st.warning("يجب إضافة مواقع من حساب المدير")
        else:
            if role == "Store": # المغازة
                with st.form("st_f"):
                    item = st.text_input("المادة"); unit = st.selectbox("الوحدة", ["كغ", "طن", "متر", "كيس"])
                    qty = st.number_input("الكمية"); t = st.radio("النوع", ["Entry", "Exit"]); s = st.selectbox("الموقع", sites_list)
                    if st.form_submit_button("حفظ"):
                        session.add(StoreLog(item=item, unit=unit, qty=qty, type=t, site=s)); session.commit(); st.success("✅")

            elif role == "Work": # الأشغال
                with st.form("wk_f"):
                    s = st.selectbox("الموقع", sites_list); p = st.slider("الإنجاز %", 0, 100); n = st.text_area("ملاحظات")
                    if st.form_submit_button("إرسال"):
                        session.add(WorkLog(site=s, progress=p, notes=n)); session.commit(); st.success("✅")

    session.close()
