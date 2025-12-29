import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
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

engine = create_engine('sqlite:///egms_final_v30.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. الإعدادات واللغة ---
st.set_page_config(page_title="EGMS Enterprise ERP", layout="wide")
sel_lang = st.sidebar.selectbox("🌐 Language", ["العربية", "Français"])
T = {"العربية": {"honor": "🏆 لوحة الشرف", "best_site": "أفضل حضيرة (الأسرع)", "best_worker": "أفضل عامل (الأكثر ساعات)"}, 
     "Français": {"honor": "🏆 Tableau d'Honneur", "best_site": "Meilleur Chantier", "best_worker": "Meilleur Ouvrier"}}[sel_lang]

def get_sites():
    session = Session(); s = session.query(Site).all(); session.close()
    return {x.name: (x.lat, x.lon) for x in s}

# --- 3. نظام الدخول ---
if "logged_in" not in st.session_state:
    st.title("🏗️ EGMS Digital ERP")
    u = st.text_input("User"); p = st.text_input("Pass", type="password")
    if st.button("🚀 Login"):
        access = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store"), "safety": ("safe2025", "Safety"), "labo": ("lab2025", "Lab")}
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role_id": access[u][1]}); st.rerun()
else:
    role_id = st.session_state.get("role_id")
    st.sidebar.success(f"Role: {role_id}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    all_sites = get_sites()

    # --- 4. واجهة المدير (Admin) ---
    if role_id == "Admin":
        st.title("📊 لوحة التحكم والذكاء الإداري")
        tabs = st.tabs(["🏆 لوحة الشرف", "🔮 التوقعات", "💰 ميزانية العمال", "📦 المخزن", "🛡️ السلامة & المختبر", "⚙️ الإعدادات"])
        session = Session()

        with tabs[0]: # لوحة الشرف
            st.header(T["honor"])
            col1, col2 = st.columns(2)
            # منطق أفضل عامل
            df_w = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            if not df_w.empty:
                top_worker = df_w.groupby('worker_name')['hours'].sum().idxmax()
                total_h = df_w.groupby('worker_name')['hours'].sum().max()
                with col1: st.metric(T["best_worker"], top_worker, f"{total_h} ساعة")
            # منطق أفضل حضيرة (سرعة الإنجاز)
            df_p = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_p.empty:
                best_s = df_p.groupby('site')['progress'].max().idxmax()
                with col2: st.metric(T["best_site"], best_s, "أعلى نسبة إنجاز")
            

        with tabs[1]: # التوقعات الذكية
            st.header("🔮 موعد التسليم المتوقع")
            df_prog = pd.read_sql(session.query(WorkLog).statement, session.bind)
            if not df_prog.empty:
                df_prog['timestamp'] = pd.to_datetime(df_prog['timestamp'])
                for site in df_prog['site'].unique():
                    data = df_prog[df_prog['site'] == site].sort_values('timestamp')
                    if len(data) >= 2:
                        days = (data['timestamp'].iloc[-1] - data['timestamp'].iloc[0]).days or 1
                        speed = data['progress'].iloc[-1] / days
                        if speed > 0:
                            rem = (100 - data['progress'].iloc[-1]) / speed
                            finish = datetime.now() + timedelta(days=int(rem))
                            st.write(f"📍 **{site}**: المتوقع تنتهي في **{finish.date()}** (بناءً على سرعة {speed:.1f}% يومياً)")

        with tabs[2]: # ميزانية العمال
            st.subheader("إدارة المصاريف البشرية")
            if not df_w.empty:
                df_w['cost'] = df_w['hours'] * df_w['hourly_rate']
                st.plotly_chart(px.pie(df_w, values='cost', names='specialization', title="توزيع التكلفة"))
                st.download_button("📥 تحميل التقرير المالي", df_w.to_csv().encode('utf-8-sig'), "payroll.csv")

        with tabs[5]: # الإعدادات والأرشفة
            st.subheader("⚙️ إدارة النظام")
            with st.form("site_add"):
                n = st.text_input("اسم الموقع"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon", value=10.0)
                if st.form_submit_button("إضافة حضيرة"):
                    try: session.add(Site(name=n, lat=la, lon=lo)); session.commit(); st.rerun()
                    except IntegrityError: session.rollback(); st.error("موجود مسبقاً")
            if st.button("🔴 مسح كافة السجلات (أرشفة)"):
                session.query(WorkLog).delete(); session.query(WorkerLog).delete(); session.commit(); st.rerun()
        session.close()

    # --- 5. واجهات المسؤولين ---
    elif not all_sites: st.warning("يجب إضافة مواقع من حساب المدير أولاً")
    
    elif role_id == "Work":
        st.header("🏗️ تقرير الأشغال")
        with st.form("f1"):
            s = st.selectbox("Site", list(all_sites.keys())); p = st.slider("% Progress", 0, 100); n = st.text_area("Notes")
            if st.form_submit_button("حفظ"):
                session = Session(); lat, lon = all_sites[s]
                session.add(WorkLog(site=s, progress=p, notes=n, lat=lat, lon=lon)); session.commit(); session.close(); st.success("✅")

    elif role_id == "Labor":
        st.header("👷 سجل العمال")
        with st.form("f2"):
            name = st.text_input("الاسم"); h = st.number_input("الساعات"); r = st.number_input("السعر"); s = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session = Session(); session.add(WorkerLog(worker_name=name, hours=h, hourly_rate=r, site=s)); session.commit(); session.close(); st.success("✅")

    elif role_id == "Store":
        st.header("📦 المخزن")
        with st.form("f3"):
            i = st.text_input("Item"); q = st.number_input("Qty"); t = st.radio("Type", ["Entry", "Exit"]); s = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session = Session(); session.add(StoreLog(item=i, qty=q, trans_type=t, site=s)); session.commit(); session.close(); st.success("✅")

    elif role_id == "Safety":
        st.header("🛡️ السلامة")
        with st.form("f4"):
            inc = st.selectbox("Incident", ["Normal", "Accident", "Risk"]); n = st.text_area("Note"); s = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session = Session(); session.add(SafetyLog(incident=inc, notes=n, site=s)); session.commit(); session.close(); st.success("✅")

    elif role_id == "Lab":
        st.header("🧪 المختبر")
        with st.form("f5"):
            test = st.text_input("Test"); res = st.text_input("Result"); stat = st.selectbox("Status", ["OK", "NG"]); s = st.selectbox("Site", list(all_sites.keys()))
            if st.form_submit_button("حفظ"):
                session = Session(); session.add(LabLog(test_name=test, result=res, status=stat, site=s)); session.commit(); session.close(); st.success("✅")
