import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import time
from PIL import Image
# محاولة استيراد مكتبة الباركود (مع معالجة الخطأ إذا لم تكن مثبتة)
try:
    from pyzbar.pyzbar import decode
except ImportError:
    decode = None

# --- 1. إعدادات الصفحة والتصميم ---
st.set_page_config(page_title="Smart Shop | Camera Edition", page_icon="🛒", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #333;}
    section[data-testid="stSidebar"] {background-color: #2c3e50; color: white;}
    div[data-testid="stSidebarUserContent"] {color: white;}
    .metric-box {background-color: white; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-left: 5px solid #3498db; text-align: center;}
    .big-btn button {width: 100%; height: 60px; font-size: 20px; background-color: #27ae60; color: white; border: none; border-radius: 8px;}
    .big-btn button:hover {background-color: #2ecc71;}
    .alert-box {background-color: #ffeaa7; padding: 10px; border-radius: 5px; border: 1px solid #fdcb6e; color: #d35400;}
</style>
""", unsafe_allow_html=True)

# --- 2. قاعدة البيانات (SQLite) ---
def init_db():
    conn = sqlite3.connect('shop_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (barcode TEXT PRIMARY KEY, name TEXT, price REAL, stock INTEGER, min_stock INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, debt REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, total REAL, type TEXT, customer_id INTEGER)''')
    conn.commit()
    return conn

conn = init_db()

# --- 3. دوال مساعدة ---
def get_product(barcode):
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE barcode=?", (barcode,))
    return c.fetchone()

def update_stock(barcode, qty):
    c = conn.cursor()
    c.execute("UPDATE products SET stock = stock - ? WHERE barcode=?", (qty, barcode))
    conn.commit()

def add_debt(customer_id, amount):
    c = conn.cursor()
    c.execute("UPDATE customers SET debt = debt + ? WHERE id=?", (amount, customer_id))
    conn.commit()

# دالة لإضافة منتج للسلة
def add_to_cart_logic(barcode):
    prod = get_product(barcode)
    if prod:
        found = False
        for item in st.session_state['cart']:
            if item['barcode'] == prod[0]:
                item['qty'] += 1
                found = True
                break
        if not found:
            st.session_state['cart'].append({'barcode': prod[0], 'name': prod[1], 'price': prod[2], 'qty': 1})
        return True, prod[1]
    return False, None

# --- 4. إدارة الجلسة ---
if 'cart' not in st.session_state: st.session_state['cart'] = []

# --- 5. التطبيق الرئيسي ---
def main():
    with st.sidebar:
        st.title("🛒 Smart Shop")
        st.markdown("---")
        menu = st.radio("القائمة", ["💰 نقطة البيع (Caisse)", "📦 إدارة السلع (Stock)", "📒 دفتر الكريدي (Dettes)", "📊 الإحصائيات"])
        
        if decode is None:
            st.error("⚠️ مكتبة pyzbar غير مثبتة! لن تعمل الكاميرا.")
            st.code("pip install pyzbar pillow")

    # ==========================
    # 1. نقطة البيع (POS) - مع الكاميرا
    # ==========================
    if menu == "💰 نقطة البيع (Caisse)":
        st.header("💰 نقطة البيع")
        
        # --- قسم الكاميرا والبحث ---
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.markdown("### 📷 ماسح الكاميرا")
            use_cam = st.checkbox("تفعيل الكاميرا")
            if use_cam and decode:
                # التقاط الصورة
                img_file = st.camera_input("وجّه الكاميرا نحو الباركود", label_visibility="collapsed")
                
                if img_file:
                    # تحويل الصورة وقراءة الباركود
                    image = Image.open(img_file)
                    decoded_objects = decode(image)
                    
                    if decoded_objects:
                        for obj in decoded_objects:
                            scanned_code = obj.data.decode("utf-8")
                            st.success(f"تم التقاط: {scanned_code}")
                            
                            # إضافة المنتج للسلة
                            success, p_name = add_to_cart_logic(scanned_code)
                            if success:
                                st.toast(f"✅ أضيف: {p_name}")
                            else:
                                st.error("❌ منتج غير مسجل!")
                    else:
                        st.warning("⚠️ لم يتم التعرف على باركود.")

        with c2:
            st.markdown("### ⌨️ إدخال يدوي / قارئ ليزر")
            manual_code = st.text_input("امسح أو اكتب الباركود واضغط Enter:", key="man_input")
            if manual_code:
                success, p_name = add_to_cart_logic(manual_code)
                if success:
                    st.toast(f"✅ أضيف: {p_name}")
                    # تفريغ الحقل عن طريق إعادة التشغيل (خدعة بسيطة لتنظيف الخانة للقارئ اليدوي)
                    # st.rerun() # يمكن تفعيلها إذا أردت تنظيف الخانة فوراً
                else:
                    st.error("❌ منتج غير مسجل بالمخزون")

        st.markdown("---")

        # --- عرض السلة ---
        if st.session_state['cart']:
            cart_df = pd.DataFrame(st.session_state['cart'])
            cart_df['Total'] = cart_df['price'] * cart_df['qty']
            
            st.dataframe(cart_df, use_container_width=True, column_config={
                "name": "المنتج", "price": "السعر", "qty": "الكمية", "Total": "المجموع"
            })
            
            total_sum = cart_df['Total'].sum()
            
            col_tot, col_pay = st.columns([1, 2])
            with col_tot:
                st.metric("المجموع الكلي", f"{total_sum:.3f} TND")
            
            with col_pay:
                st.markdown('<div class="big-btn">', unsafe_allow_html=True)
                pay_method = st.radio("طريقة الدفع:", ["كاش (Cash)", "كريدي (Crédit)"], horizontal=True)
                
                customer_select = None
                if pay_method == "كريدي (Crédit)":
                    cust_df = pd.read_sql("SELECT id, name FROM customers", conn)
                    if not cust_df.empty:
                        cust_dict = dict(zip(cust_df['name'], cust_df['id']))
                        customer_name = st.selectbox("اختر الحريف:", list(cust_dict.keys()))
                        if customer_name: customer_select = cust_dict[customer_name]
                    else:
                        st.warning("لا يوجد حرفاء مسجلين!")

                if st.button("✅ إتمام البيع (Checkout)"):
                    if pay_method == "كريدي (Crédit)" and not customer_select:
                        st.error("يجب اختيار حريف للكريدي!")
                    else:
                        # 1. المخزون
                        for item in st.session_state['cart']:
                            update_stock(item['barcode'], item['qty'])
                        # 2. المبيعات
                        c = conn.cursor()
                        c.execute("INSERT INTO sales (date, total, type, customer_id) VALUES (?, ?, ?, ?)", 
                                  (datetime.now().strftime("%Y-%m-%d %H:%M"), total_sum, pay_method, customer_select))
                        # 3. الدين
                        if pay_method == "كريدي (Crédit)" and customer_select:
                            add_debt(customer_select, total_sum)
                            st.warning(f"📒 تم تقييد {total_sum} د على {customer_name}")
                        
                        conn.commit()
                        st.success("🎉 عملية ناجحة!")
                        st.balloons()
                        st.session_state['cart'] = []
                        time.sleep(1)
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                
                # طباعة التوصيل
                if st.checkbox("🖨️ طباعة التوصيل"):
                    receipt = f"""
                    --- MAGASIN ---
                    Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
                    Total: {total_sum:.3f} TND
                    ---------------
                    Merci de votre visite!
                    """
                    st.code(receipt)
        else:
            st.info("🛒 السلة فارغة..")

    # ==========================
    # 2. إدارة السلع (Stock)
    # ==========================
    elif menu == "📦 إدارة السلع (Stock)":
        st.header("📦 المخزون")
        
        # إضافة بالكاميرا أيضاً
        with st.expander("➕ إضافة منتج جديد (يدوي أو كاميرا)"):
            c1, c2 = st.columns([1,2])
            with c1:
                use_cam_add = st.checkbox("استعمال الكاميرا للباركود")
                scan_val = ""
                if use_cam_add and decode:
                    img_add = st.camera_input("صور الباركود للإضافة", key="cam_add")
                    if img_add:
                        decoded_add = decode(Image.open(img_add))
                        if decoded_add:
                            scan_val = decoded_add[0].data.decode("utf-8")
                            st.success(f"تم قراءة: {scan_val}")

            with st.form("add_prod"):
                # إذا قرأنا من الكاميرا نضع القيمة، وإلا نتركها فارغة للكتابة
                new_bar = st.text_input("الباركود", value=scan_val)
                new_name = st.text_input("اسم المنتج")
                col_p, col_q = st.columns(2)
                with col_p: new_price = st.number_input("سعر البيع", min_value=0.0, step=0.1)
                with col_q: new_stock = st.number_input("الكمية", min_value=0, step=1)
                new_min = st.number_input("تنبيه النقص عند", value=5)
                
                if st.form_submit_button("حفظ المنتج"):
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO products VALUES (?,?,?,?,?)", (new_bar, new_name, new_price, new_stock, new_min))
                        conn.commit()
                        st.success("تم الحفظ!")
                    except:
                        st.error("هذا الباركود مسجل مسبقاً!")

        st.subheader("قائمة السلع")
        df_prods = pd.read_sql("SELECT * FROM products", conn)
        search = st.text_input("🔍 بحث:")
        if search:
            df_prods = df_prods[df_prods['name'].str.contains(search, case=False)]
        st.dataframe(df_prods, use_container_width=True)

    # ==========================
    # 3. دفتر الكريدي
    # ==========================
    elif menu == "📒 دفتر الكريدي (Dettes)":
        st.header("📒 دفتر الكريدي")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("new_cust"):
                st.subheader("حريف جديد")
                c_name = st.text_input("الاسم")
                c_phone = st.text_input("الهاتف")
                if st.form_submit_button("إضافة"):
                    c = conn.cursor()
                    c.execute("INSERT INTO customers (name, phone, debt) VALUES (?,?,0)", (c_name, c_phone))
                    conn.commit()
                    st.success("تم!")
        with c2:
            st.subheader("خلاص")
            cust_df = pd.read_sql("SELECT * FROM customers", conn)
            if not cust_df.empty:
                pay_cust = st.selectbox("الحريف:", cust_df['name'])
                amount_pay = st.number_input("المبلغ المدفوع:", min_value=0.0)
                if st.button("تسجيل الدفع"):
                    cust_id = cust_df[cust_df['name'] == pay_cust]['id'].values[0]
                    c = conn.cursor()
                    c.execute("UPDATE customers SET debt = debt - ? WHERE id=?", (amount_pay, cust_id))
                    conn.commit()
                    st.success("تم الخلاص!")
                    st.rerun()
        
        st.dataframe(cust_df, use_container_width=True)

    # ==========================
    # 4. الإحصائيات
    # ==========================
    elif menu == "📊 الإحصائيات":
        st.header("📊 الأرقام")
        total_sales = pd.read_sql("SELECT SUM(total) FROM sales", conn).iloc[0,0] or 0
        total_credits = pd.read_sql("SELECT SUM(debt) FROM customers", conn).iloc[0,0] or 0
        
        c1, c2 = st.columns(2)
        c1.metric("المبيعات", f"{total_sales:.3f} TND")
        c2.metric("الديون (الكريدي)", f"{total_credits:.3f} TND")
        
        st.subheader("سجل العمليات")
        st.dataframe(pd.read_sql("SELECT * FROM sales ORDER BY id DESC LIMIT 10", conn), use_container_width=True)

if __name__ == '__main__':
    main()
