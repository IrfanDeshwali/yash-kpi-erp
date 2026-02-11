import os
import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# ==================================================
# PAGE
# ==================================================
st.set_page_config(page_title="Yash Gallery – KPI System", page_icon="📊", layout="wide")

# ==================================================
# DB URL BUILDER (Short secrets -> URL)
# ==================================================
def build_db_url_from_secrets() -> str | None:
    try:
        user = str(st.secrets.get("DB_USER", "")).strip()
        pwd = str(st.secrets.get("DB_PASSWORD", "")).strip()
        host = str(st.secrets.get("DB_HOST", "")).strip()
        dbn = str(st.secrets.get("DB_NAME", "")).strip()
        params = str(st.secrets.get("DB_PARAMS", "")).strip()
    except Exception:
        return None

    if not (user and pwd and host and dbn):
        return None

    pwd_enc = quote_plus(pwd)
    url = f"postgresql://{user}:{pwd_enc}@{host}/{dbn}"
    if params:
        url += f"?{params}"
    return url

def get_database_url() -> str:
    url = build_db_url_from_secrets()
    if url:
        return url

    # Optional: if you ever manage to set DATABASE_URL
    try:
        if "DATABASE_URL" in st.secrets:
            return str(st.secrets["DATABASE_URL"]).strip()
    except Exception:
        pass

    # Optional: env var
    env_url = os.getenv("DATABASE_URL", "").strip()
    if env_url:
        return env_url

    # Fallback SQLite (local only)
    os.makedirs("data", exist_ok=True)
    sqlite_path = os.path.abspath(os.path.join("data", "kpi_data.db"))
    return f"sqlite:///{sqlite_path}"

@st.cache_resource
def get_engine():
    db_url = get_database_url()

    # Ensure sslmode on postgres if missing
    if db_url.startswith("postgres") and "sslmode=" not in db_url:
        joiner = "&" if "?" in db_url else "?"
        db_url = db_url + f"{joiner}sslmode=require"

    # Use psycopg driver (best for Python 3.13)
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return create_engine(db_url, pool_pre_ping=True, future=True)

engine = get_engine()

def is_postgres() -> bool:
    return engine.url.get_backend_name() in ("postgresql", "postgres")

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def compute_rating(total: int) -> str:
    # total range 4..400
    if total >= 320:
        return "Excellent"
    if total >= 240:
        return "Good"
    if total >= 160:
        return "Average"
    return "Needs Improvement"

