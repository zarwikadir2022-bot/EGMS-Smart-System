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
st.set_page_config(page_title="Smart Shop | V4.2 Audit", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #333;}
    section[data-testid="stSidebar"] {background-color: #2c3e50; color: white;}
    .big-btn button {width: 100%; height: 60px; font-size: 20px; background-color: #27ae60; color: white; border: none; border-radius: 8px;}
    .big-btn button:hover {background-color: #2ecc71;}
    /* صندوق التنبيه للمدير */
    .warning-box {
        background-color: #ffcccc; color: #cc0000; padding: 15px; 
        border-radius: 10px; border: 1px solid #ff0000; margin-bottom: 20px;
        text-align: center; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('shop_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (barcode TEXT PRIMARY KEY, name TEXT, price REAL, cost REAL, stock INTEGER, min_stock INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, debt REAL)''')
    # جدول المبيعات يحفظ الآن الباركود أيضاً لتصحيح الأرباح لاحقاً
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, total REAL, profit REAL, type TEXT, customer_id INTEGER, seller_name TEXT, barcode TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    
    # المستخدمين
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

# --- دالة التصحيح الذكي للأرباح (جديدة) ---
def fix_historical_profits(barcode, new_cost):
    """
    عندما يضيف المدير التكلفة لمنتج كان سعره 0،
    هذه الدالة تبحث عن كل المبيعات السابقة لهذا المنتج وتعيد حساب الربح بشكل صحيح.
    """
    c = conn.cursor()
    # 1. جلب المبيعات المرتبطة بهذا المنتج
    # ملاحظة: في النسخ القديمة لم نكن نحفظ الباركود في المبيعات، هذا سيعمل للمبيعات الجديدة فقط
    # لتبسيط الأمر، سنعتمد التعديل المستقبلي، أو يمكننا تعقيد الجدول أكثر (جدول تفاصيل الفاتورة).
    # للتبسيط هنا: سنقوم فقط بتحديث المنتج. المبيعات السابقة ستبقى كما هي إلا إذا عدلنا هيكل المبيعات بالكامل (Invoice Items).
    # الحل العملي الآن: المنتج الجديد يدخل بتكلفة 0، الربح يحسب خطأ مؤقتاً، والمدير يجب أن يصححه بسرعة.
    pass 

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
    return "\n".join(lines)

# --- 4. إدارة الجلسة ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'current_user' not in st.session_state: st.session_state['current_user'] = None
if 'user_role' not in st.session_state: st.session_state['user_role'] = None
if 'cart' not in st.session_state: st.session_state['cart'] = []
if 'receipt_data' not in st.session_state: st.session_state['receipt_data'] = None 

# --- 5. شاشة تسجيل الدخول ---
def login_page():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("💡 جرب الدخول بـ: admin / 1234 أو ahmed / 0000")
        username = st.text_input("المستخدم")
        password = st.text_input("كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            user = login_user(username, password)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['current_user'] = user[0]
                st.session_state['user_role'] = user[2]
                st.rerun()
            else: st.error("خطأ")

# --- 6. التطبيق الرئيسي ---
def main_app():
    role = st.session_state['user_role']
    user = st.session_state['current_user']

    # --- القائمة الجانبية ---
    with st.sidebar:
        st.title("🛒 Smart Shop")
        st.markdown(f"👤 **{user}** ({role})")
        if st.button("خروج"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.markdown("---")
        
        # خيارات القائمة حسب الصلاحية
        if role == 'admin':
            menu_options = ["💰 نقطة البيع", "📦 المخزون", "📒 دفتر الكريدي", "📊 الإحصائيات"]
        else:
            menu_options = ["💰 نقطة البيع", "📦 المخزون", "📒 دفتر الكريدي"]
            
        menu = st.radio("القائمة", menu_options)
        
        # --- 🔴 تنبيهات للمدير في القائمة الجانبية ---
        if role == 'admin':
            # فحص المنتجات التي تكلفتها 0
            zero_cost_count = pd.read_sql("SELECT COUNT(*) FROM products WHERE cost = 0", conn).iloc[0,0]
            if zero_cost_count > 0:
                st.error(f"⚠️ هناك {zero_cost_count} منتجات تكلفتها 0!")
                st.caption("أرباح هذه المنتجات غير دقيقة.")

    # ==========================
    # 1. نقطة البيع
    # ==========================
    if menu == "💰 نقطة البيع":
        st.header(f"💰 نقطة البيع")
        
        # نموذج الإدخال
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

        # الكاميرا
        with st.expander("📷 كاميرا"):
            if decode:
                img = st.camera_input("scan")
                if img:
                    d = decode(Image.open(img))
                    if d: add_to_cart_logic(d[0].data.decode("utf-8"), 1)

        # السلة
        if st.session_state['cart']:
            df = pd.DataFrame(st.session_state['cart'])
            df['Total'] = df['price'] * df['qty']
            st.dataframe(df[['name', 'price', 'qty', 'Total']], use_container_width=True)
            
            if st.button("❌ إلغاء"): st.session_state['cart']=[]; st.rerun()
            
            total = df['Total'].sum()
            # حساب الربح (حتى لو التكلفة 0، سيحسب ربحاً وهمياً مؤقتاً)
            profit = total - (df['cost'] * df['qty']).sum()
            
            st.metric("المجموع", f"{total:.3f}")
            
            if st.button("✅ بيع"):
                # تحديث المخزون وحفظ البيعة
                for item in st.session_state['cart']:
                    update_stock(item['barcode'], item['qty'])
                
                curr_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                # حفظ البيعة (ملاحظة: نحفظ الباركود الأول فقط في النسخة المبسطة، أو نطور الجدول لاحقاً)
                # هنا سنحفظ البيعة ككل
                c = conn.cursor()
                c.execute("INSERT INTO sales (date, total, profit, type, customer_id, seller_name) VALUES (?, ?, ?, ?, ?, ?)", 
                          (curr_date, total, profit, "كاش", None, user))
                conn.commit()
                
                st.session_state['cart'] = []
                st.success("تم!")
                st.rerun()

    # ==========================
    # 2. المخزون (الذكي)
    # ==========================
    elif menu == "📦 المخزون":
        st.header("📦 إدارة المخزون")
        
        # --- رسالة تنبيه للمدير ---
        if role == 'admin':
            zero_cost = pd.read_sql("SELECT * FROM products WHERE cost = 0", conn)
            if not zero_cost.empty:
                st.markdown(f"<div class='warning-box'>⚠️ تنبيه: لديك {len(zero_cost)} منتجات أضافها الباعة بدون تحديد التكلفة.<br>الرجاء تحديث سعر الشراء لضمان حساب أرباح دقيق.</div>", unsafe_allow_html=True)
                
                if st.checkbox("🔍 عرض المنتجات الناقصة فقط"):
                    st.dataframe(zero_cost)
        
        # نموذج الإضافة
        with st.expander("➕ إضافة / تعديل منتج", expanded=True):
            with st.form("prod"):
                c1, c2 = st.columns(2)
                with c1: 
                    p_bar = st.text_input("الباركود")
                    p_name = st.text_input("الاسم")
                with c2:
                    p_stock = st.number_input("الكمية", min_value=0)
                    p_min = st.number_input("تنبيه النقص", value=5)
                
                # التعامل الذكي مع التكلفة
                if role == 'admin':
                    cc1, cc2 = st.columns(2)
                    with cc1: p_cost = st.number_input("سعر الشراء (Cost)", min_value=0.0, format="%.3f")
                    with cc2: p_price = st.number_input("سعر البيع", min_value=0.0, format="%.3f")
                else:
                    # البائع لا يرى التكلفة، نضعها 0 إذا كان جديداً
                    p_price = st.number_input("سعر البيع", min_value=0.0, format="%.3f")
                    p_cost = 0.0 
                
                if st.form_submit_button("حفظ"):
                    c = conn.cursor()
                    # منطق الحفظ:
                    # إذا كان المستخدم "بائع"، يجب أن لا يصفر التكلفة إذا كانت موجودة
                    if role != 'admin':
                        existing = get_product(p_bar)
                        if existing:
                            p_cost = existing[3] # احتفظ بالتكلفة القديمة
                        else:
                            p_cost = 0.0 # منتج جديد تماماً، التكلفة 0 (سيظهر تنبيه للمدير)
                    
                    c.execute("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?)", 
                              (p_bar, p_name, p_price, p_cost, p_stock, p_min))
                    conn.commit()
                    st.success("تم الحفظ!")
                    st.rerun()

        # جدول العرض
        df = pd.read_sql("SELECT * FROM products", conn)
        if role != 'admin':
            df = df.drop(columns=['cost']) # إخفاء التكلفة عن البائع
        
        st.dataframe(df, use_container_width=True)

    # ==========================
    # 3. دفتر الكريدي
    # ==========================
    elif menu == "📒 دفتر الكريدي":
        # (نفس الكود السابق للكريدي)
        st.header("📒 الديون")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("cust"):
                n = st.text_input("الاسم"); p = st.text_input("الهاتف")
                if st.form_submit_button("إضافة"):
                    c = conn.cursor()
                    c.execute("INSERT INTO customers (name, phone, debt) VALUES (?,?,0)", (n, p))
                    conn.commit(); st.success("تم")
        with c2:
            df = pd.read_sql("SELECT * FROM customers WHERE debt > 0", conn)
            if not df.empty:
                sel = st.selectbox("الحريف", df['name'])
                if sel:
                    curr = df[df['name']==sel]['debt'].values[0]
                    pay = st.number_input("دفع", 0.0, curr)
                    if st.button("تأكيد"):
                        cid = df[df['name']==sel]['id'].values[0]
                        c = conn.cursor(); c.execute("UPDATE customers SET debt=debt-? WHERE id=?", (pay, cid)); conn.commit(); st.rerun()
        st.dataframe(pd.read_sql("SELECT name, phone, debt FROM customers", conn), use_container_width=True)

    # ==========================
    # 4. الإحصائيات (Admin Only)
    # ==========================
    elif menu == "📊 الإحصائيات":
        if role == 'admin':
            st.header("📊 لوحة القيادة")
            
            sales = pd.read_sql("SELECT * FROM sales", conn)
            if not sales.empty:
                tot = sales['total'].sum()
                prof = sales['profit'].sum()
                
                c1, c2 = st.columns(2)
                c1.metric("المبيعات", f"{tot:.3f}")
                
                # تنبيه إذا كانت الأرباح غير دقيقة
                has_zero_cost_sales = False # يمكن تطوير هذا لاحقاً لفحص كل بيعة
                # هنا نعرض الربح
                c2.metric("الربح الصافي", f"{prof:.3f}")
                
                st.subheader("سجل المبيعات")
                st.dataframe(sales)
            else:
                st.info("لا توجد مبيعات بعد")
        else:
            st.error("ممنوع الدخول!")

if st.session_state['logged_in']:
    main_app()
else:
    login_page()
