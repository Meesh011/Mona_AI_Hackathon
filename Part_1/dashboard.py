import json
import os
import pandas as pd
import streamlit as st

st.title("Invoice Routing Agent")

# ── FIX 9: Guard against missing output file ─────────────────────────────────
# If app.py has not been run yet, show a helpful message instead of crashing.
OUTPUT_FILE = "output/invoices.json"

if not os.path.exists(OUTPUT_FILE):
    st.warning("No results found. Please run `python app.py` first to process the invoices.")
    st.stop()

with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data)

# ── FIX 10: Summary metrics row ───────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("Total Invoices", len(df))
col2.metric("Departments", df["department"].nunique())
col3.metric("Pending Approval", (df["status"] == "Pending Approval").sum())

st.divider()

# ── FIX 11: Filter section ────────────────────────────────────────────────────
department = st.selectbox(
    "Filter by department",
    ["All"] + sorted(df["department"].unique().tolist())
)

if department != "All":
    filtered_df = df[df["department"] == department]
else:
    filtered_df = df

# ── FIX 12: Removed duplicate st.dataframe(df) that showed full table THEN ──
# filtered table. Now shows only the (possibly filtered) result once.
st.dataframe(filtered_df, use_container_width=True)

st.caption(f"Showing {len(filtered_df)} of {len(df)} invoices")
