import os
import random
import re
import time
from typing import Optional, Tuple, Dict
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import ui_manager as ui

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

try:
    import google.generativeai as genai
    genai_available = True
    try:
        genai.configure(api_key=API_KEY)
    except Exception:
        # some installs expose a different configure API; ignore here and rely on calls
        pass
except Exception:
    genai_available = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]

def fetch_site_text(url: str, timeout: int = 15, retries: int = 1) -> Tuple[Optional[str], Dict[str, str]]:
    ui.log_analyst(f"Fetching site text for: {url}")
    socials = {"Contact_Page": None}
    
    for attempt in range(retries + 1):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            resp = requests.get(url, timeout=timeout, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extract emails from mailto links to ensure they are captured
            mailtos = [a["href"].replace("mailto:", "") for a in soup.select('a[href^="mailto:"]')]
            
            # Extract Social Media Links
            for link in soup.find_all('a', href=True):
                href = link['href']
                lower_href = href.lower()
                
                # Social Media
                if "facebook.com" in lower_href and "sharer" not in lower_href:
                    socials["Facebook"] = href
                elif "linkedin.com" in lower_href and "share" not in lower_href:
                    socials["LinkedIn"] = href
                elif "instagram.com" in lower_href:
                    socials["Instagram"] = href
                elif "twitter.com" in lower_href or "x.com" in lower_href:
                    socials["Twitter"] = href
                
                # Contact Page Detection
                if "contact" in lower_href and not socials.get("Contact_Page"):
                    # Resolve relative URLs
                    socials["Contact_Page"] = urljoin(url, href)

            text = soup.get_text(separator=" ", strip=True)
            if not text:
                ui.log_warning(f"No text content found for {url}")
                return None, socials
            if mailtos:
                text += " " + " ".join(mailtos)
            ui.log_analyst(f"Successfully fetched {len(text)} characters")
            return text[:2000], socials
        except Exception as e:
            if attempt < retries:
                ui.log_warning(f"Attempt {attempt+1} failed for {url}: {e}. Retrying...")
                time.sleep(2)
            else:
                ui.log_warning(f"Failed to fetch {url} after {retries+1} attempts: {e}")
                return None, socials

def analyze_with_gemini(site_dna: str) -> Optional[str]:
    prompt = f"""
You are a high-end AI Automation Consultant. Analyze this local business website text.
Find ONE specific inefficiency related to lead capture or customer service.
Focus on things like: No instant web-chat, manual booking forms, no after-hours lead capture, or buried contact info.
Write exactly ONE conversational sentence that I can drop into a cold email. 
Format: Point out the specific flaw, and hint at the revenue they are losing.
Do NOT use buzzwords like 'synergy', 'optimize', or 'paradigm'. Speak like a normal human.
Example Good Output: "I noticed you don't have an automated web-chat on your site, which means any traffic landing there after 5 PM is likely bouncing to a competitor."
Example Bad Output: "Your operational inefficiency regarding lead generation can be optimized with AI."
Website Text:
{site_dna}
"""
    try:
        if not genai_available:
            ui.log_warning("GenAI not available, skipping Gemini analysis.")
            return None
        # Use the modern GenerativeModel API
        try:
            ui.log_analyst("Sending prompt to Gemini...")
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt)
            text = response.text if hasattr(response, 'text') else str(response)
            ui.log_success("Gemini response received.")
            return text.strip().splitlines()[0]
        except Exception as e:
            ui.log_warning(f"Gemini generation failed: {e}")
            return None
    except Exception as e:
        ui.log_warning(f"Gemini API call failed: {e}")
        return None


def heuristic_analysis(site_dna: str) -> str:
    ui.log_analyst("Running heuristic analysis...")
    s = site_dna.lower()
    if "contact" not in s and "contact" not in s[:200]:
        ui.log_analyst("Heuristic triggered: No visible lead-capture form.")
        return "No visible lead-capture form — visitors can't convert without instant capture."
    if "book" in s and ("online" not in s and "book now" not in s):
        ui.log_analyst("Heuristic triggered: Manual booking process.")
        return "Manual booking process — customers must call instead of booking instantly."
    if "support" in s and ("chat" not in s and "help" in s):
        ui.log_analyst("Heuristic triggered: Outdated support flow.")
        return "Outdated support flow — no instant AI chat to resolve common issues."
    ui.log_analyst("Heuristic triggered: Default fallback.")
    return "Website lacks clear instant lead-capture — missed opportunities for immediate conversion."


