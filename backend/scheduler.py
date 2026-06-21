import os
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core.tools import tool
from config import (
    CALCOM_API_KEY,
    CALCOM_EVENT_TYPE_ID,
    CALCOM_TIMEZONE,
    CALCOM_LOOKAHEAD_DAYS,
    CALCOM_BASE_URL,
    SCHEDULING_ENABLED
)

# ── Cal.com API Helpers ───────────────────────────────────────────────────────
def _calcom_headers() -> dict:
    """Headers for Cal.com v2 slots / event-type endpoints."""
    return {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "cal-api-version": "2024-09-04",
        "Content-Type": "application/json",
    }

def _calcom_booking_headers() -> dict:
    """Headers for Cal.com v2 /bookings endpoint (requires a different API version)."""
    return {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "cal-api-version": "2024-08-13",
        "Content-Type": "application/json",
    }

def _fmt_slot(iso_str: str, tz_str: str) -> str:
    """Convert an ISO datetime string to a human-readable local time."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(ZoneInfo(tz_str)).strftime("%A, %B %d at %I:%M %p %Z")
    except Exception:
        return iso_str

def fetch_calcom_slots(date: str, duration: int = 30, timezone: str = "Asia/Kolkata") -> dict:
    """
    Fetch raw slots directly from Cal.com API and format them for the client.
    Used by the FastAPI slots endpoint.
    """
    if not SCHEDULING_ENABLED:
        return {"slots": [], "error": "Scheduling not configured"}

    tz = timezone.strip() or CALCOM_TIMEZONE
    try:
        params = {
            "start":       f"{date}T00:00:00.000Z",
            "end":         f"{date}T23:59:59.999Z",
            "eventTypeId": CALCOM_EVENT_TYPE_ID,
            "timeZone":    tz,
            "duration":    duration,
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{CALCOM_BASE_URL}/slots",
                headers=_calcom_headers(),
                params=params,
            )
            resp.raise_for_status()

        raw: dict = resp.json().get("data", {})
        slots_out = []
        for _date_key in sorted(raw):
            if not isinstance(raw[_date_key], list):
                continue
            for slot in raw[_date_key]:
                iso = slot.get("start") or slot.get("time") or ""
                if not iso:
                    continue
                try:
                    dt_local = datetime.fromisoformat(
                        iso.replace("Z", "+00:00")
                    ).astimezone(ZoneInfo(tz))
                    hhmm  = dt_local.strftime("%H:%M")
                    label = dt_local.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    hhmm  = iso
                    label = iso
                slots_out.append({"time": hhmm, "iso": iso, "label": label})

        return {"slots": slots_out}

    except httpx.HTTPStatusError as e:
        return {"slots": [], "error": f"Cal.com error {e.response.status_code}"}
    except Exception as e:
        return {"slots": [], "error": str(e)}

# ── Scheduling Tools ──────────────────────────────────────────────────────────
@tool
def get_available_slots(
    start_date: str,
    end_date: str,
    timezone: str = "",
    duration_minutes: int = 0,
) -> str:
    """
    Get Rahul's available meeting slots between two dates.
    Use this to show what times are open, or to find alternatives when a
    proposed time is unavailable.

    Args:
        start_date:        Start date in YYYY-MM-DD format.
        end_date:          End date in YYYY-MM-DD format.
        timezone:          Visitor's IANA timezone (e.g. 'America/New_York').
                           Defaults to Asia/Kolkata (IST) if not provided.
        duration_minutes:  Desired meeting length in minutes (e.g. 15, 30, 60).
                           Pass 0 or omit to use the event type's default duration.

    Returns:
        A formatted list of available slots, or an error message.
    """
    if not SCHEDULING_ENABLED:
        return (
            "Scheduling is not yet configured on this backend. "
            "Please ask the visitor to reach Rahul directly at rjhirur@gmail.com."
        )

    tz = timezone.strip() or CALCOM_TIMEZONE
    try:
        params = {
            "start": f"{start_date}T00:00:00.000Z",
            "end":   f"{end_date}T23:59:59.999Z",
            "eventTypeId": CALCOM_EVENT_TYPE_ID,
            "timeZone": tz,
        }
        if duration_minutes and duration_minutes > 0:
            params["duration"] = duration_minutes

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{CALCOM_BASE_URL}/slots",
                headers=_calcom_headers(),
                params=params,
            )
            resp.raise_for_status()

        raw_slots = resp.json().get("data", {})
        flat_slots = []
        for d in sorted(raw_slots):
            if isinstance(raw_slots[d], list):
                for slot in raw_slots[d]:
                    iso = slot.get("start") or slot.get("time") or ""
                    if iso:
                        flat_slots.append(iso)

        if not flat_slots:
            return f"No open slots found between {start_date} and {end_date}."

        lines = [f"Available slots ({tz}):"]
        for s in flat_slots[:15]:
            lines.append(f"  - {_fmt_slot(s, tz)}")
        if len(flat_slots) > 15:
            lines.append("  - ... (more slots available)")
        return "\n".join(lines)

    except Exception as e:
        return f"Error retrieving slots: {e}"

@tool
def create_booking(
    name: str,
    email: str,
    slot_datetime: str,
    timezone: str = "",
    length_in_minutes: int = 0,
    notes: str = "",
) -> str:
    """
    Confirm and create a meeting booking with Rahul.
    Generates a Google Meet link and sends confirmation emails to both parties.
    Only call this AFTER the visitor has explicitly confirmed a specific time slot
    and provided their name and email.

    Args:
        name:              Full name of the visitor.
        email:             Email address of the visitor.
        slot_datetime:     Exact ISO 8601 datetime of the confirmed slot
                           (e.g. '2026-06-20T10:00:00+05:30').
        timezone:          Visitor's IANA timezone. Defaults to Asia/Kolkata.
        length_in_minutes: Duration of the meeting in minutes (e.g. 15, 30, 60).
                           Pass 0 or omit to use the event type's default duration.
        notes:             Optional agenda or message from the visitor.

    Returns:
        Confirmation summary with Google Meet link, or an error message.
    """
    if not SCHEDULING_ENABLED:
        return (
            "Scheduling is not yet configured on this backend. "
            "Please ask the visitor to reach Rahul directly at rjhirur@gmail.com."
        )

    tz = timezone.strip() or CALCOM_TIMEZONE
    try:
        payload: dict = {
            "eventTypeId": int(CALCOM_EVENT_TYPE_ID),
            "start": slot_datetime,
            "attendee": {"name": name, "email": email, "timeZone": tz},
            "metadata": {},
        }
        if length_in_minutes and length_in_minutes > 0:
            payload["lengthInMinutes"] = length_in_minutes
        if notes:
            payload["responses"] = {"notes": notes}

        def _safe_print(msg: str):
            """Print safely even when stdout is not UTF-8 (e.g. Windows CP1252)."""
            try:
                print(msg)
            except UnicodeEncodeError:
                print(msg.encode('utf-8', errors='replace').decode('ascii', errors='replace'))

        _safe_print(f"[create_booking] POST {CALCOM_BASE_URL}/bookings payload={payload}")

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{CALCOM_BASE_URL}/bookings",
                headers=_calcom_booking_headers(),
                json=payload,
            )
            _safe_print(f"[create_booking] Cal.com responded {resp.status_code}: {resp.text[:400]}")
            resp.raise_for_status()

        booking   = resp.json().get("data", {})
        meet_link = booking.get("meetingUrl") or booking.get("videoCallData", {}).get("url", "")
        start_raw = booking.get("start", slot_datetime)
        formatted = _fmt_slot(start_raw, tz)
        duration_label = f" ({length_in_minutes} min)" if length_in_minutes else ""

        lines = [
            "Meeting confirmed! ✅",
            f"  - **When**: {formatted}{duration_label}",
            f"  - **Attendee**: {name} ({email})",
        ]
        if meet_link:
            lines.append(f"  - **Google Meet Link**: {meet_link}")
        else:
            lines.append("  - **Google Meet Link**: (Will be sent in calendar invite)")
        return "\n".join(lines)

    except Exception as e:
        return f"Error booking slot: {e}"
