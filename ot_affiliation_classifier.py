"""
Classify the "optical tweezers" PubMed corpus by author affiliation
(industry vs. academic), aggregated by year.

Pipeline:
  1. esearch (usehistory=y) to get WebEnv/QueryKey for the full result set
  2. efetch in batches of 200 (XML) to pull full records incl. affiliations
  3. classify each <Affiliation> string as industry / academic / unclear
  4. roll up author-level classifications to a paper-level label
  5. write two CSVs: per-year aggregate, and per-paper raw classifications

Usage:
    python ot_affiliation_classifier.py
    python ot_affiliation_classifier.py --api-key YOUR_KEY
    python ot_affiliation_classifier.py --qc-sample 40
    python ot_affiliation_classifier.py --refresh     # re-fetch from NCBI

Fetched records are cached to ot_affiliation_records_cache.csv so that
iterating on the keyword lists does not require re-downloading ~5k records.
"""

import argparse
import csv
import http.client
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict

QUERY = '"optical tweezers"'
TOOL = "smash-bio-ot-affiliation-classifier"
EMAIL = "matt.halma@gmail.com"
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
BATCH_SIZE = 200

PER_YEAR_CSV = "ot_affiliation_by_year.csv"
PER_PAPER_CSV = "ot_affiliation_per_paper.csv"
# Raw fetched records are cached here (one row per paper) so that iterating on
# the keyword lists below does NOT require re-fetching ~5k records from NCBI
# each time. Delete this file (or pass --refresh) to force a fresh download.
CACHE_CSV = "ot_affiliation_records_cache.csv"


# ---------------------------------------------------------------------------
# HTTP helpers (rate limiting + retry on 5xx)
# ---------------------------------------------------------------------------

class RateLimiter:
    def __init__(self, requests_per_second):
        self.min_interval = 1.0 / requests_per_second
        self._last = 0.0

    def wait(self):
        now = time.monotonic()
        elapsed = now - self._last
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last = time.monotonic()


