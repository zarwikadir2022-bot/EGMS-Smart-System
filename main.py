import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import time
from PIL import Image

# محاولة استيراد مكتبة الكاميرا
try:
    from pyzbar.pyzbar import decode
except ImportError:
    decode = None

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Smart Shop | V2.1", page_icon="🛒", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #333;}
    section[data-testid="stSidebar"] {background-color: #2c3e50; color: white;}
    .metric-box {background-color: white; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-left: 5px solid #3498db; text-align: center;}
    .big-btn button {width: 100%; height: 60px; font-size: 20px; background-color: #27ae60; color: white; border: none; border-radius: 8px;}
    .big-btn button:hover {background-color: #2ecc71;}
    div[data-testid="stDataFrame"] {background-color: white; padding: 10px; border-radius: 10px;}
    
    /* تنسيق الوصل */
    .receipt {
        background-color: #fff;
        padding: 20px;
        border: 1px dashed #333;
        font-family: 'Courier New', Courier, monospace;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. قاعدة البيانات ---
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

def add_to_cart_logic(barcode, quantity=1):
    prod = get_product(barcode)
    if prod:
        found = False
        for item in st.session_state['cart']:
            if item['barcode'] == prod[0]:
                item['qty'] += quantity
                found = True
                break
        if not found:
            st.session_state['cart'].append({
                'barcode': prod[0], 'name': prod[1], 'price': prod[2], 'qty': quantity
            })
        return True, prod[1]
    return False, None

# --- 4. إدارة الجلسة ---
if 'cart' not in st.session_state: st.session_state['cart'] = []
if 'last_receipt' not in st.session_state: st.session_state['last_receipt'] = None # لتخزين آخر وصل

# --- 5. التطبيق الرئيسي ---
def main():
    with st.sidebar:
        st.title("🛒 Smart Shop")
        st.caption("V2.1 - الإصدار الكامل")
        st.markdown("---")
        menu = st.radio("القائمة", ["💰 نقطة البيع (Caisse)", "📦 إدارة السلع (Stock)", "📒 دفتر الكريدي (Dettes)", "📊 الإحصائيات"])
        
        if decode is None:
            st.warning("⚠️ الكاميرا غير مفعلة (مكتبة pyzbar مفقودة).")

    # ==========================
    # 1. نقطة البيع (Caisse)
    # ==========================
    if menu == "💰 نقطة البيع (Caisse)":
        st.header("💰 نقطة البيع")
        
        # --- قسم الإدخال ---
        with st.container():
            st.markdown("#### ➕ إضافة منتج")
            with st.form("pos_entry", clear_on_submit=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1: code_input = st.text_input("الباركود (امسح أو اكتب):", key="code_in")
                with c2: qty_input = st.number_input("الكمية:", min_value=1, value=1, step=1, key="qty_in")
                with c3: 
                    st.write("")
                    st.write("")
                    submit_btn = st.form_submit_button("إضافة 🛒", use_container_width=True)
            
            if submit_btn and code_input:
                success, p_name = add_to_cart_logic(code_input, qty_input)
                if success: st.toast(f"✅ تمت إضافة {qty_input} من: {p_name}")
                else: st.error(f"❌ المنتج رقم {code_input} غير موجود!")

        # --- قسم الكاميرا ---
        with st.expander("📷 استخدام الكاميرا"):
            if decode:
                cam_img = st.camera_input("التقاط صورة للباركود")
                if cam_img:
                    decoded = decode(Image.open(cam_img))
                    if decoded:
                        code_cam = decoded[0].data.decode("utf-8")
                        succ, name = add_to_cart_logic(code_cam, 1)
                        if succ: st.success(f"تم التقاط: {name}")
                        else: st.error("منتج غير مسجل")
            else: st.info("الكاميرا غير مفعلة.")

        st.markdown("---")

        # --- عرض السلة ---
        col_cart, col_receipt = st.columns([2, 1]) # تقسيم الشاشة: سلة يمين، وصل يسار
        
        with col_cart:
            if st.session_state['cart']:
                st.subheader("🛒 السلة الحالية")
                cart_df = pd.DataFrame(st.session_state['cart'])
                cart_df['المجموع'] = cart_df['price'] * cart_df['qty']
                
                st.dataframe(cart_df, column_config={
                        "name": "المنتج", 
                        "price": st.column_config.NumberColumn("السعر", format="%.3f د.ت"),
                        "qty": "الكمية", 
                        "المجموع": st.column_config.NumberColumn("الإجمالي", format="%.3f د.ت")
                    }, use_container_width=True)
                
                if st.button("❌ تفريغ السلة"):
                    st.session_state['cart'] = []
                    st.rerun()

                total_sum = cart_df['المجموع'].sum()
                st.metric("المبلغ الإجمالي", f"{total_sum:.3f} TND")
                
                st.markdown('<div class="big-btn">', unsafe_allow_html=True)
                pay_method = st.radio("الدفع:", ["كاش (Cash)", "كريدي (Crédit)"], horizontal=True)
                
                cust_id = None
                cust_name_receipt = "Client Passager" # اسم افتراضي للوصل
                
                if pay_method == "كريدي (Crédit)":
                    custs = pd.read_sql("SELECT id, name FROM customers", conn)
                    if not custs.empty:
                        c_dict = dict(zip(custs['name'], custs['id']))
                        c_name = st.selectbox("الحريف:", list(c_dict.keys()))
                        cust_id = c_dict[c_name] if c_name else None
                        cust_name_receipt = c_name # تحديث الاسم للوصل
                    else: st.warning("لا يوجد حرفاء!")

                if st.button("✅ إتمام البيع (Checkout)"):
                    if pay_method == "كريدي (Crédit)" and not cust_id:
                        st.error("اختر الحريف أولاً!")
                    else:
                        # تنفيذ البيع
                        for item in st.session_state['cart']:
                            update_stock(item['barcode'], item['qty'])
                        
                        c = conn.cursor()
                        c.execute("INSERT INTO sales (date, total, type, customer_id) VALUES (?, ?, ?, ?)", 
                                  (datetime.now().strftime("%Y-%m-%d %H:%M"), total_sum, pay_method, cust_id))
                        
                        if pay_method == "كريدي (Crédit)":
                            add_debt(cust_id, total_sum)
                            st.warning(f"تم تقييد الدين على {c_name}")
                        
                        conn.commit()
                        
                        # --- إنشاء الوصل وحفظه في الذاكرة ---
                        items_str = ""
                        for item in st.session_state['cart']:
                            items_str += f"{item['name']} (x{item['qty']}) : {item['price']*item['qty']:.3f}\n"
                        
                        receipt_text = f"""
                        ***************************
                              MAGASIN TUNISIE
                        ***************************
                        Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
                        Client: {cust_name_receipt}
                        ---------------------------
                        {items_str}
                        ---------------------------
                        TOTAL: {total_sum:.3f} TND
                        Type: {pay_method}
                        ***************************
                        Merci de votre visite!
                        """
                        st.session_state['last_receipt'] = receipt_text
                        
                        st.success("🎉 عملية ناجحة!")
                        st.balloons()
                        st.session_state['cart'] = [] # تفريغ السلة
                        time.sleep(1)
                        st.rerun() # إعادة تحميل الصفحة لإظهار الوصل الجديد
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("السلة فارغة.. ابدأ بإضافة المنتجات.")

        # --- منطقة الوصل (تظهر دائماً على اليسار إذا كان هناك وصل سابق) ---
        with col_receipt:
            if st.session_state.get('last_receipt'):
                st.markdown("### 🖨️ آخر وصل")
                st.code(st.session_state['last_receipt'], language="text")
                if st.button("🗑️ إخفاء الوصل"):
                    st.session_state['last_receipt'] = None
                    st.rerun()

    # ==========================
    # 2. إدارة السلع (Stock)
    # ==========================
    elif menu == "📦 إدارة السلع (Stock)":
        st.header("📦 إدارة المخزون")
        with st.expander("➕ إضافة / تعديل منتج"):
            with st.form("prod_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1: 
                    p_bar = st.text_input("الباركود")
                    p_name = st.text_input("الاسم")
                with c2:
                    p_price = st.number_input("السعر", min_value=0.0, step=0.100, format="%.3f")
                    p_stock = st.number_input("الكمية", min_value=0, step=1)
                p_min = st.number_input("تنبيه النقص عند", value=5)
                if st.form_submit_button("حفظ"):
                    try:
                        c = conn.cursor()
                        c.execute("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?)", (p_bar, p_name, p_price, p_stock, p_min))
                        conn.commit()
                        st.success("تم الحفظ!")
                    except Exception as e: st.error(f"خطأ: {e}")

        st.subheader("جرد السلع")
        df = pd.read_sql("SELECT * FROM products", conn)
        search_q = st.text_input("🔍 بحث باسم المنتج أو الباركود:")
        if search_q: df = df[df['name'].str.contains(search_q, case=False) | df['barcode'].str.contains(search_q)]
        st.dataframe(df, use_container_width=True)

    # ==========================
    # 3. دفتر الكريدي
    # ==========================
    elif menu == "📒 دفتر الكريدي (Dettes)":
        st.header("📒 إدارة الديون")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("تسجيل حريف")
            with st.form("cust_form", clear_on_submit=True):
                nm = st.text_input("الاسم")
                ph = st.text_input("الهاتف")
                if st.form_submit_button("إضافة"):
                    c = conn.cursor()
                    c.execute("INSERT INTO customers (name, phone, debt) VALUES (?,?,0)", (nm, ph))
                    conn.commit()
                    st.success("تم!")
        with c2:
            st.subheader("استخلاص دين")
            custs = pd.read_sql("SELECT * FROM customers WHERE debt > 0", conn)
            if not custs.empty:
                c_pay = st.selectbox("اختر الحريف:", custs['name'])
                if c_pay:
                    curr_debt = custs[custs['name']==c_pay]['debt'].values[0]
                    st.info(f"الدين الحالي: {curr_debt:.3f} د.ت")
                    amt = st.number_input("المبلغ المقبوض:", min_value=0.0, max_value=curr_debt, step=1.0)
                    if st.button("تأكيد الخلاص"):
                        cid = custs[custs['name']==c_pay]['id'].values[0]
                        c = conn.cursor()
                        c.execute("UPDATE customers SET debt = debt - ? WHERE id=?", (amt, cid))
                        conn.commit()
                        st.success("تم الخلاص!")
                        st.rerun()
            else: st.success("لا توجد ديون حالياً! 👏")
        st.markdown("---")
        st.subheader("قائمة الكريدي")
        all_custs = pd.read_sql("SELECT name, phone, debt FROM customers", conn)
        st.dataframe(all_custs.style.highlight_max(subset=['debt'], color='#ffcccc'), use_container_width=True)

    # ==========================
    # 4. الإحصائيات
    # ==========================
    elif menu == "📊 الإحصائيات":
        st.header("📊 ملخص النشاط")
        tot_sales = pd.read_sql("SELECT SUM(total) FROM sales", conn).iloc[0,0] or 0
        tot_debt = pd.read_sql("SELECT SUM(debt) FROM customers", conn).iloc[0,0] or 0
        c1, c2 = st.columns(2)
        c1.metric("مجموع المبيعات", f"{tot_sales:.3f} TND")
        c2.metric("مجموع الكريدي (الخارج)", f"{tot_debt:.3f} TND")
        st.subheader("آخر العمليات")
        st.dataframe(pd.read_sql("SELECT * FROM sales ORDER BY id DESC LIMIT 15", conn), use_container_width=True)

if __name__ == '__main__':
    main()
