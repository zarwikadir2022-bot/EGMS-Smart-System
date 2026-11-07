import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- إعداد الصفحة ---
st.set_page_config(
    page_title="Projet Pont Gholoul",
    page_icon="🏗️",
    layout="wide"
)

# --- إعداد قاعدة البيانات المحلية الآمنة ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('gholoul.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poutres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_poutre TEXT,
            type TEXT,
            etape TEXT,
            specialite_ouvriers TEXT,
            effectif INTEGER,
            statut TEXT,
            date TEXT
        );
    ''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- واجهة التطبيق ---
st.title("🏗️ Tableau de Bord - Projet Pont Gholoul")
st.markdown("suivi des opérations en temps réel pour les composants (DP1 - DP5).")

# الشريط الجانبي للإدخال
st.sidebar.header("📌 إدخال بيانات جديدة")
with st.sidebar.form("poutre_form"):
    id_poutre = st.selectbox("معرف العارضة (Composant)", ["DP1", "DP2", "DP3", "DP4", "DP5"])
    type_poutre = st.selectbox("نوع العمل", ["Coffrage", Ferraillage", "Coulage", "Pose"])
    etape = st.selectbox("المرحلة", ["Préparation", "En cours", "Terminé"])
    specialite = st.text_input("تخصص العمال", "بنّاء / حدّاد")
    effectif = st.number_input("عدد العمال (Effectif)", min_value=1, value=5)
    statut = st.selectbox("الحالة", ["Actيف", "En attente", "Validé"])
    
    submitted = st.form_submit_button("حفظ البيانات في قاعدة البيانات")
    if submitted:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute('''
            INSERT INTO poutres (id_poutre, type, etape, specialite_ouvriers, effectif, statut, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (id_poutre, type_poutre, etape, specialite, effectif, statut, date_str))
        conn.commit()
        st.sidebar.success("تم حفظ البيانات بنجاح!")

# عرض البيانات المسجلة
st.subheader("📊 جدول متابعة العوارض (Poutres)")
df = pd.read_sql("SELECT * FROM poutres", conn)

if not df.empty:
    st.dataframe(df, use_container_width=True)
    
    # إحصائيات سريعة
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي العمليات", len(df))
    col2.metric("إجمالي العمال المشاركين", int(df['effectif'].sum()))
    col3.metric("العناصر المسجلة", df['id_poutre'].nunique())
else:
    st.info("لا توجد بيانات مسجلة حالياً. استخدم القائمة الجانبية لإضافة أول عنصر.")
