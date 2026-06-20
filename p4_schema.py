"""
schema.py
Data models for the CV & Certificate fraud-detection pipeline.

Pipeline shape:
  CV (text/PDF)  --Gemini-->  CVProfile (structured claims)
  Certificate img --Gemini--> CertificateExtraction (structured facts on the doc)
  CVProfile + CertificateExtraction --rules + Gemini--> CertificateAssessment
  all CertificateAssessments --rules--> CandidateReport (overall trust signal)
"""
from __future__ import annotations
from datetime import date
from typing import Optional, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# CV side
# ---------------------------------------------------------------------------

class ClaimedEducation(BaseModel):
    degree: Optional[str] = None
    field: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None


class ClaimedCertification(BaseModel):
    title: Optional[str] = None
    issuer: Optional[str] = None
    year: Optional[str] = None


class CVProfile(BaseModel):
    """What the candidate claims about themselves, extracted from their CV."""

    full_name: Optional[str] = Field(default=None, description="Candidate's full name as written on the CV")
    claimed_skills: list[str] = Field(default_factory=list)
    claimed_education: list[ClaimedEducation] = Field(default_factory=list)
    claimed_certifications: list[ClaimedCertification] = Field(default_factory=list)
    claimed_job_titles: list[str] = Field(default_factory=list, description="Past/current job titles claimed")
    notes: Optional[str] = Field(
        default=None,
        description="Anything notable about the CV itself: generic/templated AI-sounding "
        "phrasing, inconsistent timelines, vague descriptions with no specifics, etc.",
    )


# ---------------------------------------------------------------------------
# Certificate side
# ---------------------------------------------------------------------------

DocCategory = Literal[
    "academic_degree",
    "professional_certification",
    "training_accreditation",
    "license_or_permit",
    "other_personal_document",
    "unrelated_or_not_a_certificate",
]


class CertificateExtraction(BaseModel):
    is_personal_qualification_document: bool = Field(
        description="True if this document certifies a SKILL/QUALIFICATION belonging to "
        "an individual person (degree, professional cert, training completion). False if "
        "it's a company license, an unrelated document, or not legible enough to tell."
    )
    document_category: DocCategory
    holder_name: Optional[str] = Field(default=None, description="The named individual on the document, if any")
    issuing_institution: Optional[str] = None
    qualification_title: Optional[str] = Field(
        default=None, description="The degree/certificate/qualification title as printed, verbatim"
    )
    field_of_study_or_topic: Optional[str] = None
    date_issued: Optional[str] = Field(default=None, description="ISO YYYY-MM-DD if determinable")
    valid_until: Optional[str] = Field(
        default=None,
        description="ISO YYYY-MM-DD expiry date if the document states one. Null if the "
        "document type doesn't expire (e.g. most academic degrees, many course-completion certs).",
    )
    grade_or_result: Optional[str] = None
    authenticity_red_flags: list[str] = Field(
        default_factory=list,
        description="Concrete visual/textual inconsistencies noticed: mismatched fonts, "
        "implausible seal/signature, wrong-looking institution name, dates that don't "
        "make sense, text that looks digitally inserted/edited, etc. Empty list if none.",
    )
    extraction_confidence: float = Field(ge=0, le=100)


# ---------------------------------------------------------------------------
# Combined assessment
# ---------------------------------------------------------------------------

Verdict = Literal[
    "AUTHENTIC_AND_RELEVANT",   # matches a CV claim, name matches, not expired, no red flags
    "AUTHENTIC_BUT_UNRELATED",  # looks like a real personal cert, but doesn't match any CV claim
    "NAME_MISMATCH",            # holder name doesn't match candidate
    "EXPIRED",                  # past validity date
    "NOT_A_PERSONAL_CERTIFICATE",  # e.g. a company license, irrelevant document
    "SUSPICIOUS",               # red flags raised, low confidence, or inconsistent
]


class CertificateAssessment(BaseModel):
    filename: str
    verdict: Verdict
    confidence_percent: float
    name_match: Optional[bool] = None
    matched_cv_claim: Optional[str] = Field(
        default=None, description="Which CV claim (skill/education/certification) this document supports, if any"
    )
    is_expired: Optional[bool] = None
    valid_until: Optional[date] = None
    reasons: list[str] = Field(default_factory=list)
    extracted: CertificateExtraction


class CandidateReport(BaseModel):
    candidate_name: Optional[str]
    overall_trust_score: float = Field(ge=0, le=100)
    overall_flag: Literal["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"]
    unsupported_claims: list[str] = Field(
        default_factory=list, description="CV claims with no supporting certificate"
    )
    assessments: list[CertificateAssessment]
    summary: str
