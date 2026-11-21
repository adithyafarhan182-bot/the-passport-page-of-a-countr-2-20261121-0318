"""Nordhavn — an invented passport spread.

A program that draws one open passport spread for the Republic of
Nordhavn, a small island nation in the North Sea that does not exist:
a data page with a portrait and a machine-readable strip, and a visas
page with arrival and departure stamps from its real neighbours
(Norway, Iceland, the United Kingdom) plus one telling piece of
paperwork — the lighthouse endorsement of section 7 of its Maritime
Code.  All type is set by this program; the portrait is a generated
photograph shipped in assets/.

Writes /output/entry.png (1024 x 1024, under 1 MiB).
"""

from __future__ import annotations

import math
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
FONTS = ASSETS / "fonts"

# ---------------------------------------------------------------- palette
NAVY = (31, 53, 80)          # deep passport navy
NAVY_DARK = (22, 38, 58)
INK = (26, 36, 48)           # body text
LABEL = (90, 100, 112)       # small-caps labels
CREAM = (246, 241, 227)      # page paper
CREAM_DARK = (238, 231, 212)
COVER = (24, 36, 50)         # book cover leather
GOLD = (200, 168, 106)
RULE = (120, 130, 145)

W, H = 1024, 1024

# ---------------------------------------------------------------- fonts


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


SERIF_B = lambda s: font("NotoSerif-Bold.ttf", s)      # noqa: E731
SERIF_I = lambda s: font("NotoSerif-Italic.ttf", s)    # noqa: E731
SANS = lambda s: font("NotoSans-Regular.ttf", s)       # noqa: E731
SANS_B = lambda s: font("NotoSans-Bold.ttf", s)        # noqa: E731
MONO = lambda s: font("DejaVuSansMono.ttf", s)         # noqa: E731


# ---------------------------------------------------------------- text helpers


def tracked_width(draw: ImageDraw.ImageDraw, text: str,
                  fnt: ImageFont.FreeTypeFont, tracking: float) -> float:
    """Width of text drawn with extra space between letters."""
    if not text:
        return 0.0
    total = 0.0
    for ch in text:
        total += draw.textlength(ch, font=fnt) + tracking
    return total - tracking


