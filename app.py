"""
app.py — Unified Hackathon Demo
All 8 problems in one Streamlit app with sidebar navigation.
"""
import streamlit as st
import os, json, copy, tempfile, re
from pathlib import Path
from datetime import date

st.set_page_config(
    page_title="AI Agents Demo — Hackathon 2025",
    page_icon="🤖",
    layout="wide",
)

# ── Shared Gemini helper ───────────────────────────────────────────────────
import google.generativeai as genai

MODEL = "gemini-2.5-flash"

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

def gemini_json(prompt: str, schema: dict, system: str = "", api_key: str = "", temperature: float = 0.3) -> dict:
    key = api_key or os.environ.get("GEMINI_API_KEY","")
    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name=MODEL, system_instruction=system or "Return JSON only.")
    resp = model.generate_content(
        [prompt],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=_clean_schema(schema),
            temperature=temperature,
        ),
    )
    raw = resp.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip())

def gemini_text(prompt: str, system: str = "", api_key: str = "") -> str:
    key = api_key or os.environ.get("GEMINI_API_KEY","")
    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name=MODEL, system_instruction=system or "Be helpful.")
    return model.generate_content([prompt]).text

def gemini_vision(prompt: str, image_bytes: bytes, schema: dict, system: str = "", api_key: str = "") -> dict:
    key = api_key or os.environ.get("GEMINI_API_KEY","")
    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name=MODEL, system_instruction=system)
    resp = model.generate_content(
        [prompt, {"mime_type": "image/png", "data": image_bytes}],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    raw = resp.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip())

