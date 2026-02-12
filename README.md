# Scout Agent

Small script to discover local business websites.

Setup

1. Create and activate the project's virtualenv (Windows PowerShell):

```
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
```

2. Install dependencies:

```
python -m pip install -r requirements.txt
```

Run

```
python .\scout_agent.py
```

Notes
- The script writes `leads_queue.csv` in the current working directory.
- If Google scraping returns zero results, consider using SerpAPI or Google Custom Search API for reliable results.
