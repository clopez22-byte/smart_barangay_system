import streamlit as st
import sqlite3
import hashlib
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd

st.set_page_config(page_title="Smart Barangay System", page_icon="🏛️", layout="wide")
DB_PATH = Path(__file__).with_name("barangay.db")
DOCUMENTS = ["Barangay Clearance", "Certificate of Indigency", "Certificate of Residency", "Cedula / Community Tax Certificate", "Barangay Business Clearance", "Other"]
TIME_SLOTS = ["8:00 AM - 9:00 AM", "9:00 AM - 10:00 AM", "10:00 AM - 11:00 AM", "1:00 PM - 2:00 PM", "2:00 PM - 3:00 PM", "3:00 PM - 4:00 PM"]
SLOT_CAPACITY = 5

def connect():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"

def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
        return secrets.compare_digest(hash_password(password, salt).split("$", 1)[1], digest)
    except ValueError:
        return False

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'resident',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, document_type TEXT NOT NULL,
            purpose TEXT NOT NULL, appointment_date TEXT NOT NULL,
            time_slot TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending',
            admin_note TEXT DEFAULT '', created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
        admin = con.execute("SELECT id FROM users WHERE username='admin'").fetchone()
        if not admin:
            con.execute(
                "INSERT INTO users(full_name,username,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                ("Barangay Administrator", "admin", hash_password("admin12345"), "admin", datetime.now().isoformat(timespec="seconds"))
            )

def register(full_name, username, password):
    with connect() as con:
        con.execute(
            "INSERT INTO users(full_name,username,password_hash,role,created_at) VALUES(?,?,?,?,?)",
            (full_name.strip(), username.strip().lower(), hash_password(password), "resident", datetime.now().isoformat(timespec="seconds"))
        )

def get_user(username):
    with connect() as con:
        return con.execute("SELECT * FROM users WHERE username=?", (username.lower(),)).fetchone()

def available_slots(day, slot):
    with connect() as con:
        count = con.execute(
            "SELECT COUNT(*) FROM requests WHERE appointment_date=? AND time_slot=? AND status!='Rejected'",
            (str(day), slot)
        ).fetchone()[0]
    return max(0, SLOT_CAPACITY - count)

def create_request(user_id, document, purpose, day, slot):
    with connect() as con:
        count = con.execute(
            "SELECT COUNT(*) FROM requests WHERE appointment_date=? AND time_slot=? AND status!='Rejected'",
            (str(day), slot)
        ).fetchone()[0]
        if count >= SLOT_CAPACITY:
            return False
        con.execute(
            """INSERT INTO requests(user_id,document_type,purpose,appointment_date,time_slot,status,created_at)
               VALUES(?,?,?,?,?,'Pending',?)""",
            (user_id, document, purpose.strip(), str(day), slot, datetime.now().isoformat(timespec="seconds"))
        )
    return True

def resident_requests(user_id):
    with connect() as con:
        return pd.read_sql_query(
            """SELECT id AS 'Request ID', document_type AS 'Document', purpose AS 'Purpose',
               appointment_date AS 'Appointment Date', time_slot AS 'Time', status AS 'Status',
               admin_note AS 'Admin Note' FROM requests WHERE user_id=? ORDER BY id DESC""",
            con, params=(user_id,)
        )

def all_requests():
    with connect() as con:
        return pd.read_sql_query(
            """SELECT r.id AS 'Request ID', u.full_name AS 'Resident', u.username AS 'Username',
               r.document_type AS 'Document', r.purpose AS 'Purpose',
               r.appointment_date AS 'Appointment Date', r.time_slot AS 'Time',
               r.status AS 'Status', r.admin_note AS 'Admin Note'
               FROM requests r JOIN users u ON r.user_id=u.id ORDER BY r.appointment_date DESC, r.id DESC""", con
        )

def update_request(request_id, status, note):
    with connect() as con:
        con.execute("UPDATE requests SET status=?, admin_note=? WHERE id=?", (status, note, int(request_id)))

def logout():
    for key in ["user_id", "username", "full_name", "role"]:
        st.session_state.pop(key, None)
    st.rerun()

init_db()

