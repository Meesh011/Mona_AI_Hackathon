"""
video_engine.py
Renders short-form vertical reels (1080x1920, 9:16) for Allgäuer Latschenkiefer.

Safe zones per hackathon data pack (§5, Problem 6):
  top    : ~140 px  (title bar + clock)
  bottom : ~540 px  (midpoint of 480–600 range, covers caption + CTA bar)
  right  : ~150 px  (midpoint of 120–180, action icons column)
  left   :  ~40 px  (minimal chrome)
  → 'message-safe band': x 40–930, y 140–1380  (centred on the 1080 canvas)
"""
from __future__ import annotations
import os, subprocess, tempfile, copy
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ── canvas ──────────────────────────────────────────────────────────────────
W, H = 1080, 1920
FPS  = 30

# ── safe zone (from data pack brief) ────────────────────────────────────────
# Keep ALL text/logos inside this rectangle
SZ = dict(left=40, right=150, top=140, bottom=540)
SZ_X0 = SZ["left"]
SZ_X1 = W - SZ["right"]          # 930
SZ_Y0 = SZ["top"]                # 140
SZ_Y1 = H - SZ["bottom"]         # 1380
SZ_W  = SZ_X1 - SZ_X0            # 890
SZ_CX = (SZ_X0 + SZ_X1) // 2     # 485

# ── fonts ────────────────────────────────────────────────────────────────────
FONT_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf"
FONT_MED  = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def _hex(c: str | list | None, default=(30, 30, 30)) -> tuple:
    if c is None: return default
    if isinstance(c, (list, tuple)): return tuple(int(x) for x in c)
    h = c.lstrip("#")
    if len(h) == 3: h = "".join(x*2 for x in h)
    try: return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except: return default

def _gradient(c1, c2, w=W, h=H) -> Image.Image:
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for ch in range(3):
        arr[:, :, ch] = np.linspace(c1[ch], c2[ch], h).reshape(-1, 1)
    return Image.fromarray(arr)

