import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.io as pio
from fpdf import FPDF
from datetime import datetime
import io

# --- 1. إعدادات قاعدة البيانات (إصلاح الخلل) ---
def setup_database():
    conn = sqlite3.connect("web_store_inventory.db", check_same_thread=False)
    cursor = conn.cursor()
    # التأكد من إنشاء الجدول قبل أي عملية قراءة
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

# استدعاء الدالة فور تشغيل التطبيق
setup_database()

def get_data():
    conn = sqlite3.connect("web_store_inventory.db", check_same_thread=False)
    df = pd.read_sql("SELECT * FROM items", conn)
    conn.close()
    return df

# --- 2. دالة توليد تقرير PDF احترافي ---
def generate_inventory_pdf(df, fig):
    pdf = FPDF()
    pdf.add_page()
    
    # رأس التقرير
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(190, 15, "EGMS Inventory & Analytics Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    # الرسوم البيانية (Charts)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "1. Stock Visual Analytics", ln=True)
    
    # تحويل Plotly إلى صورة للـ PDF
    try:
        img_bytes = pio.to_image(fig, format="png", width=800, height=450, scale=2)
        img_buf = io.BytesIO(img_bytes)
        pdf.image(img_buf, x=15, w=180)
    except Exception:
        pdf.cell(190, 10, "(Chart visualization requires 'kaleido' library)", ln=True)
    
    pdf.ln(10)

    # جدول البيانات
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "2. Detailed Stock List", ln=True)
    pdf.ln(5)
    
    # تصميم الجدول
    pdf.set_fill_color(0, 51, 102) # أزرق داكن
    pdf.set_text_color(255, 255, 255) # أبيض
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(50, 10, "Item Name", 1, 0, 'C', True)
    pdf.cell(40, 10, "Category", 1, 0, 'C', True)
    pdf.cell(30, 10, "Qty", 1, 0, 'C', True)
    pdf.cell(70, 10, "Location", 1, 1, 'C', True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=9)
    for _, row in df.iterrows():
        pdf.cell(50, 8, str(row['name']), 1)
        pdf.cell(40, 8, str(row['category']), 1)
        pdf.cell(30, 8, str(row['quantity']), 1, 0, 'C')
        pdf.cell(70, 8, str(row['location']), 1, 1)

    return pdf.output(dest='S').encode('latin-1')

# --- 3. واجهة المستخدم ---
st.title("🏗️ EGMS Digital ERP v78")

# جلب البيانات بأمان
df = get_data()

# عرض الإحصائيات إذا وجدت بيانات
if not df.empty:
    st.success("✅ تم الاتصال بقاعدة البيانات بنجاح")
    
    # الرسم البياني
    fig = px.bar(df, x="name", y="quantity", color="category", 
                 title="Inventory Levels by Item", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # زر تحميل PDF في القائمة الجانبية
    st.sidebar.header("🖨️ التقارير الإدارية")
    if st.sidebar.button("توليد تقرير PDF الموثق"):
        pdf_file = generate_inventory_pdf(df, fig)
        st.sidebar.download_button(
            label="📥 تحميل التقرير الآن",
            data=pdf_file,
            file_name=f"EGMS_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
else:
    st.warning("📊 قاعدة البيانات جاهزة ولكنها فارغة. يرجى إضافة سلع جديدة للبدء.")
    st.info("💡 نصيحة: استخدم القائمة الجانبية لإضافة السلع.")

# (كود الإضافة والبحث يظل كما هو في النسخة v77 لضمان الاستقرار)
