#!/usr/bin/env python3
"""Pie chart of cryo-EM papers by author affiliation category.

Reads cryoem_affiliation_per_paper.csv (written by cryoem_affiliation_classifier.py)
and draws a pie chart of the paper-level classification counts.

Two modes:
  * excluded (default): drops "industry" and "mixed", matching the OT chart's
    convention, so the two pies can be placed side by side.
  * with-affiliations: keeps industry/mixed but drops the records that carry no
    affiliation information at all (no_affiliation, non_research_article), so
    every slice is a real classification decision.

Usage:
    python plot_cryoem_affiliation_pie.py
    python plot_cryoem_affiliation_pie.py --with-affiliations \
        --output cryoem_affiliation_pie_with_affiliations.png
"""

import argparse
import collections
import csv
import math
import sys

import matplotlib

matplotlib.use("Agg")  # headless: write straight to file, no display needed
import matplotlib.pyplot as plt

PER_PAPER_CSV = "cryoem_affiliation_per_paper.csv"
OUT_PNG = "cryoem_affiliation_pie.png"

# Categories left out in the default (OT-comparable) mode.
EXCLUDED_LABELS = {"industry", "mixed"}

# Categories dropped in --with-affiliations mode: these carry no evidence about
# who wrote the paper, so they cannot be plotted as a classification outcome.
NON_EVIDENTIAL = ("no_affiliation", "non_research_article")

# Display order and colours for the categories that are shown. Colours are
# chosen to stay distinguishable in greyscale and for colour-blind readers.
CATEGORY_ORDER = [
    ("academic", "Academic", "#4C72B0"),
    ("industry", "Industry", "#C44E52"),
    ("mixed", "Mixed (industry + academic)", "#8172B2"),
    ("no_affiliation", "No affiliation listed", "#DD8452"),
    ("non_research_article", "Non-research article", "#55A868"),
    ("unknown", "Unclassified", "#937860"),
]


def load_counts(path=PER_PAPER_CSV, with_affiliations=False):
    """Count paper-level classifications, dropping the categories not shown."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        sys.exit(f"error: {path} not found; run cryoem_affiliation_classifier.py first")

    counts = collections.Counter(r["classification"] for r in rows)
    if not counts:
        sys.exit(f"error: no rows found in {path}")

    drop = NON_EVIDENTIAL if with_affiliations else EXCLUDED_LABELS
    for label in drop:
        counts.pop(label, None)
    return counts


def make_pie(counts, out_path=OUT_PNG, with_affiliations=False):
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

    # The in-wedge label is only legible for slices wide enough to hold it.
    # A single threshold does not work: at 6% a two-line label still fits, but
    # below ~3% it spills past the wedge edges and neighbouring labels collide
    # in the middle of the pie. So anything under 3% gets no in-wedge label and
    # is carried by a leader line instead.
    IN_WEDGE_MIN_PCT = 3.0

    def autopct(pct):
        count = pct / 100 * total
        return f"{count:,.0f}\n({pct:.1f}%)" if pct >= IN_WEDGE_MIN_PCT else ""

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

    # Thin slices are annotated outside the rim with a leader line. The text is
    # stacked vertically and pushed clear of the pie so the labels cannot
    # overlap each other, the in-wedge numbers, or the title. Two decimals are
    # used because a single decimal would print "0.0%" for a non-zero count.
    small = [i for i, s in enumerate(sizes) if s / total * 100 < IN_WEDGE_MIN_PCT]
    for slot, i in enumerate(small):
        wedge = wedges[i]
        angle = math.radians((wedge.theta1 + wedge.theta2) / 2)
        x, y = math.cos(angle), math.sin(angle)
        # One text row per thin slice. Rows are stacked starting just above the
        # pie; anchored to the right of the wheel so the leader lines running
        # up from the top-of-wheel wedges never cross the text.
        ty = 1.02 + slot * 0.13
        ax.annotate(
            f"{labels[i]}  n={sizes[i]:,} ({sizes[i] / total * 100:.2f}%)",
            xy=(0.99 * x, 0.99 * y),
            xytext=(0.62, ty),
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
    subtitle = ("papers with an affiliation only, industry and mixed included"
                if with_affiliations
                else "industry and mixed papers excluded")
    ax.set_title(
        f"Cryo-EM papers by author affiliation\n(n={total:,}; {subtitle})",
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
    parser.add_argument("--with-affiliations", action="store_true",
                        help="keep industry/mixed and drop records with no "
                             "affiliation (affiliations-only denominator)")
    args = parser.parse_args()

    counts = load_counts(args.input, with_affiliations=args.with_affiliations)
    out_path, total = make_pie(counts, args.output,
                               with_affiliations=args.with_affiliations)

    dropped = NON_EVIDENTIAL if args.with_affiliations else sorted(EXCLUDED_LABELS)
    print(f"Excluded categories: {', '.join(dropped)}", file=sys.stderr)
    print(f"Chart total: {total:,} papers", file=sys.stderr)
    for key, display, _ in CATEGORY_ORDER:
        if key in counts:
            n = counts[key]
            print(f"  {display}: {n:,} ({n / total * 100:.2f}%)", file=sys.stderr)
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()