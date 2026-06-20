"""
schema.py
Pydantic models describing the structured data we ask Gemini to extract,
and the final verdict we compute on top of it.
"""
from __future__ import annotations
from datetime import date
from typing import Optional, Literal

from pydantic import BaseModel, Field


class ExtractedPermitData(BaseModel):
    """Raw fields Gemini extracts straight from the document image."""

    is_work_permit: bool = Field(
        description="True only if the document is a genuine-looking work/residence "
        "permit (e.g. Aufenthaltserlaubnis, Blaue Karte EU, work visa, etc.). "
        "False for passports, ID cards, payslips, random documents, or unreadable images."
    )
    document_type: Optional[str] = Field(
        default=None,
        description="The permit type/category as printed on the document, e.g. "
        "'Aufenthaltserlaubnis', 'Blaue Karte EU', 'Niederlassungserlaubnis'.",
    )
    full_name: Optional[str] = Field(default=None, description="Holder's full name")
    nationality: Optional[str] = Field(default=None)
    document_number: Optional[str] = Field(default=None)
    date_of_issue: Optional[str] = Field(
        default=None, description="ISO format YYYY-MM-DD if determinable, else null"
    )
    valid_until: Optional[str] = Field(
        default=None,
        description="The expiry / 'Gültig bis' date, ISO format YYYY-MM-DD if "
        "determinable, else null.",
    )
    employment_permitted: Optional[bool] = Field(
        default=None,
        description="True if the remarks/Nebenbestimmungen field says employment "
        "is allowed (e.g. 'Erwerbstätigkeit gestattet', 'Beschäftigung gestattet'). "
        "False if it explicitly says employment is NOT permitted. Null if unclear.",
    )
    employment_remarks_raw: Optional[str] = Field(
        default=None, description="The raw remarks text as printed, verbatim."
    )
    issuing_authority: Optional[str] = Field(default=None)
    extraction_confidence: float = Field(
        ge=0, le=100,
        description="0-100: how confident the model is in the overall extraction "
        "(legibility, completeness, internal consistency of the document).",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Any red flags noticed: tampering signs, inconsistent fonts/dates, "
        "missing security features, mismatched fields, OCR artifacts that look like "
        "alterations, etc.",
    )


class ValidationResult(BaseModel):
    """Final verdict combining Gemini's extraction with our business rules."""

    filename: str
    verdict: Literal["VALID", "INVALID", "NEEDS_REVIEW"]
    confidence_percent: float
    is_work_permit: bool
    valid_until: Optional[date]
    is_expired: Optional[bool]
    employment_permitted: Optional[bool]
    reasons: list[str]
    extracted: ExtractedPermitData
