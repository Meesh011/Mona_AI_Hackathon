# Work Permit Validator (Hackathon Solution)

For Leistenschneider Personaldienstleistungen GmbH — automated first-pass
validation of candidate work/residence permits.

## What it does

Given a permit document (PDF or photo), the agent:

1. Renders the document as an image.
2. Sends it to **Gemini 2.5 Flash** with a structured JSON schema, asking it
   to extract: document type, name, dates, issuing authority, and — critically —
   whether the remarks field says employment **is** or **is not** permitted.
3. Applies deterministic business rules on top of the extraction:
   - Is it actually a work/residence permit? (vs. a passport, ID, or junk file)
   - Has it expired (`valid_until` < today)?
   - Does it explicitly permit employment? (study permits, for example, often
     say "Employment not permitted" — a permit can be 100% genuine and
     unexpired and still not authorize the holder to work)
4. Returns a verdict: **VALID / INVALID / NEEDS_REVIEW**, a confidence
   percentage, and the expiry date, plus the reasons behind the call.

This split matters: the LLM only extracts facts off the page (which it's
good at), and a plain Python function decides what "valid" means (which you
can tune/audit without touching prompts).

## Why VALID / INVALID / NEEDS_REVIEW (not just yes/no)

A binary "is this valid" hides exactly the cases a human should look at: low
scan quality, missing date, ambiguous remarks, or anything Gemini itself
flagged as suspicious (`notes` field). Those go to `NEEDS_REVIEW` instead of
being silently auto-approved or auto-rejected.

## Setup

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
```

## Run — CLI (batch or single file)

```bash
python main.py path/to/permit.pdf
python main.py path/to/folder_of_permits/      # processes every file in the folder
```

Outputs a JSON result per file to stdout, and a combined `results.json`.

## Run — demo UI

```bash
streamlit run app.py
```

Upload a file, see the extracted image, fields, verdict, and confidence score.

## Files

| File              | Purpose                                                          |
|-------------------|-------------------------------------------------------------------|
| `pdf_utils.py`    | Converts PDF/image input into PNG bytes for the multimodal model |
| `schema.py`       | Pydantic models: what we extract, and the final verdict shape    |
| `gemini_client.py`| The actual Gemini 2.5 Flash call with JSON-schema structured output |
| `validator.py`    | Business rules → VALID/INVALID/NEEDS_REVIEW + confidence         |
| `main.py`         | CLI entrypoint for single files or batches                       |
| `app.py`          | Streamlit demo UI                                                 |

## Tested against your sample set

Your 4 sample PDFs map cleanly onto these rules:

- `permit_wp_valid_01.pdf` — Aufenthaltserlaubnis, valid until 2027, "Beschäftigung gestattet" → **VALID**
- `permit_wp_valid_02.pdf` — Blaue Karte EU, valid until 2028, employment permitted → **VALID**
- `permit_wp_invalid_01.pdf` — valid until 2024 → already **expired** → **INVALID**
- `permit_wp_invalid_02.pdf` — study permit, "Employment not permitted" → **INVALID**

## Notes / things to mention in your pitch

- Currently single-page-first-image only; `pdf_utils.file_to_images` already
  supports multi-page docs if you want to also check a back page later.
- `MIN_AUTO_APPROVE_CONFIDENCE` in `validator.py` is your tunable knob for how
  conservative the auto-approval is — raise it if you want more human review,
  lower it if you trust the model more.
- For a production version you'd add: persistent storage/audit log of every
  decision (for compliance), retry/backoff on the Gemini call, and probably a
  second-pass OCR cross-check on the date field since that's the single most
  consequential extracted value.
