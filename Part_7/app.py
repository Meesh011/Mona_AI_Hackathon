"""
app.py — Problem 7: Target-group & Customer Analytics Agent
Allgäuer Latschenkiefer / Dr. Theiss Naturwaren GmbH
"""
import streamlit as st
import pandas as pd
import json, os, io
from pathlib import Path

st.set_page_config(
    page_title="Analytics Agent · Allgäuer Latschenkiefer",
    page_icon="📊",
    layout="wide",
)

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; }

.hero {
    background: linear-gradient(135deg,#0f1e2d 0%,#162d44 55%,#1a3d28 100%);
    border:1px solid rgba(100,160,220,.2); border-radius:18px;
    padding:2.4rem 3rem 2rem; margin-bottom:1.8rem;
}
.hero-kicker { font-size:.72rem; font-weight:700; letter-spacing:.14em;
    text-transform:uppercase; color:#60a5fa; margin-bottom:.7rem; }
.hero h1 { font-family:'Space Grotesk',sans-serif; font-size:2.3rem;
    font-weight:700; color:#fff; margin:0 0 .4rem; }
.hero p  { color:rgba(255,255,255,.68); font-size:.98rem; margin:0; }

.metric-card { background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px;
    padding:1.1rem 1.3rem; text-align:center; }
.metric-num  { font-family:'Space Grotesk',sans-serif; font-size:2rem;
    font-weight:700; color:#1e3a5f; }
.metric-lbl  { font-size:.78rem; color:#64748b; margin-top:.1rem; }

.signal-card { background:#fff; border:1px solid #e2e8f0; border-radius:10px;
    padding:1rem 1.2rem; margin-bottom:.7rem; border-left:4px solid #3b82f6; }
.signal-card.high   { border-left-color:#10b981; }
.signal-card.medium { border-left-color:#f59e0b; }
.signal-card.low    { border-left-color:#94a3b8; }
.signal-title { font-weight:700; color:#1e293b; font-size:.95rem; }
.signal-meta  { font-size:.8rem; color:#64748b; margin-top:.2rem; }
.signal-copy  { background:#f1f5f9; border-radius:6px; padding:.4rem .7rem;
    font-size:.83rem; color:#334155; margin-top:.5rem; font-style:italic; }

.lift-box { border-radius:12px; padding:1.2rem 1.5rem; margin-bottom:1rem; }
.lift-pos  { background:#ecfdf5; border:1px solid #6ee7b7; }
.lift-neg  { background:#fef2f2; border:1px solid #fca5a5; }
.lift-neu  { background:#f8fafc; border:1px solid #cbd5e1; }

.seg-badge { display:inline-block; padding:3px 10px; border-radius:12px;
    font-size:.73rem; font-weight:700; margin:2px; }

.stButton>button {
    background:linear-gradient(135deg,#1d4ed8,#3b82f6) !important;
    color:#fff !important; font-weight:700 !important;
    border:none !important; border-radius:9px !important;
    padding:.6rem 1.4rem !important; width:100% !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="hero-kicker">📊 Dr. Theiss Naturwaren · Analytics Agent</div>
  <h1>Target-Group & Customer Analytics</h1>
  <p>Upload transaction data → compute RFM, seasonal patterns, category affinity
  and optimal ad send-windows → measure campaign lift with difference-in-differences.</p>
</div>
""", unsafe_allow_html=True)

# ── sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key = st.text_input("Gemini API Key", type="password",
                            value=os.environ.get("GEMINI_API_KEY",""))
    st.markdown("---")
    st.markdown("**Data Sources**")
    tx_upload = st.file_uploader("transactions.csv", type="csv")
    cx_upload = st.file_uploader("customers.csv",    type="csv")
    st.markdown("---")
    st.markdown("**Campaign Lift Settings**")
    campaign_sku = st.selectbox("Campaign SKU", [
        "ALK-LG-01","ALK-FB-01","ALK-MG-03","ALK-FB-04",
        "ALK-MG-01","ALK-FB-02","ALK-MG-02","ALK-MG-05",
    ])
    pre_start  = st.date_input("Pre-period start",  value=pd.Timestamp("2024-06-01"))
    pre_end    = st.date_input("Pre-period end",     value=pd.Timestamp("2024-06-30"))
    post_start = st.date_input("Post-period start",  value=pd.Timestamp("2024-07-01"))
    post_end   = st.date_input("Post-period end",    value=pd.Timestamp("2024-07-31"))
    st.markdown("---")
    st.caption("Data pack: Dr. Theiss / Allgäuer Latschenkiefer\nPrices & segments: synthetic")

# ── load data ──────────────────────────────────────────────────────────────
@st.cache_data
def load(tx_bytes, cx_bytes):
    from analytics import load_data
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as t1:
        t1.write(tx_bytes); tp1 = t1.name
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as t2:
        t2.write(cx_bytes); tp2 = t2.name
    tx, cx = load_data(tp1, tp2)
    os.unlink(tp1); os.unlink(tp2)
    return tx, cx

# use bundled data if no upload
BUNDLED_TX = Path(__file__).parent / "transactions.csv"
BUNDLED_CX = Path(__file__).parent / "customers.csv"

if tx_upload and cx_upload:
    tx, cx = load(tx_upload.read(), cx_upload.read())
elif BUNDLED_TX.exists() and BUNDLED_CX.exists():
    tx, cx = load(BUNDLED_TX.read_bytes(), BUNDLED_CX.read_bytes())
    st.info("Using bundled synthetic dataset (800 customers, ~3 300 transactions). Upload your own CSV files in the sidebar to replace.")
else:
    st.warning("Upload transactions.csv and customers.csv in the sidebar, or run `python generate_data.py` to create sample data.")
    st.stop()

# ── tabs ───────────────────────────────────────────────────────────────────
t1, t2, t3, t4, t5 = st.tabs([
    "📈 Overview", "👥 RFM Segments", "🗓️ Seasonal & Timing",
    "🎯 Targeting Signals", "📏 Campaign Lift"
])

# ──────────────────────────────────────────────────────────────────────────
# TAB 1: OVERVIEW
# ──────────────────────────────────────────────────────────────────────────
with t1:
    total_rev = tx["revenue"].sum()
    n_cx      = tx["customer_id"].nunique()
    n_tx      = len(tx)
    avg_order = tx["revenue"].mean()

    m1,m2,m3,m4 = st.columns(4)
    for col, num, lbl in [
        (m1, f"€{total_rev:,.0f}", "Total Revenue"),
        (m2, f"{n_cx:,}",          "Unique Customers"),
        (m3, f"{n_tx:,}",          "Transactions"),
        (m4, f"€{avg_order:.2f}",  "Avg Order Value"),
    ]:
        col.markdown(f"""<div class="metric-card">
        <div class="metric-num">{num}</div>
        <div class="metric-lbl">{lbl}</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    lc, rc = st.columns(2)

    with lc:
        st.markdown("#### Revenue by Product Line")
        line_rev = tx.groupby("line")["revenue"].sum().sort_values(ascending=False).reset_index()
        st.bar_chart(line_rev.set_index("line")["revenue"])

    with rc:
        st.markdown("#### Revenue by Channel")
        ch_rev = tx.groupby("channel")["revenue"].sum().sort_values(ascending=False).reset_index()
        st.bar_chart(ch_rev.set_index("channel")["revenue"])

    st.markdown("#### Monthly Revenue Trend")
    tx["month_str"] = tx["date"].dt.to_period("M").astype(str)
    monthly = tx.groupby("month_str")["revenue"].sum().reset_index()
    st.line_chart(monthly.set_index("month_str")["revenue"])

    st.markdown("#### Top 10 SKUs by Revenue")
    top_sku = (tx.groupby(["sku","product_name"])["revenue"]
               .sum().sort_values(ascending=False).head(10).reset_index())
    st.dataframe(top_sku, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────
# TAB 2: RFM
# ──────────────────────────────────────────────────────────────────────────
with t2:
    from analytics import compute_rfm, category_affinity
    rfm = compute_rfm(tx)
    aff = category_affinity(tx)
    rfm_full = rfm.merge(aff, on="customer_id", how="left")

    seg_counts = rfm["rfm_segment"].value_counts()
    sc1, sc2, sc3 = st.columns(3)
    colors = {"high_value":"#10b981","mid_value":"#f59e0b","at_risk":"#ef4444"}
    for col, seg in zip([sc1,sc2,sc3], ["high_value","mid_value","at_risk"]):
        cnt = seg_counts.get(seg, 0)
        pct = cnt/len(rfm)*100
        col.markdown(f"""<div class="metric-card">
        <div class="metric-num" style="color:{colors[seg]}">{cnt}</div>
        <div class="metric-lbl">{seg.replace('_',' ').title()} ({pct:.0f}%)</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    lc, rc = st.columns(2)

    with lc:
        st.markdown("#### RFM Score Distribution")
        st.bar_chart(rfm["rfm_score"].value_counts().sort_index())

    with rc:
        st.markdown("#### Avg Spend by RFM Segment")
        seg_spend = rfm.groupby("rfm_segment")["monetary"].mean().round(2).reset_index()
        seg_spend.columns = ["Segment","Avg Lifetime Spend (€)"]
        st.dataframe(seg_spend, use_container_width=True)

    st.markdown("#### RFM Data (top 200 customers)")
    disp_cols = ["customer_id","recency_days","frequency","monetary",
                 "R_score","F_score","M_score","rfm_score","rfm_segment"]
    st.dataframe(rfm[disp_cols].head(200), use_container_width=True)

    st.markdown("#### Category Affinity by Behaviour Segment")
    seg_aff = tx.groupby("segment").apply(
        lambda d: d.groupby("line")["revenue"].sum() / d["revenue"].sum()
    ).round(3)
    if not seg_aff.empty:
        st.dataframe(seg_aff.style.background_gradient(cmap="Greens"), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────
# TAB 3: SEASONAL & TIMING
# ──────────────────────────────────────────────────────────────────────────
with t3:
    from analytics import seasonal_index
    si = seasonal_index(tx)

    st.markdown("#### Seasonal Revenue Index by Product Line")
    st.caption("1.0 = average month · >1.0 = above average · colour = intensity")
    pivot = si.pivot(index="line", columns="month", values="seasonal_index").fillna(0)
    pivot.columns = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    st.dataframe(pivot.style.background_gradient(cmap="RdYlGn", axis=None, vmin=0, vmax=2.5)
                 .format("{:.2f}"), use_container_width=True)

    st.markdown("---")
    st.markdown("#### Day-of-Week Purchase Patterns")
    tx["dow"] = tx["date"].dt.day_name()
    dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    dow_rev = tx.groupby("dow")["revenue"].sum().reindex(dow_order)
    st.bar_chart(dow_rev)

    st.markdown("#### Best Send-Window per Segment × SKU")
    from analytics import send_windows
    sw = send_windows(tx)
    sw_disp = sw[["segment","sku","product_name","best_month_name","best_dow_name"]].copy()
    sw_disp.columns = ["Segment","SKU","Product","Best Month","Best Day"]
    st.dataframe(sw_disp, use_container_width=True)

    csv_sw = sw_disp.to_csv(index=False).encode()
    st.download_button("⬇️ Download Send-Window Table (CSV)", csv_sw,
                       "send_windows.csv", "text/csv")

# ──────────────────────────────────────────────────────────────────────────
# TAB 4: TARGETING SIGNALS (Gemini)
# ──────────────────────────────────────────────────────────────────────────
with t4:
    st.markdown("### 🎯 AI-Generated Targeting Recommendations")

    if st.button("🤖 Generate Targeting Report with Gemini", use_container_width=True):
        if not api_key:
            st.error("Enter Gemini API key in the sidebar.")
        else:
            with st.spinner("Analysing patterns and generating recommendations…"):
                try:
                    from analytics import compute_rfm, seasonal_index, send_windows, campaign_lift, targeting_signals
                    from gemini_client import generate_targeting_report

                    rfm_df = compute_rfm(tx)
                    rfm_summary = {
                        "total_customers": int(len(rfm_df)),
                        "high_value_count": int((rfm_df["rfm_segment"]=="high_value").sum()),
                        "mid_value_count":  int((rfm_df["rfm_segment"]=="mid_value").sum()),
                        "at_risk_count":    int((rfm_df["rfm_segment"]=="at_risk").sum()),
                        "avg_rfm_score":    float(rfm_df["rfm_score"].mean().round(2)),
                        "avg_order_value":  float(tx["revenue"].mean().round(2)),
                        "top_segments_by_revenue": (
                            tx.groupby("segment")["revenue"].sum()
                            .sort_values(ascending=False)
                            .head(4).round(2).to_dict()
                        ),
                    }

                    sw_df = send_windows(tx)
                    ts_df = targeting_signals(tx)
                    top_signals = ts_df.head(30).fillna("").to_dict(orient="records")

                    si_df = seasonal_index(tx)
                    seasonal_summary = (
                        si_df[si_df["seasonal_index"] > 1.3]
                        .sort_values("seasonal_index", ascending=False)
                        .head(15)[["line","month","seasonal_index"]]
                        .to_dict(orient="records")
                    )

                    lift = campaign_lift(tx, "ALK-LG-01",
                                        "2024-06-01","2024-06-30",
                                        "2024-07-01","2024-07-31")

                    report = generate_targeting_report(
                        rfm_summary, top_signals, seasonal_summary, lift, api_key
                    )
                    st.session_state["targeting_report"] = report
                    st.success("✅ Report generated")
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.exception(e)

    if "targeting_report" in st.session_state:
        rep = st.session_state["targeting_report"]

        st.markdown(f"""<div style="background:#f0f9ff;border:1px solid #bae6fd;
        border-radius:10px;padding:1.2rem 1.5rem;margin-bottom:1.2rem;
        color:#0c4a6e;line-height:1.7">
        <strong>Executive Summary</strong><br>{rep.get('executive_summary','')}
        </div>""", unsafe_allow_html=True)

        st.markdown("#### 📡 Top Targeting Signals")
        for sig in rep.get("top_targeting_signals", []):
            pri = sig.get("priority","Medium").lower()
            st.markdown(f"""<div class="signal-card {pri}">
            <div class="signal-title">{sig.get('product_name',sig.get('sku',''))} 
            → <strong>{sig.get('segment','').replace('_',' ').title()}</strong></div>
            <div class="signal-meta">📅 Send in <strong>{sig.get('send_month','')}</strong> 
            on <strong>{sig.get('send_day','')}</strong> 
            · Priority: <strong>{sig.get('priority','')}</strong></div>
            <div class="signal-meta" style="margin-top:.3rem">{sig.get('rationale','')}</div>
            <div class="signal-copy">💬 Ad copy hint: {sig.get('ad_copy_hint','')}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("#### 👥 Segment Insights")
        seg_cols = st.columns(2)
        for i, ins in enumerate(rep.get("segment_insights", [])):
            with seg_cols[i % 2]:
                st.markdown(f"""<div style="background:#fafafa;border:1px solid #e2e8f0;
                border-radius:10px;padding:1rem;margin-bottom:.8rem">
                <strong>{ins.get('segment','').replace('_',' ').title()}</strong><br>
                <span style="font-size:.85rem;color:#374151">{ins.get('description','')}</span><br>
                <span style="font-size:.8rem;color:#6b7280">
                📦 {ins.get('key_products','')}  ·  🕐 {ins.get('best_timing','')}  ·  📱 {ins.get('channel_rec','')}
                </span></div>""", unsafe_allow_html=True)

        if rep.get("next_campaign_rec"):
            st.markdown(f"""<div style="background:#f0fdf4;border:1px solid #86efac;
            border-radius:10px;padding:1rem 1.3rem;margin-top:.5rem">
            <strong>🚀 Next Campaign Recommendation</strong><br>
            <span style="color:#166534">{rep['next_campaign_rec']}</span>
            </div>""", unsafe_allow_html=True)

        st.download_button("⬇️ Download Report (JSON)",
            data=json.dumps(rep, indent=2, ensure_ascii=False),
            file_name="targeting_report.json", mime="application/json")

# ──────────────────────────────────────────────────────────────────────────
# TAB 5: CAMPAIGN LIFT
# ──────────────────────────────────────────────────────────────────────────
with t5:
    st.markdown("### 📏 Campaign Lift Measurement (Difference-in-Differences)")
    st.markdown("""
    **Method:** DiD compares the change in revenue for the treatment group (received campaign)
    vs. the control group (did not) between the pre-period and post-period.
    A t-test checks whether the per-customer spend difference is statistically significant.
    """)

    if st.button("📏 Calculate Lift", use_container_width=True):
        from analytics import campaign_lift
        lift = campaign_lift(
            tx, campaign_sku,
            pre_start.isoformat(), pre_end.isoformat(),
            post_start.isoformat(), post_end.isoformat(),
        )
        st.session_state["lift"] = lift

    if "lift" in st.session_state:
        lift = st.session_state["lift"]
        sig  = lift["significant"]
        lift_pct = lift["lift_pct"]
        box_cls  = "lift-pos" if lift_pct > 0 else "lift-neg"

        st.markdown(f"""<div class="lift-box {box_cls}">
        <strong>Campaign SKU:</strong> {lift['campaign_sku']}<br>
        <strong>Pre-period:</strong> {lift['pre_period']} &nbsp;|&nbsp;
        <strong>Post-period:</strong> {lift['post_period']}<br><br>
        <span style="font-size:1.8rem;font-weight:800">
        {'📈' if lift_pct > 0 else '📉'} {lift_pct:+.1f}% lift
        </span>
        &nbsp;&nbsp;(DiD: €{lift['did_lift_eur']:+,.2f})<br>
        <strong>Statistical significance:</strong>
        {'✅ p = ' + str(lift['p_value']) + ' (significant at 5%)' if sig
         else '⚠️ p = ' + str(lift['p_value']) + ' (not significant)'}
        </div>""", unsafe_allow_html=True)

        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown("**Treatment Group**")
            st.metric("Pre-period revenue",  f"€{lift['treatment_pre_rev']:,.2f}")
            st.metric("Post-period revenue", f"€{lift['treatment_post_rev']:,.2f}",
                      delta=f"€{lift['treatment_post_rev']-lift['treatment_pre_rev']:+,.2f}")
            st.metric("Customers (post)",    lift['treatment_post_cx'])
        with rc2:
            st.markdown("**Control Group**")
            st.metric("Pre-period revenue",  f"€{lift['control_pre_rev']:,.2f}")
            st.metric("Post-period revenue", f"€{lift['control_post_rev']:,.2f}",
                      delta=f"€{lift['control_post_rev']-lift['control_pre_rev']:+,.2f}")
            st.metric("Customers (post)",    lift['control_post_cx'])

        st.markdown("""---
**How to read this:**
The DiD removes any seasonality or trend that affects both groups equally.
If treatment went up by €200 and control went up by €80, the campaign caused €120 of incremental revenue.
A p-value < 0.05 means the difference is unlikely to be random chance.
        """)

        # revenue chart
        chart_data = pd.DataFrame({
            "Period": ["Pre","Post","Pre","Post"],
            "Group":  ["Treatment","Treatment","Control","Control"],
            "Revenue":[lift["treatment_pre_rev"],lift["treatment_post_rev"],
                       lift["control_pre_rev"],lift["control_post_rev"]],
        })
        st.markdown("#### Revenue Before vs. After (Treatment vs. Control)")
        st.bar_chart(chart_data.pivot(index="Period",columns="Group",values="Revenue"))

        st.download_button("⬇️ Download Lift Data (JSON)",
            data=json.dumps(lift, indent=2),
            file_name="lift_measurement.json", mime="application/json")
