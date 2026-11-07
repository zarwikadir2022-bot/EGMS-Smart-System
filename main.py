
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text

# Configuration de la page
st.set_page_config(
    page_title="Gestion du Pont - Gholoul",
    page_icon="🏗️",
    layout="wide"
)

# Style CSS professionnel
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #0056b3;
    }
    </style>
""", unsafe_allow_html=True)

# --- إعداد الاتصال بقاعدة بيانات SQL السحابية ---
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error(f"Erreur de configuration de la base de données: {e}")

# إنشاء الجدول تلقائياً إذا لم يكن موجوداً
def init_db():
    try:
        with conn.session as s:
            s.execute(text('''
                CREATE TABLE IF NOT EXISTS poutres (
                    id SERIAL PRIMARY KEY,
                    id_poutre TEXT,
                    type TEXT,
                    etape TEXT,
                    specialite_ouvriers TEXT,
                    effectif INTEGER,
                    statut TEXT,
                    date TEXT
                );
            '''))
            s.commit()
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation de la table: {e}")

init_db()

# --- جلب البيانات من SQL ---
def load_data():
    try:
        df = conn.query("SELECT * FROM poutres;", ttl=0)
        if not df.empty and "id" in df.columns:
            df = df.drop(columns=["id"])
        else:
            df = pd.DataFrame(columns=["id_poutre", "type", "etape", "specialite_ouvriers", "effectif", "statut", "date"])
        
        df = df.rename(columns={
            "id_poutre": "ID_Poutre",
            "type": "Type",
            "etape": "Etape",
            "specialite_ouvriers": "Specialite_Ouvriers",
            "effectif": "Effectif",
            "statut": "Statut",
            "date": "Date"
        })
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement des données SQL: {e}")
        return pd.DataFrame(columns=["ID_Poutre", "Type", "Etape", "Specialite_Ouvriers", "Effectif", "Statut", "Date"])

# --- حفظ صف جديد في SQL ---
def save_data_row(poutre_id, p_type, etape, specialite, effectif, statut, date_saisie):
    try:
        with conn.session as s:
            s.execute(
                text('''
                INSERT INTO poutres (id_poutre, type, etape, specialite_ouvriers, effectif, statut, date)
                VALUES (:poutre_id, :p_type, :etape, :specialite, :effectif, :statut, :date_saisie)
                '''),
                {
                    "poutre_id": poutre_id,
                    "p_type": p_type,
                    "etape": etape,
                    "specialite": specialite,
                    "effectif": int(effectif),
                    "statut": statut,
                    "date_saisie": str(date_saisie)
                }
            )
            s.commit()
        return True
    except Exception as e:
        st.error(f"Erreur lors de l'enregistrement: {e}")
        return False

# --- مسح الجدول بالكامل ---
def clear_all_data():
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM poutres;"))
            s.commit()
        return True
    except Exception as e:
        st.error(f"Erreur lors de la réinitialisation: {e}")
        return False

df = load_data()

# --- Barre latérale (Sidebar) - Espace Admin ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/constructor.png", width=70)
    st.title("Panneau de Contrôle")
    st.markdown("---")
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.subheader("🔑 Connexion Admin")
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        
        if st.button("Se connecter", use_container_width=True):
            if username == "gholoul_admin" and password == "12345":
                st.session_state.authenticated = True
                st.success("Connexion réussie !")
                st.rerun()
            else:
                st.error("Identifiants incorrects.")
    else:
        st.success("👤 Administrateur (SQL Cloud)")
        if st.button("Se déconnecter", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
            
        st.markdown("---")
        st.subheader("➕ Saisie & Mise à Jour")
        
        with st.form("add_form", clear_on_submit=True):
            poutre_id = st.text_input("ID de la Poutre (ex: DP1-01)")
            p_type = st.selectbox("Type de Poutre", ["DP1", "DP2", "DP3", "DP4", "DP5"])
            
            etape = st.selectbox("Étape Actuelle", [
                "Coffrage", 
                "Ferraillage", 
                "Coulage", 
                "Décoffrage"
            ])
            
            specialite = st.selectbox("Spécialité des Ouvriers", [
                "Coffreurs", 
                "Ferrailleurs", 
                "Équipe Béton", 
                "Équipe Mixte"
            ])
            
            effectif = st.number_input("Nombre d'ouvriers", min_value=1, max_value=100, value=5)
            
            statut = st.selectbox("Statut des Travaux", [
                "En Cours", 
                "Terminé / Réceptionné", 
                "En Attente / Bloqué"
            ])
            
            date_saisie = st.date_input("Date de l'opération")
            
            submitted = st.form_submit_button("Enregistrer sur SQL", use_container_width=True)
            if submitted:
                if poutre_id:
                    if save_data_row(poutre_id, p_type, etape, specialite, effectif, statut, date_saisie):
                        st.success(f"Poutre {poutre_id} enregistrée avec succès !")
                        st.rerun()
                else:
                    st.warning("Veuillez entrer l'ID de la poutre.")

# --- Interface Principale ---
st.title("🏗️ Tableau de Bord - Projet Pont Gholoul")
st.markdown("Connecté à une base de données SQL Cloud (Supabase) - Suivi des opérations en temps réel.")
st.markdown("---")

if not df.empty and "ID_Poutre" in df.columns and len(df.dropna(subset=["ID_Poutre"])) > 0:
    # 1. KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    total_poutres = df["ID_Poutre"].nunique()
    total_workers = int(df["Effectif"].sum()) if "Effectif" in df.columns else 0
    completed_works = len(df[df["Statut"].str.contains("Terminé", na=False)])
    ongoing_works = len(df[df["Statut"].str.contains("En Cours", na=False)])
    
    col1.metric(label="📊 Total Poutres", value=total_poutres)
    col2.metric(label="👷 Total Ouvriers", value=total_workers)
    col3.metric(label="✅ Terminés / Réceptionnés", value=completed_works)
    col4.metric(label="🔄 En Cours", value=ongoing_works)
    
    st.markdown("---")
    
    # 2. Charts
    st.subheader("📈 Analyses Globales du Chantier")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_spec = px.pie(
            df, 
            names='Specialite_Ouvriers', 
            values='Effectif',
            title="Répartition de la Main-d'œuvre par Spécialité",
            hole=0.4, 
            color_discrete_sequence=px.colors.sequential.Blues_r
        )
        fig_spec.update_layout(margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_spec, use_container_width=True)
        
    with col_chart2:
        fig_status = px.bar(
            df, 
            x='Type', 
            y='Effectif', 
            color='Statut',
            title="Volume de Main-d'œuvre par Type de Poutre et Statut",
            barmode='stack',
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_status.update_layout(margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_status, use_container_width=True)

    st.markdown("---")

    # 3. Tabs DP1 - DP5
    st.subheader("📑 Sections Détaillées par Type de Poutre (DP1 - DP5)")
    
    poutre_types = ["DP1", "DP2", "DP3", "DP4", "DP5"]
    tabs = st.tabs([f"Type {p}" for p in poutre_types])
    
    for i, p_type in enumerate(poutre_types):
        with tabs[i]:
            df_filtered = df[df["Type"] == p_type]
            if not df_filtered.empty:
                col_t1, col_t2 = st.columns(2)
                col_t1.metric(f"Éléments {p_type} Enregistrés", len(df_filtered))
                col_t2.metric(f"Ouvriers sur {p_type}", int(df_filtered["Effectif"].sum()))
                
                st.dataframe(df_filtered, use_container_width=True)
                
                fig_sub = px.bar(
                    df_filtered, 
                    x='ID_Poutre', 
                    y='Effectif', 
                    color='Etape',
                    title=f"Détails des étapes pour le {p_type}",
                    color_discrete_sequence=px.colors.sequential.Teal
                )
                st.plotly_chart(fig_sub, use_container_width=True)
            else:
                st.info(f"Aucune donnée enregistrée pour le type {p_type}.")

    st.markdown("---")
    
    # 4. Table
    st.subheader("📋 Registre Technique Général")
    st.dataframe(df, use_container_width=True)
    
    if st.session_state.authenticated:
        if st.button("🗑️ Vider la base de données SQL", type="secondary"):
            if clear_all_data():
                st.success("Base de données vidée avec succès.")
                st.rerun()

else:
    st.info("📌 La base de données SQL est actuellement vide. Connectez-vous via la barre latérale pour ajouter le premier élément.")
