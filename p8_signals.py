"""
signals.py
External signal fetchers + synthetic fallbacks for the dynamic pricing engine.
Signals:
  - Weather (OpenMeteo, free, no key)
  - Calendar events (German holidays + seasonal/religious events)
  - Football fixtures (synthetic, real integration via football-data.org)
  - Supply chain stress (synthetic per SKU/ingredient)
"""
from __future__ import annotations
import json
from datetime import date, timedelta
from typing import Optional
import urllib.request
import urllib.error

# ── Weather ──────────────────────────────────────────────────────────────────
CITY_COORDS = {
    "Hamburg":           (53.55, 10.00),
    "Berlin":            (52.52, 13.41),
    "München":           (48.14, 11.58),
    "Köln":              (50.94,  6.96),
    "Frankfurt":         (50.11,  8.68),
    "Stuttgart":         (48.78,  9.18),
    "Homburg (Saarland)":(49.32,  7.34),
    "Deutschland (avg)": (51.00, 10.00),
}

def fetch_weather(city: str = "Deutschland (avg)") -> dict:
    lat, lon = CITY_COORDS.get(city, (51.0, 10.0))
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        f"&forecast_days=7&timezone=Europe%2FBerlin"
    )
    try:
        with urllib.request.urlopen(url, timeout=6) as r:
            data = json.loads(r.read())
        daily = data["daily"]
        today = {
            "city":       city,
            "date":       daily["time"][0],
            "temp_max":   daily["temperature_2m_max"][0],
            "temp_min":   daily["temperature_2m_min"][0],
            "precip_mm":  daily["precipitation_sum"][0],
            "wmo_code":   daily["weathercode"][0],
            "forecast_7d_avg_max": round(sum(daily["temperature_2m_max"]) / 7, 1),
        }
        return today
    except Exception as e:
        # fallback based on current month
        m = date.today().month
        temp = {1:-2,2:0,3:6,4:12,5:17,6:21,7:24,8:23,9:18,10:12,11:5,12:0}.get(m, 10)
        return {"city": city, "date": date.today().isoformat(),
                "temp_max": temp+3, "temp_min": temp-3,
                "precip_mm": 2.0, "wmo_code": 3,
                "forecast_7d_avg_max": temp+2,
                "source": "synthetic_fallback", "error": str(e)}

# ── Calendar events ───────────────────────────────────────────────────────────
def upcoming_events(target_date: Optional[date] = None, window_days: int = 21) -> list[dict]:
    d = target_date or date.today()
    end = d + timedelta(days=window_days)
    year = d.year

    # Fixed German public holidays + commercial events
    fixed = [
        # (month, day, name, category, pricing_signal)
        (1,  1,  "Neujahr",                  "public_holiday", "neutral"),
        (2, 14,  "Valentinstag",              "commercial",     "gifting_spike"),
        (3,  8,  "Weltfrauentag",             "awareness",      "women_products"),
        (4,  1,  "April – Oster approx",      "seasonal",       "spring_prep"),
        (5,  1,  "Tag der Arbeit",            "public_holiday", "neutral"),
        (5, 12,  "Muttertag approx",          "commercial",     "gifting_spike"),
        (6,  1,  "Sommerbeginn",              "seasonal",       "cooling_demand"),
        (6, 16,  "Vatertag / Herrentag",      "commercial",     "mens_products"),
        (7,  1,  "Urlaubssaison Peak",        "seasonal",       "travel_care"),
        (9,  1,  "Herbstanfang",              "seasonal",       "warming_demand"),
        (10, 3,  "Tag der Deutschen Einheit", "public_holiday", "neutral"),
        (11, 1,  "Allerheiligen",             "public_holiday", "neutral"),
        (11,11,  "Martinstag / Karnevalsstart","cultural",      "neutral"),
        (11,27,  "Advent 1 approx",           "seasonal",       "gifting_spike"),
        (12, 6,  "Nikolaustag",               "commercial",     "gifting_spike"),
        (12,24,  "Heiligabend",               "commercial",     "gifting_spike"),
        (12,26,  "2. Weihnachtstag",          "public_holiday", "gifting_spike"),
        (12,31,  "Silvester",                 "commercial",     "neutral"),
        # Ramadan 2025 approx (moves yearly)
        (3,  1,  "Ramadan Beginn approx",     "religious",      "wellness_demand"),
    ]

    # German Bundesliga fixtures (approximate high-traffic windows)
    bundesliga = [
        (8, 23, "Bundesliga Saisonstart", "football", "sport_recovery"),
        (9, 14, "Spieltag Mitte Sept",   "football", "sport_recovery"),
        (10,19, "Spieltag Mitte Okt",    "football", "sport_recovery"),
        (11, 9, "Spieltag Nov",          "football", "sport_recovery"),
        (3, 15, "Rückrunde Peak",        "football", "sport_recovery"),
        (5,  3, "Saisonfinale",          "football", "sport_recovery"),
    ]

    result = []
    for month, day, name, cat, signal in fixed + bundesliga:
        try:
            ev_date = date(year, month, day)
        except ValueError:
            continue
        days_away = (ev_date - d).days
        if 0 <= days_away <= window_days:
            result.append({
                "name": name, "date": ev_date.isoformat(),
                "category": cat, "pricing_signal": signal,
                "days_away": days_away,
            })

    return sorted(result, key=lambda x: x["days_away"])

# ── Supply chain stress ───────────────────────────────────────────────────────
# Synthetic stress scores 0-100 per key ingredient/SKU family
SUPPLY_STRESS = {
    "Latschenkiefernöl":   15,   # own plantations, low risk
    "Urea":                28,   # commodity, moderate
    "Arnika-Extrakt":      35,   # herbal, some seasonality
    "Propolis":            20,
    "Bienenwachs":         22,
    "Menthol":             42,   # global supply tighter
    "Kampfer":             38,
    "Franzbranntwein-base":18,
}

SKU_INGREDIENT_MAP = {
    "ALK-FB-01": ["Latschenkiefernöl","Bienenwachs"],
    "ALK-FB-02": ["Latschenkiefernöl"],
    "ALK-FB-03": ["Urea","Latschenkiefernöl"],
    "ALK-FB-04": ["Urea","Latschenkiefernöl"],
    "ALK-FB-05": ["Urea"],
    "ALK-FB-06": ["Menthol"],
    "ALK-LG-01": ["Latschenkiefernöl","Menthol"],
    "ALK-LG-02": ["Menthol"],
    "ALK-LG-03": ["Arnika-Extrakt"],
    "ALK-MG-01": ["Latschenkiefernöl","Kampfer"],
    "ALK-MG-02": ["Kampfer","Latschenkiefernöl"],
    "ALK-MG-03": ["Menthol"],
    "ALK-MG-04": ["Franzbranntwein-base"],
    "ALK-MG-05": ["Kampfer","Latschenkiefernöl"],
    "ALK-CB-01": ["Latschenkiefernöl","Menthol"],
}

def supply_stress(sku: str) -> dict:
    ingredients = SKU_INGREDIENT_MAP.get(sku, [])
    scores = [SUPPLY_STRESS.get(ing, 20) for ing in ingredients]
    avg = sum(scores) / len(scores) if scores else 20
    level = "critical" if avg >= 60 else "elevated" if avg >= 35 else "normal"
    return {
        "sku": sku, "ingredients": ingredients,
        "stress_scores": dict(zip(ingredients, scores)),
        "avg_stress": round(avg, 1), "level": level,
    }
