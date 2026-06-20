"""
dashboard.py — UKS Shift Replacement Agent Dashboard
Run with: streamlit run dashboard.py
"""

import json
import os
import streamlit as st
import pandas as pd
from database import load_staff, find_available_staff
from agent import run_agent

st.set_page_config(
    page_title="UKS Schicht-Agent",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 UKS Shift Replacement Agent")
st.caption("Universitätsklinikum des Saarlandes — Personalplanung Minijobber")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["💬 Schicht melden", "👥 Mitarbeiter", "📋 Protokoll"])

# ── Tab 1: HR chat interface ──────────────────────────────────────────────────
with tab1:
    st.subheader("Schichtausfall melden")
    st.write("Beschreiben Sie den Ausfall in eigenen Worten — der Agent findet den Ersatz automatisch.")

    col1, col2 = st.columns([3, 1])

    with col1:
        hr_message = st.text_area(
            "Nachricht an den Agenten",
            placeholder=(
                "Beispiel: Anna Schmidt ist krank. Brauchen Ersatz für die Nachtschicht "
                "auf der Intensivstation am Freitag. Muss Pflegefachkraft sein."
            ),
            height=120
        )

    with col2:
        st.write("**Schnellauswahl**")
        if st.button("🌙 Nachtschicht ICU"):
            hr_message = "Kurzfristiger Ausfall Nachtschicht Intensivstation Freitag, Pflegefachkraft benötigt"
        if st.button("🌅 Frühschicht Chirurgie"):
            hr_message = "Ausfall Frühschicht Chirurgie Montag, Pflegehelfer ok"
        if st.button("🌆 Spätschicht Notaufnahme"):
            hr_message = "Notaufnahme Spätschicht Samstag dringend Ersatz gesucht"

    simulate_n = st.slider(
        "Simulation: Zusage nach N Kontakten (0 = niemand sagt zu)",
        min_value=0, max_value=5, value=2
    )

    if st.button("🚀 Agent starten", type="primary", disabled=not hr_message.strip()):
        with st.spinner("Agent arbeitet..."):
            import io, contextlib
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                result = run_agent(hr_message, simulate_acceptance_after=simulate_n)
            output = f.getvalue()

        st.divider()

        if result:
            if result["filled_by"]:
                st.success(f"✅ Schicht besetzt durch **{result['filled_by']}**")
            else:
                st.error("❌ Niemand verfügbar — HR-Eskalation ausgelöst")

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Kontaktiert", len(result["staff_contacted"]))
            col_b.metric("Status", result["status"].split("—")[0].strip())
            req = result["shift_request"]
            col_c.metric("Schicht", f"{req.get('shift','')} | {req.get('ward','')}")

        with st.expander("📟 Agent-Protokoll anzeigen"):
            st.code(output, language=None)

# ── Tab 2: Staff overview ──────────────────────────────────────────────────────
with tab2:
    st.subheader("Minijobber-Übersicht (50 Mitarbeiter)")

    staff = load_staff()
    df = pd.DataFrame(staff)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gesamt", len(df))
    col2.metric("Aktiv", df["active"].sum())
    col3.metric("Mit Führerschein", df["driving_license"].sum())
    col4.metric("Pflegefachkräfte",
                df["qualifications"].apply(lambda q: "Pflegefachkraft" in q).sum())

    st.divider()

    # Filter
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        qual_filter = st.selectbox("Qualifikation", ["Alle", "Pflegefachkraft", "Pflegehelfer"])
    with fc2:
        shift_filter = st.selectbox("Schicht", ["Alle", "Früh", "Spät", "Nacht"])
    with fc3:
        ward_filter = st.selectbox("Station", ["Alle", "Intensivstation", "Chirurgie",
                                                "Notaufnahme", "Innere Medizin",
                                                "Orthopädie", "Neurologie", "OP"])

    filtered = staff
    if qual_filter != "Alle":
        filtered = [s for s in filtered if qual_filter in s["qualifications"]]
    if shift_filter != "Alle":
        filtered = [s for s in filtered if shift_filter in s["available_shifts"]]
    if ward_filter != "Alle":
        filtered = [s for s in filtered if ward_filter in s["wards"]]

    display_df = pd.DataFrame(filtered)[
        ["id", "name", "phone", "qualifications", "available_shifts", "wards",
         "available_days", "driving_license", "max_hours_per_week"]
    ]
    display_df.columns = ["ID", "Name", "Telefon", "Qualifikation", "Schichten",
                           "Stationen", "Tage", "Führerschein", "Max h/Wo"]
    display_df["Qualifikation"] = display_df["Qualifikation"].apply(lambda x: ", ".join(x))
    display_df["Schichten"] = display_df["Schichten"].apply(lambda x: ", ".join(x))
    display_df["Stationen"] = display_df["Stationen"].apply(lambda x: ", ".join(x))
    display_df["Tage"] = display_df["Tage"].apply(lambda x: ", ".join(x))

    st.dataframe(display_df, use_container_width=True)
    st.caption(f"{len(filtered)} Mitarbeiter angezeigt")

# ── Tab 3: Log ────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Schicht-Protokoll")

    LOG_FILE = "output/shift_log.json"
    if not os.path.exists(LOG_FILE):
        st.info("Noch keine Einträge. Starten Sie den Agenten im ersten Tab.")
    else:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)

        for entry in reversed(log):
            req = entry["shift_request"]
            filled = entry["filled_by"]
            icon = "✅" if filled else "❌"

            with st.expander(
                f"{icon} {req.get('shift','')}schicht | {req.get('ward','')} | "
                f"{req.get('day','')} — {entry['timestamp'][:16]}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Anfrage**")
                    st.json(req)
                with col2:
                    st.write("**Ergebnis**")
                    st.write(f"Status: **{entry['status']}**")
                    st.write(f"Besetzt durch: **{filled or '—'}**")
                    st.write(f"Kontaktiert: {', '.join(entry['staff_contacted']) or '—'}")
