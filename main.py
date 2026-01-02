import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import time
from PIL import Image

try:
    from pyzbar.pyzbar import decode
except ImportError:
    decode = None

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Smart Shop System", page_icon="🛒", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #333;}
    section[data-testid="stSidebar"] {background-color: #2c3e50; color: white;}
    .big-btn button {width: 100%; height: 60px; font-size: 20px; background-color: #27ae60; color: white; border: none; border-radius: 8px;}
    .big-btn button:hover {background-color: #2ecc71;}
    .warning-box {background-color: #ffcccc; color: #cc0000; padding: 15px; border-radius: 10px; border: 1px solid #ff0000; margin-bottom: 20px; text-align: center; font-weight: bold;}
    .login-box {max-width: 400px; margin: auto; padding: 40px; background-color: white; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); text-align: center;}
</style>
""", unsafe_allow_html=True)

# --- 2. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('shop_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (barcode TEXT PRIMARY KEY, name TEXT, price REAL, cost REAL, stock INTEGER, min_stock INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, debt REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, total REAL, profit REAL, type TEXT, customer_id INTEGER, seller_name TEXT, barcode TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    
    # المستخدمين الافتراضيين (لن يتم تغييرهم إذا كانوا موجودين)
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '1234', 'admin')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('ahmed', '0000', 'seller')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('sami', '1111', 'seller')")
    
    conn.commit()
    return conn

conn = init_db()

# --- 3. دوال المساعدة ---
def login_user(username, password):
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return c.fetchone()

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
                'barcode': prod[0], 'name': prod[1], 'price': selling_price, 'cost': buying_cost, 'qty': quantity
            })
        return True, prod[1]
    return False, None

def generate_receipt_text(cart_items, total, date, client_name, pay_type, seller):
    lines = ["******************************", "       MAGASIN TUNISIE        ", "******************************"]
    lines.append(f"Date:   {date}")
    lines.append(f"Vendeur:{seller}")
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
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'current_user' not in st.session_state: st.session_state['current_user'] = None
if 'user_role' not in st.session_state: st.session_state['user_role'] = None
if 'cart' not in st.session_state: st.session_state['cart'] = []
if 'receipt_data' not in st.session_state: st.session_state['receipt_data'] = None 

# --- 5. شاشة تسجيل الدخول (تم تنظيفها) ---
def login_page():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=100)
        st.markdown("## تسجيل الدخول")
        st.markdown("---")
        
        username = st.text_input("اسم المستخدم", placeholder="User")
        password = st.text_input("كلمة السر", type="password", placeholder="Password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("دخول 🔐", use_container_width=True):
            user = login_user(username, password)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['current_user'] = user[0]
                st.session_state['user_role'] = user[2]
                st.rerun()
            else:
                st.error("❌ بيانات الدخول غير صحيحة")
        st.markdown("</div>", unsafe_allow_html=True)

# --- 6. التطبيق الرئيسي ---
def main_app():
    role = st.session_state['user_role']
    user = st.session_state['current_user']

    with st.sidebar:
        st.title("🛒 Smart Shop")
        st.markdown(f"👤 **{user}** ({role})")
        if st.button("🔴 خروج"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.markdown("---")
        
        if role == 'admin':
            menu_options = ["💰 نقطة البيع", "📦 المخزون", "📒 دفتر الكريدي", "📊 الإحصائيات"]
        else:
            menu_options = ["💰 نقطة البيع", "📦 المخزون", "📒 دفتر الكريدي"]
            
        menu = st.radio("القائمة", menu_options)
        
        if role == 'admin':
            zero_cost_count = pd.read_sql("SELECT COUNT(*) FROM products WHERE cost = 0", conn).iloc[0,0]
            if zero_cost_count > 0:
                st.error(f"⚠️ تنبيه: {zero_cost_count} منتجات بدون تكلفة!")

    # ==========================
    # 1. نقطة البيع
    # ==========================
    if menu == "💰 نقطة البيع":
        st.header(f"💰 نقطة البيع")
        
        with st.form("pos", clear_on_submit=True):
            c1, c2, c3 = st.columns([3,1,1])
            with c1: code = st.text_input("الباركود")
            with c2: qty = st.number_input("الكمية", 1, value=1)
            with c3: 
                st.write("")
                btn = st.form_submit_button("إضافة")
        
        if btn and code:
            succ, name = add_to_cart_logic(code, qty)
            if succ: st.toast(f"✅ {name}")
            else: st.error("غير موجود")

        with st.expander("📷 كاميرا"):
            if decode:
                img = st.camera_input("scan")
                if img:
                    d = decode(Image.open(img))
                    if d: add_to_cart_logic(d[0].data.decode("utf-8"), 1)

        if st.session_state['cart']:
            df = pd.DataFrame(st.session_state['cart'])
            df['Total'] = df['price'] * df['qty']
            st.dataframe(df[['name', 'price', 'qty', 'Total']], use_container_width=True)
            
            if st.button("❌ إلغاء"): st.session_state['cart']=[]; st.rerun()
            
            total = df['Total'].sum()
            profit = total - (df['cost'] * df['qty']).sum()
            
            st.metric("المجموع", f"{total:.3f}")
            
            col_pay, col_act = st.columns(2)
            with col_pay:
                pay_method = st.radio("طريقة الدفع", ["كاش", "كريدي"], horizontal=True)
                cust_id, cust_name = None, "Passager"
                if pay_method == "كريدي":
                    cd = pd.read_sql("SELECT id, name FROM customers", conn)
                    if not cd.empty:
                        dct = dict(zip(cd['name'], cd['id']))
                        cust_name = st.selectbox("الحريف", list(dct.keys()))
                        cust_id = dct[cust_name]

            with col_act:
                st.write("")
                if st.button("✅ تأكيد البيع", type="primary", use_container_width=True):
                    if pay_method == "كريدي" and not cust_id:
                        st.error("اختر الحريف!")
                    else:
                        for item in st.session_state['cart']:
                            update_stock(item['barcode'], item['qty'])
                        
                        curr = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c = conn.cursor()
                        c.execute("INSERT INTO sales (date, total, profit, type, customer_id, seller_name) VALUES (?, ?, ?, ?, ?, ?)", 
                                  (curr, total, profit, pay_method, cust_id, user))
                        
                        if pay_method == "كريدي": add_debt(cust_id, total)
                        conn.commit()
                        
                        st.session_state['receipt_data'] = generate_receipt_text(st.session_state['cart'], total, curr, cust_name, pay_method, user)
                        st.session_state['cart'] = []
                        st.success("تم!")
                        st.rerun()

        if st.session_state['receipt_data']:
            st.text(st.session_state['receipt_data'])
            st.download_button("تحميل الوصل", st.session_state['receipt_data'], "ticket.txt")
            if st.button("إخفاء"): st.session_state['receipt_data']=None; st.rerun()

    # ==========================
    # 2. المخزون
    # ==========================
    elif menu == "📦 المخزون":
        st.header("📦 إدارة المخزون")
        
        if role == 'admin':
            z = pd.read_sql("SELECT * FROM products WHERE cost = 0", conn)
            if not z.empty:
                st.markdown(f"<div class='warning-box'>⚠️ تنبيه: {len(z)} منتجات بدون تكلفة (أرباح غير دقيقة).</div>", unsafe_allow_html=True)
                if st.checkbox("عرض المنتجات الناقصة فقط"): st.dataframe(z)
        
        with st.expander("➕ إضافة / تعديل"):
            with st.form("prod"):
                c1, c2 = st.columns(2)
                with c1: p_bar = st.text_input("الباركود"); p_name = st.text_input("الاسم")
                with c2: p_stock = st.number_input("الكمية", 0); p_min = st.number_input("تنبيه النقص", 5)
                
                if role == 'admin':
                    cc1, cc2 = st.columns(2)
                    with cc1: p_cost = st.number_input("شراء", 0.0, format="%.3f")
                    with cc2: p_price = st.number_input("بيع", 0.0, format="%.3f")
                else:
                    p_price = st.number_input("بيع", 0.0, format="%.3f")
                    p_cost = 0.0 
                
                if st.form_submit_button("حفظ"):
                    c = conn.cursor()
                    if role != 'admin':
                        ex = get_product(p_bar)
                        p_cost = ex[3] if ex else 0.0
                    
                    c.execute("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?)", (p_bar, p_name, p_price, p_cost, p_stock, p_min))
                    conn.commit()
                    st.success("تم!")
                    st.rerun()

        df = pd.read_sql("SELECT * FROM products", conn)
        if role != 'admin': df = df.drop(columns=['cost'])
        st.dataframe(df, use_container_width=True)

    # ==========================
    # 3. الكريدي
    # ==========================
    elif menu == "📒 دفتر الكريدي":
        st.header("📒 الديون")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("cust"):
                n = st.text_input("الاسم"); p = st.text_input("الهاتف")
                if st.form_submit_button("إضافة"):
                    c = conn.cursor(); c.execute("INSERT INTO customers (name, phone, debt) VALUES (?,?,0)", (n, p)); conn.commit(); st.success("تم")
        with c2:
            df = pd.read_sql("SELECT * FROM customers WHERE debt > 0", conn)
            if not df.empty:
                s = st.selectbox("استخلاص:", df['name'])
                if s:
                    cur = df[df['name']==s]['debt'].values[0]
                    st.info(f"عليه: {cur:.3f}")
                    amt = st.number_input("دفع:", 0.0, cur)
                    if st.button("تأكيد"):
                        cid = df[df['name']==s]['id'].values[0]
                        c = conn.cursor(); c.execute("UPDATE customers SET debt=debt-? WHERE id=?", (amt, cid)); conn.commit(); st.success("تم!"); st.rerun()
        st.dataframe(pd.read_sql("SELECT name, phone, debt FROM customers", conn), use_container_width=True)

    # ==========================
    # 4. الإحصائيات
    # ==========================
    elif menu == "📊 الإحصائيات":
        if role == 'admin':
            st.header("📊 لوحة القيادة")
            s = pd.read_sql("SELECT * FROM sales", conn)
            if not s.empty:
                c1, c2 = st.columns(2)
                c1.metric("المبيعات", f"{s['total'].sum():.3f}")
                c2.metric("الربح", f"{s['profit'].sum():.3f}")
                st.dataframe(s)
            else: st.info("لا مبيعات")
        else: st.error("ممنوع!")

if st.session_state['logged_in']:
    main_app()
else:
    login_page()
