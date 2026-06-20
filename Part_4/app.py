"""
app.py
Streamlit demo UI for the hackathon presentation.

Run with:
    export GEMINI_API_KEY=your_key_here
    streamlit run app.py
"""
from __future__ import annotations
from pathlib import Path
import tempfile

import streamlit as st

from file_utils import to_image_bytes
from pipeline import load_cv
from gemini_client import extract_certificate
from cross_check import assess_certificate, build_candidate_report

st.set_page_config(page_title="CV & Certificate Fraud Check", page_icon="🕵️", layout="centered")

st.title("🕵️ CV & Certificate Validator")
st.caption(
    "Persowerk Deutschland GmbH — checks whether submitted certificates actually "
    "belong to the candidate and actually support what their CV claims. "
    "No LinkedIn scraping, no web search — pure document analysis."
)

cv_file = st.file_uploader("Candidate CV (PDF)", type=["pdf"])
cert_files = st.file_uploader(
    "Certificates / diplomas / licenses (images or PDFs)",
    type=["pdf", "png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
)

VERDICT_STYLE = {
    "AUTHENTIC_AND_RELEVANT": ("✅", "success"),
    "AUTHENTIC_BUT_UNRELATED": ("ℹ️", "info"),
    "NAME_MISMATCH": ("🚫", "error"),
    "EXPIRED": ("⌛", "warning"),
    "NOT_A_PERSONAL_CERTIFICATE": ("❓", "warning"),
    "SUSPICIOUS": ("⚠️", "error"),
}

if st.button("Run validation", disabled=not (cv_file and cert_files)):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cv_path = tmp / cv_file.name
        cv_path.write_bytes(cv_file.getbuffer())

        with st.spinner("Reading CV..."):
            cv_profile = load_cv(cv_path)

        st.subheader("📄 What the CV claims")
        st.json(cv_profile.model_dump())

        assessments = []
        for cf in cert_files:
            cert_path = tmp / cf.name
            cert_path.write_bytes(cf.getbuffer())

            with st.spinner(f"Analyzing {cf.name}..."):
                img = to_image_bytes(cert_path)
                extraction = extract_certificate(img)
                assessment = assess_certificate(cf.name, cv_profile, extraction)
                assessments.append(assessment)

            icon, style = VERDICT_STYLE.get(assessment.verdict, ("❔", "info"))
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(img, use_container_width=True)
                with col2:
                    getattr(st, style)(f"{icon} **{assessment.verdict}**  ({assessment.confidence_percent:.0f}% confidence)")
                    st.write(f"**Holder on document:** {assessment.extracted.holder_name or '—'}")
                    st.write(f"**Qualification:** {assessment.extracted.qualification_title or '—'}")
                    st.write(f"**Valid until:** {assessment.valid_until.isoformat() if assessment.valid_until else '—'}")
                    for r in assessment.reasons:
                        st.write(f"- {r}")

        report = build_candidate_report(cv_profile, assessments)

        st.subheader("🧾 Overall candidate report")
        risk_color = {"LOW_RISK": "success", "MEDIUM_RISK": "warning", "HIGH_RISK": "error"}[report.overall_flag]
        getattr(st, risk_color)(
            f"**{report.overall_flag}** — trust score: {report.overall_trust_score:.0f}/100"
        )
        st.write(report.summary)
        if report.unsupported_claims:
            st.write("**Claims with no supporting document found:**")
            for c in report.unsupported_claims:
                st.write(f"- {c}")
