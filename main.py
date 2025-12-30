import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.io as pio
from fpdf import FPDF
from datetime import datetime
import io

# --- 1. إعدادات قاعدة البيانات (v79) ---
def setup_database():
    conn = sqlite3.connect("egms_v79_final.db", check_same_thread=False)
    cursor = conn.cursor()
    # جدول المواد
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT,
            quantity REAL DEFAULT 0,
            unit TEXT,
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
    # جدول السجل التاريخي (Transactions)
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

setup_database()

def get_db_connection():
    return sqlite3.connect("egms_v79_final.db", check_same_thread=False)

# --- 2. محرك تقارير PDF ---
def generate_pdf(df, fig):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "EGMS Inventory Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    
    # تحويل الرسم لصور
    try:
        img_bytes = pio.to_image(fig, format="png", width=800, height=450, scale=2)
        pdf.image(io.BytesIO(img_bytes), x=15, w=180)
    except: pass
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(50, 10, "Item", 1); pdf.cell(40, 10, "Qty", 1); pdf.cell(40, 10, "Unit", 1); pdf.cell(60, 10, "Location", 1); pdf.ln()
    pdf.set_font("Arial", size=10)
    for _, row in df.iterrows():
        pdf.cell(50, 8, str(row['name']), 1)
        pdf.cell(40, 8, str(row['quantity']), 1)
        pdf.cell(40, 8, str(row['unit']), 1)
        pdf.cell(60, 8, str(row['location']), 1); pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- 3. تصميم الواجهة ---
st.set_page_config(page_title="EGMS v79 Platinum", layout="wide")
UNITS = ["وحدة", "كغ", "كيس", "لتر", "متر مربع", "متر مكعب"]

if "role" not in st.session_state:
    st.session_state.role = None

# تسجيل الدخول
if not st.session_state.role:
    st.title("🏗️ نظام EGMS - تسجيل الدخول")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("دخول"):
        if u == "admin" and p == "egms2025": st.session_state.role = "Admin"; st.rerun()
        elif u == "magaza" and p == "store2025": st.session_state.role = "Store"; st.rerun()
        else: st.error("خطأ!")
else:
    role = st.session_state.role
    st.sidebar.title(f"👤 {role}")
    if st.sidebar.button("Logout"): st.session_state.role = None; st.rerun()

    conn = get_db_connection()
    df_items = pd.read_sql("SELECT * FROM items", conn)
    df_workers = pd.read_sql("SELECT * FROM workers", conn)

    # --- واجهة مسؤول المغازة (Store) ---
    if role == "Store":
        st.header("📦 إدارة العمليات الميدانية")
        t1, t2, t3, t4 = st.tabs(["📥 تسجيل سلع", "👷 العمال", "🤝 العُهدة", "📤 استيراد CSV"])
        
        with t1: # تسجيل السلع (الذي كان مختفياً ✅)
            st.subheader("إضافة مادة جديدة أو تحديث رصيد")
            with st.form("add_item_form", clear_on_submit=True):
                mode = st.radio("الوضع", ["مادة جديدة", "تحديث موجود"])
                name = st.selectbox("اختر المادة", df_items['name'].tolist()) if mode == "تحديث موجود" else st.text_input("اسم المادة الجديدة")
                unit = st.selectbox("الوحدة", UNITS)
                qty = st.number_input("الكمية", min_value=0.1)
                loc = st.text_input("الموقع")
                if st.form_submit_button("حفظ"):
                    cursor = conn.cursor()
                    if mode == "مادة جديدة":
                        cursor.execute("INSERT OR IGNORE INTO items (name, unit, quantity, location) VALUES (?, ?, ?, ?)", (name, unit, qty, loc))
                    else:
                        cursor.execute("UPDATE items SET quantity = quantity + ? WHERE name = ?", (qty, name))
                    cursor.execute("INSERT INTO history (item_name, qty, type, person, timestamp) VALUES (?, ?, ?, ?, ?)", 
                                   (name, qty, "Entry", "Store", datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit(); st.success("تم الحفظ"); st.rerun()

        with t2: # العمال
            st.subheader("إدارة ملفات العمال")
            with st.form("worker_form"):
                wn = st.text_input("اسم العامل"); wp = st.text_area("خطة العمل")
                if st.form_submit_button("إضافة"):
                    conn.execute("INSERT OR IGNORE INTO workers (name, work_plan) VALUES (?, ?)", (wn, wp))
                    conn.commit(); st.success("تم!"); st.rerun()

        with t3: # العُهدة
            st.subheader("تسليم عُهدة لعامل")
            if not df_items.empty and not df_workers.empty:
                with st.form("handover"):
                    it = st.selectbox("المعدة", df_items['name'])
                    wk = st.selectbox("العامل", df_workers['name'])
                    q_h = st.number_input("الكمية", min_value=1.0)
                    if st.form_submit_button("تسليم"):
                        conn.execute("UPDATE items SET quantity = quantity - ? WHERE name = ?", (q_h, it))
                        conn.execute("INSERT INTO history (item_name, qty, type, person, timestamp) VALUES (?, ?, ?, ?, ?)", 
                                     (it, q_h, "Handover", wk, datetime.now().strftime("%Y-%m-%d %H:%M")))
                        conn.commit(); st.success("تم التسليم"); st.rerun()

    # --- واجهة المدير (Admin) ---
    elif role == "Admin":
        st.header("📊 لوحة القيادة والتحليلات")
        if not df_items.empty:
            fig = px.bar(df_items, x='name', y='quantity', color='name', title="رصيد المخزن")
            st.plotly_chart(fig, use_container_width=True)
            
            # تصدير PDF
            if st.button("توليد تقرير PDF"):
                pdf_bytes = generate_pdf(df_items, fig)
                st.download_button("تحميل التقرير", pdf_bytes, "Report.pdf", "application/pdf")
            
            st.dataframe(df_items, use_container_width=True)
        else: st.warning("المخزن فارغ")

    conn.close()
