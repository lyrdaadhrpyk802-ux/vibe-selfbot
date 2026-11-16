# ============================================
#  selfbot/config.py - environment-based configuration
#  All code and comments are English. No emojis.
# ============================================
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_REPLY_TEXT = "\u0641\u0639\u0644\u0627 \u062f\u0631 \u062f\u0633\u062a\u0631\u0633 \u0646\u06cc\u0633\u062a\u0645..."

def _env(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"missing required env: {name}")
    return value

def _env_int(name, default):
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default

class Config:
    def __init__(self):
        self.session_b64 = _env("VIBE_SESSION_B64", required=True)
        self.gh_token = _env("GH_TOKEN", required=True)
        self.gist_id = _env("GIST_ID", required=True)
        self.gist_filename = _env("GIST_FILENAME", "replied.json")
        self.session_path = Path(_env("VIBE_SESSION_PATH", "/tmp/vibe_selfbot"))
        self.poll_interval = _env_int("POLL_INTERVAL", 10)
        self.delay_seconds = _env_int("DELAY_SECONDS", 5)
        self.reply_text = _env("REPLY_TEXT", DEFAULT_REPLY_TEXT)
        self.max_runtime_seconds = _env_int("MAX_RUNTIME_SECONDS", 21000)

    def is_within_work_hours(self):
        return True # Currently always on
