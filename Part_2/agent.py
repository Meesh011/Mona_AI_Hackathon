"""
agent.py — Shift Replacement Agent for UKS Homburg

Flow:
  1. HR messages the agent in natural language
     e.g. "Maria Berger ist krank, brauchen Ersatz für Nachtschicht
           Intensivstation Donnerstag, muss Pflegefachkraft sein"
  2. Gemini extracts structured shift details from the message
  3. Database is queried for available qualified staff
  4. Agent contacts staff one by one (SMS + Email) until someone accepts
  5. HR gets a full summary report
"""

import json
import os
import sys
from database_real import find_available_staff, log_outreach
from notifier import send_sms, send_email, notify_hr

# ── Gemini API call ───────────────────────────────────────────────────────────

def parse_shift_request(hr_message: str) -> dict:
    import urllib.request, json

    prompt = f"""You are a hospital HR assistant. Extract shift replacement details from this message.

HR message: "{hr_message}"

Respond ONLY with valid JSON, no explanation, no markdown:
{{
  "ward": "<department name>",
  "shift": "<Früh or Spät or Nacht>",
  "day": "<German weekday>",
  "date": "<date if mentioned>",
  "qualification": "<role required or null>",
  "reason": "<reason>"
}}"""

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    api_key = os.environ.get("GEMINI_API_KEY", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── Main agent logic ──────────────────────────────────────────────────────────

def run_agent(hr_message: str, simulate_acceptance_after: int = 2):
    """
    Main entry point.

    Args:
        hr_message: Free-text message from HR
        simulate_acceptance_after: For demo — simulates the Nth contacted person
                                   saying yes (set to 0 to simulate nobody accepts)
    """
    print("\n" + "=" * 60)
    print("🏥  UKS SHIFT REPLACEMENT AGENT")
    print("=" * 60)
    print(f"\n📩 HR message received:\n   \"{hr_message}\"\n")

    # ── Step 1: Parse the request ─────────────────────────────────────────────
    print("🧠 Analysing request with Gemini AI...")
    try:
        shift_request = parse_shift_request(hr_message)
        print(f"   Parsed: {json.dumps(shift_request, ensure_ascii=False)}")
    except Exception as e:
        print(f"   ⚠️  Could not parse with AI ({e}), using fallback demo values")
        shift_request = {
            "ward": "Intensivstation",
            "shift": "Nacht",
            "day": "Donnerstag",
            "date": "Donnerstag, 26.06.2026",
            "qualification": "Pflegefachkraft",
            "reason": "Krankheit"
        }

    ward         = shift_request.get("ward", "")
    shift        = shift_request.get("shift", "")
    day          = shift_request.get("day", "")
    qualification = shift_request.get("qualification")

    # ── Step 2: Find available staff ─────────────────────────────────────────
    print(f"\n🔍 Searching for available {qualification or 'any'} staff...")
    print(f"   Station: {ward} | Schicht: {shift} | Tag: {day}")

    candidates = find_available_staff(ward, shift, day, qualification)

    if not candidates:
        # Broaden search — remove qualification filter
        print("   No exact match — broadening search (removing qualification filter)...")
        candidates = find_available_staff(ward, shift, day, certification=None)

    print(f"   Found {len(candidates)} candidate(s)\n")

    if not candidates:
        print("❌ No available staff found at all. Escalating to HR head.")
        notify_hr(shift_request, [], filled=False)
        log_outreach(shift_request, [], filled_by=None)
        return

    # ── Step 3: Contact staff one by one ─────────────────────────────────────
    print(f"📞 Contacting staff (simulating acceptance after {simulate_acceptance_after} contact(s)):\n")

    contacted = []
    filled_by = None

    for i, member in enumerate(candidates[:10]):   # cap at 10 contacts
        contacted.append(member)
        send_sms(member, shift_request)
        send_email(member, shift_request)

        # Simulate response — in production this waits for a real reply
        accepted = (simulate_acceptance_after > 0 and
                    len(contacted) >= simulate_acceptance_after)

        if accepted:
            filled_by = member
            print(f"\n  ✅ {member['name']} hat ZUGESAGT!")
            break
        else:
            print(f"  ⏳ Warte auf Antwort von {member['name']}... (keine Rückmeldung)\n")

    # ── Step 4: Report to HR ─────────────────────────────────────────────────
    print("\n" + "-" * 60)
    notify_hr(shift_request, contacted, filled=filled_by is not None, filled_by=filled_by)

    entry = log_outreach(shift_request, contacted, filled_by=filled_by)

    print("\n📁 Log saved to output/shift_log.json")
    print("=" * 60)

    return entry


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        # Default demo message
        message = (
            "Maria Berger ist heute Nacht krank gemeldet. "
            "Wir brauchen dringend Ersatz für die Nachtschicht auf der Intensivstation "
            "am Donnerstag. Bitte nur Pflegefachkraft schicken."
        )

    run_agent(message, simulate_acceptance_after=2)
