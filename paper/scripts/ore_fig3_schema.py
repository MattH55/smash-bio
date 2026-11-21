#!/usr/bin/env python3
"""ORE proof Figure 3 (submitted as 25644-V1-11-fig2_schema.tiff): structure of one SMASH-BIO record.

The script that drew the submitted figure was not kept. This is a redraw, laid out on the submitted 2055 x 1170 px
image (positions in pixels, y downwards) and drawn in the same font (DejaVu Sans) and palette (figstyle).

ORE copyedit changes: no spaces around "/" ("value/unit"); Bell–Evans with an en dash.
`--orig-text` draws the submitted wording, used only to check the redraw against the submitted image.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from figstyle import BLUE, BLUE_DARK, BLUE_LIGHT, BLUE_PALE, GREY, INK, PAPER  # noqa: E402

W, H, DPI = 2055, 1170, 300
OUT = PAPER / "figures_ore_revised" / "25644-V1-11-fig2_schema.tiff"
PX = 72 / DPI  # one pixel in points
FONT = "DejaVu Sans"
LS = 1.3
plt.rcParams["text.hinting"] = "no_hinting"  # continuous text widths, so sizes can be matched to the submitted image


def box(ax, x, y, w, h, fc="white", ec=GREY, lw=0.5, r=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw))


def text(ax, x, y, s, size, color=INK, ha="left", va="baseline", **kw):
    kw.setdefault("linespacing", LS)
    ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, family=FONT, **kw)


def main(orig: bool, out: Path) -> None:
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")

    # dashed frames
    dash = dict(fc="none", ec=GREY, lw=0.6, ls=(0, (4, 3)))
    ax.add_patch(FancyBboxPatch((24, 45), 1404, 1044, boxstyle="round,pad=0,rounding_size=14", **dash))
    ax.add_patch(FancyBboxPatch((1475, 45), 557, 856, boxstyle="round,pad=0,rounding_size=14", **dash))
    text(ax, 41, 61, "one SMASH-BIO record  (SMFS-######, schema v3.1.0)", 6.19, INK, weight="bold")
    text(ax, 1492, 61, "one SMASH-SIM record  (SIM-######)", 5.59, INK, weight="bold")

    for x, s in ((48, "Table 3 backbone"), (378, "sub-blocks"), (629, "added by SMASH-BIO"), (1021, "one Result")):
        text(ax, x, 146, s, 5.97, BLUE_DARK, weight="bold")

    # Table 3 backbone
    for y, s in zip((206, 377, 548, 719), ("hardware\n(Hardware conditions)", "assay\n(Assay conditions)",
                                           "biological_system\n(Construct parameters)", "solution\n(Factors in solution)")):
        box(ax, 46, y, 284, 137, fc=BLUE_DARK, ec="none")
        text(ax, 188, y + 68.5, s, 5.9, "white", ha="center", va="center", ma="center")
    box(ax, 47, 918, 282, 135, lw=0.6)
    text(ax, 188, 985.5, "publication · scope ·\ncuration · provenance[]", 5.64, INK, ha="center", va="center",
         ma="center")

    # sub-blocks, fanned out from hardware
    subs = ("optical", "magnetic", "afm", "acoustic", "centrifuge", "nanopore", "hydrodynamic", "bfp_micropipette",
            "tension_sensor")
    for i, s in enumerate(subs):
        y = 210 + i * 66.5
        box(ax, 375, y + 1, 205, 50, ec=BLUE, lw=0.5)
        text(ax, 477.5, y + 26, s, 5.22, INK, ha="center", va="center")
        ax.plot([330, 375], [274, y + 26], color=BLUE, lw=0.5, solid_capstyle="butt")
    text(ax, 378, 896, "shared hardware fields:\ndetection, temperature,\nacquisition and filter rate,\ncalibration",
         4.96, GREY, va="top", linespacing=1.27)

    # added by SMASH-BIO
    added = ("technique\n(primary, geometry, modalities)", "results[]", "data_availability\n(status, deposits, raw traces)",
             "annotations\n(software, models, keywords)", "fair_completeness\n(share of Table 3 fields filled)")
    for y, s in zip((176, 324.5, 500, 648, 797), added):
        box(ax, 628, y, 345, 121, fc=BLUE_PALE, ec=BLUE, lw=0.5)
        text(ax, 800.5, y + 60.5, s, 5.28, INK, ha="center", va="center", ma="center")

    # one Result
    ax.plot([973, 1019], [385, 216], color=BLUE, lw=0.5)
    ax.plot([973, 1019], [385, 595], color=BLUE, lw=0.5)
    rows = (("observable", "unfolding_force"), ("value / unit" if orig else "value/unit", "23.4 pN"),
            ("entity", "UniProt P12345"), ("conditions", "loading rate, buffer"), ("model", "Bell–Evans"),
            ("evidence", "snippet, confidence"))
    for i, (k, v) in enumerate(rows):
        y = 188 + i * 70.2
        box(ax, 1019, y, 143, 56, fc=BLUE_LIGHT, ec="none", r=7)
        box(ax, 1165, y + 1, 235, 54, ec=BLUE_LIGHT, lw=0.5, r=7)
        text(ax, 1090.5, y + 28, k, 5.0, INK, ha="center", va="center")
        text(ax, 1282.5, y + 28, v, 5.0, INK, ha="center", va="center")

    # identifiers
    text(ax, 1022, 736, "identifiers (verified flag)", 6.0, BLUE_DARK, weight="bold")
    text(ax, 1021, 775, "on each entity in biological_system", 4.8, GREY)
    ids = ("UniProt", "PDB", "Rfam", "GenBank", "ChEBI", "Cell Ontology", "NCBI Taxonomy")
    for i, s in enumerate(ids):
        x, y = 1020 + (i % 2) * 196, 810 + (i // 2) * 64.7
        box(ax, x, y, 188, 49, lw=0.6, r=6)
        text(ax, x + 94, y + 24.5, s, 4.86, INK, ha="center", va="center")

    # SMASH-SIM record
    sim = ("model\n(family, force field, unit system)", "protocol\n(mode, speed, spring, geometry)",
           "results[]  (same Result structure\n+ toughness, work; unit system)",
           "data_availability\n(trajectories, curves, inputs)", "links[]  → experiment records")
    for i, s in enumerate(sim):
        y = 95 + i * 153
        box(ax, 1498, y, 510, 121, lw=0.6)
        text(ax, 1753, y + 60.5, s, 5.29, INK, ha="center", va="center", ma="center")
    ax.annotate("", xy=(1428, 768), xytext=(1498, 768),
                arrowprops=dict(arrowstyle="-|>", color=BLUE_DARK, lw=0.9, mutation_scale=7, shrinkA=0, shrinkB=0))
    text(ax, 1462, 724.5, "match\nlevel", 4.82, BLUE_DARK, ha="center", va="center", ma="center",
         linespacing=1.1)
    text(ax, 1752.5, 980.5, "match levels: same construct, same geometry ·\nsame molecule, different geometry · homolog",
         4.89, GREY, ha="center", va="center", ma="center")
    text(ax, 1753, 1057, "compared side by side, never merged", 5.43, BLUE_DARK, ha="center", va="center",
         style="italic")

    text(ax, 40, 1143, "dark: Table 3 sections   ·   light blue: added by the schema   ·   white: technique-specific or "
         "external   ·   every automatically filled value carries an evidence object", 5.01, GREY)

    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=DPI, pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)
    print(f"saved {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--orig-text", action="store_true", help="draw the submitted wording (redraw check only)")
    p.add_argument("--out", type=Path, default=OUT)
    a = p.parse_args()
    main(a.orig_text, a.out)
