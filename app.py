import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Yash Gallery – KPI System",
    page_icon="📊",
    layout="wide"
)

# ==================================================
# iOS GLASS UI – CLEAN CSS
# ==================================================
st.markdown("""
<style>

/* -------- Background (soft iOS gradient) -------- */
.stApp {
  background:
    radial-gradient(1200px 700px at 10% 10%, rgba(99,102,241,0.25), transparent 60%),
    radial-gradient(900px 600px at 90% 20%, rgba(56,189,248,0.22), transparent 55%),
    linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}

/* -------- Layout -------- */
.block-container {
  padding-top: 1rem;
  padding-bottom: 2rem;
  max-width: 1280px;
}

/* -------- Sidebar (NORMAL, NOT DRAWER) -------- */
[data-testid="stSidebar"] {
  background: #f8fafc;
  border-right: 1px solid #e5e7eb;
}
[data-testid="stSidebar"] > div:first-child {
  padding-top: 1rem;
}
[data-testid="stSidebar"] { width: 280px; }
[data-testid="stSidebar"] > div:first-child { width: 280px; }

/* -------- Slim Header Glass -------- */
.glass-header{
  border-radius: 16px;
  padding: 12px 16px;
  border: 1px solid rgba(255,255,255,0.55);
  background: rgba(255,255,255,0.45);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 22px rgba(15,23,42,0.06);
}

/* -------- Main Glass Cards -------- */
.glass{
  border-radius: 22px;
  padding: 18px;
  border: 1px solid rgba(255,255,255,0.65);
  background: rgba(255,255,255,0.60);
  backdrop-filter: blur(14px);
  box-shadow: 0 12px 36px rgba(15,23,42,0.08);
}

/* -------- Typography -------- */
.title { font-size: 40px; font-weight: 900; letter-spacing: -0.03em; margin: 0; }
.sub { color: #475569; margin-top: 4px; }
.h2 { font-size: 24px; font-weight: 800; margin-bottom: 10px; }

/* -------- Inputs -------- */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="datepicker"] > div {
  border-radius: 14px !important;
}

/* -------- Buttons -------- */
.stButton>button, .stDownloadButton>button {
  border-radius: 14px !important;
  font-weight: 700 !important;
}

/* -------- Tabs (iOS pill) -------- */
.stTabs [data-baseweb="tab-list"]{
  gap: 8px;
  background: rgba(255,255,255,0.5);
  border: 1px solid rgba(255,255,255,0.7);
  padding: 6px;
  border-radius: 16px;
}
.stTabs [data-baseweb="tab"]{
  height: 40px;
  border-radius: 12px;
  font-weight: 700;
}
.stTabs [aria-selected="true"]{
  background: white !important;
}

/* -------- Metric Glass -------- */
.metric-glass{
  border-radius: 18px;
  padding: 14px;
  border: 1px solid rgba(255,255,255,0.6);
  background: rgba(255,255,255,0.6);
  backdrop-filter: blur(12px);
}

/* -------- Hide footer -------- */
footer {visibility: hidden;}

</style>
""", unsafe_allow_html=True)