# ==================================================
# UI CSS (Glass + white strips)
# ==================================================
st.markdown("""
<style>
.stApp{
  background:
    radial-gradient(900px 600px at 12% 10%, rgba(99,102,241,0.40), transparent 55%),
    radial-gradient(800px 600px at 88% 18%, rgba(56,189,248,0.35), transparent 55%),
    radial-gradient(900px 800px at 55% 95%, rgba(244,114,182,0.30), transparent 55%),
    linear-gradient(180deg, rgba(248,250,252,1) 0%, rgba(241,245,249,1) 100%);
}
.block-container{ max-width: 1320px; padding-top: 1rem; padding-bottom: 2rem; }

.glass{
  border-radius: 22px;
  border: 1px solid rgba(255,255,255,0.60);
  background: rgba(255,255,255,0.44);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 18px 50px rgba(15,23,42,0.10);
}
.glassHeader{ padding: 14px 16px; border-radius: 22px; }
.title{ font-size: 44px; font-weight: 900; letter-spacing: -0.03em; margin: 0; display:flex; gap:10px; align-items:center; }
.sub{ margin-top: 6px; color: rgba(30,41,59,0.75); }

.whiteStrip{
  display:flex; align-items:center; justify-content:space-between; gap:12px;
  padding: 10px 14px; border-radius: 18px;
  background: rgba(255,255,255,0.88);
  border: 1px solid rgba(255,255,255,0.98);
  box-shadow: 0 10px 30px rgba(15,23,42,0.08);
}
.stripTitle{ font-size: 22px; font-weight: 900; margin: 0; color: rgba(15,23,42,0.90); }

.stTabs [data-baseweb="tab-list"]{
  gap: 6px; padding: 6px; border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.55);
  background: rgba(255,255,255,0.35);
  backdrop-filter: blur(16px);
}
.stTabs [data-baseweb="tab"]{ height: 40px; border-radius: 14px; padding: 0 14px; font-weight: 850; }
.stTabs [aria-selected="true"]{
  background: rgba(255,255,255,0.78) !important;
  border: 1px solid rgba(255,255,255,0.78) !important;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="datepicker"] > div { border-radius: 16px !important; }

.stButton>button, .stDownloadButton>button{
  border-radius: 16px !important;
  padding: 0.62rem 1.05rem !important;
  font-weight: 850 !important;
}

[data-testid="stSidebar"]{ background: transparent !important; border-right: none !important; }
.drawerCard{
  border-radius: 22px; padding: 14px;
  border: 1px solid rgba(255,255,255,0.55);
  background: rgba(255,255,255,0.45);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 18px 50px rgba(15,23,42,0.12);
}
.metricGlass{
  border-radius: 18px; padding: 14px;
  border: 1px solid rgba(255,255,255,0.60);
  background: rgba(255,255,255,0.45);
  backdrop-filter: blur(16px);
  box-shadow: 0 14px 40px rgba(15,23,42,0.08);
}
.small-note{ color: rgba(30,41,59,0.65); font-size: 12px; }
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ==================================================
# DB INIT (works on Postgres + SQLite)
# ==================================================
def init_db():
    with engine.begin() as conn:
        backend = engine.url.get_backend_name()

        if backend in ("postgresql", "postgres"):
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS employees (
                    id SERIAL PRIMARY KEY,
                    employee_name TEXT UNIQUE,
                    department TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS kpi_entries (
                    id SERIAL PRIMARY KEY,
                    employee_name TEXT,
                    department TEXT,
                    kpi1 INTEGER,
                    kpi2 INTEGER,
                    kpi3 INTEGER,
                    kpi4 INTEGER,
                    total_score INTEGER,
                    rating TEXT,
                    created_at TEXT
                )
            """))
            # indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_kpi_dept ON kpi_entries(department)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_kpi_created ON kpi_entries(created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_kpi_emp ON kpi_entries(employee_name)"))

        else:
            # SQLite compatible
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_name TEXT UNIQUE,
                    department TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS kpi_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_name TEXT,
                    department TEXT,
                    kpi1 INTEGER,
                    kpi2 INTEGER,
                    kpi3 INTEGER,
                    kpi4 INTEGER,
                    total_score INTEGER,
                    rating TEXT,
                    created_at TEXT
                )
            """))
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_kpi_dept ON kpi_entries(department)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_kpi_created ON kpi_entries(created_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_kpi_emp ON kpi_entries(employee_name)"))
            except Exception:
                pass

init_db()

# ==================================================
# DB HELPERS
# ==================================================
def seed_if_empty():
    with engine.begin() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM employees")).scalar() or 0
        if cnt == 0:
            seed = [
                ("Irfan Deshwali", "Fabric"),
                ("Ajay", "Fabric"),
                ("Monika", "Merchant"),
                ("Jyoti", "Sampling"),
                ("Deepak", "Cutting"),
            ]
            for n, d in seed:
                try:
                    conn.execute(
                        text("INSERT INTO employees (employee_name, department, is_active, created_at) VALUES (:n,:d,1,:t)"),
                        {"n": n, "d": d, "t": now_str()}
                    )
                except Exception:
                    pass

seed_if_empty()

def get_active_employees_df() -> pd.DataFrame:
    return pd.read_sql(text("SELECT employee_name, department FROM employees WHERE is_active=1 ORDER BY employee_name"), engine)

def add_employee(name: str, dept: str):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO employees (employee_name, department, is_active, created_at) VALUES (:n,:d,1,:t)"),
                     {"n": name, "d": dept, "t": now_str()})

def deactivate_employee(name: str):
    with engine.begin() as conn:
        conn.execute(text("UPDATE employees SET is_active=0 WHERE employee_name=:n"), {"n": name})

def insert_kpi(emp: str, dept: str, k1: int, k2: int, k3: int, k4: int):
    total = int(k1 + k2 + k3 + k4)
    rating = compute_rating(total)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO kpi_entries
            (employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at)
            VALUES (:e,:d,:k1,:k2,:k3,:k4,:t,:r,:c)
        """), {"e": emp, "d": dept, "k1": k1, "k2": k2, "k3": k3, "k4": k4, "t": total, "r": rating, "c": now_str()})
    return total, rating

def load_kpis(dept_filter: str, date_range, name_search: str) -> pd.DataFrame:
    params = {}
    where = "WHERE 1=1"

    if dept_filter != "All":
        where += " AND department = :dept"
        params["dept"] = dept_filter

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        s, e = date_range
        if is_postgres():
            where += " AND CAST(created_at AS DATE) BETWEEN CAST(:s AS DATE) AND CAST(:e AS DATE)"
        else:
            where += " AND date(created_at) BETWEEN date(:s) AND date(:e)"
        params["s"] = str(s)
        params["e"] = str(e)

    if (name_search or "").strip():
        where += " AND lower(employee_name) LIKE :nm"
        params["nm"] = f"%{name_search.strip().lower()}%"

    sql = f"""
        SELECT id, employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at
        FROM kpi_entries
        {where}
        ORDER BY created_at DESC
    """
    return pd.read_sql(text(sql), engine, params=params)

