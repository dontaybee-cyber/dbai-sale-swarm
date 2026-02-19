import os
import random
import time
import smtplib
import imaplib
import pandas as pd
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import ui_manager as ui
import email
from email.policy import default
import google.generativeai as genai

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SENDER_NAME = os.getenv("SENDER_NAME", "Scout Agent Team")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_imap_connection():
    """Connect to Gmail IMAP to check for replies."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        return mail
    except Exception as e:
        ui.log_error(f"Failed to connect to IMAP: {e}")
        return None

def get_latest_reply_body(mail, recipient_email: str) -> str | None:
    """Fetch the body of the latest email from the recipient."""
    try:
        mail.select("inbox")
        status, messages = mail.search(None, f'(FROM "{recipient_email}")')
        if status != "OK" or not messages[0]:
            return None

        latest_email_id = messages[0].split()[-1]
        status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        
        if status != "OK":
            return None

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1], policy=default)
                
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            return part.get_payload(decode=True).decode()
                else:
                    return msg.get_payload(decode=True).decode()
        return None
    except Exception as e:
        ui.log_warning(f"Error fetching email body for {recipient_email}: {e}")
        return None


def analyze_reply_sentiment(reply_text: str) -> str:
    """Use Gemini to analyze the sentiment of an email reply."""
    if not GEMINI_API_KEY:
        ui.log_warning("GEMINI_API_KEY not set. Defaulting to 'Replied'.")
        return "Replied"
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""Read this email reply from a sales prospect. Categorize their intent into EXACTLY ONE of these four statuses: 'Hot Lead' (interested, asking questions, wants to meet), 'Not Interested' (polite rejection), 'Dead' (unsubscribe, angry, spam), or 'Replied' (out of office, unclear). Output ONLY the category string.

Email:
---
{reply_text}
---
Category:"""

        response = model.generate_content(prompt)
        
        # Sanitize the output to ensure it's one of the valid categories
        result = response.text.strip().replace("'", "").replace('"', '')
        valid_statuses = ['Hot Lead', 'Not Interested', 'Dead', 'Replied']
        if result in valid_statuses:
            return result
        else:
            ui.log_warning(f"Gemini returned an invalid category: '{result}'. Defaulting to 'Replied'.")
            return "Replied" # Default fallback
            
    except Exception as e:
        ui.log_error(f"Gemini analysis failed: {e}")
        return "Replied" # Return default status on error


def send_followup_email(recipient_email: str, url: str) -> bool:
    """Send a polite follow-up email."""
    if not EMAIL_USER or not EMAIL_PASS:
        return False

    domain = url.replace('https://', '').replace('http://', '').split('/')[0]
    subject = f"Re: Question about {domain}'s lead flow"
    
    body = f"""Hi again,

I know things get buried in the inbox, so I just wanted to float this to the top.

Did you get a chance to look at the AI audit I sent over for {domain}?

I'm confident that fixing that leak we identified will have an immediate impact on your conversion rates.

Let me know if you'd like me to resend the link.

Best,
{SENDER_NAME}
"""

    try:
        msg = MIMEMultipart()
        msg['From'] = f"{SENDER_NAME} <{EMAIL_USER}>"
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        ui.log_success(f"Follow-up sent to {recipient_email}")
        return True
    except Exception as e:
        ui.log_error(f"Failed to send follow-up to {recipient_email}: {e}")
        return False

def main(client_key: str):
    ui.SwarmHeader.display()
    ui.log_closer("Closer Agent starting...")
    
    audits_file = f"audits_to_send_{client_key}.csv"
    
    if not os.path.exists(audits_file):
        ui.log_error(f"{audits_file} not found.")
        return
        
    df = pd.read_csv(audits_file)
    
    if "Status" not in df.columns:
        ui.log_error(f"No 'Status' column found in {audits_file}.")
        return

    mail = get_imap_connection()
    if not mail:
        return

    followup_count = 0
    updated = False

    for idx, row in ui.track(df.iterrows(), total=len(df), description="[closer]Syncing inbox...[/closer]"):
        status = str(row.get("Status", "")).lower()
        recipient_email = row.get("Email")
        url = row.get("URL")

        if status in ["sent", "followed up"]:
            reply_text = get_latest_reply_body(mail, recipient_email)
            
            if reply_text:
                ui.log_closer(f"Reply detected from {recipient_email}. Analyzing content...")
                sentiment = analyze_reply_sentiment(reply_text)
                df.at[idx, "Status"] = sentiment
                ui.log_success(f"Status for {recipient_email} updated to '{sentiment}'.")
                updated = True
                continue # Move to the next lead

            # If no reply, check if it's time for a follow-up
            if status == "sent":
                sent_date_str = str(row.get("Sent Date", ""))
                if sent_date_str and sent_date_str != "nan":
                    try:
                        sent_date = datetime.strptime(sent_date_str, "%Y-%m-%d")
                        days_passed = (datetime.now() - sent_date).days
                        
                        if days_passed >= 3:
                            ui.log_closer(f"No reply from {recipient_email} after {days_passed} days. Sending follow-up...")
                            if send_followup_email(recipient_email, url):
                                df.at[idx, "Status"] = "Followed Up"
                                updated = True
                                followup_count += 1
                                time.sleep(random.randint(30, 60)) # Stagger emails
                    except ValueError:
                        ui.log_warning(f"Invalid date format for row {idx}: {sent_date_str}")
                        continue
    
    mail.logout()

    if updated:
        df.to_csv(audits_file, index=False)
        ui.display_dashboard(followups_sent=followup_count)
        ui.log_success(f"Process complete. Sent {followup_count} follow-ups and updated {audits_file}.")
    else:
        ui.log_info("No new replies or follow-ups needed at this time.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Closer Agent - Follow-up and Reply Checker")
    parser.add_argument("--client_key", required=True, help="Client key for isolating data files.")
    args = parser.parse_args()
    main(args.client_key)
