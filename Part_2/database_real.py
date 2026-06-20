"""
database_real.py — uses the actual UKS hospital_schedule_part_2.xlsx
"""
import json
import os
import pandas as pd
from datetime import datetime

EXCEL_FILE = "data/hospital_schedule_part_2.xlsx"
LOG_FILE   = "output/shift_log.json"


def load_roster_and_schedule():
    roster   = pd.read_excel(EXCEL_FILE, sheet_name="Roster")
    schedule = pd.read_excel(EXCEL_FILE, sheet_name="Weekly_Schedule")
    df = pd.merge(
        roster,
        schedule[["Employee ID","Sat 06/20","Sun 06/21","Mon 06/22",
                  "Tue 06/23","Wed 06/24","Thu 06/25","Fri 06/26",
                  "Scheduled Hrs (next 7d)"]],
        on="Employee ID"
    )
    return df


# Map German weekday names → Excel column names in this schedule
DAY_TO_COL = {
    "Samstag"   : "Sat 06/20",
    "Sonntag"   : "Sun 06/21",
    "Montag"    : "Mon 06/22",
    "Dienstag"  : "Tue 06/23",
    "Mittwoch"  : "Wed 06/24",
    "Donnerstag": "Thu 06/25",
    "Freitag"   : "Fri 06/26",
}

SHIFT_TO_CODE = {
    "Früh"  : "D",
    "Tag"   : "D",
    "Day"   : "D",
    "Spät"  : "D",
    "Nacht" : "N",
    "Night" : "N",
}


def find_available_staff(department: str, shift: str, day: str,
                         certification: str = None,
                         sick_employee_id: str = None,
                         decision_time: datetime = None) -> list:
    """
    Find all staff eligible to cover a shift using the real Excel data.
    Applies all 6 scenario criteria + tie-breaker ranking.
    """
    df = load_roster_and_schedule()

    if decision_time is None:
        decision_time = datetime.now()

    col = DAY_TO_COL.get(day, DAY_TO_COL.get(list(DAY_TO_COL.keys())[0]))
    shift_code = SHIFT_TO_CODE.get(shift, "N")

    # ── Filter criteria ───────────────────────────────────────────────────────
    c1_role   = df["Role"].isin(["Registered Nurse", "Charge Nurse"])
    c2_certs  = df["Certifications"].str.contains("BLS", na=False)
    if certification:
        c2_certs &= df["Certifications"].str.contains(certification, na=False)
    c3_active = df["Status"] == "Active"
    c4_off    = df[col] == "O"
    c6_hours  = (df["Scheduled Hrs (next 7d)"] + 12) <= df["Max Hrs/Week"]

    # Rest check: last clock-out must be before 08:30 on the shift day
    rest_cutoff = decision_time.replace(hour=8, minute=30, second=0, microsecond=0)

    def is_rested(co):
        if co == "— on shift —":
            return False
        if isinstance(co, datetime):
            return co <= rest_cutoff
        return False

    c5_rested = df["Last Clock Out"].apply(is_rested)

    c_not_sick = df["Employee ID"] != (sick_employee_id or "")

    mask = c1_role & c2_certs & c3_active & c4_off & c5_rested & c6_hours & c_not_sick
    candidates = df[mask].copy()
    candidates["hours_headroom"] = (
        candidates["Max Hrs/Week"] - candidates["Scheduled Hrs (next 7d)"] - 12
    )

    # ── Ranking ───────────────────────────────────────────────────────────────
    def rank(row):
        ot    = 0 if row["Overtime OK"] == "Yes" else 1
        room  = -row["hours_headroom"]
        ctype = {"Per-diem": 0, "Part-time": 1, "Full-time": 2}.get(row["Contract"], 3)
        # ICU staff get preference for ICU cover
        dept_match = 0 if row["Department"] == "ICU" else 1
        return (ot, dept_match, ctype, room)

    candidates["_rank"] = candidates.apply(rank, axis=1)
    candidates = candidates.sort_values("_rank")

    # Convert to list of dicts for compatibility with existing agent/notifier
    result = []
    for _, row in candidates.iterrows():
        result.append({
            "id"            : row["Employee ID"],
            "name"          : f"{row['First Name']} {row['Last Name']}",
            "phone"         : row["Phone"],
            "email"         : f"{row['First Name'].lower()}.{row['Last Name'].lower()}@uks.eu",
            "role"          : row["Role"],
            "department"    : row["Department"],
            "qualifications": row["Certifications"].split(", "),
            "contract"      : row["Contract"],
            "overtime_ok"   : row["Overtime OK"],
            "hours_headroom": int(row["hours_headroom"]),
            "shift_pref"    : row["Shift Preference"],
            "persona"       : row["Persona / Notes"],
            "available_days": [],   # not used when Excel schedule is the source
            "active"        : True,
        })

    return result


def log_outreach(shift_request: dict, contacted: list, filled_by: dict = None):
    os.makedirs("output", exist_ok=True)
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            try:
                log = json.load(f)
            except Exception:
                log = []

    entry = {
        "timestamp"       : datetime.now().isoformat(),
        "shift_request"   : shift_request,
        "staff_contacted" : [s["name"] for s in contacted],
        "filled_by"       : filled_by["name"] if filled_by else None,
        "status"          : "Filled" if filled_by else "Unfilled — escalate to HR"
    }
    log.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    return entry
