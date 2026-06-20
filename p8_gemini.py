"""
gemini_client.py — Part 8
Gemini interprets the pricing decisions and writes a pricing memo.
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

MEMO_SCHEMA = _clean_schema({
    "type": "object",
    "properties": {
        "executive_summary":  {"type": "string"},
        "market_context":     {"type": "string"},
        "pricing_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sku":             {"type": "string"},
                    "product_name":    {"type": "string"},
                    "action":          {"type": "string", "enum":["increase","decrease","hold"]},
                    "recommended_price":{"type": "number"},
                    "change_pct":      {"type": "number"},
                    "plain_rationale": {"type": "string"},
                    "risk_note":       {"type": "string"},
                    "priority":        {"type": "string", "enum":["High","Medium","Low"]},
                }
            }
        },
        "guardrail_summary":  {"type": "string"},
        "compliance_note":    {"type": "string"},
        "next_review_trigger":{"type": "string"},
    },
    "required": ["executive_summary","pricing_actions","guardrail_summary"]
})

SYSTEM_PROMPT = """\
You are the Revenue Manager for Allgäuer Latschenkiefer (Dr. Theiss Naturwaren GmbH).
You review signal-driven pricing recommendations and write a concise pricing memo for the commercial team.

Brand: German pharmacy cosmetics. Pharmacy pricing regulations (RPM/UVP rules) apply.
STRICT RULES:
- Never recommend gouging on health-related products
- Flag any recommendation that raises diabetic/medical-need SKUs by more than 5%
- All changes must be justifiable to a pharmacist partner
- Plain language — no jargon. The reader is a non-technical commercial manager.
- Keep compliance_note grounded in German pharmacy law context (RPM, HWG cosmetics boundary)

Return ONLY valid JSON.
"""

def generate_pricing_memo(
    weather: dict,
    events: list[dict],
    decisions: list[dict],
    api_key: str | None = None,
) -> dict:
    _configure(api_key)
    # Only send non-hold decisions to keep prompt tight
    actionable = [d for d in decisions if d.get("direction") != "hold"][:12]

    user_msg = f"""
Current market signals:
WEATHER: {json.dumps(weather, indent=2)}
UPCOMING EVENTS (next 21 days): {json.dumps(events[:8], indent=2)}

Pricing engine recommendations ({len(actionable)} actionable / {len(decisions)} total):
{json.dumps(actionable, indent=2)}

Write a pricing memo covering:
1. Executive summary of the market situation (2-3 sentences)
2. Market context explaining the key signals driving prices today
3. Pricing actions — for each actionable SKU: plain rationale, risk note, priority
4. Guardrail summary — what constraints fired and why they protect the brand
5. Compliance note — pharmacy/RPM/HWG context
6. Next review trigger — what signal would prompt an immediate re-run
"""
    model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_PROMPT)
    resp  = model.generate_content(
        [user_msg],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=MEMO_SCHEMA,
            temperature=0.3,
        ),
    )
    raw = resp.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip())
