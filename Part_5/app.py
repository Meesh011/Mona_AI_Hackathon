"""
app.py  —  Problem 5: Interview Support Agent
Streamlit UI for non-technical hiring managers at Kohlpharma / Jobs&Joy.
Paste or upload a job offer → get structured interview questions + red-flag checklist.
Uses the shared gemini_client helpers (google.generativeai SDK).
"""
import streamlit as st
import json
import os
import sys

# ── page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Interview Support Agent · Jobs&Joy",
    page_icon="🎯",
    layout="wide",
)

# ── inline gemini client (avoids dependency on Part_4 path) ────────────────
import copy
import google.generativeai as genai

MODEL_NAME = "gemini-2.5-flash"

def _configure(api_key: str) -> None:
    genai.configure(api_key=api_key)

def _clean_schema(schema: dict) -> dict:
    UNSUPPORTED = {
        "default", "title", "examples", "exclusiveMinimum", "exclusiveMaximum",
        "minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems",
        "pattern", "contentEncoding", "contentMediaType", "const",
    }
    def _clean(obj):
        if isinstance(obj, list):
            return [_clean(v) for v in obj]
        if not isinstance(obj, dict):
            return obj
        if "anyOf" in obj:
            non_null = [b for b in obj["anyOf"] if b.get("type") != "null"]
            if non_null:
                merged = copy.deepcopy(non_null[0])
                merged["nullable"] = True
                for k, v in obj.items():
                    if k not in ("anyOf",) and k not in merged:
                        merged[k] = v
                return _clean(merged)
        return {k: _clean(v) for k, v in obj.items() if k not in UNSUPPORTED}
    return _clean(schema)

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.hero {
    background: linear-gradient(135deg, #0f2942 0%, #1a4a7a 60%, #0d7a5f 100%);
    border-radius: 16px;
    padding: 2.5rem 2.5rem 2rem;
    margin-bottom: 2rem;
    color: white;
}
.hero h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2.4rem;
    margin: 0 0 0.4rem;
    line-height: 1.15;
}
.hero p { margin: 0; opacity: 0.85; font-size: 1.05rem; }
.hero .badge {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

.section-card {
    background: white;
    border: 1px solid #e8edf2;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.section-card h3 {
    font-size: 1rem;
    font-weight: 700;
    color: #0f2942;
    margin: 0 0 1rem;
    padding-bottom: 0.6rem;
    border-bottom: 2px solid #e8edf2;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.q-item {
    background: #f7f9fc;
    border-left: 3px solid #1a4a7a;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    margin-bottom: 0.6rem;
    font-size: 0.95rem;
    line-height: 1.5;
}
.q-item.behavioral { border-left-color: #0d7a5f; }
.q-item.technical   { border-left-color: #1a4a7a; }
.q-item.situational { border-left-color: #7c3aed; }

.flag-item {
    background: #fff8f0;
    border-left: 3px solid #f59e0b;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    margin-bottom: 0.6rem;
    font-size: 0.92rem;
    line-height: 1.5;
}
.flag-item.critical {
    background: #fff2f2;
    border-left-color: #ef4444;
}

.tag {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 10px;
    margin-right: 0.4rem;
    vertical-align: middle;
}
.tag-behavioral { background: #d1fae5; color: #065f46; }
.tag-technical  { background: #dbeafe; color: #1e40af; }
.tag-situational{ background: #ede9fe; color: #5b21b6; }
.tag-culture    { background: #fce7f3; color: #9d174d; }

.summary-box {
    background: linear-gradient(135deg, #f0f7ff, #f0fdf8);
    border: 1px solid #c7dff7;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1.5rem;
    font-size: 0.95rem;
    line-height: 1.6;
    color: #1e3a5f;
}

.stButton > button {
    background: linear-gradient(135deg, #0f2942, #1a4a7a) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.8rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    width: 100% !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }
</style>
""", unsafe_allow_html=True)

# ── hero ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="badge">Jobs &amp; Joy · Powered by MONA AI</div>
  <h1>Interview Support Agent</h1>
  <p>Paste a job offer and get structured interview questions + red-flag guidance — no recruiting expertise needed.</p>
</div>
""", unsafe_allow_html=True)

# ── sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password",
                            value=os.environ.get("GEMINI_API_KEY", ""),
                            help="Your Google AI Studio key")
    st.markdown("---")
    st.markdown("**How to use**")
    st.markdown("1. Enter your API key\n2. Paste the job offer text\n3. Click **Generate**\n4. Review questions & red flags")
    st.markdown("---")
    st.caption("Kohlpharma GmbH · Jobs&Joy transparency use case")

# ── main input ─────────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.markdown("#### 📋 Job Offer")
    job_text = st.text_area(
        "Paste the full job description here",
        height=320,
        placeholder="Senior Software Engineer\n\nCompany: Kohlpharma GmbH...\n\nAbout the role:\n...",
        label_visibility="collapsed",
    )

    num_questions = st.slider("Questions per category", min_value=2, max_value=6, value=3)
    focus_areas = st.multiselect(
        "Focus areas to emphasise",
        ["Technical skills", "Behavioral / soft skills", "Situational judgment",
         "Culture fit", "Red flag probes"],
        default=["Technical skills", "Behavioral / soft skills", "Red flag probes"],
    )

    generate_btn = st.button("🎯 Generate Interview Guide", use_container_width=True)

with col_right:
    st.markdown("#### 💡 Tips for non-technical hirers")
    st.info("""
**What this tool does:**
- Translates technical jargon into plain-English questions
- Highlights what *good* answers look like
- Flags vague or suspicious candidate responses

**During the interview:**
- Read questions verbatim — they're designed to be neutral
- Listen for specifics: names, numbers, dates
- Any answer that stays abstract is a yellow flag
    """)

# ── generation ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are an expert technical recruiter and interview coach helping a NON-TECHNICAL hiring manager
conduct a structured, fair interview for a technical or specialist role.

Your job is to read the job description and produce:
1. A brief plain-English role summary (2-3 sentences) for the hiring manager's context
2. Structured interview questions grouped by category
3. Red flags to watch for during interviews

CRITICAL RULES:
- ALL questions must be written in plain English a non-technical person can read aloud confidently
- For technical questions, include a "What a good answer looks like" note in plain English
- Questions should be open-ended and behavioural where possible ("Tell me about a time...")
- Red flags should be concrete observable behaviours, not vague gut-feel descriptions
- Adapt depth and category balance to the actual role — a recruiting role needs different questions than an engineering role

Return ONLY valid JSON matching the schema. No markdown, no preamble.
"""

def build_user_prompt(job_text: str, num_q: int, focus: list[str]) -> str:
    return f"""
Job offer to analyse:
---
{job_text}
---

Configuration:
- Questions per category: {num_q}
- Focus areas to emphasise: {', '.join(focus) if focus else 'all'}

Produce the interview guide JSON now.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "role_title": {"type": "string"},
        "role_summary": {"type": "string"},
        "key_skills_detected": {
            "type": "array",
            "items": {"type": "string"}
        },
        "interview_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["Technical", "Behavioral", "Situational", "Culture Fit", "Red Flag Probe"]
                    },
                    "question": {"type": "string"},
                    "why_we_ask": {"type": "string"},
                    "good_answer_looks_like": {"type": "string"},
                    "follow_up": {"type": "string", "nullable": True}
                },
                "required": ["category", "question", "why_we_ask", "good_answer_looks_like"]
            }
        },
        "red_flags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "signal": {"type": "string"},
                    "what_it_might_mean": {"type": "string"},
                    "severity": {"type": "string", "enum": ["High", "Medium", "Low"]}
                },
                "required": ["signal", "what_it_might_mean", "severity"]
            }
        },
        "interview_structure_suggestion": {"type": "string"},
        "hiring_manager_notes": {"type": "string"}
    },
    "required": ["role_title", "role_summary", "key_skills_detected",
                 "interview_questions", "red_flags", "interview_structure_suggestion"]
}

