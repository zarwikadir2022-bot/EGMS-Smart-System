import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import plotly.express as px

# --- إعداد الصفحة بتصميم عصري ---
st.set_page_config(
    page_title="Projet Pont Gholoul - Suivi des Dalles",
    page_icon="🏗️",
    layout="wide"
)

# --- تنسيقات CSS عصرية بخلفية جليدية (Glassmorphism) ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #e0f2fe 0%, #f0fdf4 50%, #eef2ff 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    div[data-testid="stMetric"], .stMetric {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.4);
    }
    h1, h2, h3 {
        color: #1e293b;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# --- إعداد قاعدة البيانات المحلية SQLite (مع تواريخ البدء والانتهاء) ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('gholoul_dalles_v2.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dalles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_dalle TEXT,
            type TEXT,
            etape TEXT,
            specialite_ouvriers TEXT,
            effectif INTEGER,
            statut TEXT,
            date_debut TEXT,
            date_fin TEXT
        );
    ''');
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- عنوان التطبيق الرئيسي ---
st.title("🏗️ Tableau de Bord - Suivi des Dalles (Pont Gholoul)")
st.markdown("لوحة التحكم الذكية لمتابعة دالات القنطرة (DP1 - DP5) مع التفاصيل اليومية للعمال والتواريخ.")

# --- الشريط الجانبي للإدخال ---
st.sidebar.header("📌 تسجيل دالة وتواريخ العمل")
with st.sidebar.form("dalle_form", clear_on_submit=True):
    id_dalle = st.selectbox("معرف الدالة (Composant)", ["DP1", "DP2", "DP3", "DP4", "DP5"])
    type_dalle = st.selectbox("نوع العمل", ["Coffrage", "Ferraillage", "Coulage", "Pose"])
    etape = st.selectbox("المرحلة", ["Préparation", "En cours", "Terminé"])
    specialite = st.text_input("تخصص العمال", "بنّاء / حدّاد / مساح")
    
    # عدد العمال التفصيلي لهذا اليوم/المهمة
    effectif = st.number_input("عدد العمال في هذا اليوم (Effectif)", min_value=1, value=6)
    
    # تواريخ البدء والانتهاء
    date_debut = st.date_input("تاريخ البدء (Date de début)", value=date.today())
    date_fin = st.date_input("تاريخ الانتهاء (Date de fin)", value=date.today())
    
    statut = st.selectbox("الحالة", ["Actif", "En attente", "Validé"])
    
    submitted = st.form_submit_button("💾 حفظ البيانات")
    if submitted:
        cursor.execute('''
            INSERT INTO dalles (id_dalle, type, etape, specialite_ouvriers, effectif, statut, date_debut, date_fin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (id_dalle, type_dalle, etape, specialite, effectif, statut, str(date_debut), str(date_fin)))
        conn.commit()
        st.sidebar.success("تم تسجيل بيانات الدالة بنجاح!")

# --- جلب البيانات وعرضها ---
df = pd.read_sql("SELECT * FROM dalles", conn)

if not df.empty:
    # --- قسم الإحصائيات (بدون جمع عشوائي للعمال) ---
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 إجمالي العمليات المسجلة", len(df))
    col2.metric("🏗️ الدالات النشطة", df['id_dalle'].nunique())
    col3.metric("✅ العمليات المكتملة", len(df[df['statut'] == 'Validé']))
    
    st.markdown("---")

    # --- الرسوم البيانية التفاعلية الملونة لتطور العمال حسب التواريخ ---
    st.subheader("📈 تتبع عدد العمال اليومي وتوزيع العمليات")
    gcol1, gcol2 = st.columns(2)
    
    with gcol1:
        # رسم بياني يوضح عدد العمال لكل دالة وتاريخ بدء
        fig_effectif = px.bar(
            df, x="date_debut", y="effectif", color="id_dalle",
            title="عدد العمال التفصيلي حسب تواريخ العمل والدالات",
            labels={"date_debut": "تاريخ البدء", "effectif": "عدد العمال"},
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_effectif.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_effectif, use_container_width=True)
        
    with gcol2:
        # رسم بياني دائري يوضح حالات العمليات
        fig_status = px.pie(
            df, names="statut", values="effectif",
            title="توزيع حصص العمال حسب حالات العمليات",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_status.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_status, use_container_width=True)

    st.markdown("---")

    # --- جدول البيانات المفصل متضمن تواريخ البدء والانتهاء وعمال كل يوم ---
    st.subheader("📋 جدول المتابعة المفصل (التواريخ والعمال)")
    st.dataframe(df, use_container_width=True)
    
    # --- زر تصدير البيانات ---
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 تحميل تقرير الدالات والعمال (CSV)",
        data=csv,
        file_name='gholoul_dalles_details.csv',
        mime='text/csv',
    )
else:
    st.info("📌 لا توجد بيانات مسجلة حتى الآن. استخدم القائمة الجانبية لإضافة أول دالة (DP1 - DP5) مع تواريخ العمل وعدد العمال التفصيلي.")
