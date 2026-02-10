import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px

# ==================================================
# PAGE
# ==================================================
st.set_page_config(page_title="Yash Gallery – KPI System", page_icon="📊", layout="wide")

# ==================================================
# CSS (Glass + White strips)
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
  background: rgba(255,255,255,0.85);
  border: 1px solid rgba(255,255,255,0.95);
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
  border-radius: 16px !important; padding: 0.62rem 1.05rem !important; font-weight: 850 !important;
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
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ==================================================
# DB
# ==================================================
@st.cache_resource
def get_conn():
    return sqlite3.connect("kpi_data.db", check_same_thread=False)

conn = get_conn()
cursor = conn.cursor()

# KPI entries
cursor.execute("""
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
""")

# Employee master
cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_name TEXT UNIQUE,
    department TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT
)
""")

# Indexes for performance
cursor.execute("CREATE INDEX IF NOT EXISTS idx_kpi_dept ON kpi_entries(department)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_kpi_created ON kpi_entries(created_at)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_kpi_emp ON kpi_entries(employee_name)")
conn.commit()

# ==================================================
# Helpers
# ==================================================
def compute_rating(total_score: int) -> str:
    # total_score range: 4..400
    if total_score >= 320:
        return "Excellent"
    if total_score >= 240:
        return "Good"
    if total_score >= 160:
        return "Average"
    return "Needs Improvement"

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_active_employees():
    rows = cursor.execute("""
        SELECT employee_name, department
        FROM employees
        WHERE is_active = 1
        ORDER BY employee_name
    """).fetchall()
    return rows

# Seed (optional): if empty, add some defaults
emp_count = cursor.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
if emp_count == 0:
    seed = [
        ("Irfan Deshwali", "Fabric"),
        ("Ajay", "Fabric"),
        ("Monika", "Merchant"),
        ("Jyoti", "Sampling"),
        ("Deepak", "Cutting"),
    ]
    for n, d in seed:
        try:
            cursor.execute("INSERT INTO employees (employee_name, department, is_active, created_at) VALUES (?,?,1,?)",
                           (n, d, now_str()))
        except Exception:
            pass
    conn.commit()

# ==================================================
# HEADER
# ==================================================
st.markdown('<div class="glass glassHeader">', unsafe_allow_html=True)
st.markdown('<div class="title">📊 <span>Yash Gallery – KPI System</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Premium Glass UI • Employee Master • Edit/Delete • Fast DB</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.write("")

# ==================================================
# SIDEBAR (Filters + Manage Employees)
# ==================================================
with st.sidebar:
    st.markdown('<div class="drawerCard">', unsafe_allow_html=True)

    st.markdown("""
      <div class="whiteStrip">
        <div class="stripTitle">🔎 Filters</div>
      </div>
    """, unsafe_allow_html=True)
    st.write("")

    # Dept filter from KPI table (distinct)
    dept_rows = cursor.execute("""
        SELECT DISTINCT department FROM kpi_entries
        WHERE department IS NOT NULL AND department <> ''
        ORDER BY department
    """).fetchall()
    dept_list = [r[0] for r in dept_rows] if dept_rows else []
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
                    cursor.execute("INSERT INTO employees (employee_name, department, is_active, created_at) VALUES (?,?,1,?)",
                                   (nm, d, now_str()))
                    conn.commit()
                    st.success("Employee added ✅")
                    st.rerun()
                except Exception:
                    st.error("This name already exists.")

        st.write("")

        act_rows = cursor.execute("""
            SELECT employee_name, department
            FROM employees
            WHERE is_active = 1
            ORDER BY employee_name
        """).fetchall()
        if act_rows:
            emp_names = [f"{r[0]}  •  {r[1]}" for r in act_rows]
            pick = st.selectbox("Deactivate Employee", ["Select..."] + emp_names)
            if pick != "Select..." and st.button("Deactivate", use_container_width=True):
                emp_name = pick.split("  •  ")[0]
                cursor.execute("UPDATE employees SET is_active = 0 WHERE employee_name = ?", (emp_name,))
                conn.commit()
                st.success("Deactivated ✅")
                st.rerun()
        else:
            st.info("No active employees.")

    st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs(["📝 Entry", "📈 Dashboard", "📋 Records (Edit/Delete)"])

# ==================================================
# TAB 1 – ENTRY (Employee Master dropdown + auto department)
# ==================================================
with tab1:
    st.markdown('<div class="glass" style="padding:18px;">', unsafe_allow_html=True)

    st.markdown("""
      <div class="whiteStrip">
        <div class="stripTitle">Employee KPI Entry</div>
      </div>
    """, unsafe_allow_html=True)
    st.write("")

    active_emps = get_active_employees()
    emp_names = [r[0] for r in active_emps]
    emp_dept_map = {r[0]: r[1] for r in active_emps}

    with st.form("kpi_form", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])

        with c1:
            employee_name = st.selectbox("Employee Name", ["Select Employee..."] + emp_names)
        with c2:
            auto_dept = emp_dept_map.get(employee_name, "")
            department = st.text_input("Department (auto)", value=auto_dept, disabled=True)

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            kpi1 = st.number_input("KPI 1 (1–100)", min_value=1, max_value=100, value=1, step=1)
        with k2:
            kpi2 = st.number_input("KPI 2 (1–100)", min_value=1, max_value=100, value=1, step=1)
        with k3:
            kpi3 = st.number_input("KPI 3 (1–100)", min_value=1, max_value=100, value=1, step=1)
        with k4:
            kpi4 = st.number_input("KPI 4 (1–100)", min_value=1, max_value=100, value=1, step=1)

        submitted = st.form_submit_button("✅ Calculate & Save")

    if submitted:
        if employee_name == "Select Employee...":
            st.error("Please select employee.")
        else:
            total = int(kpi1 + kpi2 + kpi3 + kpi4)
            rating = compute_rating(total)
            created_at = now_str()
            dept = emp_dept_map.get(employee_name, "")

            cursor.execute("""
                INSERT INTO kpi_entries
                (employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (employee_name, dept, int(kpi1), int(kpi2), int(kpi3), int(kpi4), total, rating, created_at))
            conn.commit()

            st.toast("Saved ✅", icon="✅")
            st.success(f"Saved ✅ | Total: {total} | Rating: {rating}")

    st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# LOAD DATA (filters)
