import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import io

# --- 1. إعدادات قاعدة البيانات ---
def setup_database():
    conn = sqlite3.connect("web_store_inventory.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            quantity REAL,
            price REAL,
            unit TEXT,
            location TEXT,
            date_added TEXT
        )
    """)
    conn.commit()
    conn.close()

setup_database()

def get_db_connection():
    return sqlite3.connect("web_store_inventory.db", check_same_thread=False)

# --- 2. تنسيق الواجهة الرسومية (UI) ---
st.set_page_config(page_title="EGMS Web Inventory", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .metric-card {
        background-color: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #0067c0;
    }
    h1, h2 { color: #003366; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. نظام الدخول الصلاحيات ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🏗️ نظام EGMS - تسجيل الدخول")
    with st.container():
        user = st.text_input("اسم المستخدم")
        pw = st.text_input("كلمة المرور", type="password")
        if st.button("دخول"):
            if user == "admin" and pw == "egms2025":
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("❌ بيانات الدخول غير صحيحة")
else:
    # --- الواجهة الرئيسية ---
    st.sidebar.title("🛠️ لوحة التحكم")
    menu = st.sidebar.radio("الانتقال إلى:", ["📊 التحليلات والرسوم", "📋 إدارة الجرد", "➕ إضافة سلع جديدة"])
    
    conn = get_db_connection()
    df = pd.read_sql("SELECT *, (quantity * price) as total_value FROM items", conn)
    
    # --- التبويب الأول: التحليلات ---
    if menu == "📊 التحليلات والرسوم":
        st.title("📊 لوحة تحليلات المغازة الذكية")
        
        # بطاقات KPI
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="metric-card"><h5>إجمالي الأصناف</h5><h2>{len(df)}</h2></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="metric-card"><h5>قيمة المخزون (د.ت)</h5><h2>{df["total_value"].sum() if not df.empty else 0:,.2f}</h2></div>', unsafe_allow_html=True)
        with c3: 
            low_stock = len(df[df['quantity'] < 5])
            st.markdown(f'<div class="metric-card"><h5>أصناف منخفضة</h5><h2 style="color:red;">{low_stock}</h2></div>', unsafe_allow_html=True)

        if not df.empty:
            st.divider()
            col_a, col_b = st.columns(2)
            
            # رسم بياني تفاعلي للفئات
            fig_pie = px.pie(df, values='total_value', names='category', hole=0.4, title="توزيع رأس المال حسب الفئة")
            col_a.plotly_chart(fig_pie, use_container_width=True)
            
            # رسم بياني للكميات
            fig_bar = px.bar(df.nlargest(10, 'quantity'), x='name', y='quantity', color='category', title="أعلى 10 سلع توفراً")
            col_b.plotly_chart(fig_bar, use_container_width=True)

    # --- التبويب الثاني: إدارة الجرد ---
    elif menu == "📋 إدارة الجرد":
        st.title("📋 سجل الجرد الحي")
        search = st.text_input("🔍 ابحث في المخزن (الاسم أو الفئة أو الموقع)...")
        
        filtered_df = df[df.apply(lambda row: search.lower() in row.astype(str).str.lower().values, axis=1)] if search else df
        
        st.dataframe(filtered_df, use_container_width=True)
        
        # تصدير للتحليل
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 تصدير الجرد للتحليل (CSV)", csv, "inventory_report.csv", "text/csv")

    # --- التبويب الثالث: إضافة سلع ---
    elif menu == "➕ إضافة سلع جديدة":
        st.title("📥 تسجيل توريد جديد")
        with st.form("input_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("اسم السلعة")
            cat = c2.selectbox("الفئة", ["مواد بناء", "أدوات كهربائية", "سباكة", "معدات وقاية", "أخرى"])
            qty = c1.number_input("الكمية", min_value=0.0)
            prc = c2.number_input("سعر الوحدة (د.ت)", min_value=0.0)
            unit = c1.text_input("الوحدة (كغ، قطعة...)")
            loc = c2.text_input("مكان التخزين")
            
            if st.form_submit_button("حفظ في قاعدة البيانات"):
                if name:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO items (name, category, quantity, price, unit, location, date_added) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                   (name, cat, qty, prc, unit, loc, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success(f"✅ تم تسجيل {name} بنجاح!")
                    st.rerun()
                else: st.error("يرجى إدخال الاسم")

    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.authenticated = False
        st.rerun()
    conn.close()
