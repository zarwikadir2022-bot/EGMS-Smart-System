import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import io

# --- 1. إعدادات قاعدة البيانات (V80) ---
def setup_database():
    try:
        conn = sqlite3.connect("egms_v80_safe.db", check_same_thread=False)
        cursor = conn.cursor()
        # جدول المواد
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                unit TEXT,
                quantity REAL DEFAULT 0,
                location TEXT
            )
        """)
        # جدول العمال
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                work_plan TEXT
            )
        """)
        # سجل العمليات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT,
                qty REAL,
                type TEXT,
                person TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"خطأ في قاعدة البيانات: {e}")
        return False

# تشغيل الإعداد
if setup_database():
    st.sidebar.success("✅ قاعدة البيانات متصلة")

# --- 2. منطق تسجيل الدخول (Session State) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None

# --- 3. واجهة البرنامج ---
st.set_page_config(page_title="EGMS ERP v80", layout="wide")

if not st.session_state.authenticated:
    # شاشة الدخول تظهر هنا إجبارياً
    st.title("🏗️ نظام EGMS - تسجيل الدخول")
    st.info("الرجاء إدخال البيانات للوصول إلى المنظومة")
    
    col1, col2 = st.columns(2)
    user = col1.text_input("اسم المستخدم")
    pw = col2.text_input("كلمة المرور", type="password")
    
    if st.button("دخول"):
        if user == "admin" and pw == "egms2025":
            st.session_state.authenticated = True
            st.session_state.role = "Admin"
            st.rerun()
        elif user == "magaza" and pw == "store2025":
            st.session_state.authenticated = True
            st.session_state.role = "Store"
            st.rerun()
        else:
            st.error("❌ بيانات الدخول غير صحيحة")
else:
    # الواجهة الرئيسية بعد الدخول
    role = st.session_state.role
    st.sidebar.title(f"👤 مرحباً: {role}")
    
    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.authenticated = False
        st.session_state.role = None
        st.rerun()

    conn = sqlite3.connect("egms_v80_safe.db", check_same_thread=False)
    
    # --- واجهة مسؤول المغازة (Store) ---
    if role == "Store":
        st.header("📦 لوحة عمليات المغازة")
        tab1, tab2, tab3 = st.tabs(["📥 إدارة السلع والعمال", "🤝 تسليم العُهدة", "📋 سجل الحركات"])
        
        with tab1:
            col_a, col_b = st.columns(2)
            # إضافة سلع
            with col_a:
                st.subheader("➕ إضافة/تحديث مادة")
                with st.form("item_form", clear_on_submit=True):
                    it_name = st.text_input("اسم المادة")
                    it_unit = st.selectbox("الوحدة", ["وحدة", "كغ", "كيس", "لتر", "متر مربع"])
                    it_qty = st.number_input("الكمية", min_value=0.0)
                    if st.form_submit_button("حفظ المادة"):
                        cursor = conn.cursor()
                        cursor.execute("INSERT OR REPLACE INTO items (name, unit, quantity) VALUES (?, ?, (SELECT COALESCE(quantity, 0) FROM items WHERE name=?)+?)", 
                                       (it_name, it_unit, it_name, it_qty))
                        conn.commit()
                        st.success(f"تم تسجيل {it_name}")

            # إضافة عمال
            with col_b:
                st.subheader("👷 إضافة عامل")
                with st.form("worker_form", clear_on_submit=True):
                    w_name = st.text_input("اسم العامل")
                    w_plan = st.text_area("خطة العمل")
                    if st.form_submit_button("حفظ العامل"):
                        cursor = conn.cursor()
                        cursor.execute("INSERT OR IGNORE INTO workers (name, work_plan) VALUES (?, ?)", (w_name, w_plan))
                        conn.commit()
                        st.success(f"تم تسجيل {w_name}")

    # --- واجهة المدير (Admin) ---
    elif role == "Admin":
        st.header("📊 لوحة تحليلات الإدارة")
        df_items = pd.read_sql("SELECT * FROM items", conn)
        
        if not df_items.empty:
            st.subheader("تحليل المخزون الحي")
            fig = px.bar(df_items, x='name', y='quantity', color='name', title="رصيد المواد")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_items, use_container_width=True)
        else:
            st.warning("⚠️ لا توجد بيانات لعرضها. يرجى الطلب من مسؤول المغازة إدخال السلع.")

    conn.close()
