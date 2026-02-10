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
# iOS GLASS UI (GLOBAL CSS)
# =========================
st.markdown("""
<style>
/* ===== iOS gradient background ===== */
.stApp {
  background:
    radial-gradient(1200px 700px at 12% 12%, rgba(99,102,241,0.35), transparent 60%),
    radial-gradient(900px 600px at 88% 18%, rgba(56,189,248,0.30), transparent 55%),
    radial-gradient(1000px 800px at 55% 95%, rgba(244,114,182,0.25), transparent 55%),
    linear-gradient(180deg, rgba(248,250,252,1) 0%, rgba(241,245,249,1) 100%);
}

/* ===== layout ===== */
.block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1280px; }

/* ===== sidebar as glass drawer ===== */
[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.35) !important;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-right: 1px solid rgba(255,255,255,0.6);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }

/* sidebar width */
[data-testid="stSidebar"] { width: 290px; }
[data-testid="stSidebar"] > div:first-child { width: 290px; }

/* ===== glass cards ===== */
.glass {
  border-radius: 22px;
  padding: 18px 18px;
  border: 1px solid rgba(255,255,255,0.60);
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.08);
}

/* ===== header ===== */
.title { font-size: 46px; font-weight: 900; letter-spacing: -0.03em; margin: 0; }
.sub { color: rgba(30,41,59,0.72); margin-top: 6px; }
.h2 { font-size: 24px; font-weight: 850; margin: 0 0 10px 0; }
.small-note {color: rgba(30,41,59,0.6); font-size: 12px;}

/* ===== inputs look softer ===== */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="datepicker"] > div {
  border-radius: 16px !important;
}

/* ===== buttons ===== */
.stButton>button, .stDownloadButton>button {
  border-radius: 16px !important;
  padding: 0.62rem 1.05rem !important;
  font-weight: 800 !important;
}

/* ===== iOS-like tabs (pill) ===== */
.stTabs [data-baseweb="tab-list"]{
  gap: 8px;
  background: rgba(255,255,255,0.40);
  border: 1px solid rgba(255,255,255,0.60);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 6px;
  border-radius: 18px;
}
.stTabs [data-baseweb="tab"]{
  height: 42px;
  border-radius: 14px;
  padding: 0px 14px;
  font-weight: 800;
}
.stTabs [aria-selected="true"]{
  background: rgba(255,255,255,0.75) !important;
  border: 1px solid rgba(255,255,255,0.75) !important;
}

/* ===== metrics glass ===== */
.metric-glass {
  border-radius: 18px;
  padding: 14px 14px;
  border: 1px solid rgba(255,255,255,0.60);
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

/* ===== plotly container rounding ===== */
.js-plotly-plot, .plot-container {
  border-radius: 18px !important;
}

/* ===== hide footer ===== */
footer {visibility: hidden;}
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
# HEADER (GLASS)
# =========================
st.markdown('<div class="glass">', unsafe_allow_html=True)
st.markdown('<div class="title">📊 Yash Gallery – KPI System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">iOS Glass UI • Phase 1 • Entry → Dashboard → Records</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.write("")

# =========================
# SIDEBAR (GLASS DRAWER LOOK)
# =========================
st.sidebar.markdown("### 🔎 Filters")
st.sidebar.caption("iOS style drawer")

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

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Quick Actions")
show_latest = st.sidebar.toggle("Show last 50 records", value=True)
st.sidebar.markdown('<div class="small-note">Toggle ON = faster load</div>', unsafe_allow_html=True)

# =========================
# TABS
# =========================
tab1, tab2, tab3 = st.tabs(["📝 Entry", "📈 Dashboard", "📋 Records"])

# =========================
# TAB 1: ENTRY (GLASS)
# =========================
with tab1:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown('<div class="h2">Employee KPI Entry</div>', unsafe_allow_html=True)

    with st.form("kpi_form", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            employee_name = st.text_input("Employee Name", placeholder="e.g., Irfan Deshwali")
        with c2:
            department = st.selectbox(
                "Department",
                ["Fabric", "Merchant", "Sampling", "Cutting", "Finishing", "Dispatch", "Admin", "Sales", "Accounts"]
            )

        st.caption("KPI values (1–100) • iOS stepper feel")
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

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# LOAD FILTERED DATA
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
if show_latest:
    base_q += " LIMIT 50"

rows = cursor.execute(base_q, params).fetchall()

df = pd.DataFrame(rows, columns=[
    "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
    "Total Score", "Rating", "Created At"
])

if not df.empty:
    df["Created At"] = pd.to_datetime(df["Created At"], errors="coerce")
    df = df.dropna(subset=["Created At"])
    df["Created Date"] = df["Created At"].dt.date
    df["Created At"] = df["Created At"].dt.strftime("%Y-%m-%d %H:%M:%S")

# =========================
# TAB 2: DASHBOARD (GLASS)
# =========================
with tab2:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown('<div class="h2">Summary & Insights</div>', unsafe_allow_html=True)

    total_records = len(df)
    if total_records:
        avg_score = round(df["Total Score"].mean(), 2)
        best_score = int(df["Total Score"].max())
        worst_score = int(df["Total Score"].min())
    else:
        avg_score = best_score = worst_score = 0

    a, b, c, d = st.columns(4)
    with a:
        st.markdown('<div class="metric-glass">', unsafe_allow_html=True)
        st.metric("Total Records", total_records)
        st.markdown('</div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="metric-glass">', unsafe_allow_html=True)
        st.metric("Average Score", avg_score)
        st.markdown('</div>', unsafe_allow_html=True)
    with c:
        st.markdown('<div class="metric-glass">', unsafe_allow_html=True)
        st.metric("Best Score", best_score)
        st.markdown('</div>', unsafe_allow_html=True)
    with d:
        st.markdown('<div class="metric-glass">', unsafe_allow_html=True)
        st.metric("Worst Score", worst_score)
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("")

    if total_records:
        left, right = st.columns([1.2, 1])

        with left:
            st.markdown("**Average Score by Department**")
            by_dept = df.groupby("Department", as_index=False)["Total Score"].mean().sort_values("Total Score", ascending=False)
            fig1 = px.bar(by_dept, x="Department", y="Total Score")
            fig1.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
            st.plotly_chart(fig1, use_container_width=True)

        with right:
            st.markdown("**Rating Distribution**")
            by_rating = df["Rating"].value_counts().reset_index()
            by_rating.columns = ["Rating", "Count"]
            fig2 = px.pie(by_rating, names="Rating", values="Count", hole=0.55)
            fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No records found for selected filters.")

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# TAB 3: RECORDS (GLASS)
# =========================
with tab3:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown('<div class="h2">Saved KPI Records</div>', unsafe_allow_html=True)

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
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown('</div>', unsafe_allow_html=True)
