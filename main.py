import streamlit as st
import folium
from streamlit_folium import st_folium

st.title("🗺️ الخريطة التفاعلية - مشروع Pénétrante Sud de Tunis (Lot 1)")
st.markdown("تتبع مواقع الأجزاء الهندسية والمنشآت على الخريطة الجغرافية.")

# إحداثيات مركز المنطقة الجنوبية لتونس / بن عروس / مسار المشروع
center_lat = 36.7550
center_lon = 10.2100

# 1. إنشاء كائن الخريطة تمركزه حول موقع المشروع
m = folium.Map(
    location=[center_lat, center_lon], 
    zoom_start=13,
    tiles="CartoDB positron" # تصميم عصري ونظيف للخريطة يناسب واجهات المكاتب الهندسية
)

# 2. إضافة علامات (Markers) لمكونات المشروع (يمكن جلبها لاحقاً من قاعدة بيانات Supabase)
# مثال لموقع دالة أو منشأة أولى
folium.Marker(
    location=[36.7620, 10.2080],
    popup="<b>Élément: DP1-1</b><br>Type: Coffrage / Coulage<br>Statut: Actif",
    tooltip="انقر لعرض تفاصيل الدالة DP1-1",
    icon=folium.Icon(color="red", icon="wrench", prefix="fa")
).add_to(m)

# مثال لموقع منشأة ثانية
folium.Marker(
    location=[36.7480, 10.2150],
    popup="<b>Élément: DP1-2</b><br>Type: Ferraillage<br>Statut: En cours",
    tooltip="انقر لعرض تفاصيل الدالة DP1-2",
    icon=folium.Icon(color="blue", icon="building", prefix="fa")
).add_to(m)

# 3. عرض الخريطة تفاعلياً داخل تطبيق Streamlit
st_folium(m, width=1000, height=500)
