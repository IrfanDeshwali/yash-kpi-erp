import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# ---------------- PAGE ----------------
st.set_page_config(page_title="Yash Gallery – KPI Dashboard", layout="wide")

# ---------------- CLEAN LIGHT UI ----------------
st.markdown("""
<style>
.stApp {
  background: #f6f7fb;
}
html, body, [class*="css"] { color: #0f172a !important; }
.block-container { padding-top: 1.2rem; }
[data-testid="stSidebar"] { width: 300px; }
[data-testid="stSidebar"] > div:first-child { width: 300px; }

.card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 14px 16px;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
}
.small { color:#64748b; font-size:12px; }
hr { margin: 0.7rem 0 1rem 0; border-color: #e5e7eb; }

.stButton > button, .stDownloadButton > button {
  border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DB (NEON - AUTO RECONNECT) ----------------
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
            if fetch:
                return cur.fetchall()
            return None
    except psycopg2.InterfaceError:
        st.session_state["db_conn"] = None
        conn = get_conn()
        with conn.cursor() as cur:
            if many and data is not None:
                cur.executemany(query, data)
                return None
            cur.execute(query, params or [])
            if fetch:
                return cur.fetchall()
            return None

# Create table
run("""
CREATE TABLE IF NOT EXISTS kpi_entries (
    id SERIAL PRIMARY KEY,
    employee_name TEXT NOT NULL,
    department TEXT NOT NULL,
    kpi1 INTEGER,
    kpi2 INTEGER,
    kpi3 INTEGER,
    kpi4 INTEGER,
    total_score INTEGER,
    rating TEXT,
    created_at TIMESTAMP
)
""")

# ---------------- HELPERS ----------------
def calc_rating(total: int) -> str:
    # total max 400
    if total >= 320: return "Excellent"
    if total >= 240: return "Good"
    if total >= 160: return "Average"
    return "Needs Improvement"

def to_df(rows):
    return pd.DataFrame(rows, columns=[
        "ID", "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
        "Total Score", "Rating", "Created At"
    ])

# ---------------- HEADER ----------------
st.markdown('<div class="card">', unsafe_allow_html=True)
c1, c2 = st.columns([3, 2])
with c1:
    st.title("📊 Yash Gallery – KPI Dashboard")
    st.caption("Neon DB • Filters • Reports • Import/Export • Edit/Delete")
with c2:
    st.markdown("**Quick Tips**")
    st.markdown("<div class='small'>1) Filter sidebar se<br>2) Table me row select karke Edit/Delete<br>3) Export filtered CSV</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.header("🔎 Filters")

# Dept list
dept_rows = run("""
SELECT DISTINCT department
FROM kpi_entries
WHERE department IS NOT NULL AND department <> ''
ORDER BY department
""", fetch=True) or []
dept_list = [r[0] for r in dept_rows]
dept_filter = st.sidebar.selectbox("Department", ["All"] + dept_list)

# Employee list (based on dept)
emp_q = """
SELECT DISTINCT employee_name
FROM kpi_entries
WHERE employee_name IS NOT NULL AND employee_name <> ''
"""
emp_params = []
if dept_filter != "All":
    emp_q += " AND department = %s"
    emp_params.append(dept_filter)
emp_q += " ORDER BY employee_name"
emp_rows = run(emp_q, emp_params, fetch=True) or []
emp_list = [r[0] for r in emp_rows]
emp_filter = st.sidebar.selectbox("Employee", ["All"] + emp_list)

search_text = st.sidebar.text_input("Search name contains", placeholder="e.g., Irfan")
date_range = st.sidebar.date_input("Date Range (optional)", value=[])
st.sidebar.markdown("<div class='small'>Tip: Date range me 2 dates select karo (start & end).</div>", unsafe_allow_html=True)

# ---------------- ENTRY + ACTIONS ----------------
left, right = st.columns([2, 1], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("➕ Add KPI Entry")

    with st.form("add_form", clear_on_submit=True):
        a1, a2 = st.columns([2, 1])
        with a1:
            employee_name = st.text_input("Employee Name", placeholder="e.g., Irfan Deshwali")
        with a2:
            department = st.selectbox(
                "Department",
                ["Fabric", "Merchant", "Sampling", "Cutting", "Finishing", "Dispatch", "Admin", "Sales", "Accounts"]
            )

        k1, k2, k3, k4 = st.columns(4)
        with k1: v1 = st.number_input("KPI 1", 1, 100, 1, 1)
        with k2: v2 = st.number_input("KPI 2", 1, 100, 1, 1)
        with k3: v3 = st.number_input("KPI 3", 1, 100, 1, 1)
        with k4: v4 = st.number_input("KPI 4", 1, 100, 1, 1)

        submitted = st.form_submit_button("✅ Save Entry")

    if submitted:
        emp = (employee_name or "").strip()
        if emp == "":
            st.error("Employee Name required.")
        else:
            total = int(v1 + v2 + v3 + v4)
            rating = calc_rating(total)
            created_at = datetime.now()
            run("""
                INSERT INTO kpi_entries
                (employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [emp, department, int(v1), int(v2), int(v3), int(v4), total, rating, created_at])
            st.success(f"Saved ✅ | Total: {total} | Rating: {rating}")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📥 Export / 📤 Import")

    # We'll build df first (below), so placeholders here.
    st.markdown("<div class='small'>Export filtered data as CSV, or import CSV (same columns).</div>", unsafe_allow_html=True)

    uploaded = st.file_uploader("Import KPI CSV", type=["csv"])
    import_btn = st.button("📤 Import Now")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- FETCH FILTERED DATA ----------------
q = """
SELECT id, employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at
FROM kpi_entries
WHERE 1=1
"""
p = []

if dept_filter != "All":
    q += " AND department = %s"
    p.append(dept_filter)

if emp_filter != "All":
    q += " AND employee_name = %s"
    p.append(emp_filter)

if search_text.strip():
    q += " AND employee_name ILIKE %s"
    p.append(f"%{search_text.strip()}%")

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
    q += " AND DATE(created_at) BETWEEN %s AND %s"
    p.append(str(start_date))
    p.append(str(end_date))

q += " ORDER BY created_at DESC"

rows = run(q, p, fetch=True) or []
df = to_df(rows)

# ---------------- EXPORT (now that df exists) ----------------
with right:
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download CSV (Filtered)",
        data=csv_data,
        file_name="kpi_export.csv",
        mime="text/csv"
    )

    # ---------------- IMPORT logic ----------------
    if import_btn and uploaded is not None:
        try:
            imp = pd.read_csv(uploaded)

            required = ["Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4"]
            missing = [c for c in required if c not in imp.columns]
            if missing:
                st.error(f"CSV missing columns: {', '.join(missing)}")
            else:
                imp["Employee"] = imp["Employee"].astype(str).str.strip()
                imp["Department"] = imp["Department"].astype(str).str.strip()

                for col in ["KPI1", "KPI2", "KPI3", "KPI4"]:
                    imp[col] = pd.to_numeric(imp[col], errors="coerce").fillna(0).astype(int)

                imp["Total Score"] = imp["KPI1"] + imp["KPI2"] + imp["KPI3"] + imp["KPI4"]
                if "Rating" not in imp.columns:
                    imp["Rating"] = imp["Total Score"].apply(calc_rating)
                if "Created At" in imp.columns:
                    imp["Created At"] = pd.to_datetime(imp["Created At"], errors="coerce")
                else:
                    imp["Created At"] = pd.Timestamp.now()

                data_to_insert = []
                for _, r in imp.iterrows():
                    created = r["Created At"]
                    if pd.isna(created):
                        created = datetime.now()
                    else:
                        created = created.to_pydatetime()

                    data_to_insert.append((
                        r["Employee"], r["Department"],
                        int(r["KPI1"]), int(r["KPI2"]), int(r["KPI3"]), int(r["KPI4"]),
                        int(r["Total Score"]), str(r["Rating"]), created
                    ))

                run("""
                    INSERT INTO kpi_entries
                    (employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, many=True, data=data_to_insert)

                st.success(f"✅ Imported {len(data_to_insert)} rows")
                st.rerun()
        except Exception as e:
            st.error(f"Import failed: {e}")

# ---------------- DASHBOARD METRICS ----------------
st.write("")
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("📌 Dashboard Summary")

m1, m2, m3, m4 = st.columns(4)
if len(df) > 0:
    m1.metric("Total Records", int(len(df)))
    m2.metric("Average Score", round(float(df["Total Score"].mean()), 2))
    m3.metric("Best Score", int(df["Total Score"].max()))
    m4.metric("Worst Score", int(df["Total Score"].min()))
else:
    m1.metric("Total Records", 0)
    m2.metric("Average Score", 0)
    m3.metric("Best Score", 0)
    m4.metric("Worst Score", 0)

st.markdown("</div>", unsafe_allow_html=True)

# ---------------- CHARTS ----------------
st.write("")
cA, cB, cC = st.columns([1.2, 1, 1], gap="large")

with cA:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 Score Distribution")
    if len(df) > 0:
        fig = px.histogram(df, x="Total Score", nbins=20)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data to show.")
    st.markdown("</div>", unsafe_allow_html=True)

with cB:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🏭 Dept Average")
    if len(df) > 0:
        dept_avg = df.groupby("Department", as_index=False)["Total Score"].mean().sort_values("Total Score", ascending=False)
        fig = px.bar(dept_avg, x="Department", y="Total Score")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data to show.")
    st.markdown("</div>", unsafe_allow_html=True)

with cC:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📅 Daily Trend")
    if len(df) > 0:
        tmp = df.copy()
        tmp["Day"] = pd.to_datetime(tmp["Created At"]).dt.date
        trend = tmp.groupby("Day", as_index=False)["Total Score"].mean().sort_values("Day")
        fig = px.line(trend, x="Day", y="Total Score", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data to show.")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- TABLE + EDIT/DELETE ----------------
st.write("")
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("🗂 Records (Edit / Delete)")

if len(df) == 0:
    st.info("No records found with current filters.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# Select a record ID to edit/delete
selected_id = st.selectbox("Select Record ID to Edit/Delete", df["ID"].tolist())

row = df[df["ID"] == selected_id].iloc[0]

e1, e2, e3 = st.columns([1.1, 1.1, 1], gap="large")

with e1:
    st.markdown("### ✏️ Edit Record")
    edit_emp = st.text_input("Employee", value=str(row["Employee"]))
    edit_dept = st.text_input("Department", value=str(row["Department"]))

with e2:
    k1, k2 = st.columns(2)
    with k1:
        edit_kpi1 = st.number_input("KPI1", 1, 100, int(row["KPI1"]), 1, key="ek1")
        edit_kpi2 = st.number_input("KPI2", 1, 100, int(row["KPI2"]), 1, key="ek2")
    with k2:
        edit_kpi3 = st.number_input("KPI3", 1, 100, int(row["KPI3"]), 1, key="ek3")
        edit_kpi4 = st.number_input("KPI4", 1, 100, int(row["KPI4"]), 1, key="ek4")

with e3:
    st.markdown("### 🧾 Actions")
    new_total = int(edit_kpi1 + edit_kpi2 + edit_kpi3 + edit_kpi4)
    new_rating = calc_rating(new_total)
    st.write(f"**New Total:** {new_total}")
    st.write(f"**New Rating:** {new_rating}")

    colu, cold = st.columns(2)
    with colu:
        if st.button("💾 Update", use_container_width=True):
            empx = (edit_emp or "").strip()
            deptx = (edit_dept or "").strip()
            if empx == "" or deptx == "":
                st.error("Employee & Department required.")
            else:
                run("""
                    UPDATE kpi_entries
                    SET employee_name=%s, department=%s,
                        kpi1=%s, kpi2=%s, kpi3=%s, kpi4=%s,
                        total_score=%s, rating=%s
                    WHERE id=%s
                """, [empx, deptx, int(edit_kpi1), int(edit_kpi2), int(edit_kpi3), int(edit_kpi4),
                      new_total, new_rating, int(selected_id)])
                st.success("✅ Updated")
                st.rerun()

    with cold:
        if st.button("🗑 Delete", use_container_width=True):
            run("DELETE FROM kpi_entries WHERE id=%s", [int(selected_id)])
            st.warning("🗑 Deleted")
            st.rerun()

st.markdown("----")
st.caption("Tip: Filters change karke aap report nikal sakte ho. Export always filtered data download karta hai.")

st.subheader("📋 Filtered Records Table")
st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

st.markdown("</div>", unsafe_allow_html=True)
