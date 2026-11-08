import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import plotly.express as px

# --- Configuration de la page ---
st.set_page_config(
    page_title="Lot 1 - Pénétrante Sud de Tunis (EGMS)",
    page_icon="🏗️",
    layout="wide"
)

# --- Styles CSS (Thème Glacial / Glassmorphism) ---
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

# --- Initialisation de la base de données SQLite (EGMS Lot 1) ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('egms_lot1_dalles.db', check_same_thread=False)
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

# --- En-tête principal du projet ---
st.title("🏗️ Lot 1 - Élargissement de la Pénétrante Sud de Tunis")
st.markdown("**Exécuté par l'entreprise EGMS** | Tableau de bord de suivi des dalles et ouvrages en temps réel.")

# --- Espace Connexion Administrateur dans la barre latérale ---
st.sidebar.header("🔐 Espace Administrateur (EGMS)")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    with st.sidebar.form("login_form"):
        admin_pass = st.text_input("Mot de passe administrateur", type="password")
        login_btn = st.form_submit_button("Se connecter")
        if login_btn:
            if admin_pass == "Kadirman1986":
                st.session_state.authenticated = True
                st.sidebar.success("Connexion réussie !")
                st.rerun()
            else:
                st.sidebar.error("Mot de passe incorrect !")
else:
    st.sidebar.success("Bienvenue, Administrateur")
    if st.sidebar.button("Se déconnecter (Logout)"):
        st.session_state.authenticated = False
        st.rerun()

st.sidebar.markdown("---")

# --- Formulaire d'insertion (Réservé à l'Admin) ---
if st.session_state.authenticated:
    st.sidebar.header("📌 Saisie d'une nouvelle dalle")
    with st.sidebar.form("dalle_form", clear_on_submit=True):
        id_dalle = st.text_input("Identifiant de la dalle / Élément (Ex: DP1-1, DP1-2)", value="DP1-1")
        type_dalle = st.selectbox("Type de travaux", ["Coffrage", "Ferraillage", "Coulage", "Pose"])
        etape = st.selectbox("Étape", ["Préparation", "En cours", "Terminé"])
        specialite = st.text_input("Spécialité des ouvriers", "Maçon / Ferrailleur / Topographe")
        effectif = st.number_input("Effectif journalier", min_value=1, value=6)
        date_debut = st.date_input("Date de début", value=date.today())
        date_fin = st.date_input("Date de fin", value=date.today())
        statut = st.selectbox("Statut", ["Actif", "En attente", "Validé"])
        
        submitted = st.form_submit_button("💾 Enregistrer les données")
        if submitted:
            cursor.execute('''
                INSERT INTO dalles (id_dalle, type, etape, specialite_ouvriers, effectif, statut, date_debut, date_fin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id_dalle, type_dalle, etape, specialite, effectif, statut, str(date_debut), str(date_fin)))
            conn.commit()
            st.sidebar.success("Enregistrement réussi !")
            st.rerun()
else:
    st.sidebar.info("🔒 Mode lecture seule. Connectez-vous en tant qu'administrateur pour ajouter ou modifier des données.")

# --- Récupération des données depuis SQLite ---
df = pd.read_sql("SELECT * FROM dalles", conn)

if not df.empty:
    # --- Statistiques Clés ---
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Total des opérations", len(df))
    col2.metric("🏗️ Éléments / Dalles actifs", df['id_dalle'].nunique())
    col3.metric("✅ Opérations validées", len(df[df['statut'] == 'Validé']))
    
    st.markdown("---")

    # --- Graphiques épurés ---
    st.subheader("📈 Répartition et Avancement des Opérations")
    gcol1, gcol2 = st.columns(2)
    
    with gcol1:
        fig_type = px.histogram(
            df, x="type", color="id_dalle",
            title="Nombre d'opérations par type de travaux",
            labels={"type": "Type de travaux", "count": "Nombre"},
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_type.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_type, use_container_width=True)
        
    with gcol2:
        fig_status = px.pie(
            df, names="statut",
            title="Répartition des opérations selon le statut",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_status.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_status, use_container_width=True)

    st.markdown("---")

    # --- Tableau de Suivi et Modification (Direct si Admin, Lecture seule sinon) ---
    st.subheader("📋 Tableau de Suivi Détaillé")
    
    if st.session_state.authenticated:
        st.info("💡 **وضع التعديل مفعل:** يمكنك تعديل أي خلية مباشرة في الجدول أدناه، ثم الضغط على زر الحفظ.")
        
        # استخدام st.data_editor لتعديل البيانات مباشرة
        edited_df = st.data_editor(df, num_rows="dynamic", key="dalle_editor", use_container_width=True)
        
        if st.button("💾 حفظ التعديلات في قاعدة البيانات"):
            try:
                # إعادة كتابة الجدول بالكامل في قاعدة البيانات بناءً على التعديلات
                cursor.execute("DELETE FROM dalles;")
                for index, row in edited_df.iterrows():
                    cursor.execute('''
                        INSERT INTO dalles (id, id_dalle, type, etape, specialite_ouvriers, effectif, statut, date_debut, date_fin)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (row['id'], row['id_dalle'], row['type'], row['etape'], row['specialite_ouvriers'], int(row['effectif']), row['statut'], str(row['date_debut']), str(row['date_fin'])))
                conn.commit()
                st.success("تم حفظ جميع التعديلات بنجاح!")
                st.rerun()
            except Exception as e:
                st.error(f"حدث خطأ أثناء الحفظ: {e}")
    else:
        st.dataframe(df, use_container_width=True)

    # --- Bouton de téléchargement du rapport CSV ---
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Télécharger le rapport (CSV)",
        data=csv,
        file_name='egms_lot1_penetrante_sud_tunis.csv',
        mime='text/csv',
    )
else:
    st.info("📌 Aucune donnée enregistrée pour le moment. Connectez-vous via la barre latérale pour commencer la saisie.")
