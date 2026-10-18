#!/usr/bin/env python3
"""Classify the "cryo-EM" PubMed corpus by author affiliation (industry vs.
academic), aggregated by year -- the direct comparator to the optical-tweezers
run.

This is a thin driver around ``ot_affiliation_classifier.py``. The affiliation
*classifier* (keyword lists, author-level -> paper-level rollup, and the
non_research_article / no_affiliation / unknown buckets) is IMPORTED from that
module and deliberately left untouched, so the OT and cryo-EM numbers differ
only because of the corpus, never because of a keyword-list change between the
two runs. Any fix to the classifier necessarily affects both corpora at once;
that coupling is the point.

Only three things differ from the OT run:
  1. QUERY   - the cryo-EM search string
  2. the output filenames (cryoem_* instead of ot_*)
  3. the cached-record file

Pipeline (identical to the OT run):
  1. esearch (usehistory=y) to get WebEnv/QueryKey for the full result set
  2. efetch in batches of 200 (XML) to pull full records incl. affiliations
  3. classify each <Affiliation> string as industry / academic / unclear
  4. roll up author-level classifications to a paper-level label
  5. write two CSVs: per-year aggregate, and per-paper raw classifications

Usage:
    python cryoem_affiliation_classifier.py
    python cryoem_affiliation_classifier.py --api-key YOUR_KEY
    python cryoem_affiliation_classifier.py --qc-sample 40
    python cryoem_affiliation_classifier.py --refresh     # re-fetch from NCBI

Fetched records are cached to cryoem_affiliation_records_cache.csv so that
iterating on the keyword lists does not require re-downloading ~20k records.
Pass --refresh to force a fresh download.
"""

import argparse
import json
import sys

import ot_affiliation_classifier as ot

# ---------------------------------------------------------------------------
# The three things that differ from the optical-tweezers run.
# ---------------------------------------------------------------------------

# Query used for the cryo-EM benchmark figure / corpus. All-fields phrase search,
# matching the style of the OT query ('"optical tweezers"'). The hyphenated
# "Cryo-EM" is quoted so E-utilities treats it as a phrase rather than parsing
# the hyphen as a token break.
#
# Known breadth trade-off: this catches the two dominant surface forms but not
# spelled-out variants ("cryogenic electron microscopy", "cryo electron
# tomography"). Widening it changes the denominator, so it is pinned here and
# recorded in the methods.
QUERY = '"Cryo-electron microscopy" OR "Cryo-EM"'

PER_YEAR_CSV = "cryoem_affiliation_by_year.csv"
PER_PAPER_CSV = "cryoem_affiliation_per_paper.csv"
CACHE_CSV = "cryoem_affiliation_records_cache.csv"
QC_CSV = "cryoem_affiliation_qc_sample.csv"

TOOL = "smash-bio-cryoem-affiliation-classifier"

# ---------------------------------------------------------------------------
# The OT module reads QUERY and its CSV paths from module-level globals, so the
# reused helpers are pointed at the cryo-EM corpus by overriding those globals
# rather than by copying the functions (which is what would let the two
# classifiers silently drift apart).
# ---------------------------------------------------------------------------

ot.QUERY = QUERY
ot.TOOL = TOOL
ot.PER_YEAR_CSV = PER_YEAR_CSV
ot.PER_PAPER_CSV = PER_PAPER_CSV
ot.CACHE_CSV = CACHE_CSV


# ---------------------------------------------------------------------------
# Step 1/2: corpus retrieval
#
# The OT module's history-session pagination (usehistory=y + WebEnv, paging by
# retstart) does not survive a corpus this size: the history server starts
# returning HTTP 400 partway through, which aborted the run after ~10k records.
# Two independent E-utilities limits are involved, both silent:
#
#   * esearch returns at most 9999 ids, and retstart does NOT page past that
#     cap -- a naively paged esearch yields exactly 9999 of 19739 records with
#     no error. This is the dangerous one, because the output looks complete.
#   * A long-lived WebEnv session expires mid-pagination on large result sets.
#
# So the full set is enumerated by publication-year windows (each far under the
# cap) and fetched by explicit PMID list, which needs no server-side session.
# ---------------------------------------------------------------------------