def fetch_with_retry(url, params, rate_limiter, max_retries=5):
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    backoff = 1.0
    for attempt in range(max_retries):
        rate_limiter.wait()
        try:
            with urllib.request.urlopen(full_url, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            # 5xx is the documented transient case. NCBI's history server also
            # intermittently returns 400 when a WebEnv session is rejected
            # mid-pagination (or has expired), which a retry with a freshly
            # re-established session resolves; treating it as fatal here would
            # otherwise abort a whole run and leave stale CSVs on disk.
            transient = 500 <= e.code < 600 or e.code == 400
            if transient and attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
        except (urllib.error.URLError, http.client.IncompleteRead,
                ConnectionResetError) as e:
            # URLError covers DNS/timeout/connection refusal.
            # IncompleteRead / ConnectionResetError cover NCBI dropping the
            # connection partway through the response body, which happens under
            # load and is safe to retry (the request is a read-only GET).
            if attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
    raise RuntimeError(f"Failed after {max_retries} retries: {full_url}")


# ---------------------------------------------------------------------------
# Step 1: esearch with history
# ---------------------------------------------------------------------------

def esearch_with_history(rate_limiter, api_key=None):
    params = {
        "db": "pubmed",
        "term": QUERY,
        "retmax": 100000,
        "retmode": "json",
        "usehistory": "y",
        "tool": TOOL,
        "email": EMAIL,
    }
    if api_key:
        params["api_key"] = api_key
    raw = fetch_with_retry(ESEARCH_URL, params, rate_limiter)
    import json
    data = json.loads(raw)["esearchresult"]
    return int(data["count"]), data["webenv"], data["querykey"]


# ---------------------------------------------------------------------------
# Step 2: efetch in batches, parse affiliations
# ---------------------------------------------------------------------------

def extract_year(pubmed_article):
    # Prefer ArticleDate, then JournalIssue/PubDate/Year, then MedlineDate text
    date_el = pubmed_article.find(".//ArticleDate/Year")
    if date_el is not None and date_el.text:
        return date_el.text.strip()

    pubdate = pubmed_article.find(".//Article/Journal/JournalIssue/PubDate")
    if pubdate is not None:
        year_el = pubdate.find("Year")
        if year_el is not None and year_el.text:
            return year_el.text.strip()
        medline_date = pubdate.find("MedlineDate")
        if medline_date is not None and medline_date.text:
            m = re.search(r"(1[89]\d{2}|20\d{2})", medline_date.text)
            if m:
                return m.group(1)
    return None


def extract_affiliations(pubmed_article):
    """Return list of (author_index, affiliation_string) across all authors."""
    results = []
    author_list = pubmed_article.find(".//Article/AuthorList")
    if author_list is None:
        return results

    for idx, author in enumerate(author_list.findall("Author")):
        affs = []
        # Modern schema (2014+): Author/AffiliationInfo/Affiliation (can repeat)
        for aff_info in author.findall("AffiliationInfo"):
            aff_text = aff_info.findtext("Affiliation")
            if aff_text:
                affs.append(aff_text.strip())
        # Legacy pre-2014 schema: Author/Affiliation directly
        legacy_aff = author.findtext("Affiliation")
        if legacy_aff:
            affs.append(legacy_aff.strip())

        for aff in affs:
            results.append((idx, aff))
    return results


def parse_efetch_xml(xml_bytes):
    """Yield (pmid, year, [affiliation strings]) for each PubmedArticle."""
    root = ET.fromstring(xml_bytes)
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//MedlineCitation/PMID")
        pmid = pmid_el.text.strip() if pmid_el is not None else None
        year = extract_year(article)
        affs = [aff for _, aff in extract_affiliations(article)]
        yield pmid, year, affs


def fetch_all_records(webenv, query_key, total_count, rate_limiter, api_key=None):
    records = []
    for retstart in range(0, total_count, BATCH_SIZE):
        params = {
            "db": "pubmed",
            "WebEnv": webenv,
            "query_key": query_key,
            "retstart": retstart,
            "retmax": BATCH_SIZE,
            "rettype": "abstract",
            "retmode": "xml",
            "tool": TOOL,
            "email": EMAIL,
        }
        if api_key:
            params["api_key"] = api_key
        raw = fetch_with_retry(EFETCH_URL, params, rate_limiter)
        batch = list(parse_efetch_xml(raw))
        records.extend(batch)
        print(f"  fetched {min(retstart + BATCH_SIZE, total_count)}/{total_count}", file=sys.stderr)
    return records


def read_records_cache(path=CACHE_CSV):
    """Load previously fetched records from disk. Returns None if unavailable."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return None

    records = []
    for r in rows:
        affs = r["affiliations"].split(" | ") if r["affiliations"] else []
        records.append((r["pmid"], r["year"] or None, affs))
    return records or None


def write_records_cache(records, path=CACHE_CSV):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pmid", "year", "affiliations"])
        for pmid, year, affs in records:
            writer.writerow([pmid, year or "", " | ".join(affs)])


# ---------------------------------------------------------------------------
# Step 4: classification
# ---------------------------------------------------------------------------

# Journal / editorial / news records are not research papers: PubMed sometimes
# stores the journal's own or an editor's contact details in the affiliation
# field (e.g. "Nature Methods, . nina.vogt@us.nature.com."). These have no
# institutional affiliation to classify and would otherwise sit in "unknown"
# forever, so they are detected and reported as a distinct category. Scoped
# deliberately narrowly to publisher domains and to strings that name a journal
# but no institution, to avoid catching genuine research affiliations.
NON_RESEARCH_RE = re.compile(
    r"(@[\w.-]*nature\.com\b|\bnature\s+(?:methods|and\s+nature)\b)",
    re.IGNORECASE,
)

# National labs are government/academic-adjacent, never "industry" even
# though they contain the word "Laboratory". Check this override first.
NATIONAL_LAB_RE = re.compile(
    r"\b(national\s+laborator(?:y|ies)|national\s+lab\b|"
    r"Los\s+Alamos|Lawrence\s+Berkeley|Lawrence\s+Livermore|Oak\s+Ridge|"
    r"Sandia\s+National|Brookhaven\s+National|Argonne\s+National|"
    r"Pacific\s+Northwest\s+National|NIST\b|"
    r"Forschungszentrum|Helmholtz|"
    # Publicly funded science agencies whose names contain a company-style
    # legal suffix ("Corporation"), which would otherwise false-match the
    # INDUSTRY_SUFFIX_RE. JST is a Japanese government agency; note this is
    # distinct from genuine state-owned enterprises (e.g. China Electronic
    # Technology Group Corporation, CETC) which ARE industry and must not be
    # caught here.
    r"Japan\s+Science\s+and\s+Technology\s+(?:Corporation|Agency))",
    re.IGNORECASE,
)

# Known OT-instrument vendors and biotech/pharma companies relevant to the
# single-molecule / optical-tweezers field. Extend this list as new company
# affiliations are spotted during QC.
KNOWN_INDUSTRY_ENTITIES = [
    "LUMICKS", "Impetux", "Optics11", "Thorlabs", "JPK Instruments", "Bruker",
    "Elliot Scientific", "Aresis", "BioNanoTools", "Zeiss", "Carl Zeiss",
    "Nikon", "Olympus Corporation", "Coherent Inc", "Newport Corporation",
    "Hamamatsu", "Andor Technology", "Photometrics",
    # pharma / biotech companies known to appear in OT-adjacent literature
    "Pfizer", "Novartis", "Roche", "Genentech", "AstraZeneca",
    "GlaxoSmithKline", "GSK", "Merck & Co", "Merck Sharp", "Sanofi", "Amgen",
    "Regeneron", "Vertex Pharmaceuticals", "Gilead Sciences",
    "Bristol-Myers Squibb", "Bristol Myers Squibb", "Eli Lilly", "AbbVie",
    "Bayer AG", "Johnson & Johnson", "Takeda", "Boehringer Ingelheim",
    "Biogen", "Moderna", "BioNTech", "Illumina", "Genentech", "Novo Nordisk",
    "Nokia",
    # Private consultancy operating in the single-molecule analytics space
    # (PMID 25397733). Commercial entity with no academic affiliation.
    "Ursa Analytics",
]
KNOWN_INDUSTRY_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(name) for name in KNOWN_INDUSTRY_ENTITIES) + r")\b",
    re.IGNORECASE,
)

# Company legal suffixes. "AG" and "S.A." need extra care: European postal
# codes routinely produce false hits like "9747 AG Groningen" (Dutch postal
# code, not Aktiengesellschaft) and "Hong Kong S.A.R." (Special
# Administrative Region, not Sociedad Anonima) — both excluded explicitly.
INDUSTRY_SUFFIX_RE = re.compile(
    r"\b(Inc\.?|LLC|L\.L\.C\.|Ltd\.?|Limited|Corp\.?|Corporation|GmbH|"
    r"S\.A\.(?!R\.?)|S\.p\.A\.|B\.V\.|N\.V\.|plc|PLC|Pty\.?\s?Ltd\.?|Co\.,?\s*Ltd\.?|"
    r"L\.P\.|Kabushiki\s+Kaisha|K\.K\.)",
)
# Matched separately with a lookbehind to skip 4-digit-postal-code + "AG"
# (Dutch addresses, e.g. "9747 AG Groningen").
AG_SUFFIX_RE = re.compile(r"(?<!\d{4} )\bAG\b")

# Explicit industry sector terms. These are ambiguous on their own: academic
# units are routinely named "Department/Faculty/Institute/School of
# Biotechnology" or "... Biosciences", so a bare term match is only trusted
# when its own comma/semicolon-delimited clause does NOT also contain an
# academic-unit word (Institute, Faculty, Department, School, Center, ...).
INDUSTRY_TERM_RE = re.compile(
    r"\b(Pharmaceuticals?|Pharma\b|Biotech(?:nology)?|Biosciences?|"
    r"Therapeutics|Diagnostics|Biosystems)\b",
    re.IGNORECASE,
)
ACADEMIC_UNIT_WORD_RE = re.compile(
    r"\b(Institute|Faculty|Department|Dept\.?|School|Center|Centre|"
    r"Division|Program|Programme|College|Laboratory|Laboratories|Lab|"
    r"Research\s+Group|Group)\b",
    re.IGNORECASE,
)

# A known industry name (e.g. "Novo Nordisk") preceding "Foundation" is
# almost always philanthropic funding of an academic unit (e.g. "Novo
# Nordisk Foundation Center for Stem Cell Biology"), not a corporate
# affiliation of the author — treat as academic, not industry.
FOUNDATION_NAMED_UNIT_RE = re.compile(r"\bFoundation\b", re.IGNORECASE)


def _has_standalone_industry_term(aff):
    """True if an industry sector term appears in a clause that isn't itself
    (or adjacent to) an academic organizational unit. A short sliding window
    of neighboring clauses is checked, not just the exact clause, because
    affiliation strings routinely split an academic unit name across commas
    (e.g. "Biosciences, University of Exeter" or "Faculty, Biotechnology,
    Univ. of X")."""
    clauses = re.split(r"[;,]", aff)
    for i, clause in enumerate(clauses):
        if not INDUSTRY_TERM_RE.search(clause):
            continue
        window = " ".join(clauses[max(0, i - 1):i + 2])
        if not (ACADEMIC_UNIT_WORD_RE.search(window) or ACADEMIC_RE.search(window)):
            return True
    return False

# "Laboratories" paired with a company-style name (not "National Laboratory",
# already excluded above) — heuristic: capitalized word immediately before
# "Laboratories" that isn't "National"/"Research"/"Central".
COMPANY_LABS_RE = re.compile(
    r"\b(Bell\s+Lab(?:oratories|s)|Genentech\s+Laboratories|Merck\s+Laboratories)\b",
    re.IGNORECASE,
)

ACADEMIC_RE = re.compile(
    r"\b(University|Universit[äaeéà]t|Universit[ée]|Universidad|Universit[aà]|"
    r"Universiteit|Rijksuniversiteit|"
    r"Institute\s+of\s+Technology|Coll[eè]ge|Dept\.?|Departamento|Department|"
    r"\bSchool\b|Hospital|Krankenhaus|Institut\w*|"
    r"CNRS|CSIC|INSERM|\bCNR\b|Council\s+of\s+Scientific\s+and\s+Industrial\s+Research|"
    r"\bCSIR\b|Max\s+Planck|Howard\s+Hughes\s+Medical\s+Institute|"
    r"Academy\s+of\s+Sciences?|Polytechnic\w*|Polytechniqu\w*|Polit[eé]cnic\w*|"
    r"National\s+Institutes?\s+of\s+Health|\bNIH\b|\bNHLBI\b|"
    r"Naval\s+Research\s+Laboratory|Army\s+Research\s+Laboratory|"
    r"Rutherford\s+Appleton\s+Laboratory|European\s+Synchrotron\s+Radiation\s+Facility|"
    r"Science\s+and\s+Technology\s+Facilities\s+Council|"
    r"\bAMOLF\b|\bIMDEA\b|Raja\s+Ramanna\s+Cent(?:er|re)|Cent(?:er|re)\s+for\s+Advanced\s+Technology|"
    r"\bETH\s+Z[uü]rich\b|\bEMBL\b|European\s+Molecular\s+Biology\s+Laboratory|"
    r"\bMRC\b|Medical\s+Research\s+Council|Ecole\s+Normale\s+Sup[eé]rieure|"
    r"\bTU\s+Dresden\b|Istituto\s+Italiano\s+di\s+Tecnologia|"
    r"National\s+Physical\s+Laboratory|Consiglio\s+Nazionale\s+delle\s+Ricerche|"
    r"Consejo\s+Superior\s+de\s+Investigaciones\s+Cient[ií]ficas|"
    # --- Final refinement pass: recurring non-industry institutions that were
    # still landing in "unclear" during the QC sweep. All are government,
    # university, or publicly funded research organisations, never companies.
    r"Scottish\s+Universities\s+Physics\s+Alliance|\bUniv\.\s+of\b|\bUniv\.\b|"
    r"Istituto\s+Italiano\s+di\s+Tecnologia|\bIMEC\b|"
    r"Japan\s+Science\s+and\s+Technology\s+Agency|\bJST\b|ERATO|"
    r"\bKTH\b|Linnaeus|"
    r"\bDFG\b|Deutsche\s+Forschungsgemeinschaft|\bFU\s+Berlin\b|"
    r"Manchester\s+Interdisciplinary\s+Biocentre|Biocentre|"
    r"Elettra|Synchrotron|"
    r"\bINFM\b|Istituto\s+Nazionale\s+per\s+la\s+Fisica\s+della\s+Materia|"
    r"Institut\s+National\s+de\s+la\s+Sant[eé]|"
    r"Ecole\s+Sup[eé]rieure|"
    r"ESPCI|ParisTech|"
    r"Max\s+Planck|\bMPI\b|"
    r"Dipartimento|Universit[aà]\s+di|"
    r"Laboratoire|Laboratoires?|"
    r"Federal\s+Research\s+(?:Center|Centre)|"
    r"Laserzentrum|Krankenhaus|"
    r"EMBL|European\s+Laboratory\s+for\s+Nonlinear\s+Spectroscopy|"
    # --- Resolvable stragglers from the final QC sweep. Each verified against
    # the source PubMed record as a real publicly funded / university body.
    r"Centro\s+Nacional\s+de\s+Investigaciones\s+Cardiovasculares|\bCNIC\b|"
    r"Programme\s+d'Epig[eé]nomique|Epig[eé]nomique|Genopole|"
    r"Georges-Koehler-Allee|"
    r"Place\s+Eug[eè]ne\s+Bataillon|\bI3M\b|"
    r"@[\w.-]+\.(?:edu(?:\.[a-z]{2,3})?|ac\.[a-z]{2,3}|gov(?:\.[a-z]{2,3})?|mil|fr|de|it|nl|ch|uk|ca|au|jp)\b)",
    re.IGNORECASE,
)


def _has_standalone_known_industry_entity(aff):
    """True if a known vendor/pharma name appears outside a philanthropically
    named academic unit or a same-named university, e.g. skips "Novo Nordisk
    Foundation Center for Stem Cell Biology" and "Hamamatsu University School
    of Medicine" (a Japanese city, coincidentally also a vendor name, that a
    university is named after) but still catches "Genentech Inc, South San
    Francisco" and "Hamamatsu Photonics K.K.\""""
    clauses = re.split(r"[;,]", aff)
    for i, clause in enumerate(clauses):
        if not KNOWN_INDUSTRY_RE.search(clause):
            continue
        window = " ".join(clauses[max(0, i - 1):i + 2])
        has_suffix = bool(INDUSTRY_SUFFIX_RE.search(window) or COMPANY_LABS_RE.search(window))
        if not has_suffix and re.search(r"\bUniversity\b", window, re.IGNORECASE):
            continue
        if FOUNDATION_NAMED_UNIT_RE.search(window) and ACADEMIC_UNIT_WORD_RE.search(window):
            continue
        return True
    return False


def classify_affiliation(aff):
    """Classify a single affiliation string: 'industry', 'academic', or 'unclear'."""
    if not aff or not aff.strip():
        return "unclear"

    if NATIONAL_LAB_RE.search(aff):
        return "academic"

    if (_has_standalone_known_industry_entity(aff) or INDUSTRY_SUFFIX_RE.search(aff)
            or AG_SUFFIX_RE.search(aff) or COMPANY_LABS_RE.search(aff)
            or _has_standalone_industry_term(aff)):
        return "industry"

    if ACADEMIC_RE.search(aff):
        return "academic"

    return "unclear"


def classify_paper(affiliations):
    """Roll up a list of affiliation strings to a paper-level label.

    Labels:
      industry            - every classifiable author affiliation is industry
      academic            - every classifiable author affiliation is academic
      mixed               - both industry and academic affiliations present
      no_affiliation      - PubMed returned no affiliation string for any author
                            (no data to classify; NOT the same as unclassifiable)
      non_research_article- the affiliation field holds journal/editor contact
                            details rather than any institution (commentary,
                            news, or editorial items); there is no affiliation
                            to classify
      unknown             - affiliation text exists but matched neither keyword
                            list, so it was deliberately left unclassified
    """
    non_empty = [a for a in affiliations if a and a.strip()]
    if not non_empty:
        return "no_affiliation"

    # Checked before anything else: a journal/editor contact detail is not an
    # institutional affiliation, so it must not be forced into academic or
    # industry just because it mentions a publisher.
    if all(NON_RESEARCH_RE.search(a) for a in non_empty):
        return "non_research_article"

    labels = {classify_affiliation(a) for a in non_empty}
    classified = labels - {"unclear"}

    if not classified:
        return "unknown"
    if classified == {"industry"}:
        return "industry"
    if classified == {"academic"}:
        return "academic"
    return "mixed"  # both industry and academic present


# ---------------------------------------------------------------------------
# Step 5: aggregate + write CSVs
# ---------------------------------------------------------------------------

def write_per_paper_csv(records, classifications, path=PER_PAPER_CSV):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pmid", "year", "affiliations", "classification"])
        for (pmid, year, affs), label in zip(records, classifications):
            writer.writerow([pmid, year or "", " | ".join(affs), label])


def write_per_year_csv(records, classifications, path=PER_YEAR_CSV):
    by_year = defaultdict(lambda: defaultdict(int))
    for (pmid, year, affs), label in zip(records, classifications):
        y = year or "unknown_year"
        by_year[y]["total"] += 1
        by_year[y][label] += 1

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "year", "total_papers", "industry_papers", "academic_papers",
            "mixed_papers", "non_research_article_papers", "unknown_papers",
            "no_affiliation_papers", "pct_industry_or_mixed",
        ])
        for year in sorted(by_year.keys(), key=lambda y: (y == "unknown_year", y)):
            counts = by_year[year]
            total = counts["total"]
            industry = counts.get("industry", 0)
            academic = counts.get("academic", 0)
            mixed = counts.get("mixed", 0)
            non_research = counts.get("non_research_article", 0)
            unknown = counts.get("unknown", 0)
            no_aff = counts.get("no_affiliation", 0)
            # Denominator: papers with any affiliation data, i.e. excluding the
            # records where PubMed simply has nothing to classify (no_affiliation)
            # and the commentary/editorial items whose "affiliation" is really a
            # journal contact (non_research_article). Otherwise older years with
            # sparse affiliation indexing drag the industry-or-mixed rate
            # artificially downward. total_papers still reports the full corpus
            # count for transparency.
            denom = total - no_aff - non_research
            pct = (industry + mixed) / denom * 100 if denom else 0.0
            writer.writerow([year, total, industry, academic, mixed, non_research,
                             unknown, no_aff, f"{pct:.1f}"])


