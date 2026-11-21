#!/usr/bin/env python3
"""ORE proof Figure 5 (submitted as 25644-V1-11-fig3_corpus.tiff): the corpus at release.

The script that drew the submitted figure was not kept. This is a redraw on the submitted figure's geometry
(an 8 in wide figstyle figure saved at 2055 px, in DejaVu Sans). Values come from the frozen v3.1.0 release:
panel A counts records per publication year and technique in data/smash-smfs-records.jsonl.gz (all 7694 records,
schema 3.1.0); panel B reads out/corpus_stats.json. Nothing is recomputed by corpus_stats.py.

ORE copyedit changes: sentence case; four-digit numbers without a comma (7694); no spaces around "/".
`--orig-text` draws the submitted wording, used only to check the redraw against the submitted image.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from PIL import Image  # noqa: E402
from figstyle import BLUE, BLUE_DARK, BLUE_LIGHT, GREY, GREY_LIGHT, INK, PAPER, num, stats  # noqa: E402

W_IN, W_PX, H_PX = 8.0, 2055, 825
SAVE_DPI = W_PX / W_IN  # the submitted figure was drawn 8 in wide and exported 2055 px wide (300 dpi tag)
OUT = PAPER / "figures_ore_revised" / "25644-V1-11-fig3_corpus.tiff"
RECORDS = PAPER / "data" / "smash-smfs-records.jsonl.gz"
FONT = "DejaVu Sans"
TECHS = (("optical_tweezers", "Optical tweezers", BLUE_DARK), ("afm_smfs", "AFM force spectroscopy", BLUE),
         ("magnetic_tweezers", "Magnetic tweezers", BLUE_LIGHT))


def counts_by_year() -> tuple[list[int], dict[str, list[int]]]:
    by: dict[int, Counter] = defaultdict(Counter)
    n = 0
    with gzip.open(RECORDS, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            assert r["schema_version"] == "3.1.0"
            t = r["technique"]["primary"]
            by[r["publication"]["year"]][t if t in dict((k, 0) for k, _, _ in TECHS) else "other"] += 1
            n += 1
    assert n == 7694, n
    years = sorted(by)
    return years, {k: [by[y][k] for y in years] for k in ("other", *(k for k, _, _ in TECHS))}


def tiles(s: dict, sim: dict, orig: bool) -> list[tuple[str, str, str]]:
    sm = s
    assert sm["n_deposits_linked"] == 634 and sm["pct_fulltext_checked"] == 28.7
    curated, ai = sm["curation_levels"]["curated"], sm["curation_levels"]["ai_assisted"]
    n = (lambda v: f"{v:,}") if orig else num
    rows = [
        (n(sm["n_records"]), "studies indexed", f"{sm['year_min']}–{sm['year_max']}, {sm['n_techniques']} techniques"),
        (n(sm["n_records_with_uniprot"]), "UniProt-linked systems", f"{n(sm['identifiers_any']['uniprot'])} distinct accessions"),
        (n(sm["n_fulltext_checked"]), "full texts read", f"{sm['pct_fulltext_checked']}% of records"),
        (n(sm["n_deposits"]), "deposits catalogued", f"{sm['n_deposits_linked']} linked to {sm['n_with_dataset']} studies"),
        (n(sm["n_results_extracted"]), "results extracted", f"in {sm['n_records_with_results']} records"),
        (n(sm["n_with_raw_traces"]), "with raw force traces", "deposit classed as traces"),
        (n(sim["n_sim_records"]), "simulation records", f"{sim['n_sim_records_with_a_link']} linked to experiments"),
        (n(sim["n_links"]), "simulation–experiment links",
         f"{n(sim['links_by_match_level']['same_molecule_different_geometry'])} same molecule"),
        (n(curated + ai), "curated or AI-assisted", f"{curated} curated · {ai} AI-assisted"),
    ]
    if orig:
        return rows
    cap = lambda t: t[0].upper() + t[1:]  # noqa: E731  (sentence case; leaves "UniProt", "AI" and numbers alone)
    return [(a, cap(b), cap(c)) for a, b, c in rows]


def main(orig: bool, out: Path) -> None:
    plt.rcParams.update({"font.family": FONT, "font.sans-serif": [FONT], "text.hinting": "no_hinting"})
    st = stats()
    s, sim = st["smfs"], st["sim"]
    years, c = counts_by_year()

    fig = plt.figure(figsize=(W_IN, W_IN * H_PX / W_PX))
    ax = fig.add_axes([0.07, 0.15, 0.42, 0.80])
    bottom = [0] * len(years)
    series = [("other", "other / unspecified" if orig else "Other/unspecified", GREY)] + list(TECHS)
    for k, label, col in series:
        ax.bar(years, c[k], bottom=bottom, width=0.8, color=col, edgecolor="white", linewidth=0.5, zorder=2)
        bottom = [b + v for b, v in zip(bottom, c[k])]
    last = years[-1]
    ax.add_patch(Rectangle((last - 0.4, 0), 0.8, bottom[-1], fill=False, ec=INK, lw=0.8, ls=(0, (1, 1)), zorder=3))
    ax.set_xlim(1985.24, 2026.77)
    ax.set_ylim(0, 1.05 * max(bottom))
    ax.set_xticks(range(1990, 2026, 5))
    ax.yaxis.grid(True, color="#dfdfdf", lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=7.62)
    ax.tick_params(axis="x", pad=4.05)
    ax.set_xlabel("Publication year", fontsize=8.12, labelpad=4.6)
    ax.set_ylabel("Indexed records per publication year", fontsize=8.2, labelpad=4.85)

    # overlay in pixels of the exported image (y downwards): legend, partial-year note, panel B, panel letters
    ov = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ov.set_xlim(0, W_PX)
    ov.set_ylim(H_PX, 0)
    ov.axis("off")
    for i, (_, label, col) in enumerate(series):
        y = 65 + i * 35
        ov.add_patch(Rectangle((160, y - 7), 20, 15, color=col, lw=0))
        ov.text(201, y, label, fontsize=6.56, va="center", ha="left")
    ov.text(990.5, 138, "partial\nyear" if orig else "Partial\nyear", fontsize=5.96, color=GREY, ha="center", va="center",
            linespacing=1.2)
    ov.text(41, 31, "A", fontsize=10.7, fontweight="bold", ha="right", va="baseline")
    ov.text(1069, 30, "B", fontsize=10.5, fontweight="bold", ha="right", va="baseline")

    for i, (big, label, sub) in enumerate(tiles(s, sim, orig)):
        x, y = (1082, 1404, 1725)[i % 3], (32, 296, 560)[i // 3]
        ov.add_patch(Rectangle((x + 0.5, y + 0.5), 297, 233, fill=False, ec=GREY_LIGHT, lw=0.6))
        ov.text(x + 21, y + 70, big, fontsize=11.73, fontweight="bold", color=BLUE_DARK, va="baseline")
        # the submitted figure let this one label run past its tile border; the revision fits it inside the tile
        fit = not orig and label.startswith("Simulation–")
        ov.text(x + 20, y + 137, label, fontsize=5.35 if fit else 5.99, color=INK, va="baseline")
        ov.text(x + 21, y + 189, sub, fontsize=5.15, color=GREY, va="baseline")

    out.parent.mkdir(exist_ok=True)
    tmp = out.with_suffix(".tmp.png")
    fig.savefig(tmp, dpi=SAVE_DPI)
    plt.close(fig)
    im = Image.open(tmp)
    assert im.size == (W_PX, H_PX), im.size
    im.save(out, dpi=(300, 300), compression="tiff_lzw")
    tmp.unlink()
    print(f"saved {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--orig-text", action="store_true", help="draw the submitted wording (redraw check only)")
    p.add_argument("--out", type=Path, default=OUT)
    a = p.parse_args()
    main(a.orig_text, a.out)
