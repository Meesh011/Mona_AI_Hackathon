"""
app.py — Problem 8: Dynamic Pricing Agent
Allgäuer Latschenkiefer / Dr. Theiss Naturwaren GmbH
"""
import streamlit as st
import pandas as pd
import json, os
from datetime import date, timedelta

st.set_page_config(
    page_title="Dynamic Pricing Agent · Allgäuer Latschenkiefer",
    page_icon="💶",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; }

.hero {
    background:linear-gradient(135deg,#0a1628 0%,#0f2d4a 55%,#1a3028 100%);
    border:1px solid rgba(96,165,250,.18); border-radius:18px;
    padding:2.4rem 3rem 2rem; margin-bottom:1.8rem;
}
.kicker { font-size:.72rem;font-weight:700;letter-spacing:.14em;
    text-transform:uppercase;color:#60a5fa;margin-bottom:.7rem; }
.hero h1 { font-family:'Space Grotesk',sans-serif;font-size:2.3rem;
    font-weight:700;color:#fff;margin:0 0 .4rem; }
.hero p  { color:rgba(255,255,255,.68);font-size:.98rem;margin:0; }

.signal-pill {
    display:inline-block;padding:4px 12px;border-radius:20px;
    font-size:.73rem;font-weight:700;margin:2px;
}
.pill-weather  { background:#dbeafe;color:#1e40af; }
.pill-events   { background:#ede9fe;color:#5b21b6; }
.pill-supply   { background:#fef3c7;color:#92400e; }
.pill-guard    { background:#fee2e2;color:#991b1b; }

.price-row-up   { background:#f0fdf4;border-left:4px solid #10b981; }
.price-row-down { background:#fff7ed;border-left:4px solid #f59e0b; }
.price-row-hold { background:#f8fafc;border-left:4px solid #94a3b8; }

.guardrail-box {
    background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;
    padding:1rem 1.3rem;margin:.5rem 0;font-size:.87rem;color:#7c2d12;
}
.compliance-box {
    background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;
    padding:1rem 1.3rem;margin:.5rem 0;font-size:.87rem;color:#1e3a5f;
}

.metric-card { background:#f8fafc;border:1px solid #e2e8f0;
    border-radius:12px;padding:1.1rem 1.3rem;text-align:center; }
.metric-num  { font-family:'Space Grotesk',sans-serif;font-size:1.9rem;
    font-weight:700;color:#1e3a5f; }
.metric-lbl  { font-size:.75rem;color:#64748b;margin-top:.1rem; }

.audit-row { border:1px solid #e2e8f0;border-radius:8px;padding:.7rem 1rem;
    margin:.4rem 0;font-size:.83rem; }

.stButton>button {
    background:linear-gradient(135deg,#0369a1,#0ea5e9) !important;
    color:#fff !important;font-weight:700 !important;
    border:none !important;border-radius:9px !important;
    padding:.6rem 1.4rem !important;width:100% !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="kicker">💶 Dr. Theiss Naturwaren · Dynamic Pricing Agent</div>
  <h1>Signal-Driven Pricing Engine</h1>
  <p>Weather · Calendar events · Football fixtures · Supply-chain stress →
  automated pricing within a strict ±12% guardrail band, fully logged for audit.</p>
</div>
""", unsafe_allow_html=True)

# ── sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key = st.text_input("Gemini API Key", type="password",
                            value=os.environ.get("GEMINI_API_KEY",""))
    st.markdown("---")
    st.markdown("**Pricing Guardrails**")
    st.markdown("""
| Rule | Value |
|------|-------|
| Max increase | +12% |
| Max decrease | −12% |
| Single-step fairness cap | +8% |
| Sensitive SKU ceiling (Urea) | +5% |
| Min margin floor | €1.20 |
| Price rounding | €0.05 steps |
    """)
    st.markdown("---")
    city = st.selectbox("Weather city", [
        "Deutschland (avg)","Hamburg","Berlin","München",
        "Köln","Frankfurt","Homburg (Saarland)","Stuttgart"
    ], index=0)
    target_date = st.date_input("Pricing date", value=date.today())
    event_window = st.slider("Event look-ahead (days)", 7, 30, 21)
    st.markdown("---")
    st.caption("Prices & segments: synthetic\nPharmacy RPM rules apply")

# ── tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📡 Live Signals", "💶 Price Recommendations",
    "🛡️ Guardrails & Audit", "📝 Pricing Memo (AI)"
])

# ── fetch signals (cached 15min) ───────────────────────────────────────────
@st.cache_data(ttl=900)
def get_signals(city, target_date_str, window):
    from signals import fetch_weather, upcoming_events
    w = fetch_weather(city)
    e = upcoming_events(date.fromisoformat(target_date_str), window)
    return w, e

@st.cache_data(ttl=900)
def get_decisions(city, target_date_str, window):
    from signals import fetch_weather, upcoming_events, supply_stress
    from pricing_engine import run_all
    w = fetch_weather(city)
    e = upcoming_events(date.fromisoformat(target_date_str), window)
    return run_all(w, e), w, e

# ──────────────────────────────────────────────────────────────────────────
# TAB 1: LIVE SIGNALS
# ──────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 📡 Current Market Signals")
    with st.spinner("Fetching weather + events…"):
        weather, events = get_signals(city, target_date.isoformat(), event_window)

    # weather card
    wc1, wc2, wc3, wc4 = st.columns(4)
    temp_max = weather.get("temp_max", "—")
    temp_min = weather.get("temp_min", "—")
    precip   = weather.get("precip_mm", "—")
    avg7     = weather.get("forecast_7d_avg_max", "—")
    src      = weather.get("source","live API")

    for col, num, lbl in [
        (wc1, f"{temp_max}°C", f"Today Max · {city}"),
        (wc2, f"{temp_min}°C", "Today Min"),
        (wc3, f"{precip}mm",   "Precipitation"),
        (wc4, f"{avg7}°C",     "7-day Avg Max"),
    ]:
        col.markdown(f"""<div class="metric-card">
        <div class="metric-num">{num}</div>
        <div class="metric-lbl">{lbl}</div></div>""", unsafe_allow_html=True)

    if src == "synthetic_fallback":
        st.warning("⚠️ Weather API unreachable — using seasonal average estimate.")

    st.markdown("---")
    # events
    st.markdown("#### 📅 Upcoming Events & Fixtures")
    if events:
        ev_df = pd.DataFrame(events)
        ev_df["days_away"] = ev_df["days_away"].astype(int)
        st.dataframe(
            ev_df[["name","date","category","pricing_signal","days_away"]]
            .rename(columns={"days_away":"Days Away","pricing_signal":"Signal"}),
            use_container_width=True
        )
    else:
        st.info("No significant events in the selected window.")

    # supply chain
    st.markdown("#### 🏭 Supply Chain Stress")
    from signals import supply_stress
    from pricing_engine import CATALOGUE
    stress_rows = []
    for sku in CATALOGUE:
        s = supply_stress(sku)
        stress_rows.append({
            "SKU": sku,
            "Product": CATALOGUE[sku]["name"],
            "Ingredients": ", ".join(s["ingredients"]),
            "Avg Stress": s["avg_stress"],
            "Level": s["level"],
        })
    stress_df = pd.DataFrame(stress_rows)
    st.dataframe(
        stress_df.style.map(
            lambda v: "background:#fee2e2" if v=="critical"
                 else "background:#fef3c7" if v=="elevated" else "",
            subset=["Level"]
        ),
        use_container_width=True
    )

# ──────────────────────────────────────────────────────────────────────────
# TAB 2: PRICE RECOMMENDATIONS
# ──────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 💶 Price Recommendations — Full Catalogue")
    with st.spinner("Running pricing engine…"):
        decisions, weather2, events2 = get_decisions(city, target_date.isoformat(), event_window)

    # summary metrics
    n_up   = sum(1 for d in decisions if d.direction=="increase")
    n_down = sum(1 for d in decisions if d.direction=="decrease")
    n_hold = sum(1 for d in decisions if d.direction=="hold")
    max_up = max((d.change_pct for d in decisions if d.direction=="increase"), default=0)
    guards = sum(len(d.guardrails_fired) for d in decisions)

    mc = st.columns(5)
    for col, num, lbl, color in [
        (mc[0], n_up,           "Price Increases", "#10b981"),
        (mc[1], n_down,         "Price Decreases", "#f59e0b"),
        (mc[2], n_hold,         "Hold",            "#94a3b8"),
        (mc[3], f"+{max_up:.1f}%", "Max Increase", "#1e3a5f"),
        (mc[4], guards,         "Guardrails Fired","#ef4444"),
    ]:
        col.markdown(f"""<div class="metric-card">
        <div class="metric-num" style="color:{color}">{num}</div>
        <div class="metric-lbl">{lbl}</div></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Filter controls
    fc1, fc2 = st.columns([2,3])
    with fc1:
        show_filter = st.multiselect("Show", ["increase","decrease","hold"],
                                     default=["increase","decrease"])
    with fc2:
        line_filter = st.multiselect("Product line",
            ["Feet","Legs","Muscles/Joints","Cough drops"],
            default=["Feet","Legs","Muscles/Joints","Cough drops"])

    from pricing_engine import CATALOGUE
    rows = []
    for d in decisions:
        if d.direction not in show_filter: continue
        line = CATALOGUE.get(d.sku,{}).get("line","")
        if line not in line_filter: continue

        dir_icon = "📈" if d.direction=="increase" else "📉" if d.direction=="decrease" else "➡️"
        color_cls = "price-row-up" if d.direction=="increase" \
               else "price-row-down" if d.direction=="decrease" else "price-row-hold"

        signals_html = ""
        for s in d.signals_applied:
            src_cls = {"weather":"pill-weather","events":"pill-events",
                       "supply":"pill-supply"}.get(s["source"],"")
            signals_html += f'<span class="signal-pill {src_cls}">{s["source"]}: ×{s["multiplier"]:.3f}</span>'
        if d.guardrails_fired:
            signals_html += f'<span class="signal-pill pill-guard">⚠️ {len(d.guardrails_fired)} guardrail(s)</span>'

        st.markdown(f"""<div class="audit-row {color_cls}">
        <strong>{dir_icon} {d.product_name}</strong>
        <span style="color:#64748b;font-size:.8rem"> · {d.sku}</span>
        <span style="float:right;font-family:monospace;font-size:1rem">
          <span style="color:#94a3b8">€{d.base_price:.2f}</span> →
          <strong>€{d.recommended_price:.2f}</strong>
          <span style="color:{'#10b981' if d.change_pct>0 else '#f59e0b'};margin-left:6px">
            {d.change_pct:+.1f}%</span>
        </span><br>
        <div style="margin:.3rem 0">{signals_html}</div>
        <div style="font-size:.82rem;color:#374151">{d.rationale[:200]}</div>
        </div>""", unsafe_allow_html=True)

    # CSV export
    rows_export = [d.to_dict() for d in decisions]
    csv = pd.DataFrame(rows_export).to_csv(index=False).encode()
    st.download_button("⬇️ Export All Prices (CSV)", csv,
                       f"pricing_{target_date.isoformat()}.csv", "text/csv")

# ──────────────────────────────────────────────────────────────────────────
# TAB 3: GUARDRAILS & AUDIT LOG
# ──────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 🛡️ Guardrails & Audit Log")
    st.markdown("""
    Every price change is logged with full signal provenance. This log is the
    compliance record for pharmacy partner negotiations and internal review.
    """)

    fired = [d for d in decisions if d.guardrails_fired]
    if fired:
        st.markdown(f"#### ⚠️ {len(fired)} SKU(s) had guardrails fire")
        for d in fired:
            for g in d.guardrails_fired:
                st.markdown(f"""<div class="guardrail-box">
                <strong>{d.product_name} ({d.sku})</strong><br>
                🛡️ {g}
                </div>""", unsafe_allow_html=True)
    else:
        st.success("✅ No guardrails fired for current signals.")

    st.markdown("---")
    st.markdown("#### 📋 Full Audit Trail")
    for d in decisions:
        with st.expander(
            f"{'📈' if d.direction=='increase' else '📉' if d.direction=='decrease' else '➡️'} "
            f"{d.product_name} — €{d.base_price:.2f} → €{d.recommended_price:.2f} "
            f"({d.change_pct:+.1f}%)  ·  {d.timestamp[:10]}"
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**SKU:** {d.sku}")
                st.markdown(f"**Base price:** €{d.base_price:.2f}")
                st.markdown(f"**Recommended:** €{d.recommended_price:.2f}")
                st.markdown(f"**Change:** {d.change_pct:+.1f}%")
                st.markdown(f"**Direction:** {d.direction}")
            with c2:
                st.markdown(f"**Signals applied:**")
                for s in d.signals_applied:
                    st.markdown(f"- {s['source']}: ×{s['multiplier']:.4f} — {s['reason']}")
                if d.guardrails_fired:
                    st.markdown(f"**Guardrails:**")
                    for g in d.guardrails_fired:
                        st.markdown(f"- ⚠️ {g}")
            st.markdown(f"**Rationale:** {d.rationale}")
            st.markdown(f"**Timestamp:** {d.timestamp}")

    # full JSON export
    audit_json = json.dumps([d.to_dict() for d in decisions], indent=2, ensure_ascii=False)
    st.download_button("⬇️ Export Full Audit Log (JSON)", audit_json,
                       f"audit_log_{target_date.isoformat()}.json", "application/json")

# ──────────────────────────────────────────────────────────────────────────
# TAB 4: PRICING MEMO (GEMINI)
# ──────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 📝 AI Pricing Memo")
    st.markdown("Gemini interprets the engine's output and writes a plain-language memo for the commercial team.")

    if st.button("✍️ Generate Pricing Memo", use_container_width=True):
        if not api_key:
            st.error("Enter Gemini API key in the sidebar.")
        else:
            with st.spinner("Writing pricing memo…"):
                try:
                    from gemini_client import generate_pricing_memo
                    memo = generate_pricing_memo(
                        weather2,
                        events2[:8],
                        [d.to_dict() for d in decisions],
                        api_key,
                    )
                    st.session_state["memo"] = memo
                    st.success("✅ Memo generated")
                except Exception as e:
                    st.error(f"Gemini error: {e}")
                    st.exception(e)

    if "memo" in st.session_state:
        memo = st.session_state["memo"]

        st.markdown(f"""<div style="background:#f0f9ff;border:1px solid #bae6fd;
        border-radius:10px;padding:1.2rem 1.5rem;margin-bottom:1.2rem;color:#0c4a6e;line-height:1.7">
        <strong>Executive Summary</strong><br>{memo.get('executive_summary','')}
        </div>""", unsafe_allow_html=True)

        if memo.get("market_context"):
            st.markdown(f"""<div style="background:#fafafa;border:1px solid #e2e8f0;
            border-radius:10px;padding:1rem 1.3rem;margin-bottom:1rem;line-height:1.6;font-size:.9rem">
            <strong>Market Context</strong><br>{memo['market_context']}
            </div>""", unsafe_allow_html=True)

        st.markdown("#### 💶 Pricing Actions")
        for action in memo.get("pricing_actions", []):
            act = action.get("action","hold")
            pri = action.get("priority","Medium").lower()
            icon = "📈" if act=="increase" else "📉" if act=="decrease" else "➡️"
            color = "#10b981" if act=="increase" else "#f59e0b" if act=="decrease" else "#94a3b8"
            border = {"high":"#10b981","medium":"#f59e0b","low":"#94a3b8"}.get(pri,"#e2e8f0")
            st.markdown(f"""<div style="border:1px solid {border};border-left:4px solid {color};
            border-radius:10px;padding:1rem;margin-bottom:.7rem">
            <strong>{icon} {action.get('product_name','')}
            <span style="font-family:monospace;margin-left:8px;color:{color}">
            €{action.get('recommended_price','—')} ({action.get('change_pct',0):+.1f}%)</span>
            </strong>
            <span style="float:right;font-size:.75rem;font-weight:700;
            background:{border};padding:2px 8px;border-radius:10px;color:#374151">
            {action.get('priority','')}</span><br>
            <span style="font-size:.86rem;color:#374151">{action.get('plain_rationale','')}</span><br>
            <span style="font-size:.82rem;color:#6b7280;margin-top:.3rem;display:block">
            ⚠️ Risk: {action.get('risk_note','—')}</span>
            </div>""", unsafe_allow_html=True)

        if memo.get("guardrail_summary"):
            st.markdown(f"""<div class="guardrail-box">
            <strong>🛡️ Guardrail Summary</strong><br>{memo['guardrail_summary']}
            </div>""", unsafe_allow_html=True)

        if memo.get("compliance_note"):
            st.markdown(f"""<div class="compliance-box">
            <strong>⚖️ Compliance Note</strong><br>{memo['compliance_note']}
            </div>""", unsafe_allow_html=True)

        if memo.get("next_review_trigger"):
            st.info(f"🔔 **Next review trigger:** {memo['next_review_trigger']}")

        st.download_button("⬇️ Download Memo (JSON)",
            data=json.dumps(memo, indent=2, ensure_ascii=False),
            file_name=f"pricing_memo_{target_date.isoformat()}.json",
            mime="application/json")
