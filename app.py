import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_option_menu import option_menu

# ---------------- PAGE ----------------
st.set_page_config(page_title="Yash Gallery – KPI System", layout="wide")

# ---------------- UI CSS (clean product style) ----------------
st.markdown("""
<style>
.block-container{padding-top:1rem}
.card{
  background:#fff;border:1px solid #e5e7eb;border-radius:16px;
  padding:14px 16px; box-shadow:0 6px 18px rgba(15,23,42,0.06);
}
.small{color:#64748b;font-size:12px}
.hline{height:1px;background:#e5e7eb;margin:10px 0}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;
  border:1px solid #e5e7eb;background:#f8fafc;font-size:12px;color:#334155}
</style>
""", unsafe_allow_html=True)

# ---------------- DB (Neon + auto reconnect) ----------------
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
            return cur.fetchall() if fetch else None
    except psycopg2.InterfaceError:
        st.session_state["db_conn"] = None
        conn = get_conn()
        with conn.cursor() as cur:
            if many and data is not None:
                cur.executemany(query, data)
                return None
            cur.execute(query, params or [])
            return cur.fetchall() if fetch else None

# ---------------- Tables ----------------
run("""
CREATE TABLE IF NOT EXISTS kpi_entries (
    id SERIAL PRIMARY KEY,
    employee_name TEXT NOT NULL,
    department TEXT NOT NULL,
    kpi1 INTEGER, kpi2 INTEGER, kpi3 INTEGER, kpi4 INTEGER,
    total_score INTEGER, rating TEXT,
    created_at TIMESTAMP
)
""")

# KPI master (dynamic KPI labels)
run("""
CREATE TABLE IF NOT EXISTS kpi_master (
    id SERIAL PRIMARY KEY,
    kpi_key TEXT UNIQUE NOT NULL,
    kpi_label TEXT NOT NULL
)
""")

# Ensure default KPI labels exist
defaults = [("kpi1", "KPI 1"), ("kpi2", "KPI 2"), ("kpi3", "KPI 3"), ("kpi4", "KPI 4")]
for k, lbl in defaults:
    run("""
    INSERT INTO kpi_master (kpi_key, kpi_label)
    VALUES (%s,%s)
    ON CONFLICT (kpi_key) DO NOTHING
    """, [k, lbl])

def get_kpi_labels():
    rows = run("SELECT kpi_key, kpi_label FROM kpi_master ORDER BY kpi_key", fetch=True) or []
    d = {k: v for k, v in rows}
    return d.get("kpi1","KPI 1"), d.get("kpi2","KPI 2"), d.get("kpi3","KPI 3"), d.get("kpi4","KPI 4")

def calc_rating(total: int) -> str:
    # max 400
    if total >= 320: return "Excellent"
    if total >= 240: return "Good"
    if total >= 160: return "Average"
    return "Needs Improvement"

# ---------------- Sidebar (filters + admin) ----------------
st.sidebar.markdown("## 🔎 Filters")
dept_rows = run("SELECT DISTINCT department FROM kpi_entries ORDER BY department", fetch=True) or []
dept_list = [r[0] for r in dept_rows if r[0]]
dept_filter = st.sidebar.selectbox("Department", ["All"] + dept_list)

emp_q = "SELECT DISTINCT employee_name FROM kpi_entries WHERE 1=1"
emp_p = []
if dept_filter != "All":
    emp_q += " AND department=%s"
    emp_p.append(dept_filter)
emp_q += " ORDER BY employee_name"
emp_rows = run(emp_q, emp_p, fetch=True) or []
emp_list = [r[0] for r in emp_rows if r[0]]
emp_filter = st.sidebar.selectbox("Employee", ["All"] + emp_list)

date_range = st.sidebar.date_input("Date Range (optional)", value=[])
search_text = st.sidebar.text_input("Search name", placeholder="e.g., Irfan")

