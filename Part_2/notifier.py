"""
notifier.py — Simulated outreach module.

In production this would call:
  - Twilio API  →  SMS to staff mobile
  - SendGrid    →  Email backup
  - Teams Webhook → HR notification

For the hackathon demo we print to console and write to output/messages.txt
"""

import os
from datetime import datetime

MESSAGE_LOG = "output/messages.txt"

os.makedirs("output", exist_ok=True)


def _log_message(channel: str, recipient: str, message: str):
    with open(MESSAGE_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().strftime('%H:%M:%S')}] {channel} → {recipient}\n")
        f.write(message)
        f.write("\n" + "-" * 60)


def send_sms(staff_member: dict, shift_request: dict) -> str:
    """Send SMS to a staff member asking if they can cover a shift."""
    name = staff_member["name"].split()[0]   # first name only
    ward = shift_request["ward"]
    shift = shift_request["shift"]
    day = shift_request["day"]
    date = shift_request.get("date", day)

    message = (
        f"Hallo {name}, hier ist das UKS Homburg.\n"
        f"Können Sie kurzfristig einspringen?\n"
        f"Schicht: {shift} | Station: {ward} | Datum: {date}\n"
        f"Bitte antworten Sie mit JA oder NEIN innerhalb von 30 Min.\n"
        f"Vielen Dank! — UKS Personalplanung"
    )

    print(f"  📱 SMS → {staff_member['name']} ({staff_member['phone']})")
    print(f"     \"{message[:80]}...\"")
    _log_message("SMS", f"{staff_member['name']} {staff_member['phone']}", message)

    return message


def send_email(staff_member: dict, shift_request: dict) -> str:
    """Send email as a backup channel."""
    name = staff_member["name"].split()[0]
    ward = shift_request["ward"]
    shift = shift_request["shift"]
    day = shift_request["day"]
    date = shift_request.get("date", day)

    subject = f"[UKS] Kurzfristig: {shift}schicht {ward} am {date}"
    body = (
        f"Sehr geehrte/r {staff_member['name']},\n\n"
        f"wir benötigen dringend Unterstützung für folgende Schicht:\n\n"
        f"  Station : {ward}\n"
        f"  Schicht : {shift}\n"
        f"  Datum   : {date}\n\n"
        f"Bitte melden Sie sich so schnell wie möglich telefonisch unter\n"
        f"+49 6841 16-0 oder antworten Sie auf diese E-Mail.\n\n"
        f"Mit freundlichen Grüßen\n"
        f"Personalplanung — Universitätsklinikum des Saarlandes"
    )

    print(f"  📧 Email → {staff_member['email']}")
    _log_message("EMAIL", staff_member["email"], f"Subject: {subject}\n\n{body}")

    return body


def notify_hr(shift_request: dict, contacted: list, filled: bool, filled_by: dict = None):
    """Send a summary notification to HR regardless of outcome."""
    ward = shift_request["ward"]
    shift = shift_request["shift"]
    day = shift_request["day"]

    if filled and filled_by:
        status = f"✅ Schicht besetzt durch {filled_by['name']}"
    else:
        status = "❌ NICHT BESETZT — manuelle Eskalation erforderlich"

    summary = (
        f"[UKS Schicht-Agent — Bericht]\n"
        f"Anfrage : {shift}schicht | {ward} | {day}\n"
        f"Kontaktiert : {len(contacted)} Mitarbeiter\n"
        f"Ergebnis : {status}\n"
    )
    if contacted:
        summary += "Kontaktierte Personen:\n"
        for s in contacted:
            summary += f"  - {s['name']} ({s['phone']})\n"

    print(f"\n  🏥 HR-Benachrichtigung:")
    print("  " + summary.replace("\n", "\n  "))
    _log_message("HR-NOTIFY", "hr.personalplanung@uks.eu", summary)
