import json, random
from datetime import datetime

random.seed(42)

FIRST_NAMES = [
    "Anna","Felix","Lena","Markus","Sarah","Jonas","Marie","Tobias","Julia","Lukas",
    "Laura","Simon","Katharina","David","Lisa","Stefan","Nina","Michael","Petra","Thomas",
    "Sandra","Andreas","Monika","Christian","Eva","Sebastian","Claudia","Florian","Angela","Patrick",
    "Sabrina","Daniel","Melanie","Dominik","Franziska","Jan","Nadine","Maximilian","Tanja","Oliver",
    "Anja","Philipp","Stefanie","Christoph","Birgit","Alexander","Kerstin","Benjamin","Renate","Tim"
]

LAST_NAMES = [
    "Müller","Schmidt","Schneider","Fischer","Weber","Meyer","Wagner","Becker","Schulz","Hoffmann",
    "Schäfer","Koch","Bauer","Richter","Klein","Wolf","Schröder","Neumann","Schwarz","Zimmermann",
    "Braun","Krüger","Hofmann","Hartmann","Lange","Schmitt","Werner","Schmitz","Krause","Meier",
    "Lehmann","Schmid","Schulze","Maier","Köhler","Herrmann","König","Walter","Mayer","Huber",
    "Kaiser","Fuchs","Peters","Lang","Scholz","Möller","Weiß","Jung","Hahn","Schubert"
]

QUALIFICATIONS = [
    ["Pflegefachkraft"], ["Pflegefachkraft"], ["Pflegefachkraft"],
    ["Pflegehelfer"], ["Pflegehelfer"], ["Pflegehelfer"],
    ["Pflegefachkraft", "Intensivpflege"],
    ["Pflegefachkraft", "Intensivpflege"],
    ["Pflegefachkraft", "OP-Pflege"],
    ["Pflegehelfer", "Stationshilfe"],
]

WARDS = ["Innere Medizin", "Chirurgie", "Intensivstation", "Notaufnahme", "Orthopädie", "Neurologie", "OP"]

DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

staff = []
for i in range(50):
    quals = random.choice(QUALIFICATIONS)
    has_license = random.random() > 0.35
    avail_days = sorted(random.sample(DAYS, random.randint(3, 6)))
    shifts = random.sample(["Früh", "Spät", "Nacht"], random.randint(1, 3))
    wards = random.sample(WARDS, random.randint(1, 3))
    phone = f"+49 {random.randint(151,179)} {random.randint(10000000,99999999)}"

    staff.append({
        "id": f"S{i+1:03d}",
        "name": f"{FIRST_NAMES[i]} {LAST_NAMES[i]}",
        "phone": phone,
        "email": f"{FIRST_NAMES[i].lower()}.{LAST_NAMES[i].lower()}@uks-minijob.de",
        "qualifications": quals,
        "driving_license": has_license,
        "available_days": avail_days,
        "available_shifts": shifts,
        "wards": wards,
        "max_hours_per_week": random.choice([10, 15, 20]),
        "active": True
    })

with open("data/staff.json", "w", encoding="utf-8") as f:
    json.dump(staff, f, ensure_ascii=False, indent=2)

print(f"Generated {len(staff)} staff members")
