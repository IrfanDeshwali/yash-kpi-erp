import streamlit as st
import psycopg2
from datetime import datetime
import pandas as pd

# ---------------- PAGE ----------------
st.set_page_config(page_title="Yash Gallery – KPI System", layout="wide")

# ---------------- GLASS UI CSS ----------------
st.markdown("""
<style>
/* App background */
.stApp {
  background: radial-gradient(1200px 700px at 20% 10%, rgba(99,102,241,.18), transparent 55%),
              radial-gradient(900px 600px at 85% 15%, rgba(16,185,129,.16), transparent 55%),
              radial-gradient(900px 600px at 60% 90%, rgba(236,72,153,.12), transparent 55%),
              linear-gradient(180deg, rgba(15,23,42,.98) 0%, rgba(2,6,23,.98) 100%);
  color: #e5e7eb;
}

/* Make default text light */
html, body, [class*="css"]  {
  color: #e5e7eb !important;
}

/* Sidebar width */
[data-testid="stSidebar"] { width: 290px; }
[data-testid="stSidebar"] > div:first-child { width: 290px; }

/* Glass cards */
.glass {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 18px;
  padding: 16px 18px;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}

/* Headings */
h1, h2, h3 { color: #f9fafb !important; }
.small-note { color:#9ca3af; font-size:12px; }

/* Inputs and widgets styling */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] div {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  color: #e5e7eb !important;
  border-radius: 12px !important;
}

/* Buttons */
.stButton > button, .stDownloadButton > button {
  border-radius: 12px !important;
  border: 1px solid rgba(255,255,255,0.16) !important;
  background: rgba(255,255,255,0.08) !important;
  color: #f9fafb !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  background: rgba(255,255,255,0.12) !important;
}

/* Dataframe container look */
[data-testid="stDataFrame"] {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 16px !important;
  padding: 6px !important;
}

/* Reduce top padding */
.block-container { padding-top: 1.2rem; }
</style>
""", unsafe_allow_html=True)

# ---------------- DB (NEON POSTGRES) ----------------
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
st.markdown('<div class="glass">', unsafe_allow_html=True)
st.title("📊 Yash Gallery – KPI System")
st.caption("Simple KPI software – Phase 1 (Neon DB + Export/Import + Filters)")
st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.markdown("## 🔎 Filters")

# Department list
cursor.execute("""
SELECT DISTINCT department
FROM kpi_entries
WHERE department IS NOT NULL AND department <> ''
ORDER BY department
""")
dept_rows = cursor.fetchall()
dept_list = [r[0] for r in dept_rows] if dept_rows else []
dept_filter = st.sidebar.selectbox("Department", ["All"] + dept_list)

# Employee list (depends on dept filter)
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

cursor.execute(emp_q, emp_params)
emp_rows = cursor.fetchall()
emp_list = [r[0] for r in emp_rows] if emp_rows else []
emp_filter = st.sidebar.selectbox("Employee", ["All"] + emp_list)

date_range = st.sidebar.date_input("Date Range (optional)", value=[])
st.sidebar.markdown('<div class="small-note">Tip: Date Range me 2 dates select karo (start & end).</div>', unsafe_allow_html=True)

# ---------------- ENTRY (FORM) ----------------
st.markdown('<div class="glass">', unsafe_allow_html=True)
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

        # Rating based on total (max 400)
        if total >= 320:
            rating = "Excellent"
        elif total >= 240:
            rating = "Good"
        elif total >= 160:
            rating = "Average"
        else:
            rating = "Needs Improvement"

        created_at = datetime.now()

        cursor.execute("""
            INSERT INTO kpi_entries
            (employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (emp, department, int(kpi1), int(kpi2), int(kpi3), int(kpi4), total, rating, created_at))
        conn.commit()

        st.success(f"Saved ✅ | Total: {total} | Rating: {rating}")

st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ---------------- QUERY (Filtered) ----------------
base_q = """
SELECT employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at
FROM kpi_entries
WHERE 1=1
"""
params = []

if dept_filter != "All":
    base_q += " AND department = %s"
    params.append(dept_filter)

if emp_filter != "All":
    base_q += " AND employee_name = %s"
    params.append(emp_filter)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
    base_q += " AND DATE(created_at) BETWEEN %s AND %s"
    params.append(str(start_date))
    params.append(str(end_date))

base_q += " ORDER BY created_at DESC"

cursor.execute(base_q, params)
rows = cursor.fetchall()

df = pd.DataFrame(rows, columns=[
    "Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4",
    "Total Score", "Rating", "Created At"
])

# ---------------- SUMMARY ----------------
st.markdown('<div class="glass">', unsafe_allow_html=True)
st.subheader("Summary")

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

st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ---------------- EXPORT / IMPORT ----------------
st.markdown('<div class="glass">', unsafe_allow_html=True)
st.subheader("Export / Import")

# Export CSV (filtered)
csv_data = df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download CSV (Filtered Data)",
    data=csv_data,
    file_name="kpi_export.csv",
    mime="text/csv"
)

st.write("")

# Import CSV (bulk insert)
uploaded = st.file_uploader("⬆️ Import KPI CSV", type=["csv"])

if uploaded is not None:
    try:
        imp_df = pd.read_csv(uploaded)

        required_cols = ["Employee", "Department", "KPI1", "KPI2", "KPI3", "KPI4"]
        missing = [c for c in required_cols if c not in imp_df.columns]

        if missing:
            st.error(f"CSV columns missing: {', '.join(missing)}")
        else:
            imp_df["Employee"] = imp_df["Employee"].astype(str).str.strip()
            imp_df["Department"] = imp_df["Department"].astype(str).str.strip()

            for col in ["KPI1", "KPI2", "KPI3", "KPI4"]:
                imp_df[col] = pd.to_numeric(imp_df[col], errors="coerce").fillna(0).astype(int)

            if "Total Score" not in imp_df.columns:
                imp_df["Total Score"] = imp_df["KPI1"] + imp_df["KPI2"] + imp_df["KPI3"] + imp_df["KPI4"]

            if "Rating" not in imp_df.columns:
                def rate(total):
                    if total >= 320: return "Excellent"
                    if total >= 240: return "Good"
                    if total >= 160: return "Average"
                    return "Needs Improvement"
                imp_df["Rating"] = imp_df["Total Score"].apply(rate)

            if "Created At" in imp_df.columns:
                imp_df["Created At"] = pd.to_datetime(imp_df["Created At"], errors="coerce")
            else:
                imp_df["Created At"] = pd.Timestamp.now()

            data_to_insert = []
            for _, r in imp_df.iterrows():
                created = r["Created At"]
                if pd.isna(created):
                    created = datetime.now()
                else:
                    created = created.to_pydatetime()

                data_to_insert.append((
                    r["Employee"],
                    r["Department"],
                    int(r["KPI1"]),
                    int(r["KPI2"]),
                    int(r["KPI3"]),
                    int(r["KPI4"]),
                    int(r["Total Score"]),
                    str(r["Rating"]),
                    created
                ))

            cursor.executemany("""
                INSERT INTO kpi_entries
                (employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, data_to_insert)
            conn.commit()

            st.success(f"✅ Imported {len(data_to_insert)} rows successfully.")
            st.info("Page refresh karke imported data table me dikh jayega.")

    except Exception as e:
        st.error(f"Import failed: {e}")

st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ---------------- TABLE ----------------
st.markdown('<div class="glass">', unsafe_allow_html=True)
st.subheader("Saved KPI Records")
st.dataframe(df, use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)