def update_kpi_row(row_id: int, k1: int, k2: int, k3: int, k4: int):
    total = int(k1 + k2 + k3 + k4)
    rating = compute_rating(total)
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE kpi_entries
            SET kpi1=:k1, kpi2=:k2, kpi3=:k3, kpi4=:k4, total_score=:t, rating=:r
            WHERE id=:id
        """), {"k1": k1, "k2": k2, "k3": k3, "k4": k4, "t": total, "r": rating, "id": row_id})
    return total, rating

def delete_kpi_row(row_id: int):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM kpi_entries WHERE id=:id"), {"id": row_id})

# ==================================================
# HEADER
# ==================================================
st.markdown('<div class="glass glassHeader">', unsafe_allow_html=True)
st.markdown('<div class="title">📊 <span>Yash Gallery – KPI System</span></div>', unsafe_allow_html=True)
db_mode = "✅ Permanent DB (Postgres)" if is_postgres() else "⚠️ Local SQLite (Cloud restart may reset)"
st.markdown(f'<div class="sub">Premium Glass UI • Employee Master • Edit/Delete • {db_mode}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.write("")

# ==================================================
# SIDEBAR
# ==================================================
with st.sidebar:
    st.markdown('<div class="drawerCard">', unsafe_allow_html=True)
    st.markdown("""
      <div class="whiteStrip">
        <div class="stripTitle">🔎 Filters</div>
      </div>
    """, unsafe_allow_html=True)
    st.write("")

    dept_rows = pd.read_sql(text("""
        SELECT DISTINCT department FROM kpi_entries
        WHERE department IS NOT NULL AND department <> ''
        ORDER BY department
    """), engine)
    dept_list = dept_rows["department"].dropna().tolist() if not dept_rows.empty else []
    dept_filter = st.selectbox("Department", ["All"] + dept_list)

    date_range = st.date_input("Date Range (optional)", value=[])
    name_search = st.text_input("Search Employee", placeholder="Type name…")

    st.write("")
    with st.expander("👥 Manage Employees (Admin)", expanded=False):
        st.caption("Add employee here so Entry me dropdown aayega.")
        with st.form("add_emp_form", clear_on_submit=True):
            n = st.text_input("Employee Name (unique)")
            d = st.selectbox("Department", ["Fabric", "Merchant", "Sampling", "Cutting", "Finishing", "Dispatch", "Admin", "Sales", "Accounts"])
            add = st.form_submit_button("➕ Add Employee")

        if add:
            nm = (n or "").strip()
            if not nm:
                st.error("Name required.")
            else:
                try:
                    add_employee(nm, d)
                    st.success("Employee added ✅")
                    st.rerun()
                except Exception:
                    st.error("This name already exists.")

        st.write("")
        active_emp_df = get_active_employees_df()
        if not active_emp_df.empty:
            options = (active_emp_df["employee_name"] + "  •  " + active_emp_df["department"]).tolist()
            pick = st.selectbox("Deactivate Employee", ["Select..."] + options)
            if pick != "Select..." and st.button("Deactivate", use_container_width=True):
                emp_name = pick.split("  •  ")[0]
                deactivate_employee(emp_name)
                st.success("Deactivated ✅")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs(["📝 Entry", "📈 Dashboard", "📋 Records (Edit/Delete)"])

# TAB 1 – ENTRY
with tab1:
    st.markdown('<div class="glass" style="padding:18px;">', unsafe_allow_html=True)
    st.markdown("""
      <div class="whiteStrip">
        <div class="stripTitle">Employee KPI Entry</div>
      </div>
    """, unsafe_allow_html=True)
    st.write("")

    emp_df = get_active_employees_df()
    emp_names = emp_df["employee_name"].tolist() if not emp_df.empty else []
    emp_dept = dict(zip(emp_df["employee_name"], emp_df["department"])) if not emp_df.empty else {}

    with st.form("kpi_form", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            employee_name = st.selectbox("Employee Name", ["Select Employee..."] + emp_names)
        with c2:
            department = st.text_input("Department (auto)", value=emp_dept.get(employee_name, ""), disabled=True)

        k1, k2, k3, k4 = st.columns(4)
        v1 = k1.number_input("KPI 1 (1–100)", 1, 100, 1, 1)
        v2 = k2.number_input("KPI 2 (1–100)", 1, 100, 1, 1)
        v3 = k3.number_input("KPI 3 (1–100)", 1, 100, 1, 1)
        v4 = k4.number_input("KPI 4 (1–100)", 1, 100, 1, 1)

        submitted = st.form_submit_button("✅ Calculate & Save")

    if submitted:
        if employee_name == "Select Employee...":
            st.error("Please select employee.")
        else:
            total, rating = insert_kpi(employee_name, emp_dept.get(employee_name, ""), int(v1), int(v2), int(v3), int(v4))
            st.success(f"Saved ✅ | Total: {total} | Rating: {rating}")

    st.markdown('</div>', unsafe_allow_html=True)

# Load KPI data
df = load_kpis(dept_filter, date_range, name_search)

# TAB 2 – DASHBOARD
with tab2:
    st.markdown('<div class="glass" style="padding:18px;">', unsafe_allow_html=True)
    st.markdown("""
      <div class="whiteStrip">
        <div class="stripTitle">Dashboard</div>
      </div>
    """, unsafe_allow_html=True)
    st.write("")

    if df.empty:
        st.info("No data found for selected filters.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        for box, label, value in [
            (m1, "Total Records", len(df)),
            (m2, "Average Score", round(df["total_score"].mean(), 2)),
            (m3, "Best Score", int(df["total_score"].max())),
            (m4, "Worst Score", int(df["total_score"].min())),
        ]:
            with box:
                st.markdown('<div class="metricGlass">', unsafe_allow_html=True)
                st.metric(label, value)
                st.markdown('</div>', unsafe_allow_html=True)

        left, right = st.columns([1.2, 1])
        with left:
            by_dept = df.groupby("department", as_index=False)["total_score"].mean().sort_values("total_score", ascending=False)
            fig1 = px.bar(by_dept, x="department", y="total_score")
            fig1.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig1, use_container_width=True)

        with right:
            by_rating = df["rating"].value_counts().reset_index()
            by_rating.columns = ["rating", "count"]
            fig2 = px.pie(by_rating, names="rating", values="count", hole=0.55)
            fig2.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# TAB 3 – RECORDS (Edit/Delete)
with tab3:
    st.markdown('<div class="glass" style="padding:18px;">', unsafe_allow_html=True)
    st.markdown("""
      <div class="whiteStrip">
        <div class="stripTitle">Records (Edit / Delete)</div>
      </div>
    """, unsafe_allow_html=True)
    st.write("")

    if df.empty:
        st.info("No records available.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        export_df = df.rename(columns={
            "employee_name": "Employee",
            "department": "Department",
            "kpi1": "KPI1",
            "kpi2": "KPI2",
            "kpi3": "KPI3",
            "kpi4": "KPI4",
            "total_score": "Total Score",
            "rating": "Rating",
            "created_at": "Created At"
        }).drop(columns=["id"])

        st.download_button(
            "⬇️ Download CSV Backup",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name="kpi_records_backup.csv",
            mime="text/csv"
        )
        st.write("")
        st.dataframe(export_df, use_container_width=True, hide_index=True)

        st.write("")
        st.markdown("### ✏️ Edit / 🗑️ Delete")

        labels = df.apply(lambda r: f'#{int(r["id"])} | {r["employee_name"]} | {r["department"]} | {r["created_at"]}', axis=1).tolist()
        id_map = {labels[i]: int(df.iloc[i]["id"]) for i in range(len(labels))}
        pick = st.selectbox("Select record", ["Select..."] + labels)

        if pick != "Select...":
            rid = id_map[pick]
            rec = df[df["id"] == rid].iloc[0]

            colL, colR = st.columns([1.4, 1])

            with colL:
                st.markdown("**Edit values**")
                ek1, ek2, ek3, ek4 = st.columns(4)
                nk1 = ek1.number_input("KPI1", 1, 100, int(rec["kpi1"]), key=f"e1_{rid}")
                nk2 = ek2.number_input("KPI2", 1, 100, int(rec["kpi2"]), key=f"e2_{rid}")
                nk3 = ek3.number_input("KPI3", 1, 100, int(rec["kpi3"]), key=f"e3_{rid}")
                nk4 = ek4.number_input("KPI4", 1, 100, int(rec["kpi4"]), key=f"e4_{rid}")

                if st.button("💾 Update Record", use_container_width=True):
                    total, rating = update_kpi_row(rid, int(nk1), int(nk2), int(nk3), int(nk4))
                    st.success(f"Updated ✅ | Total: {total} | Rating: {rating}")
                    st.rerun()

            with colR:
                st.markdown("**Danger zone**")
                st.caption(f'Employee: **{rec["employee_name"]}**  | Dept: **{rec["department"]}**')
                st.caption(f'Created: **{rec["created_at"]}**')
                confirm = st.checkbox("I understand, delete permanently", key=f"del_{rid}")
                if st.button("🗑️ Delete Record", use_container_width=True, disabled=not confirm):
                    delete_kpi_row(rid)
                    st.success("Deleted ✅")
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
