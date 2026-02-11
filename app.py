import streamlit as st
import psycopg2
from datetime import datetime
import pandas as pd

# ---------------- PAGE ----------------
st.set_page_config(page_title="Yash Gallery – KPI System", layout="wide")

# ---- Sidebar width CSS ----
st.markdown("""
<style>
[data-testid="stSidebar"] { width: 280px; }
[data-testid="stSidebar"] > div:first-child { width: 280px; }
.small-note {color:#6b7280; font-size: 12px;}
</style>
""", unsafe_allow_html=True)

# ---------------- DB ----------------
@st.cache_resource
def get_conn():
    return psycopg2.connect(st.secrets["NEON_DATABASE_URL"])

conn = get_conn()
cursor = conn.cursor()

cursor.execute("""
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
conn.commit()
# ---------------- HEADER ----------------
st.title("📊 Yash Gallery – KPI System")
st.caption("Simple KPI software – Phase 1")

# ---------------- ENTRY (FORM) ----------------
st.subheader("Employee KPI Entry")

with st.form("kpi_form", clear_on_submit=True):
    c1, c2 = st.columns([2, 1])

    with c1:
        employee_name = st.text_input("Employee Name", placeholder="e.g., Irfan Deshwali")
    with c2:
        department = st.selectbox(
            "Department",
            ["Fabric", "Merchant", "Sampling", "Cutting", "Finishing", "Dispatch", "Admin", "Sales", "Accounts"]
        )

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
    emp = (employee_name or "").strip()
    if emp == "":
        st.error("Employee Name required.")
    else:
        total = int(kpi1 + kpi2 + kpi3 + kpi4)

        if total >= 80:
            rating = "Excellent"
        elif total >= 60:
            rating = "Good"
        elif total >= 40:
            rating = "Average"
        else:
            rating = "Needs Improvement"

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO kpi_entries
            (employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (emp, department, int(kpi1), int(kpi2), int(kpi3), int(kpi4), total, rating, created_at))
        conn.commit()

        st.success(f"Saved ✅ | Total: {total} | Rating: {rating}")

st.divider()

# ---------------- FILTERS (SIDEBAR) ----------------
st.sidebar.header("🔎 Filters")

dept_rows = cursor.execute("""
SELECT DISTINCT department
FROM kpi_entries
WHERE department IS NOT NULL AND department <> ''
ORDER BY department
""").fetchall()

dept_list = [r[0] for r in dept_rows] if dept_rows else []
dept_filter = st.sidebar.selectbox("Department", ["All"] + dept_list)

date_range = st.sidebar.date_input("Date Range (optional)", value=[])
st.sidebar.markdown('<div class="small-note">Tip: Date Range me 2 dates select karo (start & end).</div>', unsafe_allow_html=True)

# ---------------- QUERY ----------------
base_q = """
SELECT employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at
FROM kpi_entries
WHERE 1=1
"""
params = []

if dept_filter != "All":
    base_q += " AND department = %s"
    params.append(dept_filter)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
    base_q += " AND DATE(created_at) BETWEEN %s AND %s"
    params.append(str(start_date))
    params.append(str(end_date))

base_q += " ORDER BY datetime(created_at) DESC"

rows = cursor.execute(base_q, params).fetchall()

# ---------------- SUMMARY ----------------
st.subheader("Summary")

total_records = len(rows)
if total_records > 0:
    scores = [r[6] for r in rows]
    avg_score = round(sum(scores) / total_records, 2)
    best_score = max(scores)
    worst_score = min(scores)
else:
    avg_score = best_score = worst_score = 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Records", total_records)
m2.metric("Average Score", avg_score)
m3.metric("Best Score", best_score)
m4.metric("Worst Score", worst_score)

# ---------------- TABLE ----------------
st.subheader("Saved KPI Records")

df = pd.DataFrame(rows, columns=[
    "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
    "Total Score", "Rating", "Created At"
])

st.dataframe(df, use_container_width=True, hide_index=True)
