import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
import ui_manager as ui

# Import Agents
import scout_agent
import analyst_agent
import sniper_agent

# Load environment variables (Local fallback)
load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="DBAI Audit Swarm",
    page_icon="🚀",
    layout="wide"
)

# --- Helper Functions ---
def get_config(key, default=""):
    """Get configuration from st.secrets (Cloud) or os.getenv (Local)."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return os.getenv(key, default)

def render_header():
    st.markdown("""
    <div style="background-color:#0F172A;padding:15px;border-bottom: 3px solid #38BDF8;border-radius: 5px;margin-bottom: 20px;">
        <h1 style="color:#F8FAFC; margin:0; font-size: 24px;">🚀 DBAI Audit Swarm</h1>
        <p style="color:#94A3B8; margin:0; font-size: 14px;">Automated Sales Command Center</p>
    </div>
    """, unsafe_allow_html=True)

def load_csv(filename):
    if os.path.exists(filename):
        try:
            return pd.read_csv(filename)
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def save_env(key, value):
    """Save to .env file (Local only)."""
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    key_found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            key_found = True
        else:
            new_lines.append(line)
    
    if not key_found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"{key}={value}\n")
        
    with open(env_path, "w") as f:
        f.writelines(new_lines)

# --- Main App ---
render_header()

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["📊 Mission Control", "🔭 Scout", "🧠 Analyst", "🎯 Sniper", "⚙️ Settings"])

# --- TAB 1: MISSION CONTROL ---
if page == "📊 Mission Control":
    st.subheader("Live Mission Stats")

    leads_df = load_csv("leads_queue.csv")
    audits_df = load_csv("audits_to_send.csv")

    col1, col2, col3, col4 = st.columns(4)

    leads_count = len(leads_df) if not leads_df.empty else 0
    analyzed_count = len(audits_df) if not audits_df.empty else 0
    sent_count = len(audits_df[audits_df["Status"] == "Sent"]) if not audits_df.empty and "Status" in audits_df.columns else 0

    col1.metric("Leads Found", leads_count, delta="Scout")
    col2.metric("Sites Analyzed", analyzed_count, delta="Analyst")
    col3.metric("Emails Sent", sent_count, delta="Sniper")

    st.divider()
    st.subheader("Pipeline Status")
    if not leads_df.empty and "Status" in leads_df.columns:
        st.bar_chart(leads_df["Status"].value_counts())
    else:
        st.info("No data available for visualization.")

# --- TAB 2: SCOUT ---
elif page == "🔭 Scout":
    st.subheader("Lead Discovery")
    col1, col2 = st.columns(2)
    niche = col1.text_input("Target Niche", value="Roofing", placeholder="e.g. Dentists")
    location = col2.text_input("Target Location", value="Denver", placeholder="e.g. Chicago")

    if st.button("🚀 Launch Scout", type="primary"):
        with st.status("Scout is searching...", expanded=True):
            scout_agent.scout_leads(niche, location)
        st.success("Mission Complete!")
        st.rerun()

    st.divider()
    leads_df = load_csv("leads_queue.csv")
    if not leads_df.empty:
        st.dataframe(leads_df, use_container_width=True)

# --- TAB 3: ANALYST ---
elif page == "🧠 Analyst":
    st.subheader("AI Analysis")
    if st.button("🧠 Start Analysis", type="primary"):
        with st.status("Analyst is working...", expanded=True):
            analyst_agent.main()
        st.success("Analysis Complete!")
        st.rerun()

    with st.expander("Live Agent Logs", expanded=True):
        log_file = os.path.join("logs", "swarm.log")
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                lines = f.readlines()
                st.code("".join(lines[-20:]), language="log")
        else:
            st.info("No logs found.")

# --- TAB 4: SNIPER ---
elif page == "🎯 Sniper":
    st.subheader("Email Outreach")
    if st.button("🎯 Fire Sniper Emails", type="primary"):
        with st.status("Sniper is engaging targets...", expanded=True):
            sniper_agent.main()
        st.success("Outreach Complete!")
        st.rerun()

    audits_df = load_csv("audits_to_send.csv")
    if not audits_df.empty and "Status" in audits_df.columns:
        sent_df = audits_df[audits_df["Status"] == "Sent"]
        st.dataframe(sent_df, use_container_width=True)

# --- TAB 5: SETTINGS ---
elif page == "⚙️ Settings":
    st.subheader("Configuration")
    
    with st.form("config_form"):
        gemini_key = st.text_input("GEMINI_API_KEY", value=get_config("GEMINI_API_KEY"), type="password")
        serp_key = st.text_input("SERP_API_KEY", value=get_config("SERP_API_KEY"), type="password")
        email_user = st.text_input("EMAIL_USER", value=get_config("EMAIL_USER"))
        email_pass = st.text_input("EMAIL_PASS", value=get_config("EMAIL_PASS"), type="password")
        
        if st.form_submit_button("Save Config"):
            if not hasattr(st, "secrets"):
                save_env("GEMINI_API_KEY", gemini_key)
                save_env("SERP_API_KEY", serp_key)
                save_env("EMAIL_USER", email_user)
                save_env("EMAIL_PASS", email_pass)
                st.success("Configuration saved to .env!")
            else:
                st.warning("Cannot write to .env in Cloud mode. Please set secrets in Streamlit Cloud dashboard.")