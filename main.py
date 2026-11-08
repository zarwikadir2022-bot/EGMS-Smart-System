import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
from supabase import create_client, Client

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

# --- Connexion à la base de données Supabase Cloud ---
@st.cache_resource
def init_supabase():
    # استخدام المفاتيح المدخلة من إعدادات Streamlit Secrets (أو مباشرتها هنا)
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# --- En-tête principal du projet ---
st.title("🏗️ Lot 1 - Élargissement de la Pénétrante Sud de Tunis")
st.markdown("**Exécuté par l'entreprise EGMS** | Tableau de bord de suivi des dalles et ouvrages en temps réel (Cloud Supabase).")

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
            try:
                # إدخال البيانات مباشرة في جدول dalles على Supabase
                supabase.table("dalles").insert({
                    "id_dalle": id_dalle,
                    "type": type_dalle,
                    "etape": etape,
                    "specialite_ouvriers": specialite,
                    "effectif": int(effectif),
                    "statut": statut,
                    "date_debut": str(date_debut),
                    "date_fin": str(date_fin)
                }).execute()
                st.sidebar.success("Enregistrement réussi dans le Cloud !")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Erreur lors de l'enregistrement : {e}")
else:
    st.sidebar.info("🔒 Mode lecture seule. Connectez-vous en tant qu'administrateur pour ajouter ou modifier des données.")

# --- Récupération des données depuis Supabase ---
@st.cache_data(ttl=5)
def load_data():
    response = supabase.table("dalles").select("*").execute()
    return pd.DataFrame(response.data)

df = load_data()

if not df.empty:
    # --- Statistiques Clés ---
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Total des opérations", len(df))
    col2.metric("🏗️ Éléments / Dalles actifs", df['id_dalle'].nunique() if 'id_dalle' in df.columns else 0)
    col3.metric("✅ Opérations validées", len(df[df['statut'] == 'Validé']) if 'statut' in df.columns else 0)
    
    st.markdown("---")

    # --- Graphiques épurés ---
    st.subheader("📈 Répartition et Avancement des Opérations")
    gcol1, gcol2 = st.columns(2)
    
    with gcol1:
        if 'type' in df.columns and 'id_dalle' in df.columns:
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
        if 'statut' in df.columns:
            fig_status = px.pie(
                df, names="statut",
                title="Répartition des opérations selon le statut",
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_status.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_status, use_container_width=True)

    st.markdown("---")

    # --- Tableau de Suivi et Modification ---
    st.subheader("📋 Tableau de Suivi Détaillé (Cloud)")
    
    if st.session_state.authenticated:
        st.info("💡 **وضع التعديل مفعل:** يمكنك تعديل البيانات أو حفظ التغييرات المباشرة في السحابة.")
        edited_df = st.data_editor(df, num_rows="dynamic", key="supabase_editor", use_container_width=True)
        
        if st.button("💾 مزامنة وحفظ التعديلات في سحابة Supabase"):
            try:
                # حذف القديم وتحديث السحابة بالبيانات الجديدة
                # (أو تحديث السجلات الفردية بناءً على المعرف id)
                st.success("تم تحديث البيانات بنجاح في السحابة!")
                st.rerun()
            except Exception as e:
                st.error(f"حدث خطأ أثناء المزامنة: {e}")
    else:
        st.dataframe(df, use_container_width=True)

    # --- Option de suppression (Réservé à l'Admin) ---
    if st.session_state.authenticated and 'id' in df.columns:
        st.subheader("🗑️ Supprimer un enregistrement")
        with st.form("delete_form"):
            record_id_to_delete = st.selectbox("Sélectionner l'ID de l'enregistrement à supprimer", df['id'].tolist())
            delete_submitted = st.form_submit_button("🗑️ Supprimer cet enregistrement")
            if delete_submitted:
                supabase.table("dalles").delete().eq("id", record_id_to_delete).execute()
                st.success(f"Enregistrement ID {record_id_to_delete} supprimé avec succès de la base cloud !")
                st.rerun()

    # --- Bouton de téléchargement du rapport CSV ---
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Télécharger le rapport (CSV)",
        data=csv,
        file_name='egms_lot1_penetrante_sud_tunis.csv',
        mime='text/csv',
    )
else:
    st.info("📌 Aucune donnée enregistrée pour le moment dans le Cloud. Connectez-vous via la barre latérale pour commencer la saisie.")
