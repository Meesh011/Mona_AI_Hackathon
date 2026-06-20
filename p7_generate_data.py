from pathlib import Path
"""
generate_data.py
Generates synthetic but realistic transaction data for Allgäuer Latschenkiefer.
Run once: python generate_data.py  → creates transactions.csv + customers.csv
"""
import random, csv, math
from datetime import date, timedelta

random.seed(42)

SKUS = [
    ("ALK-FB-01","Fuß Butter","Feet",7.71,"Autumn-Winter","45+ dry-skin, women"),
    ("ALK-FB-02","Sole Fußbad","Feet",6.49,"Winter","Wellness, 50+"),
    ("ALK-FB-03","Hornhaut Reduziercreme","Feet",6.99,"Spring","Women 30-60"),
    ("ALK-FB-04","Hornhaut Entferner Maske","Feet",8.49,"Spring-Summer","Women 25-45"),
    ("ALK-FB-05","10% Urea Fußcreme","Feet",7.25,"All year","Diabetic / very dry skin"),
    ("ALK-FB-06","Fußpflege Deospray","Feet",6.10,"Summer","Active / men 20-45"),
    ("ALK-LG-01","5 in 1 Beinlotion","Legs",9.95,"Summer","Women 35-65"),
    ("ALK-LG-02","Bein Frische Gel","Legs",8.20,"Summer","Travel / standing jobs"),
    ("ALK-LG-03","Besenreiser Pflegebalsam","Legs",11.49,"Spring-Summer","Women 40-65"),
    ("ALK-MG-01","Mobil Gel","Muscles/Joints",5.83,"Autumn-Winter","Active 30+, 55+ joints"),
    ("ALK-MG-02","Mobil Einreibung Extra Stark","Muscles/Joints",8.90,"Winter / sport","Sport, 25-55"),
    ("ALK-MG-03","Mobil Eisspray akut","Muscles/Joints",9.40,"Sport season","Athletes, teams"),
    ("ALK-MG-04","Franzbranntwein","Muscles/Joints",6.75,"All year","Traditional 55+"),
    ("ALK-MG-05","Wärmendes Intensiv Gel","Muscles/Joints",8.30,"Winter","45+ tension/back"),
    ("ALK-CB-01","Ur Bonbons","Cough drops",2.49,"Cold season","Mass-market"),
]

REGIONS = ["Bayern","Baden-Württemberg","NRW","Hessen","Berlin","Hamburg","Sachsen","Niedersachsen"]
CHANNELS = ["pharmacy","online","dm","rossmann"]

SEGMENTS = {
    "wellness_50plus":   {"age_range":(50,72),"gender":"F","channel_weights":[0.5,0.3,0.1,0.1]},
    "active_women_35":   {"age_range":(30,50),"gender":"F","channel_weights":[0.3,0.4,0.2,0.1]},
    "athletes_25":       {"age_range":(20,45),"gender":"M","channel_weights":[0.2,0.5,0.2,0.1]},
    "traditional_55":    {"age_range":(55,75),"gender":"M","channel_weights":[0.6,0.1,0.15,0.15]},
    "diabetic_care":     {"age_range":(45,70),"gender":"F","channel_weights":[0.7,0.2,0.05,0.05]},
    "young_active_women":{"age_range":(22,40),"gender":"F","channel_weights":[0.2,0.5,0.2,0.1]},
}

SEG_SKU_AFFINITY = {
    "wellness_50plus":    ["ALK-FB-02","ALK-FB-01","ALK-LG-01","ALK-MG-04"],
    "active_women_35":    ["ALK-LG-01","ALK-LG-02","ALK-FB-03","ALK-FB-04","ALK-LG-03"],
    "athletes_25":        ["ALK-MG-03","ALK-MG-02","ALK-MG-01","ALK-FB-06"],
    "traditional_55":     ["ALK-MG-04","ALK-MG-01","ALK-MG-05","ALK-CB-01"],
    "diabetic_care":      ["ALK-FB-05","ALK-FB-01","ALK-FB-03"],
    "young_active_women": ["ALK-FB-04","ALK-FB-03","ALK-LG-02","ALK-FB-06"],
}

