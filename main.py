import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.io as pio
from fpdf import FPDF
from datetime import datetime
import io

# --- 1. إعدادات قاعدة البيانات ---
def get_connection():
    return sqlite3.connect("web_store_inventory.db", check_same_thread=False)

# --- 2. دالة إنشاء تقرير PDF ---
def generate_pdf(df, fig):
    pdf = FPDF()
    pdf.add_page()
    
    # العنوان
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(190, 15, "EGMS Inventory Report", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(190, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    # قسم الإحصائيات (Statistical Summary)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "1. Executive Summary", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(190, 8, f"- Total Items: {len(df)}", ln=True)
    pdf.cell(190, 8, f"- Total Quantity in Store: {df['quantity'].sum():,.2f}", ln=True)
    pdf.cell(190, 8, f"- Low Stock Items (< 5 units): {len(df[df['quantity'] < 5])}", ln=True)
    pdf.ln(10)

    # إضافة الرسم البياني (Convert Plotly to Image)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "2. Inventory Distribution Chart", ln=True)
    
    # تحويل الرسم إلى صورة بجودة عالية
    img_bytes = pio.to_image(fig, format="png", width=800, height=450, scale=2)
    img_buf = io.BytesIO(img_bytes)
    pdf.image(img_buf, x=15, w=180)
    pdf.ln(5)

    # جدول البيانات (Data Table)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "3. Detailed Inventory List", ln=True)
    pdf.ln(5)
    
    # رؤوس الجدول
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(40, 10, "Item Name", 1, 0, 'C', True)
    pdf.cell(40, 10, "Category", 1, 0, 'C', True)
    pdf.cell(30, 10, "Qty", 1, 0, 'C', True)
    pdf.cell(30, 10, "Unit", 1, 0, 'C', True)
    pdf.cell(50, 10, "Location", 1, 1, 'C', True)

    # تعبئة الجدول
    pdf.set_font("Arial", size=9)
    for index, row in df.iterrows():
        pdf.cell(40, 8, str(row['name']), 1)
        pdf.cell(40, 8, str(row['category']), 1)
        pdf.cell(30, 8, str(row['quantity']), 1, 0, 'C')
        pdf.cell(30, 8, str(row['unit']), 1, 0, 'C')
        pdf.cell(50, 8, str(row['location']), 1, 1)

    return pdf.output(dest='S').encode('latin-1')

# --- 3. واجهة البرنامج ---
st.title("📦 نظام جرد المغازة المطور v77")

conn = get_connection()
df = pd.read_sql("SELECT * FROM items", conn)
conn.close()

if not df.empty:
    # إنشاء الرسم البياني للتحليل
    fig = px.bar(df, x="name", y="quantity", color="category", title="Inventory Levels")
    st.plotly_chart(fig, use_container_width=True)

    # زر التحميل في القائمة الجانبية
    st.sidebar.markdown("---")
    st.sidebar.subheader("🖨️ تصدير التقارير")
    
    if st.sidebar.button("توليد تقرير PDF"):
        try:
            with st.spinner('جاري إنشاء التقرير...'):
                pdf_output = generate_pdf(df, fig)
                st.sidebar.download_button(
                    label="📥 تحميل ملف PDF الآن",
                    data=pdf_output,
                    file_name=f"Inventory_Report_{datetime.now().strftime('%Y%md')}.pdf",
                    mime="application/pdf"
                )
                st.sidebar.success("تم تجهيز التقرير بنجاح!")
        except Exception as e:
            st.sidebar.error(f"خطأ في المكتبات: {e}")
            st.sidebar.info("تأكد من تثبيت مكتبة 'kaleido' لتحويل الرسوم إلى صور.")
else:
    st.info("المخزن فارغ حالياً. قم بإضافة بيانات لتمكين التقارير.")
