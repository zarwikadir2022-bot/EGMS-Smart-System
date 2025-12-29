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

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True); name = Column(String(100)); hours = Column(Float); rate = Column(Float); spec = Column(String(50)); site = Column(String(100)); date = Column(DateTime, default=datetime.utcnow)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True); item = Column(String(100)); unit = Column(String(50)); qty = Column(Float); type = Column(String(20)); site = Column(String(100)); date = Column(DateTime, default=datetime.utcnow)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True); site = Column(String(100)); progress = Column(Float); notes = Column(Text); date = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///egms_final_pro_v36.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. واجهة الدخول (Logic Fix) ---
st.set_page_config(page_title="EGMS Business ERP", layout="wide")

# ضمان ظهور خيار الدخول إذا لم يكن المستخدم مسجلاً
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.title("🏗️ بوابة الدخول الرقمية - EGMS")
    with st.container():
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.button("دخول إلى النظام"):
            access = {
                "admin": ("egms2025", "Admin"),
                "labor": ("labor2025", "Labor"),
                "magaza": ("store2025", "Store"),
                "work": ("work2025", "Work")
            }
            if u in access and p == access[u][0]:
                st.session_state["logged_in"] = True
                st.session_state["role"] = access[u][1]
                st.rerun()
            else:
                st.error("⚠️ بيانات الدخول غير صحيحة")
else:
    # --- 3. واجهة النظام بعد الدخول ---
    role = st.session_state.get("role")
    st.sidebar.markdown(f"### 👤 المستخدم: {role}")
    if st.sidebar.button("تسجيل الخروج"):
        st.session_state["logged_in"] = False
        st.session_state.clear()
        st.rerun()
    
    session = Session()
    
    # واجهة المدير العام
    if role == "Admin":
        st.title("💼 لوحة التحكم الإدارية المركزية")
        tabs = st.tabs(["📍 الخريطة", "👷 العمال", "📦 المخزن", "🏗️ الأشغال", "⚙️ الإعدادات"])

        with tabs[0]: # الخريطة
            df_s = pd.read_sql(session.query(Site).statement, session.bind)
            if not df_s.empty: st.map(df_s, latitude='lat', longitude='lon')
            else: st.info("لا توجد مواقع لعرضها")

        with tabs[1]: # العمال
            df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_w.empty:
                df_w['التكلفة'] = df_w['hours'] * df_w['rate']
                st.metric("إجمالي ميزانية الرواتب", f"{df_w['التكلفة'].sum():,.2f} TND")
                st.dataframe(df_w, use_container_width=True)

        with tabs[2]: # المخزن (الرصيد الذكي)
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                df_st['temp_qty'] = df_st.apply(lambda x: x['qty'] if x['type'] == "Entry" else -x['qty'], axis=1)
                balance = df_st.groupby(['item', 'unit'])['temp_qty'].sum().reset_index()
                st.subheader("📊 الرصيد المتوفر حالياً")
                st.table(balance.rename(columns={'item': 'المادة', 'unit': 'الوحدة', 'temp_qty': 'الكمية المتوفرة'}))

        with tabs[3]: # الأشغال
            df_work = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_work.empty: st.dataframe(df_work, use_container_width=True)

        with tabs[4]: # الإعدادات (إضافة وحذف)
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("➕ إضافة موقع")
                with st.form("add_site"):
                    n = st.text_input("اسم الحضيرة")
                    la = st.number_input("Lat", value=36.0, format="%.6f")
                    lo = st.number_input("Lon", value=10.0, format="%.6f")
                    if st.form_submit_button("حفظ"):
                        try:
                            session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
                        except: session.rollback(); st.error("الموقع موجود مسبقاً")
            with col2:
                st.subheader("🗑️ حذف موقع")
                all_s = [s.name for s in session.query(Site).all()]
                s_to_del = st.selectbox("اختر الموقع للحذف", all_s)
                if st.button("تأكيد الحذف النهائي"):
                    session.query(Site).filter_by(name=s_choice).delete()
                    session.commit(); st.rerun()

    # واجهة الموظفين (المغازة / العمال / الأشغال)
    else:
        st.header(f"🛠️ بوابة {role}")
        sites = [s.name for s in session.query(Site).all()]
        if not sites:
            st.warning("⚠️ لا توجد حضائر مضافة حالياً.")
        else:
            if role == "Store": # المغازة
                with st.form("st_f"):
                    item = st.text_input("المادة"); unit = st.selectbox("الوحدة", ["كغ", "طن", "متر", "كيس"])
                    qty = st.number_input("الكمية"); t = st.radio("النوع", ["Entry", "Exit"])
                    s = st.selectbox("الموقع", sites)
                    if st.form_submit_button("حفظ"):
                        session.add(StoreLog(item=item, unit=unit, qty=qty, type=t, site=s)); session.commit(); st.success("✅")

            elif role == "Work": # الأشغال
                with st.form("wk_f"):
                    s = st.selectbox("الموقع", sites); p = st.slider("نسبة الإنجاز %", 0, 100); n = st.text_area("ملاحظات")
                    if st.form_submit_button("إرسال التقرير"):
                        session.add(WorkLog(site=s, progress=p, notes=n)); session.commit(); st.success("✅")

    session.close()
