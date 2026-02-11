import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_option_menu import option_menu

# ---------------- PAGE ----------------
st.set_page_config(page_title="Yash Gallery – KPI System", layout="wide")

# ---------------- UI CSS ----------------
st.markdown("""
<style>
.block-container{padding-top:1rem}
.card{
  background:#fff;border:1px solid #e5e7eb;border-radius:16px;
  padding:14px 16px; box-shadow:0 6px 18px rgba(15,23,42,0.06);
}
.small{color:#64748b;font-size:12px}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;
  border:1px solid #e5e7eb;background:#f8fafc;font-size:12px;color:#334155}
.hline{height:1px;background:#e5e7eb;margin:10px 0}
[data-testid="stSidebar"]{width:300px}
[data-testid="stSidebar"] > div:first-child{width:300px}
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

# ---------------- CORE TABLES ----------------
run("""
CREATE TABLE IF NOT EXISTS kpi_entries (
    id SERIAL PRIMARY KEY,
    employee_name TEXT NOT NULL,
    department TEXT NOT NULL,
    kpi1 INTEGER, kpi2 INTEGER, kpi3 INTEGER, kpi4 INTEGER,
    total_score DOUBLE PRECISION,
    rating TEXT,
    created_at TIMESTAMP
)
""")

run("""
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
""")

run("""
CREATE TABLE IF NOT EXISTS kpi_master (
    kpi_key TEXT PRIMARY KEY,
    kpi_label TEXT NOT NULL
)
""")

run("""
CREATE TABLE IF NOT EXISTS kpi_weights (
    kpi_key TEXT PRIMARY KEY,
    weight INTEGER NOT NULL
)
""")

run("""
CREATE TABLE IF NOT EXISTS rating_rules (
    id INTEGER PRIMARY KEY DEFAULT 1,
    excellent_min INTEGER NOT NULL,
    good_min INTEGER NOT NULL,
    average_min INTEGER NOT NULL
)
""")

# ---------------- DEFAULTS INIT ----------------
def set_default_if_missing(key, value):
    run("""
    INSERT INTO app_settings(key, value)
    VALUES (%s,%s)
    ON CONFLICT (key) DO NOTHING
    """, [key, value])

set_default_if_missing("admin_password", "1234")     # default admin
set_default_if_missing("allow_import", "1")          # 1=yes
set_default_if_missing("allow_edit_delete", "1")     # 1=yes

for k, lbl in [("kpi1","KPI 1"), ("kpi2","KPI 2"), ("kpi3","KPI 3"), ("kpi4","KPI 4")]:
    run("""
    INSERT INTO kpi_master(kpi_key, kpi_label)
    VALUES (%s,%s)
    ON CONFLICT (kpi_key) DO NOTHING
    """, [k, lbl])

for k, w in [("kpi1",25), ("kpi2",25), ("kpi3",25), ("kpi4",25)]:
    run("""
    INSERT INTO kpi_weights(kpi_key, weight)
    VALUES (%s,%s)
    ON CONFLICT (kpi_key) DO NOTHING
    """, [k, w])

run("""
INSERT INTO rating_rules(id, excellent_min, good_min, average_min)
VALUES (1, 80, 60, 40)
ON CONFLICT (id) DO NOTHING
""")

# ---------------- SETTINGS GET/SET ----------------
def get_setting(key, default=""):
    r = run("SELECT value FROM app_settings WHERE key=%s", [key], fetch=True)
    return r[0][0] if r else default

def set_setting(key, value):
    run("""
    INSERT INTO app_settings(key, value)
    VALUES (%s,%s)
    ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
    """, [key, value])

def get_kpi_labels():
    rows = run("SELECT kpi_key, kpi_label FROM kpi_master ORDER BY kpi_key", fetch=True) or []
    d = {k:v for k,v in rows}
    return d.get("kpi1","KPI 1"), d.get("kpi2","KPI 2"), d.get("kpi3","KPI 3"), d.get("kpi4","KPI 4")

def get_kpi_weights():
    rows = run("SELECT kpi_key, weight FROM kpi_weights ORDER BY kpi_key", fetch=True) or []
    d = {k:int(w) for k,w in rows}
    return d.get("kpi1",25), d.get("kpi2",25), d.get("kpi3",25), d.get("kpi4",25)

def get_rating_rules():
    r = run("SELECT excellent_min, good_min, average_min FROM rating_rules WHERE id=1", fetch=True)
    if not r:
        return 80, 60, 40
    return int(r[0][0]), int(r[0][1]), int(r[0][2])

def calc_weighted_score(k1,k2,k3,k4):
    w1,w2,w3,w4 = get_kpi_weights()
    score = (k1*w1 + k2*w2 + k3*w3 + k4*w4) / 100.0
    return round(score, 2)

def calc_rating(score_0_100: float):
    ex, gd, av = get_rating_rules()
    if score_0_100 >= ex: return "Excellent"
    if score_0_100 >= gd: return "Good"
    if score_0_100 >= av: return "Average"
    return "Needs Improvement"

# ---------------- AUTH (Admin) ----------------
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

# ---------------- SIDEBAR FILTERS (100% SAFE from kpi_entries) ----------------
st.sidebar.markdown("## 🔎 Filters")

dept_rows = run(
    "SELECT DISTINCT department FROM kpi_entries WHERE department IS NOT NULL AND department<>'' ORDER BY department",
    fetch=True
) or []
dept_list = [r[0] for r in dept_rows]
dept_filter = st.sidebar.selectbox("Department", ["All"] + dept_list)

emp_q = "SELECT DISTINCT employee_name FROM kpi_entries WHERE employee_name IS NOT NULL AND employee_name<>''"
emp_p = []
if dept_filter != "All":
    emp_q += " AND department=%s"
    emp_p.append(dept_filter)
emp_q += " ORDER BY employee_name"

emp_rows = run(emp_q, emp_p, fetch=True) or []
emp_list = [r[0] for r in emp_rows]
emp_filter = st.sidebar.selectbox("Employee", ["All"] + emp_list)

date_range = st.sidebar.date_input("Date Range (optional)", value=[])
search_text = st.sidebar.text_input("Search name", placeholder="e.g., Irfan")

# Admin login
st.sidebar.markdown("## 🔐 Admin")
pw = st.sidebar.text_input("Admin Password", type="password", placeholder="Enter password")
if st.sidebar.button("Login"):
    st.session_state["is_admin"] = (pw == get_setting("admin_password", "1234"))
    st.sidebar.success("Admin mode ON" if st.session_state["is_admin"] else "Wrong password")

is_admin = st.session_state.get("is_admin", False)
allow_import = get_setting("allow_import","1") == "1"
allow_edit_delete = get_setting("allow_edit_delete","1") == "1"

# ---------------- HEADER ----------------
st.markdown('<div class="card">', unsafe_allow_html=True)
c1, c2 = st.columns([3,2])
with c1:
    st.title("📊 Yash Gallery – KPI System")
    st.caption("Dashboard • Entry • Records • Reports • Control Panel (No-code settings)")
with c2:
    st.markdown(
        f"<span class='badge'>Database: Neon</span> "
        f"<span class='badge'>Admin: {'ON' if is_admin else 'OFF'}</span> "
        f"<span class='badge'>Import: {'ON' if allow_import else 'OFF'}</span> "
        f"<span class='badge'>Edit/Delete: {'ON' if allow_edit_delete else 'OFF'}</span>",
        unsafe_allow_html=True
    )
st.markdown("</div>", unsafe_allow_html=True)

menu = option_menu(
    None,
    ["Dashboard", "Entry", "Records", "Reports", "Control Panel"],
    icons=["speedometer2", "plus-circle", "table", "bar-chart", "shield-lock"],
    orientation="horizontal",
    styles={
        "container": {"padding": "0.2rem 0", "background-color": "#ffffff", "border": "1px solid #e5e7eb", "border-radius": "14px"},
        "nav-link": {"font-size": "15px", "margin": "0px", "padding": "10px 14px"},
        "nav-link-selected": {"background-color": "#2563EB", "color": "white"},
    },
)

# ---------------- QUERY FILTERED KPI ENTRIES ----------------
q = """
SELECT id, employee_name, department, kpi1,kpi2,kpi3,kpi4, total_score, rating, created_at
FROM kpi_entries
WHERE 1=1
"""
p = []
if dept_filter != "All":
    q += " AND department=%s"; p.append(dept_filter)
if emp_filter != "All":
    q += " AND employee_name=%s"; p.append(emp_filter)
if search_text.strip():
    q += " AND employee_name ILIKE %s"; p.append(f"%{search_text.strip()}%")
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    s,e = date_range
    q += " AND DATE(created_at) BETWEEN %s AND %s"; p += [str(s), str(e)]
q += " ORDER BY created_at DESC"

rows = run(q, p, fetch=True) or []
df = pd.DataFrame(rows, columns=["ID","Employee","Department","KPI1","KPI2","KPI3","KPI4","Weighted Score","Rating","Created At"])

kpi1_lbl, kpi2_lbl, kpi3_lbl, kpi4_lbl = get_kpi_labels()

# ============================================================
# Dashboard
# ============================================================
if menu == "Dashboard":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📌 Summary (Weighted out of 100)")
    m1,m2,m3,m4 = st.columns(4)
    if len(df):
        m1.metric("Total Records", len(df))
        m2.metric("Average Score", round(float(df["Weighted Score"].mean()), 2))
        m3.metric("Best Score", round(float(df["Weighted Score"].max()), 2))
        m4.metric("Worst Score", round(float(df["Weighted Score"].min()), 2))
    else:
        m1.metric("Total Records", 0); m2.metric("Average Score", 0); m3.metric("Best Score", 0); m4.metric("Worst Score", 0)
    st.markdown("</div>", unsafe_allow_html=True)

    cA, cB = st.columns([1.2, 1], gap="large")
    with cA:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Score Distribution")
        if len(df):
            st.plotly_chart(px.histogram(df, x="Weighted Score", nbins=20), use_container_width=True)
        else:
            st.info("No data with current filters.")
        st.markdown("</div>", unsafe_allow_html=True)

    with cB:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🏭 Dept Average")
        if len(df):
            dept_avg = df.groupby("Department", as_index=False)["Weighted Score"].mean().sort_values("Weighted Score", ascending=False)
            st.plotly_chart(px.bar(dept_avg, x="Department", y="Weighted Score"), use_container_width=True)
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
        a1, a2 = st.columns([2,1])
        with a1:
            emp = st.text_input("Employee Name", placeholder="e.g., Irfan Deshwali")
        with a2:
            dept = st.text_input("Department", placeholder="e.g., Fabric")

        k1,k2,k3,k4 = st.columns(4)
        with k1: v1 = st.number_input(kpi1_lbl, 1,100,1,1)
        with k2: v2 = st.number_input(kpi2_lbl, 1,100,1,1)
        with k3: v3 = st.number_input(kpi3_lbl, 1,100,1,1)
        with k4: v4 = st.number_input(kpi4_lbl, 1,100,1,1)

        ok = st.form_submit_button("✅ Save Entry")

    if ok:
        if not emp.strip() or not dept.strip():
            st.error("Employee + Department required.")
        else:
            score = calc_weighted_score(int(v1),int(v2),int(v3),int(v4))
            rating = calc_rating(score)
            run("""
                INSERT INTO kpi_entries (employee_name, department, kpi1,kpi2,kpi3,kpi4, total_score, rating, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [emp.strip(), dept.strip(), int(v1),int(v2),int(v3),int(v4), float(score), rating, datetime.now()])
            st.success(f"Saved ✅ | Score: {score} | Rating: {rating}")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# Records (Export/Import + Edit/Delete)
# ============================================================
if menu == "Records":
    left, right = st.columns([2,1], gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📋 Records Table (Filtered)")
        show_df = df.copy().rename(columns={"KPI1":kpi1_lbl,"KPI2":kpi2_lbl,"KPI3":kpi3_lbl,"KPI4":kpi4_lbl})
        st.dataframe(show_df.drop(columns=["ID"]) if len(show_df) else show_df, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("⬇️ Export / ⬆️ Import")

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV (Filtered)", csv_data, "kpi_export.csv", "text/csv")

        up = st.file_uploader("Import CSV", type=["csv"])
        can_import_now = is_admin and allow_import
        if st.button("Import Now", disabled=not can_import_now):
            if up is None:
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

                    data = []
                    for _, r in imp.iterrows():
                        score = calc_weighted_score(int(r["KPI1"]),int(r["KPI2"]),int(r["KPI3"]),int(r["KPI4"]))
                        rating = calc_rating(score)
                        data.append((r["Employee"], r["Department"], int(r["KPI1"]), int(r["KPI2"]), int(r["KPI3"]), int(r["KPI4"]),
                                     float(score), rating, datetime.now()))

                    run("""
                        INSERT INTO kpi_entries (employee_name, department, kpi1,kpi2,kpi3,kpi4,total_score,rating,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, many=True, data=data)

                    st.success(f"Imported {len(data)} rows ✅")
                    st.rerun()

        st.markdown("<div class='small'>Import/Edit/Delete: Admin + permissions required.</div>", unsafe_allow_html=True)
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

    e1,e2,e3 = st.columns([1.2,1.6,1], gap="large")
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
        score = calc_weighted_score(int(k1),int(k2),int(k3),int(k4))
        rating = calc_rating(score)
        st.markdown(f"**Score:** {score}")
        st.markdown(f"**Rating:** {rating}")

        can_edit = is_admin and allow_edit_delete
        if st.button("Update", disabled=not can_edit):
            run("""
                UPDATE kpi_entries SET employee_name=%s, department=%s,
                  kpi1=%s,kpi2=%s,kpi3=%s,kpi4=%s,total_score=%s,rating=%s
                WHERE id=%s
            """, [emp.strip(), dept.strip(), int(k1),int(k2),int(k3),int(k4), float(score), rating, int(rec_id)])
            st.success("Updated ✅"); st.rerun()

        if st.button("Delete", disabled=not can_edit):
            run("DELETE FROM kpi_entries WHERE id=%s", [int(rec_id)])
            st.warning("Deleted 🗑"); st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# Reports
# ============================================================
if menu == "Reports":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📄 Monthly Reports (Weighted)")

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
        rep = mdf.groupby("Employee", as_index=False)["Weighted Score"].mean().sort_values("Weighted Score", ascending=False)
        fig = px.bar(rep, x="Employee", y="Weighted Score")
    else:
        rep = mdf.groupby("Department", as_index=False)["Weighted Score"].mean().sort_values("Weighted Score", ascending=False)
        fig = px.bar(rep, x="Department", y="Weighted Score")

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(rep, use_container_width=True, hide_index=True)

    out = rep.to_csv(index=False).encode("utf-8")
    st.download_button("Download Report CSV", out, f"report_{sel_month}.csv", "text/csv")
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# Control Panel
# ============================================================
if menu == "Control Panel":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🛡 Control Panel (Admin Only)")
    st.markdown("<div class='small'>Yahan se KPI Names, Weights, Rating Rules, Permissions, Password sab manage hoga.</div>", unsafe_allow_html=True)
    st.markdown("<div class='hline'></div>", unsafe_allow_html=True)

    if not is_admin:
        st.warning("Admin login required.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    tab1, tab2, tab3, tab4 = st.tabs(["KPI Names", "KPI Weights", "Rating Rules", "Permissions & Password"])

    with tab1:
        st.markdown("### ✏️ KPI Labels")
        k1,k2,k3,k4 = get_kpi_labels()
        n1 = st.text_input("KPI1 Label", value=k1)
        n2 = st.text_input("KPI2 Label", value=k2)
        n3 = st.text_input("KPI3 Label", value=k3)
        n4 = st.text_input("KPI4 Label", value=k4)
        if st.button("Save KPI Labels"):
            run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi1'", [n1.strip() or "KPI 1"])
            run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi2'", [n2.strip() or "KPI 2"])
            run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi3'", [n3.strip() or "KPI 3"])
            run("UPDATE kpi_master SET kpi_label=%s WHERE kpi_key='kpi4'", [n4.strip() or "KPI 4"])
            st.success("Saved ✅"); st.rerun()

    with tab2:
        st.markdown("### ⚖️ KPI Weights (Total 100%)")
        w1,w2,w3,w4 = get_kpi_weights()
        nw1 = st.number_input("Weight KPI1", 0, 100, int(w1), 1)
        nw2 = st.number_input("Weight KPI2", 0, 100, int(w2), 1)
        nw3 = st.number_input("Weight KPI3", 0, 100, int(w3), 1)
        nw4 = st.number_input("Weight KPI4", 0, 100, int(w4), 1)
        totalw = nw1+nw2+nw3+nw4
        st.info(f"Total Weight = {totalw}")
        if st.button("Save Weights"):
            if totalw != 100:
                st.error("Total weights must be exactly 100.")
            else:
                run("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi1'", [int(nw1)])
                run("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi2'", [int(nw2)])
                run("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi3'", [int(nw3)])
                run("UPDATE kpi_weights SET weight=%s WHERE kpi_key='kpi4'", [int(nw4)])
                st.success("Weights saved ✅"); st.rerun()

    with tab3:
        st.markdown("### ⭐ Rating Rules (Score out of 100)")
        ex, gd, av = get_rating_rules()
        nex = st.number_input("Excellent Min", 0, 100, int(ex), 1)
        ngd = st.number_input("Good Min", 0, 100, int(gd), 1)
        nav = st.number_input("Average Min", 0, 100, int(av), 1)
        st.caption("Excellent >= ex, Good >= gd, Average >= av else Needs Improvement")
        if st.button("Save Rating Rules"):
            if not (nex >= ngd >= nav):
                st.error("Rule should satisfy: Excellent >= Good >= Average")
            else:
                run("UPDATE rating_rules SET excellent_min=%s, good_min=%s, average_min=%s WHERE id=1",
                    [int(nex), int(ngd), int(nav)])
                st.success("Saved ✅"); st.rerun()

    with tab4:
        st.markdown("### ✅ Permissions")
        cur_imp = get_setting("allow_import","1") == "1"
        cur_ed = get_setting("allow_edit_delete","1") == "1"
        ni = st.checkbox("Allow Import (Admin)", value=cur_imp)
        ne = st.checkbox("Allow Edit/Delete (Admin)", value=cur_ed)
        if st.button("Save Permissions"):
            set_setting("allow_import", "1" if ni else "0")
            set_setting("allow_edit_delete", "1" if ne else "0")
            st.success("Saved ✅"); st.rerun()

        st.markdown("<div class='hline'></div>", unsafe_allow_html=True)
        st.markdown("### 🔐 Change Admin Password")
        newpw1 = st.text_input("New Password", type="password")
        newpw2 = st.text_input("Confirm Password", type="password")
        if st.button("Update Password"):
            if not newpw1 or len(newpw1) < 4:
                st.error("Password min 4 characters.")
            elif newpw1 != newpw2:
                st.error("Passwords do not match.")
            else:
                set_setting("admin_password", newpw1)
                st.success("Password updated ✅ (Login again)")
                st.session_state["is_admin"] = False
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
