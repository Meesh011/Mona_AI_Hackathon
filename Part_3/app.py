from __future__ import annotations

import os
import tempfile
import streamlit as st

from pdf_utils import file_to_images
from gemini_client import extract_permit_data
from validator import validate

st.set_page_config(
    page_title="Work Permit Validator",
    page_icon="🛂",
    layout="centered"
)

st.title("🛂 Work Permit Validator")

st.caption(
    "Leistenschneider Personaldienstleistungen GmbH — automated first-pass validation "
    "of candidate work permits using Gemini 2.5 Flash."
)

uploaded = st.file_uploader(
    "Upload Work Permit",
    type=["pdf", "png", "jpg", "jpeg", "webp"]
)

VERDICT_STYLE = {
    "VALID": ("✅", "success"),
    "INVALID": ("❌", "error"),
    "NEEDS_REVIEW": ("⚠️", "warning"),
}

if uploaded is not None:

    suffix = os.path.splitext(uploaded.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded.getvalue())
        pdf_path = tmp_file.name

    with st.spinner("Analyzing document..."):

        images = file_to_images(pdf_path)

        st.image(
            images[0],
            caption="Uploaded document",
            use_container_width=True
        )

        extracted = extract_permit_data(images[0])

        result = validate(uploaded.name, extracted)

    icon, style = VERDICT_STYLE.get(result.verdict, ("❔", "info"))
    getattr(st, style)(
        f"{icon} **{result.verdict}** — Confidence: {result.confidence_percent:.0f}%"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Is Work Permit?",
            "Yes" if result.is_work_permit else "No"
        )

        st.metric(
            "Employment Permitted",
            "Yes" if result.employment_permitted else "No"
        )

    with col2:
        st.metric(
            "Valid Until",
            result.valid_until.isoformat() if result.valid_until else "Unknown"
        )

        st.metric(
            "Expired",
            "Yes" if result.is_expired else "No"
        )

    st.subheader("Reasons")

    for reason in result.reasons:
        st.write(f"- {reason}")

    with st.expander("Extracted JSON"):
        st.json(result.extracted.model_dump())

    os.remove(pdf_path)