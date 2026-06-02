"""
Generate icon PNGs for the medic_reminder integration.
Run once:  python generate_icons.py
Requires:  pip install Pillow
Output:    icon.png, icon@2x.png, dark_icon.png, dark_icon@2x.png
           brand/icon.png, brand/icon@2x.png, brand/dark_icon.png, brand/dark_icon@2x.png
"""
import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("Pillow not found. Install it with:  pip install Pillow")


# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
BLUE_BG    = (21,  101, 192, 255)   # #1565C0  light-mode background
BLUE_DARK  = (13,   71, 161, 255)   # #0D47A1  border
BLUE_LIGHT = (66,  165, 245, 255)   # #42A5F5  right capsule half
BLUE_PALE  = (187, 222, 251, 255)   # #BBDEFB  centre divider
AMBER      = (245, 127,  23, 255)   # #F57F17  bell badge
WHITE      = (255, 255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)
DARK_BG    = (30,  30,  30, 255)    # dark-mode background


# ---------------------------------------------------------------------------
# Draw icon
# ---------------------------------------------------------------------------
def draw_icon(size: int, dark: bool) -> Image.Image:
    s = size / 256

    img = Image.new("RGBA", (size, size), TRANSPARENT)
    d = ImageDraw.Draw(img)

    bg = DARK_BG if dark else BLUE_BG

    # ── Background ──────────────────────────────────────────────────────────
    r_bg = int(48 * s)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r_bg, fill=bg)

    # ── Capsule — drawn on same-size layer, then rotated ─────────────────────
    cap_layer = Image.new("RGBA", (size, size), TRANSPARENT)
    dc = ImageDraw.Draw(cap_layer)

    # Capsule centred at (120, 112), width=160, height=76
    W, H = int(160 * s), int(76 * s)
    cx, cy = int(120 * s), int(112 * s)
    r = H // 2
    ox, oy = cx - W // 2, cy - H // 2

    # Draw capsule as explicit geometry — no masking needed:
    # left semicircle (white) + left body rect (white) + right body rect (blue) + right semicircle (blue)
    # plus border semicircles and rects slightly larger in BLUE_DARK

    b = max(2, int(3 * s))  # border thickness

    # Border (slightly larger, drawn first)
    dc.ellipse([ox - b, oy - b, ox + H + b, oy + H + b], fill=BLUE_DARK)          # left border cap
    dc.ellipse([ox + W - H - b, oy - b, ox + W + b, oy + H + b], fill=BLUE_DARK)  # right border cap
    dc.rectangle([ox + r - b, oy - b, ox + W - r + b, oy + H + b], fill=BLUE_DARK)

    # Right half (blue): right semicircle + right body
    dc.ellipse([ox + W - H, oy, ox + W, oy + H], fill=BLUE_LIGHT)   # right cap
    dc.rectangle([cx, oy, ox + W - r, oy + H], fill=BLUE_LIGHT)     # right body

    # Left half (white): left semicircle + left body
    dc.ellipse([ox, oy, ox + H, oy + H], fill=WHITE)                 # left cap
    dc.rectangle([ox + r, oy, cx, oy + H], fill=WHITE)               # left body

    # Centre divider
    strip = max(3, int(5 * s))
    dc.rectangle([cx - strip // 2, oy, cx + strip // 2, oy + H], fill=BLUE_PALE)

    # Rotate and composite onto main image
    cap_rotated = cap_layer.rotate(35, resample=Image.BICUBIC, center=(cx, cy))
    img.alpha_composite(cap_rotated)

    # ── Bell badge ────────────────────────────────────────────────────────────
    d2 = ImageDraw.Draw(img)
    bc = int(192 * s)
    br = int(38 * s)

    # Orange circle
    d2.ellipse([bc - br, bc - br, bc + br, bc + br], fill=AMBER)

    # Bell: polygon silhouette + clapper + hook
    bell_cx  = bc
    bell_top = int(167 * s)
    bell_bot = int(200 * s)
    bell_hw  = int(16 * s)
    stem_hw  = int(7 * s)

    # Bell silhouette (arch top via ellipse + trapezoid body)
    arch_r = bell_hw
    arch_cy = bell_top + arch_r
    d2.ellipse([bell_cx - arch_r, bell_top, bell_cx + arch_r, bell_top + arch_r * 2], fill=WHITE)
    # Body below arch centre
    body_top = arch_cy
    body_bot = bell_bot - int(5 * s)
    d2.polygon([
        (bell_cx - arch_r,              body_top),
        (bell_cx + arch_r,              body_top),
        (bell_cx + bell_hw + int(4*s),  body_bot),
        (bell_cx - bell_hw - int(4*s),  body_bot),
    ], fill=WHITE)
    # Base bar
    base_y0 = body_bot - int(2 * s)
    base_y1 = bell_bot
    d2.rounded_rectangle(
        [bell_cx - bell_hw - int(4*s), base_y0,
         bell_cx + bell_hw + int(4*s), base_y1],
        radius=int(2 * s), fill=WHITE)
    # Clapper dot
    clap_y0 = base_y1
    clap_y1 = base_y1 + int(8 * s)
    d2.ellipse([bell_cx - int(4*s), clap_y0, bell_cx + int(4*s), clap_y1], fill=WHITE)
    # Hook
    d2.rounded_rectangle(
        [bell_cx - int(2*s), bell_top - int(6*s),
         bell_cx + int(2*s), bell_top],
        radius=int(2 * s), fill=WHITE)

    return img


# ---------------------------------------------------------------------------
# Generate all variants
# ---------------------------------------------------------------------------
HERE = Path(__file__).parent
BRAND = HERE / "brand"
BRAND.mkdir(exist_ok=True)

variants = [
    ("icon.png",         256, False),
    ("icon@2x.png",      512, False),
    ("dark_icon.png",    256, True),
    ("dark_icon@2x.png", 512, True),
]

for filename, size, dark in variants:
    icon = draw_icon(size, dark)
    path = HERE / filename
    icon.save(path, "PNG")
    print(f"  created  {path.name}  ({size}×{size})")
    brand_path = BRAND / filename
    icon.save(brand_path, "PNG")
    print(f"  created  brand/{filename}  ({size}×{size})")

print("\nDone. Restart Home Assistant to pick up the new icons.")
