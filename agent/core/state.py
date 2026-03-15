import os
import json
import asyncio
import logging

SESSIONS_FILE = "data/sessions.json"
DOWNLOADS_DIR = "downloads"

def ensure_downloads_dir():
    if not os.path.exists(DOWNLOADS_DIR):
        os.makedirs(DOWNLOADS_DIR)

ensure_downloads_dir()

def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load sessions: {e}")
            return {}
    return {}

def save_sessions():
    if not os.path.exists("data"):
        os.makedirs("data")
    with open(SESSIONS_FILE, "w") as f:
        json.dump(user_sessions, f)

user_sessions = load_sessions()
user_usage = {}
session_summarized_at = {}
session_lock = asyncio.Lock()
running_tasks = {}
