import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import io

# --- 1. بناء هيكل قاعدة البيانات الاحترافي (v63) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); lat = Column(Float); lon = Column(Float)
    tasks = relationship("SiteTask", back_populates="site_obj", cascade="all, delete-orphan")

class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'
    id = Column(Integer, primary_key=True); name = Column(String(100), unique=True); hourly_rate = Column(Float); work_plan = Column(Text)
    logs = relationship("WorkerLog", back_populates="profile")

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True); worker_id = Column(Integer, ForeignKey('worker_profiles.id')); hours = Column(Float); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)
    profile = relationship("WorkerProfile", back_populates="logs")

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True); item = Column(String(100)); unit = Column(String(50)); qty = Column(Float); trans_type = Column(String(20)); site = Column(String(100)); timestamp = Column(DateTime, default=datetime.utcnow)

class SiteTask(Base):
    __tablename__ = 'site_tasks'
    id = Column(Integer, primary_key=True); site_id = Column(Integer, ForeignKey('sites.id')); task_name = Column(String(100)); unit = Column(String(50)); target_qty = Column(Float)
    site_obj = relationship("Site", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task_obj", cascade="all, delete-orphan")

class TaskLog(Base):
    __tablename__ = 'task_logs'
    id = Column(Integer, primary_key=True); task_id = Column(Integer, ForeignKey('site_tasks.id')); qty_done = Column(Float); notes = Column(Text); image = Column(LargeBinary); timestamp = Column(DateTime, default=datetime.utcnow)
    task_obj = relationship("SiteTask", back_populates="logs")



# إعداد المحرك v63
engine = create_engine('sqlite:///egms_final_v63.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. محرك تقارير PDF ---
def generate_pdf_v63(site_obj, session):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    s_name = site_obj.name.encode('ascii', 'ignore').decode('ascii') or "Project"
    pdf.cell(190, 10, f"EGMS Report: {s_name}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    for t in site_obj.tasks:
        done = sum(l.qty_done for l in t.logs)
        p = (done/t.target_qty)*100 if t.target_qty > 0 else 0
        t_name = t.task_name.encode('ascii', 'ignore').decode('ascii') or "Task"
        pdf.cell(190, 8, f"- {t_name}: {done}/{t.target_qty} {t.unit} ({p:.1f}%)", ln=True)
    return pdf.output()

# --- 3. واجهة المستخدم الرسومية ---
st.set_page_config(page_title="EGMS Business Analytics v63", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;'>🏗️ EGMS Digital ERP & Analytics</h1>", unsafe_allow_html=True)
    u_in = st.text_input("Username")
    p_in = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "work": ("work2025", "Work"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store")}
        if u_in in acc and p_in == acc[u_in][0]:
            st.session_state.update({"logged_in": True, "role": acc[u_in][1]})
            st.rerun()
        else: st.error("Access Denied")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.success(f"User: {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    all_sites = session.query(Site).all()
    
    # --- 4. واجهة المدير (Admin Dashboards) ---
    if role == "Admin":
        st.title("💼 لوحة تحكم القيادة والتحليلات")
        tabs = st.tabs(["📊 تحليلات العمال", "📦 تحليلات المخزن", "🏗️ تحليلات الإنجاز", "📍 الخريطة", "⚙️ الإعدادات"])

        with tabs[0]: # تحليلات العمال والرواتب
            st.subheader("👷 الموارد البشرية والرواتب")
            df_labor = pd.read_sql(session.query(WorkerLog).statement, session.bind)
            df_profs = pd.read_sql(session.query(WorkerProfile).statement, session.bind)
            if not df_labor.empty and not df_profs.empty:
                df_hr = pd.merge(df_labor, df_profs, left_on='worker_id', right_on='id')
                df_hr['Cost'] = df_hr['hours'] * df_hr['hourly_rate']
                
                c1, c2 = st.columns(2)
                fig_pie = px.pie(df_hr, values='Cost', names='site', title="توزيع المصاريف حسب الموقع")
                c1.plotly_chart(fig_pie, use_container_width=True)
                
                fig_bar = px.bar(df_hr, x='name', y='hours', color='site', title="ساعات عمل الموظفين")
                c2.plotly_chart(fig_bar, use_container_width=True)
            else: st.info("بانتظار تسجيل أولى البيانات...")

        with tabs[1]: # تحليلات المخزن
            st.subheader("📦 رصيد المخزن والمواد")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                df_st['net'] = df_st.apply(lambda x: x['qty'] if x['trans_type'] == "Entry" else -x['qty'], axis=1)
                balance = df_st.groupby(['item', 'unit'])['net'].sum().reset_index()
                
                fig_store = px.bar(balance, x='item', y='net', color='item', title="الكميات المتوفرة حالياً")
                st.plotly_chart(fig_store, use_container_width=True)
                st.table(balance.rename(columns={'net':'الرصيد المتاح'}))

        with tabs[2]: # تحليلات الإنجاز
            st.subheader("🏗️ متابعة تقدم الأشغال")
            if all_sites:
                for s in all_sites:
                    with st.expander(f"موقع: {s.name}"):
                        task_list = []
                        for tk in s.tasks:
                            done = sum(l.qty_done for l in tk.logs)
                            task_list.append({"المرحلة": tk.task_name, "المنجز": done, "المستهدف": tk.target_qty})
                        
                        if task_list:
                            df_p = pd.DataFrame(task_list)
                            fig_p = px.bar(df_p, x='المرحلة', y=['المنجز', 'المستهدف'], barmode='group', title=f"تقدم العمل في {s.name}")
                            st.plotly_chart(fig_p, use_container_width=True)

        with tabs[4]: # الإعدادات والـ PDF
            st.subheader("⚙️ إعدادات النظام")
            if all_sites:
                s_pdf = st.selectbox("توليد تقرير لـ", all_sites, format_func=lambda x: x.name)
                if st.button("توليد PDF"):
                    pdf_bytes = generate_pdf_v63(s_pdf, session)
                    st.download_button("تحميل الملف", pdf_bytes, f"{s_pdf.name}.pdf", "application/pdf")
            
            with st.form("site_f"):
                sn = st.text_input("اسم الحضيرة"); la = st.number_input("Lat", value=36.0); lo = st.number_input("Lon")
                if st.form_submit_button("حفظ الموقع"):
                    session.add(Site(name=sn, lat=la, lon=lo)); session.commit(); st.rerun()
            
            if all_sites:
                with st.form("hr_f"):
                    st.write("إضافة عامل")
                    n = st.text_input("الاسم"); r = st.number_input("السعر"); pl = st.text_area("الخطة")
                    if st.form_submit_button("حفظ العامل"):
                        session.add(WorkerProfile(name=n, hourly_rate=r, work_plan=pl)); session.commit(); st.rerun()

    # --- 5. واجهات الموظفين (تم التأكد من تطابق المسميات ✅) ---
    elif role == "Store":
        st.header("📦 إدارة المخزن")
        if all_sites:
            with st.form("st_form"):
                it = st.text_input("المادة"); qt = st.number_input("الكمية")
                ty = st.radio("النوع", ["Entry", "Exit"]); si = st.selectbox("الموقع", [s.name for s in all_sites])
                if st.form_submit_button("حفظ"):
                    session.add(StoreLog(item=it, unit="كيس", qty=qt, trans_type=ty, site=si)); session.commit(); st.success("تم")
    
    elif role == "Labor":
        st.header("👷 سجل العمال")
        profs = session.query(WorkerProfile).all()
        if profs and all_sites:
            with st.form("lb_form"):
                w = st.selectbox("العامل", profs, format_func=lambda x: x.name)
                h = st.number_input("الساعات"); si = st.selectbox("الموقع", [s.name for s in all_sites])
                if st.form_submit_button("تسجيل"):
                    session.add(WorkerLog(worker_id=w.id, hours=h, site=si)); session.commit(); st.success("تم")

    elif role == "Work":
        st.header("🏗️ تقرير الإنجاز")
        if all_sites:
            s_ch = st.selectbox("الحضيرة", all_sites, format_func=lambda x: x.name)
            tasks = session.query(SiteTask).filter_by(site_id=s_ch.id).all()
            if tasks:
                with st.form("wk_form"):
                    tk = st.selectbox("المرحلة", tasks, format_func=lambda x: x.task_name)
                    qd = st.number_input("المنجز اليوم"); im = st.file_uploader("صورة", type=['jpg', 'png'])
                    if st.form_submit_button("إرسال"):
                        ib = im.read() if im else None
                        session.add(TaskLog(task_id=tk.id, qty_done=qd, notes="", image=ib)); session.commit(); st.success("تم")

    Session.remove()
