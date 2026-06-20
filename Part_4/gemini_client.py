"""
gemini_client.py
All Gemini 2.5 Flash calls for the CV & Certificate fraud-detection pipeline,
using the `google.generativeai` SDK.

Three jobs:
  1. parse_cv            -> CVProfile        (from CV text or image)
  2. extract_certificate -> CertificateExtraction (from a certificate image)
  3. judge_relevance     -> decide which CV claim (if any) a certificate supports,
                             using semantic understanding rather than exact string match
                             (e.g. "Master of Laws" should match a claimed "LL.M. Law degree")
"""
from __future__ import annotations
import os
import json
import copy

import google.generativeai as genai

from schema import CVProfile, CertificateExtraction

MODEL_NAME = "gemini-2.5-flash"


def _configure() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. export GEMINI_API_KEY=your_key_here")
    genai.configure(api_key=api_key)


def _clean_schema(schema: dict) -> dict:
    """
    Recursively remove keys that the old google.generativeai proto layer
    does not recognise ('default', 'title', 'examples', 'exclusiveMinimum', etc.)
    and flatten anyOf/allOf wrappers used by Pydantic for Optional fields so
    that the proto serialiser doesn't choke on them.
    """
    UNSUPPORTED = {"default", "title", "examples", "exclusiveMinimum",
                   "exclusiveMaximum", "minimum", "maximum", "minLength",
                   "maxLength", "minItems", "maxItems", "pattern",
                   "contentEncoding", "contentMediaType", "const"}

    def _clean(obj):
        if isinstance(obj, list):
            return [_clean(v) for v in obj]
        if not isinstance(obj, dict):
            return obj

        # Flatten Optional[X]  ->  anyOf: [{type: X}, {type: null}]
        # The proto only understands a single type string, so we pick the
        # non-null branch and add nullable=True.
        if "anyOf" in obj:
            non_null = [b for b in obj["anyOf"] if b.get("type") != "null"]
            if non_null:
                merged = copy.deepcopy(non_null[0])
                merged["nullable"] = True
                # carry over description/other siblings
                for k, v in obj.items():
                    if k not in ("anyOf",) and k not in merged:
                        merged[k] = v
                return _clean(merged)

        cleaned = {}
        for k, v in obj.items():
            if k in UNSUPPORTED:
                continue
            cleaned[k] = _clean(v)
        return cleaned

    return _clean(schema)


def _schema_dict(model_class) -> dict:
    """Return a proto-safe JSON schema dict for a Pydantic model."""
    raw = model_class.model_json_schema()
    # Inline $defs so there are no $ref pointers
    defs = raw.pop("$defs", {})

    def _resolve_refs(obj):
        if isinstance(obj, list):
            return [_resolve_refs(v) for v in obj]
        if not isinstance(obj, dict):
            return obj
        if "$ref" in obj:
            ref_name = obj["$ref"].split("/")[-1]
            return _resolve_refs(copy.deepcopy(defs.get(ref_name, obj)))
        return {k: _resolve_refs(v) for k, v in obj.items()}

    resolved = _resolve_refs(raw)
    return _clean_schema(resolved)


# ---------------------------------------------------------------------------
# 1. CV parsing
# ---------------------------------------------------------------------------

CV_SYSTEM_PROMPT = """\
You extract structured claims from a candidate's CV/resume for an HR staffing
agency. Extract ONLY what the candidate explicitly states. Do not infer skills
that aren't mentioned. List claimed education, claimed certifications, claimed
skills, and claimed job titles separately.

Also note in `notes` if the CV reads as generic/templated, has suspiciously
vague descriptions with no concrete details (dates, employers, deliverables),
or has internal timeline inconsistencies -- common red flags of fabricated or
AI-generated CVs. This is an observation for a human reviewer, not a verdict.
"""


def parse_cv_from_text(cv_text: str) -> CVProfile:
    _configure()
    model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=CV_SYSTEM_PROMPT)
    response = model.generate_content(
        [f"Here is the CV text:\n\n{cv_text}"],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=_schema_dict(CVProfile),
            temperature=0.0,
        ),
    )
    return CVProfile.model_validate_json(response.text)


