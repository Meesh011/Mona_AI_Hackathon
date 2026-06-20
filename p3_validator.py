"""
validator.py
Applies the agency's business rules on top of Gemini's raw extraction to
produce a final VALID / INVALID / NEEDS_REVIEW verdict with a confidence score.

This is deliberately kept separate from the LLM call: the LLM should only
extract facts off the document; deciding what counts as "a valid work permit"
is a deterministic business rule we own and can tune without re-prompting.
"""
from __future__ import annotations
from datetime import date, datetime
from dateutil import parser as dateparser

from p3_schema import ExtractedPermitData, ValidationResult

# Confidence floor below which we never auto-approve, regardless of the rest
MIN_AUTO_APPROVE_CONFIDENCE = 70.0


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return dateparser.parse(value, dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def validate(filename: str, extracted: ExtractedPermitData) -> ValidationResult:
    reasons: list[str] = []
    valid_until = _parse_date(extracted.valid_until)
    today = date.today()

    is_expired = None
    if valid_until is not None:
        is_expired = valid_until < today
    else:
        reasons.append("Could not determine an expiry date from the document.")

    # --- Rule 1: must actually be a work/residence permit ---
    if not extracted.is_work_permit:
        reasons.append("Document does not appear to be a work/residence permit.")

    # --- Rule 2: must not be expired ---
    if is_expired is True:
        reasons.append(f"Permit expired on {valid_until.isoformat()}.")

    # --- Rule 3: must explicitly permit employment ---
    if extracted.employment_permitted is False:
        reasons.append(
            "Document explicitly states employment is NOT permitted "
            f"(remarks: \"{extracted.employment_remarks_raw or 'n/a'}\")."
        )
    elif extracted.employment_permitted is None:
        reasons.append("Could not determine whether employment is permitted.")

    # --- Rule 4: low-confidence extraction or flagged tampering => human review ---
    needs_review = (
        extracted.extraction_confidence < MIN_AUTO_APPROVE_CONFIDENCE
        or bool(extracted.notes)
        or valid_until is None
        or extracted.employment_permitted is None
    )

    hard_fail = (
        not extracted.is_work_permit
        or is_expired is True
        or extracted.employment_permitted is False
    )

    if hard_fail:
        verdict = "INVALID"
    elif needs_review:
        verdict = "NEEDS_REVIEW"
    else:
        verdict = "VALID"
        reasons.append("Document is a valid, unexpired permit authorizing employment.")

    # Combine model's own extraction confidence with rule-based certainty.
    # If it's a clean hard pass/fail, we trust the extraction confidence directly.
    # If we're in NEEDS_REVIEW because of ambiguity, cap confidence to reflect that.
    confidence = extracted.extraction_confidence
    if verdict == "NEEDS_REVIEW":
        confidence = min(confidence, 60.0)

    return ValidationResult(
        filename=filename,
        verdict=verdict,
        confidence_percent=round(confidence, 1),
        is_work_permit=extracted.is_work_permit,
        valid_until=valid_until,
        is_expired=is_expired,
        employment_permitted=extracted.employment_permitted,
        reasons=reasons,
        extracted=extracted,
    )