def season_weight(sku_row, d: date) -> float:
    m = d.month
    s = sku_row[4]
    if "All year" in s: return 1.0
    if "Winter" in s and "Autumn" in s: return 1.6 if m in (9,10,11,12,1,2) else 0.5
    if "Winter" in s: return 1.8 if m in (11,12,1,2) else 0.4
    if "Summer" in s and "Spring" in s: return 1.7 if m in (3,4,5,6,7,8) else 0.4
    if "Spring" in s: return 1.9 if m in (3,4,5) else 0.4
    if "Summer" in s: return 1.8 if m in (6,7,8) else 0.4
    if "Cold season" in s: return 1.9 if m in (10,11,12,1,2,3) else 0.3
    if "Sport season" in s: return 1.7 if m in (3,4,5,6,7,8,9) else 0.5
    return 1.0

N_CUSTOMERS = 800
start = date(2023, 1, 1)
end   = date(2024, 12, 31)
days  = (end - start).days

customers = []
for cid in range(1, N_CUSTOMERS+1):
    seg = random.choice(list(SEGMENTS.keys()))
    cfg = SEGMENTS[seg]
    age = random.randint(*cfg["age_range"])
    gender = cfg["gender"] if random.random() < 0.85 else ("M" if cfg["gender"]=="F" else "F")
    region = random.choice(REGIONS)
    customers.append({
        "customer_id": f"C{cid:05d}",
        "segment": seg,
        "age": age,
        "gender": gender,
        "region": region,
    })

# assign to treatment / control (50/50) for lift measurement
for c in customers:
    c["campaign_group"] = "treatment" if random.random() < 0.5 else "control"

sku_map = {s[0]: s for s in SKUS}

# campaign window: simulate a campaign for ALK-LG-01 in July 2024
CAMPAIGN_SKU = "ALK-LG-01"
CAMPAIGN_START = date(2024, 7, 1)
CAMPAIGN_END   = date(2024, 7, 31)

transactions = []
tid = 1
for c in customers:
    seg   = c["segment"]
    affin = SEG_SKU_AFFINITY[seg]
    n_tx  = random.randint(2, 12)
    for _ in range(n_tx):
        d = start + timedelta(days=random.randint(0, days))
        # pick SKU — 70% from affinity list, 30% random
        if random.random() < 0.70 and affin:
            sku_id = random.choice(affin)
        else:
            sku_id = random.choice(SKUS)[0]
        sku_row = sku_map[sku_id]
        sw = season_weight(sku_row, d)
        if random.random() > sw * 0.7:
            continue
        # campaign lift: treatment group buys campaign SKU 2.3x more in July 2024
        if (sku_id == CAMPAIGN_SKU and
            CAMPAIGN_START <= d <= CAMPAIGN_END and
            c["campaign_group"] == "treatment"):
            if random.random() > 0.35:
                pass  # keep it (higher keep rate = lift)
            else:
                continue
        cfg     = SEGMENTS[seg]
        ch_w    = cfg["channel_weights"]
        channel = random.choices(CHANNELS, weights=ch_w)[0]
        qty     = random.choices([1,2,3],[0.7,0.2,0.1])[0]
        price   = round(sku_row[3] * random.uniform(0.95, 1.05), 2)
        transactions.append({
            "transaction_id": f"T{tid:07d}",
            "customer_id":    c["customer_id"],
            "sku":            sku_id,
            "product_name":   sku_row[1],
            "line":           sku_row[2] if len(sku_row)>3 else "",
            "date":           d.isoformat(),
            "qty":            qty,
            "unit_price":     price,
            "revenue":        round(price * qty, 2),
            "channel":        channel,
            "region":         c["region"],
            "segment":        seg,
            "campaign_group": c["campaign_group"],
        })
        tid += 1

transactions.sort(key=lambda x: x["date"])

with open(str(Path(__file__).parent / "transactions.csv"),"w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=transactions[0].keys())
    w.writeheader(); w.writerows(transactions)

with open(str(Path(__file__).parent / "customers.csv"),"w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=customers[0].keys())
    w.writeheader(); w.writerows(customers)

print(f"Generated {len(transactions)} transactions for {len(customers)} customers")
print(f"Campaign SKU: {CAMPAIGN_SKU}  |  Window: {CAMPAIGN_START} – {CAMPAIGN_END}")
