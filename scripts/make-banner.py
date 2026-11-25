#!/usr/bin/env python3
"""The README's banner (docs/images/banner.png, 1600x480): a desert dusk - a banded sun, mesas and a road to the
horizon - and the title, in Crema's layout. Original art: nothing from the game (the title in Lato, the quick menu's
font in patches/fonts, SIL Open Font License).

    python3 scripts/make-banner.py
"""
import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
W, H = 1600, 480
SKY_TOP, SKY_LOW = (34, 14, 54), (240, 112, 44)
SUN = (255, 200, 72)
GROUND = (24, 12, 18)
TEXT_TOP, TEXT_LOW = (255, 236, 186), (255, 140, 52)
MUTED = (214, 182, 170)


def font(size, name="Lato-Black.ttf"):
    for path in (os.path.join(ROOT, "patches", "fonts", name), "C:/Windows/Fonts/arialbd.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def scene():
    """The dusk: sky, banded sun, two mesas, the ground and a road with a dashed line, all from the sun's point."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    horizon = int(H * 0.66)
    for y in range(horizon):
        d.line([(0, y), (W, y)], fill=lerp(SKY_TOP, SKY_LOW, (y / (horizon - 1)) ** 1.7))
    cx, r = int(W * 0.27), int(H * 0.27)
    # The sun's glow, then the sun cut by the bands of an old poster.
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([cx - r * 1.9, horizon - r * 1.9, cx + r * 1.9, horizon + r * 1.9], fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(r * 0.6))
    img = Image.composite(Image.new("RGB", (W, H), (255, 170, 80)), img, glow)
    # The disc minus the bands, so the sky shows through them and nothing sticks out of the disc.
    disc = Image.new("L", (W, H), 0)
    dd = ImageDraw.Draw(disc)
    dd.ellipse([cx - r, horizon - r, cx + r, horizon + r], fill=255)
    for k in range(6):
        y = horizon - r // 6 - k * r // 7
        dd.rectangle([cx - r - 2, y, cx + r + 2, y + 3 + k], fill=0)
    img = Image.composite(Image.new("RGB", (W, H), SUN), img, disc)
    d = ImageDraw.Draw(img)
    # Mesas on the horizon, darker the nearer.
    for x0, x1, top, colour in ((-40, 360, 0.47, (58, 22, 44)), (520, 760, 0.53, (70, 26, 46)),
                                (300, 470, 0.58, (44, 18, 32))):
        t = int(H * top)
        d.polygon([(x0, horizon), (x0 + 40, t + 12), (x0 + 60, t), (x1 - 60, t), (x1 - 40, t + 12), (x1, horizon)],
                  fill=colour)
    d.rectangle([0, horizon, W, H], fill=GROUND)
    # The road from the sun to the bottom edge, and its centre line.
    d.polygon([(cx - 14, horizon), (cx + 14, horizon), (cx + 430, H), (cx - 430, H)], fill=(46, 32, 38))
    for k in range(9):
        a, b = (k / 9) ** 1.6, ((k + 0.45) / 9) ** 1.6
        y0, y1 = horizon + (H - horizon) * a, horizon + (H - horizon) * b
        w0, w1 = 1 + 9 * a, 1 + 9 * b
        d.polygon([(cx - w0, y0), (cx + w0, y0), (cx + w1, y1), (cx - w1, y1)], fill=(244, 204, 86))
    # Heat on the road: two faint lines across it.
    for k, y in enumerate((horizon + 22, horizon + 64)):
        d.line([(cx - 60 - 60 * k, y), (cx + 60 + 60 * k, y)], fill=(90, 54, 52), width=2)
    return img


def text_panel(img):
    """The right side darkens towards the title, so the text reads over the sky."""
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    start = int(W * 0.42)
    for x in range(start, W):
        sd.line([(x, 0), (x, H)], fill=int(205 * min(1.0, ((x - start) / (W * 0.22)) ** 1.2)))
    return Image.composite(Image.new("RGB", (W, H), (16, 8, 20)), img, shade)


def gradient_text(img, xy, text, f, top, low, glow=None):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=f, fill=255)
    box = mask.getbbox()
    if glow:
        halo = mask.filter(ImageFilter.GaussianBlur(14))
        halo = ImageChops.multiply(halo, Image.new("L", img.size, glow[1]))
        img = Image.composite(Image.new("RGB", img.size, glow[0]), img, halo)
    fill = Image.new("RGB", img.size)
    fd = ImageDraw.Draw(fill)
    for y in range(box[1], box[3] + 1):
        fd.line([(box[0], y), (box[2], y)], fill=lerp(top, low, (y - box[1]) / max(1, box[3] - box[1])))
    return Image.composite(fill, img, mask)


def main():
    img = text_panel(scene())
    x = int(W * 0.53)
    img = gradient_text(img, (x, 92), "VIGILANTE 8", font(112), TEXT_TOP, TEXT_LOW, glow=((255, 120, 40), 150))
    img = gradient_text(img, (x + 4, 214), "ARCADE", font(70), (255, 214, 120), (236, 96, 40),
                        glow=((255, 120, 40), 110))
    d = ImageDraw.Draw(img)
    d.text((x + 6, 318), "Xbox 360 recomp  \u00b7  native on PS4", font=font(34, "Lato-Regular.ttf"), fill=MUTED)
    # A thin rule under the subtitle, fading out to the right.
    for i in range(520):
        d.point((x + 6 + i, 372), fill=lerp((255, 150, 60), (16, 8, 20), (i / 520) ** 0.8))
    out = os.path.join(ROOT, "docs", "images", "banner.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
