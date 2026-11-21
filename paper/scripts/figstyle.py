"""Shared figure style and export for the manuscript (Biophysical Journal: 85 mm / 174 mm, >= 300 dpi)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PAPER = Path(__file__).resolve().parents[1]
FIGS = PAPER / "figures"
MM = 1 / 25.4
COL1, COL2 = 85 * MM, 174 * MM

# One colour family (blue) plus grey for "not checked / not applicable". Checked for colour-blind safety by
# varying lightness as well as hue.
INK = "#1b2733"
BLUE_DARK, BLUE, BLUE_LIGHT, BLUE_PALE = "#12395f", "#2f6fa8", "#8db7dc", "#dbe8f4"
GREY, GREY_LIGHT = "#8c8c8c", "#d9d9d9"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "axes.titlesize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "figure.dpi": 150, "savefig.dpi": 300, "lines.linewidth": 1.0,
})


def stats() -> dict:
    return json.loads((PAPER / "out" / "corpus_stats.json").read_text(encoding="utf-8"))


def num(n: int) -> str:
    """ORE number style: four-digit numbers plain (7694); five or more digits grouped with a thin space U+2009 (15 867)."""
    return f"{n:,}".replace(",", " ") if abs(n) >= 10000 else str(n)


def arial_mathtext() -> None:
    """Render $...$ in Arial so an italic n or "not checked" matches the surrounding text (ORE copyedit)."""
    plt.rcParams.update({"mathtext.fontset": "custom", "mathtext.rm": "Arial", "mathtext.it": "Arial:italic",
                         "mathtext.bf": "Arial:bold"})


def panel_letter(ax, letter: str, x: float = -0.02, y: float = 1.02) -> None:
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=9, fontweight="bold", va="bottom", ha="right")


def save(fig, name: str) -> None:
    """Write figures/<name>.pdf (vector), .tiff (300 dpi, LZW) and .png (preview for the Word/PDF build)."""
    FIGS.mkdir(exist_ok=True)
    fig.savefig(FIGS / f"{name}.pdf")
    fig.savefig(FIGS / f"{name}.tiff", dpi=300, pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(FIGS / f"{name}.png", dpi=300)
    plt.close(fig)
    print(f"saved figures/{name}.[pdf|tiff|png]")
