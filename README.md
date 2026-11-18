# Smart Barangay Appointment Scheduling and Document Processing Information System

A Streamlit and SQLite prototype for online barangay document requests, appointment scheduling, request tracking, and administrator processing.

## Features
- Resident account registration and login
- Online requests for barangay documents
- Appointment date and time selection
- Simple slot-capacity checking (5 residents per time slot)
- Resident request tracking and CSV download
- Admin dashboard, request status updates, notes, and CSV export
- Password hashing using PBKDF2

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Create and activate a virtual environment (optional but recommended).
4. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the application:
   ```bash
   streamlit run app.py
   ```
6. Open the local URL shown in the terminal.

## Demo administrator
- Username: `admin`
- Password: `admin12345`

Change/remove this demo account and add secure administrator provisioning before any real deployment. Use fictional data while testing.

## Upload to GitHub
1. Create a new **public** GitHub repository, for example `smart-barangay-appointment-system`.
2. Upload `app.py`, `requirements.txt`, `README.md`, and `.gitignore`.
3. Do not upload `barangay.db`, real resident information, passwords, or private documents.

## Deploy on Streamlit Community Cloud
1. Sign in to Streamlit Community Cloud using GitHub.
2. Choose **Create app** and select your repository, branch `main`, and file `app.py`.
3. Deploy the app.

## Important prototype limitations
- SQLite is suitable for local demonstration. The local database file may not persist reliably across Streamlit Community Cloud restarts/redeployments. For a real barangay deployment, use a managed persistent database and backups.
- This prototype does not issue official certificates, collect online payments, verify identity, or securely store uploaded documentary evidence.
- A barangay must define actual requirements, fees, office hours, capacity, approval rules, privacy notices, and records-retention procedures before production use.
- Do not enter real personal information in a public classroom demo.
