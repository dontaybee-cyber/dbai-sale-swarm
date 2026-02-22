import os
import streamlit as st
from huggingface_hub import HfApi, hf_hub_download
import ui_manager as ui
def get_hf_api():
    token = st.secrets.get("HF_TOKEN", os.getenv("HF_TOKEN"))
    repo_id = st.secrets.get("HF_REPO_ID", os.getenv("HF_REPO_ID"))
    if token and repo_id:
        return HfApi(token=token), repo_id
    return None, None

def sync_down(filename: str):
    """Pulls the permanent CSV from the cloud vault to the local server."""
    api, repo_id = get_hf_api()
    if not api: return
    try:
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            repo_type="dataset",
            local_dir=".",
            token=api.token
        )
    except Exception:
        pass # File might not exist yet, which is fine

def sync_up(filename: str):
    """Pushes the updated CSV back to the permanent cloud vault."""
    api, repo_id = get_hf_api()
    if not api or not os.path.exists(filename): return
    try:
        api.upload_file(
            path_or_fileobj=filename,
            path_in_repo=filename,
            repo_id=repo_id,
            repo_type="dataset"
        )
    except Exception as e:
        ui.log_warning(f"Cloud sync failed for {filename}: {e}")
