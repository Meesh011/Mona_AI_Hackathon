"""
pricing_engine.py
Rule-based pricing engine with guardrails.
Applies signal weights to base prices within a permitted ±12% band.
Every price change is fully logged with rationale (auditability).
"""
from __future__ import annotations
import json
from datetime import date, datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── Product catalogue ─────────────────────────────────────────────────────────
CATALOGUE = {
    "ALK-FB-01": {"name":"Fuß Butter",               "line":"Feet",           "base_price":7.71},
    "ALK-FB-02": {"name":"Sole Fußbad",              "line":"Feet",           "base_price":6.49},
    "ALK-FB-03": {"name":"Hornhaut Reduziercreme",   "line":"Feet",           "base_price":6.99},
    "ALK-FB-04": {"name":"Hornhaut Entferner Maske", "line":"Feet",           "base_price":8.49},
    "ALK-FB-05": {"name":"10% Urea Fußcreme",        "line":"Feet",           "base_price":7.25},
    "ALK-FB-06": {"name":"Fußpflege Deospray",       "line":"Feet",           "base_price":6.10},
    "ALK-LG-01": {"name":"5 in 1 Beinlotion",        "line":"Legs",           "base_price":9.95},
    "ALK-LG-02": {"name":"Bein Frische Gel",         "line":"Legs",           "base_price":8.20},
    "ALK-LG-03": {"name":"Besenreiser Pflegebalsam", "line":"Legs",           "base_price":11.49},
    "ALK-MG-01": {"name":"Mobil Gel",                "line":"Muscles/Joints", "base_price":5.83},
    "ALK-MG-02": {"name":"Mobil Einreibung Extra Stark","line":"Muscles/Joints","base_price":8.90},
    "ALK-MG-03": {"name":"Mobil Eisspray akut",      "line":"Muscles/Joints", "base_price":9.40},
    "ALK-MG-04": {"name":"Franzbranntwein",          "line":"Muscles/Joints", "base_price":6.75},
    "ALK-MG-05": {"name":"Wärmendes Intensiv Gel",   "line":"Muscles/Joints", "base_price":8.30},
    "ALK-CB-01": {"name":"Ur Bonbons",               "line":"Cough drops",    "base_price":2.49},
}

# ── Guardrails ────────────────────────────────────────────────────────────────
MAX_INCREASE_PCT = 12.0   # hard ceiling from data pack
MAX_DECREASE_PCT = 12.0   # symmetric floor
# Health/OTC products: never raise more than 8% in a single adjustment (fairness)
FAIRNESS_SINGLE_STEP_CAP = 8.0
# Diabetic/medical-need SKUs get a tighter ceiling (price sensitivity)
SENSITIVE_SKUS = {"ALK-FB-05"}   # urea for diabetic foot
SENSITIVE_CEILING = 5.0

MIN_MARGIN_EUR = 1.20  # never sell below cost proxy

# ── Signal → multiplier rules ─────────────────────────────────────────────────
def weather_multiplier(weather: dict, sku: str) -> tuple[float, str]:
    temp = weather.get("forecast_7d_avg_max", 15)
    line = CATALOGUE.get(sku, {}).get("line", "")
    reason = ""
    mult = 1.0

    if line == "Legs":
        if temp >= 24:
            mult, reason = 1.06, f"Heat wave ({temp}°C) → high demand for cooling leg products"
        elif temp >= 20:
            mult, reason = 1.03, f"Warm weather ({temp}°C) → elevated leg-care demand"
        elif temp <= 8:
            mult, reason = 0.97, f"Cold ({temp}°C) → reduced summer leg-product demand"

    elif line in ("Muscles/Joints",):
        if temp <= 3:
            mult, reason = 1.05, f"Cold snap ({temp}°C) → high demand for warming muscle products"
        elif temp >= 22:
            if sku in ("ALK-MG-03",):  # Eisspray
                mult, reason = 1.06, f"Heat + sport season ({temp}°C) → acute cold spray demand"
            else:
                mult, reason = 0.98, f"Summer ({temp}°C) → lower warming-product demand"

    elif line == "Feet":
        if temp >= 22 and sku in ("ALK-FB-06",):  # Deospray
            mult, reason = 1.05, f"Summer heat ({temp}°C) → foot deodorant demand"
        elif temp <= 5 and sku in ("ALK-FB-01","ALK-FB-02"):  # Fuß Butter, Fußbad
            mult, reason = 1.04, f"Cold dry air ({temp}°C) → rich foot care demand"

    elif line == "Cough drops":
        if temp <= 6:
            mult, reason = 1.07, f"Cold weather ({temp}°C) → cough drop season"

    return mult, reason

def event_multiplier(events: list[dict], sku: str) -> tuple[float, str]:
    line = CATALOGUE.get(sku, {}).get("line", "")
    mult, reason = 1.0, ""

    for ev in events:
        days = ev.get("days_away", 999)
        sig  = ev.get("pricing_signal", "neutral")
        name = ev.get("name", "")
        weight = max(0.3, 1.0 - days / 21)  # closer = stronger

        if sig == "gifting_spike" and days <= 14:
            bump = 0.04 * weight
            mult += bump
            reason = f"{name} in {days}d → gifting demand surge"

        elif sig == "sport_recovery" and line == "Muscles/Joints":
            bump = 0.05 * weight
            mult += bump
            reason = f"{name} in {days}d → sport recovery products in demand"

        elif sig == "cooling_demand" and line == "Legs":
            bump = 0.04 * weight
            mult += bump
            reason = f"{name}: summer peak → leg/cooling demand"

        elif sig == "warming_demand" and line in ("Muscles/Joints","Feet"):
            bump = 0.04 * weight
            mult += bump
            reason = f"{name}: autumn/winter transition → warming product demand"

        elif sig == "mens_products" and sku == "ALK-FB-06":
            bump = 0.03 * weight
            mult += bump
            reason = f"{name}: men's gifting period → foot deospray"

        elif sig == "spring_prep" and sku in ("ALK-FB-03","ALK-FB-04"):
            bump = 0.04 * weight
            mult += bump
            reason = f"{name}: sandal season prep → callus products"

    return round(mult, 4), reason

