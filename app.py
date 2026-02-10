import streamlit as st
import sqlite3
from datetime import datetime, date
import pandas as pd

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Yash Gallery – KPI System", page_icon="📊", layout="wide")

# -----------------------------
# DB helpers
# -----------------------------
DB_NAME = "kpi_data.db"

def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
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
    conn.commit()
    conn.close()

def calc_rating(total: int) -> str:
    if total >= 80:
        return "Excellent"
    elif total >= 60:
        return "Good"
    elif total >= 40:
        return "Average"
    else:
        return "Needs Improvement"

init_db()
conn = get_conn()
cursor = conn.cursor()

# -----------------------------
# Header
# -----------------------------
st.title("📊 Yash Gallery – KPI System")
st.caption("Phase 1 • KPI Entry + Filters + Summary + Charts")

# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.header("🔎 Filters")

dept_rows = cursor.execute(
    "SELECT DISTINCT department FROM kpi_entries WHERE department IS NOT NULL AND department != ''"
).fetchall()
dept_list = sorted([r[0] for r in dept_rows])

dept_filter = st.sidebar.selectbox("Department", ["All"] + dept_list)

date_range = st.sidebar.date_input("Date Range (optional)", value=())

st.sidebar.markdown("---")
st.sidebar.caption("Tip: Date Range me 2 dates select karo (start & end).")

# -----------------------------
# Layout: Entry + Summary/Records
# -----------------------------
left, right = st.columns([1.1, 1.4], gap="large")

# -----------------------------
# Entry Form (Left)
# -----------------------------
with left:
    st.subheader("Employee KPI Entry")

    with st.form("kpi_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            employee_name = st.text_input("Employee Name", placeholder="e.g., Sandeep Kumar")
        with c2:
            department = st.selectbox(
                "Department",
                ["Fabric", "Merchant", "Sampling", "Cutting", "Finishing", "Dispatch", "Admin", "Sales", "Accounts"]
            )

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            kpi1 = st.number_input("KPI 1", 0, 100, 0)
        with k2:
            kpi2 = st.number_input("KPI 2", 0, 100, 0)
        with k3:
            kpi3 = st.number_input("KPI 3", 0, 100, 0)
        with k4:
            kpi4 = st.number_input("KPI 4", 0, 100, 0)

        submitted = st.form_submit_button("✅ Calculate & Save", use_container_width=True)

    # Save action
    if submitted:
        if not employee_name.strip():
            st.error("Employee Name required.")
        else:
            total = int(kpi1 + kpi2 + kpi3 + kpi4)
            rating = calc_rating(total)

            cursor.execute("""
                INSERT INTO kpi_entries
                (employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                employee_name.strip(), department,
                int(kpi1), int(kpi2), int(kpi3), int(kpi4),
                total, rating,
                datetime.now().isoformat(timespec="seconds")
            ))
            conn.commit()

            st.success(f"Saved ✅ | Total: {total} | Rating: {rating}")

    st.markdown("---")
    st.caption("Scoring Rule: 80+ Excellent • 60–79 Good • 40–59 Average • <40 Needs Improvement")

# -----------------------------
# Query data with filters
# -----------------------------
base_q = """
SELECT employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at
FROM kpi_entries
WHERE 1=1
"""
params = []

if dept_filter != "All":
    base_q += " AND department = ?"
    params.append(dept_filter)

# Date filter (2 dates selected)
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
    base_q += " AND date(created_at) BETWEEN date(?) AND date(?)"
    params.append(str(start_date))
    params.append(str(end_date))

base_q += " ORDER BY datetime(created_at) DESC"

rows = cursor.execute(base_q, params).fetchall()

df = pd.DataFrame(rows, columns=[
    "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
    "Total Score", "Rating", "Created At"
])

# -----------------------------
# Right panel: Summary + Charts + Table
# -----------------------------
with right:
    st.subheader("Summary & Records")

    total_records = len(df)
    if total_records > 0:
        avg_score = round(df["Total Score"].mean(), 2)
        best_score = int(df["Total Score"].max())
        worst_score = int(df["Total Score"].min())
    else:
        avg_score = 0
        best_score = 0
        worst_score = 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Records", total_records)
    m2.metric("Average Score", avg_score)
    m3.metric("Best Score", best_score)
    m4.metric("Worst Score", worst_score)

    st.markdown("---")

    # Charts
    if total_records > 0:
        c1, c2 = st.columns(2)

        with c1:
            st.caption("Department-wise Average Score")
            dept_avg = df.groupby("Department")["Total Score"].mean().sort_values(ascending=False).reset_index()
            st.bar_chart(dept_avg, x="Department", y="Total Score")

        with c2:
            st.caption("Daily Average Score (by Created Date)")
            df["Created Date"] = pd.to_datetime(df["Created At"]).dt.date
            daily_avg = df.groupby("Created Date")["Total Score"].mean().reset_index()
            st.line_chart(daily_avg, x="Created Date", y="Total Score")

        st.markdown("---")

    # Records table + download
    st.subheader("Saved KPI Records")

    st.dataframe(df.drop(columns=["Created Date"], errors="ignore"), use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download CSV",
        data=csv,
        file_name="kpi_records.csv",
        mime="text/csv",
        use_container_width=True
    )

# Close conn at end (safe)
# conn.close()
