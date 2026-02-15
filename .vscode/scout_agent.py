import os
from googlesearch import search
import pandas as pd
import time
from urllib.parse import urlparse
from typing import List

# Optional SerpAPI fallback - requires `google-search-results` package and SERPAPI_API_KEY env var
try:
    from serpapi import GoogleSearch
except Exception:
    GoogleSearch = None

def serpapi_search(query: str, num_results: int = 10) -> List[str]:
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key or GoogleSearch is None:
        return []
    params = {
        "q": query,
        "engine": "google",
        "api_key": api_key,
        "num": num_results,
    }
    try:
        client = GoogleSearch(params)
        data = client.get_dict()
        urls = []
        for item in data.get("organic_results", []):
            link = item.get("link") or item.get("displayed_link")
            if link:
                urls.append(link)
        return urls
    except Exception:
        return []

def scout_leads(niche, location, num_results=20):
    query = f"{niche} {location} official site"
    print(f"🚀 Scout Agent starting...")
    
    leads = []
    # Avoid picking up directories—we want direct business owners
    forbidden = ['yelp', 'yellowpages', 'crunchbase', 'thumbtack', 'bbb.org', 'facebook']
    
    try:
        # We start small (20 results) to ensure we don't get '429 Too Many Requests' from Google
        # Try to collect raw results (try advanced mode first, then fallback)
        raw_results = list(search(query, num_results=num_results, advanced=True, sleep_interval=2))
        if not raw_results:
            # try basic search fallback
            raw_results = list(search(query, num_results=num_results, sleep_interval=2))

        print(f"🔁 search() returned {len(raw_results)} raw results")

        # If scraping returned no results, try SerpAPI fallback (if configured)
        if not raw_results:
            serp_results = serpapi_search(query, num_results=num_results)
            if serp_results:
                print(f"🔁 SerpAPI returned {len(serp_results)} results (fallback)")
                raw_results = serp_results

        for url in raw_results:
            parsed = urlparse(url)
            host = (parsed.netloc or "").lower()
            if any(f in host for f in forbidden):
                # debug: show skipped host for inspection
                print(f"⛔ Skipped (forbidden host): {host} --> {url}")
                continue

            # debug (remove after confirming)
            print(f"🔎 Raw result: {url}")

            print(f"📍 Lead Found: {url}")
            leads.append({"URL": url, "Status": "Unscanned"})
            time.sleep(2)
                
        if leads:
            df = pd.DataFrame(leads)
            # 'a' mode appends so you don't delete your old leads!
            df.to_csv("leads_queue.csv", mode='a', index=False, header=not os.path.exists("leads_queue.csv"))
            print(f"✅ Success! {len(leads)} leads added to leads_queue.csv")
        else:
            print("⚠️ No direct business websites found. Try changing the niche.")
            
    except Exception as e:
        print(f"❌ Error: {e}. You might be searching too fast. Wait 5 minutes.")

if __name__ == "__main__":
    # Let's start with something local to you to test the quality
    scout_leads(niche="Solar Panel Installation", location="Colorado Springs")