def extract_email_from_text(text: str) -> Optional[str]:
    # Basic regex for email extraction
    # Advanced regex to catch emails buried in scripts/tags
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    
    ignore_terms = ['sentry', 'no-reply', 'noreply', 'example', 'domain', 'email', 'username', 'user', 'test']
    ignore_exts = ('.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.svg', '.woff', '.woff2', '.ttf', '.webp')

    if matches:
        for email in matches:
            lower_email = email.lower()
            # Filter out common false positives
            if any(term in lower_email for term in ignore_terms):
                continue
            if lower_email.endswith(ignore_exts):
                continue
            return email
    return None

def main():
    ui.SwarmHeader.display()
    ui.log_analyst("Analyst Agent starting...")
    
    if not os.path.exists("leads_queue.csv"):
        ui.log_error("leads_queue.csv not found in current directory.")
        return

    leads_df = pd.read_csv("leads_queue.csv")
    if "Status" not in leads_df.columns or "URL" not in leads_df.columns:
        ui.log_error("leads_queue.csv must contain 'URL' and 'Status' columns.")
        return

    out_rows = []
    updated = False
    ui.log_analyst(f"Found {len(leads_df)} rows in leads_queue.csv.")

    # Use UI track for progress bar
    for idx, row in ui.track(leads_df.iterrows(), total=len(leads_df), description="[analyst]Analyzing Sites...[/analyst]"):
        try:
            if str(row.get("Status", "")).strip().lower() != "unscanned":
                continue

            url = row.get("URL")
            site_dna, socials = fetch_site_text(url)
            extracted_email = None
            if not site_dna:
                pain = "Could not fetch site content"
            else:
                pain = None
                if genai_available and API_KEY:
                    pain = analyze_with_gemini(site_dna)
                if not pain:
                    ui.log_analyst("No pain point from Gemini, falling back to heuristics.")
                    pain = heuristic_analysis(site_dna)
                # Attempt to extract email from the site content
                extracted_email = extract_email_from_text(site_dna)
                if extracted_email:
                    ui.log_success(f"Extracted email: {extracted_email}")
                else:
                    # Deep Email Discovery: Check sub-pages
                    base_domain = url.rstrip("/")
                    sub_paths = ["/contact", "/about", "/contact-us", "/about-us", "/privacy"]
                    for path in sub_paths:
                        sub_url = base_domain + path
                        ui.log_analyst(f"Deep Search: Checking {sub_url} for email...")
                        sub_text, _ = fetch_site_text(sub_url, timeout=10, retries=0)
                        if sub_text:
                            extracted_email = extract_email_from_text(sub_text)
                            if extracted_email:
                                ui.log_success(f"Deep Search found email: {extracted_email}")
                                break

            # Waterfall Status Logic
            status = "Dead End"
            if extracted_email:
                status = "Analyzed"
            elif socials.get("Facebook") or socials.get("Instagram") or socials.get("LinkedIn") or socials.get("Twitter"):
                status = "Requires DM"
            elif socials.get("Contact_Page"):
                status = "Use Form"

            out_rows.append({
                "URL": url, 
                "Pain Point": pain, 
                "Status": status,
                "Email": extracted_email,
                "Facebook": socials.get("Facebook"),
                "LinkedIn": socials.get("LinkedIn"),
                "Instagram": socials.get("Instagram"),
                "Twitter": socials.get("Twitter"),
                "Contact Page": socials.get("Contact_Page")
            })
            leads_df.at[idx, "Status"] = "Processed"
            updated = True
        except Exception as e:
            ui.log_error(f"Unexpected error processing row {idx}: {e}")

    # Write audits_to_send.csv (append if exists)
    out_df = pd.DataFrame(out_rows, columns=["URL", "Pain Point", "Status", "Email", "Facebook", "LinkedIn", "Instagram", "Twitter", "Contact Page"])
    if not out_df.empty:
        if os.path.exists("audits_to_send.csv"):
            # Check if columns match to prevent corruption
            try:
                existing_cols = pd.read_csv("audits_to_send.csv", nrows=0).columns.tolist()
                if existing_cols == list(out_df.columns):
                    out_df.to_csv("audits_to_send.csv", mode="a", index=False, header=False)
                else:
                    ui.log_warning("CSV Schema mismatch (Old version detected). Overwriting audits_to_send.csv with new format.")
                    out_df.to_csv("audits_to_send.csv", index=False)
            except Exception:
                # If file is unreadable/corrupt, overwrite it
                out_df.to_csv("audits_to_send.csv", index=False)
        else:
            out_df.to_csv("audits_to_send.csv", index=False)
        ui.display_dashboard(sites_analyzed=len(out_df))
        ui.log_success(f"Wrote {len(out_df)} rows to audits_to_send.csv")

    # Save updated leads queue
    if updated:
        leads_df.to_csv("leads_queue.csv", index=False)
        ui.log_info("Updated leads_queue.csv statuses to 'Processed'.")


if __name__ == "__main__":
    main()
