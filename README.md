# DBAI SaleSwarm (Streamlit)

Streamlit app that runs the Scout → Analyst → Sniper → Closer workflow.

## Local setup

1) Create and activate a virtualenv (Windows PowerShell):

```powershell
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
```

2) Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3) Create a local `.env` (example keys):

```env
# Required for login (choose one approach)
MASTER_KEY=your_master_key
# or set CLIENT_KEYS in Streamlit secrets when deploying

# Scout (SerpAPI)
SERP_API_KEY=your_serpapi_key

# Analyst (Gemini)
GEMINI_API_KEY=your_gemini_key

# Sniper/Closer (email) - optional for local testing
EMAIL_USER=you@gmail.com
EMAIL_PASS=your_gmail_app_password
HUNTER_API_KEY=optional_hunter_key

# App behavior
CLOUD_MODE=false
SENDER_NAME=Your Name
```

4) Run the Streamlit app:

```powershell
streamlit run app.py
```

## Streamlit Cloud deployment

1) Push this repo to GitHub.

2) In Streamlit Cloud:
- App file: `app.py`
- Python dependencies: `requirements.txt` (already included)

3) Add secrets in Streamlit Cloud (App → Settings → Secrets). Example:

```toml
# Login
CLIENT_KEYS = ["client1", "client2"]
# Optional override
MASTER_KEY = "your_master_key"

# APIs
SERP_API_KEY = "your_serpapi_key"
GEMINI_API_KEY = "your_gemini_key"

# Email (optional; may not work on Streamlit Cloud due to SMTP/IMAP restrictions)
EMAIL_USER = "you@gmail.com"
EMAIL_PASS = "your_gmail_app_password"
HUNTER_API_KEY = "optional_hunter_key"

# App behavior
CLOUD_MODE = "true"
SENDER_NAME = "Your Name"
```

## Important notes / limitations

- The app writes CSVs and logs to the local filesystem (ephemeral on Streamlit Cloud). Data may reset on redeploy/restart.
- SMTP/IMAP (Gmail) often fails on hosted platforms. For production, replace with an email API provider and Gmail API.