YEAR_MIN, YEAR_MAX = 1980, 2050


def esearch_ids_for_term(term, rate_limiter, api_key=None, retmax=5000):
    """Return up to `retmax` PMIDs for a term, in relevance/order of the query."""
    params = {
        "db": "pubmed",
        "term": term,
        "retmax": retmax,
        "retmode": "json",
        "tool": TOOL,
        "email": ot.EMAIL,
    }
    if api_key:
        params["api_key"] = api_key
    raw = ot.fetch_with_retry(ot.ESEARCH_URL, params, rate_limiter)
    return json.loads(raw)["esearchresult"]["idlist"]


def esearch_all_pmids(rate_limiter, api_key=None):
    """Enumerate every PMID for QUERY by paging over publication years.

    Each year window is queried separately and the results are unioned, because
    a single esearch cannot return more than 9999 records and retstart will not
    page past that ceiling. Returns (ordered unique pmid list, total esearch
    count as reported by NCBI) so the caller can assert the two agree.
    """
    seen = set()
    ordered = []
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        ids = esearch_ids_for_term(f"({QUERY}) AND {year}[dp]", rate_limiter, api_key)
        new = [p for p in ids if p not in seen]
        seen.update(new)
        ordered.extend(new)
        if ids:
            print(f"  {year}: {len(ids)}", file=sys.stderr)

    # Cross-check against the un-windowed count from NCBI. A mismatch means a
    # window silently hit the 9999 cap (i.e. one year alone exceeded it) and the
    # corpus would be short, so fail loudly rather than emit wrong totals.
    params = {"db": "pubmed", "term": QUERY, "retmax": 0, "retmode": "json",
              "tool": TOOL, "email": ot.EMAIL}
    if api_key:
        params["api_key"] = api_key
    raw = ot.fetch_with_retry(ot.ESEARCH_URL, params, rate_limiter)
    expected = int(json.loads(raw)["esearchresult"]["count"])
    if len(ordered) != expected:
        raise RuntimeError(
            f"PMID enumeration mismatch: collected {len(ordered)} unique PMIDs "
            f"but NCBI reports {expected} for this query. A year window has "
            "likely exceeded the 9999-id esearch cap; split that year by month."
        )
    return ordered, expected


