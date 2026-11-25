#!/usr/bin/env python3
"""The pkg's icon0.png (512x512) and pic1.png (1920x1080): original art, no game assets.

    make-icon.py <sce_sys folder>
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def font(size):
    for name in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arialbd.ttf",
                 "C:/Windows/Fonts/arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def sunset(w, h):
    """A desert dusk: purple sky to orange horizon, a low sun, a dark road to the horizon."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    horizon = int(h * 0.62)
    top, low = (38, 16, 58), (236, 110, 40)
    for y in range(horizon):
        t = y / max(1, horizon - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (low[i] - top[i]) * t ** 1.6) for i in range(3)))
    r = int(h * 0.16)
    cx = w // 2
    d.ellipse([cx - r, horizon - r, cx + r, horizon + r], fill=(255, 196, 70))
    # Bands across the sun, as on old posters.
    for k in range(5):
        y = horizon - r // 5 - k * r // 6
        d.rectangle([cx - r, y, cx + r, y + max(2, r // 22 + k)], fill=tuple(int(top[i] + (low[i] - top[i]) * 0.75)
                                                                          for i in range(3)))
    d.rectangle([0, horizon, w, h], fill=(26, 14, 18))
    # The road: a trapezoid with a dashed centre line.
    d.polygon([(cx - w * 0.04, horizon), (cx + w * 0.04, horizon), (cx + w * 0.42, h), (cx - w * 0.42, h)],
              fill=(44, 36, 40))
    for k in range(8):
        y0 = horizon + (h - horizon) * (k / 8) ** 1.5
        y1 = horizon + (h - horizon) * ((k + 0.5) / 8) ** 1.5
        wd0, wd1 = 1 + 6 * (y0 - horizon) / (h - horizon), 1 + 6 * (y1 - horizon) / (h - horizon)
        d.polygon([(cx - wd0, y0), (cx + wd0, y0), (cx + wd1, y1), (cx - wd1, y1)], fill=(240, 200, 80))
    return img, d


def centered(d, w, text, y, size, fill, shadow=None):
    f = font(size)
    tw = d.textlength(text, font=f)
    if shadow:
        d.text(((w - tw) / 2 + size // 18 + 2, y + size // 18 + 2), text, font=f, fill=shadow)
    d.text(((w - tw) / 2, y), text, font=f, fill=fill)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    img, d = sunset(512, 512)
    centered(d, 512, "V8", 40, 170, (255, 236, 200), shadow=(70, 20, 40))
    centered(d, 512, "ARCADE", 222, 54, (255, 236, 200), shadow=(70, 20, 40))
    centered(d, 512, "PS4", 420, 56, (240, 200, 80), shadow=(0, 0, 0))
    img.save(os.path.join(out, "icon0.png"))
    pic, d = sunset(1920, 1080)
    pic.save(os.path.join(out, "pic1.png"))
    print("wrote", os.path.join(out, "icon0.png"), "and pic1.png")


if __name__ == "__main__":
    main()
