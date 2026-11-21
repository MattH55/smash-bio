#!/usr/bin/env python3
"""ORE proof Figure 1 (submitted as 25644-V1-11-fig1_experiment.tiff): IMAGE PATCH, not a source edit.

The vector artwork for this figure was not found, so the two ORE copyedit corrections are applied to the submitted
2055 x 1107 px image:
  1. Panel A label: the submitted "A" is cut off at the left edge. It is replaced by a whole "A" drawn the way the
     "B" was drawn (DejaVu Sans Bold, same ink colour and cap height).
  2. Spaces around "=" in the five force formulas: the existing glyphs are moved apart (no re-typesetting), so the
     typeface, subscripts and the vector arrow are the original pixels.
Everything else is the submitted image, pixel for pixel. Replace this with a source edit if the artwork turns up.

usage: ore_fig1_patch.py <submitted 25644-V1-11-fig1_experiment.tiff>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

PAPER = Path(__file__).resolve().parents[1]
OUT = PAPER / "figures_ore_revised" / "25644-V1-11-fig1_experiment.tiff"
INK = (27, 39, 51)
BG = (254, 254, 254)
SP = 5  # px added on each side of "=" (gaps were 2-4 px; a word space at this size is ~7 px)

# (rows y0..y1, cut x positions [F | = | rest], direction) measured on the submitted image.
# Cuts sit in the blank columns between glyphs. "right": "=" moves +SP and the rest +2*SP (free space on the right);
# "left": F moves -2*SP and "=" -SP (the magnetic-tweezers formula has field lines and a magnet just to its right).
FORMULAS = {
    "optical F = k_OT x": (200, 230, (1931, 1941, 1953, 1990), "right"),
    "magnetic F = -grad U": (355, 380, (1864, 1875, 1887, 1919), "left"),
    "AFM F = k_AFM x": (550, 581, (1925, 1936, 1948, 1992), "right"),
    "hydrodynamic F = F_drag": (780, 811, (1970, 1982, 1994, 2028), "right"),
    "acoustic F = F_a": (972, 1000, (1963, 1975, 1986, 2004), "right"),
}


def spread(a: np.ndarray, y0: int, y1: int, cuts: tuple[int, int, int, int], side: str) -> None:
    c0, c1, c2, c3 = cuts
    strip = a[y0:y1, c0:c3].copy()
    shifts = (0, SP, 2 * SP) if side == "right" else (-2 * SP, -SP, 0)
    a[y0:y1, c0 + shifts[0]:c3 + shifts[2]] = BG
    parts = ((c0, c1), (c1, c2), (c2, c3))
    for (p0, p1), dx in zip(parts, shifts):
        a[y0:y1, p0 + dx:p1 + dx] = strip[:, p0 - c0:p1 - c0]


def check_blank(a: np.ndarray, y0: int, y1: int, x0: int, x1: int, what: str) -> None:
    """The area a glyph moves into must be empty background, so nothing else in the artwork is covered."""
    assert (a[y0:y1, x0:x1].min(axis=2) >= 245).all(), f"{what}: target area x{x0}-{x1} y{y0}-{y1} is not blank"


def main(src: Path) -> None:
    im = Image.open(src)
    assert im.size == (2055, 1107) and im.mode == "RGBA", (im.size, im.mode)
    rgba = np.array(im)
    assert (rgba[..., 3] == 255).all()
    a = rgba[..., :3].copy()

    for what, (y0, y1, cuts, side) in FORMULAS.items():
        c0, c3 = cuts[0], cuts[3]
        if side == "right":
            check_blank(a, y0, y1, c3, c3 + 2 * SP, what)
        else:
            check_blank(a, y0, y1, c0 - 2 * SP, c0, what)
        spread(a, y0, y1, cuts, side)

    # panel A: blank the clipped glyph (x 0-14, y 16-42) and draw a whole "A" matching the "B" (x 542-563, y 16-42)
    a[10:48, 0:20] = BG
    img = Image.fromarray(a)
    font = ImageFont.truetype(font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold")), 37)
    d = ImageDraw.Draw(img)
    l, t, r, b = d.textbbox((0, 0), "A", font=font)
    assert abs((b - t) - 27) <= 1, b - t  # cap height of the submitted "B"
    check_blank(np.array(img), 14, 45, 3, 3 + (r - l) + 2, "panel A")
    d.text((4 - l, 16 - t), "A", font=font, fill=INK)

    out = np.dstack([np.array(img), np.full(a.shape[:2], 255, np.uint8)])
    OUT.parent.mkdir(exist_ok=True)
    Image.fromarray(out, "RGBA").save(OUT, dpi=(300, 300), compression="tiff_lzw")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
