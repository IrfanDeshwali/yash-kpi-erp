import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Yash Gallery – KPI System", page_icon="📊", layout="wide")

# =========================
# MODERN CSS
# =========================
st.markdown("""
<style>
/* Sidebar width */
[data-testid="stSidebar"] { width: 260px; }
[data-testid="stSidebar"] > div:first-child { width: 260px; }

/* App container */
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

/* Title */
.yg-title { font-size: 44px; font-weight: 800; letter-spacing: -0.02em; margin: 0; }
.yg-sub { color: #6b7280; margin-top: 6px; }

/* Soft cards */
.soft-card {
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 18px;
  padding: 16px 16px;
  background: rgba(255,255,255,0.75);
  backdrop-filter: blur(8px);
}

/* Small note */
.small-note {color:#6b7280; font-size: 12px;}
</style>
""", unsafe_allow_html=True)

# =========================
# DB
# =========================
@st.cache_resource
def get_conn():
    return sqlite3.connect("kpi_data.db", check_same_thread=False)

conn = get_conn()
cursor = conn.cursor()

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

# =========================
# HEADER
# =========================
st.markdown('<div class="soft-card">', unsafe_allow_html=True)
st.markdown('<div class="yg-title">📊 Yash Gallery – KPI System</div>', unsafe_allow_html=True)
st.markdown('<div class="yg-sub">Simple KPI software – Phase 1 (Modern UI Upgrade)</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# =========================
# SIDEBAR FILTERS
# =========================
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
st.sidebar.markdown('<div class="small-note">Tip: 2 dates select karo (start & end).</div>', unsafe_allow_html=True)

name_search = st.sidebar.text_input("Search Employee", placeholder="Type name…")

# =========================
# TABS
# =========================
tab1, tab2, tab3 = st.tabs(["📝 Entry", "📈 Dashboard", "📋 Records"])

# =========================
# TAB 1: ENTRY
# =========================
with tab1:
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (emp, department, int(kpi1), int(kpi2), int(kpi3), int(kpi4), total, rating, created_at))
            conn.commit()

            st.toast("Saved ✅", icon="✅")
            st.success(f"Saved ✅ | Total: {total} | Rating: {rating}")

# =========================
# LOAD DATA (shared)
# =========================
base_q = """
SELECT employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at
FROM kpi_entries
WHERE 1=1
"""
params = []

if dept_filter != "All":
    base_q += " AND department = ?"
    params.append(dept_filter)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
    base_q += " AND date(created_at) BETWEEN date(?) AND date(?)"
    params += [str(start_date), str(end_date)]

if name_search.strip():
    base_q += " AND lower(employee_name) LIKE ?"
    params.append(f"%{name_search.strip().lower()}%")

base_q += " ORDER BY created_at DESC"
rows = cursor.execute(base_q, params).fetchall()

df = pd.DataFrame(rows, columns=[
    "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
    "Total Score", "Rating", "Created At"
])

# SAFE datetime parsing (FIXED)
if not df.empty:
    df["Created At"] = pd.to_datetime(df["Created At"], errors="coerce")
    df = df.dropna(subset=["Created At"])
    df["Created Date"] = df["Created At"].dt.date
    df["Created At"] = df["Created At"].dt.strftime("%Y-%m-%d %H:%M:%S")

# =========================
# TAB 2: DASHBOARD
# =========================
with tab2:
    st.subheader("Summary & Insights")

    total_records = len(df)
    if total_records > 0:
        avg_score = round(df["Total Score"].mean(), 2)
        best_score = int(df["Total Score"].max())
        worst_score = int(df["Total Score"].min())
    else:
        avg_score = best_score = worst_score = 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Records", total_records)
    m2.metric("Average Score", avg_score)
    m3.metric("Best Score", best_score)
    m4.metric("Worst Score", worst_score)

    st.write("")

    if total_records > 0:
        c1, c2 = st.columns([1.2, 1])

        with c1:
            by_dept = df.groupby("Department", as_index=False)["Total Score"].mean().sort_values("Total Score", ascending=False)
            fig1 = px.bar(by_dept, x="Department", y="Total Score", title="Average Score by Department")
            st.plotly_chart(fig1, use_container_width=True)

        with c2:
            by_rating = df["Rating"].value_counts().reset_index()
            by_rating.columns = ["Rating", "Count"]
            fig2 = px.pie(by_rating, names="Rating", values="Count", title="Rating Distribution")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No records found for selected filters.")

# =========================
# TAB 3: RECORDS
# =========================
with tab3:
    st.subheader("Saved KPI Records")

    if df.empty:
        st.info("No data to show.")
    else:
        st.download_button(
            "⬇️ Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="kpi_records.csv",
            mime="text/csv"
        )

        st.write("")

        # Modern table (editable feel, but not updating DB in this version)
        st.dataframe(df, use_container_width=True, hide_index=True)
