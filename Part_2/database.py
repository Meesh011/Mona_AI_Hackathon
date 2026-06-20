import json
import os
from datetime import datetime

STAFF_FILE = "staff.json"
LOG_FILE = "output/shift_log.json"


def load_staff():
    with open(STAFF_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def find_available_staff(ward: str, shift: str, day: str, qualification: str = None) -> list:
    """
    Find all staff who:
      - are active
      - have the required qualification
      - are available on the given day and shift
      - can work in the given ward
    Returns list sorted by qualification match quality (most qualified first).
    """
    staff = load_staff()
    matches = []

    for member in staff:
        if not member["active"]:
            continue
        if day not in member["available_days"]:
            continue
        if shift not in member["available_shifts"]:
            continue
        if ward not in member["wards"]:
            continue
        if qualification and qualification not in member["qualifications"]:
            continue
        matches.append(member)

    # Sort: Pflegefachkraft before Pflegehelfer, then by name
    def sort_key(m):
        rank = 0 if "Pflegefachkraft" in m["qualifications"] else 1
        return (rank, m["name"])

    return sorted(matches, key=sort_key)


def log_outreach(shift_request: dict, contacted: list, filled_by: dict = None):
    """Append a shift-filling attempt to the log file."""
    os.makedirs("output", exist_ok=True)

    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            try:
                log = json.load(f)
            except json.JSONDecodeError:
                log = []

    entry = {
        "timestamp": datetime.now().isoformat(),
        "shift_request": shift_request,
        "staff_contacted": [s["name"] for s in contacted],
        "filled_by": filled_by["name"] if filled_by else None,
        "status": "Filled" if filled_by else "Unfilled — escalate to HR"
    }
    log.append(entry)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    return entry
