import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import time
from PIL import Image

# --- تهيئة مكتبة الباركود (مع حماية ضد الأخطاء) ---
try:
    from pyzbar.pyzbar import decode
except ImportError:
    decode = None

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Smart Shop | V2.2", page_icon="🛒", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #333;}
    section[data-testid="stSidebar"] {background-color: #2c3e50; color: white;}
    /* تحسين شكل الأزرار */
    .big-btn button {width: 100%; height: 60px; font-size: 20px; background-color: #27ae60; color: white; border: none; border-radius: 8px;}
    .big-btn button:hover {background-color: #2ecc71;}
    /* تحسين الخط في الوصل */
    .receipt-box {
        font-family: 'Courier New', Courier, monospace;
        background-color: #fff;
        padding: 15px;
        border: 1px dashed #000;
        white-space: pre-wrap; /* للحفاظ على تنسيق الأسطر */
    }
</style>
""", unsafe_allow_html=True)

# --- 2. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('shop_data.db', check_same_thread=False)
    c = conn.cursor()
    # جداول البيانات (تمت مراجعتها)
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

# دالة لتوليد نص الوصل المنسق
def generate_receipt_text(cart_items, total, date, client_name, pay_type):
    lines = []
    lines.append("******************************")
    lines.append("       MAGASIN TUNISIE        ")
    lines.append("******************************")
    lines.append(f"Date: {date}")
    lines.append(f"Client: {client_name}")
    lines.append("------------------------------")
    lines.append(f"{'Article':<15} {'Qt':<3} {'Prix'}")
    lines.append("------------------------------")
    for item in cart_items:
        # تنسيق السطر: الاسم (أول 15 حرف) - الكمية - السعر الإجمالي
        name_short = item['name'][:15]
        line_price = item['price'] * item['qty']
        lines.append(f"{name_short:<15} x{item['qty']:<2} {line_price:.3f}")
    lines.append("------------------------------")
    lines.append(f"TOTAL:          {total:.3f} TND")
    lines.append(f"Mode:           {pay_type}")
    lines.append("******************************")
    lines.append("     Merci de votre visite    ")
    lines.append("******************************")
    return "\n".join(lines)

# --- 4. إدارة الجلسة ---
if 'cart' not in st.session_state: st.session_state['cart'] = []
# متغير لتخزين الوصل الجاهز للتحميل
if 'receipt_data' not in st.session_state: st.session_state['receipt_data'] = None 

# --- 5. التطبيق الرئيسي ---
def main():
    with st.sidebar:
        st.title("🛒 Smart Shop")
        st.caption("System V2.2 - Print Edition")
        st.markdown("---")
        menu = st.radio("القائمة", ["💰 نقطة البيع (Caisse)", "📦 إدارة السلع (Stock)", "📒 دفتر الكريدي (Dettes)", "📊 الإحصائيات"])
        
        if decode is None:
            st.warning("⚠️ تنبيه: الكاميرا غير مفعلة (pyzbar مفقود).")

    # ==========================
    # 1. نقطة البيع (Caisse)
    # ==========================
    if menu == "💰 نقطة البيع (Caisse)":
        st.header("💰 نقطة البيع")
        
        # --- الإدخال اليدوي ---
        with st.container():
            st.markdown("#### ➕ إضافة منتج")
            with st.form("pos_entry", clear_on_submit=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1: code_input = st.text_input("الباركود:", key="code_in")
                with c2: qty_input = st.number_input("الكمية:", min_value=1, value=1, step=1)
                with c3: 
                    st.write("")
                    st.write("")
                    submit_btn = st.form_submit_button("إضافة 🛒", use_container_width=True)
            
            if submit_btn and code_input:
                success, p_name = add_to_cart_logic(code_input, qty_input)
                if success: st.toast(f"✅ أضيف: {p_name}")
                else: st.error(f"❌ منتج غير موجود!")

        # --- الكاميرا ---
        with st.expander("📷 الكاميرا"):
            if decode:
                cam_img = st.camera_input("مسح الباركود")
                if cam_img:
                    decoded = decode(Image.open(cam_img))
                    if decoded:
                        code_cam = decoded[0].data.decode("utf-8")
                        succ, name = add_to_cart_logic(code_cam, 1)
                        if succ: st.success(f"تم التقاط: {name}")
                        else: st.error("غير مسجل")
            else: st.info("المكتبة غير مثبتة.")

        st.markdown("---")

        # --- عرض السلة والوصل ---
        col_cart, col_receipt = st.columns([2, 1])
        
        with col_cart:
            if st.session_state['cart']:
                st.subheader("🛒 السلة")
                cart_df = pd.DataFrame(st.session_state['cart'])
                cart_df['Total'] = cart_df['price'] * cart_df['qty']
                
                st.dataframe(cart_df, column_config={
                        "name": "المنتج", "price": "سعر", "qty": "كمية", "Total": "مجموع"
                    }, use_container_width=True)
                
                if st.button("❌ تفريغ السلة"):
                    st.session_state['cart'] = []
                    st.rerun()

                total_sum = cart_df['Total'].sum()
                st.metric("الإجمالي", f"{total_sum:.3f} TND")
                
                st.markdown('<div class="big-btn">', unsafe_allow_html=True)
                pay_method = st.radio("الدفع:", ["كاش (Cash)", "كريدي (Crédit)"], horizontal=True)
                
                cust_id = None
                cust_name_receipt = "Passager"
                
                if pay_method == "كريدي (Crédit)":
                    custs = pd.read_sql("SELECT id, name FROM customers", conn)
                    if not custs.empty:
                        c_dict = dict(zip(custs['name'], custs['id']))
                        c_name = st.selectbox("الحريف:", list(c_dict.keys()))
                        cust_id = c_dict[c_name] if c_name else None
                        cust_name_receipt = c_name
                    else: st.warning("لا يوجد حرفاء!")

                if st.button("✅ إتمام البيع"):
                    if pay_method == "كريدي (Crédit)" and not cust_id:
                        st.error("اختر الحريف!")
                    else:
                        # 1. تحديث المخزون
                        for item in st.session_state['cart']:
                            update_stock(item['barcode'], item['qty'])
                        
                        # 2. حفظ المبيعات
                        curr_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c = conn.cursor()
                        c.execute("INSERT INTO sales (date, total, type, customer_id) VALUES (?, ?, ?, ?)", 
                                  (curr_date, total_sum, pay_method, cust_id))
                        
                        # 3. تحديث الدين
                        if pay_method == "كريدي (Crédit)":
                            add_debt(cust_id, total_sum)
                        
                        conn.commit()
                        
                        # 4. تجهيز الوصل للطباعة
                        receipt_txt = generate_receipt_text(st.session_state['cart'], total_sum, curr_date, cust_name_receipt, pay_method)
                        st.session_state['receipt_data'] = receipt_txt
                        
                        st.session_state['cart'] = [] # تفريغ السلة
                        st.success("تمت العملية بنجاح!")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("السلة فارغة.")

        # --- قسم طباعة الوصل (يظهر عند وجود وصل) ---
        with col_receipt:
            if st.session_state['receipt_data']:
                st.markdown("### 🖨️ الوصل جاهز")
                # عرض شكل الوصل
                st.text(st.session_state['receipt_data'])
                
                # زر التحميل (للطباعة)
                st.download_button(
                    label="🖨️ تحميل وطباعة (Ticket)",
                    data=st.session_state['receipt_data'],
                    file_name=f"ticket_{int(time.time())}.txt",
                    mime="text/plain"
                )
                
                if st.button("🗑️ إغلاق الوصل"):
                    st.session_state['receipt_data'] = None
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
        search_q = st.text_input("🔍 بحث:")
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
            else: st.success("لا ديون!")
        st.dataframe(pd.read_sql("SELECT name, phone, debt FROM customers", conn), use_container_width=True)

    # ==========================
    # 4. الإحصائيات
    # ==========================
    elif menu == "📊 الإحصائيات":
        st.header("📊 ملخص النشاط")
        tot_sales = pd.read_sql("SELECT SUM(total) FROM sales", conn).iloc[0,0] or 0
        tot_debt = pd.read_sql("SELECT SUM(debt) FROM customers", conn).iloc[0,0] or 0
        c1, c2 = st.columns(2)
        c1.metric("المبيعات", f"{tot_sales:.3f} TND")
        c2.metric("الديون", f"{tot_debt:.3f} TND")
        st.dataframe(pd.read_sql("SELECT * FROM sales ORDER BY id DESC LIMIT 15", conn), use_container_width=True)

if __name__ == '__main__':
    main()
