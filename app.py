import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# ---------- DB CONNECTION ----------
conn = sqlite3.connect("kpi_data.db", check_same_thread=False)
cursor = conn.cursor()
# ---------- DB INIT (Cloud safe) ----------
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
conn.commit()


# ---------- UI ----------
st.set_page_config(page_title="Yash Gallery – KPI System", layout="wide")

st.title("📊 Yash Gallery – KPI System")
st.caption("Simple KPI software – Phase 1")

st.subheader("Employee KPI Entry")

col1, col2 = st.columns(2)

with col1:
    employee_name = st.text_input("Employee Name")
with col2:
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

# ---------- CALCULATE ----------
if st.button("Calculate & Save"):
    if not employee_name.strip():
        st.warning("Employee Name required")
    else:
        total = kpi1 + kpi2 + kpi3 + kpi4

        if total >= 80:
            rating = "Excellent"
        elif total >= 60:
            rating = "Good"
        elif total >= 40:
            rating = "Average"
        else:
            rating = "Needs Improvement"

        cursor.execute("""
            INSERT INTO kpi_entries
            (employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            employee_name.strip(), department,
            kpi1, kpi2, kpi3, kpi4,
            total, rating,
            datetime.now().isoformat(sep=" ", timespec="seconds")
        ))
        conn.commit()

        st.success(f"Total Score: {total} | Rating: {rating}")

# ---------- SHOW DATA ----------
st.divider()
st.subheader("Filters")

# Department list (DB se unique)
dept_rows = cursor.execute(
    "SELECT DISTINCT department FROM kpi_entries WHERE department IS NOT NULL"
).fetchall()
dept_list = sorted([r[0] for r in dept_rows if r[0]])

colf1, colf2 = st.columns(2)
with colf1:
    dept_filter = st.selectbox("Department Filter", ["All"] + dept_list)

with colf2:
    # user empty bhi chod sakta hai
    date_range = st.date_input("Date Range", [])

# ---------- QUERY ----------
base_q = """
SELECT employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at
FROM kpi_entries
WHERE 1=1
"""
params = []

if dept_filter != "All":
    base_q += " AND department = ?"
    params.append(dept_filter)

# date_range agar user ne select kiya ho (start,end)
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
    base_q += " AND date(created_at) BETWEEN date(?) AND date(?)"
    params.append(str(start_date))
    params.append(str(end_date))

base_q += " ORDER BY created_at DESC"

rows = cursor.execute(base_q, params).fetchall()

# ---------- SUMMARY ----------
total_records = len(rows)

if total_records > 0:
    scores = [r[6] for r in rows]  # total_score index
    avg_score = round(sum(scores) / total_records, 2)
    best_score = max(scores)
    worst_score = min(scores)
else:
    avg_score = best_score = worst_score = 0

st.subheader("Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Records", total_records)
c2.metric("Average Score", avg_score)
c3.metric("Best Score", best_score)
c4.metric("Worst Score", worst_score)

# ---------- STEP 15: Department-wise Average Score ----------
if total_records > 0:
    st.subheader("Department-wise Average Score")

    dept_scores = {}
    for r in rows:
        dept = r[1]      # department
        score = r[6]     # total_score
        if dept:
            dept_scores.setdefault(dept, []).append(score)

    if dept_scores:
        dept_avg = {d: round(sum(v) / len(v), 2) for d, v in dept_scores.items()}
        dept_df = pd.DataFrame(dept_avg.items(), columns=["Department", "Average Score"])
        st.bar_chart(dept_df.set_index("Department"))

# ---------- TABLE ----------
st.subheader("Saved KPI Records")

df = pd.DataFrame(rows, columns=[
    "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
    "Total Score", "Rating", "Created At"
])
import io

# Export to Excel
output = io.BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="KPI Records")

st.download_button(
    label="⬇️ Download Excel",
    data=output.getvalue(),
    file_name="kpi_records.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
st.dataframe(df, use_container_width=True)
