import os
import sys
from dotenv import load_dotenv

# ── Environment ───────────────────────────────────────────────────────────────
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path, override=True)

# ── Force UTF-8 stdout so Unicode in LLM responses doesn't crash print() on Windows ──
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass  # Already UTF-8 or not reconfigurable (e.g. Hugging Face)

# ── LLM Provider Configuration ────────────────────────────────────────────────
PROVIDERS = {
    "cerebras": {
        "api_key_env":  "CEREBRAS_API_KEY",
        "default_url":  "https://api.cerebras.ai/v1",
        "default_model": "gpt-oss-120b",
    },
    "groq": {
        "api_key_env":  "GROQ_API_KEY",
        "default_url":  "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openai": {
        "api_key_env":  "OPENAI_API_KEY",
        "default_url":  "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
    },
}

# ── Cal.com Configuration ─────────────────────────────────────────────────────
CALCOM_API_KEY        = os.getenv("CALCOM_API_KEY", "")
CALCOM_EVENT_TYPE_ID  = os.getenv("CALCOM_EVENT_TYPE_ID", "")
CALCOM_USERNAME       = os.getenv("CALCOM_USERNAME", "rahul-hirur")
CALCOM_TIMEZONE       = os.getenv("CALCOM_DEFAULT_TIMEZONE", "Asia/Kolkata")
CALCOM_LOOKAHEAD_DAYS = int(os.getenv("CALCOM_AVAILABILITY_DAYS", "7"))
CALCOM_BASE_URL       = "https://api.cal.com/v2"
SCHEDULING_ENABLED    = bool(CALCOM_API_KEY and CALCOM_EVENT_TYPE_ID)
