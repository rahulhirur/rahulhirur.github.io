import os
from langchain_core.tools import tool
from config import SCHEDULING_ENABLED
from scheduler import get_available_slots, create_booking

@tool
def request_scheduling_form() -> str:
    """
    Call this tool ONLY when the visitor explicitly asks to schedule/book a
    meeting with Rahul (e.g. "I want to meet him", "Let's schedule a call", "Book a meeting").
    This will render an interactive calendar slot picker directly in their chat.
    After calling this tool, reply to the user with a polite, warm confirmation.
    """
    return "__SCHEDULE_FORM_REQUESTED__"

# ── Tool Registry ─────────────────────────────────────────────────────────────
TOOLS = [request_scheduling_form, get_available_slots, create_booking] if SCHEDULING_ENABLED else []

# ── System Prompt Loader ──────────────────────────────────────────────────────
def load_system_instruction() -> str:
    path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Warning: could not load system_prompt.md — {e}")
        return "You are Rahul's AI Assistant. Represent his career professionally."