def parse_cv_from_image(image_bytes: bytes, mime_type: str = "image/png") -> CVProfile:
    _configure()
    model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=CV_SYSTEM_PROMPT)
    response = model.generate_content(
        [
            {"mime_type": mime_type, "data": image_bytes},
            "This image is a candidate's CV. Extract their claims.",
        ],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=_schema_dict(CVProfile),
            temperature=0.0,
        ),
    )
    return CVProfile.model_validate_json(response.text)


# ---------------------------------------------------------------------------
# 2. Certificate extraction
# ---------------------------------------------------------------------------

CERT_SYSTEM_PROMPT = """\
You are a document-verification assistant for an HR/staffing agency screening
candidate-submitted certificates, diplomas, and licenses for fraud.

Extract exactly what is printed on the document. Do not guess missing values --
return null instead. Critically assess:

- Is this even a PERSONAL qualification document (degree, professional
  certificate, training completion certificate) belonging to a named
  individual? Company licenses, permits issued to a business/organization, or
  documents unrelated to personal qualifications are NOT personal qualification
  documents, even if they look official.
- Be skeptical of filenames or surrounding context -- judge only the actual
  printed content. A document that LOOKS like it's about one topic from a
  filename might actually be about something else entirely once read.
- Watch for word-level traps: an institution or business name that happens to
  contain a common word (e.g. a company surname that looks like a profession
  or trade) is not evidence the document relates to that trade.
- Note any visual red flags: mismatched fonts/sizes, signatures/seals that
  look pasted in, inconsistent date formats, anachronistic logos, or text
  that looks digitally altered.
- If the document states a validity/expiry date, extract it. If the document
  type inherently does not expire (most academic degrees), leave valid_until
  null and do not treat that as a red flag.

Respond using the provided JSON schema only.
"""


def extract_certificate(image_bytes: bytes, mime_type: str = "image/png") -> CertificateExtraction:
    _configure()
    model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=CERT_SYSTEM_PROMPT)
    response = model.generate_content(
        [
            {"mime_type": mime_type, "data": image_bytes},
            "Analyze this certificate/document image and extract the requested fields.",
        ],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=_schema_dict(CertificateExtraction),
            temperature=0.0,
        ),
    )
    return CertificateExtraction.model_validate_json(response.text)


# ---------------------------------------------------------------------------
# 3. Semantic relevance matching (CV claim <-> certificate)
# ---------------------------------------------------------------------------

RELEVANCE_SYSTEM_PROMPT = """\
You compare ONE extracted certificate against a candidate's CV claims (education,
certifications, skills, job titles) and decide whether the certificate provides
genuine supporting evidence for any specific claim.

Respond ONLY with a JSON object of the exact shape:
{"matched_claim": "<the exact claim text it supports, or null>",
 "rationale": "<one sentence>"}

A match requires real semantic equivalence (e.g. a printed 'Master of Laws
(LL.M.)' degree DOES match a claimed 'LL.M. in Law'; a driving-school
accreditation issued to a company does NOT match a claimed 'culinary
training' just because the company name contains an unrelated word). If
nothing on the CV corresponds to what the certificate actually certifies,
matched_claim must be null.
"""


def judge_relevance(cv_profile: CVProfile, cert: CertificateExtraction) -> tuple[str | None, str]:
    _configure()
    model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=RELEVANCE_SYSTEM_PROMPT)

    payload = {
        "cv_claims": {
            "education": [e.model_dump() for e in cv_profile.claimed_education],
            "certifications": [c.model_dump() for c in cv_profile.claimed_certifications],
            "skills": cv_profile.claimed_skills,
            "job_titles": cv_profile.claimed_job_titles,
        },
        "certificate": {
            "qualification_title": cert.qualification_title,
            "field_of_study_or_topic": cert.field_of_study_or_topic,
            "issuing_institution": cert.issuing_institution,
            "document_category": cert.document_category,
        },
    }

    response = model.generate_content(
        [json.dumps(payload, ensure_ascii=False)],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )
    try:
        data = json.loads(response.text)
        return data.get("matched_claim"), data.get("rationale", "")
    except (json.JSONDecodeError, AttributeError):
        return None, "Could not parse relevance judgement."
