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

# --- 1. إعدادات الصفحة والتصميم الجديد ---
st.set_page_config(page_title="Smart Shop | 3D V5.0", page_icon="🛒", layout="wide")

# 🔥✨ هنا يكمن سحر التصميم الجديد ✨🔥
st.markdown("""
<style>
    /* 1. الخلفية العامة الدافئة */
    .stApp {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%); /* تدرج برتقالي كريمي */
        color: #3E2723; /* نص بني غامق */
    }
    
    /* 2. القائمة الجانبية */
    section[data-testid="stSidebar"] {
        background-color: #BF360C; /* لون الطوب الأحمر الدافئ */
        color: #FFF3E0;
        box-shadow: 5px 0 15px rgba(0,0,0,0.2); /* ظل جانبي */
    }
    div[data-testid="stSidebarUserContent"] * {color: #FFF3E0 !important;} /* جعل نصوص القائمة فاتحة */

    /* 3. البطاقات ثلاثية الأبعاد (The 3D Cards) */
    /* سنستخدم هذا الكلاس لتغليف العناصر */
    .three-d-card {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
        /* هذا الظل هو سر الـ 3D */
        box-shadow: 0 10px 25px rgba(62, 39, 35, 0.15), 0 5px 10px rgba(62, 39, 35, 0.1);
        transition: transform 0.3s ease;
    }
    .three-d-card:hover {
         transform: translateY(-5px); /* تأثير ارتفاع خفيف عند الماوس */
    }

    /* 4. الأزرار الكبيرة (3D) */
    .big-btn button {
        width: 100%; height: 65px; font-size: 22px; font-weight: bold;
        background: linear-gradient(to bottom, #FF5722, #E64A19); /* تدرج برتقالي ناري */
        color: white; border: none; border-radius: 12px;
        box-shadow: 0 6px #BF360C; /* ظل صلب للزر */
        transition: all 0.1s;
    }
    .big-btn button:hover {
        background: linear-gradient(to bottom, #FF7043, #F4511E);
        transform: translateY(-2px);
        box-shadow: 0 8px #BF360C;
    }
    .big-btn button:active {
        transform: translateY(4px);
        box-shadow: 0 2px #BF360C; /* تأثير الضغط */
    }

    /* 5. صناديق التنبيه وتسجيل الدخول */
    .warning-box {
        background-color: #FFCCBC; color: #BF360C; padding: 15px; 
        border-radius: 12px; border: 2px solid #FF5722; margin-bottom: 20px; 
        text-align: center; font-weight: bold; box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .login-box {
        max-width: 400px; margin: auto; padding: 40px; 
        background: #fff; border-radius: 25px; 
        /* ظل قوي جداً للـ Login */
        box-shadow: 0 20px 40px rgba(0,0,0,0.2); 
        text-align: center;
    }
    
    /* 6. تحسين الجداول والأرقام */
    div[data-testid="stDataFrame"] {
        border-radius: 15px; overflow: hidden; box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetricValue"] { color: #E64A19; font-weight: 800; }
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

# --- 5. شاشة تسجيل الدخول (3D) ---
def login_page():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=120)
        st.markdown("<h2 style='color:#BF360C;'>تسجيل الدخول</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة السر", type="password")
        
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
        st.title("🛒 Smart Shop 3D")
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
                st.markdown(f"<div class='warning-box' style='font-size:0.8em;'>⚠️ {zero_cost_count} منتجات بدون تكلفة!</div>", unsafe_allow_html=True)

    # ==========================
    # 1. نقطة البيع
    # ==========================
    if menu == "💰 نقطة البيع":
        st.header(f"💰 نقطة البيع")
        
        # تغليف الإدخال ببطاقة 3D
        st.markdown('<div class="three-d-card">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("📷 كاميرا"):
            if decode:
                img = st.camera_input("scan")
                if img:
                    d = decode(Image.open(img))
                    if d: add_to_cart_logic(d[0].data.decode("utf-8"), 1)

        if st.session_state['cart']:
            # تغليف السلة ببطاقة 3D
            st.markdown('<div class="three-d-card">', unsafe_allow_html=True)
            st.subheader("🛒 السلة")
            df = pd.DataFrame(st.session_state['cart'])
            df['Total'] = df['price'] * df['qty']
            st.dataframe(df[['name', 'price', 'qty', 'Total']], use_container_width=True)
            
            if st.button("❌ إلغاء"): st.session_state['cart']=[]; st.rerun()
            
            total = df['Total'].sum()
            profit = total - (df['cost'] * df['qty']).sum()
            
            st.metric("المجموع النهائي", f"{total:.3f} TND")
            st.markdown("---")

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
                st.markdown('<div class="big-btn">', unsafe_allow_html=True)
                if st.button("✅ تأكيد البيع 3D"):
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
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state['receipt_data']:
            st.markdown('<div class="three-d-card" style="background:#FFF8E1;">', unsafe_allow_html=True)
            st.markdown("#### 🖨️ الوصل")
            st.text(st.session_state['receipt_data'])
            st.download_button("تحميل الوصل", st.session_state['receipt_data'], "ticket.txt")
            if st.button("إخفاء"): st.session_state['receipt_data']=None; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ==========================
    # 2. المخزون
    # ==========================
    elif menu == "📦 المخزون":
        st.header("📦 المخزون")
        
        if role == 'admin':
            z = pd.read_sql("SELECT * FROM products WHERE cost = 0", conn)
            if not z.empty:
                st.markdown(f"<div class='warning-box'>⚠️ تنبيه: {len(z)} منتجات بدون تكلفة!</div>", unsafe_allow_html=True)
                if st.checkbox("عرض المنتجات الناقصة فقط"): st.dataframe(z)
        
        # تغليف نموذج الإضافة
        st.markdown('<div class="three-d-card">', unsafe_allow_html=True)
        with st.expander("➕ إضافة / تعديل منتج", expanded=True):
            with st.form("prod"):
                c1, c2 = st.columns(2)
                with c1: p_bar = st.text_input("الباركود"); p_name = st.text_input("الاسم")
                with c2: p_stock = st.number_input("الكمية", 0); p_min = st.number_input("تنبيه النقص", 5)
                
                if role == 'admin':
                    cc1, cc2 = st.columns(2)
                    with cc1: p_cost = st.number_input("شراء", 0.0, format="%.3f")
                    with cc2: p_price = st.number_input("بيع", 0.0, format="%.3f")
                else:
                    p_price = st.number_input("بيع", 0.0, format="%.3f"); p_cost = 0.0 
                
                if st.form_submit_button("حفظ 💾"):
                    c = conn.cursor()
                    if role != 'admin':
                        ex = get_product(p_bar)
                        p_cost = ex[3] if ex else 0.0
                    c.execute("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?)", (p_bar, p_name, p_price, p_cost, p_stock, p_min))
                    conn.commit(); st.success("تم!"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # تغليف الجدول
        st.markdown('<div class="three-d-card">', unsafe_allow_html=True)
        df = pd.read_sql("SELECT * FROM products", conn)
        if role != 'admin': df = df.drop(columns=['cost'])
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==========================
    # 3. الكريدي
    # ==========================
    elif menu == "📒 دفتر الكريدي":
        st.header("📒 الديون")
        st.markdown('<div class="three-d-card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("إضافة حريف")
            with st.form("cust"):
                n = st.text_input("الاسم"); p = st.text_input("الهاتف")
                if st.form_submit_button("حفظ"):
                    c = conn.cursor(); c.execute("INSERT INTO customers (name, phone, debt) VALUES (?,?,0)", (n, p)); conn.commit(); st.success("تم")
        with c2:
            st.subheader("استخلاص")
            df = pd.read_sql("SELECT * FROM customers WHERE debt > 0", conn)
            if not df.empty:
                s = st.selectbox("الحريف", df['name'])
                if s:
                    cur = df[df['name']==s]['debt'].values[0]
                    st.metric("الدين الحالي", f"{cur:.3f}")
                    amt = st.number_input("دفع:", 0.0, cur)
                    if st.button("تأكيد الدفع 💰"):
                        cid = df[df['name']==s]['id'].values[0]
                        c = conn.cursor(); c.execute("UPDATE customers SET debt=debt-? WHERE id=?", (amt, cid)); conn.commit(); st.success("تم!"); st.rerun()
        st.markdown("---")
        st.dataframe(pd.read_sql("SELECT name, phone, debt FROM customers", conn), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==========================
    # 4. الإحصائيات
    # ==========================
    elif menu == "📊 الإحصائيات":
        if role == 'admin':
            st.header("📊 لوحة القيادة")
            st.markdown('<div class="three-d-card">', unsafe_allow_html=True)
            s = pd.read_sql("SELECT * FROM sales", conn)
            if not s.empty:
                c1, c2 = st.columns(2)
                c1.metric("المبيعات الكلية", f"{s['total'].sum():.3f}")
                c2.metric("الربح الصافي", f"{s['profit'].sum():.3f}")
                st.markdown("---")
                st.dataframe(s)
            else: st.info("لا مبيعات")
            st.markdown('</div>', unsafe_allow_html=True)
        else: st.error("ممنوع!")

if st.session_state['logged_in']:
    main_app()
else:
    login_page()
