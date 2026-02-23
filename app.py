import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_option_menu import option_menu
import hashlib
import secrets

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Yash Gallery – KPI System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS STYLING
# ============================================================
st.markdown("""
<style>
.block-container{padding-top:1rem}
.card{
  background:#fff;border:1px solid #e5e7eb;border-radius:16px;
  padding:14px 16px;box-shadow:0 6px 18px rgba(15,23,42,0.06);
  margin-bottom:1rem;
}
.small{color:#64748b;font-size:12px}
.badge{
  display:inline-block;padding:2px 10px;border-radius:999px;
  border:1px solid #e5e7eb;background:#f8fafc;font-size:12px;color:#334155;
  margin:2px;
}
.badge-success{background:#dcfce7;color:#166534;border-color:#86efac}
.badge-danger{background:#fee2e2;color:#991b1b;border-color:#fca5a5}
.badge-warning{background:#fef3c7;color:#92400e;border-color:#fcd34d}
.badge-info{background:#dbeafe;color:#1e40af;border-color:#93c5fd}
.hline{height:1px;background:#e5e7eb;margin:10px 0}
.login-container{
  max-width:420px;margin:80px auto;padding:40px;
  background:white;border-radius:20px;
  box-shadow:0 20px 60px rgba(0,0,0,0.15);
}
.role-badge-admin{
  background:#dc2626;color:white;padding:6px 14px;
  border-radius:12px;font-weight:bold;font-size:11px;
}
.role-badge-manager{
  background:#2563eb;color:white;padding:6px 14px;
  border-radius:12px;font-weight:bold;font-size:11px;
}
.role-badge-employee{
  background:#16a34a;color:white;padding:6px 14px;
  border-radius:12px;font-weight:bold;font-size:11px;
}
.metric-card{
  padding:20px;border-radius:12px;background:#f8fafc;
  border:2px solid #e5e7eb;text-align:center;
}
.performance-box{
  padding:12px;border-radius:8px;margin:8px 0;
  font-weight:500;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASE CONNECTION & QUERY FUNCTIONS
# ============================================================
@st.cache_resource
def init_connection():
    """Initialize PostgreSQL connection"""
    try:
        conn = psycopg2.connect(
            st.secrets["NEON_DATABASE_URL"],
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
        st.stop()

def get_conn():
    """Get or refresh database connection"""
    if "db_conn" not in st.session_state or st.session_state.db_conn.closed:
        st.session_state.db_conn = init_connection()
    return st.session_state.db_conn

def run_query(query, params=None, fetch=False):
    """Execute a single query"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or [])
            if fetch:
                return cur.fetchall()
            conn.commit()
            return None
    except psycopg2.OperationalError:
        st.session_state.db_conn = init_connection()
        return run_query(query, params, fetch)
    except Exception as e:
        conn.rollback()
        st.error(f"Database error: {str(e)}")
        return None if fetch else False

def run_many(query, data):
    """Execute batch insert"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.executemany(query, data)
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        st.error(f"Batch insert error: {str(e)}")
        return False

# ============================================================
# PASSWORD HASHING FUNCTIONS
# ============================================================
def hash_password(password: str, salt: str = None) -> tuple:
    """Hash password with salt using SHA-256"""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify password against stored hash"""
    test_hash, _ = hash_password(password, salt)
    return test_hash == hashed

# ============================================================
# DATABASE INITIALIZATION
# ============================================================
def initialize_database():
    """Create all tables and insert default data"""
    
    # Drop existing tables (fresh start)
    run_query("""
        DROP TABLE IF EXISTS audit_log, kpi_entries, users, employees, 
        departments, app_settings, kpi_master, kpi_weights, rating_rules CASCADE
    """)
    
    # Create departments table
    run_query("""
        CREATE TABLE departments (
            id SERIAL PRIMARY KEY,
            department_name TEXT UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create employees table
    run_query("""
        CREATE TABLE employees (
            id SERIAL PRIMARY KEY,
            employee_name TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create users table
    run_query("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'employee')),
            employee_name TEXT,
            department TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            created_by TEXT
        )
    """)
    
    # Create kpi_entries table
    run_query("""
        CREATE TABLE kpi_entries (
            id SERIAL PRIMARY KEY,
            employee_name TEXT NOT NULL,
            department TEXT NOT NULL,
            kpi1 INTEGER,
            kpi2 INTEGER,
            kpi3 INTEGER,
            kpi4 INTEGER,
            total_score DOUBLE PRECISION,
            rating TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            entry_month TEXT,
            created_by TEXT,
            updated_by TEXT,
            updated_at TIMESTAMP
        )
    """)
    
    # Create audit_log table
    run_query("""
        CREATE TABLE audit_log (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create app_settings table
    run_query("""
        CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    # Create kpi_master table
    run_query("""
        CREATE TABLE kpi_master (
            kpi_key TEXT PRIMARY KEY,
            kpi_label TEXT NOT NULL
        )
    """)
    
    # Create kpi_weights table
    run_query("""
        CREATE TABLE kpi_weights (
            kpi_key TEXT PRIMARY KEY,
            weight INTEGER NOT NULL
        )
    """)
    
    # Create rating_rules table
    run_query("""
        CREATE TABLE rating_rules (
            id INTEGER PRIMARY KEY DEFAULT 1,
            excellent_min INTEGER NOT NULL,
            good_min INTEGER NOT NULL,
            average_min INTEGER NOT NULL
        )
    """)
    
    # Insert default app settings
    default_settings = [
        ("allow_import", "1"),
        ("allow_edit_delete", "1"),
        ("session_timeout", "30")
    ]
    run_many("INSERT INTO app_settings(key, value) VALUES (%s,%s) ON CONFLICT (key) DO NOTHING", default_settings)
    
    # Insert default KPI labels
    default_kpi_labels = [
        ("kpi1", "Quality"),
        ("kpi2", "Productivity"),
        ("kpi3", "Attendance"),
        ("kpi4", "Behavior")
    ]
    run_many("INSERT INTO kpi_master(kpi_key, kpi_label) VALUES (%s,%s) ON CONFLICT (kpi_key) DO NOTHING", default_kpi_labels)
    
    # Insert default KPI weights
    default_weights = [
        ("kpi1", 25),
        ("kpi2", 25),
        ("kpi3", 25),
        ("kpi4", 25)
    ]
    run_many("INSERT INTO kpi_weights(kpi_key, weight) VALUES (%s,%s) ON CONFLICT (kpi_key) DO NOTHING", default_weights)
    
    # Insert default rating rules
    run_query("INSERT INTO rating_rules(id, excellent_min, good_min, average_min) VALUES (1, 80, 60, 40) ON CONFLICT (id) DO NOTHING")
    
    # Create default admin user
    admin_check = run_query("SELECT id FROM users WHERE username='admin'", fetch=True)
    if not admin_check:
        hashed, salt = hash_password("admin123")
        run_query("""
            INSERT INTO users (username, password_hash, password_salt, full_name, role, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ["admin", hashed, salt, "System Administrator", "admin", True, "system"])
    
    # Insert sample departments
    sample_departments = [
        ("Fabric", True),
        ("Dyeing", True),
        ("Quality Control", True),
        ("Production", True),
        ("Finishing", True),
        ("Stitching", True)
    ]
    run_many("INSERT INTO departments (department_name, is_active) VALUES (%s, %s) ON CONFLICT (department_name) DO NOTHING", 
             sample_departments)
    
    return True

# Initialize database on first run
if "db_initialized" not in st.session_state:
    with st.spinner("🔄 Initializing database... Please wait..."):
        if initialize_database():
            st.session_state.db_initialized = True
            st.success("✅ Database initialized successfully!")

# ============================================================
# AUDIT LOG FUNCTION
# ============================================================
def log_action(username: str, action: str, details: str = ""):
    """Log user actions for audit trail"""
    run_query("""
        INSERT INTO audit_log (username, action, details, timestamp)
        VALUES (%s, %s, %s, %s)
    """, [username, action, details, datetime.now()])

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def get_setting(key, default=""):
    """Get app setting value"""
    r = run_query("SELECT value FROM app_settings WHERE key=%s", [key], fetch=True)
    return r[0][0] if r else default

def set_setting(key, value):
    """Set app setting value"""
    run_query("""
        INSERT INTO app_settings(key, value)
        VALUES (%s,%s)
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
    """, [key, value])

def get_kpi_labels():
    """Get KPI label names"""
    rows = run_query("SELECT kpi_key, kpi_label FROM kpi_master ORDER BY kpi_key", fetch=True) or []
    d = {k:v for k,v in rows}
    return d.get("kpi1","KPI 1"), d.get("kpi2","KPI 2"), d.get("kpi3","KPI 3"), d.get("kpi4","KPI 4")

def get_kpi_weights():
    """Get KPI weights"""
    rows = run_query("SELECT kpi_key, weight FROM kpi_weights ORDER BY kpi_key", fetch=True) or []
    d = {k:int(w) for k,w in rows}
    return d.get("kpi1",25), d.get("kpi2",25), d.get("kpi3",25), d.get("kpi4",25)

def get_rating_rules():
    """Get rating threshold rules"""
    r = run_query("SELECT excellent_min, good_min, average_min FROM rating_rules WHERE id=1", fetch=True)
    return (int(r[0][0]), int(r[0][1]), int(r[0][2])) if r else (80, 60, 40)

def calc_weighted_score(k1, k2, k3, k4):
    """Calculate weighted KPI score"""
    w1, w2, w3, w4 = get_kpi_weights()
    return round((k1*w1 + k2*w2 + k3*w3 + k4*w4) / 100.0, 2)

def calc_rating(score: float):
    """Calculate rating based on score"""
    ex, gd, av = get_rating_rules()
    if score >= ex: return "Excellent"
    if score >= gd: return "Good"
    if score >= av: return "Average"
    return "Needs Improvement"

def get_active_employees():
    """Get list of active employees"""
    return run_query("SELECT employee_name, department FROM employees WHERE is_active=TRUE ORDER BY employee_name", fetch=True) or []

def get_all_employees():
    """Get all employees"""
    return run_query("SELECT id, employee_name, department, is_active, created_at FROM employees ORDER BY employee_name", fetch=True) or []

def get_active_departments():
    """Get list of active departments"""
    rows = run_query("SELECT department_name FROM departments WHERE is_active=TRUE ORDER BY department_name", fetch=True) or []
    return [r[0] for r in rows]

def get_all_departments():
    """Get all departments"""
    return run_query("SELECT id, department_name, is_active, created_at FROM departments ORDER BY department_name", fetch=True) or []

# ============================================================
# AUTHENTICATION FUNCTIONS
# ============================================================
def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user and return user info"""
    user = run_query("""
        SELECT id, username, password_hash, password_salt, full_name, role, 
               employee_name, department, is_active 
        FROM users WHERE username=%s
    """, [username], fetch=True)
    
    if not user:
        return {"success": False, "message": "❌ Invalid username or password"}
    
    user_id, uname, pwd_hash, pwd_salt, full_name, role, emp_name, dept, is_active = user[0]
    
    if not is_active:
        return {"success": False, "message": "⚠️ Account is inactive. Contact administrator."}
    
    if not verify_password(password, pwd_hash, pwd_salt):
        return {"success": False, "message": "❌ Invalid username or password"}
    
    # Update last login
    run_query("UPDATE users SET last_login=%s WHERE id=%s", [datetime.now(), user_id])
    log_action(username, "LOGIN", "User logged in successfully")
    
    return {
        "success": True,
        "user_id": user_id,
        "username": uname,
        "full_name": full_name,
        "role": role,
        "employee_name": emp_name,
        "department": dept
    }

def check_permission(required_role: str) -> bool:
    """Check if current user has required permission"""
    if "user" not in st.session_state:
        return False
    user_role = st.session_state["user"]["role"]
    role_levels = {"admin": 3, "manager": 2, "employee": 1}
    return role_levels.get(user_role, 0) >= role_levels.get(required_role, 0)

def require_auth(required_role: str = "employee"):
    """Require authentication with specific role"""
    if "user" not in st.session_state:
        return False
    if not check_permission(required_role):
        st.error(f"⛔ Access Denied: {required_role.upper()} role required")
        return False
    return True

# ============================================================
# LOGIN PAGE
# ============================================================
def show_login_page():
    """Display login page"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown("## 🔐 Yash Gallery KPI System")
    st.markdown("### Welcome Back!")
    st.markdown("---")
    
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("👤 Username", placeholder="Enter your username", key="login_user")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_pass")
        
        col1, col2 = st.columns(2)
        submit = col1.form_submit_button("🚀 Login", use_container_width=True)
        clear = col2.form_submit_button("❌ Clear", use_container_width=True)
        
        if submit:
            if username and password:
                result = authenticate_user(username, password)
                if result["success"]:
                    st.session_state["user"] = result
                    st.session_state["logged_in"] = True
                    st.success(f"✅ Welcome, {result['full_name']}!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(result["message"])
            else:
                st.error("⚠️ Please enter both username and password")
    
    st.markdown("---")
    st.markdown("""
    <div class='small' style='text-align:center'>
        <b>🔑 Default Login Credentials:</b><br>
        Username: <code>admin</code> | Password: <code>admin123</code><br><br>
        <b>💡 First Time Setup:</b><br>
        1. Login as admin<br>
        2. Create departments (already added: Fabric, Dyeing, etc.)<br>
        3. Add employees<br>
        4. Create user accounts<br>
        5. Start tracking KPIs!
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# SESSION MANAGEMENT
# ============================================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "user" not in st.session_state:
    st.session_state["user"] = None

# Show login page if not authenticated
if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()

# Get current user info
current_user = st.session_state["user"]
username = current_user["username"]
full_name = current_user["full_name"]
user_role = current_user["role"]
user_employee_name = current_user.get("employee_name")
user_department = current_user.get("department")

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### 👤 User Profile")
    st.markdown(f"**{full_name}**")
    st.markdown(f"<span class='role-badge-{user_role}'>{user_role.upper()}</span>", unsafe_allow_html=True)
    
    if user_employee_name:
        st.markdown(f"**Employee:** {user_employee_name}")
    if user_department:
        st.markdown(f"**Department:** {user_department}")
    
    st.markdown(f"**Username:** {username}")
    
    if st.button("🚪 Logout", use_container_width=True, type="primary"):
        log_action(username, "LOGOUT", "User logged out")
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    st.markdown("## 🔎 Data Filters")
    
    # Role-based filtering
    if user_role == "employee":
        dept_filter = user_department or "All"
        emp_filter = user_employee_name or "All"
        st.info("📌 Viewing your data only")
    else:
        dept_rows = run_query(
            "SELECT DISTINCT department FROM kpi_entries WHERE department IS NOT NULL AND department<>'' ORDER BY department",
            fetch=True
        ) or []
        dept_list = [r[0] for r in dept_rows]
        
        if user_role == "manager":
            dept_list = [d for d in dept_list if d == user_department]
            if user_department and user_department in dept_list:
                dept_filter = user_department
                st.info(f"📌 Department: {user_department}")
            else:
                dept_filter = "All"
        else:
            dept_filter = st.selectbox("🏢 Department", ["All"] + dept_list)
        
        emp_q = "SELECT DISTINCT employee_name FROM kpi_entries WHERE employee_name IS NOT NULL AND employee_name<>''"
        emp_p = []
        if dept_filter != "All":
            emp_q += " AND department=%s"
            emp_p.append(dept_filter)
        emp_q += " ORDER BY employee_name"
        
        emp_rows = run_query(emp_q, emp_p, fetch=True) or []
        emp_list = [r[0] for r in emp_rows]
        emp_filter = st.selectbox("👤 Employee", ["All"] + emp_list)
    
    date_range = st.date_input("📅 Date Range", value=[])
    rating_filter = st.selectbox("⭐ Rating", ["All", "Excellent", "Good", "Average", "Needs Improvement"])

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="card">', unsafe_allow_html=True)
col_h1, col_h2 = st.columns([3, 2])

with col_h1:
    st.title("📊 Yash Gallery – KPI Management System")
    st.caption("🔐 Role-Based Access • 👥 Multi-User Support • 📋 Audit Trail • 📈 Real-Time Analytics")

with col_h2:
    st.markdown(f"""
        <div style='text-align:right;padding:10px'>
            <span class='badge badge-info'>User: {username}</span><br>
            <span class='role-badge-{user_role}'>{user_role.upper()}</span>
            <span class='badge badge-success'>● Online</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# DYNAMIC MENU BASED ON ROLE
# ============================================================
if user_role == "admin":
    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employees", "Departments", "Users", "Audit Log", "Settings"]
    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people", "building", "person-badge", "clipboard-data", "gear"]
elif user_role == "manager":
    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employees"]
    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people"]
else:  # employee
    menu_options = ["Dashboard", "My Records"]
    menu_icons = ["speedometer2", "table"]

menu = option_menu(
    None,
    menu_options,
    icons=menu_icons,
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0.2rem 0", "background-color": "#ffffff", 
                     "border": "1px solid #e5e7eb", "border-radius": "14px"},
        "icon": {"color": "#2563EB", "font-size": "16px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", 
                    "padding": "10px 12px", "color": "#374151"},
        "nav-link-selected": {"background-color": "#2563EB", "color": "white", 
                             "font-weight": "bold"},
    }
)

# ============================================================
# QUERY KPI ENTRIES
# ============================================================
q = """
SELECT id, employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, 
       created_at, COALESCE(created_by, 'system') as created_by
FROM kpi_entries WHERE 1=1
"""
p = []

# Role-based data filtering
if user_role == "employee":
    q += " AND employee_name=%s"
    p.append(user_employee_name)
elif user_role == "manager":
    q += " AND department=%s"
    p.append(user_department)

if dept_filter != "All" and user_role == "admin":
    q += " AND department=%s"
    p.append(dept_filter)
if emp_filter != "All" and user_role != "employee":
    q += " AND employee_name=%s"
    p.append(emp_filter)
if rating_filter != "All":
    q += " AND rating=%s"
    p.append(rating_filter)
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    q += " AND DATE(created_at) BETWEEN %s AND %s"
    p += [str(date_range[0]), str(date_range[1])]

q += " ORDER BY created_at DESC"

rows = run_query(q, p, fetch=True) or []
df = pd.DataFrame(rows, columns=["ID", "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
                                 "Score", "Rating", "Created At", "Created By"])

kpi1_lbl, kpi2_lbl, kpi3_lbl, kpi4_lbl = get_kpi_labels()

# ============================================================
# DASHBOARD
# ============================================================
if menu == "Dashboard":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 KPI Performance Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_records = len(df)
    avg_score = round(float(df["Score"].mean()), 2) if total_records > 0 else 0
    best_score = round(float(df["Score"].max()), 2) if total_records > 0 else 0
    
    if user_role == "admin":
        active_emp = len(run_query("SELECT id FROM employees WHERE is_active=TRUE", fetch=True) or [])
        active_dept = len(run_query("SELECT id FROM departments WHERE is_active=TRUE", fetch=True) or [])
    elif user_role == "manager":
        active_emp = len(run_query("SELECT id FROM employees WHERE is_active=TRUE AND department=%s", 
                                  [user_department], fetch=True) or [])
        active_dept = 1
    else:
        active_emp = 1
        active_dept = 1
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("📝 Total Records", total_records)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("⭐ Average Score", avg_score)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🏆 Best Score", best_score)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("👥 Employees", active_emp)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col5:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🏢 Departments", active_dept)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    if len(df) > 0:
        st.write("")
        
        # Rating Distribution & Performance Summary
        col_chart1, col_chart2 = st.columns([1.5, 1])
        
        with col_chart1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📊 Rating Distribution")
            rating_counts = df["Rating"].value_counts().reset_index()
            rating_counts.columns = ["Rating", "Count"]
            
            colors = {
                "Excellent": "#10b981",
                "Good": "#3b82f6",
                "Average": "#f59e0b",
                "Needs Improvement": "#ef4444"
            }
            
            fig = px.pie(rating_counts, values="Count", names="Rating", 
                        color="Rating", color_discrete_map=colors, hole=0.4)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(showlegend=True, height=350)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col_chart2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🎯 Performance Breakdown")
            total_cnt = len(df)
            
            for rating, color, emoji in [
                ("Excellent", "#dcfce7", "🌟"),
                ("Good", "#dbeafe", "👍"),
                ("Average", "#fef3c7", "📊"),
                ("Needs Improvement", "#fee2e2", "⚠️")
            ]:
                cnt = len(df[df["Rating"] == rating])
                pct = round(cnt/total_cnt*100, 1) if total_cnt > 0 else 0
                st.markdown(f"""
                <div class='performance-box' style='background:{color}'>
                    <b>{emoji} {rating}:</b> {cnt} records ({pct}%)
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Department & Employee Performance
        if user_role != "employee":
            st.write("")
            col_perf1, col_perf2 = st.columns(2)
            
            with col_perf1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("🏭 Department Performance")
                dept_avg = df.groupby("Department")["Score"].mean().reset_index()
                dept_avg = dept_avg.sort_values("Score", ascending=False)
                fig = px.bar(dept_avg, x="Department", y="Score", 
                            color="Score", color_continuous_scale="Viridis",
                            text="Score")
                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col_perf2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("👤 Top 10 Performers")
                top_emp = df.groupby("Employee")["Score"].mean().reset_index()
                top_emp = top_emp.sort_values("Score", ascending=False).head(10)
                fig = px.bar(top_emp, x="Score", y="Employee", orientation='h',
                            color="Score", color_continuous_scale="RdYlGn",
                            text="Score")
                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, height=400)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Monthly Trend
        st.write("")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📈 Monthly Performance Trend")
        tmp = df.copy()
        tmp["Month"] = pd.to_datetime(tmp["Created At"]).dt.to_period("M").astype(str)
        monthly_avg = tmp.groupby("Month")["Score"].mean().reset_index()
        monthly_avg = monthly_avg.sort_values("Month")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly_avg["Month"],
            y=monthly_avg["Score"],
            mode='lines+markers',
            name='Average Score',
            line=dict(color='#2563eb', width=3),
            marker=dict(size=10, color='#2563eb')
        ))
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Average Score",
            hovermode='x unified',
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("📌 No KPI data available. Start by adding entries!")

# ============================================================
# ENTRY
# ============================================================
if menu == "Entry":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("➕ Add New KPI Entry")
    
    with st.form("add_kpi_form", clear_on_submit=True):
        col_info1, col_info2 = st.columns([2, 1])
        
        with col_info1:
            active_emps = get_active_employees()
            
            if user_role == "manager":
                active_emps = [e for e in active_emps if e[1] == user_department]
            
            emp_list = [e[0] for e in active_emps]
            emp = st.selectbox("🔍 Select Employee", [""] + emp_list, help="Choose employee to add KPI entry")
            
            if emp:
                dept = [e[1] for e in active_emps if e[0] == emp][0]
                st.success(f"✅ Department: **{dept}**")
            else:
                dept = user_department if user_role == "manager" else ""
        
        with col_info2:
            st.markdown("### 📅 Entry Info")
            st.info(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}")
            st.info(f"**Created By:** {username}")
        
        st.markdown("---")
        st.markdown("### 📊 Enter KPI Scores (1-100)")
        
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        
        with col_k1:
            v1 = st.number_input(f"🎯 {kpi1_lbl}", min_value=1, max_value=100, value=50, step=1)
        with col_k2:
            v2 = st.number_input(f"📈 {kpi2_lbl}", min_value=1, max_value=100, value=50, step=1)
        with col_k3:
            v3 = st.number_input(f"📅 {kpi3_lbl}", min_value=1, max_value=100, value=50, step=1)
        with col_k4:
            v4 = st.number_input(f"🤝 {kpi4_lbl}", min_value=1, max_value=100, value=50, step=1)
        
        # Calculate preview score
        preview_score = calc_weighted_score(v1, v2, v3, v4)
        preview_rating = calc_rating(preview_score)
        
        st.markdown("---")
        col_preview, col_submit = st.columns([2, 1])
        
        with col_preview:
            st.markdown(f"### 📊 Preview:")
            st.markdown(f"**Weighted Score:** {preview_score} / 100")
            st.markdown(f"**Rating:** {preview_rating}")
        
        with col_submit:
            submit = st.form_submit_button("✅ Save Entry", use_container_width=True, type="primary")
    
    if submit:
        if emp and dept:
            score = calc_weighted_score(v1, v2, v3, v4)
            rating = calc_rating(score)
            now = datetime.now()
            month = now.strftime("%Y-%m")
            
            result = run_query("""
                INSERT INTO kpi_entries (employee_name, department, kpi1, kpi2, kpi3, kpi4, 
                                        total_score, rating, created_at, entry_month, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [emp, dept, v1, v2, v3, v4, score, rating, now, month, username])
            
            if result is not None:
                log_action(username, "CREATE_KPI_ENTRY", f"Created entry for {emp} - Score: {score}")
                st.success(f"✅ Entry saved successfully! **Score:** {score} | **Rating:** {rating}")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Failed to save entry. Please try again.")
        else:
            st.error("⚠️ Please select an employee before submitting.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# RECORDS / MY RECORDS
# ============================================================
if menu in ["Records", "My Records"]:
    if menu == "Records" and not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 KPI Records" if menu == "Records" else "📋 My KPI Records")
    
    if len(df) > 0:
        # Rename columns for display
        show_df = df.drop(columns=["ID"]).rename(columns={
            "KPI1": kpi1_lbl,
            "KPI2": kpi2_lbl,
            "KPI3": kpi3_lbl,
            "KPI4": kpi4_lbl
        })
        
        # Color coding for ratings
        def highlight_rating(row):
            colors = {
                "Excellent": "background-color: #dcfce7",
                "Good": "background-color: #dbeafe",
                "Average": "background-color: #fef3c7",
                "Needs Improvement": "background-color: #fee2e2"
            }
            return [colors.get(row["Rating"], "")] * len(row)
        
        styled_df = show_df.style.apply(highlight_rating, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Export options
        st.markdown("---")
        col_exp1, col_exp2, col_exp3 = st.columns([2, 1, 1])
        
        with col_exp1:
            st.markdown(f"**Total Records:** {len(df)}")
        
        with col_exp2:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"kpi_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_exp3:
            excel_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 Download Excel",
                data=excel_data,
                file_name=f"kpi_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )
    else:
        st.info("📌 No records found matching the current filters.")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Edit/Delete Section (for Manager and Admin)
    if user_role in ["admin", "manager"] and len(df) > 0 and get_setting("allow_edit_delete", "1") == "1":
        st.write("")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("✏️ Edit / Delete Records")
        
        rec_id = st.selectbox("🔍 Select Record ID", df["ID"].tolist())
        row = df[df["ID"] == rec_id].iloc[0]
        
        col_edit1, col_edit2 = st.columns([2, 1])
        
        with col_edit1:
            st.markdown("#### 📝 Edit KPI Values")
            col_k1, col_k2, col_k3, col_k4 = st.columns(4)
            
            with col_k1:
                e_k1 = st.number_input(kpi1_lbl, 1, 100, int(row["KPI1"]), key="edit_k1")
            with col_k2:
                e_k2 = st.number_input(kpi2_lbl, 1, 100, int(row["KPI2"]), key="edit_k2")
            with col_k3:
                e_k3 = st.number_input(kpi3_lbl, 1, 100, int(row["KPI3"]), key="edit_k3")
            with col_k4:
                e_k4 = st.number_input(kpi4_lbl, 1, 100, int(row["KPI4"]), key="edit_k4")
        
        with col_edit2:
            st.markdown("#### 📊 Current Info")
            st.info(f"**Employee:** {row['Employee']}")
            st.info(f"**Department:** {row['Department']}")
            st.info(f"**Current Score:** {row['Score']}")
            st.info(f"**Current Rating:** {row['Rating']}")
            
            new_score = calc_weighted_score(e_k1, e_k2, e_k3, e_k4)
            new_rating = calc_rating(new_score)
            st.success(f"**New Score:** {new_score}")
            st.success(f"**New Rating:** {new_rating}")
        
        st.markdown("---")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
        
        with col_btn1:
            if st.button("💾 Update Record", use_container_width=True, type="primary"):
                run_query("""
                    UPDATE kpi_entries 
                    SET kpi1=%s, kpi2=%s, kpi3=%s, kpi4=%s, total_score=%s, rating=%s, 
                        updated_by=%s, updated_at=%s
                    WHERE id=%s
                """, [e_k1, e_k2, e_k3, e_k4, new_score, new_rating, username, datetime.now(), rec_id])
                
                log_action(username, "UPDATE_KPI_ENTRY", f"Updated entry ID {rec_id} for {row['Employee']}")
                st.success("✅ Record updated successfully!")
                st.rerun()
        
        with col_btn2:
            if st.button("🗑️ Delete Record", use_container_width=True, type="secondary"):
                run_query("DELETE FROM kpi_entries WHERE id=%s", [rec_id])
                log_action(username, "DELETE_KPI_ENTRY", f"Deleted entry ID {rec_id} for {row['Employee']}")
                st.warning("🗑️ Record deleted!")
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# REPORTS
# ============================================================
if menu == "Reports":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 Performance Reports")
    
    if len(df) > 0:
        tmp = df.copy()
        tmp["Month"] = pd.to_datetime(tmp["Created At"]).dt.to_period("M").astype(str)
        months = sorted(tmp["Month"].unique())[::-1]
        
        col_r1, col_r2, col_r3 = st.columns(3)
        
        with col_r1:
            report_type = st.selectbox("📋 Report Type", ["Employee Wise Average", "Department Wise Average", "Detailed Records"])
        
        with col_r2:
            sel_month = st.selectbox("📅 Select Month", months)
        
        with col_r3:
            chart_type = st.selectbox("📈 Chart Type", ["Bar Chart", "Line Chart", "Pie Chart"])
        
        mdf = tmp[tmp["Month"] == sel_month]
        
        st.markdown("---")
        
        if report_type == "Employee Wise Average":
            rep = mdf.groupby("Employee")["Score"].mean().reset_index()
            rep = rep.sort_values("Score", ascending=False)
            x_col, y_col = "Employee", "Score"
        elif report_type == "Department Wise Average":
            rep = mdf.groupby("Department")["Score"].mean().reset_index()
            rep = rep.sort_values("Score", ascending=False)
            x_col, y_col = "Department", "Score"
        else:
            rep = mdf[["Employee", "Department", "Score", "Rating"]].copy()
            x_col, y_col = "Employee", "Score"
        
        # Generate chart
        if chart_type == "Bar Chart":
            fig = px.bar(rep, x=x_col, y=y_col, color=y_col, 
                        color_continuous_scale="Viridis", text=y_col)
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        elif chart_type == "Line Chart":
            fig = px.line(rep, x=x_col, y=y_col, markers=True)
        else:
            fig = px.pie(rep, values=y_col, names=x_col)
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.dataframe(rep, use_container_width=True, hide_index=True)
        
        # Export report
        csv = rep.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Report",
            data=csv,
            file_name=f"report_{sel_month}_{report_type.replace(' ', '_')}.csv",
            mime="text/csv"
        )
    else:
        st.info("📌 No data available for reports.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# EMPLOYEES MANAGEMENT
# ============================================================
if menu == "Employees":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👥 Employee Management")
    
    tab1, tab2 = st.tabs(["➕ Add Employee", "📋 Manage Employees"])
    
    with tab1:
        st.markdown("### Add New Employee")
        
        with st.form("add_employee_form"):
            col_add1, col_add2 = st.columns(2)
            
            with col_add1:
                emp_name = st.text_input("👤 Employee Name", placeholder="Enter full name")
            
            with col_add2:
                if user_role == "admin":
                    emp_dept = st.selectbox("🏢 Department", get_active_departments())
                else:
                    emp_dept = user_department
                    st.info(f"🏢 Department: **{user_department}**")
            
            emp_active = st.checkbox("✅ Active Status", value=True)
            
            submit = st.form_submit_button("➕ Add Employee", use_container_width=True, type="primary")
            
            if submit:
                if emp_name.strip() and emp_dept:
                    result = run_query("""
                        INSERT INTO employees (employee_name, department, is_active, created_at)
                        VALUES (%s, %s, %s, %s)
                    """, [emp_name.strip(), emp_dept, emp_active, datetime.now()])
                    
                    if result is not None:
                        log_action(username, "ADD_EMPLOYEE", f"Added employee: {emp_name}")
                        st.success(f"✅ Employee '{emp_name}' added successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Employee already exists or error occurred.")
                else:
                    st.error("⚠️ Please enter employee name and select department.")
    
    with tab2:
        st.markdown("### Existing Employees")
        
        emps = get_all_employees()
        
        if user_role == "manager":
            emps = [e for e in emps if e[2] == user_department]
        
        if emps:
            emp_df = pd.DataFrame(emps, columns=["ID", "Name", "Dept", "Active", "Created"])
            emp_df["Status"] = emp_df["Active"].apply(lambda x: "✅ Active" if x else "❌ Inactive")
            
            st.dataframe(emp_df[["Name", "Dept", "Status", "Created"]], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### ✏️ Edit Employee")
            
            emp_to_edit = st.selectbox("Select Employee", [e[1] for e in emps])
            
            if emp_to_edit:
                emp_data = [e for e in emps if e[1] == emp_to_edit][0]
                emp_id, emp_name, emp_dept, emp_active, _ = emp_data
                
                col_e1, col_e2 = st.columns(2)
                
                with col_e1:
                    new_name = st.text_input("Employee Name", value=emp_name, key="edit_emp_name")
                    
                    if user_role == "admin":
                        depts = get_active_departments()
                        new_dept = st.selectbox("Department", depts, 
                                               index=depts.index(emp_dept) if emp_dept in depts else 0,
                                               key="edit_emp_dept")
                    else:
                        new_dept = emp_dept
                        st.info(f"Department: **{emp_dept}**")
                
                with col_e2:
                    new_active = st.checkbox("Active Status", value=emp_active, key="edit_emp_active")
                    st.info(f"**Current Status:** {'✅ Active' if emp_active else '❌ Inactive'}")
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("💾 Update Employee", use_container_width=True, type="primary"):
                        run_query("""
                            UPDATE employees 
                            SET employee_name=%s, department=%s, is_active=%s, updated_at=%s
                            WHERE id=%s
                        """, [new_name.strip(), new_dept, new_active, datetime.now(), emp_id])
                        
                        log_action(username, "UPDATE_EMPLOYEE", f"Updated: {emp_name} → {new_name}")
                        st.success("✅ Employee updated successfully!")
                        st.rerun()
                
                with col_btn2:
                    if st.button("🗑️ Delete Employee", use_container_width=True, type="secondary") and user_role == "admin":
                        entries = run_query("SELECT COUNT(*) FROM kpi_entries WHERE employee_name=%s", 
                                          [emp_name], fetch=True)
                        if entries and entries[0][0] > 0:
                            st.error(f"⚠️ Cannot delete! {entries[0][0]} KPI entries exist for this employee.")
                        else:
                            run_query("DELETE FROM employees WHERE id=%s", [emp_id])
                            log_action(username, "DELETE_EMPLOYEE", f"Deleted employee: {emp_name}")
                            st.success("🗑️ Employee deleted!")
                            st.rerun()
        else:
            st.info("📌 No employees found. Add employees using the 'Add Employee' tab.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# DEPARTMENTS MANAGEMENT (Admin Only)
# ============================================================
if menu == "Departments":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🏢 Department Management")
    
    tab1, tab2 = st.tabs(["➕ Add Department", "📋 Manage Departments"])
    
    with tab1:
        st.markdown("### Add New Department")
        
        with st.form("add_dept_form"):
            dept_name = st.text_input("🏢 Department Name", placeholder="e.g., Fabric, Dyeing, Quality Control")
            dept_active = st.checkbox("✅ Active Status", value=True)
            
            submit = st.form_submit_button("➕ Add Department", use_container_width=True, type="primary")
            
            if submit:
                if dept_name.strip():
                    result = run_query("""
                        INSERT INTO departments (department_name, is_active, created_at)
                        VALUES (%s, %s, %s)
                    """, [dept_name.strip(), dept_active, datetime.now()])
                    
                    if result is not None:
                        log_action(username, "ADD_DEPARTMENT", f"Added department: {dept_name}")
                        st.success(f"✅ Department '{dept_name}' added successfully!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Department already exists or error occurred.")
                else:
                    st.error("⚠️ Please enter department name.")
    
    with tab2:
        st.markdown("### Existing Departments")
        
        depts = get_all_departments()
        
        if depts:
            dept_df = pd.DataFrame(depts, columns=["ID", "Name", "Active", "Created"])
            dept_df["Status"] = dept_df["Active"].apply(lambda x: "✅ Active" if x else "❌ Inactive")
            
            # Count employees per department
            for idx, row in dept_df.iterrows():
                emp_count = run_query("SELECT COUNT(*) FROM employees WHERE department=%s", 
                                     [row["Name"]], fetch=True)
                dept_df.at[idx, "Employees"] = emp_count[0][0] if emp_count else 0
            
            st.dataframe(dept_df[["Name", "Status", "Employees", "Created"]], 
                        use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### ✏️ Edit Department")
            
            dept_to_edit = st.selectbox("Select Department", [d[1] for d in depts])
            
            if dept_to_edit:
                dept_data = [d for d in depts if d[1] == dept_to_edit][0]
                dept_id, dept_name, dept_active, _ = dept_data
                
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    new_dept_name = st.text_input("Department Name", value=dept_name, key="edit_dept_name")
                
                with col_d2:
                    new_dept_active = st.checkbox("Active Status", value=dept_active, key="edit_dept_active")
                    st.info(f"**Current:** {'✅ Active' if dept_active else '❌ Inactive'}")
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("💾 Update Department", use_container_width=True, type="primary"):
                        run_query("""
                            UPDATE departments 
                            SET department_name=%s, is_active=%s
                            WHERE id=%s
                        """, [new_dept_name.strip(), new_dept_active, dept_id])
                        
                        log_action(username, "UPDATE_DEPARTMENT", f"Updated: {dept_name} → {new_dept_name}")
                        st.success("✅ Department updated successfully!")
                        st.rerun()
                
                with col_btn2:
                    if st.button("🗑️ Delete Department", use_container_width=True, type="secondary"):
                        emp_count = run_query("SELECT COUNT(*) FROM employees WHERE department=%s", 
                                            [dept_name], fetch=True)
                        if emp_count and emp_count[0][0] > 0:
                            st.error(f"⚠️ Cannot delete! {emp_count[0][0]} employees exist in this department.")
                        else:
                            run_query("DELETE FROM departments WHERE id=%s", [dept_id])
                            log_action(username, "DELETE_DEPARTMENT", f"Deleted department: {dept_name}")
                            st.success("🗑️ Department deleted!")
                            st.rerun()
        else:
            st.info("📌 No departments found. Add departments using the 'Add Department' tab.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# USER MANAGEMENT (Admin Only)
# ============================================================
if menu == "Users":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👨‍💼 User Management")
    
    tab1, tab2 = st.tabs(["➕ Create User", "📋 Manage Users"])
    
    with tab1:
        st.markdown("### Create New User Account")
        
        with st.form("add_user_form"):
            col_u1, col_u2 = st.columns(2)
            
            with col_u1:
                new_username = st.text_input("👤 Username", placeholder="e.g., john.doe")
                new_password = st.text_input("🔒 Password", type="password", placeholder="Min 6 characters")
                new_password2 = st.text_input("🔒 Confirm Password", type="password")
            
            with col_u2:
                new_fullname = st.text_input("📝 Full Name", placeholder="e.g., John Doe")
                new_role = st.selectbox("🎯 Role", ["employee", "manager", "admin"])
                
                if new_role in ["employee", "manager"]:
                    active_emps = get_active_employees()
                    emp_list = [e[0] for e in active_emps]
                    new_emp_name = st.selectbox("🔗 Link to Employee", [""] + emp_list)
                    
                    if new_emp_name:
                        emp_dept = [e[1] for e in active_emps if e[0] == new_emp_name]
                        new_dept = emp_dept[0] if emp_dept else ""
                        st.info(f"Department: **{new_dept}**")
                    else:
                        new_dept = ""
                else:
                    new_emp_name = ""
                    new_dept = ""
            
            new_active = st.checkbox("✅ Active Status", value=True)
            
            submit = st.form_submit_button("➕ Create User", use_container_width=True, type="primary")
            
            if submit:
                if not new_username or not new_password or not new_fullname:
                    st.error("⚠️ Username, password, and full name are required.")
                elif len(new_password) < 6:
                    st.error("⚠️ Password must be at least 6 characters.")
                elif new_password != new_password2:
                    st.error("⚠️ Passwords do not match.")
                else:
                    hashed, salt = hash_password(new_password)
                    result = run_query("""
                        INSERT INTO users (username, password_hash, password_salt, full_name, role,
                                         employee_name, department, is_active, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [new_username, hashed, salt, new_fullname, new_role, 
                         new_emp_name or None, new_dept or None, new_active, username])
                    
                    if result is not None:
                        log_action(username, "CREATE_USER", f"Created user: {new_username} ({new_role})")
                        st.success(f"✅ User '{new_username}' created successfully!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Username already exists.")
    
    with tab2:
        st.markdown("### Existing Users")
        
        users = run_query("""
            SELECT username, full_name, role, employee_name, department, is_active, last_login
            FROM users 
            WHERE username != 'admin'
            ORDER BY created_at DESC
        """, fetch=True) or []
        
        if users:
            user_df = pd.DataFrame(users, columns=["Username", "Full Name", "Role", "Employee", 
                                                   "Department", "Active", "Last Login"])
            user_df["Status"] = user_df["Active"].apply(lambda x: "✅ Active" if x else "❌ Inactive")
            user_df["Role Badge"] = user_df["Role"].apply(lambda x: x.upper())
            
            st.dataframe(user_df[["Username", "Full Name", "Role Badge", "Employee", 
                                 "Department", "Status", "Last Login"]], 
                        use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### ✏️ Edit User")
            
            user_to_edit = st.selectbox("Select User", [u[0] for u in users])
            
            if user_to_edit:
                user_data = [u for u in users if u[0] == user_to_edit][0]
                uname, ufull, urole, uemp, udept, uactive, ulast = user_data
                
                col_ue1, col_ue2 = st.columns(2)
                
                with col_ue1:
                    edit_fullname = st.text_input("Full Name", value=ufull, key="edit_user_fullname")
                    edit_role = st.selectbox("Role", ["employee", "manager", "admin"],
                                            index=["employee", "manager", "admin"].index(urole),
                                            key="edit_user_role")
                
                with col_ue2:
                    edit_active = st.checkbox("Active Status", value=uactive, key="edit_user_active")
                    st.info(f"**Last Login:** {ulast if ulast else 'Never'}")
                    
                    # Password reset
                    st.markdown("#### 🔒 Reset Password")
                    new_pwd = st.text_input("New Password (optional)", type="password", key="edit_user_pwd")
                    new_pwd2 = st.text_input("Confirm Password", type="password", key="edit_user_pwd2")
                
                col_ubtn1, col_ubtn2 = st.columns(2)
                
                with col_ubtn1:
                    if st.button("💾 Update User", use_container_width=True, type="primary"):
                        # Update user info
                        run_query("""
                            UPDATE users 
                            SET full_name=%s, role=%s, is_active=%s
                            WHERE username=%s
                        """, [edit_fullname, edit_role, edit_active, uname])
                        
                        # Update password if provided
                        if new_pwd:
                            if len(new_pwd) >= 6 and new_pwd == new_pwd2:
                                hashed, salt = hash_password(new_pwd)
                                run_query("UPDATE users SET password_hash=%s, password_salt=%s WHERE username=%s",
                                         [hashed, salt, uname])
                                log_action(username, "RESET_PASSWORD", f"Reset password for: {uname}")
                            else:
                                st.error("⚠️ Password must be 6+ chars and match")
                        
                        log_action(username, "UPDATE_USER", f"Updated user: {uname}")
                        st.success("✅ User updated successfully!")
                        st.rerun()
                
                with col_ubtn2:
                    if st.button("🗑️ Delete User", use_container_width=True, type="secondary"):
                        run_query("DELETE FROM users WHERE username=%s", [uname])
                        log_action(username, "DELETE_USER", f"Deleted user: {uname}")
                        st.success("🗑️ User deleted!")
                        st.rerun()
        else:
            st.info("📌 No users found. Create users using the 'Create User' tab.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# AUDIT LOG (Admin Only)
# ============================================================
if menu == "Audit Log":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 System Audit Trail")
    
    col_audit1, col_audit2, col_audit3 = st.columns(3)
    
    with col_audit1:
        all_users = run_query("SELECT DISTINCT username FROM audit_log ORDER BY username", fetch=True) or []
        user_list = [u[0] for u in all_users]
        filter_user = st.selectbox("Filter by User", ["All"] + user_list)
    
    with col_audit2:
        all_actions = run_query("SELECT DISTINCT action FROM audit_log ORDER BY action", fetch=True) or []
        action_list = [a[0] for a in all_actions]
        filter_action = st.selectbox("Filter by Action", ["All"] + action_list)
    
    with col_audit3:
        limit = st.selectbox("Show Records", [50, 100, 200, 500], index=1)
    
    # Build query
    audit_q = "SELECT username, action, details, timestamp FROM audit_log WHERE 1=1"
    audit_p = []
    
    if filter_user != "All":
        audit_q += " AND username=%s"
        audit_p.append(filter_user)
    
    if filter_action != "All":
        audit_q += " AND action=%s"
        audit_p.append(filter_action)
    
    audit_q += f" ORDER BY timestamp DESC LIMIT {limit}"
    
    logs = run_query(audit_q, audit_p, fetch=True) or []
    
    if logs:
        st.markdown("---")
        log_df = pd.DataFrame(logs, columns=["User", "Action", "Details", "Timestamp"])
        st.dataframe(log_df, use_container_width=True, hide_index=True)
        
        # Export audit log
        csv = log_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Audit Log",
            data=csv,
            file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("📌 No audit logs found.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# SETTINGS (Admin Only)
# ============================================================
if menu == "Settings":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚙️ System Settings & Configuration")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 KPI Labels", "⚖️ KPI Weights", "⭐ Rating Rules", "🔧 System"])
    
    with tab1:
        st.markdown("### Configure KPI Names")
        k1, k2, k3, k4 = get_kpi_labels()
        
        col_kpi1, col_kpi2 = st.columns(2)
        
        with col_kpi1:
            n1 = st.text_input("KPI 1 Label", value=k1, key="kpi_label_1")
            n2 = st.text_input("KPI 2 Label", value=k2, key="kpi_label_2")
        
        with col_kpi2:
            n3 = st.text_input("KPI 3 Label", value=k3, key="kpi_label_3")
            n4 = st.text_input("KPI 4 Label", value=k4, key="kpi_label_4")
        
        if st.button("💾 Save KPI Labels", use_container_width=True, type="primary"):
            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi1'", [n1.strip() or "KPI 1"])
            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi2'", [n2.strip() or "KPI 2"])
            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi3'", [n3.strip() or "KPI 3"])
            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi4'", [n4.strip() or "KPI 4"])
            log_action(username, "UPDATE_KPI_LABELS", "Updated KPI label names")
            st.success("✅ KPI labels updated successfully!")
            st.rerun()
    
    with tab2:
        st.markdown("### Configure KPI Weights (Total must equal 100%)")
        w1, w2, w3, w4 = get_kpi_weights()
        
        col_w1, col_w2 = st.columns(2)
        
        with col_w1:
            nw1 = st.number_input(f"Weight for {kpi1_lbl}", 0, 100, w1, key="weight_1")
            nw2 = st.number_input(f"Weight for {kpi2_lbl}", 0, 100, w2, key="weight_2")
        
        with col_w2:
            nw3 = st.number_input(f"Weight for {kpi3_lbl}", 0, 100, w3, key="weight_3")
            nw4 = st.number_input(f"Weight for {kpi4_lbl}", 0, 100, w4, key="weight_4")
        
        total_weight = nw1 + nw2 + nw3 + nw4
        
        if total_weight == 100:
            st.success(f"✅ Total Weight: {total_weight}% (Perfect!)")
        else:
            st.error(f"❌ Total Weight: {total_weight}% (Must be exactly 100%)")
        
        if st.button("💾 Save Weights", use_container_width=True, type="primary"):
            if total_weight == 100:
                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi1'", [nw1])
                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi2'", [nw2])
                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi3'", [nw3])
                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi4'", [nw4])
                log_action(username, "UPDATE_KPI_WEIGHTS", f"Updated weights: {nw1},{nw2},{nw3},{nw4}")
                st.success("✅ KPI weights saved successfully!")
                st.rerun()
            else:
                st.error("⚠️ Total weight must equal 100%. Please adjust values.")
    
    with tab3:
        st.markdown("### Configure Rating Thresholds")
        ex, gd, av = get_rating_rules()
        
        col_r1, col_r2, col_r3 = st.columns(3)
        
        with col_r1:
            nex = st.number_input("🌟 Excellent Minimum", 0, 100, ex, key="rating_ex")
        with col_r2:
            ngd = st.number_input("👍 Good Minimum", 0, 100, gd, key="rating_gd")
        with col_r3:
            nav = st.number_input("📊 Average Minimum", 0, 100, av, key="rating_av")
        
        st.info(f"""
        **Rating Logic Preview:**
        - Score ≥ {nex} → 🌟 Excellent
        - Score ≥ {ngd} → 👍 Good
        - Score ≥ {nav} → 📊 Average
        - Score < {nav} → ⚠️ Needs Improvement
        """)
        
        if st.button("💾 Save Rating Rules", use_container_width=True, type="primary"):
            if nex >= ngd >= nav:
                run_query("""
                    UPDATE rating_rules 
                    SET excellent_min=%s, good_min=%s, average_min=%s 
                    WHERE id=1
                """, [nex, ngd, nav])
                log_action(username, "UPDATE_RATING_RULES", f"Updated thresholds: {nex},{ngd},{nav}")
                st.success("✅ Rating rules saved successfully!")
                st.rerun()
            else:
                st.error("⚠️ Rule must satisfy: Excellent ≥ Good ≥ Average")
    
    with tab4:
        st.markdown("### System Permissions")
        
        cur_import = get_setting("allow_import", "1") == "1"
        cur_edit_del = get_setting("allow_edit_delete", "1") == "1"
        
        col_sys1, col_sys2 = st.columns(2)
        
        with col_sys1:
            allow_import = st.checkbox("📤 Allow CSV Import (Admin)", value=cur_import)
        
        with col_sys2:
            allow_edit_del = st.checkbox("✏️ Allow Edit/Delete Records", value=cur_edit_del)
        
        if st.button("💾 Save System Settings", use_container_width=True, type="primary"):
            set_setting("allow_import", "1" if allow_import else "0")
            set_setting("allow_edit_delete", "1" if allow_edit_del else "0")
            log_action(username, "UPDATE_SYSTEM_SETTINGS", 
                      f"Import:{allow_import}, Edit/Delete:{allow_edit_del}")
            st.success("✅ System settings saved!")
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 System Information")
        
        total_users = len(run_query("SELECT id FROM users", fetch=True) or [])
        total_emps = len(run_query("SELECT id FROM employees", fetch=True) or [])
        total_depts = len(run_query("SELECT id FROM departments", fetch=True) or [])
        total_entries = len(run_query("SELECT id FROM kpi_entries", fetch=True) or [])
        
        col_info1, col_info2, col_info3, col_info4 = st.columns(4)
        col_info1.metric("👥 Total Users", total_users)
        col_info2.metric("👤 Total Employees", total_emps)
        col_info3.metric("🏢 Total Departments", total_depts)
        col_info4.metric("📝 Total KPI Entries", total_entries)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="card" style="text-align:center">', unsafe_allow_html=True)
st.markdown(f"""
<div class='small'>
    <b>Yash Gallery KPI Management System v3.0</b><br>
    👤 Logged in as: <b>{full_name}</b> ({user_role.upper()}) | 🕒 Session Active<br>
    🔐 Role-Based Access • 👥 Multi-User Support • 📋 Complete Audit Trail • 📊 Real-Time Analytics<br>
    © 2024 Yash Gallery | Built with ❤️ using Streamlit + PostgreSQL (Neon Database)<br>
    🚀 Enterprise-Ready • 🔒 Secure • 📈 Scalable
</div>
""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
