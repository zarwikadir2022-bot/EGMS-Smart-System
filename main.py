import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import time
from PIL import Image

# --- تهيئة مكتبة الباركود ---
try:
    from pyzbar.pyzbar import decode
except ImportError:
    decode = None

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Smart Shop | Pro V3.0", page_icon="💰", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #333;}
    section[data-testid="stSidebar"] {background-color: #2c3e50; color: white;}
    .big-btn button {width: 100%; height: 60px; font-size: 20px; background-color: #27ae60; color: white; border: none; border-radius: 8px;}
    .big-btn button:hover {background-color: #2ecc71;}
    .receipt-box {font-family: 'Courier New', monospace; background-color: #fff; padding: 15px; border: 1px dashed #000; white-space: pre-wrap;}
    /* تنسيق صناديق الأرقام */
    div[data-testid="stMetricValue"] {font-size: 24px; color: #2c3e50;}
</style>
""", unsafe_allow_html=True)

# --- 2. قاعدة البيانات (تم التعديل لإضافة سعر الشراء والربح) ---
def init_db():
    conn = sqlite3.connect('shop_data.db', check_same_thread=False)
    c = conn.cursor()
    # المنتجات: أضفنا cost (سعر التكلفة)
    c.execute('''CREATE TABLE IF NOT EXISTS products 
                 (barcode TEXT PRIMARY KEY, name TEXT, price REAL, cost REAL, stock INTEGER, min_stock INTEGER)''')
    # الزبائن
    c.execute('''CREATE TABLE IF NOT EXISTS customers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, debt REAL)''')
    # المبيعات: أضفنا profit (الربح من هذه البيعة)
    c.execute('''CREATE TABLE IF NOT EXISTS sales 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, total REAL, profit REAL, type TEXT, customer_id INTEGER)''')
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

# دالة الإضافة للسلة (تأخذ السعر والربح)
def add_to_cart_logic(barcode, quantity=1):
    prod = get_product(barcode) # (barcode, name, price, cost, stock, min)
    if prod:
        selling_price = prod[2]
        buying_cost = prod[3]
        
        found = False
        for item in st.session_state['cart']:
            if item['barcode'] == prod[0]:
                item['qty'] += quantity
                found = True
                break
        if not found:
            st.session_state['cart'].append({
                'barcode': prod[0], 
                'name': prod[1], 
                'price': selling_price,
                'cost': buying_cost, # نحتفظ بالتكلفة لحساب الربح
                'qty': quantity
            })
        return True, prod[1]
    return False, None

def generate_receipt_text(cart_items, total, date, client_name, pay_type):
    lines = ["******************************", "       MAGASIN TUNISIE        ", "******************************"]
    lines.append(f"Date: {date}")
    lines.append(f"Client: {client_name}")
    lines.append("------------------------------")
    lines.append(f"{'Article':<15} {'Qt':<3} {'Prix'}")
    lines.append("------------------------------")
    for item in cart_items:
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
if 'receipt_data' not in st.session_state: st.session_state['receipt_data'] = None 

# --- 5. التطبيق الرئيسي ---
def main():
    with st.sidebar:
        st.title("💰 Smart Shop Pro")
        st.caption("نظام إدارة مع حساب الأرباح")
        st.markdown("---")
        menu = st.radio("القائمة", ["💰 نقطة البيع", "📦 إدارة السلع (والمربوح)", "📒 دفتر الكريدي", "📊 الإحصائيات والأرباح"])
        
        if decode is None:
            st.warning("⚠️ الكاميرا غير مفعلة.")

    # ==========================
    # 1. نقطة البيع (Caisse)
    # ==========================
    if menu == "💰 نقطة البيع":
        st.header("💰 نقطة البيع")
        
        # الإدخال
        with st.container():
            with st.form("pos_entry", clear_on_submit=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1: code_input = st.text_input("الباركود:", key="code_in")
                with c2: qty_input = st.number_input("الكمية:", min_value=1, value=1)
                with c3: 
                    st.write("")
                    st.write("")
                    submit_btn = st.form_submit_button("إضافة 🛒", use_container_width=True)
            
            if submit_btn and code_input:
                success, p_name = add_to_cart_logic(code_input, qty_input)
                if success: st.toast(f"✅ أضيف: {p_name}")
                else: st.error("❌ منتج غير موجود!")

        # الكاميرا
        with st.expander("📷 الكاميرا"):
            if decode:
                cam_img = st.camera_input("مسح")
                if cam_img:
                    decoded = decode(Image.open(cam_img))
                    if decoded:
                        succ, name = add_to_cart_logic(decoded[0].data.decode("utf-8"), 1)
                        if succ: st.success(f"تم: {name}")
                        else: st.error("غير مسجل")
            else: st.info("المكتبة مفقودة")

        st.markdown("---")

        col_cart, col_receipt = st.columns([2, 1])
        with col_cart:
            if st.session_state['cart']:
                cart_df = pd.DataFrame(st.session_state['cart'])
                cart_df['Total'] = cart_df['price'] * cart_df['qty']
                # لا نعرض سعر التكلفة للزبون في الجدول
                st.dataframe(cart_df[['name', 'price', 'qty', 'Total']], use_container_width=True)
                
                if st.button("❌ تفريغ السلة"):
                    st.session_state['cart'] = []
                    st.rerun()

                total_sum = cart_df['Total'].sum()
                
                # حساب الربح لهذه البيعة
                # الربح = (سعر البيع - سعر الشراء) * الكمية
                total_cost = (cart_df['cost'] * cart_df['qty']).sum()
                total_profit = total_sum - total_cost
                
                st.metric("الإجمالي للدفع", f"{total_sum:.3f} TND")
                
                st.markdown('<div class="big-btn">', unsafe_allow_html=True)
                pay_method = st.radio("الدفع:", ["كاش", "كريدي"], horizontal=True)
                
                cust_id = None
                cust_name = "Passager"
                if pay_method == "كريدي":
                    custs = pd.read_sql("SELECT id, name FROM customers", conn)
                    if not custs.empty:
                        c_dict = dict(zip(custs['name'], custs['id']))
                        c_name = st.selectbox("الحريف:", list(c_dict.keys()))
                        cust_id = c_dict[c_name] if c_name else None
                        cust_name = c_name
                
                if st.button("✅ إتمام البيع"):
                    if pay_method == "كريدي" and not cust_id:
                        st.error("اختر الحريف!")
                    else:
                        for item in st.session_state['cart']:
                            update_stock(item['barcode'], item['qty'])
                        
                        curr_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c = conn.cursor()
                        # نسجل الربح في قاعدة البيانات
                        c.execute("INSERT INTO sales (date, total, profit, type, customer_id) VALUES (?, ?, ?, ?, ?)", 
                                  (curr_date, total_sum, total_profit, pay_method, cust_id))
                        
                        if pay_method == "كريدي": add_debt(cust_id, total_sum)
                        
                        conn.commit()
                        st.session_state['receipt_data'] = generate_receipt_text(st.session_state['cart'], total_sum, curr_date, cust_name, pay_method)
                        st.session_state['cart'] = []
                        st.success("تم!")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        with col_receipt:
            if st.session_state['receipt_data']:
                st.text(st.session_state['receipt_data'])
                st.download_button("🖨️ تحميل الوصل", st.session_state['receipt_data'], f"ticket.txt")
                if st.button("إغلاق"):
                    st.session_state['receipt_data'] = None
                    st.rerun()

    # ==========================
    # 2. إدارة السلع (Stock)
    # ==========================
    elif menu == "📦 إدارة السلع (والمربوح)":
        st.header("📦 إدارة المخزون والتسعير")
        
        with st.expander("➕ إضافة / تعديل منتج (مع التكلفة)", expanded=True):
            with st.form("prod_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1: 
                    p_bar = st.text_input("الباركود")
                    p_name = st.text_input("اسم المنتج")
                with c2:
                    p_stock = st.number_input("الكمية", min_value=0, step=1)
                    p_min = st.number_input("تنبيه النقص", value=5)
                
                st.markdown("#### 💸 التسعير (لحساب الربح)")
                cc1, cc2, cc3 = st.columns(3)
                with cc1:
                    p_cost = st.number_input("سعر الشراء (التكلفة)", min_value=0.0, step=0.1, format="%.3f", help="بكم اشتريت السلعة؟")
                with cc2:
                    p_price = st.number_input("سعر البيع (للزبون)", min_value=0.0, step=0.1, format="%.3f")
                with cc3:
                    # عرض الربح المتوقع فوراً
                    st.write("")
                    st.write("")
                    if p_price > p_cost:
                        margin = p_price - p_cost
                        st.markdown(f"✅ الربح في القطعة: **{margin:.3f}**")
                    else:
                        st.markdown("⚠️ **خسارة!**")

                if st.form_submit_button("حفظ المنتج"):
                    try:
                        c = conn.cursor()
                        c.execute("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?)", 
                                  (p_bar, p_name, p_price, p_cost, p_stock, p_min))
                        conn.commit()
                        st.success("تم الحفظ!")
                    except Exception as e: st.error(f"خطأ: {e}")

        st.subheader("جرد السلع")
        df = pd.read_sql("SELECT * FROM products", conn)
        # حساب الربح المتوقع في الجدول
        if not df.empty:
            df['الربح_في_القطعة'] = df['price'] - df['cost']
        
        search_q = st.text_input("🔍 بحث:")
        if search_q and not df.empty: 
            df = df[df['name'].str.contains(search_q, case=False) | df['barcode'].str.contains(search_q)]
            
        st.dataframe(df, use_container_width=True)

    # ==========================
    # 3. دفتر الكريدي
    # ==========================
    elif menu == "📒 دفتر الكريدي":
        st.header("📒 الديون")
        # (نفس الكود السابق للكريدي لا تغيير فيه)
        c1, c2 = st.columns(2)
        with c1:
            with st.form("cust_form", clear_on_submit=True):
                nm = st.text_input("اسم الحريف")
                ph = st.text_input("الهاتف")
                if st.form_submit_button("إضافة"):
                    c = conn.cursor()
                    c.execute("INSERT INTO customers (name, phone, debt) VALUES (?,?,0)", (nm, ph))
                    conn.commit()
                    st.success("تم!")
        with c2:
            custs = pd.read_sql("SELECT * FROM customers WHERE debt > 0", conn)
            if not custs.empty:
                c_pay = st.selectbox("استخلاص من:", custs['name'])
                if c_pay:
                    curr = custs[custs['name']==c_pay]['debt'].values[0]
                    st.info(f"عليه: {curr:.3f}")
                    amt = st.number_input("دفع:", min_value=0.0, max_value=curr)
                    if st.button("تأكيد"):
                        cid = custs[custs['name']==c_pay]['id'].values[0]
                        c = conn.cursor()
                        c.execute("UPDATE customers SET debt = debt - ? WHERE id=?", (amt, cid))
                        conn.commit()
                        st.success("خالص!")
                        st.rerun()
        st.dataframe(pd.read_sql("SELECT name, phone, debt FROM customers", conn), use_container_width=True)

    # ==========================
    # 4. الإحصائيات والأرباح
    # ==========================
    elif menu == "📊 الإحصائيات والأرباح":
        st.header("📊 لوحة قيادة التاجر")
        
        # جلب البيانات
        sales_data = pd.read_sql("SELECT total, profit FROM sales", conn)
        total_revenue = sales_data['total'].sum() if not sales_data.empty else 0
        total_profit = sales_data['profit'].sum() if not sales_data.empty else 0
        
        total_debt = pd.read_sql("SELECT SUM(debt) FROM customers", conn).iloc[0,0] or 0
        
        # رأس المال (قيمة السلعة بسعر الشراء)
        stock_data = pd.read_sql("SELECT cost, stock FROM products", conn)
        capital = (stock_data['cost'] * stock_data['stock']).sum() if not stock_data.empty else 0

        # الصف الأول: المبيعات والديون
        c1, c2 = st.columns(2)
        c1.metric("💰 المبيعات (Chiffre d'affaire)", f"{total_revenue:.3f} TND")
        c2.metric("📒 الكريدي (عند الناس)", f"{total_debt:.3f} TND", delta_color="inverse")
        
        st.markdown("---")
        
        # الصف الثاني: الربح ورأس المال (الأهم)
        c3, c4 = st.columns(2)
        c3.metric("💎 الربح الصافي (Net Profit)", f"{total_profit:.3f} TND", delta="مربوحك الصافي")
        c4.metric("📦 رأس المال (قيمة السلعة)", f"{capital:.3f} TND", help="قيمة السلعة المخزنة بسعر الشراء")
        
        st.markdown("---")
        st.subheader("سجل المبيعات")
        st.dataframe(pd.read_sql("SELECT * FROM sales ORDER BY id DESC LIMIT 20", conn), use_container_width=True)

if __name__ == '__main__':
    main()
