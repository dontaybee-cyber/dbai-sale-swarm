import os
import argparse
import pandas as pd
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import List
from dotenv import load_dotenv
import ui_manager as ui

load_dotenv(override=True)

# Optional SerpAPI fallback - requires `google-search-results` package and SERPAPI_API_KEY env var
try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

def get_known_domains() -> set:
    """The 'Ironclad Ledger': Load all known domains to ensure zero repeated leads."""
    known_domains = set()
    files = ["leads_queue.csv", "audits_to_send.csv"]
    for f in files:
        if os.path.exists(f):
            try:
                df = pd.read_csv(f, on_bad_lines='skip')
                if "URL" in df.columns:
                    for url in df["URL"].dropna():
                        domain = urlparse(str(url)).netloc.lower()
                        if domain:
                            known_domains.add(domain)
            except Exception:
                pass
    return known_domains

def scout_leads(niche, location, num_results=20):
    ui.SwarmHeader.display()
    ui.display_mission_briefing(niche, location)

    master_domain_set = get_known_domains()
    if master_domain_set:
        ui.log_info(f"Loaded {len(master_domain_set)} known domains to skip (Freshness Guarantee).")

    query = f'"{niche}" "{location}" -site:yelp.com -site:bbb.org -site:facebook.com -site:linkedin.com -site:yellowpages.com -site:angi.com'
    ui.log_scout(f"Starting search for: [bold white]{query}[/bold white]")

    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        ui.log_warning("SERP_API_KEY is missing from .env configuration.")
        api_key = ui.console.input("[bold yellow]Please paste your SERP_API_KEY right now:[/bold yellow] ").strip()
        if api_key:
            with open(".env", "a") as f:
                f.write(f"\nSERP_API_KEY={api_key}")
            ui.log_success("Key appended to .env file.")
        else:
            ui.log_error("No key provided. Cannot proceed.")
            return

    if GoogleSearch is None:
        ui.log_error("The 'google-search-results' library is not installed.")
        ui.log_info("Run: pip install google-search-results")
        return

    ui.log_scout("🛰️ SCOUT: Using SerpAPI for deep-search...")

    TARGET_NEW_LEADS = 10
    fresh_leads = []
    search_offset = 0
    
    forbidden = ['yelp', 'yellowpages', 'crunchbase', 'thumbtack', 'bbb.org', 'facebook', 'linkedin', 'angi', 'homeadvisor', 'porch']

    while len(fresh_leads) < TARGET_NEW_LEADS:
        if search_offset >= 50:
            ui.log_warning(f"Safety breakout: Checked 5 pages but couldn't find {TARGET_NEW_LEADS} new leads. Proceeding with {len(fresh_leads)} found.")
            break

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": num_results,
            "start": search_offset
        }
        
        ui.log_scout(f"Searching page {search_offset // 10 + 1}...")

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            organic_results = results.get("organic_results", [])

            if not organic_results:
                ui.log_info("No more organic results found. Ending search.")
                break

            for result in organic_results:
                url = result.get("link")
                if not url:
                    continue

                parsed = urlparse(url)
                host = (parsed.netloc or "").lower().replace('www.', '')

                if host in master_domain_set:
                    ui.log_scout(f"Skipping {host} - Already in system.")
                    continue
                
                if any(f in host for f in forbidden):
                    continue

                ui.log_success(f"Lead Found: {url}")
                fresh_leads.append({"URL": url, "Status": "Unscanned"})
                master_domain_set.add(host) # Add to master set to avoid duplicates in this session

                if len(fresh_leads) >= TARGET_NEW_LEADS:
                    break
            
            search_offset += 10 # Increment for the next page

        except Exception as e:
            ui.log_error(f"SerpAPI failed: {e}")
            break # Exit on API error
            
    if fresh_leads:
        df = pd.DataFrame(fresh_leads)
        df.to_csv("leads_queue.csv", mode='a', index=False, header=not os.path.exists("leads_queue.csv"))
        ui.display_dashboard(leads_found=len(fresh_leads))
        ui.log_success(f"{len(fresh_leads)} new leads added to leads_queue.csv")
    else:
        ui.log_warning("No new direct business websites found after deep search.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scout Agent - Lead Discovery")
    parser.add_argument("--niche", type=str, help="Target Niche")
    parser.add_argument("--location", type=str, help="Target Location")
    args = parser.parse_args()

    ui.SwarmHeader.display()
    
    try:
        if args.niche and args.location:
            scout_leads(niche=args.niche, location=args.location)
        else:
            target_niche = ui.console.input("[bold green]Enter Target Niche[/bold green] (e.g. Roofing) [default: Plumbing]: ").strip() or "Plumbing"
            target_location = ui.console.input("[bold green]Enter Target Location[/bold green] (e.g. Dallas) [default: Denver]: ").strip() or "Denver"

            if target_niche and target_location:
                scout_leads(niche=target_niche, location=target_location)
            else:
                ui.log_error("Niche and Location are required to run the Scout.")
    except KeyboardInterrupt:
        ui.console.print("\n[bold red]Aborted by user.[/bold red]")
