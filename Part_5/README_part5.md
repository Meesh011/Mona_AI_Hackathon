# Problem 5 — Interview Support Agent

Streamlit app for non-technical hiring managers (Kohlpharma / Jobs&Joy use case).

## Setup

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
streamlit run app.py
```

Or enter the API key directly in the sidebar when the app opens.

## Usage

1. Paste a job offer into the text area (use the sample PDFs from `problem5_job_offers.pdf`)
2. Adjust number of questions and focus areas
3. Click **Generate Interview Guide**
4. Review:
   - **Role summary** in plain English
   - **Questions** grouped by category (Technical / Behavioral / Situational / Culture Fit / Red Flag Probe)
   - Each question includes *why we ask* and *what a good answer looks like*
   - **Red flags** with severity levels (High / Medium / Low)
5. Download the full guide as JSON

## Sample job offers (from the PDF)

- **Hiring Manager — People & Talent** (MONA AI GmbH)
- **Go-to-Market Engineer** (MONA AI GmbH)
- **Forward Deployed Engineer** (MONA AI GmbH)
