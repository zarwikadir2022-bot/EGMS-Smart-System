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
st.set_page_config(page_title="Smart Shop | Privacy V4.1", page_icon="🔐", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #333;}
    section[data-testid="stSidebar"] {background-color: #2c3e50; color: white;}
    .big-btn button {width: 100%; height: 60px; font-size: 20px; background-color: #27ae60; color: white; border: none; border-radius: 8px;}
    .big-btn button:hover {background-color: #2ecc71;}
    .login-box {
        max-width: 400px; margin: auto; padding: 30px; 
        background-color: white; border-radius: 10px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('shop_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (barcode TEXT PRIMARY KEY, name TEXT, price REAL, cost REAL, stock INTEGER, min_stock INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, debt REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, total REAL, profit REAL, type TEXT, customer_id INTEGER, seller_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    
    # المستخدمين الافتراضيين
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

# --- 5. شاشة تسجيل الدخول ---
def login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=100)
        st.title("تسجيل الدخول")
        st.markdown("##### Smart Shop System")
        
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة السر", type="password")
        
        if st.button("دخول 🔐", use_container_width=True):
            user = login_user(username, password) # user = (username, pass, role)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['current_user'] = user[0]
                st.session_state['user_role'] = user[2]
                st.success(f"مرحباً {user[0]} ({user[2]})")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("خطأ في البيانات!")
        st.markdown("</div>", unsafe_allow_html=True)

# --- 6. التطبيق الرئيسي ---
def main_app():
    role = st.session_state['user_role']
    user = st.session_state['current_user']

    # --- القائمة الجانبية الذكية (Smart Sidebar) ---
    with st.sidebar:
        st.title("🛒 Smart Shop")
        st.markdown(f"👤 المستخدم: **{user}**")
        st.caption(f"الصلاحية: {role}")
        
        if st.button("🔴 تسجيل الخروج"):
            st.session_state['logged_in'] = False
            st.session_state['current_user'] = None
            st.session_state['user_role'] = None
            st.rerun()
            
        st.markdown("---")
        
        # تحديد القوائم المسموحة
        if role == 'admin':
            # المدير يرى كل شيء
            menu_options = ["💰 نقطة البيع", "📦 المخزون", "📒 دفتر الكريدي", "📊 الإحصائيات"]
        else:
            # البائع يرى البيع والمخزون والكريدي فقط
            menu_options = ["💰 نقطة البيع", "📦 المخزون", "📒 دفتر الكريدي"]
            
        menu = st.radio("القائمة", menu_options)
        
        if decode is None: st.warning("⚠️ الكاميرا غير مفعلة.")

    # ==========================
    # 1. نقطة البيع (للجميع)
    # ==========================
    if menu == "💰 نقطة البيع":
        st.header(f"💰 نقطة البيع")
        
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
                else: st.error("❌ غير موجود")

        with st.expander("📷 الكاميرا"):
            if decode:
                cam_img = st.camera_input("مسح")
                if cam_img:
                    decoded = decode(Image.open(cam_img))
                    if decoded:
                        succ, name = add_to_cart_logic(decoded[0].data.decode("utf-8"), 1)
                        if succ: st.success(f"تم: {name}")
                        else: st.error("غير مسجل")

        col_cart, col_receipt = st.columns([2, 1])
        with col_cart:
            if st.session_state['cart']:
                cart_df = pd.DataFrame(st.session_state['cart'])
                cart_df['Total'] = cart_df['price'] * cart_df['qty']
                st.dataframe(cart_df[['name', 'price', 'qty', 'Total']], use_container_width=True)
                
                if st.button("❌ تفريغ السلة"):
                    st.session_state['cart'] = []; st.rerun()

                total_sum = cart_df['Total'].sum()
                st.metric("الإجمالي", f"{total_sum:.3f} TND")
                
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

                if st.button("✅ إتمام البيع", type="primary", use_container_width=True):
                    if pay_method == "كريدي" and not cust_id:
                        st.error("اختر الحريف!")
                    else:
                        for item in st.session_state['cart']:
                            update_stock(item['barcode'], item['qty'])
                        
                        curr_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                        # حساب الربح في الخلفية (البائع لا يراه)
                        total_cost = (cart_df['cost'] * cart_df['qty']).sum()
                        total_profit = total_sum - total_cost
                        
                        c = conn.cursor()
                        c.execute("INSERT INTO sales (date, total, profit, type, customer_id, seller_name) VALUES (?, ?, ?, ?, ?, ?)", 
                                  (curr_date, total_sum, total_profit, pay_method, cust_id, user))
                        
                        if pay_method == "كريدي": add_debt(cust_id, total_sum)
                        conn.commit()
                        
                        st.session_state['receipt_data'] = generate_receipt_text(st.session_state['cart'], total_sum, curr_date, cust_name, pay_method, user)
                        st.session_state['cart'] = []
                        st.success("تم!")
                        st.rerun()

        with col_receipt:
            if st.session_state['receipt_data']:
                st.text(st.session_state['receipt_data'])
                st.download_button("تحميل الوصل", st.session_state['receipt_data'], "ticket.txt")
                if st.button("إخفاء"): st.session_state['receipt_data'] = None; st.rerun()

    # ==========================
    # 2. المخزون (تحكم بصلاحيات التكلفة)
    # ==========================
    elif menu == "📦 المخزون":
        st.header("📦 إدارة المخزون")
        
        with st.expander("➕ إضافة / تعديل منتج"):
            with st.form("prod_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1: 
                    p_bar = st.text_input("الباركود")
                    p_name = st.text_input("الاسم")
                with c2:
                    p_stock = st.number_input("الكمية", min_value=0)
                    p_min = st.number_input("تنبيه النقص", value=5)
                
                # إظهار سعر الشراء للمدير فقط
                if role == 'admin':
                    cc1, cc2 = st.columns(2)
                    with cc1: p_cost = st.number_input("سعر الشراء (التكلفة)", min_value=0.0, format="%.3f")
                    with cc2: p_price = st.number_input("سعر البيع", min_value=0.0, format="%.3f")
                else:
                    # البائع يرى سعر البيع فقط
                    p_price = st.number_input("سعر البيع", min_value=0.0, format="%.3f")
                    p_cost = 0.0 # قيمة افتراضية للبائع (لن يتم حفظها إذا كان المنتج موجوداً)
                
                if st.form_submit_button("حفظ"):
                    try:
                        c = conn.cursor()
                        # إذا كان بائع، نحتاج لجلب التكلفة القديمة حتى لا نصفرها
                        if role != 'admin':
                            old_prod = get_product(p_bar)
                            if old_prod:
                                p_cost = old_prod[3] # الحفاظ على التكلفة القديمة
                            else:
                                p_cost = 0.0 # منتج جديد من بائع (بدون تكلفة مؤقتاً)
                                
                        c.execute("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?)", 
                                  (p_bar, p_name, p_price, p_cost, p_stock, p_min))
                        conn.commit()
                        st.success("تم الحفظ!")
                    except: st.error("خطأ")

        # عرض الجدول (إخفاء التكلفة للبائع)
        df = pd.read_sql("SELECT * FROM products", conn)
        if role != 'admin' and not df.empty:
            # حذف عمود التكلفة من العرض للبائع
            df = df.drop(columns=['cost'])
            
        st.dataframe(df, use_container_width=True)

    # ==========================
    # 3. دفتر الكريدي (للجميع)
    # ==========================
    elif menu == "📒 دفتر الكريدي":
        st.header("📒 الديون")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("cust_form"):
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
                c_pay = st.selectbox("استخلاص:", custs['name'])
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
    # 4. الإحصائيات (للمدير فقط)
    # ==========================
    elif menu == "📊 الإحصائيات" and role == 'admin':
        st.header("📊 لوحة القيادة (Admin Only)")
        
        sales_data = pd.read_sql("SELECT total, profit FROM sales", conn)
        total_rev = sales_data['total'].sum() if not sales_data.empty else 0
        total_prof = sales_data['profit'].sum() if not sales_data.empty else 0
        
        c1, c2 = st.columns(2)
        c1.metric("المبيعات", f"{total_rev:.3f} TND")
        c2.metric("الربح الصافي", f"{total_prof:.3f} TND", delta="صافي")
        
        st.subheader("أداء الباعة")
        sales_df = pd.read_sql("SELECT * FROM sales", conn)
        if not sales_df.empty:
            seller_stats = sales_df.groupby('seller_name')['total'].sum()
            st.bar_chart(seller_stats)
            st.dataframe(sales_df)
    
    # حماية إضافية: إذا حاول البائع الوصول للإحصائيات
    elif menu == "📊 الإحصائيات" and role != 'admin':
        st.error("⛔ عذراً، هذه الصفحة مخصصة للمدير فقط.")

# --- تشغيل ---
if st.session_state['logged_in']:
    main_app()
else:
    login_page()
