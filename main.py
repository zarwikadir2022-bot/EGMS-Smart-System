import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px

# --- 1. هيكلة قاعدة البيانات الاحترافية (v71) ---
Base = declarative_base()

class InventoryItem(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    unit = Column(String(50))
    total_qty = Column(Float, default=0.0)

class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    work_plan = Column(Text)

class HandoverLog(Base):
    __tablename__ = 'handover_logs'
    id = Column(Integer, primary_key=True)
    worker_name = Column(String(100))
    item_name = Column(String(100))
    qty = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class TransactionHistory(Base):
    __tablename__ = 'transaction_history'
    id = Column(Integer, primary_key=True)
    item_name = Column(String(100))
    qty = Column(Float)
    type = Column(String(50)) # Entry, Handover, Return, Waste
    person = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)

# إنشاء محرك قاعدة البيانات
engine = create_engine('sqlite:///egms_platinum_v71.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

# --- 2. إعدادات الواجهة ---
st.set_page_config(page_title="EGMS Platinum ERP v71", layout="wide")

UNITS_LIST = ["وحدة", "كغ", "كيس", "لتر", "متر مربع", "متر مكعب"]

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center; color:#004a99;'>🏗️ EGMS Digital ERP - Platinum</h1>", unsafe_allow_html=True)
    with st.container():
        u = st.text_input("اسم المستخدم (User)")
        p = st.text_input("كلمة المرور (Pass)", type="password")
        if st.button("دخول النظام"):
            acc = {"admin": ("egms2025", "Admin"), "magaza": ("store2025", "Store")}
            if u in acc and p == acc[u][0]:
                st.session_state.update({"logged_in": True, "role": acc[u][1]})
                st.rerun()
            else: st.error("⚠️ بيانات الدخول غير صحيحة")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.info(f"👤 المتصل الآن: {role}")
    if st.sidebar.button("تسجيل الخروج"): st.session_state.clear(); st.rerun()

    # جلب البيانات المشتركة
    df_inv = pd.read_sql(session.query(InventoryItem).statement, session.bind)
    df_hist = pd.read_sql(session.query(TransactionHistory).statement, session.bind)
    df_workers = pd.read_sql(session.query(WorkerProfile).statement, session.bind)

    # --- 3. واجهة المدير (Admin) - التحليل والرقابة ---
    if role == "Admin":
        st.title("📊 لوحة تحكم المدير العام")
        tabs = st.tabs(["📈 التحليلات الذكية", "📋 الجرد التفصيلي", "📑 التقارير"])

        with tabs[0]: # التحليلات (Google Analytics Style)
            st.subheader("رؤية شاملة للعمليات الميدانية")
            if not df_inv.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(px.bar(df_inv, x='name', y='total_qty', color='name', title="رصيد المخزن الحالي"), use_container_width=True)
                with c2:
                    if not df_hist.empty:
                        st.plotly_chart(px.pie(df_hist, names='type', title="توزيع العمليات الميدانية"), use_container_width=True)
            else: st.info("بانتظار إدخال البيانات من الميدان.")

        with tabs[1]: # الجرد
            st.subheader("الجرد الحي للمعدات")
            st.dataframe(df_inv, use_container_width=True)
            st.subheader("سجل الحركات التاريخي")
            st.dataframe(df_hist, use_container_width=True)

        with tabs[2]: # التقارير
            if not df_hist.empty:
                csv_data = df_hist.to_csv(index=False).encode('utf-8')
                st.download_button("📥 تحميل السجل الكامل (CSV)", csv_data, "EGMS_Full_Log.csv", "text/csv")

    # --- 4. واجهة مسؤول المغازة (Store) - الإدخال والتحكم ---
    elif role == "Store":
        st.title("📦 مركز العمليات الميدانية")
        m_tabs = st.tabs(["📥 تسجيل سلع", "👷 إدارة العمال", "🤝 تسليم عُهدة", "🔙 استرجاع عُهدة", "📤 استيراد CSV"])

        with m_tabs[0]: # تسجيل المواد
            with st.form("entry_f"):
                st.subheader("إضافة مادة أو معدة")
                it_name = st.text_input("اسم المادة")
                it_unit = st.selectbox("وحدة القيس", UNITS_LIST)
                it_qty = st.number_input("الكمية", min_value=0.1)
                if st.form_submit_button("حفظ"):
                    exist = session.query(InventoryItem).filter_by(name=it_name).first()
                    if exist: exist.total_qty += it_qty
                    else: session.add(InventoryItem(name=it_name, unit=it_unit, total_qty=it_qty))
                    session.add(TransactionHistory(item_name=it_name, qty=it_qty, type="Entry", person="Store"))
                    session.commit(); st.success("✅ تم تحديث المخزن"); st.rerun()

        with m_tabs[1]: # إدارة العمال
            st.subheader("تسجيل العمال وخطط العمل")
            with st.form("worker_f"):
                nm = st.text_input("اسم العامل")
                pl = st.text_area("خطة العمل الموكلة له")
                if st.form_submit_button("حفظ ملف العامل"):
                    session.add(WorkerProfile(name=nm, work_plan=pl))
                    session.commit(); st.success("✅ تم التسجيل"); st.rerun()
            st.dataframe(df_workers, use_container_width=True)

        with m_tabs[2]: # تسليم عُهدة
            items = session.query(InventoryItem).all()
            workers = session.query(WorkerProfile).all()
            if items and workers:
                with st.form("handover_f"):
                    it = st.selectbox("المعدة", [i.name for i in items])
                    wk = st.selectbox("العامل", workers, format_func=lambda x: x.name)
                    st.warning(f"📋 خطة عمله: {wk.work_plan}")
                    qt = st.number_input("الكمية المسلمة", min_value=1.0)
                    if st.form_submit_button("تأكيد التسليم"):
                        item_obj = session.query(InventoryItem).filter_by(name=it).first()
                        if item_obj.total_qty >= qt:
                            item_obj.total_qty -= qt
                            session.add(HandoverLog(worker_name=wk.name, item_name=it, qty=qt))
                            session.add(TransactionHistory(item_name=it, qty=qt, type="Handover", person=wk.name))
                            session.commit(); st.success("✅ تم التسليم"); st.rerun()
                        else: st.error("❌ الكمية غير كافية!")
            else: st.info("يجب إضافة عمال ومواد أولاً.")

        with m_tabs[3]: # استرجاع عُهدة
            h_logs = session.query(HandoverLog).all()
            if h_logs:
                for log in h_logs:
                    c1, c2 = st.columns([3, 1])
                    c1.warning(f"👷 {log.worker_name} لديه ({log.qty}) {log.item_name}")
                    if c2.button("استرجاع", key=log.id):
                        it_obj = session.query(InventoryItem).filter_by(name=log.item_name).first()
                        it_obj.total_qty += log.qty
                        session.add(TransactionHistory(item_name=log.item_name, qty=log.qty, type="Return", person=log.worker_name))
                        session.delete(log)
                        session.commit(); st.rerun()
            else: st.info("لا توجد عُهد مفتوحة حالياً.")

        with m_tabs[4]: # استيراد CSV
            st.subheader("استيراد بيانات من ملف CSV")
            up_file = st.file_uploader("اختر الملف", type="csv")
            if up_file:
                df_up = pd.read_csv(up_file)
                st.dataframe(df_up)
                if st.button("تأكيد الرفع"):
                    for _, row in df_up.iterrows():
                        exist = session.query(InventoryItem).filter_by(name=row['item_name']).first()
                        if exist: exist.total_qty += float(row['qty'])
                        else: session.add(InventoryItem(name=row['item_name'], unit=row['unit'], total_qty=float(row['qty'])))
                        session.add(TransactionHistory(item_name=row['item_name'], qty=row['qty'], type="CSV_Entry", person="Store"))
                    session.commit(); st.success("✅ تم الاستيراد"); st.rerun()

    Session.remove()
