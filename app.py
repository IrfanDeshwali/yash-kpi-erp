 1	import streamlit as st
     2	import psycopg2
     3	import pandas as pd
     4	import plotly.express as px
     5	import plotly.graph_objects as go
     6	from datetime import datetime
     7	from streamlit_option_menu import option_menu
     8	import hashlib
     9	import secrets
    10	
    11	# ============================================================
    12	# PAGE CONFIGURATION
    13	# ============================================================
    14	st.set_page_config(
    15	    page_title="Yash Gallery – KPI System",
    16	    page_icon="📊",
    17	    layout="wide",
    18	    initial_sidebar_state="expanded"
    19	)
    20	
    21	# ============================================================
    22	# CSS STYLING
    23	# ============================================================
    24	st.markdown("""
    25	<style>
    26	.block-container{padding-top:1rem}
    27	.card{
    28	  background:#fff;border:1px solid #e5e7eb;border-radius:16px;
    29	  padding:14px 16px;box-shadow:0 6px 18px rgba(15,23,42,0.06);
    30	  margin-bottom:1rem;
    31	}
    32	.small{color:#64748b;font-size:12px}
    33	.badge{
    34	  display:inline-block;padding:2px 10px;border-radius:999px;
    35	  border:1px solid #e5e7eb;background:#f8fafc;font-size:12px;color:#334155;
    36	  margin:2px;
    37	}
    38	.badge-success{background:#dcfce7;color:#166534;border-color:#86efac}
    39	.badge-danger{background:#fee2e2;color:#991b1b;border-color:#fca5a5}
    40	.badge-warning{background:#fef3c7;color:#92400e;border-color:#fcd34d}
    41	.badge-info{background:#dbeafe;color:#1e40af;border-color:#93c5fd}
    42	.hline{height:1px;background:#e5e7eb;margin:10px 0}
    43	.login-container{
    44	  max-width:420px;margin:80px auto;padding:40px;
    45	  background:white;border-radius:20px;
    46	  box-shadow:0 20px 60px rgba(0,0,0,0.15);
    47	}
    48	.role-badge-admin{
    49	  background:#dc2626;color:white;padding:6px 14px;
    50	  border-radius:12px;font-weight:bold;font-size:11px;
    51	}
    52	.role-badge-manager{
    53	  background:#2563eb;color:white;padding:6px 14px;
    54	  border-radius:12px;font-weight:bold;font-size:11px;
    55	}
    56	.role-badge-employee{
    57	  background:#16a34a;color:white;padding:6px 14px;
    58	  border-radius:12px;font-weight:bold;font-size:11px;
    59	}
    60	.metric-card{
    61	  padding:20px;border-radius:12px;background:#f8fafc;
    62	  border:2px solid #e5e7eb;text-align:center;
    63	}
    64	.performance-box{
    65	  padding:12px;border-radius:8px;margin:8px 0;
    66	  font-weight:500;
    67	}
    68	</style>
    69	""", unsafe_allow_html=True)
    70	
    71	# ============================================================
    72	# DATABASE CONNECTION & QUERY FUNCTIONS
    73	# ============================================================
    74	@st.cache_resource
    75	def init_connection():
    76	    """Initialize PostgreSQL connection"""
    77	    try:
    78	        conn = psycopg2.connect(
    79	            st.secrets["NEON_DATABASE_URL"],
    80	            connect_timeout=10,
    81	            keepalives=1,
    82	            keepalives_idle=30,
    83	            keepalives_interval=10,
    84	            keepalives_count=5,
    85	        )
    86	        return conn
    87	    except Exception as e:
    88	        st.error(f"❌ Database connection failed: {str(e)}")
    89	        st.stop()
    90	
    91	def get_conn():
    92	    """Get or refresh database connection"""
    93	    if "db_conn" not in st.session_state or st.session_state.db_conn.closed:
    94	        st.session_state.db_conn = init_connection()
    95	    return st.session_state.db_conn
    96	
    97	def run_query(query, params=None, fetch=False):
    98	    """Execute a single query"""
    99	    conn = get_conn()
   100	    try:
   101	        with conn.cursor() as cur:
   102	            cur.execute(query, params or [])
   103	            if fetch:
   104	                return cur.fetchall()
   105	            conn.commit()
   106	            return None
   107	    except psycopg2.OperationalError:
   108	        st.session_state.db_conn = init_connection()
   109	        return run_query(query, params, fetch)
   110	    except Exception as e:
   111	        conn.rollback()
   112	        st.error(f"Database error: {str(e)}")
   113	        return None if fetch else False
   114	
   115	def run_many(query, data):
   116	    """Execute batch insert"""
   117	    conn = get_conn()
   118	    try:
   119	        with conn.cursor() as cur:
   120	            cur.executemany(query, data)
   121	            conn.commit()
   122	            return True
   123	    except Exception as e:
   124	        conn.rollback()
   125	        st.error(f"Batch insert error: {str(e)}")
   126	        return False
   127	
   128	# ============================================================
   129	# PASSWORD HASHING FUNCTIONS
   130	# ============================================================
   131	def hash_password(password: str, salt: str = None) -> tuple:
   132	    """Hash password with salt using SHA-256"""
   133	    if salt is None:
   134	        salt = secrets.token_hex(16)
   135	    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
   136	    return hashed, salt
   137	
   138	def verify_password(password: str, hashed: str, salt: str) -> bool:
   139	    """Verify password against stored hash"""
   140	    test_hash, _ = hash_password(password, salt)
   141	    return test_hash == hashed
   142	
   143	# ============================================================
   144	# DATABASE INITIALIZATION
   145	# ============================================================
   146	def initialize_database():
   147	    """Create all tables and insert default data"""
   148	    
   149	    # Drop existing tables (fresh start)
   150	    run_query("""
   151	        DROP TABLE IF EXISTS audit_log, kpi_entries, users, employees, 
   152	        departments, app_settings, kpi_master, kpi_weights, rating_rules CASCADE
   153	    """)
   154	    
   155	    # Create departments table
   156	    run_query("""
   157	        CREATE TABLE departments (
   158	            id SERIAL PRIMARY KEY,
   159	            department_name TEXT UNIQUE NOT NULL,
   160	            is_active BOOLEAN DEFAULT TRUE,
   161	            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   162	        )
   163	    """)
   164	    
   165	    # Create employees table
   166	    run_query("""
   167	        CREATE TABLE employees (
   168	            id SERIAL PRIMARY KEY,
   169	            employee_name TEXT UNIQUE NOT NULL,
   170	            department TEXT NOT NULL,
   171	            is_active BOOLEAN DEFAULT TRUE,
   172	            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   173	            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   174	        )
   175	    """)
   176	    
   177	    # Create users table
   178	    run_query("""
   179	        CREATE TABLE users (
   180	            id SERIAL PRIMARY KEY,
   181	            username TEXT UNIQUE NOT NULL,
   182	            password_hash TEXT NOT NULL,
   183	            password_salt TEXT NOT NULL,
   184	            full_name TEXT NOT NULL,
   185	            role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'employee')),
   186	            employee_name TEXT,
   187	            department TEXT,
   188	            is_active BOOLEAN DEFAULT TRUE,
   189	            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   190	            last_login TIMESTAMP,
   191	            created_by TEXT
   192	        )
   193	    """)
   194	    
   195	    # Create kpi_entries table
   196	    run_query("""
   197	        CREATE TABLE kpi_entries (
   198	            id SERIAL PRIMARY KEY,
   199	            employee_name TEXT NOT NULL,
   200	            department TEXT NOT NULL,
   201	            kpi1 INTEGER,
   202	            kpi2 INTEGER,
   203	            kpi3 INTEGER,
   204	            kpi4 INTEGER,
   205	            total_score DOUBLE PRECISION,
   206	            rating TEXT,
   207	            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   208	            entry_month TEXT,
   209	            created_by TEXT,
   210	            updated_by TEXT,
   211	            updated_at TIMESTAMP
   212	        )
   213	    """)
   214	    
   215	    # Create audit_log table
   216	    run_query("""
   217	        CREATE TABLE audit_log (
   218	            id SERIAL PRIMARY KEY,
   219	            username TEXT NOT NULL,
   220	            action TEXT NOT NULL,
   221	            details TEXT,
   222	            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   223	        )
   224	    """)
   225	    
   226	    # Create app_settings table
   227	    run_query("""
   228	        CREATE TABLE app_settings (
   229	            key TEXT PRIMARY KEY,
   230	            value TEXT NOT NULL
   231	        )
   232	    """)
   233	    
   234	    # Create kpi_master table
   235	    run_query("""
   236	        CREATE TABLE kpi_master (
   237	            kpi_key TEXT PRIMARY KEY,
   238	            kpi_label TEXT NOT NULL
   239	        )
   240	    """)
   241	    
   242	    # Create kpi_weights table
   243	    run_query("""
   244	        CREATE TABLE kpi_weights (
   245	            kpi_key TEXT PRIMARY KEY,
   246	            weight INTEGER NOT NULL
   247	        )
   248	    """)
   249	    
   250	    # Create rating_rules table
   251	    run_query("""
   252	        CREATE TABLE rating_rules (
   253	            id INTEGER PRIMARY KEY DEFAULT 1,
   254	            excellent_min INTEGER NOT NULL,
   255	            good_min INTEGER NOT NULL,
   256	            average_min INTEGER NOT NULL
   257	        )
   258	    """)
   259	    
   260	    # Insert default app settings
   261	    default_settings = [
   262	        ("allow_import", "1"),
   263	        ("allow_edit_delete", "1"),
   264	        ("session_timeout", "30")
   265	    ]
   266	    run_many("INSERT INTO app_settings(key, value) VALUES (%s,%s) ON CONFLICT (key) DO NOTHING", default_settings)
   267	    
   268	    # Insert default KPI labels
   269	    default_kpi_labels = [
   270	        ("kpi1", "Quality"),
   271	        ("kpi2", "Productivity"),
   272	        ("kpi3", "Attendance"),
   273	        ("kpi4", "Behavior")
   274	    ]
   275	    run_many("INSERT INTO kpi_master(kpi_key, kpi_label) VALUES (%s,%s) ON CONFLICT (kpi_key) DO NOTHING", default_kpi_labels)
   276	    
   277	    # Insert default KPI weights
   278	    default_weights = [
   279	        ("kpi1", 25),
   280	        ("kpi2", 25),
   281	        ("kpi3", 25),
   282	        ("kpi4", 25)
   283	    ]
   284	    run_many("INSERT INTO kpi_weights(kpi_key, weight) VALUES (%s,%s) ON CONFLICT (kpi_key) DO NOTHING", default_weights)
   285	    
   286	    # Insert default rating rules
   287	    run_query("INSERT INTO rating_rules(id, excellent_min, good_min, average_min) VALUES (1, 80, 60, 40) ON CONFLICT (id) DO NOTHING")
   288	    
   289	    # Create default admin user
   290	    admin_check = run_query("SELECT id FROM users WHERE username='admin'", fetch=True)
   291	    if not admin_check:
   292	        hashed, salt = hash_password("admin123")
   293	        run_query("""
   294	            INSERT INTO users (username, password_hash, password_salt, full_name, role, is_active, created_by)
   295	            VALUES (%s, %s, %s, %s, %s, %s, %s)
   296	        """, ["admin", hashed, salt, "System Administrator", "admin", True, "system"])
   297	    
   298	    # Insert sample departments
   299	    sample_departments = [
   300	        ("Fabric", True),
   301	        ("Dyeing", True),
   302	        ("Quality Control", True),
   303	        ("Production", True),
   304	        ("Finishing", True),
   305	        ("Stitching", True)
   306	    ]
   307	    run_many("INSERT INTO departments (department_name, is_active) VALUES (%s, %s) ON CONFLICT (department_name) DO NOTHING", 
   308	             sample_departments)
   309	    
   310	    return True
   311	
   312	# Initialize database on first run
   313	if "db_initialized" not in st.session_state:
   314	    with st.spinner("🔄 Initializing database... Please wait..."):
   315	        if initialize_database():
   316	            st.session_state.db_initialized = True
   317	            st.success("✅ Database initialized successfully!")
   318	
   319	# ============================================================
   320	# AUDIT LOG FUNCTION
   321	# ============================================================
   322	def log_action(username: str, action: str, details: str = ""):
   323	    """Log user actions for audit trail"""
   324	    run_query("""
   325	        INSERT INTO audit_log (username, action, details, timestamp)
   326	        VALUES (%s, %s, %s, %s)
   327	    """, [username, action, details, datetime.now()])
   328	
   329	# ============================================================
   330	# HELPER FUNCTIONS
   331	# ============================================================
   332	def get_setting(key, default=""):
   333	    """Get app setting value"""
   334	    r = run_query("SELECT value FROM app_settings WHERE key=%s", [key], fetch=True)
   335	    return r[0][0] if r else default
   336	
   337	def set_setting(key, value):
   338	    """Set app setting value"""
   339	    run_query("""
   340	        INSERT INTO app_settings(key, value)
   341	        VALUES (%s,%s)
   342	        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
   343	    """, [key, value])
   344	
   345	def get_kpi_labels():
   346	    """Get KPI label names"""
   347	    rows = run_query("SELECT kpi_key, kpi_label FROM kpi_master ORDER BY kpi_key", fetch=True) or []
   348	    d = {k:v for k,v in rows}
   349	    return d.get("kpi1","KPI 1"), d.get("kpi2","KPI 2"), d.get("kpi3","KPI 3"), d.get("kpi4","KPI 4")
   350	
   351	def get_kpi_weights():
   352	    """Get KPI weights"""
   353	    rows = run_query("SELECT kpi_key, weight FROM kpi_weights ORDER BY kpi_key", fetch=True) or []
   354	    d = {k:int(w) for k,w in rows}
   355	    return d.get("kpi1",25), d.get("kpi2",25), d.get("kpi3",25), d.get("kpi4",25)
   356	
   357	def get_rating_rules():
   358	    """Get rating threshold rules"""
   359	    r = run_query("SELECT excellent_min, good_min, average_min FROM rating_rules WHERE id=1", fetch=True)
   360	    return (int(r[0][0]), int(r[0][1]), int(r[0][2])) if r else (80, 60, 40)
   361	
   362	def calc_weighted_score(k1, k2, k3, k4):
   363	    """Calculate weighted KPI score"""
   364	    w1, w2, w3, w4 = get_kpi_weights()
   365	    return round((k1*w1 + k2*w2 + k3*w3 + k4*w4) / 100.0, 2)
   366	
   367	def calc_rating(score: float):
   368	    """Calculate rating based on score"""
   369	    ex, gd, av = get_rating_rules()
   370	    if score >= ex: return "Excellent"
   371	    if score >= gd: return "Good"
   372	    if score >= av: return "Average"
   373	    return "Needs Improvement"
   374	
   375	def get_active_employees():
   376	    """Get list of active employees"""
   377	    return run_query("SELECT employee_name, department FROM employees WHERE is_active=TRUE ORDER BY employee_name", fetch=True) or []
   378	
   379	def get_all_employees():
   380	    """Get all employees"""
   381	    return run_query("SELECT id, employee_name, department, is_active, created_at FROM employees ORDER BY employee_name", fetch=True) or []
   382	
   383	def get_active_departments():
   384	    """Get list of active departments"""
   385	    rows = run_query("SELECT department_name FROM departments WHERE is_active=TRUE ORDER BY department_name", fetch=True) or []
   386	    return [r[0] for r in rows]
   387	
   388	def get_all_departments():
   389	    """Get all departments"""
   390	    return run_query("SELECT id, department_name, is_active, created_at FROM departments ORDER BY department_name", fetch=True) or []
   391	
   392	# ============================================================
   393	# AUTHENTICATION FUNCTIONS
   394	# ============================================================
   395	def authenticate_user(username: str, password: str) -> dict:
   396	    """Authenticate user and return user info"""
   397	    user = run_query("""
   398	        SELECT id, username, password_hash, password_salt, full_name, role, 
   399	               employee_name, department, is_active 
   400	        FROM users WHERE username=%s
   401	    """, [username], fetch=True)
   402	    
   403	    if not user:
   404	        return {"success": False, "message": "❌ Invalid username or password"}
   405	    
   406	    user_id, uname, pwd_hash, pwd_salt, full_name, role, emp_name, dept, is_active = user[0]
   407	    
   408	    if not is_active:
   409	        return {"success": False, "message": "⚠️ Account is inactive. Contact administrator."}
   410	    
   411	    if not verify_password(password, pwd_hash, pwd_salt):
   412	        return {"success": False, "message": "❌ Invalid username or password"}
   413	    
   414	    # Update last login
   415	    run_query("UPDATE users SET last_login=%s WHERE id=%s", [datetime.now(), user_id])
   416	    log_action(username, "LOGIN", "User logged in successfully")
   417	    
   418	    return {
   419	        "success": True,
   420	        "user_id": user_id,
   421	        "username": uname,
   422	        "full_name": full_name,
   423	        "role": role,
   424	        "employee_name": emp_name,
   425	        "department": dept
   426	    }
   427	
   428	def check_permission(required_role: str) -> bool:
   429	    """Check if current user has required permission"""
   430	    if "user" not in st.session_state:
   431	        return False
   432	    user_role = st.session_state["user"]["role"]
   433	    role_levels = {"admin": 3, "manager": 2, "employee": 1}
   434	    return role_levels.get(user_role, 0) >= role_levels.get(required_role, 0)
   435	
   436	def require_auth(required_role: str = "employee"):
   437	    """Require authentication with specific role"""
   438	    if "user" not in st.session_state:
   439	        return False
   440	    if not check_permission(required_role):
   441	        st.error(f"⛔ Access Denied: {required_role.upper()} role required")
   442	        return False
   443	    return True
   444	
   445	# ============================================================
   446	# LOGIN PAGE
   447	# ============================================================
   448	def show_login_page():
   449	    """Display login page"""
   450	    st.markdown('<div class="login-container">', unsafe_allow_html=True)
   451	    st.markdown("## 🔐 Yash Gallery KPI System")
   452	    st.markdown("### Welcome Back!")
   453	    st.markdown("---")
   454	    
   455	    with st.form("login_form", clear_on_submit=False):
   456	        username = st.text_input("👤 Username", placeholder="Enter your username", key="login_user")
   457	        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_pass")
   458	        
   459	        col1, col2 = st.columns(2)
   460	        submit = col1.form_submit_button("🚀 Login", use_container_width=True)
   461	        clear = col2.form_submit_button("❌ Clear", use_container_width=True)
   462	        
   463	        if submit:
   464	            if username and password:
   465	                result = authenticate_user(username, password)
   466	                if result["success"]:
   467	                    st.session_state["user"] = result
   468	                    st.session_state["logged_in"] = True
   469	                    st.success(f"✅ Welcome, {result['full_name']}!")
   470	                    st.balloons()
   471	                    st.rerun()
   472	                else:
   473	                    st.error(result["message"])
   474	            else:
   475	                st.error("⚠️ Please enter both username and password")
   476	    
   477	    st.markdown("---")
   478	    st.markdown("""
   479	    <div class='small' style='text-align:center'>
   480	        <b>🔑 Default Login Credentials:</b><br>
   481	        Username: <code>admin</code> | Password: <code>admin123</code><br><br>
   482	        <b>💡 First Time Setup:</b><br>
   483	        1. Login as admin<br>
   484	        2. Create departments (already added: Fabric, Dyeing, etc.)<br>
   485	        3. Add employees<br>
   486	        4. Create user accounts<br>
   487	        5. Start tracking KPIs!
   488	    </div>
   489	    """, unsafe_allow_html=True)
   490	    st.markdown("</div>", unsafe_allow_html=True)
   491	
   492	# ============================================================
   493	# SESSION MANAGEMENT
   494	# ============================================================
   495	if "logged_in" not in st.session_state:
   496	    st.session_state["logged_in"] = False
   497	
   498	if "user" not in st.session_state:
   499	    st.session_state["user"] = None
   500	
   501	# Show login page if not authenticated
   502	if not st.session_state["logged_in"]:
   503	    show_login_page()
   504	    st.stop()
   505	
   506	# Get current user info
   507	current_user = st.session_state["user"]
   508	username = current_user["username"]
   509	full_name = current_user["full_name"]
   510	user_role = current_user["role"]
   511	user_employee_name = current_user.get("employee_name")
   512	user_department = current_user.get("department")
   513	
   514	# ============================================================
   515	# SIDEBAR
   516	# ============================================================
   517	with st.sidebar:
   518	    st.markdown("### 👤 User Profile")
   519	    st.markdown(f"**{full_name}**")
   520	    st.markdown(f"<span class='role-badge-{user_role}'>{user_role.upper()}</span>", unsafe_allow_html=True)
   521	    
   522	    if user_employee_name:
   523	        st.markdown(f"**Employee:** {user_employee_name}")
   524	    if user_department:
   525	        st.markdown(f"**Department:** {user_department}")
   526	    
   527	    st.markdown(f"**Username:** {username}")
   528	    
   529	    if st.button("🚪 Logout", use_container_width=True, type="primary"):
   530	        log_action(username, "LOGOUT", "User logged out")
   531	        st.session_state.clear()
   532	        st.rerun()
   533	    
   534	    st.markdown("---")
   535	    st.markdown("## 🔎 Data Filters")
   536	    
   537	    # Role-based filtering
   538	    if user_role == "employee":
   539	        dept_filter = user_department or "All"
   540	        emp_filter = user_employee_name or "All"
   541	        st.info("📌 Viewing your data only")
   542	    else:
   543	        dept_rows = run_query(
   544	            "SELECT DISTINCT department FROM kpi_entries WHERE department IS NOT NULL AND department<>'' ORDER BY department",
   545	            fetch=True
   546	        ) or []
   547	        dept_list = [r[0] for r in dept_rows]
   548	        
   549	        if user_role == "manager":
   550	            dept_list = [d for d in dept_list if d == user_department]
   551	            if user_department and user_department in dept_list:
   552	                dept_filter = user_department
   553	                st.info(f"📌 Department: {user_department}")
   554	            else:
   555	                dept_filter = "All"
   556	        else:
   557	            dept_filter = st.selectbox("🏢 Department", ["All"] + dept_list)
   558	        
   559	        emp_q = "SELECT DISTINCT employee_name FROM kpi_entries WHERE employee_name IS NOT NULL AND employee_name<>''"
   560	        emp_p = []
   561	        if dept_filter != "All":
   562	            emp_q += " AND department=%s"
   563	            emp_p.append(dept_filter)
   564	        emp_q += " ORDER BY employee_name"
   565	        
   566	        emp_rows = run_query(emp_q, emp_p, fetch=True) or []
   567	        emp_list = [r[0] for r in emp_rows]
   568	        emp_filter = st.selectbox("👤 Employee", ["All"] + emp_list)
   569	    
   570	    date_range = st.date_input("📅 Date Range", value=[])
   571	    rating_filter = st.selectbox("⭐ Rating", ["All", "Excellent", "Good", "Average", "Needs Improvement"])
   572	
   573	# ============================================================
   574	# HEADER
   575	# ============================================================
   576	st.markdown('<div class="card">', unsafe_allow_html=True)
   577	col_h1, col_h2 = st.columns([3, 2])
   578	
   579	with col_h1:
   580	    st.title("📊 Yash Gallery – KPI Management System")
   581	    st.caption("🔐 Role-Based Access • 👥 Multi-User Support • 📋 Audit Trail • 📈 Real-Time Analytics")
   582	
   583	with col_h2:
   584	    st.markdown(f"""
   585	        <div style='text-align:right;padding:10px'>
   586	            <span class='badge badge-info'>User: {username}</span><br>
   587	            <span class='role-badge-{user_role}'>{user_role.upper()}</span>
   588	            <span class='badge badge-success'>● Online</span>
   589	        </div>
   590	    """, unsafe_allow_html=True)
   591	
   592	st.markdown("</div>", unsafe_allow_html=True)
   593	
   594	# ============================================================
   595	# DYNAMIC MENU BASED ON ROLE
   596	# ============================================================
   597	if user_role == "admin":
   598	    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employees", "Departments", "Users", "Audit Log", "Settings"]
   599	    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people", "building", "person-badge", "clipboard-data", "gear"]
   600	elif user_role == "manager":
   601	    menu_options = ["Dashboard", "Entry", "Records", "Reports", "Employees"]
   602	    menu_icons = ["speedometer2", "plus-circle", "table", "bar-chart", "people"]
   603	else:  # employee
   604	    menu_options = ["Dashboard", "My Records"]
   605	    menu_icons = ["speedometer2", "table"]
   606	
   607	menu = option_menu(
   608	    None,
   609	    menu_options,
   610	    icons=menu_icons,
   611	    menu_icon="cast",
   612	    default_index=0,
   613	    orientation="horizontal",
   614	    styles={
   615	        "container": {"padding": "0.2rem 0", "background-color": "#ffffff", 
   616	                     "border": "1px solid #e5e7eb", "border-radius": "14px"},
   617	        "icon": {"color": "#2563EB", "font-size": "16px"}, 
   618	        "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", 
   619	                    "padding": "10px 12px", "color": "#374151"},
   620	        "nav-link-selected": {"background-color": "#2563EB", "color": "white", 
   621	                             "font-weight": "bold"},
   622	    }
   623	)
   624	
   625	# ============================================================
   626	# QUERY KPI ENTRIES
   627	# ============================================================
   628	q = """
   629	SELECT id, employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, 
   630	       created_at, COALESCE(created_by, 'system') as created_by
   631	FROM kpi_entries WHERE 1=1
   632	"""
   633	p = []
   634	
   635	# Role-based data filtering
   636	if user_role == "employee":
   637	    q += " AND employee_name=%s"
   638	    p.append(user_employee_name)
   639	elif user_role == "manager":
   640	    q += " AND department=%s"
   641	    p.append(user_department)
   642	
   643	if dept_filter != "All" and user_role == "admin":
   644	    q += " AND department=%s"
   645	    p.append(dept_filter)
   646	if emp_filter != "All" and user_role != "employee":
   647	    q += " AND employee_name=%s"
   648	    p.append(emp_filter)
   649	if rating_filter != "All":
   650	    q += " AND rating=%s"
   651	    p.append(rating_filter)
   652	if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
   653	    q += " AND DATE(created_at) BETWEEN %s AND %s"
   654	    p += [str(date_range[0]), str(date_range[1])]
   655	
   656	q += " ORDER BY created_at DESC"
   657	
   658	rows = run_query(q, p, fetch=True) or []
   659	df = pd.DataFrame(rows, columns=["ID", "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
   660	                                 "Score", "Rating", "Created At", "Created By"])
   661	
   662	kpi1_lbl, kpi2_lbl, kpi3_lbl, kpi4_lbl = get_kpi_labels()
   663	
   664	# ============================================================
   665	# DASHBOARD
   666	# ============================================================
   667	if menu == "Dashboard":
   668	    st.markdown('<div class="card">', unsafe_allow_html=True)
   669	    st.subheader("📊 KPI Performance Summary")
   670	    
   671	    col1, col2, col3, col4, col5 = st.columns(5)
   672	    
   673	    total_records = len(df)
   674	    avg_score = round(float(df["Score"].mean()), 2) if total_records > 0 else 0
   675	    best_score = round(float(df["Score"].max()), 2) if total_records > 0 else 0
   676	    
   677	    if user_role == "admin":
   678	        active_emp = len(run_query("SELECT id FROM employees WHERE is_active=TRUE", fetch=True) or [])
   679	        active_dept = len(run_query("SELECT id FROM departments WHERE is_active=TRUE", fetch=True) or [])
   680	    elif user_role == "manager":
   681	        active_emp = len(run_query("SELECT id FROM employees WHERE is_active=TRUE AND department=%s", 
   682	                                  [user_department], fetch=True) or [])
   683	        active_dept = 1
   684	    else:
   685	        active_emp = 1
   686	        active_dept = 1
   687	    
   688	    with col1:
   689	        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
   690	        st.metric("📝 Total Records", total_records)
   691	        st.markdown('</div>', unsafe_allow_html=True)
   692	    
   693	    with col2:
   694	        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
   695	        st.metric("⭐ Average Score", avg_score)
   696	        st.markdown('</div>', unsafe_allow_html=True)
   697	    
   698	    with col3:
   699	        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
   700	        st.metric("🏆 Best Score", best_score)
   701	        st.markdown('</div>', unsafe_allow_html=True)
   702	    
   703	    with col4:
   704	        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
   705	        st.metric("👥 Employees", active_emp)
   706	        st.markdown('</div>', unsafe_allow_html=True)
   707	    
   708	    with col5:
   709	        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
   710	        st.metric("🏢 Departments", active_dept)
   711	        st.markdown('</div>', unsafe_allow_html=True)
   712	    
   713	    st.markdown("</div>", unsafe_allow_html=True)
   714	    
   715	    if len(df) > 0:
   716	        st.write("")
   717	        
   718	        # Rating Distribution & Performance Summary
   719	        col_chart1, col_chart2 = st.columns([1.5, 1])
   720	        
   721	        with col_chart1:
   722	            st.markdown('<div class="card">', unsafe_allow_html=True)
   723	            st.subheader("📊 Rating Distribution")
   724	            rating_counts = df["Rating"].value_counts().reset_index()
   725	            rating_counts.columns = ["Rating", "Count"]
   726	            
   727	            colors = {
   728	                "Excellent": "#10b981",
   729	                "Good": "#3b82f6",
   730	                "Average": "#f59e0b",
   731	                "Needs Improvement": "#ef4444"
   732	            }
   733	            
   734	            fig = px.pie(rating_counts, values="Count", names="Rating", 
   735	                        color="Rating", color_discrete_map=colors, hole=0.4)
   736	            fig.update_traces(textposition='inside', textinfo='percent+label')
   737	            fig.update_layout(showlegend=True, height=350)
   738	            st.plotly_chart(fig, use_container_width=True)
   739	            st.markdown("</div>", unsafe_allow_html=True)
   740	        
   741	        with col_chart2:
   742	            st.markdown('<div class="card">', unsafe_allow_html=True)
   743	            st.subheader("🎯 Performance Breakdown")
   744	            total_cnt = len(df)
   745	            
   746	            for rating, color, emoji in [
   747	                ("Excellent", "#dcfce7", "🌟"),
   748	                ("Good", "#dbeafe", "👍"),
   749	                ("Average", "#fef3c7", "📊"),
   750	                ("Needs Improvement", "#fee2e2", "⚠️")
   751	            ]:
   752	                cnt = len(df[df["Rating"] == rating])
   753	                pct = round(cnt/total_cnt*100, 1) if total_cnt > 0 else 0
   754	                st.markdown(f"""
   755	                <div class='performance-box' style='background:{color}'>
   756	                    <b>{emoji} {rating}:</b> {cnt} records ({pct}%)
   757	                </div>
   758	                """, unsafe_allow_html=True)
   759	            
   760	            st.markdown("</div>", unsafe_allow_html=True)
   761	        
   762	        # Department & Employee Performance
   763	        if user_role != "employee":
   764	            st.write("")
   765	            col_perf1, col_perf2 = st.columns(2)
   766	            
   767	            with col_perf1:
   768	                st.markdown('<div class="card">', unsafe_allow_html=True)
   769	                st.subheader("🏭 Department Performance")
   770	                dept_avg = df.groupby("Department")["Score"].mean().reset_index()
   771	                dept_avg = dept_avg.sort_values("Score", ascending=False)
   772	                fig = px.bar(dept_avg, x="Department", y="Score", 
   773	                            color="Score", color_continuous_scale="Viridis",
   774	                            text="Score")
   775	                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
   776	                fig.update_layout(showlegend=False, height=400)
   777	                st.plotly_chart(fig, use_container_width=True)
   778	                st.markdown("</div>", unsafe_allow_html=True)
   779	            
   780	            with col_perf2:
   781	                st.markdown('<div class="card">', unsafe_allow_html=True)
   782	                st.subheader("👤 Top 10 Performers")
   783	                top_emp = df.groupby("Employee")["Score"].mean().reset_index()
   784	                top_emp = top_emp.sort_values("Score", ascending=False).head(10)
   785	                fig = px.bar(top_emp, x="Score", y="Employee", orientation='h',
   786	                            color="Score", color_continuous_scale="RdYlGn",
   787	                            text="Score")
   788	                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
   789	                fig.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, height=400)
   790	                st.plotly_chart(fig, use_container_width=True)
   791	                st.markdown("</div>", unsafe_allow_html=True)
   792	        
   793	        # Monthly Trend
   794	        st.write("")
   795	        st.markdown('<div class="card">', unsafe_allow_html=True)
   796	        st.subheader("📈 Monthly Performance Trend")
   797	        tmp = df.copy()
   798	        tmp["Month"] = pd.to_datetime(tmp["Created At"]).dt.to_period("M").astype(str)
   799	        monthly_avg = tmp.groupby("Month")["Score"].mean().reset_index()
   800	        monthly_avg = monthly_avg.sort_values("Month")
   801	        
   802	        fig = go.Figure()
   803	        fig.add_trace(go.Scatter(
   804	            x=monthly_avg["Month"],
   805	            y=monthly_avg["Score"],
   806	            mode='lines+markers',
   807	            name='Average Score',
   808	            line=dict(color='#2563eb', width=3),
   809	            marker=dict(size=10, color='#2563eb')
   810	        ))
   811	        fig.update_layout(
   812	            xaxis_title="Month",
   813	            yaxis_title="Average Score",
   814	            hovermode='x unified',
   815	            height=350
   816	        )
   817	        st.plotly_chart(fig, use_container_width=True)
   818	        st.markdown("</div>", unsafe_allow_html=True)
   819	    else:
   820	        st.info("📌 No KPI data available. Start by adding entries!")
   821	
   822	# ============================================================
   823	# ENTRY
   824	# ============================================================
   825	if menu == "Entry":
   826	    if not require_auth("manager"):
   827	        st.stop()
   828	    
   829	    st.markdown('<div class="card">', unsafe_allow_html=True)
   830	    st.subheader("➕ Add New KPI Entry")
   831	    
   832	    with st.form("add_kpi_form", clear_on_submit=True):
   833	        col_info1, col_info2 = st.columns([2, 1])
   834	        
   835	        with col_info1:
   836	            active_emps = get_active_employees()
   837	            
   838	            if user_role == "manager":
   839	                active_emps = [e for e in active_emps if e[1] == user_department]
   840	            
   841	            emp_list = [e[0] for e in active_emps]
   842	            emp = st.selectbox("🔍 Select Employee", [""] + emp_list, help="Choose employee to add KPI entry")
   843	            
   844	            if emp:
   845	                dept = [e[1] for e in active_emps if e[0] == emp][0]
   846	                st.success(f"✅ Department: **{dept}**")
   847	            else:
   848	                dept = user_department if user_role == "manager" else ""
   849	        
   850	        with col_info2:
   851	            st.markdown("### 📅 Entry Info")
   852	            st.info(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}")
   853	            st.info(f"**Created By:** {username}")
   854	        
   855	        st.markdown("---")
   856	        st.markdown("### 📊 Enter KPI Scores (1-100)")
   857	        
   858	        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
   859	        
   860	        with col_k1:
   861	            v1 = st.number_input(f"🎯 {kpi1_lbl}", min_value=1, max_value=100, value=50, step=1)
   862	        with col_k2:
   863	            v2 = st.number_input(f"📈 {kpi2_lbl}", min_value=1, max_value=100, value=50, step=1)
   864	        with col_k3:
   865	            v3 = st.number_input(f"📅 {kpi3_lbl}", min_value=1, max_value=100, value=50, step=1)
   866	        with col_k4:
   867	            v4 = st.number_input(f"🤝 {kpi4_lbl}", min_value=1, max_value=100, value=50, step=1)
   868	        
   869	        # Calculate preview score
   870	        preview_score = calc_weighted_score(v1, v2, v3, v4)
   871	        preview_rating = calc_rating(preview_score)
   872	        
   873	        st.markdown("---")
   874	        col_preview, col_submit = st.columns([2, 1])
   875	        
   876	        with col_preview:
   877	            st.markdown(f"### 📊 Preview:")
   878	            st.markdown(f"**Weighted Score:** {preview_score} / 100")
   879	            st.markdown(f"**Rating:** {preview_rating}")
   880	        
   881	        with col_submit:
   882	            submit = st.form_submit_button("✅ Save Entry", use_container_width=True, type="primary")
   883	    
   884	    if submit:
   885	        if emp and dept:
   886	            score = calc_weighted_score(v1, v2, v3, v4)
   887	            rating = calc_rating(score)
   888	            now = datetime.now()
   889	            month = now.strftime("%Y-%m")
   890	            
   891	            result = run_query("""
   892	                INSERT INTO kpi_entries (employee_name, department, kpi1, kpi2, kpi3, kpi4, 
   893	                                        total_score, rating, created_at, entry_month, created_by)
   894	                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
   895	            """, [emp, dept, v1, v2, v3, v4, score, rating, now, month, username])
   896	            
   897	            if result is not None:
   898	                log_action(username, "CREATE_KPI_ENTRY", f"Created entry for {emp} - Score: {score}")
   899	                st.success(f"✅ Entry saved successfully! **Score:** {score} | **Rating:** {rating}")
   900	                st.balloons()
   901	                st.rerun()
   902	            else:
   903	                st.error("❌ Failed to save entry. Please try again.")
   904	        else:
   905	            st.error("⚠️ Please select an employee before submitting.")
   906	    
   907	    st.markdown("</div>", unsafe_allow_html=True)
   908	
   909	# ============================================================
   910	# RECORDS / MY RECORDS
   911	# ============================================================
   912	if menu in ["Records", "My Records"]:
   913	    if menu == "Records" and not require_auth("manager"):
   914	        st.stop()
   915	    
   916	    st.markdown('<div class="card">', unsafe_allow_html=True)
   917	    st.subheader("📋 KPI Records" if menu == "Records" else "📋 My KPI Records")
   918	    
   919	    if len(df) > 0:
   920	        # Rename columns for display
   921	        show_df = df.drop(columns=["ID"]).rename(columns={
   922	            "KPI1": kpi1_lbl,
   923	            "KPI2": kpi2_lbl,
   924	            "KPI3": kpi3_lbl,
   925	            "KPI4": kpi4_lbl
   926	        })
   927	        
   928	        # Color coding for ratings
   929	        def highlight_rating(row):
   930	            colors = {
   931	                "Excellent": "background-color: #dcfce7",
   932	                "Good": "background-color: #dbeafe",
   933	                "Average": "background-color: #fef3c7",
   934	                "Needs Improvement": "background-color: #fee2e2"
   935	            }
   936	            return [colors.get(row["Rating"], "")] * len(row)
   937	        
   938	        styled_df = show_df.style.apply(highlight_rating, axis=1)
   939	        st.dataframe(styled_df, use_container_width=True, hide_index=True)
   940	        
   941	        # Export options
   942	        st.markdown("---")
   943	        col_exp1, col_exp2, col_exp3 = st.columns([2, 1, 1])
   944	        
   945	        with col_exp1:
   946	            st.markdown(f"**Total Records:** {len(df)}")
   947	        
   948	        with col_exp2:
   949	            csv = df.to_csv(index=False).encode('utf-8')
   950	            st.download_button(
   951	                label="📥 Download CSV",
   952	                data=csv,
   953	                file_name=f"kpi_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
   954	                mime="text/csv",
   955	                use_container_width=True
   956	            )
   957	        
   958	        with col_exp3:
   959	            excel_data = df.to_csv(index=False).encode('utf-8')
   960	            st.download_button(
   961	                label="📊 Download Excel",
   962	                data=excel_data,
   963	                file_name=f"kpi_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
   964	                mime="application/vnd.ms-excel",
   965	                use_container_width=True
   966	            )
   967	    else:
   968	        st.info("📌 No records found matching the current filters.")
   969	    
   970	    st.markdown("</div>", unsafe_allow_html=True)
   971	    
   972	    # Edit/Delete Section (for Manager and Admin)
   973	    if user_role in ["admin", "manager"] and len(df) > 0 and get_setting("allow_edit_delete", "1") == "1":
   974	        st.write("")
   975	        st.markdown('<div class="card">', unsafe_allow_html=True)
   976	        st.subheader("✏️ Edit / Delete Records")
   977	        
   978	        rec_id = st.selectbox("🔍 Select Record ID", df["ID"].tolist())
   979	        row = df[df["ID"] == rec_id].iloc[0]
   980	        
   981	        col_edit1, col_edit2 = st.columns([2, 1])
   982	        
   983	        with col_edit1:
   984	            st.markdown("#### 📝 Edit KPI Values")
   985	            col_k1, col_k2, col_k3, col_k4 = st.columns(4)
   986	            
   987	            with col_k1:
   988	                e_k1 = st.number_input(kpi1_lbl, 1, 100, int(row["KPI1"]), key="edit_k1")
   989	            with col_k2:
   990	                e_k2 = st.number_input(kpi2_lbl, 1, 100, int(row["KPI2"]), key="edit_k2")
   991	            with col_k3:
   992	                e_k3 = st.number_input(kpi3_lbl, 1, 100, int(row["KPI3"]), key="edit_k3")
   993	            with col_k4:
   994	                e_k4 = st.number_input(kpi4_lbl, 1, 100, int(row["KPI4"]), key="edit_k4")
   995	        
   996	        with col_edit2:
   997	            st.markdown("#### 📊 Current Info")
   998	            st.info(f"**Employee:** {row['Employee']}")
   999	            st.info(f"**Department:** {row['Department']}")
  1000	            st.info(f"**Current Score:** {row['Score']}")
  1001	            st.info(f"**Current Rating:** {row['Rating']}")
  1002	            
  1003	            new_score = calc_weighted_score(e_k1, e_k2, e_k3, e_k4)
  1004	            new_rating = calc_rating(new_score)
  1005	            st.success(f"**New Score:** {new_score}")
  1006	            st.success(f"**New Rating:** {new_rating}")
  1007	        
  1008	        st.markdown("---")
  1009	        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
  1010	        
  1011	        with col_btn1:
  1012	            if st.button("💾 Update Record", use_container_width=True, type="primary"):
  1013	                run_query("""
  1014	                    UPDATE kpi_entries 
  1015	                    SET kpi1=%s, kpi2=%s, kpi3=%s, kpi4=%s, total_score=%s, rating=%s, 
  1016	                        updated_by=%s, updated_at=%s
  1017	                    WHERE id=%s
  1018	                """, [e_k1, e_k2, e_k3, e_k4, new_score, new_rating, username, datetime.now(), rec_id])
  1019	                
  1020	                log_action(username, "UPDATE_KPI_ENTRY", f"Updated entry ID {rec_id} for {row['Employee']}")
  1021	                st.success("✅ Record updated successfully!")
  1022	                st.rerun()
  1023	        
  1024	        with col_btn2:
  1025	            if st.button("🗑️ Delete Record", use_container_width=True, type="secondary"):
  1026	                run_query("DELETE FROM kpi_entries WHERE id=%s", [rec_id])
  1027	                log_action(username, "DELETE_KPI_ENTRY", f"Deleted entry ID {rec_id} for {row['Employee']}")
  1028	                st.warning("🗑️ Record deleted!")
  1029	                st.rerun()
  1030	        
  1031	        st.markdown("</div>", unsafe_allow_html=True)
  1032	
  1033	# ============================================================
  1034	# REPORTS
  1035	# ============================================================
  1036	if menu == "Reports":
  1037	    if not require_auth("manager"):
  1038	        st.stop()
  1039	    
  1040	    st.markdown('<div class="card">', unsafe_allow_html=True)
  1041	    st.subheader("📊 Performance Reports")
  1042	    
  1043	    if len(df) > 0:
  1044	        tmp = df.copy()
  1045	        tmp["Month"] = pd.to_datetime(tmp["Created At"]).dt.to_period("M").astype(str)
  1046	        months = sorted(tmp["Month"].unique())[::-1]
  1047	        
  1048	        col_r1, col_r2, col_r3 = st.columns(3)
  1049	        
  1050	        with col_r1:
  1051	            report_type = st.selectbox("📋 Report Type", ["Employee Wise Average", "Department Wise Average", "Detailed Records"])
  1052	        
  1053	        with col_r2:
  1054	            sel_month = st.selectbox("📅 Select Month", months)
  1055	        
  1056	        with col_r3:
  1057	            chart_type = st.selectbox("📈 Chart Type", ["Bar Chart", "Line Chart", "Pie Chart"])
  1058	        
  1059	        mdf = tmp[tmp["Month"] == sel_month]
  1060	        
  1061	        st.markdown("---")
  1062	        
  1063	        if report_type == "Employee Wise Average":
  1064	            rep = mdf.groupby("Employee")["Score"].mean().reset_index()
  1065	            rep = rep.sort_values("Score", ascending=False)
  1066	            x_col, y_col = "Employee", "Score"
  1067	        elif report_type == "Department Wise Average":
  1068	            rep = mdf.groupby("Department")["Score"].mean().reset_index()
  1069	            rep = rep.sort_values("Score", ascending=False)
  1070	            x_col, y_col = "Department", "Score"
  1071	        else:
  1072	            rep = mdf[["Employee", "Department", "Score", "Rating"]].copy()
  1073	            x_col, y_col = "Employee", "Score"
  1074	        
  1075	        # Generate chart
  1076	        if chart_type == "Bar Chart":
  1077	            fig = px.bar(rep, x=x_col, y=y_col, color=y_col, 
  1078	                        color_continuous_scale="Viridis", text=y_col)
  1079	            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
  1080	        elif chart_type == "Line Chart":
  1081	            fig = px.line(rep, x=x_col, y=y_col, markers=True)
  1082	        else:
  1083	            fig = px.pie(rep, values=y_col, names=x_col)
  1084	        
  1085	        fig.update_layout(height=500)
  1086	        st.plotly_chart(fig, use_container_width=True)
  1087	        
  1088	        st.markdown("---")
  1089	        st.dataframe(rep, use_container_width=True, hide_index=True)
  1090	        
  1091	        # Export report
  1092	        csv = rep.to_csv(index=False).encode('utf-8')
  1093	        st.download_button(
  1094	            label="📥 Download Report",
  1095	            data=csv,
  1096	            file_name=f"report_{sel_month}_{report_type.replace(' ', '_')}.csv",
  1097	            mime="text/csv"
  1098	        )
  1099	    else:
  1100	        st.info("📌 No data available for reports.")
  1101	    
  1102	    st.markdown("</div>", unsafe_allow_html=True)
  1103	
  1104	# ============================================================
  1105	# EMPLOYEES MANAGEMENT
  1106	# ============================================================
  1107	if menu == "Employees":
  1108	    if not require_auth("manager"):
  1109	        st.stop()
  1110	    
  1111	    st.markdown('<div class="card">', unsafe_allow_html=True)
  1112	    st.subheader("👥 Employee Management")
  1113	    
  1114	    tab1, tab2 = st.tabs(["➕ Add Employee", "📋 Manage Employees"])
  1115	    
  1116	    with tab1:
  1117	        st.markdown("### Add New Employee")
  1118	        
  1119	        with st.form("add_employee_form"):
  1120	            col_add1, col_add2 = st.columns(2)
  1121	            
  1122	            with col_add1:
  1123	                emp_name = st.text_input("👤 Employee Name", placeholder="Enter full name")
  1124	            
  1125	            with col_add2:
  1126	                if user_role == "admin":
  1127	                    emp_dept = st.selectbox("🏢 Department", get_active_departments())
  1128	                else:
  1129	                    emp_dept = user_department
  1130	                    st.info(f"🏢 Department: **{user_department}**")
  1131	            
  1132	            emp_active = st.checkbox("✅ Active Status", value=True)
  1133	            
  1134	            submit = st.form_submit_button("➕ Add Employee", use_container_width=True, type="primary")
  1135	            
  1136	            if submit:
  1137	                if emp_name.strip() and emp_dept:
  1138	                    result = run_query("""
  1139	                        INSERT INTO employees (employee_name, department, is_active, created_at)
  1140	                        VALUES (%s, %s, %s, %s)
  1141	                    """, [emp_name.strip(), emp_dept, emp_active, datetime.now()])
  1142	                    
  1143	                    if result is not None:
  1144	                        log_action(username, "ADD_EMPLOYEE", f"Added employee: {emp_name}")
  1145	                        st.success(f"✅ Employee '{emp_name}' added successfully!")
  1146	                        st.rerun()
  1147	                    else:
  1148	                        st.error("❌ Employee already exists or error occurred.")
  1149	                else:
  1150	                    st.error("⚠️ Please enter employee name and select department.")
  1151	    
  1152	    with tab2:
  1153	        st.markdown("### Existing Employees")
  1154	        
  1155	        emps = get_all_employees()
  1156	        
  1157	        if user_role == "manager":
  1158	            emps = [e for e in emps if e[2] == user_department]
  1159	        
  1160	        if emps:
  1161	            emp_df = pd.DataFrame(emps, columns=["ID", "Name", "Dept", "Active", "Created"])
  1162	            emp_df["Status"] = emp_df["Active"].apply(lambda x: "✅ Active" if x else "❌ Inactive")
  1163	            
  1164	            st.dataframe(emp_df[["Name", "Dept", "Status", "Created"]], use_container_width=True, hide_index=True)
  1165	            
  1166	            st.markdown("---")
  1167	            st.markdown("### ✏️ Edit Employee")
  1168	            
  1169	            emp_to_edit = st.selectbox("Select Employee", [e[1] for e in emps])
  1170	            
  1171	            if emp_to_edit:
  1172	                emp_data = [e for e in emps if e[1] == emp_to_edit][0]
  1173	                emp_id, emp_name, emp_dept, emp_active, _ = emp_data
  1174	                
  1175	                col_e1, col_e2 = st.columns(2)
  1176	                
  1177	                with col_e1:
  1178	                    new_name = st.text_input("Employee Name", value=emp_name, key="edit_emp_name")
  1179	                    
  1180	                    if user_role == "admin":
  1181	                        depts = get_active_departments()
  1182	                        new_dept = st.selectbox("Department", depts, 
  1183	                                               index=depts.index(emp_dept) if emp_dept in depts else 0,
  1184	                                               key="edit_emp_dept")
  1185	                    else:
  1186	                        new_dept = emp_dept
  1187	                        st.info(f"Department: **{emp_dept}**")
  1188	                
  1189	                with col_e2:
  1190	                    new_active = st.checkbox("Active Status", value=emp_active, key="edit_emp_active")
  1191	                    st.info(f"**Current Status:** {'✅ Active' if emp_active else '❌ Inactive'}")
  1192	                
  1193	                col_btn1, col_btn2 = st.columns(2)
  1194	                
  1195	                with col_btn1:
  1196	                    if st.button("💾 Update Employee", use_container_width=True, type="primary"):
  1197	                        run_query("""
  1198	                            UPDATE employees 
  1199	                            SET employee_name=%s, department=%s, is_active=%s, updated_at=%s
  1200	                            WHERE id=%s
  1201	                        """, [new_name.strip(), new_dept, new_active, datetime.now(), emp_id])
  1202	                        
  1203	                        log_action(username, "UPDATE_EMPLOYEE", f"Updated: {emp_name} → {new_name}")
  1204	                        st.success("✅ Employee updated successfully!")
  1205	                        st.rerun()
  1206	                
  1207	                with col_btn2:
  1208	                    if st.button("🗑️ Delete Employee", use_container_width=True, type="secondary") and user_role == "admin":
  1209	                        entries = run_query("SELECT COUNT(*) FROM kpi_entries WHERE employee_name=%s", 
  1210	                                          [emp_name], fetch=True)
  1211	                        if entries and entries[0][0] > 0:
  1212	                            st.error(f"⚠️ Cannot delete! {entries[0][0]} KPI entries exist for this employee.")
  1213	                        else:
  1214	                            run_query("DELETE FROM employees WHERE id=%s", [emp_id])
  1215	                            log_action(username, "DELETE_EMPLOYEE", f"Deleted employee: {emp_name}")
  1216	                            st.success("🗑️ Employee deleted!")
  1217	                            st.rerun()
  1218	        else:
  1219	            st.info("📌 No employees found. Add employees using the 'Add Employee' tab.")
  1220	    
  1221	    st.markdown("</div>", unsafe_allow_html=True)
  1222	
  1223	# ============================================================
  1224	# DEPARTMENTS MANAGEMENT (Admin Only)
  1225	# ============================================================
  1226	if menu == "Departments":
  1227	    if not require_auth("admin"):
  1228	        st.stop()
  1229	    
  1230	    st.markdown('<div class="card">', unsafe_allow_html=True)
  1231	    st.subheader("🏢 Department Management")
  1232	    
  1233	    tab1, tab2 = st.tabs(["➕ Add Department", "��� Manage Departments"])
  1234	    
  1235	    with tab1:
  1236	        st.markdown("### Add New Department")
  1237	        
  1238	        with st.form("add_dept_form"):
  1239	            dept_name = st.text_input("🏢 Department Name", placeholder="e.g., Fabric, Dyeing, Quality Control")
  1240	            dept_active = st.checkbox("✅ Active Status", value=True)
  1241	            
  1242	            submit = st.form_submit_button("➕ Add Department", use_container_width=True, type="primary")
  1243	            
  1244	            if submit:
  1245	                if dept_name.strip():
  1246	                    result = run_query("""
  1247	                        INSERT INTO departments (department_name, is_active, created_at)
  1248	                        VALUES (%s, %s, %s)
  1249	                    """, [dept_name.strip(), dept_active, datetime.now()])
  1250	                    
  1251	                    if result is not None:
  1252	                        log_action(username, "ADD_DEPARTMENT", f"Added department: {dept_name}")
  1253	                        st.success(f"✅ Department '{dept_name}' added successfully!")
  1254	                        st.balloons()
  1255	                        st.rerun()
  1256	                    else:
  1257	                        st.error("❌ Department already exists or error occurred.")
  1258	                else:
  1259	                    st.error("⚠️ Please enter department name.")
  1260	    
  1261	    with tab2:
  1262	        st.markdown("### Existing Departments")
  1263	        
  1264	        depts = get_all_departments()
  1265	        
  1266	        if depts:
  1267	            dept_df = pd.DataFrame(depts, columns=["ID", "Name", "Active", "Created"])
  1268	            dept_df["Status"] = dept_df["Active"].apply(lambda x: "✅ Active" if x else "❌ Inactive")
  1269	            
  1270	            # Count employees per department
  1271	            for idx, row in dept_df.iterrows():
  1272	                emp_count = run_query("SELECT COUNT(*) FROM employees WHERE department=%s", 
  1273	                                     [row["Name"]], fetch=True)
  1274	                dept_df.at[idx, "Employees"] = emp_count[0][0] if emp_count else 0
  1275	            
  1276	            st.dataframe(dept_df[["Name", "Status", "Employees", "Created"]], 
  1277	                        use_container_width=True, hide_index=True)
  1278	            
  1279	            st.markdown("---")
  1280	            st.markdown("### ✏️ Edit Department")
  1281	            
  1282	            dept_to_edit = st.selectbox("Select Department", [d[1] for d in depts])
  1283	            
  1284	            if dept_to_edit:
  1285	                dept_data = [d for d in depts if d[1] == dept_to_edit][0]
  1286	                dept_id, dept_name, dept_active, _ = dept_data
  1287	                
  1288	                col_d1, col_d2 = st.columns(2)
  1289	                
  1290	                with col_d1:
  1291	                    new_dept_name = st.text_input("Department Name", value=dept_name, key="edit_dept_name")
  1292	                
  1293	                with col_d2:
  1294	                    new_dept_active = st.checkbox("Active Status", value=dept_active, key="edit_dept_active")
  1295	                    st.info(f"**Current:** {'✅ Active' if dept_active else '❌ Inactive'}")
  1296	                
  1297	                col_btn1, col_btn2 = st.columns(2)
  1298	                
  1299	                with col_btn1:
  1300	                    if st.button("💾 Update Department", use_container_width=True, type="primary"):
  1301	                        run_query("""
  1302	                            UPDATE departments 
  1303	                            SET department_name=%s, is_active=%s
  1304	                            WHERE id=%s
  1305	                        """, [new_dept_name.strip(), new_dept_active, dept_id])
  1306	                        
  1307	                        log_action(username, "UPDATE_DEPARTMENT", f"Updated: {dept_name} → {new_dept_name}")
  1308	                        st.success("✅ Department updated successfully!")
  1309	                        st.rerun()
  1310	                
  1311	                with col_btn2:
  1312	                    if st.button("🗑️ Delete Department", use_container_width=True, type="secondary"):
  1313	                        emp_count = run_query("SELECT COUNT(*) FROM employees WHERE department=%s", 
  1314	                                            [dept_name], fetch=True)
  1315	                        if emp_count and emp_count[0][0] > 0:
  1316	                            st.error(f"⚠️ Cannot delete! {emp_count[0][0]} employees exist in this department.")
  1317	                        else:
  1318	                            run_query("DELETE FROM departments WHERE id=%s", [dept_id])
  1319	                            log_action(username, "DELETE_DEPARTMENT", f"Deleted department: {dept_name}")
  1320	                            st.success("🗑️ Department deleted!")
  1321	                            st.rerun()
  1322	        else:
  1323	            st.info("📌 No departments found. Add departments using the 'Add Department' tab.")
  1324	    
  1325	    st.markdown("</div>", unsafe_allow_html=True)
  1326	
  1327	# ============================================================
  1328	# USER MANAGEMENT (Admin Only)
  1329	# ============================================================
  1330	if menu == "Users":
  1331	    if not require_auth("admin"):
  1332	        st.stop()
  1333	    
  1334	    st.markdown('<div class="card">', unsafe_allow_html=True)
  1335	    st.subheader("👨‍💼 User Management")
  1336	    
  1337	    tab1, tab2 = st.tabs(["➕ Create User", "📋 Manage Users"])
  1338	    
  1339	    with tab1:
  1340	        st.markdown("### Create New User Account")
  1341	        
  1342	        with st.form("add_user_form"):
  1343	            col_u1, col_u2 = st.columns(2)
  1344	            
  1345	            with col_u1:
  1346	                new_username = st.text_input("👤 Username", placeholder="e.g., john.doe")
  1347	                new_password = st.text_input("🔒 Password", type="password", placeholder="Min 6 characters")
  1348	                new_password2 = st.text_input("🔒 Confirm Password", type="password")
  1349	            
  1350	            with col_u2:
  1351	                new_fullname = st.text_input("📝 Full Name", placeholder="e.g., John Doe")
  1352	                new_role = st.selectbox("🎯 Role", ["employee", "manager", "admin"])
  1353	                
  1354	                if new_role in ["employee", "manager"]:
  1355	                    active_emps = get_active_employees()
  1356	                    emp_list = [e[0] for e in active_emps]
  1357	                    new_emp_name = st.selectbox("🔗 Link to Employee", [""] + emp_list)
  1358	                    
  1359	                    if new_emp_name:
  1360	                        emp_dept = [e[1] for e in active_emps if e[0] == new_emp_name]
  1361	                        new_dept = emp_dept[0] if emp_dept else ""
  1362	                        st.info(f"Department: **{new_dept}**")
  1363	                    else:
  1364	                        new_dept = ""
  1365	                else:
  1366	                    new_emp_name = ""
  1367	                    new_dept = ""
  1368	            
  1369	            new_active = st.checkbox("✅ Active Status", value=True)
  1370	            
  1371	            submit = st.form_submit_button("➕ Create User", use_container_width=True, type="primary")
  1372	            
  1373	            if submit:
  1374	                if not new_username or not new_password or not new_fullname:
  1375	                    st.error("⚠️ Username, password, and full name are required.")
  1376	                elif len(new_password) < 6:
  1377	                    st.error("⚠️ Password must be at least 6 characters.")
  1378	                elif new_password != new_password2:
  1379	                    st.error("⚠️ Passwords do not match.")
  1380	                else:
  1381	                    hashed, salt = hash_password(new_password)
  1382	                    result = run_query("""
  1383	                        INSERT INTO users (username, password_hash, password_salt, full_name, role,
  1384	                                         employee_name, department, is_active, created_by)
  1385	                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
  1386	                    """, [new_username, hashed, salt, new_fullname, new_role, 
  1387	                         new_emp_name or None, new_dept or None, new_active, username])
  1388	                    
  1389	                    if result is not None:
  1390	                        log_action(username, "CREATE_USER", f"Created user: {new_username} ({new_role})")
  1391	                        st.success(f"✅ User '{new_username}' created successfully!")
  1392	                        st.balloons()
  1393	                        st.rerun()
  1394	                    else:
  1395	                        st.error("❌ Username already exists.")
  1396	    
  1397	    with tab2:
  1398	        st.markdown("### Existing Users")
  1399	        
  1400	        users = run_query("""
  1401	            SELECT username, full_name, role, employee_name, department, is_active, last_login
  1402	            FROM users 
  1403	            WHERE username != 'admin'
  1404	            ORDER BY created_at DESC
  1405	        """, fetch=True) or []
  1406	        
  1407	        if users:
  1408	            user_df = pd.DataFrame(users, columns=["Username", "Full Name", "Role", "Employee", 
  1409	                                                   "Department", "Active", "Last Login"])
  1410	            user_df["Status"] = user_df["Active"].apply(lambda x: "✅ Active" if x else "❌ Inactive")
  1411	            user_df["Role Badge"] = user_df["Role"].apply(lambda x: x.upper())
  1412	            
  1413	            st.dataframe(user_df[["Username", "Full Name", "Role Badge", "Employee", 
  1414	                                 "Department", "Status", "Last Login"]], 
  1415	                        use_container_width=True, hide_index=True)
  1416	            
  1417	            st.markdown("---")
  1418	            st.markdown("### ✏️ Edit User")
  1419	            
  1420	            user_to_edit = st.selectbox("Select User", [u[0] for u in users])
  1421	            
  1422	            if user_to_edit:
  1423	                user_data = [u for u in users if u[0] == user_to_edit][0]
  1424	                uname, ufull, urole, uemp, udept, uactive, ulast = user_data
  1425	                
  1426	                col_ue1, col_ue2 = st.columns(2)
  1427	                
  1428	                with col_ue1:
  1429	                    edit_fullname = st.text_input("Full Name", value=ufull, key="edit_user_fullname")
  1430	                    edit_role = st.selectbox("Role", ["employee", "manager", "admin"],
  1431	                                            index=["employee", "manager", "admin"].index(urole),
  1432	                                            key="edit_user_role")
  1433	                
  1434	                with col_ue2:
  1435	                    edit_active = st.checkbox("Active Status", value=uactive, key="edit_user_active")
  1436	                    st.info(f"**Last Login:** {ulast if ulast else 'Never'}")
  1437	                    
  1438	                    # Password reset
  1439	                    st.markdown("#### 🔒 Reset Password")
  1440	                    new_pwd = st.text_input("New Password (optional)", type="password", key="edit_user_pwd")
  1441	                    new_pwd2 = st.text_input("Confirm Password", type="password", key="edit_user_pwd2")
  1442	                
  1443	                col_ubtn1, col_ubtn2 = st.columns(2)
  1444	                
  1445	                with col_ubtn1:
  1446	                    if st.button("💾 Update User", use_container_width=True, type="primary"):
  1447	                        # Update user info
  1448	                        run_query("""
  1449	                            UPDATE users 
  1450	                            SET full_name=%s, role=%s, is_active=%s
  1451	                            WHERE username=%s
  1452	                        """, [edit_fullname, edit_role, edit_active, uname])
  1453	                        
  1454	                        # Update password if provided
  1455	                        if new_pwd:
  1456	                            if len(new_pwd) >= 6 and new_pwd == new_pwd2:
  1457	                                hashed, salt = hash_password(new_pwd)
  1458	                                run_query("UPDATE users SET password_hash=%s, password_salt=%s WHERE username=%s",
  1459	                                         [hashed, salt, uname])
  1460	                                log_action(username, "RESET_PASSWORD", f"Reset password for: {uname}")
  1461	                            else:
  1462	                                st.error("⚠️ Password must be 6+ chars and match")
  1463	                        
  1464	                        log_action(username, "UPDATE_USER", f"Updated user: {uname}")
  1465	                        st.success("✅ User updated successfully!")
  1466	                        st.rerun()
  1467	                
  1468	                with col_ubtn2:
  1469	                    if st.button("🗑️ Delete User", use_container_width=True, type="secondary"):
  1470	                        run_query("DELETE FROM users WHERE username=%s", [uname])
  1471	                        log_action(username, "DELETE_USER", f"Deleted user: {uname}")
  1472	                        st.success("🗑️ User deleted!")
  1473	                        st.rerun()
  1474	        else:
  1475	            st.info("📌 No users found. Create users using the 'Create User' tab.")
  1476	    
  1477	    st.markdown("</div>", unsafe_allow_html=True)
  1478	
  1479	# ============================================================
  1480	# AUDIT LOG (Admin Only)
  1481	# ============================================================
  1482	if menu == "Audit Log":
  1483	    if not require_auth("admin"):
  1484	        st.stop()
  1485	    
  1486	    st.markdown('<div class="card">', unsafe_allow_html=True)
  1487	    st.subheader("📋 System Audit Trail")
  1488	    
  1489	    col_audit1, col_audit2, col_audit3 = st.columns(3)
  1490	    
  1491	    with col_audit1:
  1492	        all_users = run_query("SELECT DISTINCT username FROM audit_log ORDER BY username", fetch=True) or []
  1493	        user_list = [u[0] for u in all_users]
  1494	        filter_user = st.selectbox("Filter by User", ["All"] + user_list)
  1495	    
  1496	    with col_audit2:
  1497	        all_actions = run_query("SELECT DISTINCT action FROM audit_log ORDER BY action", fetch=True) or []
  1498	        action_list = [a[0] for a in all_actions]
  1499	        filter_action = st.selectbox("Filter by Action", ["All"] + action_list)
  1500	    
  1501	    with col_audit3:
  1502	        limit = st.selectbox("Show Records", [50, 100, 200, 500], index=1)
  1503	    
  1504	    # Build query
  1505	    audit_q = "SELECT username, action, details, timestamp FROM audit_log WHERE 1=1"
  1506	    audit_p = []
  1507	    
  1508	    if filter_user != "All":
  1509	        audit_q += " AND username=%s"
  1510	        audit_p.append(filter_user)
  1511	    
  1512	    if filter_action != "All":
  1513	        audit_q += " AND action=%s"
  1514	        audit_p.append(filter_action)
  1515	    
  1516	    audit_q += f" ORDER BY timestamp DESC LIMIT {limit}"
  1517	    
  1518	    logs = run_query(audit_q, audit_p, fetch=True) or []
  1519	    
  1520	    if logs:
  1521	        st.markdown("---")
  1522	        log_df = pd.DataFrame(logs, columns=["User", "Action", "Details", "Timestamp"])
  1523	        st.dataframe(log_df, use_container_width=True, hide_index=True)
  1524	        
  1525	        # Export audit log
  1526	        csv = log_df.to_csv(index=False).encode('utf-8')
  1527	        st.download_button(
  1528	            label="📥 Export Audit Log",
  1529	            data=csv,
  1530	            file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
  1531	            mime="text/csv"
  1532	        )
  1533	    else:
  1534	        st.info("📌 No audit logs found.")
  1535	    
  1536	    st.markdown("</div>", unsafe_allow_html=True)
  1537	
  1538	# ============================================================
  1539	# SETTINGS (Admin Only)
  1540	# ============================================================
  1541	if menu == "Settings":
  1542	    if not require_auth("admin"):
  1543	        st.stop()
  1544	    
  1545	    st.markdown('<div class="card">', unsafe_allow_html=True)
  1546	    st.subheader("⚙️ System Settings & Configuration")
  1547	    
  1548	    tab1, tab2, tab3, tab4 = st.tabs(["📝 KPI Labels", "⚖️ KPI Weights", "⭐ Rating Rules", "🔧 System"])
  1549	    
  1550	    with tab1:
  1551	        st.markdown("### Configure KPI Names")
  1552	        k1, k2, k3, k4 = get_kpi_labels()
  1553	        
  1554	        col_kpi1, col_kpi2 = st.columns(2)
  1555	        
  1556	        with col_kpi1:
  1557	            n1 = st.text_input("KPI 1 Label", value=k1, key="kpi_label_1")
  1558	            n2 = st.text_input("KPI 2 Label", value=k2, key="kpi_label_2")
  1559	        
  1560	        with col_kpi2:
  1561	            n3 = st.text_input("KPI 3 Label", value=k3, key="kpi_label_3")
  1562	            n4 = st.text_input("KPI 4 Label", value=k4, key="kpi_label_4")
  1563	        
  1564	        if st.button("💾 Save KPI Labels", use_container_width=True, type="primary"):
  1565	            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi1'", [n1.strip() or "KPI 1"])
  1566	            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi2'", [n2.strip() or "KPI 2"])
  1567	            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi3'", [n3.strip() or "KPI 3"])
  1568	            run_query("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi4'", [n4.strip() or "KPI 4"])
  1569	            log_action(username, "UPDATE_KPI_LABELS", "Updated KPI label names")
  1570	            st.success("✅ KPI labels updated successfully!")
  1571	            st.rerun()
  1572	    
  1573	    with tab2:
  1574	        st.markdown("### Configure KPI Weights (Total must equal 100%)")
  1575	        w1, w2, w3, w4 = get_kpi_weights()
  1576	        
  1577	        col_w1, col_w2 = st.columns(2)
  1578	        
  1579	        with col_w1:
  1580	            nw1 = st.number_input(f"Weight for {kpi1_lbl}", 0, 100, w1, key="weight_1")
  1581	            nw2 = st.number_input(f"Weight for {kpi2_lbl}", 0, 100, w2, key="weight_2")
  1582	        
  1583	        with col_w2:
  1584	            nw3 = st.number_input(f"Weight for {kpi3_lbl}", 0, 100, w3, key="weight_3")
  1585	            nw4 = st.number_input(f"Weight for {kpi4_lbl}", 0, 100, w4, key="weight_4")
  1586	        
  1587	        total_weight = nw1 + nw2 + nw3 + nw4
  1588	        
  1589	        if total_weight == 100:
  1590	            st.success(f"✅ Total Weight: {total_weight}% (Perfect!)")
  1591	        else:
  1592	            st.error(f"❌ Total Weight: {total_weight}% (Must be exactly 100%)")
  1593	        
  1594	        if st.button("💾 Save Weights", use_container_width=True, type="primary"):
  1595	            if total_weight == 100:
  1596	                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi1'", [nw1])
  1597	                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi2'", [nw2])
  1598	                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi3'", [nw3])
  1599	                run_query("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi4'", [nw4])
  1600	                log_action(username, "UPDATE_KPI_WEIGHTS", f"Updated weights: {nw1},{nw2},{nw3},{nw4}")
  1601	                st.success("✅ KPI weights saved successfully!")
  1602	                st.rerun()
  1603	            else:
  1604	                st.error("⚠️ Total weight must equal 100%. Please adjust values.")
  1605	    
  1606	    with tab3:
  1607	        st.markdown("### Configure Rating Thresholds")
  1608	        ex, gd, av = get_rating_rules()
  1609	        
  1610	        col_r1, col_r2, col_r3 = st.columns(3)
  1611	        
  1612	        with col_r1:
  1613	            nex = st.number_input("🌟 Excellent Minimum", 0, 100, ex, key="rating_ex")
  1614	        with col_r2:
  1615	            ngd = st.number_input("👍 Good Minimum", 0, 100, gd, key="rating_gd")
  1616	        with col_r3:
  1617	            nav = st.number_input("📊 Average Minimum", 0, 100, av, key="rating_av")
  1618	        
  1619	        st.info(f"""
  1620	        **Rating Logic Preview:**
  1621	        - Score ≥ {nex} → 🌟 Excellent
  1622	        - Score ≥ {ngd} → 👍 Good
  1623	        - Score ≥ {nav} → 📊 Average
  1624	        - Score < {nav} → ⚠️ Needs Improvement
  1625	        """)
  1626	        
  1627	        if st.button("💾 Save Rating Rules", use_container_width=True, type="primary"):
  1628	            if nex >= ngd >= nav:
  1629	                run_query("""
  1630	                    UPDATE rating_rules 
  1631	                    SET excellent_min=%s, good_min=%s, average_min=%s 
  1632	                    WHERE id=1
  1633	                """, [nex, ngd, nav])
  1634	                log_action(username, "UPDATE_RATING_RULES", f"Updated thresholds: {nex},{ngd},{nav}")
  1635	                st.success("✅ Rating rules saved successfully!")
  1636	                st.rerun()
  1637	            else:
  1638	                st.error("⚠️ Rule must satisfy: Excellent ≥ Good ≥ Average")
  1639	    
  1640	    with tab4:
  1641	        st.markdown("### System Permissions")
  1642	        
  1643	        cur_import = get_setting("allow_import", "1") == "1"
  1644	        cur_edit_del = get_setting("allow_edit_delete", "1") == "1"
  1645	        
  1646	        col_sys1, col_sys2 = st.columns(2)
  1647	        
  1648	        with col_sys1:
  1649	            allow_import = st.checkbox("📤 Allow CSV Import (Admin)", value=cur_import)
  1650	        
  1651	        with col_sys2:
  1652	            allow_edit_del = st.checkbox("✏️ Allow Edit/Delete Records", value=cur_edit_del)
  1653	        
  1654	        if st.button("💾 Save System Settings", use_container_width=True, type="primary"):
  1655	            set_setting("allow_import", "1" if allow_import else "0")
  1656	            set_setting("allow_edit_delete", "1" if allow_edit_del else "0")
  1657	            log_action(username, "UPDATE_SYSTEM_SETTINGS", 
  1658	                      f"Import:{allow_import}, Edit/Delete:{allow_edit_del}")
  1659	            st.success("✅ System settings saved!")
  1660	            st.rerun()
  1661	        
  1662	        st.markdown("---")
  1663	        st.markdown("### 📊 System Information")
  1664	        
  1665	        total_users = len(run_query("SELECT id FROM users", fetch=True) or [])
  1666	        total_emps = len(run_query("SELECT id FROM employees", fetch=True) or [])
  1667	        total_depts = len(run_query("SELECT id FROM departments", fetch=True) or [])
  1668	        total_entries = len(run_query("SELECT id FROM kpi_entries", fetch=True) or [])
  1669	        
  1670	        col_info1, col_info2, col_info3, col_info4 = st.columns(4)
  1671	        col_info1.metric("👥 Total Users", total_users)
  1672	        col_info2.metric("👤 Total Employees", total_emps)
  1673	        col_info3.metric("🏢 Total Departments", total_depts)
  1674	        col_info4.metric("📝 Total KPI Entries", total_entries)
  1675	    
  1676	    st.markdown("</div>", unsafe_allow_html=True)
  1677	
  1678	# ============================================================
  1679	# FOOTER
  1680	# ============================================================
  1681	st.markdown("<br>", unsafe_allow_html=True)
  1682	st.markdown('<div class="card" style="text-align:center">', unsafe_allow_html=True)
  1683	st.markdown(f"""
  1684	<div class='small'>
  1685	    <b>Yash Gallery KPI Management System v3.0</b><br>
  1686	    👤 Logged in as: <b>{full_name}</b> ({user_role.upper()}) | 🕒 Session Active<br>
  1687	    🔐 Role-Based Access • 👥 Multi-User Support • 📋 Complete Audit Trail • 📊 Real-Time Analytics<br>
  1688	    © 2024 Yash Gallery | Built with ❤️ using Streamlit + PostgreSQL (Neon Database)<br>
  1689	    🚀 Enterprise-Ready • 🔒 Secure • 📈 Scalable
  1690	</div>
  1691	""", unsafe_allow_html=True)
  1692	st.markdown("</div>", unsafe_allow_html=True)
