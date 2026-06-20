"""
gemini_client.py — Part 7
Generates natural-language targeting recommendations from analytics data.
"""
from __future__ import annotations
import os, json, copy
import google.generativeai as genai

MODEL_NAME = "gemini-2.5-flash"

def _configure(api_key=None):
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key: raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=key)

def _clean_schema(s):
    DROP = {"default","title","examples","exclusiveMinimum","exclusiveMaximum",
            "minimum","maximum","minLength","maxLength","minItems","maxItems",
            "pattern","contentEncoding","contentMediaType","const"}
    def _c(o):
        if isinstance(o, list): return [_c(v) for v in o]
        if not isinstance(o, dict): return o
        if "anyOf" in o:
            nn = [b for b in o["anyOf"] if b.get("type") != "null"]
            if nn:
                m = copy.deepcopy(nn[0]); m["nullable"] = True
                for k,v in o.items():
                    if k != "anyOf" and k not in m: m[k] = v
                return _c(m)
        return {k: _c(v) for k,v in o.items() if k not in DROP}
    return _c(s)

TARGETING_SCHEMA = _clean_schema({
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "top_targeting_signals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "segment":      {"type": "string"},
                    "sku":          {"type": "string"},
                    "product_name": {"type": "string"},
                    "send_month":   {"type": "string"},
                    "send_day":     {"type": "string"},
                    "rationale":    {"type": "string"},
                    "ad_copy_hint": {"type": "string"},
                    "priority":     {"type": "string", "enum": ["High","Medium","Low"]},
                }
            }
        },
        "segment_insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "segment":     {"type": "string"},
                    "description": {"type": "string"},
                    "key_products":{"type": "string"},
                    "best_timing": {"type": "string"},
                    "channel_rec": {"type": "string"},
                }
            }
        },
        "lift_interpretation": {"type": "string"},
        "next_campaign_rec":   {"type": "string"},
    },
    "required": ["executive_summary","top_targeting_signals","segment_insights"]
})

SYSTEM_PROMPT = """\
You are a senior CRM and performance marketing analyst for Allgäuer Latschenkiefer
(Dr. Theiss Naturwaren GmbH). You interpret customer analytics data and produce
actionable targeting recommendations for pharmacy-channel advertising.

Brand context: natural foot/leg/muscle care brand sold in German pharmacies.
Products are cosmetics — no medical cure claims allowed (HWG).
Segments: wellness_50plus, active_women_35, athletes_25, traditional_55,
          diabetic_care, young_active_women.

Be specific — name SKUs, months, days of week. Give concrete ad copy hints.
Return ONLY valid JSON.
"""

def generate_targeting_report(
    rfm_summary: dict,
    top_signals: list[dict],
    seasonal_summary: dict,
    lift_result: dict,
    api_key: str | None = None,
) -> dict:
    _configure(api_key)
    user_msg = f"""
Analyse this customer data and generate targeting recommendations:

RFM SUMMARY:
{json.dumps(rfm_summary, indent=2)}

TOP TARGETING SIGNALS (segment × SKU × best timing):
{json.dumps(top_signals[:30], indent=2)}

SEASONAL REVENUE INDEX (top lines):
{json.dumps(seasonal_summary, indent=2)}

CAMPAIGN LIFT MEASUREMENT (ALK-LG-01 / 5in1 Beinlotion, July 2024):
{json.dumps(lift_result, indent=2)}

Produce:
1. Executive summary (3-4 sentences) of the customer base and key patterns
2. Top 8 targeting signals with specific send month/day and ad copy hints
3. One insight paragraph per segment
4. Interpretation of the campaign lift result
5. Recommendation for the next campaign (which SKU, which segment, which month)
"""
    model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_PROMPT)
    resp  = model.generate_content(
        [user_msg],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=TARGETING_SCHEMA,
            temperature=0.4,
        ),
    )
    raw = resp.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip())
