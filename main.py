import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import plotly.express as px

# --- 1. هيكلة قاعدة البيانات (v70) ---
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

engine = create_engine('sqlite:///egms_v70_final.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))

# --- 2. واجهة التطبيق ---
st.set_page_config(page_title="EGMS Analytics v70", layout="wide")

UNITS_LIST = ["وحدة", "كغ", "كيس", "لتر", "متر مربع", "متر مكعب"]

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;'>🏗️ EGMS Digital ERP v70</h1>", unsafe_allow_html=True)
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        acc = {"admin": ("egms2025", "Admin"), "magaza": ("store2025", "Store")}
        if u in acc and p == acc[u][0]:
            st.session_state.update({"logged_in": True, "role": acc[u][1]})
            st.rerun()
        else: st.error("Access Denied")
else:
    role = st.session_state["role"]; session = Session()
    st.sidebar.success(f"Role: {role}")
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

    # جلب البيانات للتحليل
    all_items = session.query(InventoryItem).all()
    all_workers = session.query(WorkerProfile).all()
    df_inv = pd.read_sql(session.query(InventoryItem).statement, session.bind)
    df_hist = pd.read_sql(session.query(TransactionHistory).statement, session.bind)
    df_hand = pd.read_sql(session.query(HandoverLog).statement, session.bind)

    # --- 3. واجهة المدير (Admin) - تحليل ورؤية فقط ---
    if role == "Admin":
        st.title("📊 لوحة تحكم المدير - التحليلات والجرد")
        tabs = st.tabs(["📈 الرسوم البيانية", "📋 الجرد الحي", "📄 استخراج التقارير"])

        with tabs[0]: # الرسوم البيانية (تم الإصلاح ✅)
            st.subheader("تحليل بيانات الميدان")
            if not df_inv.empty:
                col1, col2 = st.columns(2)
                fig1 = px.bar(df_inv, x='name', y='total_qty', color='name', title="مستويات المخزون الحالي")
                col1.plotly_chart(fig1, use_container_width=True)
                
                if not df_hist.empty:
                    fig2 = px.pie(df_hist, names='type', title="توزيع العمليات (دخول، تسليم، استرجاع)")
                    col2.plotly_chart(fig2, use_container_width=True)
            else: st.info("بانتظار تسجيل البيانات من مسؤول المغازة.")

        with tabs[1]: # الجرد التفصيلي
            st.subheader("حالة المخزن والعُهد")
            st.dataframe(df_inv, use_container_width=True)
            st.subheader("العُهد المفتوحة لدى العمال")
            st.dataframe(df_hand, use_container_width=True)

        with tabs[2]: # التقارير
            if not df_hist.empty:
                csv = df_hist.to_csv(index=False).encode('utf-8')
                st.download_button("📥 تحميل سجل العمليات الكامل (CSV)", csv, "EGMS_Report_v70.csv", "text/csv")

    # --- 4. واجهة مسؤول المغازة (Store) - المسؤولية الكاملة ✅ ---
    elif role == "Store":
        st.title("📦 مركز العمليات الميدانية")
        m_tabs = st.tabs(["📥 تسجيل سلع", "👷 إدارة العمال", "🤝 تسليم عُهدة", "🔙 استرجاع عُهدة", "📤 استيراد CSV"])

        with m_tabs[0]: # تسجيل المواد
            with st.form("entry_v70"):
                st.subheader("إضافة مادة/معدة")
                item_name = st.text_input("اسم المادة")
                item_unit = st.selectbox("الوحدة", UNITS_LIST)
                item_qty = st.number_input("الكمية", min_value=0.1)
                if st.form_submit_button("حفظ"):
                    exist = session.query(InventoryItem).filter_by(name=item_name).first()
                    if exist: exist.total_qty += item_qty
                    else: session.add(InventoryItem(name=item_name, unit=item_unit, total_qty=item_qty))
                    session.add(TransactionHistory(item_name=item_name, qty=item_qty, type="Entry", person="Store"))
                    session.commit(); st.success("تم الحفظ"); st.rerun()

        with m_tabs[1]: # إدارة العمال (نقلت للمغازة ✅)
            st.subheader("تسجيل العمال وخطط العمل")
            with st.form("worker_v70"):
                wn = st.text_input("اسم العامل")
                wp = st.text_area("خطة العمل الموكلة له")
                if st.form_submit_button("حفظ ملف العامل"):
                    session.add(WorkerProfile(name=wn, work_plan=wp))
                    session.commit(); st.success("تم تسجيل العامل بنجاح"); st.rerun()
            st.dataframe(pd.read_sql(session.query(WorkerProfile).statement, session.bind), use_container_width=True)

        with m_tabs[2]: # تسليم عُهدة
            if all_items and all_workers:
                with st.form("handover_v70"):
                    it = st.selectbox("المعدات", [i.name for i in all_items])
                    wk = st.selectbox("العامل المستلم", all_workers, format_func=lambda x: x.name)
                    st.warning(f"خطة العمل: {wk.work_plan}")
                    qt = st.number_input("الكمية", min_value=1.0)
                    if st.form_submit_button("تأكيد التسليم"):
                        item = session.query(InventoryItem).filter_by(name=it).first()
                        if item.total_qty >= qt:
                            item.total_qty -= qt
                            session.add(HandoverLog(worker_name=wk.name, item_name=it, qty=qt))
                            session.add(TransactionHistory(item_name=it, qty=qt, type="Handover", person=wk.name))
                            session.commit(); st.success("تم التسليم"); st.rerun()
                        else: st.error("المخزن غير كافٍ")

        with m_tabs[3]: # استرجاع عُهدة
            if not df_hand.empty:
                for idx, row in df_hand.iterrows():
                    c1, c2 = st.columns([3, 1])
                    c1.info(f"عُهدة: {row['worker_name']} لديه {row['qty']} {row['item_name']}")
                    if c2.button("استرجاع", key=row['id']):
                        item = session.query(InventoryItem).filter_by(name=row['item_name']).first()
                        item.total_qty += row['qty']
                        session.add(TransactionHistory(item_name=row['item_name'], qty=row['qty'], type="Return", person=row['worker_name']))
                        session.query(HandoverLog).filter_by(id=row['id']).delete()
                        session.commit(); st.rerun()
            else: st.info("لا توجد عُهد حالياً.")

    Session.remove()
