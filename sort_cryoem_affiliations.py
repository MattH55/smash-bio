#!/usr/bin/env python3
"""Sort the cryo-EM corpus's affiliations by the OT classifier's categories.

The classifier rolls each paper up to one of six labels (industry, academic,
mixed, no_affiliation, non_research_article, unknown). This script inverts that
roll-up: for every record it prints the individual affiliation strings bucketed
by the label of the paper they belong to, so the two corpora can be compared
category by category.

Affiliation strings are normalized before grouping (whitespace collapsed, a
trailing period removed) so that near-identical strings collapse into one row,
and each row is reported with the number of distinct papers it appears in.

Because the classifier's decision for a paper is a roll-up over all of its
affiliations, a single paper can contribute strings to more than one bucket
(e.g. a "mixed" paper contributes its industry strings and its academic
strings). The bucket labels are therefore the *paper* classification, and the
per-string counts within a bucket are what should be compared across corpora.

Usage:
    python sort_cryoem_affiliations.py                 # cryo-EM corpus (default)
    python sort_cryoem_affiliations.py --prefix ot     # the OT corpus
    python sort_cryoem_affiliations.py --top 50        # rows shown per category
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict

import ot_affiliation_classifier as ot

# Affiliation strings routinely contain non-ASCII institution names
# ("Universität", "Umeå", "Neuchâtel"). The Windows console defaults to a legacy
# codepage (cp1252) and either mangles or refuses those characters, so force
# UTF-8 on the output streams where the interpreter supports it.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

# The six paper-level labels, in the order the classifier documents them, with a
# human-readable heading for each. Kept in one place so the console report and
# the CSVs can never disagree about category names.
CATEGORIES = [
    ("industry", "Industry"),
    ("academic", "Academic"),
    ("mixed", "Mixed (industry + academic)"),
    ("unknown", "Unknown (matched neither list)"),
    ("no_affiliation", "No affiliation in PubMed"),
    ("non_research_article", "Non-research article (journal/editor contact)"),
]

CATEGORY_LABEL = dict(CATEGORIES)


def normalize(aff):
    """Collapse whitespace and drop a trailing period so near-identical strings
    from the same institution group into a single row."""
    return " ".join(aff.split()).strip().rstrip(".").strip()


def load_corpus(prefix):
    """Return records from <prefix>'s record cache, repointing the module global
    so the classifier is imported unchanged but reads the right corpus."""
    cache_csv = f"{prefix}_affiliation_records_cache.csv"
    ot.CACHE_CSV = cache_csv
    records = ot.read_records_cache(cache_csv)
    if records is None:
        raise SystemExit(
            f"No record cache found at {cache_csv}. Run the {prefix} classifier "
            "first to fetch the corpus."
        )
    return records


def bucket_affiliations(records):
    """Group affiliation strings by the classification of the paper containing
    them. Returns (by_category, paper_counts) where by_category maps a label to
    normalized string -> set of PMIDs, and paper_counts maps a label to the
    number of papers that received it."""
    by_category = defaultdict(lambda: defaultdict(set))
    paper_counts = Counter()

    for pmid, _year, affs in records:
        label = ot.classify_paper(affs)          # classifier imported unchanged
        paper_counts[label] += 1
        for aff in affs:
            if aff and aff.strip():
                by_category[label][normalize(aff)].add(pmid)
    return by_category, paper_counts


def report(by_category, paper_counts, total_papers, top=None):
    print(f"\nCorpus: {total_papers} papers\n")
    print("=" * 78)
    print("CATEGORY SUMMARY")
    print("=" * 78)
    for key, heading in CATEGORIES:
        n = paper_counts.get(key, 0)
        pct = n / total_papers * 100 if total_papers else 0.0
        print(f"  {heading:<48} {n:>7}  ({pct:5.1f}%)")

    # Any label the classifier returns that isn't in CATEGORIES would be drift
    # between this script and the classifier, so surface it instead of dropping it.
    unexpected = set(paper_counts) - {k for k, _ in CATEGORIES}
    if unexpected:
        print(f"\n  WARNING: unexpected classification label(s): {sorted(unexpected)}")

    for key, heading in CATEGORIES:
        strings = by_category.get(key)
        if not strings:
            continue
        ranked = sorted(strings.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        shown = ranked[:top] if top else ranked
        print("\n" + "=" * 78)
        print(f"{heading.upper()}  -  {len(ranked)} distinct affiliation string(s), "
              f"{paper_counts.get(key, 0)} paper(s)")
        print("=" * 78)
        for aff, pmids in shown:
            print(f"  {len(pmids):>5}x  {aff}")
        if top and len(ranked) > top:
            print(f"  ... {len(ranked) - top} more (raise --top to see)")


def write_csvs(by_category, paper_counts, total_papers, prefix):
    aff_path = f"{prefix}_affiliations_by_category.csv"
    with open(aff_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "category_heading", "affiliation",
                         "paper_count", "example_pmids"])
        for key, heading in CATEGORIES:
            strings = by_category.get(key, {})
            for aff, pmids in sorted(strings.items(),
                                     key=lambda kv: (-len(kv[1]), kv[0])):
                # Cap the sample of PMIDs so a very common string (e.g. a large
                # university) doesn't bloat a single cell.
                sample = sorted(pmids)[:10]
                writer.writerow([key, heading, aff, len(pmids), " ".join(sample)])

    summ_path = f"{prefix}_category_summary.csv"
    with open(summ_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "category_heading", "papers",
                         "pct_of_corpus", "distinct_affiliation_strings"])
        for key, heading in CATEGORIES:
            n = paper_counts.get(key, 0)
            pct = n / total_papers * 100 if total_papers else 0.0
            writer.writerow([key, heading, n, f"{pct:.1f}",
                             len(by_category.get(key, {}))])

    print(f"\nWrote {aff_path}")
    print(f"Wrote {summ_path}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prefix", default="cryoem",
                        help="Corpus prefix: 'cryoem' (default) or 'ot'")
    parser.add_argument("--top", type=int, default=25,
                        help="Affiliation rows shown per category (0 = all)")
    parser.add_argument("--csv", action="store_true",
                        help="Also write the per-category CSVs")
    args = parser.parse_args()

    records = load_corpus(args.prefix)
    by_category, paper_counts = bucket_affiliations(records)
    report(by_category, paper_counts, len(records), top=args.top or None)
    if args.csv:
        write_csvs(by_category, paper_counts, len(records), args.prefix)


if __name__ == "__main__":
    main()