"""
cross_check.py
Deterministic rules layered on top of the LLM extractions. Kept separate from
the prompts so the fraud-decision logic is auditable/tunable without touching
Gemini calls.
"""
from __future__ import annotations
from datetime import date

from dateutil import parser as dateparser
from rapidfuzz import fuzz

from schema import CVProfile, CertificateExtraction, CertificateAssessment, CandidateReport
from gemini_client import judge_relevance

NAME_MATCH_THRESHOLD = 78  # rapidfuzz token_sort_ratio, 0-100
MIN_CONFIDENT_EXTRACTION = 65.0


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return dateparser.parse(value, dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def names_match(cv_name: str | None, cert_name: str | None) -> bool | None:
    if not cv_name or not cert_name:
        return None
    score = fuzz.token_sort_ratio(cv_name.lower(), cert_name.lower())
    return score >= NAME_MATCH_THRESHOLD


def assess_certificate(
    filename: str, cv_profile: CVProfile, cert: CertificateExtraction
) -> CertificateAssessment:
    reasons: list[str] = []
    valid_until = _parse_date(cert.valid_until)
    is_expired = (valid_until < date.today()) if valid_until else None

    name_match = names_match(cv_profile.full_name, cert.holder_name)

    # --- Hard gate: not a personal qualification document at all ---
    if not cert.is_personal_qualification_document or cert.document_category in (
        "license_or_permit",
        "unrelated_or_not_a_certificate",
    ):
        reasons.append(
            f"Document is classified as '{cert.document_category}', not a personal "
            "qualification document, even if it looks official."
        )
        return CertificateAssessment(
            filename=filename,
            verdict="NOT_A_PERSONAL_CERTIFICATE",
            confidence_percent=cert.extraction_confidence,
            name_match=name_match,
            is_expired=is_expired,
            valid_until=valid_until,
            reasons=reasons,
            extracted=cert,
        )

    # --- Name check ---
    if name_match is False:
        reasons.append(
            f"Holder name on document ('{cert.holder_name}') does not match candidate "
            f"name on CV ('{cv_profile.full_name}')."
        )
        return CertificateAssessment(
            filename=filename,
            verdict="NAME_MISMATCH",
            confidence_percent=cert.extraction_confidence,
            name_match=False,
            is_expired=is_expired,
            valid_until=valid_until,
            reasons=reasons,
            extracted=cert,
        )
    if name_match is None:
        reasons.append("Could not confirm holder name matches candidate (missing on one side).")

    # --- Expiry check ---
    if is_expired:
        reasons.append(f"Certificate expired on {valid_until.isoformat()}.")
        return CertificateAssessment(
            filename=filename,
            verdict="EXPIRED",
            confidence_percent=cert.extraction_confidence,
            name_match=name_match,
            is_expired=True,
            valid_until=valid_until,
            reasons=reasons,
            extracted=cert,
        )

    # --- Red flags / low confidence => suspicious ---
    if cert.authenticity_red_flags or cert.extraction_confidence < MIN_CONFIDENT_EXTRACTION:
        reasons.extend(cert.authenticity_red_flags)
        if cert.extraction_confidence < MIN_CONFIDENT_EXTRACTION:
            reasons.append("Low extraction confidence -- recommend manual review of original document.")
        return CertificateAssessment(
            filename=filename,
            verdict="SUSPICIOUS",
            confidence_percent=cert.extraction_confidence,
            name_match=name_match,
            is_expired=is_expired,
            valid_until=valid_until,
            reasons=reasons,
            extracted=cert,
        )

    # --- Relevance to CV claims (semantic, via Gemini) ---
    matched_claim, rationale = judge_relevance(cv_profile, cert)
    if matched_claim:
        reasons.append(f"Supports claimed: '{matched_claim}'. {rationale}".strip())
        verdict = "AUTHENTIC_AND_RELEVANT"
    else:
        reasons.append(
            "Certificate appears genuine but does not correspond to any specific "
            f"claim on the CV. {rationale}".strip()
        )
        verdict = "AUTHENTIC_BUT_UNRELATED"

    return CertificateAssessment(
        filename=filename,
        verdict=verdict,
        confidence_percent=cert.extraction_confidence,
        name_match=name_match,
        matched_cv_claim=matched_claim,
        is_expired=is_expired,
        valid_until=valid_until,
        reasons=reasons,
        extracted=cert,
    )


def build_candidate_report(cv_profile: CVProfile, assessments: list[CertificateAssessment]) -> CandidateReport:
    all_claims = (
        [e.degree or "" for e in cv_profile.claimed_education]
        + [c.title or "" for c in cv_profile.claimed_certifications]
    )
    matched = {a.matched_cv_claim for a in assessments if a.matched_cv_claim}
    unsupported = [c for c in all_claims if c and c not in matched]

    risk_points = 0
    for a in assessments:
        if a.verdict == "NAME_MISMATCH":
            risk_points += 35
        elif a.verdict == "SUSPICIOUS":
            risk_points += 25
        elif a.verdict == "NOT_A_PERSONAL_CERTIFICATE":
            risk_points += 10
        elif a.verdict == "EXPIRED":
            risk_points += 8
        elif a.verdict == "AUTHENTIC_BUT_UNRELATED":
            risk_points += 3

    risk_points += min(len(unsupported) * 5, 20)

    trust_score = max(0.0, 100.0 - risk_points)
    if trust_score >= 75:
        flag = "LOW_RISK"
    elif trust_score >= 45:
        flag = "MEDIUM_RISK"
    else:
        flag = "HIGH_RISK"

    summary_bits = [f"{a.filename}: {a.verdict}" for a in assessments]
    summary = (
        f"{len(assessments)} document(s) reviewed. " + "; ".join(summary_bits) +
        (f". Unsupported CV claims: {', '.join(unsupported)}." if unsupported else "")
    )

    return CandidateReport(
        candidate_name=cv_profile.full_name,
        overall_trust_score=round(trust_score, 1),
        overall_flag=flag,
        unsupported_claims=unsupported,
        assessments=assessments,
        summary=summary,
    )
