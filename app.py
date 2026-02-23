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
.badge-info{background:#dbeafe;color:#1e40af;border-color:#93c5fd}
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
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASE CONNECTION
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
        conn.autocommit = True
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
    """Execute a single query safely"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or [])
            if fetch:
                return cur.fetchall()
            return None
    except psycopg2.OperationalError:
        st.session_state.db_conn = init_connection()
        return run_query(query, params, fetch)
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return None if fetch else False

def run_many(query, data):
    """Execute batch insert"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.executemany(query, data)
        return True
    except Exception as e:
        st.error(f"Batch insert error: {str(e)}")
        return False

# ============================================================
# PASSWORD HASHING
# ============================================================
def hash_password(password: str, salt: str = None) -> tuple:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    test_hash, _ = hash_password(password, salt)
    return test_hash == hashed

# ============================================================
# DATABASE INITIALIZATION - FIXED VERSION
# ============================================================
def initialize_database():
    """Create all tables and insert default data - FIXED"""
    
    # Step 1: Drop all tables
    drop_queries = [
        "DROP TABLE IF EXISTS audit_log CASCADE",
        "DROP TABLE IF EXISTS kpi_entries CASCADE",
        "DROP TABLE IF EXISTS users CASCADE",
        "DROP TABLE IF EXISTS employees CASCADE",
        "DROP TABLE IF EXISTS departments CASCADE",
        "DROP TABLE IF EXISTS app_settings CASCADE",
        "DROP TABLE IF EXISTS kpi_master CASCADE",
        "DROP TABLE IF EXISTS kpi_weights CASCADE",
        "DROP TABLE IF EXISTS rating_rules CASCADE"
    ]
    
    for query in drop_queries:
        run_query(query)
    
    # Step 2: Create tables in correct order
    create_queries = [
        """CREATE TABLE departments (
            id SERIAL PRIMARY KEY,
            department_name TEXT UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        """CREATE TABLE employees (
            id SERIAL PRIMARY KEY,
            employee_name TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        """CREATE TABLE users (
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
        )""",
        
        """CREATE TABLE kpi_entries (
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
        )""",
        
        """CREATE TABLE audit_log (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        """CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""",
        
        """CREATE TABLE kpi_master (
            kpi_key TEXT PRIMARY KEY,
            kpi_label TEXT NOT NULL
        )""",
        
        """CREATE TABLE kpi_weights (
            kpi_key TEXT PRIMARY KEY,
            weight INTEGER NOT NULL
        )""",
        
        """CREATE TABLE rating_rules (
            id INTEGER PRIMARY KEY DEFAULT 1,
            excellent_min INTEGER NOT NULL,
            good_min INTEGER NOT NULL,
            average_min INTEGER NOT NULL
        )"""
    ]
    
    for query in create_queries:
        run_query(query)
    
    # Step 3: Insert default settings
    run_query("INSERT INTO app_settings(key, value) VALUES ('allow_import', '1')")
    run_query("INSERT INTO app_settings(key, value) VALUES ('allow_edit_delete', '1')")
    
    # Step 4: Insert KPI labels
    run_query("INSERT INTO kpi_master(kpi_key, kpi_label) VALUES ('kpi1', 'Quality')")
    run_query("INSERT INTO kpi_master(kpi_key, kpi_label) VALUES ('kpi2', 'Productivity')")
    run_query("INSERT INTO kpi_master(kpi_key, kpi_label) VALUES ('kpi3', 'Attendance')")
    run_query("INSERT INTO kpi_master(kpi_key, kpi_label) VALUES ('kpi4', 'Behavior')")
    
    # Step 5: Insert KPI weights
    run_query("INSERT INTO kpi_weights(kpi_key, weight) VALUES ('kpi1', 25)")
    run_query("INSERT INTO kpi_weights(kpi_key, weight) VALUES ('kpi2', 25)")
    run_query("INSERT INTO kpi_weights(kpi_key, weight) VALUES ('kpi3', 25)")
    run_query("INSERT INTO kpi_weights(kpi_key, weight) VALUES ('kpi4', 25)")
    
    # Step 6: Insert rating rules
    run_query("INSERT INTO rating_rules(id, excellent_min, good_min, average_min) VALUES (1, 80, 60, 40)")
    
    # Step 7: Create admin user
    hashed, salt = hash_password("admin123")
    run_query("""
        INSERT INTO users (username, password_hash, password_salt, full_name, role, is_active, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, ["admin", hashed, salt, "System Administrator", "admin", True, "system"])
    
    # Step 8: Insert sample departments
    sample_depts = ["Fabric", "Dyeing", "Quality Control", "Production", "Finishing", "Stitching"]
    for dept in sample_depts:
        run_query("INSERT INTO departments (department_name, is_active, created_at) VALUES (%s, %s, %s)",
                 [dept, True, datetime.now()])
    
    return True

# Initialize database on first run
if "db_initialized" not in st.session_state:
    with st.spinner("🔄 Setting up database... Please wait..."):
        try:
            if initialize_database():
                st.session_state.db_initialized = True
                st.success("✅ Database initialized successfully!")
        except Exception as e:
            st.error(f"Database initialization failed: {str(e)}")
            st.stop()

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def log_action(username: str, action: str, details: str = ""):
    """Log user actions"""
    run_query("INSERT INTO audit_log (username, action, details, timestamp) VALUES (%s, %s, %s, %s)",
             [username, action, details, datetime.now()])

def get_setting(key, default=""):
    r = run_query("SELECT value FROM app_settings WHERE key=%s", [key], fetch=True)
    return r[0][0] if r else default

def set_setting(key, value):
    run_query("INSERT INTO app_settings(key, value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
             [key, value])

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
    return (int(r[0][0]), int(r[0][1]), int(r[0][2])) if r else (80, 60, 40)

def calc_weighted_score(k1, k2, k3, k4):
    w1, w2, w3, w4 = get_kpi_weights()
    return round((k1*w1 + k2*w2 + k3*w3 + k4*w4) / 100.0, 2)

def calc_rating(score: float):
    ex, gd, av = get_rating_rules()
    if score >= ex: return "Excellent"
    if score >= gd: return "Good"
    if score >= av: return "Average"
    return "Needs Improvement"

def get_active_employees():
    return run_query("SELECT employee_name, department FROM employees WHERE is_active=TRUE ORDER BY employee_name", fetch=True) or []

def get_all_employees():
    return run_query("SELECT id, employee_name, department, is_active, created_at FROM employees ORDER BY employee_name", fetch=True) or []

def get_active_departments():
    rows = run_query("SELECT department_name FROM departments WHERE is_active=TRUE ORDER BY department_name", fetch=True) or []
    return [r[0] for r in rows]

def get_all_departments():
    rows = run_query("SELECT id, department_name, is_active, created_at FROM departments ORDER BY department_name", fetch=True) or []
    return rows

# ============================================================
# AUTHENTICATION
# ============================================================
def authenticate_user(username: str, password: str) -> dict:
    user = run_query("""
        SELECT id, username, password_hash, password_salt, full_name, role, 
               employee_name, department, is_active 
        FROM users WHERE username=%s
    """, [username], fetch=True)
    
    if not user:
        return {"success": False, "message": "❌ Invalid credentials"}
    
    user_id, uname, pwd_hash, pwd_salt, full_name, role, emp_name, dept, is_active = user[0]
    
    if not is_active:
        return {"success": False, "message": "⚠️ Account inactive"}
    
    if not verify_password(password, pwd_hash, pwd_salt):
        return {"success": False, "message": "❌ Invalid credentials"}
    
    run_query("UPDATE users SET last_login=%s WHERE id=%s", [datetime.now(), user_id])
    log_action(username, "LOGIN", "Logged in")
    
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
    if "user" not in st.session_state:
        return False
    user_role = st.session_state["user"]["role"]
    role_levels = {"admin": 3, "manager": 2, "employee": 1}
    return role_levels.get(user_role, 0) >= role_levels.get(required_role, 0)

def require_auth(required_role: str = "employee"):
    if "user" not in st.session_state:
        return False
    if not check_permission(required_role):
        st.error(f"⛔ {required_role.upper()} role required")
        return False
    return True

# ============================================================
# LOGIN PAGE
# ============================================================
def show_login_page():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown("## 🔐 Yash Gallery KPI")
    st.markdown("### Welcome Back!")
    st.markdown("---")
    
    with st.form("login_form"):
        username = st.text_input("👤 Username")
        password = st.text_input("🔒 Password", type="password")
        
        col1, col2 = st.columns(2)
        submit = col1.form_submit_button("🚀 Login", use_container_width=True)
        
        if submit and username and password:
            result = authenticate_user(username, password)
            if result["success"]:
                st.session_state["user"] = result
                st.session_state["logged_in"] = True
                st.success(f"✅ Welcome, {result['full_name']}!")
                st.rerun()
            else:
                st.error(result["message"])
    
    st.markdown("---")
    st.markdown("<div class='small' style='text-align:center'><b>Default:</b><br>Username: <code>admin</code> | Password: <code>admin123</code></div>", 
                unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# SESSION MANAGEMENT
# ============================================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()

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
    st.markdown("### 👤 Profile")
    st.markdown(f"**{full_name}**")
    st.markdown(f"<span class='role-badge-{user_role}'>{user_role.upper()}</span>", unsafe_allow_html=True)
    
    if user_employee_name:
        st.markdown(f"**Employee:** {user_employee_name}")
    if user_department:
        st.markdown(f"**Dept:** {user_department}")
    
    if st.button("🚪 Logout", use_container_width=True):
        log_action(username, "LOGOUT", "Logged out")
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    st.markdown("## 🔎 Filters")
    
    if user_role == "employee":
        dept_filter = user_department or "All"
        emp_filter = user_employee_name or "All"
        st.info("Your data only")
    else:
        dept_rows = run_query("SELECT DISTINCT department FROM kpi_entries ORDER BY department", fetch=True) or []
        dept_list = [r[0] for r in dept_rows]
        
        if user_role == "manager":
            dept_list = [d for d in dept_list if d == user_department]
            dept_filter = user_department if user_department in dept_list else "All"
        else:
            dept_filter = st.selectbox("Department", ["All"] + dept_list)
        
        emp_q = "SELECT DISTINCT employee_name FROM kpi_entries WHERE 1=1"
        emp_p = []
        if dept_filter != "All":
            emp_q += " AND department=%s"
            emp_p.append(dept_filter)
        emp_q += " ORDER BY employee_name"
        
        emp_rows = run_query(emp_q, emp_p, fetch=True) or []
        emp_list = [r[0] for r in emp_rows]
        emp_filter = st.selectbox("Employee", ["All"] + emp_list)
    
    rating_filter = st.selectbox("Rating", ["All", "Excellent", "Good", "Average", "Needs Improvement"])

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="card">', unsafe_allow_html=True)
col_h1, col_h2 = st.columns([3, 2])
col_h1.title("📊 Yash Gallery KPI")
col_h1.caption("Role-Based • Multi-User • Audit Trail")
col_h2.markdown(f"<span class='badge'>{username}</span> <span class='role-badge-{user_role}'>{user_role.upper()}</span>", 
                unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# MENU
# ============================================================
if user_role == "admin":
    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employees", "Departments", "Users", "Audit", "Settings"]
    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people", "building", "person-badge", "clipboard-data", "gear"]
elif user_role == "manager":
    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employees"]
    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people"]
else:
    menu_options = ["Dashboard", "My Records"]
    menu_icons = ["speedometer2", "table"]

menu = option_menu(None, menu_options, icons=menu_icons, orientation="horizontal",
    styles={"container": {"padding": "0.2rem 0", "background-color": "#fff", "border": "1px solid #e5e7eb", "border-radius": "14px"},
            "nav-link": {"font-size": "13px", "padding": "8px 10px"},
            "nav-link-selected": {"background-color": "#2563EB", "color": "white"}})

# Query KPI entries
q = "SELECT id, employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at, COALESCE(created_by, 'system') FROM kpi_entries WHERE 1=1"
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

q += " ORDER BY created_at DESC"

rows = run_query(q, p, fetch=True) or []
df = pd.DataFrame(rows, columns=["ID", "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
                                 "Score", "Rating", "Created At", "Created By"])

kpi1_lbl, kpi2_lbl, kpi3_lbl, kpi4_lbl = get_kpi_labels()

# ============================================================
# DEPARTMENTS MENU - COMPLETELY FIXED
# ============================================================
if menu == "Departments":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🏢 Department Management")
    
    tab1, tab2 = st.tabs(["➕ Add Department", "📋 Manage Departments"])
    
    with tab1:
        st.markdown("### Add New Department")
        
        with st.form("add_dept_form", clear_on_submit=True):
            dept_name = st.text_input("🏢 Department Name", placeholder="e.g., HR, Marketing, IT")
            dept_active = st.checkbox("✅ Active Status", value=True)
            
            submit = st.form_submit_button("➕ Add Department", use_container_width=True, type="primary")
            
            if submit:
                if dept_name.strip():
                    # Check if department already exists
                    existing = run_query("SELECT id FROM departments WHERE LOWER(department_name)=LOWER(%s)", 
                                        [dept_name.strip()], fetch=True)
                    
                    if existing:
                        st.error(f"❌ Department '{dept_name}' already exists!")
                    else:
                        result = run_query("""
                            INSERT INTO departments (department_name, is_active, created_at)
                            VALUES (%s, %s, %s)
                        """, [dept_name.strip(), dept_active, datetime.now()])
                        
                        if result is not None:
                            log_action(username, "ADD_DEPARTMENT", f"Added: {dept_name}")
                            st.success(f"✅ Department '{dept_name}' added successfully!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Failed to add department. Please try again.")
                else:
                    st.error("⚠️ Please enter department name.")
    
    with tab2:
        st.markdown("### Existing Departments")
        
        # Get all departments
        depts = get_all_departments()
        
        if depts and len(depts) > 0:
            # Create DataFrame
            dept_df = pd.DataFrame(depts, columns=["ID", "Name", "Active", "Created"])
            dept_df["Status"] = dept_df["Active"].apply(lambda x: "✅ Active" if x else "❌ Inactive")
            
            # Count employees per department
            for idx, row in dept_df.iterrows():
                emp_count = run_query("SELECT COUNT(*) FROM employees WHERE department=%s", 
                                     [row["Name"]], fetch=True)
                dept_df.at[idx, "Employees"] = emp_count[0][0] if emp_count else 0
            
            # Display table
            st.dataframe(dept_df[["Name", "Status", "Employees", "Created"]], 
                        use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### ✏️ Edit Department")
            
            dept_names = [d[1] for d in depts]
            dept_to_edit = st.selectbox("Select Department", dept_names, key="dept_select")
            
            if dept_to_edit:
                # Get department data
                dept_data = [d for d in depts if d[1] == dept_to_edit][0]
                dept_id, dept_name, dept_active, dept_created = dept_data
                
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    new_dept_name = st.text_input("Department Name", value=dept_name, key="edit_dept_name")
                
                with col_d2:
                    new_dept_active = st.checkbox("Active Status", value=dept_active, key="edit_dept_active")
                    st.info(f"**Current:** {'✅ Active' if dept_active else '❌ Inactive'}")
                    st.info(f"**Created:** {dept_created}")
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("💾 Update Department", use_container_width=True, type="primary"):
                        if new_dept_name.strip():
                            # Check if new name conflicts with existing
                            if new_dept_name.strip().lower() != dept_name.lower():
                                existing = run_query("SELECT id FROM departments WHERE LOWER(department_name)=LOWER(%s)", 
                                                    [new_dept_name.strip()], fetch=True)
                                if existing:
                                    st.error(f"❌ Department '{new_dept_name}' already exists!")
                                    st.stop()
                            
                            result = run_query("""
                                UPDATE departments 
                                SET department_name=%s, is_active=%s
                                WHERE id=%s
                            """, [new_dept_name.strip(), new_dept_active, dept_id])
                            
                            if result is not None:
                                log_action(username, "UPDATE_DEPT", f"Updated: {dept_name} → {new_dept_name}")
                                st.success("✅ Department updated successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to update. Please try again.")
                        else:
                            st.error("⚠️ Department name cannot be empty.")
                
                with col_btn2:
                    if st.button("🗑️ Delete Department", use_container_width=True, type="secondary"):
                        # Check if department has employees
                        emp_count = run_query("SELECT COUNT(*) FROM employees WHERE department=%s", 
                                            [dept_name], fetch=True)
                        
                        if emp_count and emp_count[0][0] > 0:
                            st.error(f"⚠️ Cannot delete! {emp_count[0][0]} employees exist in this department.")
                        else:
                            # Check if department has KPI entries
                            kpi_count = run_query("SELECT COUNT(*) FROM kpi_entries WHERE department=%s",
                                                [dept_name], fetch=True)
                            
                            if kpi_count and kpi_count[0][0] > 0:
                                st.warning(f"⚠️ Warning: {kpi_count[0][0]} KPI entries exist for this department.")
                                if st.checkbox("I understand and want to delete anyway"):
                                    result = run_query("DELETE FROM departments WHERE id=%s", [dept_id])
                                    if result is not None:
                                        log_action(username, "DELETE_DEPT", f"Deleted: {dept_name}")
                                        st.success("🗑️ Department deleted!")
                                        st.rerun()
                            else:
                                result = run_query("DELETE FROM departments WHERE id=%s", [dept_id])
                                if result is not None:
                                    log_action(username, "DELETE_DEPT", f"Deleted: {dept_name}")
                                    st.success("🗑️ Department deleted!")
                                    st.rerun()
        else:
            st.info("📌 No departments found. Add departments using the 'Add Department' tab.")
            st.info("💡 Sample departments should have been created during initialization.")
            
            # Add button to reinitialize if needed
            if st.button("🔄 Reinitialize Sample Departments"):
                sample_depts = ["Fabric", "Dyeing", "Quality Control", "Production", "Finishing", "Stitching"]
                for dept in sample_depts:
                    existing = run_query("SELECT id FROM departments WHERE department_name=%s", [dept], fetch=True)
                    if not existing:
                        run_query("INSERT INTO departments (department_name, is_active, created_at) VALUES (%s, %s, %s)",
                                [dept, True, datetime.now()])
                st.success("✅ Sample departments created!")
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# OTHER MENUS (Dashboard, Entry, etc.) - Simplified versions
# ============================================================
elif menu == "Dashboard":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Records", len(df))
    col2.metric("Avg Score", round(df["Score"].mean(), 2) if len(df) > 0 else 0)
    col3.metric("Best", round(df["Score"].max(), 2) if len(df) > 0 else 0)
    col4.metric("Departments", len(get_all_departments()))
    
    if len(df) > 0:
        st.markdown("---")
        rating_counts = df["Rating"].value_counts().reset_index()
        rating_counts.columns = ["Rating", "Count"]
        fig = px.pie(rating_counts, values="Count", names="Rating", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

elif menu == "Entry":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("➕ Add KPI Entry")
    
    with st.form("add_kpi"):
        active_emps = get_active_employees()
        if user_role == "manager":
            active_emps = [e for e in active_emps if e[1] == user_department]
        
        emp_list = [e[0] for e in active_emps]
        emp = st.selectbox("Employee", [""] + emp_list)
        
        if emp:
            dept = [e[1] for e in active_emps if e[0] == emp][0]
            st.info(f"Dept: {dept}")
        else:
            dept = ""
        
        c1,c2,c3,c4 = st.columns(4)
        v1 = c1.number_input(kpi1_lbl, 1, 100, 50)
        v2 = c2.number_input(kpi2_lbl, 1, 100, 50)
        v3 = c3.number_input(kpi3_lbl, 1, 100, 50)
        v4 = c4.number_input(kpi4_lbl, 1, 100, 50)
        
        if st.form_submit_button("Save", use_container_width=True):
            if emp and dept:
                score = calc_weighted_score(v1,v2,v3,v4)
                rating = calc_rating(score)
                now = datetime.now()
                
                run_query("""
                    INSERT INTO kpi_entries (employee_name, department, kpi1,kpi2,kpi3,kpi4, 
                                            total_score, rating, created_at, entry_month, created_by)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, [emp, dept, v1,v2,v3,v4, score, rating, now, now.strftime("%Y-%m"), username])
                
                log_action(username, "ADD_KPI", f"{emp} - {score}")
                st.success(f"✅ Saved! Score: {score}")
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

elif menu in ["Records", "My Records"]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 Records")
    
    if len(df) > 0:
        st.dataframe(df.drop(columns=["ID", "Created By"]), use_container_width=True)
        csv = df.to_csv(index=False).encode()
        st.download_button("📥 Download", csv, "records.csv")
    else:
        st.info("No records")
    
    st.markdown("</div>", unsafe_allow_html=True)

elif menu == "Employees":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👥 Employees")
    
    tab1, tab2 = st.tabs(["Add", "Manage"])
    
    with tab1:
        with st.form("add_emp"):
            name = st.text_input("Name")
            if user_role == "admin":
                dept = st.selectbox("Dept", get_active_departments())
            else:
                dept = user_department
            
            if st.form_submit_button("Add"):
                if name and dept:
                    run_query("INSERT INTO employees(employee_name, department, is_active) VALUES(%s,%s,%s)",
                             [name, dept, True])
                    st.success("Added!")
                    st.rerun()
    
    with tab2:
        emps = get_all_employees()
        if emps:
            emp_df = pd.DataFrame(emps, columns=["ID","Name","Dept","Active","Created"])
            st.dataframe(emp_df[["Name","Dept","Active"]], use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info(f"📌 {menu} page - Implementation in progress")

# Footer
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f'<div class="card" style="text-align:center"><div class="small"><b>Yash Gallery KPI v3.0</b> | {full_name} ({user_role.upper()})</div></div>', 
            unsafe_allow_html=True)
