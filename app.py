import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
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
# DATABASE CONNECTION WITH AUTO-RECOVERY
# ============================================================
def get_connection():
    """Get database connection with auto-recovery"""
    try:
        if 'db_conn' not in st.session_state or st.session_state.db_conn.closed:
            conn = psycopg2.connect(
                st.secrets["NEON_DATABASE_URL"],
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
            st.session_state.db_conn = conn
        return st.session_state.db_conn
    except Exception as e:
        st.error(f"❌ Database connection error: {str(e)}")
        st.stop()

def execute_query(query, params=None, fetch=False, fetch_one=False):
    """Execute query with automatic retry on connection failure"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                if fetch_one:
                    result = cur.fetchone()
                    conn.commit()
                    return result
                elif fetch:
                    result = cur.fetchall()
                    conn.commit()
                    return result
                else:
                    conn.commit()
                    return True
        except psycopg2.OperationalError:
            # Connection lost, clear and retry
            if 'db_conn' in st.session_state:
                try:
                    st.session_state.db_conn.close()
                except:
                    pass
                del st.session_state.db_conn
            if attempt == max_retries - 1:
                st.error("❌ Database connection lost. Please refresh the page.")
                return [] if fetch else False
        except Exception as e:
            conn = get_connection()
            conn.rollback()
            st.error(f"❌ Database error: {str(e)}")
            return [] if fetch else False

# ============================================================
# PASSWORD HASHING
# ============================================================
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

# ============================================================
# DATABASE INITIALIZATION
# ============================================================
def initialize_database():
    """Initialize database WITHOUT dropping existing data"""
    try:
        # Check if tables exist
        table_check = execute_query("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'kpi_entries'
            )
        """, fetch_one=True)
        
        tables_exist = table_check[0] if table_check else False
        
        if tables_exist:
            st.info("✅ Database exists. Data preserved.")
            return True
        
        # First-time setup
        st.info("🔄 First-time database setup...")
        
        # Create departments table
        execute_query("""
            CREATE TABLE IF NOT EXISTS departments (
                id SERIAL PRIMARY KEY,
                department_name TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create employees table
        execute_query("""
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                employee_name TEXT UNIQUE NOT NULL,
                department TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create users table
        execute_query("""
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
        
        # Create kpi_entries table
        execute_query("""
            CREATE TABLE IF NOT EXISTS kpi_entries (
                id SERIAL PRIMARY KEY,
                employee_name TEXT NOT NULL,
                department TEXT NOT NULL,
                kpi1 INTEGER NOT NULL,
                kpi2 INTEGER NOT NULL,
                kpi3 INTEGER NOT NULL,
                kpi4 INTEGER NOT NULL,
                total_score DOUBLE PRECISION NOT NULL,
                rating TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                entry_month TEXT,
                created_by TEXT,
                updated_by TEXT,
                updated_at TIMESTAMP
            )
        """)
        
        # Create audit_log table
        execute_query("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create app_settings table
        execute_query("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Create kpi_master table
        execute_query("""
            CREATE TABLE IF NOT EXISTS kpi_master (
                kpi_key TEXT PRIMARY KEY,
                kpi_label TEXT NOT NULL
            )
        """)
        
        # Create kpi_weights table
        execute_query("""
            CREATE TABLE IF NOT EXISTS kpi_weights (
                kpi_key TEXT PRIMARY KEY,
                weight INTEGER NOT NULL
            )
        """)
        
        # Create rating_rules table
        execute_query("""
            CREATE TABLE IF NOT EXISTS rating_rules (
                id INTEGER PRIMARY KEY DEFAULT 1,
                excellent_min INTEGER NOT NULL,
                good_min INTEGER NOT NULL,
                average_min INTEGER NOT NULL
            )
        """)
        
        # Insert default settings
        for key, value in [("allow_import", "1"), ("allow_edit_delete", "1"), ("session_timeout", "30")]:
            execute_query("INSERT INTO app_settings(key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING", 
                        [key, value])
        
        # Insert default KPI labels
        for kpi_key, label in [("kpi1", "Quality"), ("kpi2", "Productivity"), 
                              ("kpi3", "Attendance"), ("kpi4", "Behavior")]:
            execute_query("INSERT INTO kpi_master(kpi_key, kpi_label) VALUES (%s, %s) ON CONFLICT (kpi_key) DO NOTHING", 
                        [kpi_key, label])
        
        # Insert default KPI weights
        for kpi_key in ["kpi1", "kpi2", "kpi3", "kpi4"]:
            execute_query("INSERT INTO kpi_weights(kpi_key, weight) VALUES (%s, %s) ON CONFLICT (kpi_key) DO NOTHING", 
                        [kpi_key, 25])
        
        # Insert default rating rules
        execute_query("INSERT INTO rating_rules(id, excellent_min, good_min, average_min) VALUES (1, 80, 60, 40) ON CONFLICT (id) DO NOTHING")
        
        # Create admin user
        admin_exists = execute_query("SELECT id FROM users WHERE username='admin'", fetch=True)
        if not admin_exists:
            hashed, salt = hash_password("admin123")
            execute_query("""
                INSERT INTO users (username, password_hash, password_salt, full_name, role, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, ["admin", hashed, salt, "System Administrator", "admin", True, "system"])
        
        # Insert sample departments
        for dept_name in ["Fabric", "Dyeing", "Quality Control", "Production", "Finishing", "Stitching"]:
            execute_query("INSERT INTO departments (department_name, is_active, created_at) VALUES (%s, %s, %s) ON CONFLICT (department_name) DO NOTHING", 
                        [dept_name, True, datetime.now()])
        
        st.success("✅ Database initialized with sample data!")
        return True
    except Exception as e:
        st.error(f"❌ Database initialization error: {str(e)}")
        return False

# Initialize database (preserve data)
if "db_initialized" not in st.session_state:
    with st.spinner("🔄 Checking database..."):
        if initialize_database():
            st.session_state.db_initialized = True

# ============================================================
# AUDIT LOG
# ============================================================
def log_action(username: str, action: str, details: str = ""):
    """Log user action"""
    execute_query("INSERT INTO audit_log (username, action, details, timestamp) VALUES (%s, %s, %s, %s)",
                 [username, action, details, datetime.now()])

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def get_setting(key, default=""):
    """Get app setting"""
    result = execute_query("SELECT value FROM app_settings WHERE key=%s", [key], fetch_one=True)
    return result[0] if result else default

def set_setting(key, value):
    """Update app setting"""
    execute_query("""
        INSERT INTO app_settings(key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
    """, [key, value])

def get_kpi_labels():
    """Get KPI labels"""
    rows = execute_query("SELECT kpi_key, kpi_label FROM kpi_master ORDER BY kpi_key", fetch=True) or []
    labels = {k: v for k, v in rows}
    return (labels.get("kpi1", "KPI 1"), labels.get("kpi2", "KPI 2"), 
            labels.get("kpi3", "KPI 3"), labels.get("kpi4", "KPI 4"))

def get_kpi_weights():
    """Get KPI weights"""
    rows = execute_query("SELECT kpi_key, weight FROM kpi_weights ORDER BY kpi_key", fetch=True) or []
    weights = {k: int(w) for k, w in rows}
    return (weights.get("kpi1", 25), weights.get("kpi2", 25), 
            weights.get("kpi3", 25), weights.get("kpi4", 25))

def get_rating_rules():
    """Get rating rules"""
    result = execute_query("SELECT excellent_min, good_min, average_min FROM rating_rules WHERE id=1", fetch_one=True)
    return (int(result[0]), int(result[1]), int(result[2])) if result else (80, 60, 40)

def calc_weighted_score(k1, k2, k3, k4):
    """Calculate weighted score"""
    w1, w2, w3, w4 = get_kpi_weights()
    return round((k1*w1 + k2*w2 + k3*w3 + k4*w4) / 100.0, 2)

def calc_rating(score: float):
    """Calculate rating"""
    ex, gd, av = get_rating_rules()
    if score >= ex: return "Excellent"
    if score >= gd: return "Good"
    if score >= av: return "Average"
    return "Needs Improvement"

def get_active_employees():
    """Get active employees"""
    return execute_query("SELECT employee_name, department FROM employees WHERE is_active=TRUE ORDER BY employee_name", fetch=True) or []

def get_all_employees():
    """Get all employees"""
    return execute_query("SELECT id, employee_name, department, is_active, created_at FROM employees ORDER BY employee_name", fetch=True) or []

def get_active_departments():
    """Get active departments"""
    rows = execute_query("SELECT department_name FROM departments WHERE is_active=TRUE ORDER BY department_name", fetch=True) or []
    return [r[0] for r in rows]

def get_all_departments():
    """Get all departments"""
    return execute_query("SELECT id, department_name, is_active, created_at FROM departments ORDER BY department_name", fetch=True) or []

# ============================================================
# AUTHENTICATION
# ============================================================
def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user"""
    user = execute_query("""
        SELECT id, username, password_hash, password_salt, full_name, role, 
               employee_name, department, is_active 
        FROM users WHERE username=%s
    """, [username], fetch_one=True)
    
    if not user:
        return {"success": False, "message": "❌ Invalid credentials"}
    
    user_id, uname, pwd_hash, pwd_salt, full_name, role, emp_name, dept, is_active = user
    
    if not is_active:
        return {"success": False, "message": "⚠️ Account inactive"}
    
    if not verify_password(password, pwd_hash, pwd_salt):
        return {"success": False, "message": "❌ Invalid credentials"}
    
    # Update last login
    execute_query("UPDATE users SET last_login=%s WHERE id=%s", [datetime.now(), user_id])
    log_action(username, "LOGIN", "User logged in")
    
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
    """Check user permission"""
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

# ============================================================
# LOGIN PAGE
# ============================================================
def show_login_page():
    """Show login page"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown("## 🔐 Yash Gallery KPI System")
    st.markdown("### Welcome Back!")
    st.markdown("---")
    
    with st.form("login_form"):
        username = st.text_input("👤 Username", placeholder="Enter username")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter password")
        
        col1, col2 = st.columns(2)
        submit = col1.form_submit_button("🚀 Login", use_container_width=True)
        
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
                st.error("⚠️ Please enter username and password")
    
    st.markdown("---")
    st.markdown("""
    <div class='small' style='text-align:center'>
        <b>💾 Data Persistence:</b><br>
        ✅ All data permanently saved<br>
        ✅ Refresh-safe, only manual delete removes data
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# SESSION MANAGEMENT
# ============================================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

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
    
    if st.button("🚪 Logout", use_container_width=True, type="primary"):
        log_action(username, "LOGOUT", "User logged out")
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    st.markdown("## 🔎 Filters")
    
    # Role-based filtering
    if user_role == "employee":
        dept_filter = user_department or "All"
        emp_filter = user_employee_name or "All"
        st.info("📌 Your data only")
    else:
        dept_rows = execute_query(
            "SELECT DISTINCT department FROM kpi_entries WHERE department IS NOT NULL ORDER BY department",
            fetch=True
        ) or []
        dept_list = [r[0] for r in dept_rows]
        
        if user_role == "manager":
            dept_list = [d for d in dept_list if d == user_department]
            dept_filter = user_department if user_department in dept_list else "All"
            if dept_filter != "All":
                st.info(f"📌 Department: {dept_filter}")
        else:
            dept_filter = st.selectbox("🏢 Department", ["All"] + dept_list)
        
        emp_q = "SELECT DISTINCT employee_name FROM kpi_entries WHERE employee_name IS NOT NULL"
        emp_p = []
        if dept_filter != "All":
            emp_q += " AND department=%s"
            emp_p.append(dept_filter)
        emp_q += " ORDER BY employee_name"
        
        emp_rows = execute_query(emp_q, emp_p, fetch=True) or []
        emp_list = [r[0] for r in emp_rows]
        emp_filter = st.selectbox("👤 Employee", ["All"] + emp_list)
    
    date_range = st.date_input("📅 Date Range", value=[])
    rating_filter = st.selectbox("⭐ Rating", ["All", "Excellent", "Good", "Average", "Needs Improvement"])
    
    # Data status
    st.markdown("---")
    st.markdown("### 💾 Data Status")
    total_saved = len(execute_query("SELECT id FROM kpi_entries", fetch=True) or [])
    st.success(f"✅ {total_saved} saved")
    st.info("🔒 Persistent")

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="card">', unsafe_allow_html=True)
col_h1, col_h2 = st.columns([3, 2])

with col_h1:
    st.title("📊 Yash Gallery – KPI Management")
    st.caption("💾 Persistent Data • 🔐 Secure • 👥 Multi-User • 📈 Analytics")

with col_h2:
    st.markdown(f"""
        <div style='text-align:right;padding:10px'>
            <span class='badge badge-info'>{username}</span><br>
            <span class='role-badge-{user_role}'>{user_role.upper()}</span>
            <span class='badge badge-success'>● Online</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# MENU
# ============================================================
if user_role == "admin":
    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employees", "Departments", "Users", "Audit Log", "Settings"]
    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people", "building", "person-badge", "clipboard-data", "gear"]
elif user_role == "manager":
    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employees"]
    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people"]
else:
    menu_options = ["Dashboard", "My Records"]
    menu_icons = ["speedometer2", "table"]

menu = option_menu(
    None, menu_options, icons=menu_icons,
    default_index=0, orientation="horizontal",
    styles={
        "container": {"padding": "0.2rem 0", "background-color": "#fff", "border": "1px solid #e5e7eb", "border-radius": "14px"},
        "icon": {"color": "#2563EB", "font-size": "16px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "padding": "10px 12px", "color": "#374151"},
        "nav-link-selected": {"background-color": "#2563EB", "color": "white", "font-weight": "bold"},
    }
)

# ============================================================
# QUERY KPI DATA
# ============================================================
q = """
SELECT id, employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, 
       created_at, COALESCE(created_by, 'system') as created_by
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

rows = execute_query(q, p, fetch=True) or []
df = pd.DataFrame(rows, columns=["ID", "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
                                 "Score", "Rating", "Created At", "Created By"])

kpi1_lbl, kpi2_lbl, kpi3_lbl, kpi4_lbl = get_kpi_labels()

# ============================================================
# DASHBOARD
# ============================================================
if menu == "Dashboard":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 KPI Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_records = len(df)
    avg_score = round(float(df["Score"].mean()), 2) if total_records > 0 else 0
    best_score = round(float(df["Score"].max()), 2) if total_records > 0 else 0
    
    if user_role == "admin":
        active_emp = len(execute_query("SELECT id FROM employees WHERE is_active=TRUE", fetch=True) or [])
        active_dept = len(execute_query("SELECT id FROM departments WHERE is_active=TRUE", fetch=True) or [])
    elif user_role == "manager":
        active_emp = len(execute_query("SELECT id FROM employees WHERE is_active=TRUE AND department=%s", 
                                      [user_department], fetch=True) or [])
        active_dept = 1
    else:
        active_emp = 1
        active_dept = 1
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("📝 Records", total_records)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("⭐ Avg Score", avg_score)
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
        
        # Rating Distribution
        col_c1, col_c2 = st.columns([1.5, 1])
        
        with col_c1:
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
        
        with col_c2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🎯 Performance")
            total = len(df)
            
            for rating, color, emoji in [
                ("Excellent", "#dcfce7", "🌟"),
                ("Good", "#dbeafe", "👍"),
                ("Average", "#fef3c7", "📊"),
                ("Needs Improvement", "#fee2e2", "⚠️")
            ]:
                cnt = len(df[df["Rating"] == rating])
                pct = round(cnt/total*100, 1) if total > 0 else 0
                st.markdown(f"""
                <div class='performance-box' style='background:{color}'>
                    <b>{emoji} {rating}:</b> {cnt} ({pct}%)
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Charts
        if user_role != "employee":
            st.write("")
            col_p1, col_p2 = st.columns(2)
            
            with col_p1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("🏭 Department")
                dept_avg = df.groupby("Department")["Score"].mean().reset_index()
                dept_avg = dept_avg.sort_values("Score", ascending=False)
                fig = px.bar(dept_avg, x="Department", y="Score", 
                            color="Score", color_continuous_scale="Viridis", text="Score")
                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col_p2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("👤 Top 10")
                top_emp = df.groupby("Employee")["Score"].mean().reset_index()
                top_emp = top_emp.sort_values("Score", ascending=False).head(10)
                fig = px.bar(top_emp, x="Score", y="Employee", orientation='h',
                            color="Score", color_continuous_scale="RdYlGn", text="Score")
                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, height=400)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Monthly Trend
        st.write("")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📈 Monthly Trend")
        tmp = df.copy()
        tmp["Month"] = pd.to_datetime(tmp["Created At"]).dt.to_period("M").astype(str)
        monthly = tmp.groupby("Month")["Score"].mean().reset_index().sort_values("Month")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly["Month"], y=monthly["Score"],
            mode='lines+markers', name='Avg Score',
            line=dict(color='#2563eb', width=3),
            marker=dict(size=10)
        ))
        fig.update_layout(xaxis_title="Month", yaxis_title="Score", height=350)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("📌 No data. Add entries to see dashboard!")

# ============================================================
# ENTRY
# ============================================================
if menu == "Entry":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("➕ Add KPI Entry")
    
    with st.form("kpi_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            active_emps = get_active_employees()
            if user_role == "manager":
                active_emps = [e for e in active_emps if e[1] == user_department]
            
            emp_list = [e[0] for e in active_emps]
            emp = st.selectbox("👤 Employee", [""] + emp_list)
            
            if emp:
                dept = [e[1] for e in active_emps if e[0] == emp][0]
                st.success(f"✅ Department: **{dept}**")
            else:
                dept = user_department if user_role == "manager" else ""
        
        with col2:
            st.markdown("### 📅 Info")
            st.info(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}")
            st.info(f"**By:** {username}")
        
        st.markdown("---")
        st.markdown("### 📊 KPI Scores (1-100)")
        
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        
        with col_k1:
            v1 = st.number_input(f"🎯 {kpi1_lbl}", 1, 100, 50, 1)
        with col_k2:
            v2 = st.number_input(f"📈 {kpi2_lbl}", 1, 100, 50, 1)
        with col_k3:
            v3 = st.number_input(f"📅 {kpi3_lbl}", 1, 100, 50, 1)
        with col_k4:
            v4 = st.number_input(f"🤝 {kpi4_lbl}", 1, 100, 50, 1)
        
        preview_score = calc_weighted_score(v1, v2, v3, v4)
        preview_rating = calc_rating(preview_score)
        
        st.markdown("---")
        col_p, col_s = st.columns([2, 1])
        
        with col_p:
            st.markdown(f"### 📊 Preview")
            st.markdown(f"**Score:** {preview_score} / 100")
            st.markdown(f"**Rating:** {preview_rating}")
        
        with col_s:
            submit = st.form_submit_button("✅ Save", use_container_width=True, type="primary")
    
    if submit:
        if emp and dept:
            score = calc_weighted_score(v1, v2, v3, v4)
            rating = calc_rating(score)
            now = datetime.now()
            month = now.strftime("%Y-%m")
            
            result = execute_query("""
                INSERT INTO kpi_entries (employee_name, department, kpi1, kpi2, kpi3, kpi4, 
                                        total_score, rating, created_at, entry_month, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [emp, dept, v1, v2, v3, v4, score, rating, now, month, username])
            
            if result:
                log_action(username, "CREATE_KPI", f"{emp} - {score}")
                st.success(f"✅ Saved! **Score:** {score} | **Rating:** {rating}")
                st.info("💾 Data permanently saved to database!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Failed to save")
        else:
            st.error("⚠️ Select employee")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# RECORDS / MY RECORDS
# ============================================================
if menu in ["Records", "My Records"]:
    if menu == "Records" and not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(f"📋 {menu}")
    
    if len(df) > 0:
        show_df = df.drop(columns=["ID"]).rename(columns={
            "KPI1": kpi1_lbl, "KPI2": kpi2_lbl,
            "KPI3": kpi3_lbl, "KPI4": kpi4_lbl
        })
        
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
        
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"**Total:** {len(df)} records (💾 Permanently saved)")
        
        with col2:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 CSV", csv, 
                             f"kpi_{datetime.now().strftime('%Y%m%d')}.csv",
                             "text/csv", use_container_width=True)
        
        with col3:
            st.download_button("📊 Excel", csv,
                             f"kpi_{datetime.now().strftime('%Y%m%d')}.csv",
                             "application/vnd.ms-excel", use_container_width=True)
    else:
        st.info("📌 No records. Once added, data will be saved permanently.")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Edit/Delete
    if user_role in ["admin", "manager"] and len(df) > 0 and get_setting("allow_edit_delete", "1") == "1":
        st.write("")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("✏️ Edit / Delete")
        
        rec_id = st.selectbox("Select Record", df["ID"].tolist())
        row = df[df["ID"] == rec_id].iloc[0]
        
        col_e1, col_e2 = st.columns([2, 1])
        
        with col_e1:
            st.markdown("#### Edit Values")
            col_k1, col_k2, col_k3, col_k4 = st.columns(4)
            
            with col_k1:
                ek1 = st.number_input(kpi1_lbl, 1, 100, int(row["KPI1"]), key="ek1")
            with col_k2:
                ek2 = st.number_input(kpi2_lbl, 1, 100, int(row["KPI2"]), key="ek2")
            with col_k3:
                ek3 = st.number_input(kpi3_lbl, 1, 100, int(row["KPI3"]), key="ek3")
            with col_k4:
                ek4 = st.number_input(kpi4_lbl, 1, 100, int(row["KPI4"]), key="ek4")
        
        with col_e2:
            st.markdown("#### Current")
            st.info(f"**Employee:** {row['Employee']}")
            st.info(f"**Dept:** {row['Department']}")
            st.info(f"**Score:** {row['Score']}")
            st.info(f"**Rating:** {row['Rating']}")
            
            new_score = calc_weighted_score(ek1, ek2, ek3, ek4)
            new_rating = calc_rating(new_score)
            st.success(f"**New:** {new_score}")
            st.success(f"**New:** {new_rating}")
        
        st.markdown("---")
        col_b1, col_b2, col_b3 = st.columns([1, 1, 2])
        
        with col_b1:
            if st.button("💾 Update", use_container_width=True, type="primary"):
                execute_query("""
                    UPDATE kpi_entries 
                    SET kpi1=%s, kpi2=%s, kpi3=%s, kpi4=%s, total_score=%s, rating=%s, 
                        updated_by=%s, updated_at=%s
                    WHERE id=%s
                """, [ek1, ek2, ek3, ek4, new_score, new_rating, username, datetime.now(), rec_id])
                
                log_action(username, "UPDATE_KPI", f"ID {rec_id}")
                st.success("✅ Updated!")
                st.rerun()
        
        with col_b2:
            if st.button("🗑️ Delete", use_container_width=True):
                execute_query("DELETE FROM kpi_entries WHERE id=%s", [rec_id])
                log_action(username, "DELETE_KPI", f"ID {rec_id}")
                st.warning("🗑️ Deleted!")
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# REPORTS
# ============================================================
if menu == "Reports":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 Reports")
    
    if len(df) > 0:
        tmp = df.copy()
        tmp["Month"] = pd.to_datetime(tmp["Created At"]).dt.to_period("M").astype(str)
        months = sorted(tmp["Month"].unique())[::-1]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            report_type = st.selectbox("Type", ["Employee Average", "Department Average", "Detailed"])
        
        with col2:
            sel_month = st.selectbox("Month", months)
        
        with col3:
            chart_type = st.selectbox("Chart", ["Bar", "Line", "Pie"])
        
        mdf = tmp[tmp["Month"] == sel_month]
        
        st.markdown("---")
        
        if report_type == "Employee Average":
            rep = mdf.groupby("Employee")["Score"].mean().reset_index().sort_values("Score", ascending=False)
            x, y = "Employee", "Score"
        elif report_type == "Department Average":
            rep = mdf.groupby("Department")["Score"].mean().reset_index().sort_values("Score", ascending=False)
            x, y = "Department", "Score"
        else:
            rep = mdf[["Employee", "Department", "Score", "Rating"]].copy()
            x, y = "Employee", "Score"
        
        if chart_type == "Bar":
            fig = px.bar(rep, x=x, y=y, color=y, color_continuous_scale="Viridis", text=y)
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        elif chart_type == "Line":
            fig = px.line(rep, x=x, y=y, markers=True)
        else:
            fig = px.pie(rep, values=y, names=x)
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.dataframe(rep, use_container_width=True, hide_index=True)
        
        csv = rep.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download", csv,
                          f"report_{sel_month}.csv", "text/csv")
    else:
        st.info("📌 No data for reports")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# EMPLOYEES
# ============================================================
if menu == "Employees":
    if not require_auth("manager"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👥 Employees")
    
    tab1, tab2 = st.tabs(["➕ Add", "📋 Manage"])
    
    with tab1:
        st.markdown("### Add Employee")
        
        with st.form("add_emp"):
            col1, col2 = st.columns(2)
            
            with col1:
                emp_name = st.text_input("Name", placeholder="Full name")
            
            with col2:
                if user_role == "admin":
                    emp_dept = st.selectbox("Department", get_active_departments())
                else:
                    emp_dept = user_department
                    st.info(f"Dept: **{user_department}**")
            
            emp_active = st.checkbox("Active", value=True)
            submit = st.form_submit_button("➕ Add", use_container_width=True, type="primary")
            
            if submit:
                if emp_name.strip() and emp_dept:
                    result = execute_query("""
                        INSERT INTO employees (employee_name, department, is_active, created_at)
                        VALUES (%s, %s, %s, %s)
                    """, [emp_name.strip(), emp_dept, emp_active, datetime.now()])
                    
                    if result:
                        log_action(username, "ADD_EMPLOYEE", emp_name)
                        st.success(f"✅ Added '{emp_name}'!")
                        st.rerun()
                    else:
                        st.error("❌ Already exists or error")
                else:
                    st.error("⚠️ Enter name and select dept")
    
    with tab2:
        st.markdown("### Manage Employees")
        
        emps = get_all_employees()
        if user_role == "manager":
            emps = [e for e in emps if e[2] == user_department]
        
        if emps:
            emp_df = pd.DataFrame(emps, columns=["ID", "Name", "Dept", "Active", "Created"])
            emp_df["Status"] = emp_df["Active"].apply(lambda x: "✅" if x else "❌")
            st.dataframe(emp_df[["Name", "Dept", "Status", "Created"]], 
                        use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### ✏️ Edit")
            
            emp_sel = st.selectbox("Select", [e[1] for e in emps])
            
            if emp_sel:
                emp_data = [e for e in emps if e[1] == emp_sel][0]
                emp_id, emp_name, emp_dept, emp_active, _ = emp_data
                
                col1, col2 = st.columns(2)
                
                with col1:
                    new_name = st.text_input("Name", value=emp_name, key="en")
                    
                    if user_role == "admin":
                        depts = get_active_departments()
                        new_dept = st.selectbox("Dept", depts, 
                                               index=depts.index(emp_dept) if emp_dept in depts else 0,
                                               key="ed")
                    else:
                        new_dept = emp_dept
                        st.info(f"Dept: **{emp_dept}**")
                
                with col2:
                    new_active = st.checkbox("Active", value=emp_active, key="ea")
                    st.info(f"**Status:** {'✅' if emp_active else '❌'}")
                
                col_b1, col_b2 = st.columns(2)
                
                with col_b1:
                    if st.button("💾 Update", use_container_width=True, type="primary"):
                        execute_query("""
                            UPDATE employees 
                            SET employee_name=%s, department=%s, is_active=%s, updated_at=%s
                            WHERE id=%s
                        """, [new_name.strip(), new_dept, new_active, datetime.now(), emp_id])
                        
                        log_action(username, "UPDATE_EMPLOYEE", new_name)
                        st.success("✅ Updated!")
                        st.rerun()
                
                with col_b2:
                    if st.button("🗑️ Delete", use_container_width=True) and user_role == "admin":
                        entries = execute_query("SELECT COUNT(*) FROM kpi_entries WHERE employee_name=%s", 
                                              [emp_name], fetch_one=True)
                        if entries and entries[0] > 0:
                            st.error(f"⚠️ Cannot delete! {entries[0]} entries exist")
                        else:
                            execute_query("DELETE FROM employees WHERE id=%s", [emp_id])
                            log_action(username, "DELETE_EMPLOYEE", emp_name)
                            st.success("🗑️ Deleted!")
                            st.rerun()
        else:
            st.info("📌 No employees. Add using 'Add' tab")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# DEPARTMENTS (Admin only)
# ============================================================
if menu == "Departments":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🏢 Departments")
    
    tab1, tab2 = st.tabs(["➕ Add", "📋 Manage"])
    
    with tab1:
        st.markdown("### Add Department")
        
        with st.form("add_dept"):
            dept_name = st.text_input("Name", placeholder="e.g., Fabric, Dyeing")
            dept_active = st.checkbox("Active", value=True)
            submit = st.form_submit_button("➕ Add", use_container_width=True, type="primary")
            
            if submit:
                if dept_name.strip():
                    # Check for duplicates (case-insensitive)
                    existing = execute_query(
                        "SELECT department_name FROM departments WHERE LOWER(department_name) = LOWER(%s)", 
                        [dept_name.strip()], fetch_one=True
                    )
                    
                    if existing:
                        st.error(f"❌ Department '{dept_name}' already exists!")
                    else:
                        result = execute_query("""
                            INSERT INTO departments (department_name, is_active, created_at)
                            VALUES (%s, %s, %s)
                        """, [dept_name.strip(), dept_active, datetime.now()])
                        
                        if result:
                            log_action(username, "ADD_DEPARTMENT", dept_name)
                            st.success(f"✅ Added '{dept_name}'!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Error occurred")
                else:
                    st.error("⚠️ Enter department name")
    
    with tab2:
        st.markdown("### Manage Departments")
        
        depts = get_all_departments()
        
        if depts:
            dept_df = pd.DataFrame(depts, columns=["ID", "Name", "Active", "Created"])
            dept_df["Status"] = dept_df["Active"].apply(lambda x: "✅" if x else "❌")
            
            # Count employees
            for idx, row in dept_df.iterrows():
                emp_count = execute_query("SELECT COUNT(*) FROM employees WHERE department=%s", 
                                         [row["Name"]], fetch_one=True)
                dept_df.at[idx, "Employees"] = emp_count[0] if emp_count else 0
            
            st.dataframe(dept_df[["Name", "Status", "Employees", "Created"]], 
                        use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### ✏️ Edit")
            
            dept_sel = st.selectbox("Select", [d[1] for d in depts])
            
            if dept_sel:
                dept_data = [d for d in depts if d[1] == dept_sel][0]
                dept_id, dept_name, dept_active, _ = dept_data
                
                col1, col2 = st.columns(2)
                
                with col1:
                    new_dept_name = st.text_input("Name", value=dept_name, key="dn")
                
                with col2:
                    new_dept_active = st.checkbox("Active", value=dept_active, key="da")
                    st.info(f"**Status:** {'✅' if dept_active else '❌'}")
                
                col_b1, col_b2 = st.columns(2)
                
                with col_b1:
                    if st.button("💾 Update", use_container_width=True, type="primary"):
                        # Check for duplicate names (excluding current)
                        existing = execute_query(
                            "SELECT department_name FROM departments WHERE LOWER(department_name) = LOWER(%s) AND id != %s", 
                            [new_dept_name.strip(), dept_id], fetch_one=True
                        )
                        
                        if existing:
                            st.error(f"❌ Name '{new_dept_name}' already exists!")
                        else:
                            execute_query("""
                                UPDATE departments 
                                SET department_name=%s, is_active=%s
                                WHERE id=%s
                            """, [new_dept_name.strip(), new_dept_active, dept_id])
                            
                            log_action(username, "UPDATE_DEPARTMENT", f"{dept_name} → {new_dept_name}")
                            st.success("✅ Updated!")
                            st.rerun()
                
                with col_b2:
                    if st.button("🗑️ Delete", use_container_width=True):
                        emp_count = execute_query("SELECT COUNT(*) FROM employees WHERE department=%s", 
                                                [dept_name], fetch_one=True)
                        if emp_count and emp_count[0] > 0:
                            st.error(f"⚠️ Cannot delete! {emp_count[0]} employees in this dept")
                        else:
                            execute_query("DELETE FROM departments WHERE id=%s", [dept_id])
                            log_action(username, "DELETE_DEPARTMENT", dept_name)
                            st.success("🗑️ Deleted!")
                            st.rerun()
        else:
            st.info("📌 No departments. Add using 'Add' tab")
            if st.button("🔄 Re-initialize Sample Departments"):
                for dept_name in ["Fabric", "Dyeing", "Quality Control", "Production", "Finishing", "Stitching"]:
                    execute_query("""
                        INSERT INTO departments (department_name, is_active, created_at)
                        VALUES (%s, %s, %s) ON CONFLICT (department_name) DO NOTHING
                    """, [dept_name, True, datetime.now()])
                st.success("✅ Sample departments added!")
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# USERS (Admin only)
# ============================================================
if menu == "Users":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👨‍💼 Users")
    
    tab1, tab2 = st.tabs(["➕ Create", "📋 Manage"])
    
    with tab1:
        st.markdown("### Create User")
        
        with st.form("add_user"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username", placeholder="e.g., john.doe")
                new_password = st.text_input("Password", type="password", placeholder="Min 6 chars")
                new_password2 = st.text_input("Confirm", type="password")
            
            with col2:
                new_fullname = st.text_input("Full Name", placeholder="e.g., John Doe")
                new_role = st.selectbox("Role", ["employee", "manager", "admin"])
                
                if new_role in ["employee", "manager"]:
                    active_emps = get_active_employees()
                    emp_list = [e[0] for e in active_emps]
                    new_emp_name = st.selectbox("Link Employee", [""] + emp_list)
                    
                    if new_emp_name:
                        emp_dept = [e[1] for e in active_emps if e[0] == new_emp_name]
                        new_dept = emp_dept[0] if emp_dept else ""
                        st.info(f"Dept: **{new_dept}**")
                    else:
                        new_dept = ""
                else:
                    new_emp_name = ""
                    new_dept = ""
            
            new_active = st.checkbox("Active", value=True)
            submit = st.form_submit_button("➕ Create", use_container_width=True, type="primary")
            
            if submit:
                if not new_username or not new_password or not new_fullname:
                    st.error("⚠️ All fields required")
                elif len(new_password) < 6:
                    st.error("⚠️ Password min 6 chars")
                elif new_password != new_password2:
                    st.error("⚠️ Passwords don't match")
                else:
                    hashed, salt = hash_password(new_password)
                    result = execute_query("""
                        INSERT INTO users (username, password_hash, password_salt, full_name, role,
                                         employee_name, department, is_active, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [new_username, hashed, salt, new_fullname, new_role, 
                         new_emp_name or None, new_dept or None, new_active, username])
                    
                    if result:
                        log_action(username, "CREATE_USER", f"{new_username} ({new_role})")
                        st.success(f"✅ User '{new_username}' created!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Username exists")
    
    with tab2:
        st.markdown("### Manage Users")
        
        users = execute_query("""
            SELECT username, full_name, role, employee_name, department, is_active, last_login
            FROM users 
            WHERE username != 'admin'
            ORDER BY created_at DESC
        """, fetch=True) or []
        
        if users:
            user_df = pd.DataFrame(users, columns=["Username", "Name", "Role", "Employee", 
                                                   "Dept", "Active", "Last Login"])
            user_df["Status"] = user_df["Active"].apply(lambda x: "✅" if x else "❌")
            
            st.dataframe(user_df[["Username", "Name", "Role", "Employee", "Dept", "Status", "Last Login"]], 
                        use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### ✏️ Edit User")
            
            user_sel = st.selectbox("Select", [u[0] for u in users])
            
            if user_sel:
                user_data = [u for u in users if u[0] == user_sel][0]
                uname, ufull, urole, uemp, udept, uactive, ulast = user_data
                
                col1, col2 = st.columns(2)
                
                with col1:
                    edit_fullname = st.text_input("Full Name", value=ufull, key="uf")
                    edit_role = st.selectbox("Role", ["employee", "manager", "admin"],
                                            index=["employee", "manager", "admin"].index(urole), key="ur")
                
                with col2:
                    edit_active = st.checkbox("Active", value=uactive, key="ua")
                    st.info(f"**Last:** {ulast if ulast else 'Never'}")
                    
                    st.markdown("#### 🔒 Reset Password")
                    new_pwd = st.text_input("New (optional)", type="password", key="up")
                    new_pwd2 = st.text_input("Confirm", type="password", key="up2")
                
                col_b1, col_b2 = st.columns(2)
                
                with col_b1:
                    if st.button("💾 Update", use_container_width=True, type="primary"):
                        execute_query("""
                            UPDATE users 
                            SET full_name=%s, role=%s, is_active=%s
                            WHERE username=%s
                        """, [edit_fullname, edit_role, edit_active, uname])
                        
                        if new_pwd:
                            if len(new_pwd) >= 6 and new_pwd == new_pwd2:
                                hashed, salt = hash_password(new_pwd)
                                execute_query("UPDATE users SET password_hash=%s, password_salt=%s WHERE username=%s",
                                             [hashed, salt, uname])
                                log_action(username, "RESET_PASSWORD", uname)
                            else:
                                st.error("⚠️ Password 6+ chars and match")
                        
                        log_action(username, "UPDATE_USER", uname)
                        st.success("✅ Updated!")
                        st.rerun()
                
                with col_b2:
                    if st.button("🗑️ Delete", use_container_width=True):
                        execute_query("DELETE FROM users WHERE username=%s", [uname])
                        log_action(username, "DELETE_USER", uname)
                        st.success("🗑️ Deleted!")
                        st.rerun()
        else:
            st.info("📌 No users. Create using 'Create' tab")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# AUDIT LOG (Admin only)
# ============================================================
if menu == "Audit Log":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 Audit Trail")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        all_users = execute_query("SELECT DISTINCT username FROM audit_log ORDER BY username", fetch=True) or []
        user_list = [u[0] for u in all_users]
        filter_user = st.selectbox("User", ["All"] + user_list)
    
    with col2:
        all_actions = execute_query("SELECT DISTINCT action FROM audit_log ORDER BY action", fetch=True) or []
        action_list = [a[0] for a in all_actions]
        filter_action = st.selectbox("Action", ["All"] + action_list)
    
    with col3:
        limit = st.selectbox("Records", [50, 100, 200, 500], index=1)
    
    audit_q = "SELECT username, action, details, timestamp FROM audit_log WHERE 1=1"
    audit_p = []
    
    if filter_user != "All":
        audit_q += " AND username=%s"
        audit_p.append(filter_user)
    
    if filter_action != "All":
        audit_q += " AND action=%s"
        audit_p.append(filter_action)
    
    audit_q += f" ORDER BY timestamp DESC LIMIT {limit}"
    
    logs = execute_query(audit_q, audit_p, fetch=True) or []
    
    if logs:
        st.markdown("---")
        log_df = pd.DataFrame(logs, columns=["User", "Action", "Details", "Time"])
        st.dataframe(log_df, use_container_width=True, hide_index=True)
        
        csv = log_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export", csv,
                          f"audit_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
    else:
        st.info("📌 No logs")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# SETTINGS (Admin only)
# ============================================================
if menu == "Settings":
    if not require_auth("admin"):
        st.stop()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚙️ Settings")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Labels", "⚖️ Weights", "⭐ Ratings", "🔧 System"])
    
    with tab1:
        st.markdown("### KPI Labels")
        k1, k2, k3, k4 = get_kpi_labels()
        
        col1, col2 = st.columns(2)
        
        with col1:
            n1 = st.text_input("KPI 1", value=k1, key="kl1")
            n2 = st.text_input("KPI 2", value=k2, key="kl2")
        
        with col2:
            n3 = st.text_input("KPI 3", value=k3, key="kl3")
            n4 = st.text_input("KPI 4", value=k4, key="kl4")
        
        if st.button("💾 Save Labels", use_container_width=True, type="primary"):
            execute_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi1'", [n1.strip() or "KPI 1"])
            execute_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi2'", [n2.strip() or "KPI 2"])
            execute_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi3'", [n3.strip() or "KPI 3"])
            execute_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi4'", [n4.strip() or "KPI 4"])
            log_action(username, "UPDATE_LABELS", "Labels updated")
            st.success("✅ Saved!")
            st.rerun()
    
    with tab2:
        st.markdown("### KPI Weights (Must total 100%)")
        w1, w2, w3, w4 = get_kpi_weights()
        
        col1, col2 = st.columns(2)
        
        with col1:
            nw1 = st.number_input(f"{kpi1_lbl}", 0, 100, w1, key="w1")
            nw2 = st.number_input(f"{kpi2_lbl}", 0, 100, w2, key="w2")
        
        with col2:
            nw3 = st.number_input(f"{kpi3_lbl}", 0, 100, w3, key="w3")
            nw4 = st.number_input(f"{kpi4_lbl}", 0, 100, w4, key="w4")
        
        total = nw1 + nw2 + nw3 + nw4
        
        if total == 100:
            st.success(f"✅ Total: {total}%")
        else:
            st.error(f"❌ Total: {total}% (Must be 100%)")
        
        if st.button("💾 Save Weights", use_container_width=True, type="primary"):
            if total == 100:
                execute_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi1'", [nw1])
                execute_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi2'", [nw2])
                execute_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi3'", [nw3])
                execute_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi4'", [nw4])
                log_action(username, "UPDATE_WEIGHTS", f"{nw1},{nw2},{nw3},{nw4}")
                st.success("✅ Saved!")
                st.rerun()
            else:
                st.error("⚠️ Total must be 100%")
    
    with tab3:
        st.markdown("### Rating Rules")
        ex, gd, av = get_rating_rules()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nex = st.number_input("🌟 Excellent Min", 0, 100, ex, key="rex")
        with col2:
            ngd = st.number_input("👍 Good Min", 0, 100, gd, key="rgd")
        with col3:
            nav = st.number_input("📊 Average Min", 0, 100, av, key="rav")
        
        st.info(f"""
        **Logic:**
        - Score ≥ {nex} → 🌟 Excellent
        - Score ≥ {ngd} → 👍 Good
        - Score ≥ {nav} → 📊 Average
        - Score < {nav} → ⚠️ Needs Improvement
        """)
        
        if st.button("💾 Save Rules", use_container_width=True, type="primary"):
            if nex >= ngd >= nav:
                execute_query("""
                    UPDATE rating_rules 
                    SET excellent_min=%s, good_min=%s, average_min=%s 
                    WHERE id=1
                """, [nex, ngd, nav])
                log_action(username, "UPDATE_RATINGS", f"{nex},{ngd},{nav}")
                st.success("✅ Saved!")
                st.rerun()
            else:
                st.error("⚠️ Must be: Excellent ≥ Good ≥ Average")
    
    with tab4:
        st.markdown("### System")
        
        cur_import = get_setting("allow_import", "1") == "1"
        cur_edit = get_setting("allow_edit_delete", "1") == "1"
        
        col1, col2 = st.columns(2)
        
        with col1:
            allow_import = st.checkbox("📤 CSV Import", value=cur_import)
        
        with col2:
            allow_edit = st.checkbox("✏️ Edit/Delete", value=cur_edit)
        
        if st.button("💾 Save System", use_container_width=True, type="primary"):
            set_setting("allow_import", "1" if allow_import else "0")
            set_setting("allow_edit_delete", "1" if allow_edit else "0")
            log_action(username, "UPDATE_SYSTEM", f"Import:{allow_import}, Edit:{allow_edit}")
            st.success("✅ Saved!")
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 System Info")
        
        total_users = len(execute_query("SELECT id FROM users", fetch=True) or [])
        total_emps = len(execute_query("SELECT id FROM employees", fetch=True) or [])
        total_depts = len(execute_query("SELECT id FROM departments", fetch=True) or [])
        total_entries = len(execute_query("SELECT id FROM kpi_entries", fetch=True) or [])
        
        col_i1, col_i2, col_i3, col_i4 = st.columns(4)
        col_i1.metric("👥 Users", total_users)
        col_i2.metric("👤 Employees", total_emps)
        col_i3.metric("🏢 Departments", total_depts)
        col_i4.metric("📝 Entries", total_entries)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="card" style="text-align:center">', unsafe_allow_html=True)
st.markdown(f"""
<div class='small'>
    <b>Yash Gallery KPI System v4.0 - Data Persistence Edition</b><br>
    👤 {full_name} ({user_role.upper()}) | 🕒 Active Session<br>
    💾 Permanent Storage • 🔐 Secure • 👥 Multi-User • 📈 Real-Time<br>
    © 2024 Yash Gallery | Built with Streamlit + PostgreSQL (Neon)<br>
    ✅ Data Persists Forever • 🔄 Refresh-Safe • 📈 Production Ready
</div>
""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
