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
/* Background */
.stApp{
  background:
    radial-gradient(900px 600px at 12% 10%, rgba(99,102,241,0.40), transparent 55%),
    radial-gradient(800px 600px at 88% 18%, rgba(56,189,248,0.35), transparent 55%),
    radial-gradient(900px 800px at 55% 95%, rgba(244,114,182,0.30), transparent 55%),
    linear-gradient(180deg, rgba(248,250,252,1) 0%, rgba(241,245,249,1) 100%);
}
.block-container{ max-width: 1320px; padding-top: 1rem; padding-bottom: 2rem; }

/* Glass cards */
.glass{
  border-radius: 22px;
  border: 1px solid rgba(255,255,255,0.60);
  background: rgba(255,255,255,0.44);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 18px 50px rgba(15,23,42,0.10);
}

/* Slim header */
.glassHeader{ padding: 14px 16px; border-radius: 22px; }
.title{ font-size: 44px; font-weight: 900; letter-spacing: -0.03em; margin: 0; display:flex; gap:10px; align-items:center; }
.sub{ margin-top: 6px; color: rgba(30,41,59,0.75); }

/* White strip (patti) */
.whiteStrip{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding: 10px 14px;
  border-radius: 18px;
  background: rgba(255,255,255,0.85);
  border: 1px solid rgba(255,255,255,0.95);
  box-shadow: 0 10px 30px rgba(15,23,42,0.08);
}
.stripTitle{
  font-size: 22px;
  font-weight: 900;
  margin: 0;
  color: rgba(15,23,42,0.90);
}

/* Tabs segmented */
.stTabs [data-baseweb="tab-list"]{
  gap: 6px;
  padding: 6px;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.55);
  background: rgba(255,255,255,0.35);
  backdrop-filter: blur(16px);
}
.stTabs [data-baseweb="tab"]{
  height: 40px;
  border-radius: 14px;
  padding: 0 14px;
  font-weight: 850;
}
.stTabs [aria-selected="true"]{
  background: rgba(255,255,255,0.78) !important;
  border: 1px solid rgba(255,255,255,0.78) !important;
}

/* Inputs rounding */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="datepicker"] > div {
  border-radius: 16px !important;
}

/* Buttons */
.stButton>button, .stDownloadButton>button{
  border-radius: 16px !important;
  padding: 0.62rem 1.05rem !important;
  font-weight: 850 !important;
}

/* Sidebar clean */
[data-testid="stSidebar"]{ background: transparent !important; border-right: none !important; }
.drawerCard{
  border-radius: 22px;
  padding: 14px;
  border: 1px solid rgba(255,255,255,0.55);
  background: rgba(255,255,255,0.45);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 18px 50px rgba(15,23,42,0.12);
}

/* Metric glass */
.metricGlass{
  border-radius: 18px;
  padding: 14px;
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

# ==================================================
# HEADER
# ==================================================
st.markdown('<div class="glass glassHeader">', unsafe_allow_html=True)
st.markdown('<div class="title">📊 <span>Yash Gallery – KPI System</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Premium Glass UI • Fast • Entry → Dashboard → Records</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.write("")

# ==================================================
# SIDEBAR (Filters title in white strip)
# ==================================================
with st.sidebar:
    st.markdown('<div class="drawerCard">', unsafe_allow_html=True)

    st.markdown("""
      <div class="whiteStrip">
        <div class="stripTitle">🔎 Filters</div>
      </div>
    """, unsafe_allow_html=True)

    st.write("")

    dept_rows = cursor.execute("""
        SELECT DISTINCT department FROM kpi_entries
        WHERE department IS NOT NULL AND department <> ''
        ORDER BY department
    """).fetchall()
    dept_list = [r[0] for r in dept_rows] if dept_rows else []
    dept_filter = st.selectbox("Department", ["All"] + dept_list)

    date_range = st.date_input("Date Range (optional)", value=[])
    name_search = st.text_input("Search Employee", placeholder="Type name…")

    st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs(["📝 Entry", "📈 Dashboard", "📋 Records"])

# ==================================================
# TAB 1 – ENTRY (white strip heading + number inputs)
# ==================================================
with tab1:
    st.markdown('<div class="glass" style="padding:18px;">', unsafe_allow_html=True)

    st.markdown("""
      <div class="whiteStrip">
        <div class="stripTitle">Employee KPI Entry</div>
      </div>
    """, unsafe_allow_html=True)

    st.write("")

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
            rating = (
                "Excellent" if total >= 320 else
                "Good" if total >= 240 else
                "Average" if total >= 160 else
                "Needs Improvement"
            )
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

# ==================================================
# LOAD DATA
# ==================================================
q = """
SELECT employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at
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

if name_search.strip():
    q += " AND lower(employee_name) LIKE ?"
    params.append(f"%{name_search.strip().lower()}%")

q += " ORDER BY created_at DESC"
rows = cursor.execute(q, params).fetchall()

df = pd.DataFrame(rows, columns=[
    "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
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
# TAB 3 – RECORDS
# ==================================================
with tab3:
    st.markdown('<div class="glass" style="padding:18px;">', unsafe_allow_html=True)

    st.markdown("""
      <div class="whiteStrip">
        <div class="stripTitle">Records</div>
      </div>
    """, unsafe_allow_html=True)

    st.write("")

    if df.empty:
        st.info("No records available.")
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