def draw_tracked(draw: ImageDraw.ImageDraw, xy, text: str,
                 fnt: ImageFont.FreeTypeFont, fill, tracking: float = 0.0):
    """Draw text with letter-spacing, returning the end x."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def draw_centered(draw: ImageDraw.ImageDraw, cx: float, y: float, text: str,
                  fnt: ImageFont.FreeTypeFont, fill, tracking: float = 0.0):
    w = tracked_width(draw, text, fnt, tracking)
    draw_tracked(draw, (cx - w / 2, y), text, fnt, fill, tracking)


def field(draw: ImageDraw.ImageDraw, x: float, y: float, label: str,
          value: str, value_size: int = 14, value_font=None,
          label_size: int = 9):
    """One passport field: small-caps label above a bold value."""
    draw.text((x, y), label, font=SANS(label_size), fill=LABEL)
    draw.text((x, y + 13), value, font=value_font or SANS_B(value_size),
              fill=INK)


# ---------------------------------------------------------------- MRZ (ICAO 9303)


def _mrz_value(ch: str) -> int:
    if ch == "<":
        return 0
    if ch.isdigit():
        return int(ch)
    return ord(ch) - ord("A") + 10


def mrz_check(text: str) -> str:
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(text):
        total += _mrz_value(ch) * weights[i % 3]
    return str(total % 10)


def mrz_lines() -> tuple[str, str]:
    doc = "NVD041788"
    dob = "911108"          # 08 NOV 1991
    expiry = "330314"       # 14 MAR 2033
    personal = "<" * 14
    line1 = ("P<NVD" + "HALVORSEN" + "<<" + "INGRID" + "<" + "MARIE")
    line1 = line1 + "<" * (44 - len(line1))
    doc_c, dob_c, exp_c, per_c = (mrz_check(doc), mrz_check(dob),
                                  mrz_check(expiry), mrz_check(personal))
    # Composite check covers doc+check, dob+check, expiry+check,
    # personal+check only (ICAO 9303) — not nationality or sex.
    composite_in = (doc + doc_c + dob + dob_c + expiry + exp_c
                    + personal + per_c)
    line2 = (doc + doc_c + "NVD" + dob + dob_c + "F" + expiry + exp_c
             + personal + per_c + mrz_check(composite_in))
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


# ---------------------------------------------------------------- guilloche


def guilloche(page: Image.Image, box, colour, alpha: int = 14):
    """Faint concentric arcs, like a security print, clipped to a page."""
    layer = Image.new("RGBA", page.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, y0 - 260
    r = 300
    while r < 1150:
        d.arc([cx - r, cy - r, cx + r, cy + r], 15, 165,
              fill=colour + (alpha,), width=1)
        r += 7
    page.alpha_composite(layer)


# ---------------------------------------------------------------- emblem


def emblem(size: int, colour=NAVY, alpha: int = 255) -> Image.Image:
    """The arms of Nordhavn: a lighthouse in a ring, over three waves."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = colour + (alpha,)
    m = size / 100.0
    d.ellipse([2 * m, 2 * m, 98 * m, 98 * m], outline=c, width=max(2, int(2.4 * m)))
    d.ellipse([7 * m, 7 * m, 93 * m, 93 * m], outline=c, width=max(1, int(1.0 * m)))
    # light beams
    d.polygon([(50 * m, 26 * m), (12 * m, 14 * m), (12 * m, 30 * m)],
              fill=colour + (int(alpha * 0.35),))
    d.polygon([(50 * m, 26 * m), (88 * m, 14 * m), (88 * m, 30 * m)],
              fill=colour + (int(alpha * 0.35),))
    # lantern room + dome
    d.rectangle([44 * m, 22 * m, 56 * m, 30 * m], outline=c,
                width=max(2, int(2.2 * m)))
    d.arc([42 * m, 12 * m, 58 * m, 26 * m], 180, 360, fill=c,
          width=max(2, int(2.2 * m)))
    # tower
    d.polygon([(44 * m, 30 * m), (56 * m, 30 * m), (59 * m, 68 * m),
               (41 * m, 68 * m)], outline=c, width=max(2, int(2.2 * m)))
    d.line([43 * m, 44 * m, 57 * m, 44 * m], fill=c, width=max(1, int(1.6 * m)))
    d.line([42 * m, 56 * m, 58 * m, 56 * m], fill=c, width=max(1, int(1.6 * m)))
    # rock + waves
    d.polygon([(36 * m, 68 * m), (64 * m, 68 * m), (70 * m, 76 * m),
               (30 * m, 76 * m)], fill=c)
    for yy in (80, 86):
        d.arc([26 * m, yy * m, 46 * m, (yy + 8) * m], 180, 360, fill=c,
              width=max(1, int(1.6 * m)))
        d.arc([54 * m, yy * m, 74 * m, (yy + 8) * m], 180, 360, fill=c,
              width=max(1, int(1.6 * m)))
    # two small stars
    for sx in (20, 80):
        d.text((sx * m, 34 * m), "*", font=font("NotoSerif-Bold.ttf",
               max(8, int(14 * m))), fill=c)
    return img


# ---------------------------------------------------------------- canvas


