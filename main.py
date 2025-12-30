import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# --- 1. إعدادات قاعدة البيانات ---
def get_connection():
    conn = sqlite3.connect("web_store_inventory.db", check_same_thread=False)
    return conn

def setup_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            quantity REAL,
            unit TEXT,
            location TEXT,
            date_added TEXT
        )
    """)
    conn.commit()
    conn.close()

# --- 2. إعدادات واجهة المستخدم (Streamlit) ---
st.set_page_config(page_title="نظام جرد المغازة الحديث", layout="wide")

# تصميم CSS بسيط لتحسين المظهر
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

setup_database()

# --- 3. المنطق البرمجي (CRUD) ---
def add_item(name, cat, qty, unit, loc):
    conn = get_connection()
    cursor = conn.cursor()
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO items (name, category, quantity, unit, location, date_added) VALUES (?, ?, ?, ?, ?, ?)",
                   (name, cat, qty, unit, loc, date_now))
    conn.commit()
    conn.close()

def delete_item(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id=?", (id,))
    conn.commit()
    conn.close()

# --- 4. هيكل التطبيق (Layout) ---

st.title("📦 نظام إدارة جرد مغازة الأشغال")
st.markdown("---")

# القائمة الجانبية لإدخال البيانات
with st.sidebar:
    st.header("➕ إضافة سلعة جديدة")
    with st.form("input_form", clear_on_submit=True):
        name = st.text_input("اسم السلعة")
        category = st.selectbox("الفئة", ["مواد بناء", "كهرباء", "سباكة", "معدات ثقيلة", "أدوات يدوية"])
        quantity = st.number_input("الكمية", min_value=0.0, step=0.1)
        unit = st.text_input("الوحدة (كغ، قطعة، متر...)")
        location = st.text_input("مكان التخزين")
        submit = st.form_submit_button("إضافة للمخزن")
        
        if submit:
            if name:
                add_item(name, category, quantity, unit, location)
                st.success(f"تمت إضافة {name} بنجاح")
            else:
                st.error("يرجى إدخال اسم السلعة")

# جلب البيانات للعرض والتحليل
conn = get_connection()
df = pd.read_sql("SELECT * FROM items", conn)
conn.close()

# --- 5. لوحة الإحصائيات (Analytics Dashboard) ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("إجمالي الأصناف", len(df))
with col2:
    low_stock = len(df[df['quantity'] < 5])
    st.metric("أصناف منخفضة المخزون", low_stock, delta_color="inverse")
with col3:
    total_qty = df['quantity'].sum()
    st.metric("إجمالي الكميات", f"{total_qty:,.0f}")

st.markdown("### 📊 تحليل المخزون")
if not df.empty:
    fig = px.bar(df, x="name", y="quantity", color="category", 
                 title="كميات السلع حسب الفئة", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# --- 6. جدول البيانات والبحث ---
st.markdown("### 📋 سجل الجرد الحالي")
search_query = st.text_input("🔍 بحث سريع بالاسم أو الفئة")
if search_query:
    df_display = df[df['name'].str.contains(search_query, case=False) | 
                    df['category'].str.contains(search_query, case=False)]
else:
    df_display = df

st.dataframe(df_display, use_container_width=True)

# خيار الحذف
if not df_display.empty:
    st.markdown("---")
    col_del1, col_del2 = st.columns([1, 3])
    with col_del1:
        id_to_delete = st.number_input("أدخل ID للحذف", min_value=1, step=1)
        if st.button("🗑️ حذف السلعة"):
            delete_item(id_to_delete)
            st.warning(f"تم حذف السلعة رقم {id_to_delete}")
            st.rerun()

# تصدير البيانات (مهم جداً لمحلل البيانات)
st.sidebar.markdown("---")
csv = df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="📥 تحميل الجرد كملف CSV",
    data=csv,
    file_name='inventory_report.csv',
    mime='text/csv',
)
