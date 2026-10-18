#!/usr/bin/env python3
"""Pie chart of optical-tweezers papers by author affiliation category.

Reads ot_affiliation_per_paper.csv (written by ot_affiliation_classifier.py) and
draws a pie chart of the paper-level classification counts.

The "industry" and "mixed" categories are EXCLUDED by default, so the chart
shows only the remaining categories: academic, no_affiliation,
non_research_article and unknown.

Usage:
    python plot_ot_affiliation_pie.py
    python plot_ot_affiliation_pie.py --input other.csv --output chart.png
"""

import argparse
import collections
import csv
import math
import sys

import matplotlib

matplotlib.use("Agg")  # headless: write straight to file, no display needed
import matplotlib.pyplot as plt

PER_PAPER_CSV = "ot_affiliation_per_paper.csv"
OUT_PNG = "ot_affiliation_pie.png"

# Categories left out of the chart.
EXCLUDED_LABELS = {"industry", "mixed"}

# Display order and colours for the categories that are shown. Colours are
# chosen to stay distinguishable in greyscale and for colour-blind readers.
CATEGORY_ORDER = [
    ("academic", "Academic", "#4C72B0"),
    ("no_affiliation", "No affiliation listed", "#DD8452"),
    ("non_research_article", "Non-research article", "#55A868"),
    ("unknown", "Unclassified", "#C44E52"),
]


def load_counts(path=PER_PAPER_CSV):
    """Count paper-level classifications, dropping the excluded categories."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        sys.exit(f"error: {path} not found; run ot_affiliation_classifier.py first")

    counts = collections.Counter(r["classification"] for r in rows)
    if not counts:
        sys.exit(f"error: no rows found in {path}")

    for label in EXCLUDED_LABELS:
        counts.pop(label, None)
    return counts


def make_pie(counts, out_path=OUT_PNG):
    """Draw the pie chart and save it to out_path."""
    labels, sizes, colours = [], [], []
    for key, display, colour in CATEGORY_ORDER:
        if counts.get(key):
            labels.append(display)
            sizes.append(counts[key])
            colours.append(colour)

    # Preserve any category present in the data but not in CATEGORY_ORDER, so
    # a future classifier change cannot silently drop a slice from the chart.
    known = {k for k, _, _ in CATEGORY_ORDER}
    for key in sorted(counts):
        if key not in known:
            labels.append(key)
            sizes.append(counts[key])
            colours.append("#999999")

    total = sum(sizes)
    fig, ax = plt.subplots(figsize=(9, 7))

    # Counts and percentages are both labelled: with one dominant slice the
    # small categories are invisible, so the absolute numbers matter.
    def autopct(pct):
        count = pct / 100 * total
        return f"{count:,.0f}\n({pct:.1f}%)" if pct >= 1 else ""

    wedges, _texts, autotexts = ax.pie(
        sizes,
        labels=None,
        colors=colours,
        autopct=autopct,
        startangle=90,
        counterclock=False,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        textprops={"fontsize": 10},
    )
    for t in autotexts:
        t.set_fontsize(10)
        t.set_fontweight("bold")
        t.set_color("white")

    # Slices below ~2% are too thin to hold a legible label, so they are
    # annotated outside the rim with a leader line. The text is stacked
    # vertically and pushed above the pie to keep the rare-category labels from
    # overlapping each other or the title.
    small = [i for i, s in enumerate(sizes) if s / total * 100 < 2]
    for slot, i in enumerate(small):
        wedge = wedges[i]
        angle = math.radians((wedge.theta1 + wedge.theta2) / 2)
        x, y = math.cos(angle), math.sin(angle)
        # One text row per rare slice, stacked upward from the top of the pie.
        ty = 1.16 + slot * 0.19
        ax.annotate(
            f"{labels[i]}  n={sizes[i]:,} ({sizes[i] / total * 100:.2f}%)",
            xy=(0.99 * x, 0.99 * y),
            xytext=(0.30, ty),
            ha="left",
            va="center",
            fontsize=9,
            color="#333333",
            arrowprops={
                "arrowstyle": "-",
                "color": "#666666",
                "linewidth": 0.9,
                "connectionstyle": "angle,angleA=0,angleB=90,rad=0",
            },
        )

    ax.legend(
        wedges,
        [f"{lab} (n={s:,})" for lab, s in zip(labels, sizes)],
        loc="center left",
        bbox_to_anchor=(1.30, 0.5),
        frameon=False,
        fontsize=10,
    )
    ax.set_title(
        f"Optical tweezers papers by author affiliation\n"
        f"(n={total:,}; industry and mixed papers excluded)",
        fontsize=12,
        fontweight="bold",
        pad=70,
    )
    # "equal" keeps the pie circular; it also sets the limits, so it must come
    # last (explicit limits here would be overridden and warn).
    ax.axis("equal")
    ax.set_ylim(-1.05, 1.55)

    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path, total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=PER_PAPER_CSV,
                        help=f"per-paper CSV to read (default: {PER_PAPER_CSV})")
    parser.add_argument("--output", default=OUT_PNG,
                        help=f"output image path (default: {OUT_PNG})")
    args = parser.parse_args()

    counts = load_counts(args.input)
    out_path, total = make_pie(counts, args.output)

    print(f"Excluded categories: {', '.join(sorted(EXCLUDED_LABELS))}", file=sys.stderr)
    print(f"Chart total: {total:,} papers", file=sys.stderr)
    for key, display, _ in CATEGORY_ORDER:
        n = counts.get(key, 0)
        print(f"  {display}: {n:,} ({n / total * 100:.2f}%)", file=sys.stderr)
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
