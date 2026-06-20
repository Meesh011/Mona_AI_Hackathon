import os
import json
import google.generativeai as genai

from schema import ExtractedPermitData

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a document analysis expert specializing in work permits and residence documents.
Your task is to extract structured data from document images.

You MUST always respond with a valid JSON object that exactly matches the required schema.
Never omit required fields. Never add markdown formatting or code fences — return raw JSON only.

Required fields that must ALWAYS be present in your response:
- is_work_permit (boolean): True only if the document is a genuine work/residence permit
- extraction_confidence (float, 0-100): your confidence in the overall extraction quality

All other fields are optional and should be null if not determinable from the document."""

USER_PROMPT = """Analyze this document image and extract all permit-related information.

Return a JSON object with these fields:
{
  "is_work_permit": <true|false>,
  "document_type": <string or null>,
  "full_name": <string or null>,
  "nationality": <string or null>,
  "document_number": <string or null>,
  "date_of_issue": <"YYYY-MM-DD" or null>,
  "valid_until": <"YYYY-MM-DD" or null>,
  "employment_permitted": <true|false|null>,
  "employment_remarks_raw": <string or null>,
  "issuing_authority": <string or null>,
  "extraction_confidence": <float 0-100>,
  "notes": <string or null>
}

Rules:
- Set is_work_permit=true only for genuine work/residence permits (Aufenthaltserlaubnis, Blaue Karte EU, work visa, etc.)
- Set is_work_permit=false for passports, ID cards, payslips, or unreadable images
- extraction_confidence: 90-100 for clear complete docs, 60-89 for minor issues, 30-59 for partial/unclear, 0-29 for unreadable
- employment_permitted=true if remarks say employment IS allowed, false if explicitly NOT permitted, null if unclear
- Note any red flags (tampering, inconsistent fonts, missing security features) in the notes field
- Return ONLY the JSON object, no other text"""

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    MODEL_NAME,
    system_instruction=SYSTEM_PROMPT,
)


def extract_permit_data(image_bytes: bytes) -> ExtractedPermitData:

    prompt = [
        USER_PROMPT,
        {
            "mime_type": "image/png",
            "data": image_bytes,
        },
    ]

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    # Strip markdown code fences if Gemini wraps the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)

    return ExtractedPermitData(**data)