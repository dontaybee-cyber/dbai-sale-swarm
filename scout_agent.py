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

def load_sent_history() -> set:
    """Load domains contacted in the last 30 days to prevent spam."""
    blocked_domains = set()
    history_file = "audits_to_send.csv"
    
    if not os.path.exists(history_file):
        return blocked_domains
        
    try:
        # Read history with error skipping
        df = pd.read_csv(history_file, on_bad_lines='skip')
        if "Sent Date" not in df.columns or "URL" not in df.columns:
            return blocked_domains
            
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for _, row in df.iterrows():
            sent_date_str = str(row.get("Sent Date", ""))
            url = str(row.get("URL", ""))
            
            if sent_date_str and sent_date_str.lower() != "nan":
                try:
                    sent_date = datetime.strptime(sent_date_str, "%Y-%m-%d")
                    if sent_date >= cutoff_date:
                        domain = urlparse(url).netloc.lower()
                        if domain:
                            blocked_domains.add(domain)
                except ValueError:
                    continue
    except Exception as e:
        ui.log_warning(f"Could not load sent history: {e}")
        
    return blocked_domains

def scout_leads(niche, location, num_results=20):
    ui.SwarmHeader.display()
    ui.display_mission_briefing(niche, location)
    
    # Load 30-day cooldown list
    blocked_domains = load_sent_history()
    if blocked_domains:
        ui.log_info(f"Active Cooldown: {len(blocked_domains)} domains blocked (contacted < 30 days ago).")
    
    query = f"{niche} in {location} business website"
    ui.log_scout(f"Starting search for: [bold white]{query}[/bold white]")
    
    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        ui.log_warning("SERP_API_KEY is missing from .env configuration.")
        
        # Interactive Fix
        api_key = ui.console.input("[bold yellow]Please paste your SERP_API_KEY right now:[/bold yellow] ").strip()
        
        if api_key:
            with open(".env", "a") as f:
                f.write(f"\nSERP_API_KEY={api_key}")
            ui.log_success("Key appended to .env file.")
            
            # Verify write
            ui.console.print("[dim]--- Last 3 lines of .env ---[/dim]")
            with open(".env", "r") as f:
                for line in f.readlines()[-3:]:
                    ui.console.print(f"[dim]{line.strip()}[/dim]")
        else:
            ui.log_error("No key provided. Cannot proceed.")
            return

    if GoogleSearch is None:
        ui.log_error("The 'google-search-results' library is not installed.")
        ui.log_info("Run: pip install google-search-results")
        return

    ui.log_scout("🛰️ SCOUT: Using SerpAPI for deep-search...")

    leads = []
    # Avoid picking up directories—we want direct business owners
    forbidden = ['yelp', 'yellowpages', 'crunchbase', 'thumbtack', 'bbb.org', 'facebook', 'linkedin', 'angi', 'homeadvisor', 'porch']
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": num_results
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        organic_results = results.get("organic_results", [])
        
        if not organic_results:
             ui.log_warning("SerpAPI returned no organic results.")

        for result in ui.track(organic_results, description="[scout]Filtering & Verifying Leads...[/scout]"):
            url = result.get("link")
            if not url:
                continue

            parsed = urlparse(url)
            host = (parsed.netloc or "").lower()
            
            # Check 30-day cooldown
            if host in blocked_domains:
                ui.log_scout(f"Skipping {host} - In 30-day cooldown.")
                continue
                
            if any(f in host for f in forbidden):
                continue

            ui.log_success(f"Lead Found: {url}")
            leads.append({"URL": url, "Status": "Unscanned"})
                
        if leads:
            df = pd.DataFrame(leads)
            # 'a' mode appends so you don't delete your old leads!
            df.to_csv("leads_queue.csv", mode='a', index=False, header=not os.path.exists("leads_queue.csv"))
            ui.display_dashboard(leads_found=len(leads))
            ui.log_success(f"{len(leads)} leads added to leads_queue.csv")
        else:
            ui.log_warning("No direct business websites found after filtering.")
            
    except Exception as e:
        ui.log_error(f"SerpAPI failed: {e}")

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