# ── Shared CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; }
.hero { border-radius:14px; padding:2rem 2.5rem 1.6rem; margin-bottom:1.6rem; }
.kicker { font-size:.7rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.6rem; }
.hero h1 { font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:700;margin:0 0 .35rem; }
.hero p  { opacity:.75;font-size:.95rem;margin:0; }
.card { background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:1rem 1.2rem;margin-bottom:.7rem; }
.verdict-valid   { background:#ecfdf5;border:2px solid #10b981;border-radius:10px;padding:1rem 1.3rem; }
.verdict-invalid { background:#fef2f2;border:2px solid #ef4444;border-radius:10px;padding:1rem 1.3rem; }
.verdict-review  { background:#fffbeb;border:2px solid #f59e0b;border-radius:10px;padding:1rem 1.3rem; }
.stButton>button { border-radius:8px!important; font-weight:600!important; width:100%!important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar navigation ─────────────────────────────────────────────────────
PAGES = {
    "🏠 Home":                       "home",
    "1️⃣  Invoice Processing":         "p1",
    "2️⃣  Shift Replacement":          "p2",
    "3️⃣  Work Permit Validation":     "p3",
    "4️⃣  CV & Certificate Fraud":     "p4",
    "5️⃣  Interview Support":          "p5",
    "6️⃣  Filmmaker / Reel Agent":     "p6",
    "7️⃣  Customer Analytics":         "p7",
    "8️⃣  Dynamic Pricing":            "p8",
}

with st.sidebar:
    st.markdown("## 🤖 Hackathon 2025")
    st.markdown("---")
    page_label = st.radio("Navigate to", list(PAGES.keys()), label_visibility="collapsed")
    page = PAGES[page_label]
    st.markdown("---")
    api_key = st.text_input("🔑 Gemini API Key", type="password",
                             value=os.environ.get("GEMINI_API_KEY",""),
                             help="Required for AI features")
    st.markdown("---")
    st.caption("All 8 agents in one app\nSaarland Hackathon 2025")

# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if page == "home":
    st.markdown("""
    <div class="hero" style="background:linear-gradient(135deg,#0f1e3d,#1a3a6e,#0d4f3f);color:white">
      <div class="kicker" style="color:#60a5fa">Saarland AI Hackathon 2025</div>
      <h1 style="color:white">8 AI Agents. One App.</h1>
      <p style="color:rgba(255,255,255,.75)">
        Real business problems from Saarland companies, solved with Gemini AI agents.
        Use the sidebar to navigate between all 8 solutions.
      </p>
    </div>
    """, unsafe_allow_html=True)

    companies = [
        ("1️⃣", "Invoice Processing",       "Globus Group",                      "St. Wendel",     "Auto-routes supplier invoices to the right department"),
        ("2️⃣", "Shift Replacement",         "Universitätsklinikum des Saarlandes","Homburg",        "Fills night-shift gaps by contacting available staff automatically"),
        ("3️⃣", "Work Permit Validation",    "Leistenschneider Personaldienstl.", "Saarbrücken",    "Validates work permits and checks expiry with AI document reading"),
        ("4️⃣", "CV & Certificate Fraud",    "Persowerk Deutschland GmbH",        "Saarbrücken",    "Detects fake CVs and unverifiable certificates"),
        ("5️⃣", "Interview Support",         "Kohlpharma GmbH",                   "Merzig",         "Generates interview questions for non-technical hiring managers"),
        ("6️⃣", "Filmmaker Agent",           "Dr. Theiss / Allgäuer Latschenk.",  "Homburg",        "Creates TikTok/Instagram reels with safe-zone-aware text placement"),
        ("7️⃣", "Customer Analytics",        "Dr. Theiss Naturwaren GmbH",        "Homburg",        "RFM segments, seasonal targeting signals, campaign lift measurement"),
        ("8️⃣", "Dynamic Pricing",           "Dr. Theiss Naturwaren GmbH",        "Homburg",        "Adjusts prices based on weather, events, and supply-chain signals"),
    ]
    cols = st.columns(2)
    for i, (num, title, company, city, desc) in enumerate(companies):
        with cols[i % 2]:
            st.markdown(f"""<div class="card">
            <strong>{num} {title}</strong><br>
            <span style="font-size:.8rem;color:#6b7280">{company} · {city}</span><br>
            <span style="font-size:.85rem;color:#374151;margin-top:.3rem;display:block">{desc}</span>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — INVOICE PROCESSING
# ══════════════════════════════════════════════════════════════════════════════
elif page == "p1":
    st.markdown("""
    <div class="hero" style="background:linear-gradient(135deg,#1e3a5f,#2d6a9f);color:white">
      <div class="kicker" style="color:#93c5fd">Globus Group · St. Wendel</div>
      <h1 style="color:white">Invoice Processing Agent</h1>
      <p>Upload supplier invoices (PDF, DOCX, images) → auto-routed to the right department.</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload invoices", type=["pdf","docx","png","jpg","jpeg"],
                                 accept_multiple_files=True)

    if uploaded:
        import sys; sys.path.insert(0, str(Path(__file__).parent))
        from p1_classifier import classify_invoice
        from p1_invoice_processor import extract_text
        import pandas as pd

        results = []
        for f in uploaded:
            with tempfile.NamedTemporaryFile(suffix=Path(f.name).suffix, delete=False) as tmp:
                tmp.write(f.read()); tmp_path = tmp.name
            try:
                text = extract_text(tmp_path)
                dept = classify_invoice(text)
            except Exception as e:
                dept = f"Error: {e}"
            finally:
                os.unlink(tmp_path)
            results.append({"Invoice": f.name, "Department": dept, "Status": "Pending Approval"})

        df = pd.DataFrame(results)
        st.success(f"✅ Processed {len(results)} invoice(s)")
        DEPT_COLORS = {
            "IT":"#dbeafe","Marketing":"#fce7f3","HR / Travel":"#dcfce7",
            "Facilities":"#fef3c7","Operations":"#ede9fe","Unclassified":"#f1f5f9"
        }
        for r in results:
            bg = DEPT_COLORS.get(r["Department"],"#f8fafc")
            st.markdown(f"""<div style="background:{bg};border-radius:8px;padding:.8rem 1rem;
            margin-bottom:.5rem;border-left:4px solid #94a3b8">
            <strong>{r['Invoice']}</strong> →
            <strong style="margin-left:.5rem">{r['Department']}</strong>
            <span style="float:right;font-size:.8rem;color:#6b7280">{r['Status']}</span>
            </div>""", unsafe_allow_html=True)

        st.download_button("⬇️ Download Results CSV",
            data=df.to_csv(index=False).encode(),
            file_name="invoice_routing.csv", mime="text/csv")
    else:
        st.info("Upload one or more invoice files to get started.")
        st.markdown("""**Supported departments:** IT · Marketing · HR/Travel · Facilities · Operations
        \n**Supported formats:** PDF · Word (.docx) · PNG/JPG images""")

# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — SHIFT REPLACEMENT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "p2":
    st.markdown("""
    <div class="hero" style="background:linear-gradient(135deg,#1a0533,#3b0764,#1e3a5f);color:white">
      <div class="kicker" style="color:#c4b5fd">UKS Homburg · Universitätsklinikum</div>
      <h1 style="color:white">Shift Replacement Agent</h1>
      <p>Type a natural-language HR message → Gemini extracts the shift details → finds available qualified staff.</p>
    </div>
    """, unsafe_allow_html=True)

    demo_msgs = [
        "Maria Berger ist krank. Brauchen Ersatz Nachtschicht Intensivstation Donnerstag. Nur Pflegefachkraft.",
        "Notfall: Pfleger Thomas Müller ausgefallen, Frühschicht Kardiologie Montag.",
        "Krankheitsausfall Spätschicht Notaufnahme Mittwoch, bitte Krankenschwester finden.",
    ]
    msg = st.selectbox("Try a demo message or type your own:", ["(type your own)"] + demo_msgs)
    hr_msg = st.text_area("HR Message", value="" if msg == "(type your own)" else msg, height=80)
    accept_after = st.slider("Simulate acceptance after N contacts", 1, 5, 2)

    if st.button("🏥 Run Shift Agent") and hr_msg:
        if not api_key:
            st.error("API key required")
        else:
            with st.spinner("Parsing request and finding staff…"):
                # Parse with Gemini
                schema = {"type":"object","properties":{
                    "ward":{"type":"string"},"shift":{"type":"string"},
                    "day":{"type":"string"},"date":{"type":"string","nullable":True},
                    "qualification":{"type":"string","nullable":True},"reason":{"type":"string"}
                },"required":["ward","shift","day"]}
                try:
                    parsed = gemini_json(
                        f'HR message: "{hr_msg}"\nExtract the shift replacement details.',
                        schema,
                        system="You are a hospital HR assistant. Extract shift details from the message.",
                        api_key=api_key,
                    )
                except Exception as e:
                    parsed = {"ward":"Intensivstation","shift":"Nacht","day":"Donnerstag",
                              "qualification":"Pflegefachkraft","reason":"Krankheit"}
                    st.warning(f"AI parse failed ({e}), using demo values")

            st.markdown("#### 📋 Parsed Shift Request")
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Ward", parsed.get("ward","—"))
            c2.metric("Shift", parsed.get("shift","—"))
            c3.metric("Day", parsed.get("day","—"))
            c4.metric("Qualification", parsed.get("qualification") or "Any")

            # Find staff from database if excel exists, else show demo
            data_path = Path(__file__).parent / "data" / "hospital_schedule_part_2.xlsx"
            if data_path.exists():
                from p2_database import find_available_staff
                candidates = find_available_staff(
                    parsed.get("ward",""), parsed.get("shift",""),
                    parsed.get("day",""), parsed.get("qualification")
                )
            else:
                # Demo staff
                candidates = [
                    {"name":"Anna Schmidt","phone":"+49 681 111001","email":"anna.schmidt@uks.eu",
                     "role":"Registered Nurse","department":"ICU","qualifications":["BLS","ICU"],
                     "contract":"Part-time","overtime_ok":"Yes","hours_headroom":12},
                    {"name":"Klaus Weber","phone":"+49 681 111002","email":"klaus.weber@uks.eu",
                     "role":"Registered Nurse","department":"General","qualifications":["BLS"],
                     "contract":"Full-time","overtime_ok":"No","hours_headroom":8},
                    {"name":"Sarah Becker","phone":"+49 681 111003","email":"sarah.becker@uks.eu",
                     "role":"Charge Nurse","department":"ICU","qualifications":["BLS","ICU","ACLS"],
                     "contract":"Per-diem","overtime_ok":"Yes","hours_headroom":20},
                ]

            st.markdown(f"#### 👥 Found {len(candidates)} Available Staff")
            filled_by = None
            for i, staff in enumerate(candidates[:6]):
                accepted = (i + 1) >= accept_after
                if accepted and filled_by is None:
                    filled_by = staff
                status_icon = "✅ Accepted" if accepted else "⏳ No reply"
                bg = "#ecfdf5" if accepted else "#f8fafc"
                st.markdown(f"""<div style="background:{bg};border-radius:8px;padding:.8rem 1rem;
                margin-bottom:.4rem;border-left:4px solid {'#10b981' if accepted else '#cbd5e1'}">
                <strong>{staff['name']}</strong> · {staff['role']} · {staff['department']}<br>
                <span style="font-size:.82rem;color:#6b7280">
                📱 {staff['phone']} · {staff['contract']} · OT: {staff['overtime_ok']}
                · Headroom: {staff.get('hours_headroom',0)}h</span>
                <span style="float:right;font-weight:700;
                color:{'#10b981' if accepted else '#94a3b8'}">{status_icon}</span>
                </div>""", unsafe_allow_html=True)
                if accepted:
                    break

            if filled_by:
                st.success(f"✅ Shift filled by **{filled_by['name']}** — SMS + email sent")
            else:
                st.error("❌ No staff accepted — escalate to HR head")

# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — WORK PERMIT VALIDATION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "p3":
    st.markdown("""
    <div class="hero" style="background:linear-gradient(135deg,#0c2340,#1a4060,#0d3b2e);color:white">
      <div class="kicker" style="color:#6ee7b7">Leistenschneider Personaldienstleistungen · Saarbrücken</div>
      <h1 style="color:white">Work Permit Validation Agent</h1>
      <p>Upload a work permit document → AI reads it → VALID / INVALID / NEEDS REVIEW verdict with confidence score.</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload work permit (PDF or image)", type=["pdf","png","jpg","jpeg"])

    if uploaded:
        if not api_key:
            st.error("Gemini API key required")
        else:
            with st.spinner("Reading document with AI…"):
                # Convert to image bytes
                suffix = Path(uploaded.name).suffix
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(uploaded.read()); tmp_path = tmp.name
                try:
                    from p3_pdf_utils import file_to_images
                    images = file_to_images(tmp_path)
                    image_bytes = images[0]
                finally:
                    os.unlink(tmp_path)

                # Call Gemini with vision
                PERMIT_PROMPT = """Analyze this document image and extract work permit information.
Return a JSON object with exactly these fields:
{
  "is_work_permit": true/false,
  "document_type": string or null,
  "full_name": string or null,
  "nationality": string or null,
  "document_number": string or null,
  "date_of_issue": "YYYY-MM-DD" or null,
  "valid_until": "YYYY-MM-DD" or null,
  "employment_permitted": true/false/null,
  "employment_remarks_raw": string or null,
  "issuing_authority": string or null,
  "extraction_confidence": float 0-100,
  "notes": string or null
}
Return ONLY the JSON object."""
                key = api_key or os.environ.get("GEMINI_API_KEY","")
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_name=MODEL)
                resp = model.generate_content(
                    [PERMIT_PROMPT, {"mime_type":"image/png","data":image_bytes}],
                    generation_config=genai.GenerationConfig(response_mime_type="application/json", temperature=0),
                )
                raw = resp.text.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"): raw = raw[4:]
                data = json.loads(raw.strip())

            # Apply validation rules
            from p3_schema import ExtractedPermitData
            from p3_validator import validate
            extracted = ExtractedPermitData(**data)
            result = validate(uploaded.name, extracted)

            verdict_cls = {"VALID":"verdict-valid","INVALID":"verdict-invalid","NEEDS_REVIEW":"verdict-review"}[result.verdict]
            verdict_icon = {"VALID":"✅","INVALID":"❌","NEEDS_REVIEW":"⚠️"}[result.verdict]
            st.markdown(f"""<div class="{verdict_cls}">
            <span style="font-size:1.5rem">{verdict_icon} <strong>{result.verdict}</strong></span>
            &nbsp;&nbsp; Confidence: <strong>{result.confidence_percent:.0f}%</strong>
            </div>""", unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Extracted Data**")
                for k, v in [
                    ("Document Type", extracted.document_type),
                    ("Name", extracted.full_name),
                    ("Nationality", extracted.nationality),
                    ("Document #", extracted.document_number),
                    ("Issued", extracted.date_of_issue),
                    ("Valid Until", str(result.valid_until) if result.valid_until else "—"),
                    ("Expired", "Yes" if result.is_expired else "No" if result.is_expired is False else "Unknown"),
                    ("Employment OK", "✅ Yes" if extracted.employment_permitted else "❌ No" if extracted.employment_permitted is False else "Unclear"),
                ]:
                    if v: st.markdown(f"- **{k}:** {v}")
            with c2:
                st.markdown("**Decision Reasons**")
                for r in result.reasons:
                    st.markdown(f"- {r}")
                if extracted.notes:
                    st.warning(f"🚩 Red flags: {extracted.notes}")
    else:
        st.info("Upload a work permit PDF or image. Supports Aufenthaltserlaubnis, Blaue Karte EU, residence permits.")

# ══════════════════════════════════════════════════════════════════════════════
# PART 4 — CV & CERTIFICATE FRAUD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "p4":
    st.markdown("""
    <div class="hero" style="background:linear-gradient(135deg,#1a0a2e,#2d1454,#0f2040);color:white">
      <div class="kicker" style="color:#f9a8d4">Persowerk Deutschland GmbH · Saarbrücken</div>
      <h1 style="color:white">CV & Certificate Fraud Detection</h1>
      <p>Upload a CV + certificate images → AI cross-checks claims → trust score with per-certificate verdicts.</p>
    </div>
    """, unsafe_allow_html=True)

    if not api_key:
        st.warning("Gemini API key required for this module.")

    cv_file = st.file_uploader("Upload CV (PDF or image)", type=["pdf","png","jpg","jpeg"])
    cert_files = st.file_uploader("Upload certificates (images or PDFs)",
                                   type=["pdf","png","jpg","jpeg"], accept_multiple_files=True)

    if cv_file and st.button("🔍 Run Fraud Check") and api_key:
        with st.spinner("Analysing CV and certificates…"):
            import sys; sys.path.insert(0, str(Path(__file__).parent))
            # set api key env for the pipeline modules
            os.environ["GEMINI_API_KEY"] = api_key
            from p4_file_utils import to_image_bytes, extract_text_if_possible
            from p4_gemini import parse_cv_from_text, parse_cv_from_image, extract_certificate, judge_relevance
            from p4_cross_check import assess_certificate, build_candidate_report

            # Save CV
            with tempfile.NamedTemporaryFile(suffix=Path(cv_file.name).suffix, delete=False) as t:
                t.write(cv_file.read()); cv_path = t.name
            text = extract_text_if_possible(cv_path)
            cv_profile = parse_cv_from_text(text) if text else parse_cv_from_image(to_image_bytes(cv_path))
            os.unlink(cv_path)

            # Process certificates
            assessments = []
            for cf in cert_files:
                with tempfile.NamedTemporaryFile(suffix=Path(cf.name).suffix, delete=False) as t:
                    t.write(cf.read()); cert_path = t.name
                img = to_image_bytes(cert_path)
                cert = extract_certificate(img)
                assessment = assess_certificate(cf.name, cv_profile, cert)
                assessments.append(assessment)
                os.unlink(cert_path)

            report = build_candidate_report(cv_profile, assessments)

        # Trust score
        score_color = "#10b981" if report.overall_trust_score >= 75 else "#f59e0b" if report.overall_trust_score >= 45 else "#ef4444"
        flag_icon = {"LOW_RISK":"✅","MEDIUM_RISK":"⚠️","HIGH_RISK":"🚨"}[report.overall_flag]
        st.markdown(f"""<div style="background:#f8fafc;border:2px solid {score_color};border-radius:12px;
        padding:1.2rem 1.5rem;margin-bottom:1rem">
        <span style="font-size:1.8rem;font-weight:800;color:{score_color}">
        {flag_icon} Trust Score: {report.overall_trust_score:.0f}/100 — {report.overall_flag.replace('_',' ')}</span><br>
        <span style="color:#374151">{report.summary}</span>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"**Candidate:** {report.candidate_name or 'Unknown'}")
        if report.unsupported_claims:
            st.warning(f"**Unsupported CV claims:** {', '.join(report.unsupported_claims)}")

        VERDICT_COLORS = {
            "AUTHENTIC_AND_RELEVANT":"#ecfdf5","AUTHENTIC_BUT_UNRELATED":"#eff6ff",
            "NAME_MISMATCH":"#fef2f2","EXPIRED":"#fff7ed",
            "NOT_A_PERSONAL_CERTIFICATE":"#f8fafc","SUSPICIOUS":"#fef2f2"
        }
        for a in report.assessments:
            bg = VERDICT_COLORS.get(a.verdict,"#f8fafc")
            icon = {"AUTHENTIC_AND_RELEVANT":"✅","AUTHENTIC_BUT_UNRELATED":"ℹ️",
                    "NAME_MISMATCH":"🚨","EXPIRED":"⏰",
                    "NOT_A_PERSONAL_CERTIFICATE":"❌","SUSPICIOUS":"⚠️"}.get(a.verdict,"?")
            with st.expander(f"{icon} {a.filename} — {a.verdict}  (confidence {a.confidence_percent:.0f}%)"):
                for reason in a.reasons:
                    st.markdown(f"- {reason}")
    elif not cv_file:
        st.info("Upload a CV file to start. Certificates are optional but increase detection accuracy.")

# ══════════════════════════════════════════════════════════════════════════════
# PART 5 — INTERVIEW SUPPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "p5":
    st.markdown("""
    <div class="hero" style="background:linear-gradient(135deg,#0f2942,#1a4a7a,#0d7a5f);color:white">
      <div class="kicker" style="color:#6ee7b7">Kohlpharma GmbH · Merzig · Jobs&Joy</div>
      <h1 style="color:white">Interview Support Agent</h1>
      <p>Paste a job description → get structured interview questions, good-answer guides, and red flags.</p>
    </div>
    """, unsafe_allow_html=True)

    SAMPLE_JOB = """Go-to-Market (GTM) Engineer — MONA AI GmbH
Build systems that scale sales. Design lead enrichment pipelines, CRM automations (HubSpot/Salesforce),
internal tools with LLM APIs. Python/TypeScript, SQL, REST/webhooks required. 2+ years GTM/RevOps."""

    job_text = st.text_area("Paste job description", value=SAMPLE_JOB, height=180)
    n_q = st.slider("Questions per category", 2, 5, 3)
    focus = st.multiselect("Focus areas", ["Technical skills","Behavioral","Situational","Culture Fit","Red Flag Probes"],
                            default=["Technical skills","Behavioral","Red Flag Probes"])

    if st.button("🎯 Generate Interview Guide") and job_text:
        if not api_key:
            st.error("API key required")
        else:
            SCHEMA = {"type":"object","properties":{
                "role_title":{"type":"string"},
                "role_summary":{"type":"string"},
                "key_skills_detected":{"type":"array","items":{"type":"string"}},
                "interview_questions":{"type":"array","items":{"type":"object","properties":{
                    "category":{"type":"string","enum":["Technical","Behavioral","Situational","Culture Fit","Red Flag Probe"]},
                    "question":{"type":"string"},
                    "why_we_ask":{"type":"string"},
                    "good_answer_looks_like":{"type":"string"},
                    "follow_up":{"type":"string","nullable":True},
                },"required":["category","question","why_we_ask","good_answer_looks_like"]}},
                "red_flags":{"type":"array","items":{"type":"object","properties":{
                    "signal":{"type":"string"},
                    "what_it_might_mean":{"type":"string"},
                    "severity":{"type":"string","enum":["High","Medium","Low"]},
                },"required":["signal","what_it_might_mean","severity"]}},
                "interview_structure_suggestion":{"type":"string"},
            },"required":["role_title","interview_questions","red_flags"]}
            SYS = "You are an expert technical recruiter helping a NON-TECHNICAL hiring manager. Write all questions in plain English a non-technical person can read aloud. Return JSON only."
            with st.spinner("Generating interview guide…"):
                try:
                    guide = gemini_json(
                        f"Job offer:\n{job_text}\n\nGenerate {n_q} questions per category. Focus: {', '.join(focus)}",
                        SCHEMA, system=SYS, api_key=api_key, temperature=0.3
                    )
                    st.session_state["p5_guide"] = guide
                except Exception as e:
                    st.error(f"Error: {e}")

    if "p5_guide" in st.session_state:
        g = st.session_state["p5_guide"]
        st.markdown(f"### {g.get('role_title','Role')}")
        st.info(g.get("role_summary",""))
        skills = g.get("key_skills_detected",[])
        if skills:
            st.markdown(" ".join(f"`{s}`" for s in skills))

        by_cat = {}
        for q in g.get("interview_questions",[]):
            by_cat.setdefault(q["category"],[]).append(q)
        CAT_ICONS = {"Technical":"🔧","Behavioral":"🧠","Situational":"💼","Culture Fit":"🤝","Red Flag Probe":"🚩"}
        for cat, qs in by_cat.items():
            with st.expander(f"{CAT_ICONS.get(cat,'•')} {cat} ({len(qs)})", expanded=True):
                for i, q in enumerate(qs,1):
                    st.markdown(f"**Q{i}.** {q['question']}")
                    st.markdown(f"  *Why:* {q.get('why_we_ask','')}")
                    st.markdown(f"  ✓ *Good answer:* {q.get('good_answer_looks_like','')}")
                    if q.get("follow_up"):
                        st.markdown(f"  ↩ *Follow-up:* {q['follow_up']}")
                    st.markdown("---")

        st.markdown("### 🚨 Red Flags")
        for flag in g.get("red_flags",[]):
            sev = flag.get("severity","Medium")
            color = "#ef4444" if sev=="High" else "#f59e0b" if sev=="Medium" else "#94a3b8"
            st.markdown(f"""<div style="border-left:4px solid {color};background:#f8fafc;
            padding:.6rem 1rem;border-radius:0 8px 8px 0;margin-bottom:.4rem">
            <strong>{flag['signal']}</strong> <span style="color:{color};font-size:.75rem">({sev})</span><br>
            <span style="font-size:.85rem;color:#374151">{flag['what_it_might_mean']}</span>
            </div>""", unsafe_allow_html=True)

        st.download_button("⬇️ Download Guide (JSON)",
            data=json.dumps(g, indent=2, ensure_ascii=False),
            file_name="interview_guide.json", mime="application/json")

# ══════════════════════════════════════════════════════════════════════════════
# PART 6 — FILMMAKER AGENT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "p6":
    st.markdown("""
    <div class="hero" style="background:linear-gradient(135deg,#0a1a0e,#1a3d28,#2d5a1e);color:white">
      <div class="kicker" style="color:#86efac">Dr. Theiss · Allgäuer Latschenkiefer · Homburg</div>
      <h1 style="color:white">🎬 Reel Filmmaker Agent</h1>
      <p>Pick a product → Gemini writes a 5-scene brief → renders a real 1080×1920 MP4 with safe zones locked in.</p>
    </div>
    """, unsafe_allow_html=True)

    HERO_SKUS = [
        {"sku":"ALK-MG-01","name":"Mobil Gel","desc":"Classic muscle & joint gel with Latschenkiefernöl","audience":"Active 30+, 55+ joints","season":"Autumn–Winter"},
        {"sku":"ALK-MG-03","name":"Mobil Eisspray akut","desc":"Fast-acting cold spray for acute muscle strain","audience":"Athletes, teams","season":"Sport season"},
        {"sku":"ALK-LG-01","name":"5 in 1 Beinlotion","desc":"Multi-benefit leg lotion for tired, heavy legs","audience":"Women 35–65","season":"Summer"},
        {"sku":"ALK-FB-02","name":"Sole Fußbad","desc":"Alpine brine foot bath with Latschenkiefernöl","audience":"Wellness, 50+","season":"Winter"},
        {"sku":"ALK-FB-01","name":"Fuß Butter","desc":"Rich foot butter for very dry skin","audience":"45+ dry-skin, women","season":"Autumn–Winter"},
        {"sku":"ALK-FB-04","name":"Hornhaut Entferner Maske","desc":"2-step sock-mask callus treatment","audience":"Women 25–45","season":"Spring–Summer"},
    ]
    ANGLES = {
        "ritual_asmr":  "🛁 ASMR Foot Bath Ritual",
        "post_workout": "⚡ 15s Post-Workout Recovery",
        "heavy_legs":   "😮‍💨 Heavy Legs After a Shift",
        "origin_story": "🌲 Ingredient Origin Story",
        "sandal_prep":  "👡 Sandal Season Prep",
    }

    c1, c2 = st.columns([3,2])
    with c1:
        sku_key = st.radio("Hero SKU", [s["sku"] for s in HERO_SKUS],
                            format_func=lambda x: next(s["name"] for s in HERO_SKUS if s["sku"]==x))
        selected = next(s for s in HERO_SKUS if s["sku"]==sku_key)
        st.caption(f"{selected['desc']} · {selected['audience']} · {selected['season']}")
        angle = st.radio("Content angle", list(ANGLES.keys()), format_func=lambda x: ANGLES[x])
    with c2:
        platform = st.selectbox("Platform", ["Both","TikTok","Instagram Reels"])
        st.markdown("""**Safe zones enforced:**
- Top: 140px · Bottom: 540px
- Right: 150px · Left: 40px
- Message band: 890×1240px""")
        show_sz = st.checkbox("Show safe zone guides on preview")

    if st.button("🌲 Generate Brief + Preview") and api_key:
        from p6_gemini import generate_reel_brief
        with st.spinner("Generating reel brief…"):
            brief = generate_reel_brief(
                product_name=selected["name"], product_description=selected["desc"],
                sku=selected["sku"], target_audience=selected["audience"],
                platform=platform, content_angle=angle, api_key=api_key,
            )
            st.session_state["p6_brief"] = brief
        st.success(f"✅ {len(brief.get('scenes',[]))} scenes · {brief.get('total_duration_seconds','?')}s")

    if "p6_brief" in st.session_state:
        brief = st.session_state["p6_brief"]
        from p6_video_engine import render_thumbnail
        from PIL import Image as PILImage
        scenes = brief.get("scenes",[])
        st.markdown(f"### {brief.get('reel_title','')}")
        thumb_cols = st.columns(min(len(scenes),5))
        for i, scene in enumerate(scenes):
            with thumb_cols[i % 5]:
                try:
                    th = render_thumbnail(scene, show_safe_zone=show_sz)
                    dw = int(260 * 1080/1920)
                    st.image(th.resize((dw, 260), PILImage.LANCZOS), use_container_width=True)
                except Exception as e:
                    st.error(str(e))
                st.caption(f"S{scene['scene_number']} · {scene.get('scene_purpose','')} · {scene.get('duration_seconds','?')}s")

        burn_sz = st.checkbox("Burn guides into video")
        if st.button("🎬 Render MP4"):
            from p6_video_engine import write_video
            import shutil, glob as _glob
            def _find_ffmpeg():
                f = shutil.which("ffmpeg")
                if f: return f
                for p in [r"C:\ffmpeg\bin\ffmpeg.exe",r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"] + _glob.glob(r"C:\ffmpeg*\bin\ffmpeg.exe"):
                    if os.path.isfile(p): return p
                raise FileNotFoundError("ffmpeg not found. Run: winget install Gyan.FFmpeg")
            try:
                _find_ffmpeg()
                with st.spinner("Rendering…"):
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                        tmp = f.name
                    write_video(scenes, tmp, show_safe_zone=burn_sz)
                    with open(tmp,"rb") as f: vb = f.read()
                    os.unlink(tmp)
                st.video(vb)
                st.download_button("⬇️ Download MP4", vb,
                    file_name=f"{brief.get('reel_title','reel').replace(' ','_')}.mp4", mime="video/mp4")
            except FileNotFoundError as e:
                st.error(str(e))
    elif not api_key:
        st.info("Enter your Gemini API key in the sidebar to generate a reel brief.")

# ══════════════════════════════════════════════════════════════════════════════
# PART 7 — CUSTOMER ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "p7":
    st.markdown("""
    <div class="hero" style="background:linear-gradient(135deg,#0f1e2d,#162d44,#0a2010);color:white">
      <div class="kicker" style="color:#60a5fa">Dr. Theiss Naturwaren GmbH · Homburg</div>
      <h1 style="color:white">📊 Customer Analytics Agent</h1>
      <p>RFM segmentation · seasonal patterns · optimal ad send-windows · campaign lift measurement.</p>
    </div>
    """, unsafe_allow_html=True)

    import pandas as pd
    import sys; sys.path.insert(0, str(Path(__file__).parent))

    # Load or generate data
    TX_PATH = Path(__file__).parent / "transactions.csv"
    CX_PATH = Path(__file__).parent / "customers.csv"
    if not TX_PATH.exists():
        with st.spinner("Generating synthetic dataset…"):
            # inline minimal data gen
            exec(open(Path(__file__).parent / "p7_generate_data.py").read())
    if TX_PATH.exists():
        from p7_analytics import load_data, compute_rfm, seasonal_index, send_windows, campaign_lift
        tx, cx = load_data(str(TX_PATH), str(CX_PATH))

        tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview","👥 RFM","🗓️ Seasonal","📏 Lift"])

        with tab1:
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Total Revenue", f"€{tx['revenue'].sum():,.0f}")
            m2.metric("Customers", tx['customer_id'].nunique())
            m3.metric("Transactions", len(tx))
            m4.metric("Avg Order", f"€{tx['revenue'].mean():.2f}")
            tx["month_str"] = tx["date"].dt.to_period("M").astype(str)
            st.line_chart(tx.groupby("month_str")["revenue"].sum())

        with tab2:
            rfm = compute_rfm(tx)
            seg_c = rfm["rfm_segment"].value_counts()
            c1,c2,c3 = st.columns(3)
            c1.metric("High Value", seg_c.get("high_value",0))
            c2.metric("Mid Value",  seg_c.get("mid_value",0))
            c3.metric("At Risk",    seg_c.get("at_risk",0))
            st.dataframe(rfm[["customer_id","recency_days","frequency","monetary","rfm_segment"]].head(100), use_container_width=True)

        with tab3:
            si = seasonal_index(tx)
            pivot = si.pivot(index="line", columns="month", values="seasonal_index").fillna(0)
            pivot.columns = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            st.dataframe(pivot.style.background_gradient(cmap="RdYlGn",axis=None,vmin=0,vmax=2.5).format("{:.2f}"), use_container_width=True)
            sw = send_windows(tx)
            st.dataframe(sw[["segment","sku","product_name","best_month_name","best_dow_name"]].rename(
                columns={"best_month_name":"Best Month","best_dow_name":"Best Day"}), use_container_width=True)

        with tab4:
            lift = campaign_lift(tx,"ALK-LG-01","2024-06-01","2024-06-30","2024-07-01","2024-07-31")
            lp = lift["lift_pct"]
            color = "#10b981" if lp > 0 else "#ef4444"
            st.markdown(f"""<div style="background:#f8fafc;border:2px solid {color};border-radius:12px;padding:1.2rem 1.5rem">
            <span style="font-size:1.6rem;font-weight:800;color:{color}">
            {'📈' if lp>0 else '📉'} {lp:+.1f}% Lift (5in1 Beinlotion · July 2024)</span><br>
            DiD: €{lift['did_lift_eur']:+,.2f} · p={lift['p_value']} · {'✅ Significant' if lift['significant'] else '⚠️ Not significant'}
            </div>""", unsafe_allow_html=True)
            c1,c2 = st.columns(2)
            c1.metric("Treatment Post-Revenue", f"€{lift['treatment_post_rev']:,.2f}", delta=f"€{lift['treatment_post_rev']-lift['treatment_pre_rev']:+,.2f}")
            c2.metric("Control Post-Revenue",   f"€{lift['control_post_rev']:,.2f}",   delta=f"€{lift['control_post_rev']-lift['control_pre_rev']:+,.2f}")

        if api_key:
            if st.button("🤖 Generate AI Targeting Report"):
                from p7_gemini import generate_targeting_report
                rfm_s = {"total_customers":int(len(rfm)),"high_value_count":int((rfm["rfm_segment"]=="high_value").sum()),
                         "avg_order_value":float(tx["revenue"].mean().round(2)),
                         "top_segments":tx.groupby("segment")["revenue"].sum().sort_values(ascending=False).head(3).round(2).to_dict()}
                si_top = si[si["seasonal_index"]>1.3].sort_values("seasonal_index",ascending=False).head(10)[["line","month","seasonal_index"]].to_dict(orient="records")
                lift_r = campaign_lift(tx,"ALK-LG-01","2024-06-01","2024-06-30","2024-07-01","2024-07-31")
                sw_top = send_windows(tx).head(20).fillna("").to_dict(orient="records")
                with st.spinner("Analysing…"):
                    rep = generate_targeting_report(rfm_s, sw_top, si_top, lift_r, api_key)
                st.markdown(f"**{rep.get('executive_summary','')}**")
                for sig in rep.get("top_targeting_signals",[])[:5]:
                    st.markdown(f"- **{sig.get('product_name','')}** → {sig.get('segment','')} · Send in {sig.get('send_month','')} on {sig.get('send_day','')} · {sig.get('rationale','')}")
    else:
        if st.button("Generate Sample Data"):
            exec(open(Path(__file__).parent / "p7_generate_data.py").read())
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PART 8 — DYNAMIC PRICING
# ══════════════════════════════════════════════════════════════════════════════
elif page == "p8":
    st.markdown("""
    <div class="hero" style="background:linear-gradient(135deg,#0a1628,#0f2d4a,#0a2018);color:white">
      <div class="kicker" style="color:#60a5fa">Dr. Theiss Naturwaren GmbH · Homburg</div>
      <h1 style="color:white">💶 Dynamic Pricing Agent</h1>
      <p>Weather · events · football · supply chain → signal-driven pricing within ±12% guardrail band.</p>
    </div>
    """, unsafe_allow_html=True)

    import sys; sys.path.insert(0, str(Path(__file__).parent))

    c1, c2 = st.columns([2,1])
    with c1:
        city = st.selectbox("Weather city", ["Deutschland (avg)","Hamburg","Berlin","München","Köln","Homburg (Saarland)"])
    with c2:
        target_date = st.date_input("Pricing date", value=date.today())

    @st.cache_data(ttl=900)
    def _get_decisions(city, d):
        from p8_signals import fetch_weather, upcoming_events, supply_stress
        from p8_pricing_engine import run_all
        w = fetch_weather(city)
        e = upcoming_events(date.fromisoformat(d), 21)
        return run_all(w, e), w, e

    decisions, weather, events = _get_decisions(city, target_date.isoformat())

    # Weather strip
    wc = st.columns(4)
    for col, val, lbl in [
        (wc[0], f"{weather.get('temp_max','?')}°C", f"Max · {city}"),
        (wc[1], f"{weather.get('temp_min','?')}°C", "Min"),
        (wc[2], f"{weather.get('precip_mm','?')}mm", "Rain"),
        (wc[3], f"{weather.get('forecast_7d_avg_max','?')}°C", "7d Avg"),
    ]:
        col.metric(lbl, val)

    if weather.get("source") == "synthetic_fallback":
        st.caption("⚠️ Weather API unavailable — using seasonal estimate")

    # Events
    if events:
        ev_df = pd.DataFrame(events)[["name","date","category","pricing_signal","days_away"]]
        st.dataframe(ev_df, use_container_width=True, height=160)

    # Pricing decisions
    n_up = sum(1 for d in decisions if d.direction=="increase")
    n_dn = sum(1 for d in decisions if d.direction=="decrease")
    n_ho = sum(1 for d in decisions if d.direction=="hold")
    n_gd = sum(len(d.guardrails_fired) for d in decisions)
    mc = st.columns(4)
    for col, n, lbl, col_hex in [(mc[0],n_up,"Increases","#10b981"),(mc[1],n_dn,"Decreases","#f59e0b"),
                                  (mc[2],n_ho,"Hold","#94a3b8"),(mc[3],n_gd,"Guardrails","#ef4444")]:
        col.markdown(f"""<div style="text-align:center;background:#f8fafc;border-radius:10px;padding:.8rem">
        <div style="font-size:1.6rem;font-weight:800;color:{col_hex}">{n}</div>
        <div style="font-size:.75rem;color:#64748b">{lbl}</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    show_hold = st.checkbox("Show held prices too", value=False)
    import pandas as pd
    from p8_pricing_engine import CATALOGUE

    for d in decisions:
        if not show_hold and d.direction == "hold": continue
        icon = "📈" if d.direction=="increase" else "📉" if d.direction=="decrease" else "➡️"
        border = "#10b981" if d.direction=="increase" else "#f59e0b" if d.direction=="decrease" else "#e2e8f0"
        line = CATALOGUE.get(d.sku,{}).get("line","")
        guard_html = f' <span style="background:#fee2e2;color:#991b1b;font-size:.7rem;padding:2px 7px;border-radius:8px">⚠️ {len(d.guardrails_fired)} guardrail(s)</span>' if d.guardrails_fired else ""
        st.markdown(f"""<div style="border-left:4px solid {border};background:#f8fafc;border-radius:0 8px 8px 0;
        padding:.7rem 1rem;margin-bottom:.4rem">
        <strong>{icon} {d.product_name}</strong>
        <span style="font-size:.8rem;color:#94a3b8"> · {d.sku} · {line}</span>
        {guard_html}
        <span style="float:right;font-family:monospace">
        <span style="color:#94a3b8">€{d.base_price:.2f}</span> →
        <strong>€{d.recommended_price:.2f}</strong>
        <span style="color:{'#10b981' if d.change_pct>0 else '#f59e0b'};margin-left:4px">{d.change_pct:+.1f}%</span>
        </span><br>
        <span style="font-size:.8rem;color:#374151">{d.rationale[:180]}</span>
        </div>""", unsafe_allow_html=True)

    import pandas as pd
    csv = pd.DataFrame([d.to_dict() for d in decisions]).to_csv(index=False).encode()
    st.download_button("⬇️ Export Prices CSV", csv, f"pricing_{target_date}.csv", "text/csv")

    if api_key and st.button("✍️ Generate AI Pricing Memo"):
        from p8_gemini import generate_pricing_memo
        with st.spinner("Writing memo…"):
            memo = generate_pricing_memo(weather, events[:8], [d.to_dict() for d in decisions], api_key)
        st.markdown(f"**{memo.get('executive_summary','')}**")
        if memo.get("compliance_note"):
            st.info(f"⚖️ {memo['compliance_note']}")
        if memo.get("next_review_trigger"):
            st.success(f"🔔 Next review: {memo['next_review_trigger']}")
