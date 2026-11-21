#!/usr/bin/env python3
"""Figure 3: what the hub shows about the field. Every value is read from out/corpus_stats.json."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import matplotlib.pyplot as plt  # noqa: E402
from figstyle import (BLUE, BLUE_DARK, BLUE_LIGHT, COL2, GREY, GREY_LIGHT, INK, arial_mathtext, num,  # noqa: E402
                      panel_letter, save, stats)
from corpus_stats import TECH_LABELS  # noqa: E402


def noslash(label: str) -> str:
    """ORE copyedit: no spaces around "/" in figure text. Applied here only, because TECH_LABELS and the stats keys also feed Table 2."""
    return label.replace(" / ", "/")


MIN_RECORDS_B = 30  # techniques with fewer records are omitted from panel B (listed in Table 2)


def panel_a(ax, s: dict) -> None:
    rows = [y for y in s["availability_by_year"] if y["drawn_in_fig3a"]]
    years = [y["year"] for y in rows]
    share = [100 * y["n_with_dataset"] / y["n_checked"] for y in rows]
    size = [y["n_checked"] / 3.2 for y in rows]
    ax.plot(years, share, color=BLUE, lw=1.0, zorder=2)
    ax.scatter(years[:-1], share[:-1], s=size[:-1], color=BLUE_DARK, zorder=3, linewidths=0)
    ax.scatter(years[-1:], share[-1:], s=size[-1:], facecolor="white", edgecolor=BLUE_DARK, lw=0.8, zorder=3)
    ax.set_xlim(2003, 2027.5)
    ax.set_ylim(0, 38)
    ax.set_xticks(range(2005, 2026, 5))
    ax.set_ylabel("Checked studies with a\nlinked repository deposit (%)")
    for y, v, dy in ((2019, share[years.index(2019)], 3.0), (2025, share[years.index(2025)], 3.4)):
        ax.annotate(f"{v:.1f}%", (y, v), xytext=(0, dy * 2.2), textcoords="offset points", ha="center", fontsize=6.5)
    ax.annotate("2026 partial\nyear", (2026, share[-1]), xytext=(2026.3, 8), fontsize=6, ha="center", color=GREY,
                arrowprops=dict(arrowstyle="-", color=GREY, lw=0.5))
    ax.text(0.02, 0.97, "Marker area = studies checked\nin that year", transform=ax.transAxes, fontsize=6,
            color=GREY, va="top")


def panel_b(ax, s: dict) -> None:
    items = [(k, v) for k, v in s["by_technique"].items() if v["records"] >= MIN_RECORDS_B]
    items.sort(key=lambda kv: kv[1]["records"])  # barh draws bottom-up, so largest ends on top
    ypos = range(len(items))
    for y, (k, v) in zip(ypos, items):
        n = v["records"]
        with_ds = 100 * v["with_dataset"] / n
        checked_no = 100 * (v["checked"] - v["with_dataset"]) / n
        not_checked = 100 * (n - v["checked"]) / n
        ax.barh(y, with_ds, color=BLUE_DARK, height=0.7)
        ax.barh(y, checked_no, left=with_ds, color=BLUE_LIGHT, height=0.7)
        ax.barh(y, not_checked, left=with_ds + checked_no, color=GREY_LIGHT, height=0.7)
        ax.text(101.5, y, f"{v['with_dataset']}/{num(n)}" + (f"  ({v['raw_traces']} raw)" if v["raw_traces"] else ""),
                va="center", fontsize=6)
    ax.set_yticks(list(ypos))
    ax.set_yticklabels([noslash(TECH_LABELS[k]) for k, _ in items])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of records (%)")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    # direct labels instead of a legend box, placed on the top bar
    top = len(items) - 1
    v = items[top][1]
    n = v["records"]
    ax.text(0, top + 0.8, "Linked deposit", ha="left", va="bottom", fontsize=6, color=BLUE_DARK)
    ax.text(32, top + 0.8, "Checked, none", ha="left", va="bottom", fontsize=6, color=BLUE)
    ax.text(72, top + 0.8, "Not checked", ha="left", va="bottom", fontsize=6, color=GREY)
    ax.set_ylim(-0.6, top + 1.9)


def panel_c(ax, s: dict) -> None:
    cov = s["field_coverage_pct"]
    items = sorted(((k, v) for k, v in cov.items() if k != "Linked dataset"), key=lambda kv: kv[1]["fulltext"])
    for y, (k, v) in enumerate(items):
        ax.barh(y + 0.19, v["all"], height=0.36, color=GREY_LIGHT)
        ax.barh(y - 0.19, v["fulltext"], height=0.36, color=BLUE)
        ax.text(v["fulltext"] + 1, y - 0.19, f"{v['fulltext']:.0f}", va="center", fontsize=5.8, color=BLUE_DARK)
        ax.text(v["all"] + 1, y + 0.19, f"{v['all']:.0f}", va="center", fontsize=5.8, color=GREY)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([noslash(k) for k, _ in items])
    ax.set_xlim(0, 80)
    ax.set_xlabel("Records with the field populated (%)")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    nf, na = s["fair_completeness"]["n_fulltext"], s["n_records"]
    ax.text(79, 1.2, f"Full text read\n($n$ = {num(nf)})", ha="right", va="center", fontsize=6.2, color=BLUE)
    ax.text(79, 3.3, f"All records\n($n$ = {num(na)})", ha="right", va="center", fontsize=6.2, color=GREY)


def main() -> None:
    arial_mathtext()
    s = stats()["smfs"]
    fig = plt.figure(figsize=(COL2, 4.6 * COL2 / 6.85 * 0.98))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.15], wspace=1.0, left=0.10, right=0.84, top=0.95, bottom=0.60)
    a = fig.add_subplot(gs[0, 0])
    b = fig.add_subplot(gs[0, 1])
    c = fig.add_axes([0.24, 0.08, 0.70, 0.40])
    panel_a(a, s)
    panel_b(b, s)
    panel_c(c, s)
    panel_letter(a, "A", x=-0.28)
    panel_letter(b, "B", x=-0.75)
    panel_letter(c, "C", x=-0.30)
    save(fig, "fig3_field")


if __name__ == "__main__":
    main()
