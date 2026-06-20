"""
app.py — Problem 6: Allgäuer Latschenkiefer Filmmaker Agent
Streamlit UI for the Dr. Theiss Naturwaren GmbH marketing team.
"""
import streamlit as st
import json, os, tempfile
from PIL import Image

st.set_page_config(
    page_title="Filmmaker Agent · Allgäuer Latschenkiefer",
    page_icon="🌲",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; background: #070f09; color: #e8f0ea; }

.hero {
    background: linear-gradient(135deg, #0a1a0e 0%, #112b18 55%, #1a3d28 100%);
    border: 1px solid rgba(100,180,120,0.2);
    border-radius: 18px; padding: 2.6rem 3rem 2.2rem; margin-bottom: 1.8rem;
    position: relative; overflow: hidden;
}
.hero::after {
    content:''; position:absolute; bottom:-80px; right:-80px;
    width:320px; height:320px;
    background: radial-gradient(circle, rgba(201,168,76,0.12) 0%, transparent 70%);
    border-radius:50%;
}
.hero-kicker { font-size:.72rem; font-weight:700; letter-spacing:.14em;
    text-transform:uppercase; color:#c9a84c; margin-bottom:.7rem; }
.hero h1 { font-family:'Space Grotesk',sans-serif; font-size:2.5rem;
    font-weight:700; color:#fff; margin:0 0 .45rem; line-height:1.1; }
.hero p  { color:rgba(255,255,255,.68); font-size:1rem; margin:0; }

.sku-card { background:#0d1e12; border:1px solid rgba(100,180,120,.18);
    border-radius:12px; padding:1rem 1.2rem; margin-bottom:.7rem; cursor:pointer; }
.sku-card:hover { border-color:rgba(201,168,76,.5); }
.sku-name { font-weight:700; color:#e8f0ea; font-size:.95rem; }
.sku-meta { font-size:.78rem; color:rgba(255,255,255,.5); margin-top:.15rem; }

.hwg-ok   { background:rgba(34,197,94,.1); border:1px solid rgba(34,197,94,.3);
    border-radius:8px; padding:.7rem 1rem; color:#4ade80; font-size:.83rem; margin-top:.8rem; }
.hwg-warn { background:rgba(234,179,8,.1); border:1px solid rgba(234,179,8,.3);
    border-radius:8px; padding:.7rem 1rem; color:#fbbf24; font-size:.83rem; margin-top:.8rem; }

.safe-info { background:#0d1e12; border:1px solid rgba(201,168,76,.25);
    border-radius:10px; padding:.9rem 1.1rem; margin-bottom:1rem; font-size:.82rem; color:#c9a84c; }

.stButton>button {
    background:linear-gradient(135deg,#1a5c2e,#2d8c50) !important;
    color:#fff !important; font-weight:700 !important; font-size:.95rem !important;
    border:none !important; border-radius:10px !important;
    padding:.62rem 1.5rem !important; width:100% !important;
}
div[data-testid="stTabs"] button { color:#a0b8a8 !important; }
div[data-testid="stTabs"] button[aria-selected="true"] {
    color:#c9a84c !important; border-bottom:2px solid #c9a84c !important;
}
</style>
""", unsafe_allow_html=True)

# ── hero ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-kicker">🌲 Allgäuer Latschenkiefer · Dr. Theiss Naturwaren GmbH</div>
  <h1>Reel Filmmaker Agent</h1>
  <p>Pick a hero SKU and content angle → Gemini writes the studio brief → renders a real 1080×1920 MP4
  with TikTok &amp; Instagram safe zones locked in and HWG cosmetics law guardrails applied.</p>
</div>
""", unsafe_allow_html=True)

# ── data ───────────────────────────────────────────────────────────────────
HERO_SKUS = [
    {"sku":"ALK-MG-01","name":"Mobil Gel","line":"Muscles & Joints",
     "desc":"Classic muscle & joint gel with Latschenkiefernöl for active recovery and everyday tension.",
     "audience":"Active 30+, 55+ joints","season":"Autumn–Winter","price":5.83},
    {"sku":"ALK-MG-03","name":"Mobil Eisspray akut","line":"Muscles & Joints",
     "desc":"Fast-acting cold spray for acute muscle strain and sports injuries. 150ml.",
     "audience":"Athletes, teams","season":"Sport season","price":9.40},
    {"sku":"ALK-LG-01","name":"5 in 1 Beinlotion","line":"Legs",
     "desc":"Multi-benefit leg lotion for tired, heavy legs. Five targeted benefits in one product.",
     "audience":"Women 35–65","season":"Summer","price":9.95},
    {"sku":"ALK-FB-02","name":"Sole Fußbad","line":"Feet",
     "desc":"Alpine brine foot bath with Latschenkiefernöl for a reviving, warming foot ritual.",
     "audience":"Wellness, 50+","season":"Winter","price":6.49},
    {"sku":"ALK-FB-01","name":"Fuß Butter","line":"Feet",
     "desc":"Rich foot butter for very dry skin. Deep nourishment, silky finish.",
     "audience":"45+ dry-skin, women","season":"Autumn–Winter","price":7.71},
    {"sku":"ALK-FB-04","name":"Hornhaut Entferner Maske","line":"Feet",
     "desc":"2-step sock-mask treatment that removes callus and leaves feet soft. Before/after ritual.",
     "audience":"Women 25–45","season":"Spring–Summer","price":8.49},
]

CONTENT_ANGLES = {
    "ritual_asmr":  "🛁 ASMR Foot Bath Ritual — sensory, evening wind-down, product textures",
    "post_workout": "⚡ 15s Post-Workout Recovery — sport energy, Eisspray moment",
    "heavy_legs":   "😮‍💨 'Heavy Legs After a Shift' — relatable hook, Beinlotion relief",
    "origin_story": "🌲 Ingredient Origin Story — Allgäu plantation → distillation → bottle",
    "sandal_prep":  "👡 Sandal Season Prep — spring callus care countdown",
}

# ── sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key = st.text_input("Gemini API Key", type="password",
                            value=os.environ.get("GEMINI_API_KEY",""))
    st.markdown("---")
    st.markdown("**Safe Zone Spec** *(data pack §5)*")
    st.markdown("""
| Edge   | Margin  | x / y boundary |
|--------|---------|----------------|
| Top    | 140 px  | y ≥ 140        |
| Bottom | 540 px  | y ≤ 1380       |
| Right  | 150 px  | x ≤ 930        |
| Left   |  40 px  | x ≥ 40         |
    """)
    st.markdown("*Canvas 1080×1920 · Message band 890×1240 px*")
    st.markdown("---")
    show_sz = st.checkbox("Show safe zone guides on preview", value=False)
    st.markdown("---")
    st.caption("Hackathon — Problems 6–9 data pack\nBrand data: public sources\nPrices/segments: synthetic")

# ── tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["✏️  Create", "🖼️  Preview", "🎬  Export MP4"])

# ──────────────────────────────────────────────────────────────────────────
# TAB 1: CREATE
# ──────────────────────────────────────────────────────────────────────────
with tab1:
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown("#### 🌿 Hero SKU")
        sku_choice = st.radio(
            "Select product",
            options=[s["sku"] for s in HERO_SKUS],
            format_func=lambda x: next(s["name"] for s in HERO_SKUS if s["sku"]==x),
            horizontal=False, label_visibility="collapsed",
        )
        selected = next(s for s in HERO_SKUS if s["sku"]==sku_choice)
        st.markdown(f"""<div class="sku-card">
        <div class="sku-name">{selected['name']} — {selected['sku']}</div>
        <div class="sku-meta">{selected['line']} · {selected['season']} · €{selected['price']} · {selected['audience']}</div>
        <div style="margin-top:.5rem;font-size:.85rem;color:rgba(255,255,255,.7)">{selected['desc']}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("#### 🎬 Content Angle")
        angle_key = st.radio(
            "Angle",
            options=list(CONTENT_ANGLES.keys()),
            format_func=lambda x: CONTENT_ANGLES[x],
            label_visibility="collapsed",
        )

    with right:
        st.markdown("#### 📱 Platform & Settings")
        platform = st.selectbox("Platform", ["Both", "TikTok", "Instagram Reels"])

        st.markdown("""<div class="safe-info">
        🛡️ <strong>Safe zones auto-enforced</strong><br>
        Text rendered inside 890×1240px message band.<br>
        CTA bar anchored in y 1280–1360 slot.<br>
        TikTok action icons (right 150px) always clear.
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div class="hwg-warn">
        ⚖️ <strong>HWG Guardrails active</strong><br>
        No medical cure claims. Cosmetic language only.<br>
        Gemini prompted to flag non-compliant text.
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    go = st.button("🌲 Generate Reel Brief", use_container_width=True)

    if go:
        if not api_key:
            st.error("Enter Gemini API key in the sidebar.")
        else:
            with st.spinner("Generating studio reel brief with Gemini…"):
                try:
                    from gemini_client import generate_reel_brief
                    brief = generate_reel_brief(
                        product_name=selected["name"],
                        product_description=selected["desc"],
                        sku=selected["sku"],
                        target_audience=selected["audience"],
                        platform=platform,
                        content_angle=angle_key,
                        api_key=api_key,
                    )
                    st.session_state["brief"] = brief
                    scenes = brief.get("scenes", [])
                    hwg_ok = all(s.get("hwg_compliant", True) for s in scenes)
                    st.success(
                        f"✅ Brief ready · {len(scenes)} scenes · "
                        f"{brief.get('total_duration_seconds','?')}s · "
                        f"{'⚖️ HWG compliant' if hwg_ok else '⚠️ Check HWG flags'}"
                    )
                    if brief.get("hwg_compliance_note"):
                        st.info(f"**HWG note:** {brief['hwg_compliance_note']}")
                except Exception as e:
                    st.error(f"Gemini error: {e}")

    if "brief" in st.session_state:
        with st.expander("📋 Raw JSON brief"):
            st.json(st.session_state["brief"])

# ──────────────────────────────────────────────────────────────────────────
# TAB 2: PREVIEW
# ──────────────────────────────────────────────────────────────────────────
with tab2:
    if "brief" not in st.session_state:
        st.info("Generate a brief in the **Create** tab first.")
    else:
        brief  = st.session_state["brief"]
        scenes = brief.get("scenes", [])

        st.markdown(f"### {brief.get('reel_title','Untitled')}")
        meta_cols = st.columns(4)
        meta_cols[0].metric("Platform",  brief.get("platform","—"))
        meta_cols[1].metric("Duration",  f"{brief.get('total_duration_seconds','?')}s")
        meta_cols[2].metric("Scenes",    len(scenes))
        meta_cols[3].metric("Music mood",brief.get("music_mood","—"))

        st.markdown("---")

        from video_engine import render_thumbnail

        ICONS = {"hook":"🪝","product":"📦","benefit":"✨","social_proof":"⭐","cta":"🎯"}
        cols = st.columns(min(len(scenes), 5))
        for i, scene in enumerate(scenes):
            with cols[i % 5]:
                try:
                    thumb = render_thumbnail(scene, show_safe_zone=show_sz)
                    dh = 300
                    dw = int(dh * W / H)
                    st.image(thumb.resize((dw, dh), Image.LANCZOS), use_container_width=True)
                except Exception as e:
                    st.error(str(e))
                icon = ICONS.get(scene.get("scene_purpose",""), "🎬")
                hwg  = "✅" if scene.get("hwg_compliant", True) else "⚠️"
                st.markdown(
                    f"**{icon} S{scene['scene_number']} · {scene.get('duration_seconds','?')}s** {hwg}  \n"
                    f"*{scene.get('scene_purpose','')}*  \n"
                    f"{scene.get('headline','')[:45]}"
                )

        st.markdown("---")
        st.markdown("#### 📝 Scene Detail")
        for s in scenes:
            icon = ICONS.get(s.get("scene_purpose",""),"🎬")
            hwg  = "✅ HWG OK" if s.get("hwg_compliant", True) else "⚠️ Review HWG"
            with st.expander(f"{icon} Scene {s['scene_number']} — {s.get('headline','')[:55]}  ·  {hwg}"):
                c1, c2 = st.columns(2)
                with c1:
                    for k in ["duration_seconds","scene_purpose","layout","headline","subtext","cta"]:
                        if s.get(k): st.markdown(f"**{k}:** {s[k]}")
                with c2:
                    for k in ["badge","voiceover_hint","bg_color_1","bg_color_2","accent_color"]:
                        if s.get(k): st.markdown(f"**{k}:** `{s[k]}`")

        tags = brief.get("hashtags",[])
        if tags:
            st.markdown("#### # Hashtags")
            st.code(" ".join(tags))
        if brief.get("caption"):
            st.markdown("#### 💬 Caption")
            st.text_area("Caption (copy for posting)", value=brief["caption"], height=90)

# ──────────────────────────────────────────────────────────────────────────
# TAB 3: EXPORT
# ──────────────────────────────────────────────────────────────────────────
with tab3:
    if "brief" not in st.session_state:
        st.info("Generate a brief in the **Create** tab first.")
    else:
        brief  = st.session_state["brief"]
        scenes = brief.get("scenes", [])

        st.markdown(f"""
#### 🎬 Render MP4
**{len(scenes)} scenes · {brief.get('total_duration_seconds','?')}s · 1080×1920 (9:16)**

The rendered video will:
- ✅ Enforce safe zones from data pack spec (top 140 / bottom 540 / right 150 / left 40 px)
- ✅ Leave TikTok action-icon column (right 150px) completely clear
- ✅ Keep caption/CTA bar above y=1380
- ✅ Ken Burns zoom per scene · H.264 MP4 · upload-ready
        """)

        burn_sz = st.checkbox("Burn safe zone guides into video (for review)", value=False)

        if st.button("🎬 Render MP4 (~30–60s)", use_container_width=True):
            with st.spinner("Rendering frames and encoding with FFmpeg…"):
                try:
                    from video_engine import write_video
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                        tmp = f.name
                    write_video(scenes, tmp, show_safe_zone=burn_sz)
                    with open(tmp, "rb") as f:
                        vb = f.read()
                    os.unlink(tmp)
                    fname = brief.get("reel_title","reel").replace(" ","_").lower() + ".mp4"
                    st.session_state["vbytes"] = vb
                    st.session_state["vfname"] = fname
                    st.success(f"✅ Rendered · {len(vb)//1024} KB · {fname}")
                except Exception as e:
                    st.error(f"Render error: {e}")

        if "vbytes" in st.session_state:
            st.video(st.session_state["vbytes"])
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️ Download MP4",
                    data=st.session_state["vbytes"],
                    file_name=st.session_state.get("vfname","reel.mp4"),
                    mime="video/mp4", use_container_width=True)
            with c2:
                st.download_button("⬇️ Download Brief JSON",
                    data=json.dumps(brief, indent=2, ensure_ascii=False),
                    file_name="reel_brief.json", mime="application/json",
                    use_container_width=True)