def fetch_records_by_pmids(pmids, rate_limiter, api_key=None):
    """efetch full XML records for an explicit PMID list, BATCH_SIZE at a time.

    Uses ``id=<comma-separated>`` rather than a WebEnv history session: the
    database is read-only and each request is self-contained, so a session
    expiring mid-run cannot truncate the fetch.

    A batch may legitimately return fewer records than PMIDs requested: some
    records are indexed by esearch but omitted from the efetch article feed
    (e.g. Review/book records such as PMID 30299652). Those are reported rather
    than treated as errors, but a large shortfall still aborts the run, since
    that would indicate genuine truncation rather than a handful of such records.
    """
    if not pmids:
        print("  no PMIDs to fetch", file=sys.stderr)
        return []

    records = []
    missing = []
    for start in range(0, len(pmids), ot.BATCH_SIZE):
        chunk = pmids[start:start + ot.BATCH_SIZE]
        params = {
            "db": "pubmed",
            "id": ",".join(chunk),
            "rettype": "abstract",
            "retmode": "xml",
            "tool": TOOL,
            "email": ot.EMAIL,
        }
        if api_key:
            params["api_key"] = api_key
        raw = ot.fetch_with_retry(ot.EFETCH_URL, params, rate_limiter)
        batch = list(ot.parse_efetch_xml(raw))
        returned = {pmid for pmid, _, _ in batch}
        absent = [p for p in chunk if p not in returned]
        if absent:
            missing.extend(absent)
            print(f"  note: {len(absent)} PMID(s) not in efetch feed at offset "
                  f"{start}: {', '.join(absent)}", file=sys.stderr)
        records.extend(batch)
        print(f"  fetched {min(start + ot.BATCH_SIZE, len(pmids))}/{len(pmids)}",
              file=sys.stderr)

    if missing:
        frac = len(missing) / len(pmids)
        print(f"  {len(missing)} of {len(pmids)} PMIDs ({frac:.3%}) were not "
              "retrievable via efetch", file=sys.stderr)
        if frac > 0.01:
            raise RuntimeError(
                f"{len(missing)} of {len(pmids)} PMIDs ({frac:.2%}) missing from "
                "efetch; that is too large a shortfall to be non-retrievable "
                "records, so the fetch is likely truncated"
            )
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=None,
                        help="NCBI API key (optional, raises rate limit to 10/s)")
    parser.add_argument("--qc-sample", type=int, default=40,
                        help="Number of papers to sample for manual QC (0 to skip)")
    parser.add_argument("--refresh", action="store_true",
                        help="Ignore the local record cache and re-fetch from NCBI")
    args = parser.parse_args()

    rps = 10 if args.api_key else 3
    rate_limiter = ot.RateLimiter(rps)

    records = None if args.refresh else ot.read_records_cache(CACHE_CSV)
    if records is not None:
        print(f"Using cached records ({len(records)}) from {CACHE_CSV}", file=sys.stderr)
        print("  (pass --refresh to re-fetch from NCBI)", file=sys.stderr)
    else:
        print("Step 1: enumerate PMIDs by publication-year windows...", file=sys.stderr)
        print(f"  query: {QUERY}", file=sys.stderr)
        pmids, expected = esearch_all_pmids(rate_limiter, args.api_key)
        print(f"  total records: {expected} (enumerated {len(pmids)})", file=sys.stderr)

        print("Step 2: efetch full records by PMID list...", file=sys.stderr)
        records = fetch_records_by_pmids(pmids, rate_limiter, args.api_key)
        print(f"  parsed {len(records)} PubmedArticle records", file=sys.stderr)
        if len(records) > expected:
            raise RuntimeError(
                f"parsed {len(records)} records but NCBI reports only {expected} "
                "for this query; the corpus is inconsistent"
            )
        short = expected - len(records)
        if short:
            # A small shortfall is expected: a few PMIDs are indexed by esearch
            # but absent from the efetch article feed. fetch_records_by_pmids
            # already aborts if the shortfall is large enough to indicate
            # truncation, so anything reaching here is non-retrievable records.
            print(f"  {short} record(s) not retrievable via efetch "
                  f"({short / expected:.3%} of corpus); continuing",
                  file=sys.stderr)
        ot.write_records_cache(records, CACHE_CSV)
        print(f"  cached raw records to {CACHE_CSV}", file=sys.stderr)

    print("Step 4: classifying affiliations...", file=sys.stderr)
    print("  (classifier imported unchanged from ot_affiliation_classifier)",
          file=sys.stderr)
    classifications = [ot.classify_paper(affs) for _, _, affs in records]

    print("Step 5: writing CSVs...", file=sys.stderr)
    ot.write_per_paper_csv(records, classifications, PER_PAPER_CSV)
    ot.write_per_year_csv(records, classifications, PER_YEAR_CSV)
    print(f"  wrote {PER_YEAR_CSV} and {PER_PAPER_CSV}", file=sys.stderr)

    label_counts = {}
    for label in classifications:
        label_counts[label] = label_counts.get(label, 0) + 1
    print("\nOverall classification counts:", file=sys.stderr)
    for label in ("industry", "academic", "mixed", "non_research_article",
                  "unknown", "no_affiliation"):
        n = label_counts.get(label, 0)
        pct = n / len(classifications) * 100 if classifications else 0
        print(f"  {label}: {n} ({pct:.1f}%)", file=sys.stderr)

    # Both no-affiliation and non-research-article records have no institutional
    # affiliation to classify, so they are excluded from the rate denominator.
    # Same denominator convention as the OT run, so the two rates are comparable.
    unclassifiable = (label_counts.get("no_affiliation", 0)
                      + label_counts.get("non_research_article", 0))
    classifiable = len(classifications) - unclassifiable
    ind_or_mixed = label_counts.get("industry", 0) + label_counts.get("mixed", 0)
    if classifiable:
        print(f"  industry-or-mixed rate (excluding no-affiliation and "
              f"non-research-article records): "
              f"{ind_or_mixed / classifiable * 100:.1f}%", file=sys.stderr)

    if args.qc_sample > 0:
        ot.write_qc_sample(records, classifications, args.qc_sample, QC_CSV)


if __name__ == "__main__":
    main()