st.sidebar.markdown("## 🔐 Admin")
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
pw = st.sidebar.text_input("Admin Password", type="password", placeholder="Enter password")
if st.sidebar.button("Login"):
    st.session_state["is_admin"] = (pw == st.secrets.get("ADMIN_PASSWORD",""))
    st.sidebar.success("Admin mode ON" if st.session_state["is_admin"] else "Wrong password")

is_admin = st.session_state["is_admin"]

# ---------------- Top Header + Navigation ----------------
st.markdown('<div class="card">', unsafe_allow_html=True)
c1, c2 = st.columns([3, 2])
with c1:
    st.title("📊 Yash Gallery – KPI System")
    st.caption("Professional • Dynamic KPI Labels • Dashboard • Reports • Protected Admin Actions")
with c2:
    st.markdown(f"<span class='badge'>Database: Neon</span> &nbsp; <span class='badge'>Admin: {'ON' if is_admin else 'OFF'}</span>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

menu = option_menu(
    None,
    ["Dashboard", "Entry", "Records", "Reports", "Settings"],
    icons=["speedometer2", "plus-circle", "table", "bar-chart", "gear"],
    orientation="horizontal",
    styles={
        "container": {"padding": "0.2rem 0", "background-color": "#ffffff", "border": "1px solid #e5e7eb", "border-radius": "14px"},
        "nav-link": {"font-size": "15px", "margin": "0px", "padding": "10px 14px"},
        "nav-link-selected": {"background-color": "#2563EB", "color": "white"},
    },
)

# ---------------- Data Fetch (filtered) ----------------
q = """
SELECT id, employee_name, department, kpi1, kpi2, kpi3, kpi4, total_score, rating, created_at
FROM kpi_entries WHERE 1=1
"""
p = []
if dept_filter != "All":
    q += " AND department=%s"; p.append(dept_filter)
if emp_filter != "All":
    q += " AND employee_name=%s"; p.append(emp_filter)
if search_text.strip():
    q += " AND employee_name ILIKE %s"; p.append(f"%{search_text.strip()}%")
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    s, e = date_range
    q += " AND DATE(created_at) BETWEEN %s AND %s"; p += [str(s), str(e)]
q += " ORDER BY created_at DESC"

rows = run(q, p, fetch=True) or []
df = pd.DataFrame(rows, columns=["ID","Employee","Department","KPI1","KPI2","KPI3","KPI4","Total Score","Rating","Created At"])

kpi1_lbl, kpi2_lbl, kpi3_lbl, kpi4_lbl = get_kpi_labels()

# ============================================================
# Dashboard
# ============================================================
if menu == "Dashboard":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📌 Summary")
    m1, m2, m3, m4 = st.columns(4)
    if len(df):
        m1.metric("Total Records", len(df))
        m2.metric("Average Score", round(float(df["Total Score"].mean()), 2))
        m3.metric("Best Score", int(df["Total Score"].max()))
        m4.metric("Worst Score", int(df["Total Score"].min()))
    else:
        m1.metric("Total Records", 0); m2.metric("Average Score", 0); m3.metric("Best Score", 0); m4.metric("Worst Score", 0)
    st.markdown("</div>", unsafe_allow_html=True)

    cA, cB = st.columns([1.2, 1], gap="large")
    with cA:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Score Distribution")
        if len(df):
            st.plotly_chart(px.histogram(df, x="Total Score", nbins=20), use_container_width=True)
        else:
            st.info("No data with current filters.")
        st.markdown("</div>", unsafe_allow_html=True)

    with cB:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🏭 Dept Average")
        if len(df):
            dept_avg = df.groupby("Department", as_index=False)["Total Score"].mean().sort_values("Total Score", ascending=False)
            st.plotly_chart(px.bar(dept_avg, x="Department", y="Total Score"), use_container_width=True)
        else:
            st.info("No data with current filters.")
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# Entry
# ============================================================
if menu == "Entry":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("➕ Add KPI Entry")

    with st.form("add_form", clear_on_submit=True):
        a1, a2 = st.columns([2, 1])
        with a1:
            employee_name = st.text_input("Employee Name", placeholder="e.g., Irfan Deshwali")
        with a2:
            department = st.selectbox("Department", ["Fabric","Merchant","Sampling","Cutting","Finishing","Dispatch","Admin","Sales","Accounts"])

        k1, k2, k3, k4 = st.columns(4)
        with k1: v1 = st.number_input(kpi1_lbl, 1, 100, 1, 1)
        with k2: v2 = st.number_input(kpi2_lbl, 1, 100, 1, 1)
        with k3: v3 = st.number_input(kpi3_lbl, 1, 100, 1, 1)
        with k4: v4 = st.number_input(kpi4_lbl, 1, 100, 1, 1)

        ok = st.form_submit_button("✅ Save Entry")

    if ok:
        emp = (employee_name or "").strip()
        if emp == "":
            st.error("Employee Name required.")
        else:
            total = int(v1+v2+v3+v4)
            rating = calc_rating(total)
            run("""
                INSERT INTO kpi_entries (employee_name, department, kpi1,kpi2,kpi3,kpi4,total_score,rating,created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [emp, department, int(v1), int(v2), int(v3), int(v4), total, rating, datetime.now()])
            st.success(f"Saved ✅ | Total: {total} | Rating: {rating}")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# Records (Export/Import + Edit/Delete protected)
# ============================================================
if menu == "Records":
    left, right = st.columns([2, 1], gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📋 Records Table")
        st.dataframe(df.drop(columns=["ID"]) if len(df) else df, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("⬇️ Export / ⬆️ Import")

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV (Filtered)", csv_data, "kpi_export.csv", "text/csv")

        up = st.file_uploader("Import CSV", type=["csv"])
        if st.button("Import Now", disabled=not is_admin):
            if not is_admin:
                st.warning("Admin login required for Import.")
            elif up is None:
                st.warning("Upload CSV first.")
            else:
                imp = pd.read_csv(up)
                required = ["Employee","Department","KPI1","KPI2","KPI3","KPI4"]
                miss = [c for c in required if c not in imp.columns]
                if miss:
                    st.error(f"Missing columns: {', '.join(miss)}")
                else:
                    imp["Employee"] = imp["Employee"].astype(str).str.strip()
                    imp["Department"] = imp["Department"].astype(str).str.strip()
                    for c in ["KPI1","KPI2","KPI3","KPI4"]:
                        imp[c] = pd.to_numeric(imp[c], errors="coerce").fillna(0).astype(int)
                    imp["Total Score"] = imp["KPI1"]+imp["KPI2"]+imp["KPI3"]+imp["KPI4"]
                    imp["Rating"] = imp["Total Score"].apply(calc_rating)
                    imp["Created At"] = pd.to_datetime(imp.get("Created At", pd.Timestamp.now()), errors="coerce").fillna(pd.Timestamp.now())

                    data = []
                    for _, r in imp.iterrows():
                        data.append((r["Employee"], r["Department"], int(r["KPI1"]), int(r["KPI2"]), int(r["KPI3"]), int(r["KPI4"]),
                                     int(r["Total Score"]), str(r["Rating"]), r["Created At"].to_pydatetime()))
                    run("""
                        INSERT INTO kpi_entries (employee_name, department, kpi1,kpi2,kpi3,kpi4,total_score,rating,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, many=True, data=data)
                    st.success(f"Imported {len(data)} rows ✅")
                    st.rerun()

        st.markdown("<div class='small'>Import/Edit/Delete only Admin ke liye enable hai.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Edit/Delete
    st.write("")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("✏️ Edit / 🗑 Delete (Admin Only)")

    if len(df) == 0:
        st.info("No records for current filters.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    rec_id = st.selectbox("Select Record ID", df["ID"].tolist())
    row = df[df["ID"] == rec_id].iloc[0]

    e1, e2, e3 = st.columns([1.2,1.4,1], gap="large")
    with e1:
        emp = st.text_input("Employee", value=str(row["Employee"]))
        dept = st.text_input("Department", value=str(row["Department"]))
    with e2:
        c1,c2 = st.columns(2)
        with c1:
            k1 = st.number_input(kpi1_lbl, 1,100,int(row["KPI1"]),1, key="rk1")
            k2 = st.number_input(kpi2_lbl, 1,100,int(row["KPI2"]),1, key="rk2")
        with c2:
            k3 = st.number_input(kpi3_lbl, 1,100,int(row["KPI3"]),1, key="rk3")
            k4 = st.number_input(kpi4_lbl, 1,100,int(row["KPI4"]),1, key="rk4")
    with e3:
        new_total = int(k1+k2+k3+k4)
        new_rating = calc_rating(new_total)
        st.markdown(f"**Total:** {new_total}")
        st.markdown(f"**Rating:** {new_rating}")

        if st.button("Update", disabled=not is_admin):
            if not is_admin:
                st.warning("Admin login required.")
            else:
                run("""
                    UPDATE kpi_entries SET employee_name=%s, department=%s,
                      kpi1=%s,kpi2=%s,kpi3=%s,kpi4=%s,total_score=%s,rating=%s
                    WHERE id=%s
                """, [emp.strip(), dept.strip(), int(k1),int(k2),int(k3),int(k4), new_total, new_rating, int(rec_id)])
                st.success("Updated ✅"); st.rerun()

        if st.button("Delete", disabled=not is_admin):
            if not is_admin:
                st.warning("Admin login required.")
            else:
                run("DELETE FROM kpi_entries WHERE id=%s", [int(rec_id)])
                st.warning("Deleted 🗑"); st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# Reports
# ============================================================
if menu == "Reports":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📄 Monthly Reports")

    if len(df) == 0:
        st.info("No data for current filters.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    tmp = df.copy()
    tmp["Month"] = pd.to_datetime(tmp["Created At"]).dt.to_period("M").astype(str)
    months = sorted(tmp["Month"].unique())[::-1]

    r1, r2 = st.columns([1,1])
    with r1:
        report_type = st.selectbox("Report Type", ["Employee Wise Avg", "Department Wise Avg"])
    with r2:
        sel_month = st.selectbox("Month", months)

    mdf = tmp[tmp["Month"] == sel_month]
    if report_type.startswith("Employee"):
        rep = mdf.groupby("Employee", as_index=False)["Total Score"].mean().sort_values("Total Score", ascending=False)
        fig = px.bar(rep, x="Employee", y="Total Score")
    else:
        rep = mdf.groupby("Department", as_index=False)["Total Score"].mean().sort_values("Total Score", ascending=False)
        fig = px.bar(rep, x="Department", y="Total Score")

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(rep, use_container_width=True, hide_index=True)

    out = rep.to_csv(index=False).encode("utf-8")
    st.download_button("Download Report CSV", out, f"report_{sel_month}.csv", "text/csv")
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# Settings (Dynamic KPI labels)
# ============================================================
if menu == "Settings":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚙️ Settings (Dynamic KPI Names)")

    st.info("Yahan se aap KPI1..KPI4 ke naam change kar sakte ho. (Example: Quality, Speed, Attendance, Discipline)")

    if not is_admin:
        st.warning("Admin login required to change settings.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    k1,k2,k3,k4 = get_kpi_labels()
    n1 = st.text_input("KPI 1 Label", value=k1)
    n2 = st.text_input("KPI 2 Label", value=k2)
    n3 = st.text_input("KPI 3 Label", value=k3)
    n4 = st.text_input("KPI 4 Label", value=k4)

    if st.button("Save KPI Labels"):
        run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi1'", [n1.strip() or "KPI 1"])
        run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi2'", [n2.strip() or "KPI 2"])
        run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi3'", [n3.strip() or "KPI 3"])
        run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi4'", [n4.strip() or "KPI 4"])
        st.success("Saved ✅")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
