import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_option_menu import option_menu
import hashlib
import secrets

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Yash Gallery – KPI System", layout="wide")

# ---------------- ENHANCED UI CSS ----------------
st.markdown("""
<style>
.block-container{padding-top:1rem}
.card{
  background:#fff;border:1px solid #e5e7eb;border-radius:16px;
  padding:14px 16px; box-shadow:0 6px 18px rgba(15,23,42,0.06);
}
.small{color:#64748b;font-size:12px}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;
  border:1px solid #e5e7eb;background:#f8fafc;font-size:12px;color:#334155}
.badge-success{background:#dcfce7;color:#166534;border-color:#86efac}
.badge-danger{background:#fee2e2;color:#991b1b;border-color:#fca5a5}
.badge-warning{background:#fef3c7;color:#92400e;border-color:#fcd34d}
.badge-info{background:#dbeafe;color:#1e40af;border-color:#93c5fd}
.hline{height:1px;background:#e5e7eb;margin:10px 0}
[data-testid="stSidebar"]{width:300px}
[data-testid="stSidebar"] > div:first-child{width:300px}
.login-container{
  max-width: 400px;
  margin: 100px auto;
  padding: 30px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.1);
}
.role-badge-admin{background:#dc2626;color:white;padding:4px 12px;border-radius:12px;font-weight:bold}
.role-badge-manager{background:#2563eb;color:white;padding:4px 12px;border-radius:12px;font-weight:bold}
.role-badge-employee{background:#16a34a;color:white;padding:4px 12px;border-radius:12px;font-weight:bold}
</style>
""", unsafe_allow_html=True)

