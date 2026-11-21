#!/usr/bin/env python3
"""Figure 2: the record-construction pipeline with live counts from out/corpus_stats.json."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from figstyle import BLUE, BLUE_DARK, BLUE_PALE, COL2, GREY, GREY_LIGHT, INK, arial_mathtext, num, save, stats  # noqa: E402


def box(ax, x, y, w, h, title, lines, fc=BLUE_PALE, ec=BLUE, tc=BLUE_DARK, bc=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12", fc=fc, ec=ec, lw=0.8))
    ax.text(x + w / 2, y + h - 0.16, title, ha="center", va="top", fontsize=7, fontweight="bold", color=tc)
    ax.text(x + w / 2, y + h - 0.62, "\n".join(lines), ha="center", va="top", fontsize=5.9, color=bc,
            linespacing=1.35)


def arrow(ax, x0, y0, x1, y1):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=7, lw=0.8, color=INK))


def main() -> None:
    arial_mathtext()
    S = stats()
    s, h, m = S["smfs"], S["harvest"], S["sim"]
    tiers = h["scope_tiers"]
    fig = plt.figure(figsize=(COL2, 1.75))
    ax = fig.add_axes([0.004, 0.02, 0.992, 0.96])
    ax.set_xlim(0, 21.4)
    ax.set_ylim(0, 4.9)
    ax.axis("off")
    W, Hh, Y = 3.0, 3.2, 1.0
    xs = [0.1 + i * 3.55 for i in range(6)]
    box(ax, xs[0], Y, W, Hh, "1  Harvest", ["Europe PMC and", "DataCite, one", "query set per", "technique", "", f"{num(h['n_harvested_classified'])}", "candidate papers"])
    box(ax, xs[1], Y, W, Hh, "2  Scope", ["Rule-based", "classifier", "", f"{num(tiers['core'])} core", f"{num(tiers['methods'])} methods", f"{num(tiers['peripheral'])} peripheral", f"{num(tiers['out'])} out", f"{h['n_removed_after_review']} removed in review"])
    box(ax, xs[2], Y, W, Hh, "3  Link data", ["DataCite, Scholix,", "Europe PMC links,", "accessions, data", "statements", "", f"{num(s['n_with_any_data'])} any data", f"{num(s['n_with_dataset'])} with deposit"])
    box(ax, xs[3], Y, W, Hh, "4  Annotate", ["Gazetteer to IDs;", "Methods text;", "abstract results", "", f"{num(s['n_records_with_uniprot'])} UniProt-linked", f"{num(s['n_fulltext_checked'])} full text read", f"{num(s['n_records_with_results'])} with results"])
    box(ax, xs[4], Y, W, Hh, "5  Curate", ["Curator and author", "values override", "automatic ones", "", f"{s['n_curated']} curated", f"{s['curation_levels']['ai_assisted']} AI-assisted", f"{s['n_author_verified']} author-verified"])
    box(ax, xs[5], Y, W, Hh, "6  Publish", ["Site, JSONL,", "CSV, schemas", "", f"{num(s['n_records'])} records", f"{num(s['n_deposits'])} deposits", f"{m['n_sim_records']} simulation", "records"], fc=BLUE_DARK, ec=BLUE_DARK, tc="white", bc="white")
    for i in range(5):
        arrow(ax, xs[i] + W + 0.03, Y + Hh / 2, xs[i + 1] - 0.03, Y + Hh / 2)
    ax.text(xs[2], 0.75, "Every automatically filled value stores an evidence object (method, snippet, confidence).", fontsize=6, color=GREY, va="top")
    ax.text(xs[0], 0.75, r"Records without readable full text are marked $\it{not\ checked}$.", fontsize=6, color=GREY, va="top")
    ax.text(xs[5] + W, 4.85, f"{num(m['n_links'])} simulation–experiment links, never merged", fontsize=6, color=GREY, va="top", ha="right")
    ax.text(0.1, 4.85, "Counts are for the release described here (schema v3.1.0).", fontsize=6, color=GREY, va="top")
    save(fig, "fig2_pipeline")


if __name__ == "__main__":
    main()