st.sidebar.title("🏛️ Smart Barangay")
st.sidebar.caption("Appointment & Document Processing")
if "user_id" not in st.session_state:
    page = st.sidebar.radio("Welcome", ["Login", "Create Account"])
    st.title("🏛️ Smart Barangay Appointment and Document System")
    st.write("Request barangay documents and schedule an appointment without lining up just to submit your initial request.")
    if page == "Login":
        st.subheader("Resident / Administrator Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            user = get_user(username.strip())
            if user and verify_password(password, user["password_hash"]):
                st.session_state.user_id = user["id"]
                st.session_state.username = user["username"]
                st.session_state.full_name = user["full_name"]
                st.session_state.role = user["role"]
                st.rerun()
            else:
                st.error("Incorrect username or password.")
        st.info("Demo administrator: username `admin` | password `admin12345`. Change this before any real deployment.")
    else:
        st.subheader("Create Resident Account")
        with st.form("register_form"):
            full_name = st.text_input("Complete name")
            username = st.text_input("Choose a username")
            password = st.text_input("Create password (at least 8 characters)", type="password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)
        if submitted:
            if not full_name.strip() or not username.strip():
                st.error("Please complete all fields.")
            elif len(password) < 8:
                st.error("Password must contain at least 8 characters.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    register(full_name, username, password)
                    st.success("Account created. You can now log in.")
                except sqlite3.IntegrityError:
                    st.error("That username is already taken.")
else:
    st.sidebar.write(f"Signed in as **{st.session_state.full_name}**")
    st.sidebar.caption(f"Role: {st.session_state.role.title()}")
    if st.sidebar.button("Logout", use_container_width=True):
        logout()

    if st.session_state.role == "resident":
        page = st.sidebar.radio("Resident Menu", ["Dashboard", "Request a Document", "My Requests"])
        if page == "Dashboard":
            st.title("Resident Dashboard")
            st.write(f"Welcome, **{st.session_state.full_name}**!")
            data = resident_requests(st.session_state.user_id)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Requests", len(data))
            c2.metric("Pending", int((data["Status"] == "Pending").sum()) if not data.empty else 0)
            c3.metric("Approved / Completed", int(data["Status"].isin(["Approved", "Completed"]).sum()) if not data.empty else 0)
            st.subheader("How to use the system")
            st.markdown("1. Open **Request a Document**.\n2. Select the document and enter its purpose.\n3. Choose an appointment date and available time.\n4. Submit, then check **My Requests** for updates.")
            st.info("Bring the required supporting documents and valid identification to the barangay office. Online submission does not guarantee approval or issuance.")
        elif page == "Request a Document":
            st.title("Request a Barangay Document")
            st.caption("Appointments are limited to 5 residents per time slot in this prototype.")
            with st.form("request_form"):
                document = st.selectbox("Document type", DOCUMENTS)
                purpose = st.text_area("Purpose of request", placeholder="Example: For school or employment")
                min_day = date.today() + timedelta(days=1)
                max_day = date.today() + timedelta(days=60)
                appointment_day = st.date_input("Preferred appointment date", value=min_day, min_value=min_day, max_value=max_day)
                slot = st.selectbox("Preferred time", TIME_SLOTS)
                remaining = available_slots(appointment_day, slot)
                st.caption(f"Available appointments for this slot: {remaining} of {SLOT_CAPACITY}")
                submitted = st.form_submit_button("Submit Request", use_container_width=True)
            if submitted:
                if not purpose.strip():
                    st.error("Please enter the purpose of your request.")
                elif not remaining:
                    st.error("This time slot is full. Please choose another date or time.")
                elif create_request(st.session_state.user_id, document, purpose, appointment_day, slot):
                    st.success("Your request was submitted. Save your Request ID from My Requests.")
                    st.rerun()
                else:
                    st.error("The slot just became full. Please select another time.")
        else:
            st.title("My Document Requests")
            data = resident_requests(st.session_state.user_id)
            if data.empty:
                st.info("You have not submitted any requests yet.")
            else:
                st.dataframe(data, use_container_width=True, hide_index=True)
                st.download_button("Download my requests (CSV)", data.to_csv(index=False).encode("utf-8"), "my_barangay_requests.csv", "text/csv")
    else:
        page = st.sidebar.radio("Administrator Menu", ["Overview", "Manage Requests", "Appointment Schedule"])
        data = all_requests()
        if page == "Overview":
            st.title("Administrator Dashboard")
            a, b, c, d = st.columns(4)
            a.metric("Total Requests", len(data))
            b.metric("Pending", int((data["Status"] == "Pending").sum()) if not data.empty else 0)
            c.metric("Approved", int((data["Status"] == "Approved").sum()) if not data.empty else 0)
            d.metric("Completed", int((data["Status"] == "Completed").sum()) if not data.empty else 0)
            st.subheader("Recent Requests")
            st.dataframe(data.head(10), use_container_width=True, hide_index=True)
            if not data.empty:
                st.subheader("Requests by Status")
                st.bar_chart(data["Status"].value_counts())
        elif page == "Manage Requests":
            st.title("Manage Resident Requests")
            if data.empty:
                st.info("There are no requests yet.")
            else:
                st.dataframe(data, use_container_width=True, hide_index=True)
                ids = data["Request ID"].tolist()
                selected_id = st.selectbox("Select Request ID", ids)
                selected = data[data["Request ID"] == selected_id].iloc[0]
                st.write(f"**Resident:** {selected['Resident']}  |  **Document:** {selected['Document']}")
                with st.form("update_form"):
                    status = st.selectbox("Update status", ["Pending", "Under Review", "Approved", "Rejected", "Completed"], index=["Pending", "Under Review", "Approved", "Rejected", "Completed"].index(selected["Status"]))
                    note = st.text_area("Admin note", value=selected["Admin Note"] or "")
                    save = st.form_submit_button("Save Update")
                if save:
                    update_request(selected_id, status, note)
                    st.success("Request updated.")
                    st.rerun()
                st.download_button("Export all requests (CSV)", data=data.to_csv(index=False).encode("utf-8"), file_name="barangay_requests.csv", mime="text/csv")
        else:
            st.title("Appointment Schedule")
            if data.empty:
                st.info("No appointments have been booked.")
            else:
                upcoming = data[data["Appointment Date"] >= str(date.today())].copy()
                st.dataframe(upcoming[["Request ID", "Resident", "Document", "Appointment Date", "Time", "Status"]].sort_values(["Appointment Date", "Time"]), use_container_width=True, hide_index=True)

st.sidebar.divider()
st.sidebar.caption("Capstone prototype • Use fictional data during testing")