def supply_multiplier(stress: dict) -> tuple[float, str]:
    avg = stress.get("avg_stress", 20)
    level = stress.get("level", "normal")
    if level == "critical":
        return 1.08, f"Critical supply stress ({avg:.0f}/100) on {stress.get('ingredients')} → margin protection"
    elif level == "elevated":
        return 1.04, f"Elevated supply stress ({avg:.0f}/100) → light margin protection"
    return 1.0, ""

# ── Core pricing calculation ───────────────────────────────────────────────────
@dataclass
class PriceDecision:
    sku:             str
    product_name:    str
    base_price:      float
    recommended_price: float
    change_pct:      float
    direction:       str        # "increase" | "decrease" | "hold"
    signals_applied: list[dict] = field(default_factory=list)
    guardrails_fired: list[str] = field(default_factory=list)
    rationale:       str = ""
    timestamp:       str = field(default_factory=lambda: datetime.utcnow().isoformat()+"Z")
    audit_approved:  bool = True

    def to_dict(self): return asdict(self)


def compute_price(
    sku: str,
    weather: dict,
    events: list[dict],
    stress: dict,
    override_pct: Optional[float] = None,
) -> PriceDecision:
    cat = CATALOGUE.get(sku, {})
    base = cat.get("base_price", 5.0)
    name = cat.get("name", sku)

    signals = []
    guardrails = []

    # ── Collect multipliers ───────────────────────────────────────────────
    w_mult, w_reason = weather_multiplier(weather, sku)
    e_mult, e_reason = event_multiplier(events, sku)
    s_mult, s_reason = supply_multiplier(stress)

    if w_reason: signals.append({"source":"weather",  "multiplier":w_mult, "reason":w_reason})
    if e_reason: signals.append({"source":"events",   "multiplier":e_mult, "reason":e_reason})
    if s_reason: signals.append({"source":"supply",   "multiplier":s_mult, "reason":s_reason})

    # Combine multiplicatively
    combined = w_mult * e_mult * s_mult
    raw_price = round(base * combined, 2)
    raw_change_pct = (combined - 1.0) * 100

    # ── Guardrails ────────────────────────────────────────────────────────
    ceiling_pct = SENSITIVE_CEILING if sku in SENSITIVE_SKUS else FAIRNESS_SINGLE_STEP_CAP
    floor_pct   = -MAX_DECREASE_PCT

    # Hard band ±12%
    if raw_change_pct > MAX_INCREASE_PCT:
        guardrails.append(f"Capped at +{MAX_INCREASE_PCT}% hard band (raw signal: +{raw_change_pct:.1f}%)")
        raw_change_pct = MAX_INCREASE_PCT
    if raw_change_pct < -MAX_DECREASE_PCT:
        guardrails.append(f"Floored at -{MAX_DECREASE_PCT}% hard band (raw signal: {raw_change_pct:.1f}%)")
        raw_change_pct = -MAX_DECREASE_PCT

    # Fairness single-step cap
    if raw_change_pct > ceiling_pct:
        guardrails.append(f"Fairness step cap: reduced from +{raw_change_pct:.1f}% to +{ceiling_pct}%"
                          + (" (sensitive/medical-need SKU)" if sku in SENSITIVE_SKUS else ""))
        raw_change_pct = ceiling_pct

    # Minimum margin floor
    final_price = round(base * (1 + raw_change_pct / 100), 2)
    if final_price - base < -base + MIN_MARGIN_EUR:
        guardrails.append(f"Minimum margin floor applied (€{MIN_MARGIN_EUR:.2f} above cost proxy)")
        final_price = round(base - base + MIN_MARGIN_EUR + base * 0.15, 2)

    # Round to nearest 0.05 (pharmacy pricing convention)
    final_price = round(round(final_price / 0.05) * 0.05, 2)
    actual_change = round((final_price / base - 1) * 100, 2)

    direction = "increase" if actual_change > 0.5 else "decrease" if actual_change < -0.5 else "hold"
    if direction == "hold":
        final_price = base

    reasons = [s["reason"] for s in signals if s["reason"]]
    rationale = "; ".join(reasons) if reasons else "No significant signals — hold at base price"
    if guardrails:
        rationale += f" [Guardrails: {'; '.join(guardrails)}]"

    return PriceDecision(
        sku=sku, product_name=name, base_price=base,
        recommended_price=final_price, change_pct=actual_change,
        direction=direction, signals_applied=signals,
        guardrails_fired=guardrails, rationale=rationale,
    )


def run_all(weather: dict, events: list[dict]) -> list[PriceDecision]:
    """Run pricing for the full catalogue."""
    from signals import supply_stress
    decisions = []
    for sku in CATALOGUE:
        stress = supply_stress(sku)
        decisions.append(compute_price(sku, weather, events, stress))
    return sorted(decisions, key=lambda d: abs(d.change_pct), reverse=True)
