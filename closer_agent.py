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

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SENDER_NAME = os.getenv("SENDER_NAME", "Scout Agent Team")

def get_imap_connection():
    """Connect to Gmail IMAP to check for replies."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        return mail
    except Exception as e:
        ui.log_error(f"Failed to connect to IMAP: {e}")
        return None

def has_replied(mail, recipient_email: str) -> bool:
    """Check if the recipient has replied to us."""
    try:
        mail.select("inbox")
        # Search for emails FROM the recipient
        status, messages = mail.search(None, f'(FROM "{recipient_email}")')
        if status == "OK":
            email_ids = messages[0].split()
            return len(email_ids) > 0
        return False
    except Exception as e:
        ui.log_warning(f"Error checking replies for {recipient_email}: {e}")
        # Fail-safe: If we can't check, assume they replied so we don't spam them.
        return True

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
        msg['From'] = EMAIL_USER
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
    
    if "Sent Date" not in df.columns:
        ui.log_error(f"No 'Sent Date' column found in {audits_file}. Run sniper_agent.py first.")
        return

    mail = get_imap_connection()
    if not mail:
        return

    followup_count = 0
    updated = False

    for idx, row in ui.track(df.iterrows(), total=len(df), description="[closer]Checking for replies...[/closer]"):
        status = str(row.get("Status", "")).lower()
        sent_date_str = str(row.get("Sent Date", ""))
        recipient_email = row.get("Email")
        url = row.get("URL")

        if status == "sent" and sent_date_str and sent_date_str != "nan":
            try:
                sent_date = datetime.strptime(sent_date_str, "%Y-%m-%d")
                days_passed = (datetime.now() - sent_date).days
                
                if days_passed >= 3:
                    ui.log_closer(f"Checking {recipient_email} (Sent {days_passed} days ago)...")
                    
                    if has_replied(mail, recipient_email):
                        ui.log_success(f"Reply detected from {recipient_email}. Marking as 'Replied'.")
                        df.at[idx, "Status"] = "Replied"
                        updated = True
                    else:
                        ui.log_closer(f"No reply from {recipient_email}. Sending follow-up...")
                        if send_followup_email(recipient_email, url):
                            df.at[idx, "Status"] = "Followed Up"
                            updated = True
                            followup_count += 1
                            time.sleep(random.randint(30, 60))
            except ValueError:
                ui.log_warning(f"Invalid date format for row {idx}: {sent_date_str}")
                continue

    mail.logout()

    if updated:
        df.to_csv(audits_file, index=False)
        ui.display_dashboard(followups_sent=followup_count)
        ui.log_success(f"Process complete. Sent {followup_count} follow-ups and updated {audits_file}.")
    else:
        ui.log_info("No follow-ups needed at this time.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Closer Agent - Follow-up and Reply Checker")
    parser.add_argument("--client_key", required=True, help="Client key for isolating data files.")
    args = parser.parse_args()
    main(args.client_key)