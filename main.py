import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
import plotly.express as px

# --- 1. إعدادات قاعدة البيانات (Web Database) ---
Base = declarative_base()
class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(100))
    quantity = Column(Float)
    unit = Column(String(50))
    location = Column(String(100))
    last_updated = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///web_inventory.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))

# --- 2. واجهة المستخدم (التصميم الجذاب) ---
st.set_page_config(page_title="EGMS Web Inventory", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .metric-card { background-color: white; padding: 20px; border-radius: 12px; border-left: 6px solid #003366; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    h1 { color: #003366; font-family: 'Segoe UI'; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. نظام الدخول ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🏗️ تسجيل الدخول للمنظومة")
    user = st.text_input("اسم المستخدم")
    pw = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        if user == "admin" and pw == "egms2025":
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("❌ بيانات خاطئة")
else:
    session = Session()
    st.sidebar.title("🛠️ التحكم")
    page = st.sidebar.radio("انتقل إلى:", ["لوحة التحليل (Dashboard)", "إدارة الجرد (Inventory)", "إضافة سلع جديدة"])

    # جلب البيانات
    df = pd.read_sql(session.query(Item).statement, session.bind)

    # --- صفحة التحليل (Dashboard) ---
    if page == "لوحة التحليل (Dashboard)":
        st.title("📊 لوحة تحليلات المغازة")
        
        # بطاقات KPI
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="metric-card"><h3>إجمالي الأصناف</h3><h2>{len(df)}</h2></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="metric-card"><h3>قطع المخزن</h3><h2>{df["quantity"].sum() if not df.empty else 0}</h2></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="metric-card"><h3>آخر تحديث</h3><h5>{datetime.now().strftime("%Y-%m-%d")}</h5></div>', unsafe_allow_html=True)

        if not df.empty:
            st.divider()
            col_a, col_b = st.columns(2)
            fig1 = px.bar(df, x='name', y='quantity', color='category', title="توزيع الكميات حسب الصنف")
            col_a.plotly_chart(fig1, use_container_width=True)
            
            fig2 = px.pie(df, values='quantity', names='category', hole=0.4, title="نسبة الفئات في المخزن")
            col_b.plotly_chart(fig2, use_container_width=True)

    # --- صفحة إدارة الجرد (Inventory) ---
    elif page == "إدارة الجرد (Inventory)":
        st.title("📋 سجل الجرد التفصيلي")
        search = st.text_input("🔍 ابحث عن سلعة بالاسم...")
        if search:
            display_df = df[df['name'].str.contains(search, case=False)]
        else:
            display_df = df
        
        st.dataframe(display_df, use_container_width=True)
        
        # تصدير البيانات (متطلب تحليل البيانات ✅)
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 تحميل سجل الجرد (CSV)", csv, "inventory_report.csv", "text/csv")

    # --- صفحة إضافة سلع ---
    elif page == "إضافة سلع جديدة":
        st.title("📥 تسجيل سلع ومعدات")
        with st.form("add_form"):
            name = st.text_input("اسم السلعة")
            cat = st.selectbox("الفئة", ["معدات ثقيلة", "مواد بناء", "أدوات يدوية", "أخرى"])
            qty = st.number_input("الكمية", min_value=0.0)
            unit = st.text_input("الوحدة (كغ، قطعة...)")
            loc = st.text_input("مكان التخزين (الرف/المستودع)")
            
            if st.form_submit_button("حفظ في قاعدة البيانات"):
                new_item = Item(name=name, category=cat, quantity=qty, unit=unit, location=loc)
                session.add(new_item)
                session.commit()
                st.success(f"✅ تم إضافة {name} بنجاح!")
                st.rerun()

    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.authenticated = False
        st.rerun()
    Session.remove()
