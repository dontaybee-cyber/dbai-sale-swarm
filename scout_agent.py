import os
import argparse
import pandas as pd
import time
from urllib.parse import urlparse
from dotenv import load_dotenv
import ui_manager as ui

load_dotenv(override=True)

# Optional SerpAPI fallback - requires `google-search-results` package and SERPAPI_API_KEY env var
try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

def get_known_domains(client_key: str) -> set:
    """The 'Ironclad Ledger': Load all known domains for a specific client to ensure zero repeated leads."""
    if not client_key:
        return set()
    
    known_domains = set()
    files = [f"leads_queue_{client_key}.csv", f"audits_to_send_{client_key}.csv"]
    
    for f in files:
        if os.path.exists(f):
            try:
                df = pd.read_csv(f, on_bad_lines='skip')
                if "URL" in df.columns:
                    for url in df["URL"].dropna():
                        domain = urlparse(str(url)).netloc.lower().replace('www.', '')
                        if domain:
                            known_domains.add(domain)
            except Exception:
                pass
    return known_domains

def scout_leads(niche, location, client_key, num_results=20):
    ui.SwarmHeader.display()
    ui.display_mission_briefing(niche, location)

    # Task 1: The Directory Blacklist
    blacklist = (
        "yelp.", "angi.", "bbb.", "houzz.", "thumbtack.", "expertise.", 
        "yellowpages.", "facebook.", "linkedin.", "instagram.", "twitter.", 
        "porch.", "homeadvisor.", "forbes."
    )

    master_domain_set = get_known_domains(client_key)
    if master_domain_set:
        ui.log_info(f"Loaded {len(master_domain_set)} known domains to skip for client '{client_key}'.")

    # Task 2: Advanced Search Query
    q = f'{niche} in {location} -yelp -angi -bbb -thumbtack'
    ui.log_scout(f"Starting search for: [bold white]{q}[/bold white]")

    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        ui.log_error("SERP_API_KEY is not configured. Please set it in your environment.")
        return

    if GoogleSearch is None:
        ui.log_error("The 'google-search-results' library is not installed.")
        ui.log_info("Run: pip install google-search-results")
        return

    ui.log_scout("🛰️ SCOUT: Using SerpAPI for deep-search...")

    TARGET_NEW_LEADS = 15
    fresh_leads = []
    search_offset = 0
    
    while len(fresh_leads) < TARGET_NEW_LEADS:
        if search_offset >= 50: # Safety breakout after 5 pages
            ui.log_warning(f"Checked 5 pages but couldn't find {TARGET_NEW_LEADS} new leads. Proceeding with {len(fresh_leads)} found.")
            break

        params = {
            "engine": "google",
            "q": q,
            "api_key": api_key,
            "num": num_results,
            "start": search_offset,
            "location": location,
        }
        
        ui.log_scout(f"Searching page {search_offset // 10 + 1}...")

        try:
            search = GoogleSearch(params)
            results = search.get_dict()

            # Task 3: Local Pack Extraction (Premium Leads)
            if "local_results" in results:
                ui.log_scout("Extracting from Google Local Pack...")
                for local in results["local_results"]:
                    website = local.get("website")
                    if website and not any(bad in website.lower() for bad in blacklist):
                        host = urlparse(website).netloc.lower().replace('www.', '')
                        if host and host not in master_domain_set:
                            ui.log_success(f"Premium Lead Found (Maps): {website}")
                            fresh_leads.append({"URL": website, "Status": "Unscanned"})
                            master_domain_set.add(host)
                            if len(fresh_leads) >= TARGET_NEW_LEADS: break
            
            if len(fresh_leads) >= TARGET_NEW_LEADS: break

            organic_results = results.get("organic_results", [])
            if not organic_results:
                ui.log_info("No more organic results found. Ending search.")
                break

            for result in organic_results:
                link = result.get("link")
                
                # Task 4: Filter Organic Results
                if link and not any(bad in link.lower() for bad in blacklist):
                    host = urlparse(link).netloc.lower().replace('www.', '')
                    if host and host not in master_domain_set:
                        ui.log_success(f"Lead Found (Organic): {link}")
                        fresh_leads.append({"URL": link, "Status": "Unscanned"})
                        master_domain_set.add(host)
                        if len(fresh_leads) >= TARGET_NEW_LEADS:
                            break
            
            search_offset += 10
            time.sleep(1) # Be respectful to the API

        except Exception as e:
            ui.log_error(f"SerpAPI failed: {e}")
            break
            
    if fresh_leads:
        leads_file = f"leads_queue_{client_key}.csv"
        df = pd.DataFrame(fresh_leads)
        
        # Append without header if file exists
        header = not os.path.exists(leads_file)
        df.to_csv(leads_file, mode='a', index=False, header=header)
        
        ui.display_dashboard(leads_found=len(fresh_leads))
        ui.log_success(f"{len(fresh_leads)} new leads added to {leads_file}")
    else:
        ui.log_warning("No new direct business websites found after deep search.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scout Agent - Lead Discovery")
    parser.add_argument("--niche", type=str, required=True, help="Target Niche (e.g., 'Roofing Contractors')")
    parser.add_argument("--location", type=str, required=True, help="Target Location (e.g., 'Denver, CO')")
    parser.add_argument("--client_key", type=str, required=True, help="Client-specific key for data isolation")
    args = parser.parse_args()
    
    scout_leads(niche=args.niche, location=args.location, client_key=args.client_key)