# ==================================================
q = """
SELECT id, employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at
FROM kpi_entries
WHERE 1=1
"""
params = []

if dept_filter != "All":
    q += " AND department = ?"
    params.append(dept_filter)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    q += " AND date(created_at) BETWEEN date(?) AND date(?)"
    params += [str(date_range[0]), str(date_range[1])]

if (name_search or "").strip():
    q += " AND lower(employee_name) LIKE ?"
    params.append(f"%{name_search.strip().lower()}%")

q += " ORDER BY created_at DESC"
rows = cursor.execute(q, params).fetchall()

df = pd.DataFrame(rows, columns=[
    "ID", "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
    "Total Score", "Rating", "Created At"
])

# ==================================================
# TAB 2 – DASHBOARD
# ==================================================
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
            (m2, "Average Score", round(df["Total Score"].mean(), 2)),
            (m3, "Best Score", int(df["Total Score"].max())),
            (m4, "Worst Score", int(df["Total Score"].min())),
        ]:
            with box:
                st.markdown('<div class="metricGlass">', unsafe_allow_html=True)
                st.metric(label, value)
                st.markdown('</div>', unsafe_allow_html=True)

        left, right = st.columns([1.2, 1])
        with left:
            by_dept = df.groupby("Department", as_index=False)["Total Score"].mean().sort_values("Total Score", ascending=False)
            fig1 = px.bar(by_dept, x="Department", y="Total Score")
            fig1.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig1, use_container_width=True)

        with right:
            by_rating = df["Rating"].value_counts().reset_index()
            by_rating.columns = ["Rating", "Count"]
            fig2 = px.pie(by_rating, names="Rating", values="Count", hole=0.55)
            fig2.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# TAB 3 – RECORDS (Edit/Delete)
# ==================================================
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
        st.download_button(
            "⬇️ Download CSV",
            data=df.drop(columns=["ID"]).to_csv(index=False).encode("utf-8"),
            file_name="kpi_records.csv",
            mime="text/csv"
        )
        st.write("")

        # Show table (hide ID)
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

        st.write("")
        st.markdown("### ✏️ Edit / 🗑️ Delete a record")

        # Build selector labels
        labels = df.apply(lambda r: f'#{int(r["ID"])} | {r["Employee"]} | {r["Department"]} | {r["Created At"]}', axis=1).tolist()
        id_map = {labels[i]: int(df.iloc[i]["ID"]) for i in range(len(labels))}
        pick = st.selectbox("Select record", ["Select..."] + labels)

        if pick != "Select...":
            rid = id_map[pick]
            rec = cursor.execute("""
                SELECT id, employee_name, department, kpi1, kpi2, kpi3, kpi4, created_at
                FROM kpi_entries
                WHERE id = ?
            """, (rid,)).fetchone()

            if rec:
                _, emp, dept, k1, k2, k3, k4, created_at = rec

                colL, colR = st.columns([1.4, 1])

                with colL:
                    st.markdown("**Edit values**")
                    ek1, ek2, ek3, ek4 = st.columns(4)
                    nk1 = ek1.number_input("KPI1", 1, 100, int(k1), key=f"e1_{rid}")
                    nk2 = ek2.number_input("KPI2", 1, 100, int(k2), key=f"e2_{rid}")
                    nk3 = ek3.number_input("KPI3", 1, 100, int(k3), key=f"e3_{rid}")
                    nk4 = ek4.number_input("KPI4", 1, 100, int(k4), key=f"e4_{rid}")

                    if st.button("💾 Update Record", use_container_width=True):
                        total = int(nk1 + nk2 + nk3 + nk4)
                        rating = compute_rating(total)
                        cursor.execute("""
                            UPDATE kpi_entries
                            SET kpi1=?, kpi2=?, kpi3=?, kpi4=?, total_score=?, rating=?
                            WHERE id=?
                        """, (int(nk1), int(nk2), int(nk3), int(nk4), total, rating, rid))
                        conn.commit()
                        st.success("Updated ✅")
                        st.rerun()

                with colR:
                    st.markdown("**Danger zone**")
                    st.caption(f"Employee: **{emp}**  | Dept: **{dept}**")
                    st.caption(f"Created: **{created_at}**")
                    confirm = st.checkbox("I understand, delete this record permanently", key=f"del_{rid}")
                    if st.button("🗑️ Delete Record", use_container_width=True, disabled=not confirm):
                        cursor.execute("DELETE FROM kpi_entries WHERE id=?", (rid,))
                        conn.commit()
                        st.success("Deleted ✅")
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
