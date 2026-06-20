"""
pipeline.py
Top-level orchestration: CV + folder of certificates -> CandidateReport.
"""
from __future__ import annotations
from pathlib import Path

from file_utils import to_image_bytes, extract_text_if_possible
from gemini_client import parse_cv_from_text, parse_cv_from_image, extract_certificate
from cross_check import assess_certificate, build_candidate_report
from schema import CandidateReport

ACCEPTED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


def load_cv(cv_path: str | Path):
    path = Path(cv_path)
    text = extract_text_if_possible(path)
    if text:
        return parse_cv_from_text(text)
    # scanned CV or image -> go multimodal
    return parse_cv_from_image(to_image_bytes(path))


def run_pipeline(cv_path: str | Path, cert_dir: str | Path) -> CandidateReport:
    cv_profile = load_cv(cv_path)

    cert_dir = Path(cert_dir)
    cert_files = sorted(p for p in cert_dir.iterdir() if p.suffix.lower() in ACCEPTED_EXTS)

    assessments = []
    for f in cert_files:
        image_bytes = to_image_bytes(f)
        extraction = extract_certificate(image_bytes)
        assessment = assess_certificate(f.name, cv_profile, extraction)
        assessments.append(assessment)

    return build_candidate_report(cv_profile, assessments)
