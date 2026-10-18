#!/usr/bin/env python3
"""Compare cryo-EM and optical-tweezers industry involvement, restricted to
papers that actually carry an affiliation.

Why the restriction: a paper with no affiliation in PubMed carries no evidence
either way about who wrote it, so counting it in the denominator dilutes the
rate by an amount that depends purely on how well that journal/country reports
affiliations -- not on industry involvement. The two corpora differ sharply
there (cryo-EM 2.3% missing vs OT 11.1% missing), so the unrestricted rates are
not directly comparable. This script computes both, so the reader can see how
much of the gap is real and how much is the denominator.

Excluded from the "affiliations only" denominator:
  * no_affiliation        - nothing to classify
  * non_research_article  - journal/editorial contact addresses, not authors

Reads both per-paper CSVs; does not modify the shared classifier.

Usage:
    python compare_affiliation_rates.py
"""

import argparse
import collections
import csv
import sys

NON_EVIDENTIAL = ("no_affiliation", "non_research_article")

DISPLAY = {
    "industry": "Industry only",
    "academic": "Academic only",
    "mixed": "Mixed (industry + academic)",
    "unknown": "Unknown (matched neither list)",
    "no_affiliation": "No affiliation in PubMed",
    "non_research_article": "Non-research article",
}

ORDER = ["industry", "academic", "mixed", "unknown",
         "no_affiliation", "non_research_article"]


def load(path):
    """Return per-paper classification counts for one corpus."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        sys.exit(f"error: {path} not found")
    if not rows:
        sys.exit(f"error: no rows in {path}")
    return collections.Counter(r["classification"] for r in rows)


def summarise(name, counts):
    """Compute the two denominators for one corpus."""
    total = sum(counts.values())
    non_evidential = sum(counts[k] for k in NON_EVIDENTIAL)
    with_aff = total - non_evidential

    industry_only = counts.get("industry", 0)
    mixed = counts.get("mixed", 0)
    or_mixed = industry_only + mixed

    return {
        "name": name,
        "total": total,
        "non_evidential": non_evidential,
        "with_aff": with_aff,
        "industry_only": industry_only,
        "mixed": mixed,
        "or_mixed": or_mixed,
        "rate_all": or_mixed / total * 100,
        "rate_with_aff": or_mixed / with_aff * 100 if with_aff else 0.0,
        "academic": counts.get("academic", 0),
        "unknown": counts.get("unknown", 0),
        "no_affiliation": counts.get("no_affiliation", 0),
        "non_research_article": counts.get("non_research_article", 0),
    }


def emit(lines, out_path):
    """Print the report and write it to a file as UTF-8.

    The file is written from inside Python rather than by redirecting the
    shell's stdout, because PowerShell's redirection writes UTF-16 with a BOM
    and can truncate a large stream.
    """
    text = "\n".join(lines)
    print(text)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")


def build_report(corpora):
    """Assemble the report as a list of lines."""
    cryoem, ot = corpora
    L = []
    bar = "=" * 78

    L.append("")
    L.append(bar)
    L.append("INDUSTRY INVOLVEMENT: ALL PAPERS vs PAPERS WITH AN AFFILIATION")
    L.append(bar)

    for c in corpora:
        L.append("")
        L.append(f"{c['name']}")
        L.append(f"  papers in corpus                            {c['total']:>8,}")
        L.append(f"  less: no affiliation in PubMed              "
                 f"{c['no_affiliation']:>8,}")
        L.append(f"  less: non-research article                  "
                 f"{c['non_research_article']:>8,}")
        L.append(f"  = denominator (papers with an affiliation)  "
                 f"{c['with_aff']:>8,}")
        L.append(f"  industry                                    "
                 f"{c['industry_only']:>8,}")
        L.append(f"  mixed                                       "
                 f"{c['mixed']:>8,}")
        L.append(f"  industry or mixed                           "
                 f"{c['or_mixed']:>8,}")
        L.append(f"  ...of ALL papers                     "
                 f"{c['rate_all']:>6.1f}%")
        L.append(f"  ...of papers WITH AN AFFILIATION     "
                 f"{c['rate_with_aff']:>6.1f}%")

    L.append("")
    L.append(bar)
    L.append("HEADLINE COMPARISON (affiliations-only denominator)")
    L.append(bar)
    L.append("")
    L.append(f"{'':>40}{'Cryo-EM':>13}{'OT':>13}")
    for label, key in [("Papers with an affiliation", "with_aff"),
                       ("Industry only", "industry_only"),
                       ("Mixed", "mixed"),
                       ("Industry or mixed", "or_mixed")]:
        L.append(f"{label:>40}{cryoem[key]:>13,}{ot[key]:>13,}")
    for label, key in [("Industry-or-mixed rate, all papers", "rate_all"),
                       ("Industry-or-mixed rate, with affiliation",
                        "rate_with_aff")]:
        L.append(f"{label:>40}{cryoem[key]:>12.1f}%{ot[key]:>12.1f}%")

    ratio_aff = (cryoem["rate_with_aff"] / ot["rate_with_aff"]
                 if ot["rate_with_aff"] else float("nan"))
    ratio_all = (cryoem["rate_all"] / ot["rate_all"]
                 if ot["rate_all"] else float("nan"))
    L.append("")
    L.append(f"  Gap moves from {ratio_all:.2f}x (all papers) to "
             f"{ratio_aff:.2f}x (affiliations only)")

    L.append("")
    L.append(bar)
    L.append("CATEGORY BREAKDOWN, AFFILIATIONS-ONLY DENOMINATOR")
    L.append(bar)
    L.append("")
    L.append(f"{'category':>31}{'Cryo-EM':>17}{'OT':>17}")
    for key in ORDER:
        if key in NON_EVIDENTIAL:
            continue
        field = "industry_only" if key == "industry" else key
        n_c, n_o = cryoem[field], ot[field]
        p_c = n_c / cryoem["with_aff"] * 100
        p_o = n_o / ot["with_aff"] * 100
        L.append(f"{DISPLAY[key]:>31}{n_c:>9,} ({p_c:>4.1f}%)"
                 f"{n_o:>9,} ({p_o:>4.1f}%)")
    L.append("")
    return L


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cryoem-prefix", default="cryoem")
    parser.add_argument("--ot-prefix", default="ot")
    parser.add_argument("--out", default="cryoem_vs_ot_comparison.txt",
                        help="also write the report to this file as UTF-8")
    args = parser.parse_args()

    corpora = [
        summarise("Cryo-EM",
                  load(f"{args.cryoem_prefix}_affiliation_per_paper.csv")),
        summarise("Optical tweezers",
                  load(f"{args.ot_prefix}_affiliation_per_paper.csv")),
    ]
    emit(build_report(corpora), args.out)


if __name__ == "__main__":
    main()