def make_canvas() -> Image.Image:
    """Dark leather table, open book, two cream pages, centre gutter."""
    img = Image.new("RGBA", (W, H), COVER + (255,))
    d = ImageDraw.Draw(img)
    # faint vignette on the cover
    for i in range(60):
        a = int(10 * (1 - i / 60))
        d.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, a))
    # cover peeking out around the pages
    d.rounded_rectangle([18, 32, 1006, 992], radius=10,
                        outline=GOLD + (140,), width=1)
    # pages
    d.rounded_rectangle([30, 44, 510, 980], radius=4, fill=CREAM + (255,))
    d.rounded_rectangle([514, 44, 994, 980], radius=4, fill=CREAM + (255,))
    # gutter shadow
    grad = Image.new("RGBA", (28, 936), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(14):
        gd.line([(i, 0), (i, 936)], fill=(40, 30, 20, int(52 - i * 3.4)))
        gd.line([(27 - i, 0), (27 - i, 936)],
                fill=(40, 30, 20, int(52 - i * 3.4)))
    img.alpha_composite(grad, (498, 44))
    # hairline frames inside each page
    for x0 in (30, 514):
        d.rectangle([x0 + 10, 54, x0 + 470, 970], outline=RULE + (90,),
                    width=1)
    guilloche(img, (30, 44, 510, 980), NAVY, alpha=10)
    guilloche(img, (514, 44, 994, 980), NAVY, alpha=10)
    return img


# ---------------------------------------------------------------- left page: data page


def draw_data_page(img: Image.Image):
    d = ImageDraw.Draw(img, "RGBA")
    x0, x1 = 56, 484          # content column of the left page
    cx = (x0 + x1) / 2

    # arms + country name
    em = emblem(64)
    img.alpha_composite(em, (int(cx - 32), 66))
    draw_centered(d, cx, 138, "REPUBLIC OF NORDHAVN", SERIF_B(19), NAVY,
                  tracking=2.0)
    draw_centered(d, cx, 162, "REPUBLIKKEN NORDHAVN", SANS(10), LABEL,
                  tracking=3.0)
    d.line([x0 + 60, 190, x1 - 60, 190], fill=RULE + (160,), width=1)
    d.line([x0 + 60, 193, x1 - 60, 193], fill=RULE + (110,), width=1)
    draw_centered(d, cx, 202, "PASSPORT", SERIF_B(14), NAVY, tracking=6.0)
    draw_centered(d, cx, 222, "PASS", SANS(9), LABEL, tracking=5.0)

    # portrait, left column
    photo = Image.open(ASSETS / "portrait.png").convert("RGB")
    photo = photo.crop((80, 60, 560, 663)).resize((156, 196), Image.LANCZOS)
    photo = ImageEnhance.Contrast(photo).enhance(1.04)
    photo = ImageEnhance.Color(photo).enhance(0.97)
    img.paste(photo, (x0, 244))
    d.rectangle([x0, 244, x0 + 156, 244 + 196], outline=NAVY + (255,),
                width=2)
    d.rectangle([x0 + 3, 247, x0 + 153, 244 + 193], outline=(255, 255, 255, 90),
                width=1)

    # fields right of the portrait
    fx = x0 + 176
    field(d, fx, 244, "TYPE", "P")
    field(d, fx + 52, 244, "CODE", "NVD")
    field(d, fx + 128, 244, "PASSPORT NO.", "NVD 041 788")
    field(d, fx, 292, "SURNAME", "HALVORSEN")
    field(d, fx, 340, "GIVEN NAMES", "INGRID MARIE")
    field(d, fx, 388, "NATIONALITY", "NORDHAVNIC")

    # lower data grid
    field(d, x0, 458, "DATE OF BIRTH", "08 NOV 1991")
    field(d, x0 + 218, 458, "PLACE OF BIRTH", "HAVNESTAD")
    field(d, x0, 506, "SEX", "F")
    field(d, x0 + 72, 506, "DATE OF ISSUE", "14 MAR 2023")
    field(d, x0 + 252, 506, "DATE OF EXPIRY", "14 MAR 2033")
    field(d, x0, 554, "AUTHORITY", "PASSPORT OFFICE — HAVNESTAD")

    # holder's signature
    d.line([x0, 632, x0 + 200, 632], fill=INK + (255,), width=1)
    d.text((x0 + 6, 600), "Ingrid Halvorsen", font=SERIF_I(21), fill=INK)
    d.text((x0, 638), "HOLDER'S SIGNATURE", font=SANS(9), fill=LABEL)

    # the telling detail: the lighthouse endorsement
    box = (x0, 668, x1, 756)
    d.rounded_rectangle(box, radius=3, fill=(232, 236, 240, 255),
                        outline=NAVY + (200,), width=1)
    d.text((x0 + 12, 678), "ENDORSEMENT", font=SANS_B(10), fill=NAVY)
    d.text((x0 + 12, 696),
           "§7 MARITIME CODE — The holder may land at any",
           font=SANS(11), fill=INK)
    d.text((x0 + 12, 712),
           "lighthouse station of the Republic.",
           font=SANS(11), fill=INK)
    d.text((x0 + 12, 730),
           "Keepers shall render assistance on demand.",
           font=SANS(11), fill=LABEL)

    # machine-readable zone
    line1, line2 = mrz_lines()
    d.rectangle([x0, 782, x1, 838], fill=(255, 255, 255, 255))
    d.rectangle([x0, 782, x1, 838], outline=RULE + (120,), width=1)
    mrz_font = MONO(13)
    draw_tracked(d, (x0 + 8, 790), line1, mrz_font, INK, tracking=0.6)
    draw_tracked(d, (x0 + 8, 812), line2, mrz_font, INK, tracking=0.6)

    # page number
    draw_centered(d, cx, 940, "2", SANS(11), LABEL)


# ---------------------------------------------------------------- stamps


def _stamp_base(size, colour, alpha=205):
    """Transparent layer + draw context for one rubber stamp."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    return layer, ImageDraw.Draw(layer), colour + (alpha,)


def _finish_stamp(img, layer, centre, angle: float):
    """Soften the ink, rotate, and paste the stamp onto the spread."""
    layer = layer.filter(ImageFilter.GaussianBlur(0.5))
    # faint ink speckle, seeded so every run is identical
    rng = random.Random(11)
    sp = ImageDraw.Draw(layer)
    for _ in range(90):
        x = rng.randint(0, layer.width - 1)
        y = rng.randint(0, layer.height - 1)
        if layer.getpixel((x, y))[3] > 40:
            sp.point((x, y), fill=(255, 255, 255, 110))
    layer = layer.rotate(angle, resample=Image.BICUBIC, expand=False)
    img.alpha_composite(
        layer, (int(centre[0] - layer.width / 2),
                int(centre[1] - layer.height / 2)))


def circular_stamp(img, centre, radius, colour, lines, angle=0.0,
                   sizes=(15, 13, 12)):
    layer, d, col = _stamp_base((radius * 2 + 8, radius * 2 + 8), colour)
    c = radius + 4
    d.ellipse([4, 4, radius * 2 + 4, radius * 2 + 4], outline=col, width=3)
    d.ellipse([14, 14, radius * 2 - 6, radius * 2 - 6], outline=col, width=1)
    y = c - (len(lines) - 1) * 11 - 8
    for i, text in enumerate(lines):
        fnt = SANS_B(sizes[min(i, len(sizes) - 1)])
        if i == 0:
            # long place-names must fit inside the inner ring
            maxw = (radius - 18) * 2
            while (d.textlength(text, font=fnt) > maxw
                   and fnt.size > 11):
                fnt = SANS_B(fnt.size - 1)
        w = d.textlength(text, font=fnt)
        d.text((c - w / 2, y), text, font=fnt, fill=col)
        y += 22 if i == 0 else 19
    _finish_stamp(img, layer, centre, angle)


def rectangular_stamp(img, centre, size, colour, lines, angle=0.0,
                      sizes=(13, 12, 11)):
    w, h = size
    layer, d, col = _stamp_base((w + 8, h + 8), colour)
    d.rectangle([4, 4, w + 4, h + 4], outline=col, width=3)
    d.rectangle([9, 9, w - 1, h - 1], outline=col, width=1)
    y = (h + 8) / 2 - (len(lines) - 1) * 10 - 8
    for i, text in enumerate(lines):
        fnt = SANS_B(sizes[min(i, len(sizes) - 1)])
        tw = d.textlength(text, font=fnt)
        d.text(((w + 8) / 2 - tw / 2, y), text, font=fnt, fill=col)
        y += 19
    _finish_stamp(img, layer, centre, angle)


# ---------------------------------------------------------------- right page: visas


def draw_visa_page(img: Image.Image):
    d = ImageDraw.Draw(img, "RGBA")
    x0, x1 = 540, 968          # content column of the right page
    cx = (x0 + x1) / 2

    draw_centered(d, cx, 66, "VISAS", SERIF_B(16), NAVY, tracking=4.0)
    draw_centered(d, cx, 90, "VISUM", SANS(9), LABEL, tracking=4.0)
    d.line([x0 + 90, 112, x1 - 90, 112], fill=RULE + (160,), width=1)

    # Schengen visa sticker (Norway — Nordhavn is outside Schengen)
    sticker = Image.new("RGBA", (400, 156), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sticker)
    sd.rectangle([0, 0, 399, 155], fill=(223, 231, 238, 255),
                 outline=NAVY + (255,), width=2)
    sd.rectangle([5, 5, 394, 150], outline=NAVY + (160,), width=1)
    sd.rectangle([0, 0, 399, 34], fill=NAVY + (255,))
    sd.text((12, 8), "SCHENGEN", font=SANS_B(15), fill=(255, 255, 255, 255))
    sd.text((300, 10), "NORWAY", font=SANS_B(13),
            fill=(255, 255, 255, 255))
    sd.text((12, 46), "VISUM  /  VISA", font=SANS_B(11), fill=NAVY)
    sd.text((12, 66), "VALID FROM  02 JUN 2025", font=SANS_B(12), fill=INK)
    sd.text((12, 86), "UNTIL  01 JUN 2026", font=SANS_B(12), fill=INK)
    sd.text((232, 66), "TYPE  C", font=SANS_B(12), fill=INK)
    sd.text((232, 86), "MULTIPLE ENTRY", font=SANS_B(12), fill=INK)
    sd.text((12, 108), "DURATION OF STAY  90 DAYS", font=SANS_B(12),
            fill=INK)
    sd.text((12, 128), "No. NOR 552 118 904", font=SANS(11), fill=LABEL)
    sd.text((300, 128), "NOR", font=SANS_B(12), fill=NAVY)
    sticker = sticker.rotate(-1.2, resample=Image.BICUBIC, expand=False)
    img.alpha_composite(sticker, (554, 128))

    # faint arms watermark behind the stamps
    wm = emblem(300, colour=NAVY, alpha=16)
    img.alpha_composite(wm, (int(cx - 150), 470))

    # travel history — every stamp after the 14 MAR 2023 issue date,
    # in one June 2025 journey out and home again.
    circular_stamp(img, (648, 392), 62, (31, 78, 121),
                   ["BERGEN", "02 JUN 2025", "ARRIVAL", "NORWAY"],
                   angle=-8)
    circular_stamp(img, (862, 402), 58, (107, 74, 138),
                   ["REYKJAVIK", "09 JUN 2025", "ARRIVAL", "ICELAND"],
                   angle=10)
    rectangular_stamp(img, (652, 556), (176, 66), (163, 51, 39),
                      ["DEPARTED", "NORDHAVN", "02 JUN 2025"], angle=-6)
    circular_stamp(img, (866, 566), 56, (46, 107, 79),
                   ["EDINBURGH", "17 JUN 2025", "ARRIVAL", "U.K."],
                   angle=5)
    circular_stamp(img, (756, 758), 60, (31, 53, 80),
                   ["NORDHAVN", "24 JUN 2025", "ARRIVAL", "HOME"],
                   angle=-4)
    rectangular_stamp(img, (612, 782), (150, 48), (42, 107, 107),
                      ["HARBOUR & LIGHT DUES", "PAID — 12 KR"],
                      angle=3, sizes=(10, 11))

    # ownership line + page number
    draw_centered(d, cx, 912,
                  "This passport remains the property of the Republic "
                  "of Nordhavn.",
                  SERIF_I(11), LABEL)
    draw_centered(d, cx, 940, "3", SANS(11), LABEL)


# ---------------------------------------------------------------- main


def output_path() -> Path:
    """The grader provides /output; fall back to ./output when testing."""
    for cand in (Path("/output/entry.png"),
                 HERE / "output" / "entry.png"):
        try:
            cand.parent.mkdir(parents=True, exist_ok=True)
            with open(cand, "wb"):
                pass
            cand.unlink()
            return cand
        except OSError:
            continue
    return Path("/output/entry.png")


def main() -> None:
    img = make_canvas()
    draw_data_page(img)
    draw_visa_page(img)
    out = output_path()
    img.convert("RGB").save(out, optimize=True)
    size = out.stat().st_size
    print(f"wrote {out} ({img.size[0]}x{img.size[1]}, {size} bytes)")
    assert img.size == (1024, 1024)
    assert size <= 1_048_576, f"entry.png is {size} bytes, over the 1 MiB cap"


if __name__ == "__main__":
    main()