# ---------------------------------------------------------------------------
# Step 6: QC sample
# ---------------------------------------------------------------------------

def write_qc_sample(records, classifications, n, path="ot_affiliation_qc_sample.csv"):
    by_bucket = defaultdict(list)
    for (pmid, year, affs), label in zip(records, classifications):
        by_bucket[label].append((pmid, year, affs, label))

    buckets = [b for b in by_bucket if by_bucket[b]]
    per_bucket = max(1, n // max(1, len(buckets)))
    sample = []
    for b in buckets:
        pool = by_bucket[b]
        sample.extend(random.sample(pool, min(per_bucket, len(pool))))
    random.shuffle(sample)
    sample = sample[:n]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pmid", "year", "affiliations", "classification",
                          "manual_review_correct(Y/N)", "notes"])
        for pmid, year, affs, label in sample:
            writer.writerow([pmid, year or "", " | ".join(affs), label, "", ""])
    print(f"QC sample ({len(sample)} papers) written to {path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=None, help="NCBI API key (optional, raises rate limit to 10/s)")
    parser.add_argument("--qc-sample", type=int, default=40, help="Number of papers to sample for manual QC (0 to skip)")
    parser.add_argument("--refresh", action="store_true",
                        help="Ignore the local record cache and re-fetch from NCBI")
    args = parser.parse_args()

    rps = 10 if args.api_key else 3
    rate_limiter = RateLimiter(rps)

    records = None if args.refresh else read_records_cache()
    if records is not None:
        print(f"Using cached records ({len(records)}) from {CACHE_CSV}", file=sys.stderr)
        print("  (pass --refresh to re-fetch from NCBI)", file=sys.stderr)
    else:
        print("Step 1: esearch with history...", file=sys.stderr)
        total_count, webenv, query_key = esearch_with_history(rate_limiter, args.api_key)
        print(f"  total records: {total_count}", file=sys.stderr)

        print("Step 2: efetch full records...", file=sys.stderr)
        try:
            records = fetch_all_records(webenv, query_key, total_count, rate_limiter, args.api_key)
        except (urllib.error.HTTPError, http.client.IncompleteRead, ConnectionResetError) as e:
            # A rejected/expired WebEnv session or a dropped connection shouldn't
            # lose the whole run: the query itself is deterministic, so re-run
            # esearch for a fresh session and try the pagination once more.
            print(f"  efetch failed ({e!r}); re-establishing history session...", file=sys.stderr)
            total_count, webenv, query_key = esearch_with_history(rate_limiter, args.api_key)
            records = fetch_all_records(webenv, query_key, total_count, rate_limiter, args.api_key)
        print(f"  parsed {len(records)} PubmedArticle records", file=sys.stderr)
        if len(records) < total_count:
            # Never write CSVs from a short fetch: a silently truncated run would
            # look identical to a complete one and corrupt the per-year totals.
            raise RuntimeError(
                f"incomplete fetch: parsed {len(records)} of {total_count} records; "
                "refusing to write CSVs from partial data"
            )
        write_records_cache(records)
        print(f"  cached raw records to {CACHE_CSV}", file=sys.stderr)

    print("Step 4: classifying affiliations...", file=sys.stderr)
    classifications = [classify_paper(affs) for _, _, affs in records]

    print("Step 5: writing CSVs...", file=sys.stderr)
    write_per_paper_csv(records, classifications)
    write_per_year_csv(records, classifications)
    print(f"  wrote {PER_YEAR_CSV} and {PER_PAPER_CSV}", file=sys.stderr)

    label_counts = defaultdict(int)
    for label in classifications:
        label_counts[label] += 1
    print("\nOverall classification counts:", file=sys.stderr)
    for label in ("industry", "academic", "mixed", "non_research_article",
                  "unknown", "no_affiliation"):
        n = label_counts.get(label, 0)
        pct = n / len(classifications) * 100 if classifications else 0
        print(f"  {label}: {n} ({pct:.1f}%)", file=sys.stderr)

    # Both no-affiliation and non-research-article records have no institutional
    # affiliation to classify, so they are excluded from the rate denominator.
    unclassifiable = (label_counts.get("no_affiliation", 0)
                      + label_counts.get("non_research_article", 0))
    classifiable = len(classifications) - unclassifiable
    ind_or_mixed = label_counts.get("industry", 0) + label_counts.get("mixed", 0)
    if classifiable:
        print(f"  industry-or-mixed rate (excluding no-affiliation and "
              f"non-research-article records): "
              f"{ind_or_mixed / classifiable * 100:.1f}%", file=sys.stderr)

    if args.qc_sample > 0:
        write_qc_sample(records, classifications, args.qc_sample)


if __name__ == "__main__":
    main()
