# CV & Certificate Validator (Hackathon Solution)

For Persowerk Deutschland GmbH — detects misrepresented experience/skills and
verifies that submitted certificates are genuine, current, and actually
belong to the candidate. **No LinkedIn scraping, no web search** — this is
pure document analysis + cross-referencing, exactly as scoped.

## The actual problem (confirmed against your sample files)

The interesting fraud cases in your 5 sample certificates aren't "is this
PDF obviously fake" — they're more subtle, and this pipeline is built
specifically to catch them:

| File | What it actually is | Why it matters |
|---|---|---|
| `zeugnis-master_ecfb.jpg` | Genuine M.A. degree, Saarland Uni | Clean match case |
| `bachelor_zertifikat.jpg` | Actually an **LL.M. (Master)**, not a Bachelor | Filename/claim says one thing, document says another |
| `zertifikat_koch_ausbildung.jpg` | A **driving-school accreditation** for a company literally named "Koch GmbH" — nothing to do with cooking, and it **expired in 2012** | Word-trap (Koch = surname, not "cook") + silently expired |
| `lizenz_seczruty.jpg` | A **corporate EU cash-transport license**, not a personal document at all | Not a qualification document, regardless of how official it looks |
| ISACA certificate | Genuine course-completion cert, no expiry by design | Shouldn't be flagged "no expiry date" as a red flag |

This is why the pipeline never just asks "is this real" — it asks three
separate questions per document: **(1) is this actually a personal
qualification document, (2) does the name on it match the candidate, (3) does
what it certifies match something the candidate actually claimed.**

## Architecture

```
CV file ──────────────► Gemini: parse_cv ─────► CVProfile (claims)
                                                     │
Certificate image(s) ─► Gemini: extract_certificate │
                            │                        │
                            ▼                        ▼
                     CertificateExtraction ──► cross_check.assess_certificate()
                            │                  (name match, expiry, red flags,
                            │                   then Gemini: judge_relevance for
                            │                   semantic claim-matching)
                            ▼
                  CertificateAssessment (per file)
                            │
                            ▼
                  CandidateReport (overall trust score + flag)
```

Same design philosophy as the work-permit task: **Gemini only extracts facts
and makes semantic judgments it's actually good at (reading documents,
matching meaning); a plain Python `cross_check.py` owns the actual fraud
rules** so you can explain/tune the decision logic without touching prompts.

## Per-certificate verdicts

- `AUTHENTIC_AND_RELEVANT` — genuine, current, matches a specific CV claim
- `AUTHENTIC_BUT_UNRELATED` — looks like a real personal certificate, but
  nothing on the CV corresponds to it (not necessarily fraud — just doesn't
  add evidence)
- `NAME_MISMATCH` — holder name on the document doesn't match the candidate
- `EXPIRED` — past its stated validity date
- `NOT_A_PERSONAL_CERTIFICATE` — e.g. a company license, or unrelated document
- `SUSPICIOUS` — visual/textual red flags noticed, or extraction confidence
  too low to trust

## Candidate-level trust score

`cross_check.build_candidate_report()` aggregates all assessments into a
0–100 trust score and a `LOW_RISK` / `MEDIUM_RISK` / `HIGH_RISK` flag, and
separately lists any CV claims (a degree, a certification) that **no
submitted document supports at all** — often the most useful single
signal for a recruiter.

## Setup

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
```

## Run — CLI

```bash
python main.py path/to/candidate_cv.pdf path/to/certificates_folder/
```

Prints the full JSON report and saves it to `candidate_report.json`.

> Note: the CV is expected as a single PDF. If you only have a CV as plain
> text, drop it into a quick PDF, or call `gemini_client.parse_cv_from_text()`
> directly from a script.

## Run — demo UI

```bash
streamlit run app.py
```

Upload the CV + all certificate images/PDFs, click "Run validation", and you
get a card per certificate plus the overall trust score — good for a live
hackathon demo since judges can watch each document get judged individually.

## Files

| File | Purpose |
|---|---|
| `file_utils.py` | PDF/image → PNG bytes, and text extraction for digital-text CVs |
| `schema.py` | All Pydantic models: CV claims, certificate extraction, assessments, report |
| `gemini_client.py` | The three Gemini calls: parse CV, extract certificate, judge semantic relevance |
| `cross_check.py` | Deterministic fraud rules: name matching, expiry, red flags, scoring |
| `pipeline.py` | Wires it all together for a CV + folder of certificates |
| `main.py` | CLI entrypoint |
| `app.py` | Streamlit demo UI |

## Tuning knobs (good talking points for judges)

- `NAME_MATCH_THRESHOLD` in `cross_check.py` — fuzzy-match strictness on names
  (handles minor OCR noise/middle-name differences without being naive)
- `MIN_CONFIDENT_EXTRACTION` — below this, a document is routed to
  `SUSPICIOUS` for human review instead of being auto-trusted
- Risk-point weights in `build_candidate_report()` — currently name mismatch
  is weighted heaviest (35pts), since that's the single strongest fraud signal
- `judge_relevance()` is intentionally a separate Gemini call from extraction,
  so you can swap in a cheaper/faster matching strategy later without
  re-touching the extraction prompt

## What you'd add for production

- Persist every assessment + the original image (audit trail / compliance)
- Human-in-the-loop review queue for `SUSPICIOUS` and `NAME_MISMATCH` verdicts
- OCR-level forensics (font/DPI analysis, metadata inspection) as a second
  signal alongside the vision model's own red-flag noticing
- Issuer-format allowlist (e.g. known templates from major German
  universities/chambers) to catch fabricated institutions, still without
  needing live web lookups
