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

# --- إعداد قاعدة البيانات المحلية SQLite (مع إمكانية الحذف والإدارة) ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('gholoul_dalles_v3.db', check_same_thread=False)
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
    ''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- عنوان التطبيق الرئيسي ---
st.title("🏗️ Tableau de Bord - Suivi des Dalles (Pont Gholoul)")
st.markdown("لوحة التحكم الذكية لمتابعة أجزاء ودالات القنطرة (مثل DP1-1, DP1-2) مع التفاصيل اليومية للعمال والتواريخ.")

# --- نظام تسجيل الدخول في الشريط الجانبي ---
st.sidebar.header("🔐 بوابة المشرف (Admin Login)")

# تهيئة حالة الجلسة (Session State) لتسجيل الدخول
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    with st.sidebar.form("login_form"):
        admin_pass = st.text_input("كلمة مرور المسؤول", type="password")
        login_btn = st.form_submit_button("تسجيل الدخول")
        if login_btn:
            # كلمة المرور الخاصة بك (يمكنك تغييرها هنا متى شئت)
            if admin_pass == "Kadirman1986":
                st.session_state.authenticated = True
                st.sidebar.success("تم تسجيل الدخول بنجاح!")
                st.rerun()
            else:
                st.sidebar.error("كلمة المرور غير صحيحة!")
else:
    st.sidebar.success("مرحباً بك، المشرف (عبد القادر)")
    if st.sidebar.button("تسجيل الخروج (Logout)"):
        st.session_state.authenticated = False
        st.rerun()

st.sidebar.markdown("---")

# --- نموذج الإدخال (متاح فقط للمشرف المسجل دخولاً) ---
if st.session_state.authenticated:
    st.sidebar.header("📌 تسجيل وتعديل دالة جديدة")
    with st.sidebar.form("dalle_form", clear_on_submit=True):
        id_dalle = st.text_input("معرف الدالة / الجزء (Ex: DP1-1, DP1-2)", value="DP1-1")
        type_dalle = st.selectbox("نوع العمل", ["Coffrage", "Ferraillage", "Coulage", "Pose"])
        etape = st.selectbox("المرحلة", ["Préparation", "En cours", "Terminé"])
        specialite = st.text_input("تخصص العمال", "بنّاء / حدّاد / مساح")
        effectif = st.number_input("عدد العمال في هذا اليوم (Effectif)", min_value=1, value=6)
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
            st.rerun()
else:
    st.sidebar.info("🔒 لوحة التحكم في وضع القراءة فقط. يجوز للمشرف تسجيل الدخول لإضافة أو تعديل البيانات.")

# --- جلب البيانات وعرضها ---
df = pd.read_sql("SELECT * FROM dalles", conn)

if not df.empty:
    # --- قسم الإحصائيات ---
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 إجمالي العمليات المسجلة", len(df))
    col2.metric("🏗️ الأجزاء والدالات النشطة", df['id_dalle'].nunique())
    col3.metric("✅ العمليات المكتملة", len(df[df['statut'] == 'Validé']))
    
    st.markdown("---")

    # --- الرسوم البيانية التفاعلية ---
    st.subheader("📈 تتبع عدد العمال اليومي وتوزيع الأجزاء")
    gcol1, gcol2 = st.columns(2)
    
    with gcol1:
        fig_effectif = px.bar(
            df, x="date_debut", y="effectif", color="id_dalle",
            title="عدد العمال التفصيلي حسب تواريخ العمل وأجزاء الدالات",
            labels={"date_debut": "تاريخ البدء", "effectif": "عدد العمال"},
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_effectif.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_effectif, use_container_width=True)
        
    with gcol2:
        fig_status = px.pie(
            df, names="statut", values="effectif",
            title="توزيع حصص العمال حسب حالات العمليات",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_status.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_status, use_container_width=True)

    st.markdown("---")

    # --- جدول البيانات المفصل ---
    st.subheader("📋 جدول المتابعة المفصل (الأجزاء، التواريخ والعمال)")
    st.dataframe(df, use_container_width=True)
    
    # --- ميزة حذف السجلات (متاحة حصرياً للمشرف المسجل دخولاً) ---
    if st.session_state.authenticated:
        st.subheader("🗑️ حذف سجل أو دالة مسجلة بالخطأ")
        with st.form("delete_form"):
            record_id_to_delete = st.selectbox("أدخل رقم المعرف (ID) السجل المراد حذفه", df['id'].tolist())
            delete_submitted = st.form_submit_button("🗑️ حذف السجل المحدد")
            if delete_submitted:
                cursor.execute("DELETE FROM dalles WHERE id = ?", (record_id_to_delete,))
                conn.commit()
                st.success(f"تم حذف السجل رقم {record_id_to_delete} بنجاح!")
                st.rerun()

    # --- زر تصدير البيانات ---
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 تحميل تقرير الدالات والأجزاء (CSV)",
        data=csv,
        file_name='gholoul_dalles_subparts.csv',
        mime='text/csv',
    )
else:
    st.info("📌 لا توجد بيانات مسجلة حتى الآن. قم بتسجيل الدخول من الشريط الجانبي لإضافة البيانات الأولى.")
