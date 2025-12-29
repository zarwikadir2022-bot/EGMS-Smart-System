import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import plotly.express as px
from sqlalchemy.exc import IntegrityError

# --- 1. هيكلة قاعدة البيانات (v35) ---
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

class WorkerLog(Base):
    __tablename__ = 'worker_logs'
    id = Column(Integer, primary_key=True); name = Column(String(100)); hours = Column(Float); rate = Column(Float); spec = Column(String(50)); site = Column(String(100)); date = Column(DateTime, default=datetime.utcnow)

class StoreLog(Base):
    __tablename__ = 'store_logs'
    id = Column(Integer, primary_key=True); item = Column(String(100)); unit = Column(String(50)); qty = Column(Float); type = Column(String(20)); site = Column(String(100)); date = Column(DateTime, default=datetime.utcnow)

class WorkLog(Base):
    __tablename__ = 'work_logs'
    id = Column(Integer, primary_key=True); site = Column(String(100)); progress = Column(Float); notes = Column(Text); date = Column(DateTime, default=datetime.utcnow)

# تغيير اسم القاعدة لضمان بداية نظيفة وتجنب تعارض النسخ القديمة
engine = create_engine('sqlite:///egms_pro_v35.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- 2. واجهة المستخدم ---
st.set_page_config(page_title="EGMS ERP Pro v35", layout="wide")

if "logged_in" not in st.session_state:
    st.title("🏗️ EGMS Digital Portal")
    u = st.text_input("User"); p = st.text_input("Pass", type="password")
    if st.button("Sign In"):
        access = {"admin": ("egms2025", "Admin"), "labor": ("labor2025", "Labor"), "magaza": ("store2025", "Store"), "work": ("work2025", "Work")}
        if u in access and p == access[u][0]:
            st.session_state.update({"logged_in": True, "role": access[u][1]}); st.rerun()
else:
    role = st.session_state.get("role")
    session = Session()
    
    # دالة لجلب المواقع
    def get_sites_list():
        return session.query(Site).all()

    if role == "Admin":
        st.title("💼 لوحة التحكم الإدارية")
        t1, t2, t3, t4, t5 = st.tabs(["📍 الخريطة", "👷 الموارد البشرية", "📦 المخازن", "🏗️ سير الأشغال", "⚙️ الإعدادات"])

        with t1:
            sites_data = get_sites_list()
            if sites_data:
                df_s = pd.DataFrame([{"name": s.name, "lat": s.lat, "lon": s.lon} for s in sites_data])
                st.map(df_s, latitude='lat', longitude='lon')
            else: st.info("لا توجد مواقع لعرضها حالياً.")

        with t5:
            st.subheader("⚙️ إدارة مواقع العمل (الحضائر)")
            with st.form("site_add_form", clear_on_submit=True):
                n = st.text_input("اسم الحضيرة الجديد (مثال: فوشانة 1)")
                c1, c2 = st.columns(2)
                la = c1.number_input("خط العرض (Latitude)", value=36.5, format="%.6f")
                lo = c2.number_input("خط الطول (Longitude)", value=10.2, format="%.6f")
                submit = st.form_submit_button("إضافة الحضيرة إلى النظام")
                
                if submit:
                    if n.strip() == "":
                        st.error("⚠️ يرجى إدخال اسم الحضيرة")
                    else:
                        try:
                            new_site = Site(name=n.strip(), lat=la, lon=lo)
                            session.add(new_site)
                            session.commit()
                            st.success(f"✅ تم إضافة موقع {n} بنجاح!")
                            st.rerun()
                        except IntegrityError:
                            session.rollback()
                            st.error(f"⚠️ خطأ: اسم الموقع '{n}' موجود بالفعل!")
                        except Exception as e:
                            session.rollback()
                            st.error(f"❌ حدث خطأ غير متوقع: {e}")

        # عرض بقية البيانات (العمال، المخزن، الأشغال)
        with t3:
            st.subheader("📦 رصيد المخزن")
            df_st = pd.read_sql(session.query(StoreLog).statement, session.bind)
            if not df_st.empty:
                df_st['actual_qty'] = df_st.apply(lambda x: x['qty'] if x['type'] == "Entry" else -x['qty'], axis=1)
                balance = df_st.groupby(['item', 'unit'])['actual_qty'].sum().reset_index()
                st.dataframe(balance.rename(columns={'actual_qty': 'الرصيد المتاح'}), use_container_width=True)

    # واجهات الموظفين تبقى كما هي مع التأكد من جلب القائمة الصحيحة للمواقع
    else:
        st.header(f"واجهة {role}")
        sites = get_sites_list()
        if not sites:
            st.warning("⚠️ لا توجد مواقع مضافة. يرجى مراجعة المدير.")
        else:
            site_names = [s.name for s in sites]
            if role == "Store":
                with st.form("st"):
                    item = st.text_input("المادة"); unit = st.selectbox("الوحدة", ["كغ", "طن", "كيس", "لتر"])
                    qty = st.number_input("الكمية", min_value=0.1); t_type = st.radio("العملية", ["Entry", "Exit"])
                    s = st.selectbox("الموقع", site_names)
                    if st.form_submit_button("حفظ"):
                        session.add(StoreLog(item=item, unit=unit, qty=qty, type=t_type, site=s))
                        session.commit(); st.success("✅")

    session.close()