# ==================================================
# DATABASE
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
st.markdown('<div class="glass-header">', unsafe_allow_html=True)
st.markdown('<div class="title">📊 Yash Gallery – KPI System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">iOS Glass UI • Phase 1 • Entry → Dashboard → Records</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.write("")

# ==================================================
# SIDEBAR FILTERS
# ==================================================
st.sidebar.header("🔎 Filters")

dept_rows = cursor.execute("""
SELECT DISTINCT department FROM kpi_entries
WHERE department IS NOT NULL AND department <> ''
ORDER BY department
""").fetchall()
dept_list = [r[0] for r in dept_rows] if dept_rows else []

dept_filter = st.sidebar.selectbox("Department", ["All"] + dept_list)
date_range = st.sidebar.date_input("Date Range (optional)", value=[])
name_search = st.sidebar.text_input("Search Employee", placeholder="Type name…")

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs(["📝 Entry", "📈 Dashboard", "📋 Records"])

# ==================================================
# TAB 1 – ENTRY
# ==================================================
with tab1:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown('<div class="h2">Employee KPI Entry</div>', unsafe_allow_html=True)

    with st.form("kpi_form", clear_on_submit=True):
        c1, c2 = st.columns([2,1])
        with c1:
            employee_name = st.text_input("Employee Name", placeholder="e.g., Irfan Deshwali")
        with c2:
            department = st.selectbox(
                "Department",
                ["Fabric","Merchant","Sampling","Cutting","Finishing","Dispatch","Admin","Sales","Accounts"]
            )

        k1,k2,k3,k4 = st.columns(4)
        kpi1 = k1.number_input("KPI 1 (1–100)",1,100,1)
        kpi2 = k2.number_input("KPI 2 (1–100)",1,100,1)
        kpi3 = k3.number_input("KPI 3 (1–100)",1,100,1)
        kpi4 = k4.number_input("KPI 4 (1–100)",1,100,1)

        submitted = st.form_submit_button("✅ Calculate & Save")

    if submitted:
        if not employee_name.strip():
            st.error("Employee Name required.")
        else:
            total = kpi1+kpi2+kpi3+kpi4
            rating = (
                "Excellent" if total>=80 else
                "Good" if total>=60 else
                "Average" if total>=40 else
                "Needs Improvement"
            )
            cursor.execute("""
                INSERT INTO kpi_entries
                (employee_name,department,kpi1,kpi2,kpi3,kpi4,total_score,rating,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """,(employee_name.strip(),department,kpi1,kpi2,kpi3,kpi4,total,rating,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            st.toast("Saved Successfully ✅", icon="✅")

    st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# LOAD DATA
# ==================================================
query = "SELECT employee_name,department,kpi1,kpi2,kpi3,kpi4,total_score,rating,created_at FROM kpi_entries WHERE 1=1"
params = []

if dept_filter!="All":
    query+=" AND department=?"; params.append(dept_filter)
if isinstance(date_range,(list,tuple)) and len(date_range)==2:
    query+=" AND date(created_at) BETWEEN date(?) AND date(?)"
    params += [str(date_range[0]),str(date_range[1])]
if name_search:
    query+=" AND lower(employee_name) LIKE ?"
    params.append(f"%{name_search.lower()}%")

query+=" ORDER BY created_at DESC"
rows = cursor.execute(query,params).fetchall()

df = pd.DataFrame(rows,columns=[
    "Employee","Department","KPI1","KPI2","KPI3","KPI4","Total Score","Rating","Created At"
])

# ==================================================
# TAB 2 – DASHBOARD
# ==================================================
with tab2:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown('<div class="h2">Summary</div>', unsafe_allow_html=True)

    if not df.empty:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Records",len(df))
        c2.metric("Average",round(df["Total Score"].mean(),2))
        c3.metric("Best",df["Total Score"].max())
        c4.metric("Worst",df["Total Score"].min())

        left,right = st.columns([1.2,1])
        with left:
            fig1 = px.bar(df.groupby("Department")["Total Score"].mean().reset_index(),
                          x="Department",y="Total Score")
            st.plotly_chart(fig1,use_container_width=True)
        with right:
            fig2 = px.pie(df,names="Rating",hole=0.5)
            st.plotly_chart(fig2,use_container_width=True)
    else:
        st.info("No data found.")

    st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# TAB 3 – RECORDS
# ==================================================
with tab3:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown('<div class="h2">Saved Records</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No records.")
    else:
        st.download_button("⬇️ Download CSV",
            df.to_csv(index=False).encode(),
            "kpi_records.csv","text/csv")
        st.dataframe(df,use_container_width=True,hide_index=True)

    st.markdown('</div>', unsafe_allow_html=True)
