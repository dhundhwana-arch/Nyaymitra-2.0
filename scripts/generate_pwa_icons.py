#!/usr/bin/env python3
"""Generate PWA icons from the NYAYMITRA favicon design."""
from pathlib import Path
from PIL import Image, ImageDraw

ICON_DIR = Path("web/assets/icons")
ICON_DIR.mkdir(parents=True, exist_ok=True)

# Colors from favicon.svg
BG = (0x0B, 0x13, 0x2B)      # dark blue
GOLD_START = (0xE8, 0xC9, 0x6A)  # light gold
GOLD_END = (0xB8, 0x86, 0x0B)    # dark gold


def gold_at(t: float) -> tuple[int, int, int]:
    """Linear interpolate between gold start and end colors."""
    return tuple(int(GOLD_START[i] + (GOLD_END[i] - GOLD_START[i]) * t) for i in range(3))


def draw_icon(img: Image.Image) -> None:
    """Draw the NYAYMITRA icon on the given image."""
    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")

    # Background - dark blue rounded rect
    pad = int(w * 0.08)
    r = int(w * 0.22)
    draw.rounded_rectangle([pad, pad, w - pad, h - pad], radius=r, fill=BG)

    cx = w // 2
    cy = h // 2
    line_w = max(2, int(w * 0.05))

    # Vertical line (gradient simulated with segments)
    steps = 12
    seg_h = (h - 2 * pad) // steps
    for i in range(steps):
        t = i / max(steps - 1, 1)
        color = gold_at(t)
        y0 = pad + i * seg_h
        y1 = min(pad + (i + 1) * seg_h, h - pad)
        draw.line([cx, y0, cx, y1], fill=color, width=line_w)

    # Horizontal line across middle
    y_mid = int(h * 0.38)
    draw.line([pad, y_mid, w - pad, y_mid], fill=GOLD_END, width=line_w)

    # Diagonal elements (simplified shield shape)
    draw.line([pad + int(w * 0.15), pad + int(h * 0.38),
               pad + int(w * 0.08), pad + int(h * 0.55)], fill=GOLD_END, width=line_w)
    draw.line([w - pad - int(w * 0.15), pad + int(h * 0.38),
               w - pad - int(w * 0.08), pad + int(h * 0.55)], fill=GOLD_END, width=line_w)

    # Bottom line
    draw.line([int(w * 0.35), int(h * 0.75), int(w * 0.65), int(h * 0.75)], fill=GOLD_END, width=line_w)


SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

for size in SIZES:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_icon(img)
    out = ICON_DIR / f"icon-{size}x{size}.png"
    img.save(out, "PNG")
    print(f"Generated {out} ({size}x{size})")

# Also create a maskable version (same icon, centered in safe zone)
for size in [192, 512]:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pad = int(size * 0.125)
    inner = Image.new("RGBA", (size - 2 * pad, size - 2 * pad), (0, 0, 0, 0))
    draw_icon(inner)
    img.paste(inner, (pad, pad))
    out = ICON_DIR / f"icon-{size}x{size}-maskable.png"
    img.save(out, "PNG")
    print(f"Generated {out} (maskable {size}x{size})")

print("\nAll icons generated in", ICON_DIR)
