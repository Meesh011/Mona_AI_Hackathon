"""
gemini_client.py  (Part 6 — Allgäuer Latschenkiefer Filmmaker Agent)
google.generativeai SDK with _clean_schema fix.
"""
from __future__ import annotations
import os, json, copy
import google.generativeai as genai

MODEL_NAME = "gemini-2.5-flash"

def _configure(api_key=None):
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key: raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=key)

def _clean_schema(s: dict) -> dict:
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

REEL_SCHEMA = _clean_schema({
    "type": "object",
    "properties": {
        "reel_title":              {"type": "string"},
        "platform":                {"type": "string", "enum": ["TikTok","Instagram Reels","Both"]},
        "total_duration_seconds":  {"type": "number"},
        "music_mood":              {"type": "string"},
        "content_angle":           {"type": "string"},
        "hwg_compliance_note":     {"type": "string",
                                    "description": "Brief note on HWG compliance — no medical cure claims"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene_number":     {"type": "integer"},
                    "duration_seconds": {"type": "number"},
                    "scene_purpose":    {"type": "string",
                                        "enum": ["hook","product","benefit","social_proof","cta"]},
                    "layout":           {"type": "string",
                                        "enum": ["center","top_heavy","bottom_heavy"]},
                    "bg_color_1":       {"type": "string"},
                    "bg_color_2":       {"type": "string"},
                    "accent_color":     {"type": "string"},
                    "badge":            {"type": "string"},
                    "headline":         {"type": "string"},
                    "subtext":          {"type": "string"},
                    "cta":              {"type": "string"},
                    "voiceover_hint":   {"type": "string"},
                    "hwg_compliant":    {"type": "boolean"},
                },
                "required": ["scene_number","duration_seconds","scene_purpose",
                             "bg_color_1","bg_color_2","headline","layout"]
            }
        },
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "caption":  {"type": "string"},
    },
    "required": ["reel_title","scenes","platform","total_duration_seconds"]
})

# Brand palette derived from Allgäuer Latschenkiefer visual identity
BRAND_CONTEXT = """
BRAND: Allgäuer Latschenkiefer (Dr. Theiss Naturwaren GmbH, Homburg, Saarland)
Hero ingredient: Allgäuer Latschenkiefernöl — dwarf mountain-pine oil from own plantations in the Allgäu region.
Product lines: Feet (Füße), Legs (Beine), Muscles & Joints (Muskeln & Gelenke), Cough drops.
Distribution: German pharmacies (Apotheken) + pharmacy e-commerce.
Visual identity: Alpine/forest greens (#1a3d28, #2d6a3f), warm pine gold (#c9a84c), clean pharmacy white,
  muted stone grey. Alpine authenticity + German quality + natural efficacy.
Tone: trustworthy, active, natural, unpretentious — not luxury spa, not clinical cold.
"""

SYSTEM_PROMPT = f"""\
You are a senior social-media creative director for Allgäuer Latschenkiefer (Dr. Theiss Naturwaren GmbH).
You produce studio-quality reel briefs that get rendered into actual MP4 vertical videos.

{BRAND_CONTEXT}

━━ SAFE ZONE SPEC (1080×1920 canvas) ━━
These are the MANDATORY text-safe margins from the hackathon data pack:
  top    : 140 px  (keep ALL text/logos below y=140)
  bottom : 540 px  (keep ALL text/logos above y=1380; covers caption + CTA bar)
  right  : 150 px  (keep ALL text/logos left of x=930; action icons column)
  left   :  40 px  (keep ALL text/logos right of x=40)
  → Message-safe band: x 40–930, y 140–1380 (890×1240 px centred on canvas)
  → CTA bar: place inside y 1280–1380 (100px slot above bottom safe zone)
  → NEVER place any text outside this band.

━━ VIDEO ARC (5 scenes, 9–14s total) ━━
  1. HOOK     ≤2s  — bold statement or relatable pain point that stops scroll
  2. PRODUCT  2-3s — hero product reveal, what it is
  3. BENEFIT  2-3s — #1 reason to buy (functional benefit, not medical claim)
  4. PROOF    1-2s — ingredient origin or social proof moment
  5. CTA      2-3s — clear action + product name, always with cta text field

━━ CONTENT ANGLES (pick the one matching the requested angle) ━━
  • ritual_asmr   : ASMR foot bath ritual, sensory textures, evening wind-down
  • post_workout  : 15-sec post-workout recovery, sport energy, Mobil Eisspray
  • heavy_legs    : relatable "heavy legs after a shift" hook, Beinlotion
  • origin_story  : Allgäu plantation → distillation → bottle ingredient journey
  • sandal_prep   : spring callus care before sandal season

━━ HWG (Heilmittelwerbegesetz) GUARDRAILS ━━
  These are cosmetics, NOT drugs. STRICTLY FORBIDDEN:
  - "heals", "treats", "cures", "medicates", "therapy" for any condition
  - Specific medical efficacy claims (e.g. "eliminates varicose veins")
  - Before/after medical comparisons
  ALLOWED: "cares for", "refreshes", "soothes", "supports", "revives",
           "leaves skin feeling", "for tired legs", functional descriptions.
  Set hwg_compliant=true only if ALL scene text passes this check.

━━ COLOR GUIDANCE ━━
  Evolve through the brand palette across scenes. Scene gradients should feel
  like a journey through the alpine forest. Use pine greens, warm golds, deep
  forest midnight blues. Ensure white text has sufficient contrast on gradients.

Return ONLY valid JSON. No markdown. No commentary.
"""

def generate_reel_brief(
    product_name: str,
    product_description: str,
    sku: str,
    target_audience: str,
    platform: str,
    content_angle: str,
    api_key: str | None = None,
) -> dict:
    _configure(api_key)
    user_msg = f"""
Generate a reel brief for this Allgäuer Latschenkiefer product:

SKU: {sku}
Product: {product_name}
Description: {product_description}
Target audience: {target_audience}
Platform: {platform}
Content angle: {content_angle}

Follow the 5-scene arc (hook → product → benefit → proof → CTA).
All text MUST stay within the safe band (x 40–930, y 140–1380).
Apply HWG guardrails — no medical cure claims.
Brand palette: alpine greens, pine gold, clean white.
"""
    model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_PROMPT)
    resp  = model.generate_content(
        [user_msg],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=REEL_SCHEMA,
            temperature=0.65,
        ),
    )
    raw = resp.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)
