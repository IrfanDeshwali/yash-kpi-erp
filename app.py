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
.metric-card{
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
}
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
def get_conn():
    url = st.secrets["NEON_DATABASE_URL"]
    conn = st.session_state.get("db_conn")
    if conn is None or getattr(conn, "closed", 1) != 0:
        conn = psycopg2.connect(
            url,
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
        conn.autocommit = True
        st.session_state["db_conn"] = conn
    return conn

def run(query, params=None, fetch=False, many=False, data=None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if many and data is not None:
                cur.executemany(query, data)
                return None
            cur.execute(query, params or [])
            return cur.fetchall() if fetch else None
    except psycopg2.InterfaceError:
        st.session_state["db_conn"] = None
        conn = get_conn()
        with conn.cursor() as cur:
            if many and data is not None:
                cur.executemany(query, data)
                return None
            cur.execute(query, params or [])
            return cur.fetchall() if fetch else None

# ---------------- PASSWORD HASHING ----------------
def hash_password(password: str, salt: str = None) -> tuple:
    """Hash password with salt. Returns (hashed_password, salt)"""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify password against hash"""
    test_hash, _ = hash_password(password, salt)
    return test_hash == hashed

# ---------------- CREATE ENHANCED TABLES ----------------
# Users Table with Authentication
run("""
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
""")

# Employees Table
run("""
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    employee_name TEXT UNIQUE NOT NULL,
    department TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Departments Table
run("""
CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    department_name TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# KPI Entries
run("""
CREATE TABLE IF NOT EXISTS kpi_entries (
    id SERIAL PRIMARY KEY,
    employee_name TEXT NOT NULL,
    department TEXT NOT NULL,
    kpi1 INTEGER, kpi2 INTEGER, kpi3 INTEGER, kpi4 INTEGER,
    total_score DOUBLE PRECISION,
    rating TEXT,
    created_at TIMESTAMP,
    entry_month TEXT,
    created_by TEXT,
    updated_by TEXT,
    updated_at TIMESTAMP
)
""")

# Audit Log Table
run("""
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# App Settings
run("""
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
""")

# KPI Master
run("""
CREATE TABLE IF NOT EXISTS kpi_master (
    kpi_key TEXT PRIMARY KEY,
    kpi_label TEXT NOT NULL
)
""")

# KPI Weights
run("""
CREATE TABLE IF NOT EXISTS kpi_weights (
    kpi_key TEXT PRIMARY KEY,
    weight INTEGER NOT NULL
)
""")

# Rating Rules
run("""
CREATE TABLE IF NOT EXISTS rating_rules (
    id INTEGER PRIMARY KEY DEFAULT 1,
    excellent_min INTEGER NOT NULL,
    good_min INTEGER NOT NULL,
    average_min INTEGER NOT NULL
)
""")

# ---------------- DEFAULT DATA INITIALIZATION ----------------
def set_default_if_missing(key, value):
    run("""
    INSERT INTO app_settings(key, value)
    VALUES (%s,%s)
    ON CONFLICT (key) DO NOTHING
    """, [key, value])

set_default_if_missing("allow_import", "1")
set_default_if_missing("allow_edit_delete", "1")
set_default_if_missing("session_timeout", "30")

for k, lbl in [("kpi1","KPI 1"), ("kpi2","KPI 2"), ("kpi3","KPI 3"), ("kpi4","KPI 4")]:
    run("""
    INSERT INTO kpi_master(kpi_key, kpi_label)
    VALUES (%s,%s)
    ON CONFLICT (kpi_key) DO NOTHING
    """, [k, lbl])

for k, w in [("kpi1",25), ("kpi2",25), ("kpi3",25), ("kpi4",25)]:
    run("""
    INSERT INTO kpi_weights(kpi_key, weight)
    VALUES (%s,%s)
    ON CONFLICT (kpi_key) DO NOTHING
    """, [k, w])

run("""
INSERT INTO rating_rules(id, excellent_min, good_min, average_min)
VALUES (1, 80, 60, 40)
ON CONFLICT (id) DO NOTHING
""")

# Create default admin user if not exists
admin_check = run("SELECT id FROM users WHERE username='admin'", fetch=True)
if not admin_check:
    hashed, salt = hash_password("admin123")
    run("""
        INSERT INTO users (username, password_hash, password_salt, full_name, role, is_active, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, ["admin", hashed, salt, "System Administrator", "admin", True, "system"])

# ---------------- AUDIT LOG FUNCTION ----------------
def log_action(username: str, action: str, details: str = ""):
    """Log user actions for audit trail"""
    run("""
        INSERT INTO audit_log (username, action, details, timestamp)
        VALUES (%s, %s, %s, %s)
    """, [username, action, details, datetime.now()])

# ---------------- HELPER FUNCTIONS ----------------
def get_setting(key, default=""):
    r = run("SELECT value FROM app_settings WHERE key=%s", [key], fetch=True)
    return r[0][0] if r else default

def set_setting(key, value):
    run("""
    INSERT INTO app_settings(key, value)
    VALUES (%s,%s)
    ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
    """, [key, value])

def get_kpi_labels():
    rows = run("SELECT kpi_key, kpi_label FROM kpi_master ORDER BY kpi_key", fetch=True) or []
    d = {k:v for k,v in rows}
    return d.get("kpi1","KPI 1"), d.get("kpi2","KPI 2"), d.get("kpi3","KPI 3"), d.get("kpi4","KPI 4")

def get_kpi_weights():
    rows = run("SELECT kpi_key, weight FROM kpi_weights ORDER BY kpi_key", fetch=True) or []
    d = {k:int(w) for k,w in rows}
    return d.get("kpi1",25), d.get("kpi2",25), d.get("kpi3",25), d.get("kpi4",25)

def get_rating_rules():
    r = run("SELECT excellent_min, good_min, average_min FROM rating_rules WHERE id=1", fetch=True)
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
    rows = run("SELECT employee_name, department FROM employees WHERE is_active=TRUE ORDER BY employee_name", fetch=True) or []
    return rows

def get_all_employees():
    rows = run("SELECT id, employee_name, department, is_active, created_at FROM employees ORDER BY employee_name", fetch=True) or []
    return rows

def get_active_departments():
    rows = run("SELECT department_name FROM departments WHERE is_active=TRUE ORDER BY department_name", fetch=True) or []
    return [r[0] for r in rows]

def get_all_departments():
    rows = run("SELECT id, department_name, is_active, created_at FROM departments ORDER BY department_name", fetch=True) or []
    return rows

def get_user_info(username: str):
    """Get user information"""
    r = run("SELECT id, username, full_name, role, employee_name, department, is_active FROM users WHERE username=%s", 
            [username], fetch=True)
    return r[0] if r else None

# ---------------- AUTHENTICATION FUNCTIONS ----------------
def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user and return user info"""
    user = run("""
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
    run("UPDATE users SET last_login=%s WHERE id=%s", [datetime.now(), user_id])
    
    # Log successful login
    log_action(username, "LOGIN", f"User logged in successfully")
    
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
    
    # Role hierarchy: admin > manager > employee
    role_levels = {"admin": 3, "manager": 2, "employee": 1}
    
    return role_levels.get(user_role, 0) >= role_levels.get(required_role, 0)

def require_auth(required_role: str = "employee"):
    """Decorator-like function to require authentication"""
    if "user" not in st.session_state:
        return False
    if not check_permission(required_role):
        st.error(f"⛔ Access Denied: This feature requires {required_role.upper()} role or higher")
        return False
    return True

# ---------------- LOGIN PAGE ----------------
def show_login_page():
    """Display login page"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown("## 🔐 Login to KPI System")
    st.markdown("---")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
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
        <b>Default Login Credentials:</b><br>
        Username: <code>admin</code> | Password: <code>admin123</code>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- SESSION MANAGEMENT ----------------
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

# ---------------- SIDEBAR (After Login) ----------------
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

# ---------------- FILTERS ----------------
st.sidebar.markdown("## 🔎 Filters")

# Role-based filtering
if user_role == "employee":
    # Employees can only see their own data
    dept_filter = user_department or "All"
    emp_filter = user_employee_name or "All"
    st.sidebar.info(f"Viewing your data only")
else:
    # Managers see their department, Admins see all
    dept_rows = run(
        "SELECT DISTINCT department FROM kpi_entries WHERE department IS NOT NULL AND department<>'' ORDER BY department",
        fetch=True
    ) or []
    dept_list = [r[0] for r in dept_rows]
    
    if user_role == "manager":
        # Managers can only see their department
        dept_list = [d for d in dept_list if d == user_department]
        if user_department and user_department in dept_list:
            dept_filter = user_department
            st.sidebar.info(f"Viewing: {user_department} department")
        else:
            dept_filter = "All"
    else:
        # Admin sees all
        dept_filter = st.sidebar.selectbox("Department", ["All"] + dept_list)
    
    emp_q = "SELECT DISTINCT employee_name FROM kpi_entries WHERE employee_name IS NOT NULL AND employee_name<>''"
    emp_p = []
    if dept_filter != "All":
        emp_q += " AND department=%s"
        emp_p.append(dept_filter)
    emp_q += " ORDER BY employee_name"
    
    emp_rows = run(emp_q, emp_p, fetch=True) or []
    emp_list = [r[0] for r in emp_rows]
    emp_filter = st.sidebar.selectbox("Employee", ["All"] + emp_list)

date_range = st.sidebar.date_input("Date Range (optional)", value=[])
search_text = st.sidebar.text_input("Search name", placeholder="e.g., Irfan") if user_role != "employee" else ""
rating_filter = st.sidebar.selectbox("Rating", ["All", "Excellent", "Good", "Average", "Needs Improvement"])

allow_import = get_setting("allow_import","1") == "1"
allow_edit_delete = get_setting("allow_edit_delete","1") == "1"

# ---------------- HEADER ----------------
st.markdown('<div class="card">', unsafe_allow_html=True)
c1, c2 = st.columns([3,2])
with c1:
    st.title("📊 Yash Gallery – KPI System")
    st.caption("Role-Based Access Control | Multi-User Support | Audit Trail")
with c2:
    st.markdown(
        f"<span class='badge'>Database: Neon</span> "
        f"<span class='badge badge-info'>User: {username}</span> "
        f"<span class='role-badge-{user_role}'>{user_role.upper()}</span>",
        unsafe_allow_html=True
    )
st.markdown("</div>", unsafe_allow_html=True)

# Dynamic menu based on role
if user_role == "admin":
    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employee Management", 
                    "Department Management", "User Management", "Audit Log", "Control Panel"]
    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people", 
                  "building", "person-badge", "clipboard-data", "shield-lock"]
elif user_role == "manager":
    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employee Management"]
    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people"]
else:  # employee
    menu_options = ["Dashboard", "My Records"]
    menu_icons = ["speedometer2", "table"]

menu = option_menu(
    None,
    menu_options,
    icons=menu_icons,
    orientation="horizontal",
    styles={
        "container": {"padding": "0.2rem 0", "background-color": "#ffffff", "border": "1px solid #e5e7eb", "border-radius": "14px"},
        "nav-link": {"font-size": "13px", "margin": "0px", "padding": "8px 10px"},
        "nav-link-selected": {"background-color": "#2563EB", "color": "white"},
    },
)

# ---------------- QUERY FILTERED KPI ENTRIES ----------------
q = """
SELECT id, employee_name, department, kpi1,kpi2,kpi3,kpi4, total_score, rating, created_at, created_by
FROM kpi_entries
WHERE 1=1
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
    q += " AND department=%s"; p.append(dept_filter)
if emp_filter != "All" and user_role != "employee":
    q += " AND employee_name=%s"; p.append(emp_filter)
if search_text and search_text.strip():
    q += " AND employee_name ILIKE %s"; p.append(f"%{search_text.strip()}%")
if rating_filter != "All":
    q += " AND rating=%s"; p.append(rating_filter)
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    s,e = date_range
    q += " AND DATE(created_at) BETWEEN %s AND %s"; p += [str(s), str(e)]
q += " ORDER BY created_at DESC"

rows = run(q, p, fetch=True) or []
df = pd.DataFrame(rows, columns=["ID","Employee","Department","KPI1","KPI2","KPI3","KPI4","Weighted Score","Rating","Created At","Created By"])

kpi1_lbl, kpi2_lbl, kpi3_lbl, kpi4_lbl = get_kpi_labels()

# ============================================================
# DASHBOARD
# ============================================================
if menu == "Dashboard":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📌 Real-Time KPI Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_records = len(df)
        st.metric("📝 Total Records", total_records)
    
    with col2:
        avg_score = round(float(df["Weighted Score"].mean()), 2) if len(df) > 0 else 0
        st.metric("⭐ Average Score", avg_score)
    
    with col3:
        best_score = round(float(df["Weighted Score"].max()), 2) if len(df) > 0 else 0
        st.metric("🏆 Best Score", best_score)
    
    with col4:
        if user_role == "admin":
            active_employees = len(run("SELECT id FROM employees WHERE is_active=TRUE", fetch=True) or [])
        elif user_role == "manager":
            active_employees = len(run("SELECT id FROM employees WHERE is_active=TRUE AND department=%s", 
                                      [user_department], fetch=True) or [])
        else:
            active_employees = 1
        st.metric("👥 Active Employees", active_employees)
    
    with col5:
        if user_role == "admin":
            active_depts = len(run("SELECT id FROM departments WHERE is_active=TRUE", fetch=True) or [])
        else:
            active_depts = 1
        st.metric("🏢 Departments", active_depts)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.write("")
    
    # Rating Distribution
    col_a, col_b = st.columns([1.5, 1], gap="large")
    
    with col_a:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Rating Distribution")
        if len(df) > 0:
            rating_counts = df["Rating"].value_counts().reset_index()
            rating_counts.columns = ["Rating", "Count"]
            
            colors = {
                "Excellent": "#10b981",
                "Good": "#3b82f6", 
                "Average": "#f59e0b",
                "Needs Improvement": "#ef4444"
            }
            rating_counts["Color"] = rating_counts["Rating"].map(colors)
            
            fig = px.pie(rating_counts, values="Count", names="Rating", 
                        color="Rating", color_discrete_map=colors,
                        hole=0.4)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_b:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🎯 Performance Summary")
        if len(df) > 0:
            excellent = len(df[df["Rating"] == "Excellent"])
            good = len(df[df["Rating"] == "Good"])
            average = len(df[df["Rating"] == "Average"])
            needs_imp = len(df[df["Rating"] == "Needs Improvement"])
            
            total = len(df)
            st.markdown(f"""
            <div style='padding: 10px; background: #dcfce7; border-radius: 8px; margin: 8px 0;'>
                <b>🌟 Excellent:</b> {excellent} ({round(excellent/total*100, 1)}%)
            </div>
            <div style='padding: 10px; background: #dbeafe; border-radius: 8px; margin: 8px 0;'>
                <b>👍 Good:</b> {good} ({round(good/total*100, 1)}%)
            </div>
            <div style='padding: 10px; background: #fef3c7; border-radius: 8px; margin: 8px 0;'>
                <b>📊 Average:</b> {average} ({round(average/total*100, 1)}%)
            </div>
            <div style='padding: 10px; background: #fee2e2; border-radius: 8px; margin: 8px 0;'>
                <b>⚠️ Needs Improvement:</b> {needs_imp} ({round(needs_imp/total*100, 1)}%)
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No data available")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.write("")
    
    # Department & Employee Performance (if not employee role)
    if user_role != "employee":
        col_c, col_d = st.columns([1, 1], gap="large")
        
        with col_c:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🏭 Department Performance")
            if len(df) > 0:
                dept_avg = df.groupby("Department", as_index=False)["Weighted Score"].mean()
                dept_avg = dept_avg.sort_values("Weighted Score", ascending=False)
                fig = px.bar(dept_avg, x="Department", y="Weighted Score", 
                            color="Weighted Score",
                            color_continuous_scale="Viridis")
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col_d:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("👤 Top 10 Performers")
            if len(df) > 0:
                top_emp = df.groupby("Employee", as_index=False)["Weighted Score"].mean()
                top_emp = top_emp.sort_values("Weighted Score", ascending=False).head(10)
                fig = px.bar(top_emp, x="Weighted Score", y="Employee", 
                            orientation='h',
                            color="Weighted Score",
                            color_continuous_scale="RdYlGn")
                fig.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available")
            st.markdown("</div>", unsafe_allow_html=True)
    
    st.write("")
    
    # Trend Analysis
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📈 Monthly Trend Analysis")
    if len(df) > 0:
        trend_df = df.copy()
        trend_df["Month"] = pd.to_datetime(trend_df["Created At"]).dt.to_period("M").astype(str)
        monthly_avg = trend_df.groupby("Month", as_index=False)["Weighted Score"].mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly_avg["Month"],
            y=monthly_avg["Weighted Score"],
            mode='lines+markers',
            name='Average Score',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=10)
        ))
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Average Score",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available")
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
        a1, a2 = st.columns([2,1])
        
        active_employees = get_active_employees()
        
        # Filter employees based on role
        if user_role == "manager":
            active_employees = [e for e in active_employees if e[1] == user_department]
        
        emp_list = [e[0] for e in active_employees]
        active_depts = get_active_departments()
        
        with a1:
            emp = st.selectbox("Select Employee", [""] + emp_list, help="Only active employees are shown")
            if emp:
                emp_dept = [e[1] for e in active_employees if e[0] == emp]
                if emp_dept:
                    dept = emp_dept[0]
                    st.info(f"Department: **{dept}**")
                else:
                    if user_role == "manager":
                        dept = user_department
                    else:
                        dept = st.selectbox("Department", [""] + active_depts)
            else:
                if user_role == "manager":
                    dept = user_department
                    st.info(f"Department: **{dept}**")
                else:
                    dept = st.selectbox("Department", [""] + active_depts)
        
        with a2:
            st.markdown("### KPI Scores")
            st.caption("Enter scores (1-100)")

        k1,k2,k3,k4 = st.columns(4)
        with k1: v1 = st.number_input(kpi1_lbl, 1,100,1,1)
        with k2: v2 = st.number_input(kpi2_lbl, 1,100,1,1)
        with k3: v3 = st.number_input(kpi3_lbl, 1,100,1,1)
        with k4: v4 = st.number_input(kpi4_lbl, 1,100,1,1)

        ok = st.form_submit_button("✅ Save Entry", use_container_width=True)

    if ok:
        if not emp or not dept:
            st.error("Please select Employee and Department.")
        else:
            score = calc_weighted_score(int(v1),int(v2),int(v3),int(v4))
            rating = calc_rating(score)
            now = datetime.now()
            month = now.strftime("%Y-%m")
            
            run("""
                INSERT INTO kpi_entries (employee_name, department, kpi1,kpi2,kpi3,kpi4, total_score, rating, 
                                        created_at, entry_month, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [emp, dept, int(v1),int(v2),int(v3),int(v4), float(score), rating, now, month, username])
            
            log_action(username, "CREATE_KPI_ENTRY", f"Created KPI entry for {emp} - Score: {score}")
            st.success(f"✅ Entry saved! Score: {score} | Rating: {rating}")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# RECORDS / MY RECORDS
# ============================================================
if menu in ["Records", "My Records"]:
    if menu == "Records" and not require_auth("manager"):
        st.stop()
    
    left, right = st.columns([2,1], gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📋 Records Table")
        show_df = df.copy().rename(columns={"KPI1":kpi1_lbl,"KPI2":kpi2_lbl,"KPI3":kpi3_lbl,"KPI4":kpi4_lbl})
        
        def highlight_rating(row):
            colors = {
                "Excellent": "background-color: #dcfce7",
                "Good": "background-color: #dbeafe",
                "Average": "background-color: #fef3c7",
                "Needs Improvement": "background-color: #fee2e2"
            }
            return [colors.get(row["Rating"], "")] * len(row)
        
        if len(show_df) > 0:
            display_cols = ["Employee","Department",kpi1_lbl,kpi2_lbl,kpi3_lbl,kpi4_lbl,
                          "Weighted Score","Rating","Created At"]
            if user_role == "admin":
                display_cols.append("Created By")
            styled_df = show_df[display_cols].style.apply(highlight_rating, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("No records found")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("⬇️ Export / ⬆️ Import")

        csv_data = df.drop(columns=["Created By"] if "Created By" in df.columns else []).to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv_data, "kpi_export.csv", "text/csv", use_container_width=True)

        if user_role == "admin" and allow_import:
            up = st.file_uploader("📤 Import CSV", type=["csv"])
            if st.button("Import Now", use_container_width=True):
                if up is None:
                    st.warning("Upload CSV first.")
                else:
                    imp = pd.read_csv(up)
                    required = ["Employee","Department","KPI1","KPI2","KPI3","KPI4"]
                    miss = [c for c in required if c not in imp.columns]
                    if miss:
                        st.error(f"Missing columns: {', '.join(miss)}")
                    else:
                        imp["Employee"] = imp["Employee"].astype(str).str.strip()
                        imp["Department"] = imp["Department"].astype(str).str.strip()
                        for c in ["KPI1","KPI2","KPI3","KPI4"]:
                            imp[c] = pd.to_numeric(imp[c], errors="coerce").fillna(0).astype(int)

                        data = []
                        for _, r in imp.iterrows():
                            score = calc_weighted_score(int(r["KPI1"]),int(r["KPI2"]),int(r["KPI3"]),int(r["KPI4"]))
                            rating = calc_rating(score)
                            now = datetime.now()
                            month = now.strftime("%Y-%m")
                            data.append((r["Employee"], r["Department"], int(r["KPI1"]), int(r["KPI2"]), 
                                       int(r["KPI3"]), int(r["KPI4"]), float(score), rating, now, month, username))

                        run("""
                            INSERT INTO kpi_entries (employee_name, department, kpi1,kpi2,kpi3,kpi4,total_score,rating,
                                                    created_at,entry_month,created_by)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, many=True, data=data)

                        log_action(username, "IMPORT_KPI_ENTRIES", f"Imported {len(data)} KPI entries")
                        st.success(f"✅ Imported {len(data)} rows")
                        st.rerun()

        st.markdown("<div class='small'>⚠️ Import/Edit/Delete requires appropriate privileges</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Edit/Delete (Admin and Manager only)
    if user_role in ["admin", "manager"] and allow_edit_delete:
        st.write("")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("✏️ Edit / 🗑 Delete")

        if len(df) == 0:
            st.info("No records for current filters.")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            rec_id = st.selectbox("Select Record ID", df["ID"].tolist())
            row = df[df["ID"] == rec_id].iloc[0]

            e1,e2,e3 = st.columns([1.2,1.6,1], gap="large")
            with e1:
                emp = st.text_input("Employee", value=str(row["Employee"]))
                dept = st.text_input("Department", value=str(row["Department"]))
            with e2:
                c1,c2 = st.columns(2)
                with c1:
                    k1 = st.number_input(kpi1_lbl, 1,100,int(row["KPI1"]),1, key="rk1")
                    k2 = st.number_input(kpi2_lbl, 1,100,int(row["KPI2"]),1, key="rk2")
                with c2:
                    k3 = st.number_input(kpi3_lbl, 1,100,int(row["KPI3"]),1, key="rk3")
                    k4 = st.number_input(kpi4_lbl, 1,100,int(row["KPI4"]),1, key="rk4")
            with e3:
                score = calc_weighted_score(int(k1),int(k2),int(k3),int(k4))
                rating = calc_rating(score)
                st.markdown(f"**Score:** {score}")
                st.markdown(f"**Rating:** {rating}")

                if st.button("✅ Update", use_container_width=True):
                    run("""
                        UPDATE kpi_entries SET employee_name=%s, department=%s,
                          kpi1=%s,kpi2=%s,kpi3=%s,kpi4=%s,total_score=%s,rating=%s,updated_by=%s,updated_at=%s
                        WHERE id=%s
                    """, [emp.strip(), dept.strip(), int(k1),int(k2),int(k3),int(k4), 
                         float(score), rating, username, datetime.now(), int(rec_id)])
                    log_action(username, "UPDATE_KPI_ENTRY", f"Updated KPI entry ID {rec_id} for {emp}")
                    st.success("✅ Updated successfully")
                    st.rerun()

                if st.button("🗑 Delete", use_container_width=True):
                    run("DELETE FROM kpi_entries WHERE id=%s", [int(rec_id)])
                    log_action(username, "DELETE_KPI_ENTRY", f"Deleted KPI entry ID {rec_id} for {emp}")
                    st.warning("🗑 Record deleted")
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# REPORTS
# ============================================================
if menu == "Reports":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📄 Monthly Reports")

    if len(df) == 0:
        st.info("No data for current filters.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        tmp = df.copy()
        tmp["Month"] = pd.to_datetime(tmp["Created At"]).dt.to_period("M").astype(str)
        months = sorted(tmp["Month"].unique())[::-1]

        r1, r2, r3 = st.columns([1,1,1])
        with r1:
            report_type = st.selectbox("Report Type", ["Employee Wise Avg", "Department Wise Avg", "Detailed Individual"])
        with r2:
            sel_month = st.selectbox("Month", months)
        with r3:
            chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Pie"])

        mdf = tmp[tmp["Month"] == sel_month]
        
        if report_type == "Employee Wise Avg":
            rep = mdf.groupby("Employee", as_index=False)["Weighted Score"].mean().sort_values("Weighted Score", ascending=False)
            x_col, y_col = "Employee", "Weighted Score"
        elif report_type == "Department Wise Avg":
            rep = mdf.groupby("Department", as_index=False)["Weighted Score"].mean().sort_values("Weighted Score", ascending=False)
            x_col, y_col = "Department", "Weighted Score"
        else:
            rep = mdf[["Employee", "Department", "Weighted Score", "Rating"]].copy()
            x_col, y_col = "Employee", "Weighted Score"

        if chart_type == "Bar":
            fig = px.bar(rep, x=x_col, y=y_col, color=y_col, color_continuous_scale="Viridis")
        elif chart_type == "Line":
            fig = px.line(rep, x=x_col, y=y_col, markers=True)
        else:
            fig = px.pie(rep, values=y_col, names=x_col)

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(rep, use_container_width=True, hide_index=True)

        out = rep.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Report CSV", out, f"report_{sel_month}.csv", "text/csv")
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# EMPLOYEE MANAGEMENT
# ============================================================
if menu == "Employee Management":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👥 Employee Management")
    
    tab1, tab2 = st.tabs(["➕ Add Employee", "📋 Manage Employees"])
    
    with tab1:
        st.markdown("### Add New Employee")
        with st.form("add_employee_form"):
            emp_name = st.text_input("Employee Name", placeholder="Enter full name")
            active_depts = get_active_departments()
            
            if user_role == "manager":
                emp_dept = user_department
                st.info(f"Department: **{user_department}**")
            else:
                emp_dept = st.selectbox("Department", [""] + active_depts)
            
            emp_active = st.checkbox("Active", value=True)
            
            submit = st.form_submit_button("➕ Add Employee", use_container_width=True)
            
            if submit:
                if not emp_name.strip():
                    st.error("Employee name is required")
                elif not emp_dept:
                    st.error("Department is required")
                else:
                    try:
                        run("""
                            INSERT INTO employees (employee_name, department, is_active, created_at)
                            VALUES (%s, %s, %s, %s)
                        """, [emp_name.strip(), emp_dept, emp_active, datetime.now()])
                        log_action(username, "CREATE_EMPLOYEE", f"Added employee: {emp_name} - {emp_dept}")
                        st.success(f"✅ Employee '{emp_name}' added successfully!")
                        st.rerun()
                    except Exception as e:
                        if "unique" in str(e).lower():
                            st.error(f"Employee '{emp_name}' already exists")
                        else:
                            st.error(f"Error: {str(e)}")
    
    with tab2:
        st.markdown("### Manage Existing Employees")
        all_employees = get_all_employees()
        
        # Filter for managers
        if user_role == "manager":
            all_employees = [e for e in all_employees if e[2] == user_department]
        
        if not all_employees:
            st.info("No employees found.")
        else:
            emp_df = pd.DataFrame(all_employees, columns=["ID", "Name", "Department", "Active", "Created"])
            emp_df["Status"] = emp_df["Active"].apply(lambda x: "✅ Active" if x else "❌ Inactive")
            
            st.dataframe(emp_df[["Name", "Department", "Status", "Created"]], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### Edit/Toggle Employee")
            
            emp_to_edit = st.selectbox("Select Employee", [e[1] for e in all_employees])
            
            if emp_to_edit:
                emp_data = [e for e in all_employees if e[1] == emp_to_edit][0]
                emp_id, emp_name, emp_dept, emp_active, _ = emp_data
                
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("Employee Name", value=emp_name, key="edit_name")
                    if user_role == "admin":
                        active_depts = get_active_departments()
                        new_dept = st.selectbox("Department", active_depts, 
                                               index=active_depts.index(emp_dept) if emp_dept in active_depts else 0,
                                               key="edit_dept")
                    else:
                        new_dept = emp_dept
                        st.info(f"Department: **{emp_dept}**")
                
                with col2:
                    new_active = st.checkbox("Active Status", value=emp_active, key="edit_active")
                    st.markdown(f"**Current Status:** {'✅ Active' if emp_active else '❌ Inactive'}")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💾 Update Employee", use_container_width=True):
                        run("""
                            UPDATE employees 
                            SET employee_name=%s, department=%s, is_active=%s, updated_at=%s
                            WHERE id=%s
                        """, [new_name.strip(), new_dept, new_active, datetime.now(), emp_id])
                        log_action(username, "UPDATE_EMPLOYEE", f"Updated employee: {emp_name} -> {new_name}")
                        st.success("✅ Employee updated!")
                        st.rerun()
                
                with col_b:
                    if user_role == "admin":
                        if st.button("🗑 Delete Employee", use_container_width=True):
                            entries = run("SELECT COUNT(*) FROM kpi_entries WHERE employee_name=%s", [emp_name], fetch=True)
                            if entries and entries[0][0] > 0:
                                st.error(f"⚠️ Cannot delete. {entries[0][0]} KPI entries exist.")
                            else:
                                run("DELETE FROM employees WHERE id=%s", [emp_id])
                                log_action(username, "DELETE_EMPLOYEE", f"Deleted employee: {emp_name}")
                                st.success("🗑 Employee deleted!")
                                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# DEPARTMENT MANAGEMENT
# ============================================================
if menu == "Department Management":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🏢 Department Management")
    
    tab1, tab2 = st.tabs(["➕ Add Department", "📋 Manage Departments"])
    
    with tab1:
        st.markdown("### Add New Department")
        with st.form("add_dept_form"):
            dept_name = st.text_input("Department Name", placeholder="e.g., Fabric, Dyeing, Quality Control")
            dept_active = st.checkbox("Active", value=True)
            
            submit = st.form_submit_button("➕ Add Department", use_container_width=True)
            
            if submit:
                if not dept_name.strip():
                    st.error("Department name is required")
                else:
                    try:
                        run("""
                            INSERT INTO departments (department_name, is_active, created_at)
                            VALUES (%s, %s, %s)
                        """, [dept_name.strip(), dept_active, datetime.now()])
                        log_action(username, "CREATE_DEPARTMENT", f"Added department: {dept_name}")
                        st.success(f"✅ Department '{dept_name}' added successfully!")
                        st.rerun()
                    except Exception as e:
                        if "unique" in str(e).lower():
                            st.error(f"Department '{dept_name}' already exists")
                        else:
                            st.error(f"Error: {str(e)}")
    
    with tab2:
        st.markdown("### Manage Existing Departments")
        all_depts = get_all_departments()
        
        if not all_depts:
            st.info("No departments found.")
        else:
            dept_df = pd.DataFrame(all_depts, columns=["ID", "Name", "Active", "Created"])
            dept_df["Status"] = dept_df["Active"].apply(lambda x: "✅ Active" if x else "❌ Inactive")
            
            for idx, row in dept_df.iterrows():
                emp_count = run("SELECT COUNT(*) FROM employees WHERE department=%s", [row["Name"]], fetch=True)
                dept_df.at[idx, "Employees"] = emp_count[0][0] if emp_count else 0
            
            st.dataframe(dept_df[["Name", "Status", "Employees", "Created"]], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### Edit/Toggle Department")
            
            dept_to_edit = st.selectbox("Select Department", [d[1] for d in all_depts])
            
            if dept_to_edit:
                dept_data = [d for d in all_depts if d[1] == dept_to_edit][0]
                dept_id, dept_name, dept_active, _ = dept_data
                
                col1, col2 = st.columns(2)
                with col1:
                    new_dept_name = st.text_input("Department Name", value=dept_name, key="edit_dept_name")
                
                with col2:
                    new_dept_active = st.checkbox("Active Status", value=dept_active, key="edit_dept_active")
                    st.markdown(f"**Current Status:** {'✅ Active' if dept_active else '❌ Inactive'}")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💾 Update Department", use_container_width=True):
                        run("""
                            UPDATE departments 
                            SET department_name=%s, is_active=%s
                            WHERE id=%s
                        """, [new_dept_name.strip(), new_dept_active, dept_id])
                        log_action(username, "UPDATE_DEPARTMENT", f"Updated department: {dept_name} -> {new_dept_name}")
                        st.success("✅ Department updated!")
                        st.rerun()
                
                with col_b:
                    if st.button("🗑 Delete Department", use_container_width=True):
                        emp_count = run("SELECT COUNT(*) FROM employees WHERE department=%s", [dept_name], fetch=True)
                        if emp_count and emp_count[0][0] > 0:
                            st.error(f"⚠️ Cannot delete. {emp_count[0][0]} employees exist.")
                        else:
                            run("DELETE FROM departments WHERE id=%s", [dept_id])
                            log_action(username, "DELETE_DEPARTMENT", f"Deleted department: {dept_name}")
                            st.success("🗑 Department deleted!")
                            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# USER MANAGEMENT (Admin Only)
# ============================================================
if menu == "User Management":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👨‍💼 User Management")
    
    tab1, tab2 = st.tabs(["➕ Add User", "📋 Manage Users"])
    
    with tab1:
        st.markdown("### Create New User")
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username", placeholder="e.g., john.doe")
                new_password = st.text_input("Password", type="password", placeholder="Min 6 characters")
                new_password2 = st.text_input("Confirm Password", type="password")
                new_fullname = st.text_input("Full Name", placeholder="e.g., John Doe")
            
            with col2:
                new_role = st.selectbox("Role", ["employee", "manager", "admin"])
                
                if new_role in ["employee", "manager"]:
                    active_employees = get_active_employees()
                    emp_list = [e[0] for e in active_employees]
                    new_emp_name = st.selectbox("Link to Employee", [""] + emp_list)
                    
                    if new_emp_name:
                        emp_dept = [e[1] for e in active_employees if e[0] == new_emp_name]
                        new_dept = emp_dept[0] if emp_dept else ""
                        st.info(f"Department: **{new_dept}**")
                    else:
                        new_dept = ""
                else:
                    new_emp_name = ""
                    new_dept = ""
                
                new_active = st.checkbox("Active", value=True)
            
            submit = st.form_submit_button("➕ Create User", use_container_width=True)
            
            if submit:
                if not new_username or not new_password or not new_fullname:
                    st.error("Username, password, and full name are required")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                elif new_password != new_password2:
                    st.error("Passwords do not match")
                else:
                    try:
                        hashed, salt = hash_password(new_password)
                        run("""
                            INSERT INTO users (username, password_hash, password_salt, full_name, role, 
                                             employee_name, department, is_active, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [new_username, hashed, salt, new_fullname, new_role, 
                             new_emp_name or None, new_dept or None, new_active, username])
                        log_action(username, "CREATE_USER", f"Created user: {new_username} ({new_role})")
                        st.success(f"✅ User '{new_username}' created successfully!")
                        st.rerun()
                    except Exception as e:
                        if "unique" in str(e).lower():
                            st.error(f"Username '{new_username}' already exists")
                        else:
                            st.error(f"Error: {str(e)}")
    
    with tab2:
        st.markdown("### Manage Existing Users")
        all_users = run("""
            SELECT id, username, full_name, role, employee_name, department, is_active, last_login, created_at
            FROM users ORDER BY created_at DESC
        """, fetch=True) or []
        
        if not all_users:
            st.info("No users found.")
        else:
            users_df = pd.DataFrame(all_users, 
                                   columns=["ID", "Username", "Full Name", "Role", "Employee", "Department", 
                                          "Active", "Last Login", "Created"])
            users_df["Status"] = users_df["Active"].apply(lambda x: "✅ Active" if x else "❌ Inactive")
            users_df["Role Badge"] = users_df["Role"].apply(lambda x: x.upper())
            
            st.dataframe(users_df[["Username", "Full Name", "Role Badge", "Employee", "Department", "Status", "Last Login"]], 
                        use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### Edit User")
            
            user_to_edit = st.selectbox("Select User", [u[1] for u in all_users if u[1] != "admin"])
            
            if user_to_edit:
                user_data = [u for u in all_users if u[1] == user_to_edit][0]
                user_id, uname, ufull, urole, uemp, udept, uactive, ulast, ucreated = user_data
                
                col1, col2 = st.columns(2)
                with col1:
                    edit_fullname = st.text_input("Full Name", value=ufull, key="edit_user_fullname")
                    edit_role = st.selectbox("Role", ["employee", "manager", "admin"], 
                                           index=["employee", "manager", "admin"].index(urole),
                                           key="edit_user_role")
                    
                    if edit_role in ["employee", "manager"]:
                        active_employees = get_active_employees()
                        emp_list = [e[0] for e in active_employees]
                        edit_emp = st.selectbox("Link to Employee", [""] + emp_list,
                                              index=emp_list.index(uemp)+1 if uemp in emp_list else 0,
                                              key="edit_user_emp")
                        if edit_emp:
                            emp_dept = [e[1] for e in active_employees if e[0] == edit_emp]
                            edit_dept = emp_dept[0] if emp_dept else ""
                        else:
                            edit_dept = ""
                    else:
                        edit_emp = ""
                        edit_dept = ""
                
                with col2:
                    edit_active = st.checkbox("Active Status", value=uactive, key="edit_user_active")
                    st.markdown(f"**Current Status:** {'✅ Active' if uactive else '❌ Inactive'}")
                    st.markdown(f"**Last Login:** {ulast if ulast else 'Never'}")
                    
                    st.markdown("#### Reset Password")
                    new_pwd = st.text_input("New Password (optional)", type="password", key="edit_user_pwd")
                    new_pwd2 = st.text_input("Confirm New Password", type="password", key="edit_user_pwd2")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💾 Update User", use_container_width=True):
                        # Update user info
                        run("""
                            UPDATE users 
                            SET full_name=%s, role=%s, employee_name=%s, department=%s, is_active=%s
                            WHERE id=%s
                        """, [edit_fullname, edit_role, edit_emp or None, edit_dept or None, edit_active, user_id])
                        
                        # Update password if provided
                        if new_pwd:
                            if len(new_pwd) < 6:
                                st.error("Password must be at least 6 characters")
                            elif new_pwd != new_pwd2:
                                st.error("Passwords do not match")
                            else:
                                hashed, salt = hash_password(new_pwd)
                                run("UPDATE users SET password_hash=%s, password_salt=%s WHERE id=%s",
                                   [hashed, salt, user_id])
                                log_action(username, "RESET_PASSWORD", f"Reset password for user: {uname}")
                        
                        log_action(username, "UPDATE_USER", f"Updated user: {uname}")
                        st.success("✅ User updated!")
                        st.rerun()
                
                with col_b:
                    if st.button("🗑 Delete User", use_container_width=True):
                        run("DELETE FROM users WHERE id=%s", [user_id])
                        log_action(username, "DELETE_USER", f"Deleted user: {uname}")
                        st.success("🗑 User deleted!")
                        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# AUDIT LOG (Admin Only)
# ============================================================
if menu == "Audit Log":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 Audit Trail & Activity Log")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_user = st.selectbox("Filter by User", ["All"] + [u[1] for u in run("SELECT DISTINCT username FROM audit_log ORDER BY username", fetch=True) or []])
    with col2:
        filter_action = st.selectbox("Filter by Action", ["All"] + [a[0] for a in run("SELECT DISTINCT action FROM audit_log ORDER BY action", fetch=True) or []])
    with col3:
        limit = st.selectbox("Show Records", [50, 100, 200, 500], index=1)
    
    audit_q = "SELECT username, action, details, timestamp FROM audit_log WHERE 1=1"
    audit_p = []
    
    if filter_user != "All":
        audit_q += " AND username=%s"
        audit_p.append(filter_user)
    
    if filter_action != "All":
        audit_q += " AND action=%s"
        audit_p.append(filter_action)
    
    audit_q += f" ORDER BY timestamp DESC LIMIT {limit}"
    
    audit_logs = run(audit_q, audit_p, fetch=True) or []
    
    if audit_logs:
        audit_df = pd.DataFrame(audit_logs, columns=["Username", "Action", "Details", "Timestamp"])
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
        
        # Export audit log
        csv_data = audit_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Export Audit Log", csv_data, "audit_log.csv", "text/csv")
    else:
        st.info("No audit logs found")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# CONTROL PANEL (Admin Only)
# ============================================================
if menu == "Control Panel":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🛡 System Control Panel")
    st.markdown("<div class='small'>Complete KPI system configuration</div>", unsafe_allow_html=True)
    st.markdown("<div class='hline'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📝 KPI Names", "⚖️ KPI Weights", "⭐ Rating Rules", "⚙️ System Settings"])

    with tab1:
        st.markdown("### ✏️ KPI Labels")
        k1,k2,k3,k4 = get_kpi_labels()
        n1 = st.text_input("KPI1 Label", value=k1)
        n2 = st.text_input("KPI2 Label", value=k2)
        n3 = st.text_input("KPI3 Label", value=k3)
        n4 = st.text_input("KPI4 Label", value=k4)
        if st.button("💾 Save KPI Labels", use_container_width=True):
            run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi1'", [n1.strip() or "KPI 1"])
            run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi2'", [n2.strip() or "KPI 2"])
            run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi3'", [n3.strip() or "KPI 3"])
            run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi4'", [n4.strip() or "KPI 4"])
            log_action(username, "UPDATE_KPI_LABELS", "Updated KPI label names")
            st.success("✅ Labels saved!")
            st.rerun()

    with tab2:
        st.markdown("### ⚖️ KPI Weights (Total must be 100%)")
        w1,w2,w3,w4 = get_kpi_weights()
        
        col1, col2 = st.columns(2)
        with col1:
            nw1 = st.number_input(f"Weight {kpi1_lbl}", 0, 100, int(w1), 1)
            nw2 = st.number_input(f"Weight {kpi2_lbl}", 0, 100, int(w2), 1)
        with col2:
            nw3 = st.number_input(f"Weight {kpi3_lbl}", 0, 100, int(w3), 1)
            nw4 = st.number_input(f"Weight {kpi4_lbl}", 0, 100, int(w4), 1)
        
        totalw = nw1+nw2+nw3+nw4
        
        if totalw == 100:
            st.success(f"✅ Total Weight = {totalw}%")
        else:
            st.error(f"❌ Total Weight = {totalw}% (Must be 100%)")
        
        if st.button("💾 Save Weights", use_container_width=True):
            if totalw != 100:
                st.error("Total weights must be exactly 100%")
            else:
                run("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi1'", [int(nw1)])
                run("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi2'", [int(nw2)])
                run("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi3'", [int(nw3)])
                run("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi4'", [int(nw4)])
                log_action(username, "UPDATE_KPI_WEIGHTS", f"Updated weights: {nw1},{nw2},{nw3},{nw4}")
                st.success("✅ Weights saved!")
                st.rerun()

    with tab3:
        st.markdown("### ⭐ Rating Rules (Score out of 100)")
        ex, gd, av = get_rating_rules()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            nex = st.number_input("🌟 Excellent Min", 0, 100, int(ex), 1)
        with col2:
            ngd = st.number_input("👍 Good Min", 0, 100, int(gd), 1)
        with col3:
            nav = st.number_input("📊 Average Min", 0, 100, int(av), 1)
        
        st.info(f"""
        **Rating Logic:**
        - Score ≥ {nex} → Excellent 🌟
        - Score ≥ {ngd} → Good 👍
        - Score ≥ {nav} → Average 📊
        - Score < {nav} → Needs Improvement ⚠️
        """)
        
        if st.button("💾 Save Rating Rules", use_container_width=True):
            if not (nex >= ngd >= nav):
                st.error("Rule must satisfy: Excellent ≥ Good ≥ Average")
            else:
                run("UPDATE rating_rules SET excellent_min=%s, good_min=%s, average_min=%s WHERE id=1",
                    [int(nex), int(ngd), int(nav)])
                log_action(username, "UPDATE_RATING_RULES", f"Updated rating rules: {nex},{ngd},{nav}")
                st.success("✅ Rating rules saved!")
                st.rerun()

    with tab4:
        st.markdown("### ⚙️ System Permissions")
        cur_imp = get_setting("allow_import","1") == "1"
        cur_ed = get_setting("allow_edit_delete","1") == "1"
        
        col1, col2 = st.columns(2)
        with col1:
            ni = st.checkbox("📤 Allow Import", value=cur_imp)
        with col2:
            ne = st.checkbox("✏️ Allow Edit/Delete", value=cur_ed)
        
        if st.button("💾 Save Permissions", use_container_width=True):
            set_setting("allow_import", "1" if ni else "0")
            set_setting("allow_edit_delete", "1" if ne else "0")
            log_action(username, "UPDATE_PERMISSIONS", f"Import:{ni}, Edit/Delete:{ne}")
            st.success("✅ Permissions saved!")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- FOOTER ----------------
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div class="card" style="text-align:center">', unsafe_allow_html=True)
st.markdown(f"""
<div class='small'>
    <b>Yash Gallery KPI System v3.0</b> | Role-Based Access Control | Multi-User Authentication | Audit Trail<br>
    Logged in as: <b>{full_name}</b> ({user_role.upper()}) | Built with Streamlit + PostgreSQL (Neon)<br>
    © 2024 | Secure • Scalable • Enterprise-Ready
</div>
""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