def _wrap(text: str, font, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    return lines

def _text_block(draw, text, cx, y, font, fill, max_w,
                align="center", shadow=True, shadow_col=(0,0,0)) -> int:
    lh = font.size + 10
    for line in _wrap(text, font, max_w, draw):
        bw = draw.textbbox((0,0), line, font=font)[2]
        x = cx - bw//2 if align=="center" else cx
        if shadow:
            draw.text((x+3, y+3), line, font=font, fill=(*shadow_col, 130))
        draw.text((x, y), line, font=font, fill=fill)
        y += lh
    return y


def render_frame(scene: dict, show_safe_zone: bool = False) -> Image.Image:
    """
    Render one 1080×1920 frame from a scene dict.

    Expected scene keys:
      bg_color_1/2  – hex gradient
      accent_color  – hex
      layout        – "center" | "top_heavy" | "bottom_heavy"
      badge         – small pill (e.g. "#NatürlicheKraft")
      headline      – main text
      subtext       – supporting copy
      cta           – CTA bar text (anchored inside bottom safe zone)
      hwg_compliant – bool (just metadata, not rendered)
    """
    c1  = _hex(scene.get("bg_color_1"), (10, 28, 20))
    c2  = _hex(scene.get("bg_color_2"), (25, 55, 35))
    acc = _hex(scene.get("accent_color"), (180, 150, 60))

    img  = _gradient(c1, c2)
    draw = ImageDraw.Draw(img, "RGBA")

    # ── decorative circles (atmospheric, outside safe zone is fine) ─────────
    draw.ellipse([W//2-380, H//2-380, W//2+380, H//2+380], fill=(*acc, 14))
    draw.ellipse([W//2-210, H//2-210, W//2+210, H//2+210], fill=(*acc, 10))

    # horizontal accent rule just below top safe zone
    rule_y = SZ_Y0 + 52
    draw.rectangle([SZ_X0, rule_y, SZ_X1, rule_y+3], fill=(*acc, 210))

    layout = scene.get("layout", "center")

    # ── badge pill ────────────────────────────────────────────────────────
    badge_bottom = SZ_Y0 + 12
    badge = scene.get("badge", "")
    if badge:
        fb = _font(FONT_MED, 30)
        bb = draw.textbbox((0,0), badge, font=fb)
        bw, bh = bb[2]-bb[0]+28, bb[3]-bb[1]+14
        bx = SZ_CX - bw//2
        by = SZ_Y0 + 8
        draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=bh//2, fill=(*acc, 225))
        draw.text((bx+14, by+7), badge, font=fb, fill=(255,255,255))
        badge_bottom = by + bh + 20

    text_start = badge_bottom + 30

    # ── headline ─────────────────────────────────────────────────────────
    headline = scene.get("headline", "")
    bottom_y = text_start
    if headline:
        sz = 90 if len(headline) < 22 else 68 if len(headline) < 40 else 54
        fh = _font(FONT_BOLD, sz)
        if layout == "top_heavy":
            hl_y = text_start
        elif layout == "bottom_heavy":
            # anchor headline well above CTA — stay inside safe zone
            hl_y = SZ_Y1 - 420
        else:
            hl_y = SZ_Y0 + (SZ_Y1 - SZ_Y0)//2 - 200
        bottom_y = _text_block(draw, headline, SZ_CX, hl_y, fh,
                                fill=(255,255,255), max_w=SZ_W-40)

    # ── subtext ───────────────────────────────────────────────────────────
    subtext = scene.get("subtext", "")
    if subtext:
        fs = _font(FONT_REG, 42)
        _text_block(draw, subtext, SZ_CX, bottom_y+22, fs,
                    fill=(215,215,215), max_w=SZ_W-80)

    # ── CTA bar (anchored at bottom of safe zone, not below it) ──────────
    cta = scene.get("cta", "")
    if cta:
        fc   = _font(FONT_BOLD, 46)
        lines= _wrap(cta, fc, SZ_W-60, draw)
        lh   = fc.size + 8
        th   = lh * len(lines) + 22
        # top of CTA box: inside safe zone, at least 30px above SZ_Y1
        cta_box_top = SZ_Y1 - th - 30
        draw.rounded_rectangle(
            [SZ_X0+16, cta_box_top-12, SZ_X1-16, SZ_Y1-20],
            radius=16, fill=(*acc, 235))
        _text_block(draw, cta, SZ_CX, cta_box_top,
                    fc, fill=(255,255,255), max_w=SZ_W-80, shadow=False)

    # ── safe zone debug overlay ───────────────────────────────────────────
    if show_safe_zone:
        draw.rectangle([SZ_X0, SZ_Y0, SZ_X1, SZ_Y1],
                       outline=(255,220,0), width=4)
        draw.text((SZ_X0+10, SZ_Y0+8), f"SAFE ZONE  {SZ_W}×{SZ_Y1-SZ_Y0}px",
                  font=_font(FONT_BOLD, 26), fill=(255,220,0))
        # show margins
        for label, x, y in [
            (f"← {SZ['left']}px", 2, H//2),
            (f"{SZ['right']}px →", SZ_X1+4, H//2),
        ]:
            draw.text((x, y), label, font=_font(FONT_REG, 24), fill=(255,220,0))

    return img


def frames_for_scene(scene: dict, duration_s: float,
                     show_safe_zone: bool = False) -> list[Image.Image]:
    """Ken Burns zoom + slight drift per scene."""
    n = max(1, int(duration_s * FPS))
    base_arr = np.array(render_frame(scene, show_safe_zone))
    frames = []
    for i in range(n):
        t  = i / max(n-1, 1)
        sc = 1.0 + 0.055 * t
        dx = int(18 * t)
        dy = int(8  * t)
        nw, nh = int(W*sc), int(H*sc)
        zoomed = Image.fromarray(base_arr).resize((nw, nh), Image.LANCZOS)
        ox = min(max(0, (nw-W)//2 + dx), nw-W)
        oy = min(max(0, (nh-H)//2 + dy), nh-H)
        frames.append(zoomed.crop((ox, oy, ox+W, oy+H)))
    return frames


def write_video(scenes: list[dict], output_path: str,
                show_safe_zone: bool = False) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        fd = Path(tmp) / "f"
        fd.mkdir()
        idx = 0
        for s in scenes:
            for f in frames_for_scene(s, float(s.get("duration_seconds", 3.0)), show_safe_zone):
                f.save(fd / f"frame_{idx:06d}.png")
                idx += 1
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", str(fd / "frame_%06d.png"),
            "-c:v", "libx264", "-preset", "fast",
            "-crf", "20", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"FFmpeg error:\n{r.stderr}")
    return output_path


def render_thumbnail(scene: dict, show_safe_zone: bool = False) -> Image.Image:
    return render_frame(scene, show_safe_zone)