# ---------------- DB CONNECTION ----------------
@st.cache_resource
def init_connection():
    """Initialize database connection"""
    try:
        return psycopg2.connect(
            st.secrets["NEON_DATABASE_URL"],
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        st.stop()

def get_conn():
    """Get or create database connection"""
    if "db_conn" not in st.session_state or st.session_state.db_conn.closed:
        st.session_state.db_conn = init_connection()
    return st.session_state.db_conn

def run_query(query, params=None, fetch=False):
    """Execute a single query safely"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or [])
            if fetch:
                return cur.fetchall()
            conn.commit()
            return None
    except psycopg2.OperationalError:
        # Reconnect on connection issues
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

# ---------------- PASSWORD HASHING ----------------
def hash_password(password: str, salt: str = None) -> tuple:
    """Hash password with salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify password"""
    test_hash, _ = hash_password(password, salt)
    return test_hash == hashed

# ---------------- DATABASE INITIALIZATION ----------------
def initialize_database():
    """Create all required tables and default data"""
    
    # Drop and recreate tables to fix schema issues
    init_queries = [
        # Drop existing tables if schema mismatch
        """
        DROP TABLE IF EXISTS audit_log CASCADE;
        DROP TABLE IF EXISTS kpi_entries CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        DROP TABLE IF EXISTS employees CASCADE;
        DROP TABLE IF EXISTS departments CASCADE;
        DROP TABLE IF EXISTS app_settings CASCADE;
        DROP TABLE IF EXISTS kpi_master CASCADE;
        DROP TABLE IF EXISTS kpi_weights CASCADE;
        DROP TABLE IF EXISTS rating_rules CASCADE;
        """,
        
        # Create departments table
        """
        CREATE TABLE IF NOT EXISTS departments (
            id SERIAL PRIMARY KEY,
            department_name TEXT UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Create employees table
        """
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            employee_name TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Create users table
        """
        CREATE TABLE IF NOT EXISTS users (
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
        """,
        
        # Create kpi_entries table
        """
        CREATE TABLE IF NOT EXISTS kpi_entries (
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
        """,
        
        # Create audit_log table
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Create app_settings table
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """,
        
        # Create kpi_master table
        """
        CREATE TABLE IF NOT EXISTS kpi_master (
            kpi_key TEXT PRIMARY KEY,
            kpi_label TEXT NOT NULL
        )
        """,
        
        # Create kpi_weights table
        """
        CREATE TABLE IF NOT EXISTS kpi_weights (
            kpi_key TEXT PRIMARY KEY,
            weight INTEGER NOT NULL
        )
        """,
        
        # Create rating_rules table
        """
        CREATE TABLE IF NOT EXISTS rating_rules (
            id INTEGER PRIMARY KEY DEFAULT 1,
            excellent_min INTEGER NOT NULL,
            good_min INTEGER NOT NULL,
            average_min INTEGER NOT NULL
        )
        """
    ]
    
    # Execute all initialization queries
    for query in init_queries:
        run_query(query)
    
    # Insert default data
    default_data = [
        # App settings
        ("INSERT INTO app_settings(key, value) VALUES (%s,%s) ON CONFLICT (key) DO NOTHING", 
         [("allow_import", "1"), ("allow_edit_delete", "1"), ("session_timeout", "30")]),
        
        # KPI master
        ("INSERT INTO kpi_master(kpi_key, kpi_label) VALUES (%s,%s) ON CONFLICT (kpi_key) DO NOTHING",
         [("kpi1","Quality"), ("kpi2","Productivity"), ("kpi3","Attendance"), ("kpi4","Behavior")]),
        
        # KPI weights
        ("INSERT INTO kpi_weights(kpi_key, weight) VALUES (%s,%s) ON CONFLICT (kpi_key) DO NOTHING",
         [("kpi1",25), ("kpi2",25), ("kpi3",25), ("kpi4",25)]),
        
        # Rating rules
        ("INSERT INTO rating_rules(id, excellent_min, good_min, average_min) VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
         [(1, 80, 60, 40)])
    ]
    
    for query, data in default_data:
        run_many(query, data)
    
    # Create default admin user
    admin_check = run_query("SELECT id FROM users WHERE username='admin'", fetch=True)
    if not admin_check:
        hashed, salt = hash_password("admin123")
        run_query("""
            INSERT INTO users (username, password_hash, password_salt, full_name, role, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ["admin", hashed, salt, "System Administrator", "admin", True, "system"])
    
    # Create sample departments
    sample_depts = ["Fabric", "Dyeing", "Quality Control", "Production", "Finishing"]
    for dept in sample_depts:
        run_query("""
            INSERT INTO departments (department_name, is_active)
            VALUES (%s, %s)
            ON CONFLICT (department_name) DO NOTHING
        """, [dept, True])
    
    return True

# Initialize database on first run
if "db_initialized" not in st.session_state:
    with st.spinner("Initializing database..."):
        if initialize_database():
            st.session_state.db_initialized = True

# ---------------- AUDIT LOG ----------------
def log_action(username: str, action: str, details: str = ""):
    """Log user actions"""
    run_query("""
        INSERT INTO audit_log (username, action, details, timestamp)
        VALUES (%s, %s, %s, %s)
    """, [username, action, details, datetime.now()])

# ---------------- HELPER FUNCTIONS ----------------
def get_setting(key, default=""):
    r = run_query("SELECT value FROM app_settings WHERE key=%s", [key], fetch=True)
    return r[0][0] if r else default

def set_setting(key, value):
    run_query("""
        INSERT INTO app_settings(key, value)
        VALUES (%s,%s)
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
    """, [key, value])

def get_kpi_labels():
    rows = run_query("SELECT kpi_key, kpi_label FROM kpi_master ORDER BY kpi_key", fetch=True) or []
    d = {k:v for k,v in rows}
    return d.get("kpi1","KPI 1"), d.get("kpi2","KPI 2"), d.get("kpi3","KPI 3"), d.get("kpi4","KPI 4")

def get_kpi_weights():
    rows = run_query("SELECT kpi_key, weight FROM kpi_weights ORDER BY kpi_key", fetch=True) or []
    d = {k:int(w) for k,w in rows}
    return d.get("kpi1",25), d.get("kpi2",25), d.get("kpi3",25), d.get("kpi4",25)

def get_rating_rules():
    r = run_query("SELECT excellent_min, good_min, average_min FROM rating_rules WHERE id=1", fetch=True)
    if not r:
        return 80, 60, 40
    return int(r[0][0]), int(r[0][1]), int(r[0][2])

def calc_weighted_score(k1,k2,k3,k4):
    w1,w2,w3,w4 = get_kpi_weights()
    score = (k1*w1 + k2*w2 + k3*w3 + k4*w4) / 100.0
    return round(score, 2)

def calc_rating(score_0_100: float):
    ex, gd, av = get_rating_rules()
    if score_0_100 >= ex: return "Excellent"
    if score_0_100 >= gd: return "Good"
    if score_0_100 >= av: return "Average"
    return "Needs Improvement"

def get_active_employees():
    rows = run_query("SELECT employee_name, department FROM employees WHERE is_active=TRUE ORDER BY employee_name", fetch=True) or []
    return rows

def get_all_employees():
    rows = run_query("SELECT id, employee_name, department, is_active, created_at FROM employees ORDER BY employee_name", fetch=True) or []
    return rows

def get_active_departments():
    rows = run_query("SELECT department_name FROM departments WHERE is_active=TRUE ORDER BY department_name", fetch=True) or []
    return [r[0] for r in rows]

def get_all_departments():
    rows = run_query("SELECT id, department_name, is_active, created_at FROM departments ORDER BY department_name", fetch=True) or []
    return rows

# ---------------- AUTHENTICATION ----------------
def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user"""
    user = run_query("""
        SELECT id, username, password_hash, password_salt, full_name, role, 
               employee_name, department, is_active 
        FROM users 
        WHERE username=%s
    """, [username], fetch=True)
    
    if not user:
        return {"success": False, "message": "Invalid username or password"}
    
    user_data = user[0]
    user_id, uname, pwd_hash, pwd_salt, full_name, role, emp_name, dept, is_active = user_data
    
    if not is_active:
        return {"success": False, "message": "Account is inactive. Contact administrator."}
    
    if not verify_password(password, pwd_hash, pwd_salt):
        return {"success": False, "message": "Invalid username or password"}
    
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
    """Check if user has required permission"""
    if "user" not in st.session_state:
        return False
    user_role = st.session_state["user"]["role"]
    role_levels = {"admin": 3, "manager": 2, "employee": 1}
    return role_levels.get(user_role, 0) >= role_levels.get(required_role, 0)

def require_auth(required_role: str = "employee"):
    """Require authentication"""
    if "user" not in st.session_state:
        return False
    if not check_permission(required_role):
        st.error(f"⛔ Access Denied: {required_role.upper()} role required")
        return False
    return True

# ---------------- LOGIN PAGE ----------------
def show_login_page():
    """Display login page"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown("## 🔐 Yash Gallery KPI System")
    st.markdown("### Login to Continue")
    st.markdown("---")
    
    with st.form("login_form"):
        username = st.text_input("👤 Username", placeholder="Enter your username")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("🚀 Login", use_container_width=True)
        with col2:
            if st.form_submit_button("❌ Clear", use_container_width=True):
                st.rerun()
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                result = authenticate_user(username, password)
                if result["success"]:
                    st.session_state["user"] = result
                    st.session_state["logged_in"] = True
                    st.success(f"Welcome, {result['full_name']}!")
                    st.rerun()
                else:
                    st.error(result["message"])
    
    st.markdown("---")
    st.markdown("""
    <div class='small' style='text-align:center'>
        <b>Default Credentials:</b><br>
        Username: <code>admin</code> | Password: <code>admin123</code>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- SESSION MANAGEMENT ----------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "user" not in st.session_state:
    st.session_state["user"] = None

# Show login if not authenticated
if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()

# Get current user
current_user = st.session_state["user"]
username = current_user["username"]
full_name = current_user["full_name"]
user_role = current_user["role"]
user_employee_name = current_user.get("employee_name")
user_department = current_user.get("department")

# ---------------- SIDEBAR ----------------
st.sidebar.markdown("### 👤 User Profile")
st.sidebar.markdown(f"**Name:** {full_name}")
st.sidebar.markdown(f"**Role:** <span class='role-badge-{user_role}'>{user_role.upper()}</span>", unsafe_allow_html=True)
if user_employee_name:
    st.sidebar.markdown(f"**Employee:** {user_employee_name}")
if user_department:
    st.sidebar.markdown(f"**Department:** {user_department}")

if st.sidebar.button("🚪 Logout", use_container_width=True):
    log_action(username, "LOGOUT", "User logged out")
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("## 🔎 Filters")

# Role-based filtering
if user_role == "employee":
    dept_filter = user_department or "All"
    emp_filter = user_employee_name or "All"
    st.sidebar.info("Viewing your data only")
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
            st.sidebar.info(f"Viewing: {user_department}")
        else:
            dept_filter = "All"
    else:
        dept_filter = st.sidebar.selectbox("Department", ["All"] + dept_list)
    
    emp_q = "SELECT DISTINCT employee_name FROM kpi_entries WHERE employee_name IS NOT NULL AND employee_name<>''"
    emp_p = []
    if dept_filter != "All":
        emp_q += " AND department=%s"
        emp_p.append(dept_filter)
    emp_q += " ORDER BY employee_name"
    
    emp_rows = run_query(emp_q, emp_p, fetch=True) or []
    emp_list = [r[0] for r in emp_rows]
    emp_filter = st.sidebar.selectbox("Employee", ["All"] + emp_list)

date_range = st.sidebar.date_input("Date Range", value=[])
rating_filter = st.sidebar.selectbox("Rating", ["All", "Excellent", "Good", "Average", "Needs Improvement"])

# ---------------- HEADER ----------------
st.markdown('<div class="card">', unsafe_allow_html=True)
c1, c2 = st.columns([3,2])
with c1:
    st.title("📊 Yash Gallery – KPI System")
    st.caption("Role-Based Access • Multi-User Support • Audit Trail")
with c2:
    st.markdown(
        f"<span class='badge'>PostgreSQL</span> "
        f"<span class='badge badge-info'>{username}</span> "
        f"<span class='role-badge-{user_role}'>{user_role.upper()}</span>",
        unsafe_allow_html=True
    )
st.markdown("</div>", unsafe_allow_html=True)

# Dynamic menu based on role
if user_role == "admin":
    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employee Mgmt", 
                    "Department Mgmt", "User Mgmt", "Audit Log", "Settings"]
    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people", 
                  "building", "person-badge", "clipboard-data", "gear"]
elif user_role == "manager":
    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employee Mgmt"]
    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people"]
else:
    menu_options = ["Dashboard", "My Records"]
    menu_icons = ["speedometer2", "table"]

menu = option_menu(
    None, menu_options, icons=menu_icons, orientation="horizontal",
    styles={
        "container": {"padding": "0.2rem 0", "background-color": "#ffffff", 
                     "border": "1px solid #e5e7eb", "border-radius": "14px"},
        "nav-link": {"font-size": "13px", "margin": "0px", "padding": "8px 10px"},
        "nav-link-selected": {"background-color": "#2563EB", "color": "white"},
    },
)

# ---------------- QUERY KPI ENTRIES ----------------
q = """
SELECT id, employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at, 
       COALESCE(created_by, 'system') as created_by
FROM kpi_entries WHERE 1=1
"""
p = []

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
df = pd.DataFrame(rows, columns=["ID","Employee","Department","KPI1","KPI2","KPI3","KPI4",
                                 "Weighted Score","Rating","Created At","Created By"])

kpi1_lbl, kpi2_lbl, kpi3_lbl, kpi4_lbl = get_kpi_labels()

# ============================================================
# DASHBOARD
# ============================================================
if menu == "Dashboard":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📌 KPI Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_records = len(df)
    avg_score = round(float(df["Weighted Score"].mean()), 2) if len(df) > 0 else 0
    best_score = round(float(df["Weighted Score"].max()), 2) if len(df) > 0 else 0
    
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
    
    col1.metric("📝 Records", total_records)
    col2.metric("⭐ Avg Score", avg_score)
    col3.metric("🏆 Best Score", best_score)
    col4.metric("👥 Employees", active_emp)
    col5.metric("🏢 Departments", active_dept)
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")
    
    # Charts
    if len(df) > 0:
        col_a, col_b = st.columns([1.5, 1])
        
        with col_a:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📊 Rating Distribution")
            rating_counts = df["Rating"].value_counts().reset_index()
            rating_counts.columns = ["Rating", "Count"]
            colors = {"Excellent": "#10b981", "Good": "#3b82f6", 
                     "Average": "#f59e0b", "Needs Improvement": "#ef4444"}
            fig = px.pie(rating_counts, values="Count", names="Rating", 
                        color="Rating", color_discrete_map=colors, hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col_b:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🎯 Performance")
            total = len(df)
            for rating, color, emoji in [("Excellent", "#dcfce7", "🌟"), 
                                         ("Good", "#dbeafe", "👍"),
                                         ("Average", "#fef3c7", "📊"), 
                                         ("Needs Improvement", "#fee2e2", "⚠️")]:
                count = len(df[df["Rating"] == rating])
                pct = round(count/total*100, 1) if total > 0 else 0
                st.markdown(f"""
                <div style='padding:10px;background:{color};border-radius:8px;margin:8px 0'>
                    <b>{emoji} {rating}:</b> {count} ({pct}%)
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        if user_role != "employee":
            st.write("")
            col_c, col_d = st.columns(2)
            
            with col_c:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("🏭 Department Performance")
                dept_avg = df.groupby("Department")["Weighted Score"].mean().reset_index()
                dept_avg = dept_avg.sort_values("Weighted Score", ascending=False)
                fig = px.bar(dept_avg, x="Department", y="Weighted Score", 
                            color="Weighted Score", color_continuous_scale="Viridis")
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col_d:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("👤 Top Performers")
                top_emp = df.groupby("Employee")["Weighted Score"].mean().reset_index()
                top_emp = top_emp.sort_values("Weighted Score", ascending=False).head(10)
                fig = px.bar(top_emp, x="Weighted Score", y="Employee", orientation='h',
                            color="Weighted Score", color_continuous_scale="RdYlGn")
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# ENTRY
# ============================================================
if menu == "Entry":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("➕ Add KPI Entry")
    
    with st.form("add_form", clear_on_submit=True):
        active_employees = get_active_employees()
        
        if user_role == "manager":
            active_employees = [e for e in active_employees if e[1] == user_department]
        
        emp_list = [e[0] for e in active_employees]
        
        emp = st.selectbox("Select Employee", [""] + emp_list)
        if emp:
            emp_dept = [e[1] for e in active_employees if e[0] == emp][0]
            st.info(f"Department: **{emp_dept}**")
            dept = emp_dept
        else:
            dept = user_department if user_role == "manager" else ""
        
        st.markdown("### KPI Scores (1-100)")
        c1,c2,c3,c4 = st.columns(4)
        v1 = c1.number_input(kpi1_lbl, 1,100,50,1)
        v2 = c2.number_input(kpi2_lbl, 1,100,50,1)
        v3 = c3.number_input(kpi3_lbl, 1,100,50,1)
        v4 = c4.number_input(kpi4_lbl, 1,100,50,1)
        
        ok = st.form_submit_button("✅ Save Entry", use_container_width=True)
    
    if ok:
        if not emp or not dept:
            st.error("Please select an employee")
        else:
            score = calc_weighted_score(v1,v2,v3,v4)
            rating = calc_rating(score)
            now = datetime.now()
            month = now.strftime("%Y-%m")
            
            run_query("""
                INSERT INTO kpi_entries (employee_name, department, kpi1,kpi2,kpi3,kpi4, 
                                        total_score, rating, created_at, entry_month, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [emp, dept, v1,v2,v3,v4, score, rating, now, month, username])
            
            log_action(username, "CREATE_KPI", f"Created entry for {emp} - Score: {score}")
            st.success(f"✅ Saved! Score: {score} | Rating: {rating}")
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# RECORDS / MY RECORDS
# ============================================================
if menu in ["Records", "My Records"]:
    if menu == "Records" and not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 KPI Records")
    
    if len(df) > 0:
        show_df = df.drop(columns=["ID"]).rename(columns={
            "KPI1":kpi1_lbl, "KPI2":kpi2_lbl, "KPI3":kpi3_lbl, "KPI4":kpi4_lbl
        })
        st.dataframe(show_df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode()
        st.download_button("📥 Download CSV", csv, "kpi_records.csv", "text/csv")
    else:
        st.info("No records found")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# OTHER MENUS (Reports, Employee Mgmt, etc.)
# ============================================================
if menu == "Reports":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📄 Reports")
    
    if len(df) > 0:
        tmp = df.copy()
        tmp["Month"] = pd.to_datetime(tmp["Created At"]).dt.to_period("M").astype(str)
        months = sorted(tmp["Month"].unique())[::-1]
        
        report_type = st.selectbox("Type", ["Employee Wise", "Department Wise"])
        sel_month = st.selectbox("Month", months)
        
        mdf = tmp[tmp["Month"] == sel_month]
        
        if report_type == "Employee Wise":
            rep = mdf.groupby("Employee")["Weighted Score"].mean().reset_index()
            rep = rep.sort_values("Weighted Score", ascending=False)
            fig = px.bar(rep, x="Employee", y="Weighted Score")
        else:
            rep = mdf.groupby("Department")["Weighted Score"].mean().reset_index()
            rep = rep.sort_values("Weighted Score", ascending=False)
            fig = px.bar(rep, x="Department", y="Weighted Score")
        
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(rep, use_container_width=True)
        
        csv = rep.to_csv(index=False).encode()
        st.download_button("📥 Download", csv, f"report_{sel_month}.csv")
    else:
        st.info("No data")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Employee Management, User Management, etc. - Similar structure
if menu == "Employee Mgmt":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👥 Employee Management")
    
    tab1, tab2 = st.tabs(["➕ Add", "📋 Manage"])
    
    with tab1:
        with st.form("add_emp"):
            name = st.text_input("Name")
            if user_role == "admin":
                dept = st.selectbox("Department", get_active_departments())
            else:
                dept = user_department
                st.info(f"Department: {dept}")
            active = st.checkbox("Active", True)
            
            if st.form_submit_button("Add"):
                if name:
                    run_query("INSERT INTO employees(employee_name, department, is_active) VALUES(%s,%s,%s)",
                             [name, dept, active])
                    log_action(username, "ADD_EMPLOYEE", f"Added {name}")
                    st.success("Added!")
                    st.rerun()
    
    with tab2:
        emps = get_all_employees()
        if user_role == "manager":
            emps = [e for e in emps if e[2] == user_department]
        
        if emps:
            emp_df = pd.DataFrame(emps, columns=["ID","Name","Dept","Active","Created"])
            st.dataframe(emp_df[["Name","Dept","Active"]], use_container_width=True)
        else:
            st.info("No employees")
    
    st.markdown("</div>", unsafe_allow_html=True)

if menu == "User Mgmt":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👨‍💼 User Management")
    
    tab1, tab2 = st.tabs(["➕ Create", "📋 Manage"])
    
    with tab1:
        with st.form("add_user"):
            col1, col2 = st.columns(2)
            
            uname = col1.text_input("Username")
            pwd = col1.text_input("Password", type="password")
            pwd2 = col1.text_input("Confirm Password", type="password")
            
            fname = col2.text_input("Full Name")
            role = col2.selectbox("Role", ["employee", "manager", "admin"])
            
            if role in ["employee", "manager"]:
                emp = st.selectbox("Link Employee", [""] + [e[0] for e in get_active_employees()])
            else:
                emp = ""
            
            if st.form_submit_button("Create User"):
                if not uname or not pwd or not fname:
                    st.error("Fill all fields")
                elif len(pwd) < 6:
                    st.error("Password min 6 chars")
                elif pwd != pwd2:
                    st.error("Passwords don't match")
                else:
                    hashed, salt = hash_password(pwd)
                    emp_dept = ""
                    if emp:
                        emp_data = [e for e in get_active_employees() if e[0] == emp]
                        emp_dept = emp_data[0][1] if emp_data else ""
                    
                    run_query("""
                        INSERT INTO users(username, password_hash, password_salt, full_name, role,
                                        employee_name, department, is_active, created_by)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, [uname, hashed, salt, fname, role, emp or None, emp_dept or None, True, username])
                    
                    log_action(username, "CREATE_USER", f"Created user: {uname}")
                    st.success("User created!")
                    st.rerun()
    
    with tab2:
        users = run_query("""
            SELECT username, full_name, role, employee_name, is_active 
            FROM users WHERE username != 'admin' ORDER BY created_at DESC
        """, fetch=True) or []
        
        if users:
            user_df = pd.DataFrame(users, columns=["Username","Name","Role","Employee","Active"])
            st.dataframe(user_df, use_container_width=True)
        else:
            st.info("No users")
    
    st.markdown("</div>", unsafe_allow_html=True)

if menu == "Audit Log":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 Audit Trail")
    
    logs = run_query("SELECT username, action, details, timestamp FROM audit_log ORDER BY timestamp DESC LIMIT 100", 
                    fetch=True) or []
    
    if logs:
        log_df = pd.DataFrame(logs, columns=["User","Action","Details","Time"])
        st.dataframe(log_df, use_container_width=True)
    else:
        st.info("No logs")
    
    st.markdown("</div>", unsafe_allow_html=True)

if menu == "Settings":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚙️ System Settings")
    
    tab1, tab2, tab3 = st.tabs(["KPI Labels", "KPI Weights", "Rating Rules"])
    
    with tab1:
        k1,k2,k3,k4 = get_kpi_labels()
        n1 = st.text_input("KPI 1 Label", k1)
        n2 = st.text_input("KPI 2 Label", k2)
        n3 = st.text_input("KPI 3 Label", k3)
        n4 = st.text_input("KPI 4 Label", k4)
        
        if st.button("Save Labels"):
            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi1'", [n1])
            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi2'", [n2])
            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi3'", [n3])
            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi4'", [n4])
            log_action(username, "UPDATE_LABELS", "Updated KPI labels")
            st.success("Saved!")
            st.rerun()
    
    with tab2:
        w1,w2,w3,w4 = get_kpi_weights()
        nw1 = st.number_input("Weight 1", 0, 100, w1)
        nw2 = st.number_input("Weight 2", 0, 100, w2)
        nw3 = st.number_input("Weight 3", 0, 100, w3)
        nw4 = st.number_input("Weight 4", 0, 100, w4)
        
        total = nw1+nw2+nw3+nw4
        st.info(f"Total: {total}% (must be 100)")
        
        if st.button("Save Weights"):
            if total == 100:
                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi1'", [nw1])
                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi2'", [nw2])
                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi3'", [nw3])
                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi4'", [nw4])
                log_action(username, "UPDATE_WEIGHTS", f"Updated weights: {nw1},{nw2},{nw3},{nw4}")
                st.success("Saved!")
                st.rerun()
            else:
                st.error("Total must be 100%")
    
    with tab3:
        ex, gd, av = get_rating_rules()
        nex = st.number_input("Excellent Min", 0, 100, ex)
        ngd = st.number_input("Good Min", 0, 100, gd)
        nav = st.number_input("Average Min", 0, 100, av)
        
        if st.button("Save Rules"):
            if nex >= ngd >= nav:
                run_query("UPDATE rating_rules SET excellent_min=%s, good_min=%s, average_min=%s WHERE id=1",
                         [nex, ngd, nav])
                log_action(username, "UPDATE_RATINGS", f"Updated rules: {nex},{ngd},{nav}")
                st.success("Saved!")
                st.rerun()
            else:
                st.error("Must be: Excellent >= Good >= Average")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="card" style="text-align:center">', unsafe_allow_html=True)
st.markdown(f"""
<div class='small'>
    <b>Yash Gallery KPI System v3.0</b> | Logged in: <b>{full_name}</b> ({user_role.upper()})<br>
    Role-Based Access • Multi-User • Audit Trail • Secure Authentication<br>
    © 2024 | Built with Streamlit + PostgreSQL
</div>
""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