if generate_btn:
    if not api_key:
        st.error("Please enter your Gemini API key in the sidebar.")
    elif not job_text.strip():
        st.error("Please paste a job description first.")
    else:
        with st.spinner("Analysing job offer and generating interview guide…"):
            try:
                _configure(api_key)
                model = genai.GenerativeModel(
                    model_name=MODEL_NAME,
                    system_instruction=SYSTEM_PROMPT,
                )
                response = model.generate_content(
                    [build_user_prompt(job_text, num_questions, focus_areas)],
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                        temperature=0.3,
                    ),
                )
                raw = response.text.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                    raw = raw.strip()
                data = json.loads(raw)
                st.session_state["guide"] = data
                st.session_state["job_text"] = job_text
            except Exception as e:
                st.error(f"Error calling Gemini: {e}")

# ── results ────────────────────────────────────────────────────────────────
if "guide" in st.session_state:
    g = st.session_state["guide"]

    st.markdown("---")
    st.markdown(f"## Interview Guide — {g.get('role_title', 'Role')}")

    # summary
    st.markdown(f"""<div class="summary-box">
    <strong>Role Summary:</strong> {g.get('role_summary', '')}
    </div>""", unsafe_allow_html=True)

    # key skills detected
    skills = g.get("key_skills_detected", [])
    if skills:
        skills_html = " ".join(
            f'<span style="background:#e8f0fe;color:#1a4a7a;padding:3px 10px;border-radius:12px;font-size:0.82rem;font-weight:600;margin:2px;display:inline-block">{s}</span>'
            for s in skills
        )
        st.markdown(f"**Key skills detected:** {skills_html}", unsafe_allow_html=True)
        st.markdown("")

    # interview structure
    if g.get("interview_structure_suggestion"):
        st.markdown(f"""<div class="section-card">
        <h3>🗓️ Suggested Interview Structure</h3>
        <p style="margin:0;color:#374151;line-height:1.6">{g['interview_structure_suggestion']}</p>
        </div>""", unsafe_allow_html=True)

    # questions grouped by category
    questions = g.get("interview_questions", [])
    cat_order = ["Technical", "Behavioral", "Situational", "Culture Fit", "Red Flag Probe"]
    cat_icons = {"Technical": "🔧", "Behavioral": "🧠", "Situational": "💼",
                 "Culture Fit": "🤝", "Red Flag Probe": "🚩"}
    cat_colors = {"Technical": "technical", "Behavioral": "behavioral",
                  "Situational": "situational", "Culture Fit": "behavioral",
                  "Red Flag Probe": "technical"}
    tag_classes = {"Technical": "tag-technical", "Behavioral": "tag-behavioral",
                   "Situational": "tag-situational", "Culture Fit": "tag-culture",
                   "Red Flag Probe": "tag-technical"}

    by_cat = {}
    for q in questions:
        cat = q.get("category", "Other")
        by_cat.setdefault(cat, []).append(q)

    st.markdown("### 💬 Interview Questions")
    for cat in cat_order:
        qs = by_cat.get(cat, [])
        if not qs:
            continue
        icon = cat_icons.get(cat, "•")
        with st.expander(f"{icon} {cat} ({len(qs)} question{'s' if len(qs)!=1 else ''})", expanded=True):
            for i, q in enumerate(qs, 1):
                color_cls = cat_colors.get(cat, "behavioral")
                tag_cls = tag_classes.get(cat, "tag-technical")
                follow_up_html = ""
                if q.get("follow_up"):
                    follow_up_html = f'<div style="margin-top:0.5rem;font-size:0.85rem;color:#6b7280"><strong>Follow-up:</strong> {q["follow_up"]}</div>'
                st.markdown(f"""
<div class="q-item {color_cls}">
  <span class="tag {tag_cls}">{cat}</span>
  <strong>Q{i}.</strong> {q['question']}
  <div style="margin-top:0.6rem;font-size:0.85rem;color:#374151">
    <strong>Why we ask:</strong> {q.get('why_we_ask','')}
  </div>
  <div style="margin-top:0.3rem;font-size:0.85rem;color:#065f46">
    <strong>✓ Good answer:</strong> {q.get('good_answer_looks_like','')}
  </div>
  {follow_up_html}
</div>""", unsafe_allow_html=True)

    # red flags
    red_flags = g.get("red_flags", [])
    if red_flags:
        st.markdown("### 🚨 Red Flags to Watch For")
        high = [f for f in red_flags if f.get("severity") == "High"]
        others = [f for f in red_flags if f.get("severity") != "High"]
        for flag in high + others:
            sev = flag.get("severity", "Medium")
            cls = "critical" if sev == "High" else ""
            sev_color = "#ef4444" if sev == "High" else "#f59e0b" if sev == "Medium" else "#6b7280"
            st.markdown(f"""
<div class="flag-item {cls}">
  <span style="background:{sev_color};color:white;font-size:0.7rem;font-weight:700;padding:2px 8px;border-radius:10px;margin-right:0.5rem">{sev.upper()}</span>
  <strong>{flag['signal']}</strong>
  <div style="margin-top:0.4rem;font-size:0.87rem;color:#374151">
    <strong>What it might mean:</strong> {flag['what_it_might_mean']}
  </div>
</div>""", unsafe_allow_html=True)

    # hiring manager notes
    if g.get("hiring_manager_notes"):
        st.markdown(f"""<div class="section-card" style="margin-top:1.5rem">
        <h3>📝 Hiring Manager Notes</h3>
        <p style="margin:0;color:#374151;line-height:1.6">{g['hiring_manager_notes']}</p>
        </div>""", unsafe_allow_html=True)

    # download
    st.markdown("---")
    dl_col1, dl_col2 = st.columns([1, 3])
    with dl_col1:
        st.download_button(
            "⬇️ Download as JSON",
            data=json.dumps(g, indent=2, ensure_ascii=False),
            file_name=f"interview_guide_{g.get('role_title','role').replace(' ','_').lower()}.json",
            mime="application/json",
        )
