"""Milestone-1 deposit family resolution and biological relevance filtering.

The functions in this module are deterministic and side-effect free so they can be
used by the current JSONL pipeline now and by the planned harvester store later.
Every classification carries the rule and matched terms used to produce it.
"""
import re
import unicodedata
from collections import defaultdict

from common import norm_doi

VERSION = "1.0.0"
COUNTED_RELEVANCE = {"in_scope", "methods"}

VERSION_PATTERNS = (
    ("figshare_suffix", re.compile(r"^(10\.6084/m9\.figshare\..+?)\.v(\d+)$", re.I)),
    ("dryad_suffix", re.compile(r"^(10\.5061/dryad\..+?)/(\d+)$", re.I)),
    ("mendeley_suffix", re.compile(r"^(10\.17632/.+?)\.(\d+)$", re.I)),
    ("4tu_suffix", re.compile(r"^(10\.4121/.+?)\.v(\d+)$", re.I)),
)
VERSION_RELATIONS = {"isversionof", "hasversion", "isnewversionof", "ispreviousversionof"}

EXCLUSION_TERMS = (
    "cold atom", "cold atoms", "bose-einstein", "bose einstein", "magneto-optical trap",
    "aerosol", "plasmonic", "colloid crystal", "colloidal crystal", "photonic crystal",
    "lattice clock", "rydberg", "optical lattice", "quantum gas", "holographic projection",
)
METHOD_TERMS = (
    "calibration", "instrument", "apparatus", "setup", "software", "algorithm", "analysis",
    "simulation", "benchmark", "protocol", "method", "force spectroscopy", "optical tweezer",
    "magnetic tweezer", "acoustic force spectroscopy", "force microscope",
)


def _fold(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.encode("ascii", "ignore").decode().lower()).split())


def _version_key(doi):
    doi = norm_doi(doi) or ""
    for rule, rx in VERSION_PATTERNS:
        match = rx.match(doi)
        if match:
            return match.group(1), int(match.group(2)), rule
    return doi, -1, "identity"


def _declared_parent(row):
    """Return a repository-declared concept/parent DOI where metadata provides one."""
    candidates = []
    for rel in row.get("related") or []:
        if str(rel.get("relation") or "").lower() in VERSION_RELATIONS:
            doi = norm_doi(rel.get("id"))
            if doi:
                candidates.append(doi)
    explicit = norm_doi(row.get("concept_doi") or row.get("family_id"))
    return explicit or (sorted(candidates, key=len)[0] if candidates else None)


def family_key(row):
    """Return ``(family_id, version, rule)`` for one deposit row."""
    doi = norm_doi(row.get("doi"))
    if not doi:
        return row.get("url") or row.get("title") or "unknown", -1, "non_doi_identity"
    parent = _declared_parent(row)
    if parent:
        base, version, _ = _version_key(doi)
        return parent, version, "repository_declared"
    return _version_key(doi)


def _text(row):
    values = [row.get("title"), row.get("description"), row.get("publisher"), row.get("repository")]
    values.extend(row.get("subjects") or [])
    return _fold(" ".join(str(v) for v in values if v))


def classify_relevance(row, linked_scopes=()):
    """Label one family and return ``(label, evidence)``.

    A tier-1--3 study link is represented here by a non-empty linked scope. It is
    deliberately evaluated before exclusions, as required by the specification.
    """
    scopes = sorted(set(s for s in linked_scopes if s in COUNTED_RELEVANCE))
    if scopes:
        label = "in_scope" if "in_scope" in scopes else "methods"
        return label, {"method": "rule", "rule": "inherited_linked_study", "matched": scopes}

    text = _text(row)
    biological = sorted({term for term in (
        "protein", "dna", "rna", "nucleic", "cell", "membrane", "enzyme", "molecule",
        "biological", "biomolecule", "bacteria", "virus", "chromatin", "microtubule",
        "actin", "myosin", "kinesin", "receptor", "ligand", "peptide", "organism",
    ) if re.search(r"\b" + re.escape(term), text)})
    excluded = sorted({term for term in EXCLUSION_TERMS if term in text})
    if excluded and not biological:
        return "out_of_scope", {"method": "rule", "rule": "physics_exclusion", "matched": excluded}

    repository = _fold(row.get("repository"))
    publisher = _fold(row.get("publisher"))
    doi = norm_doi(row.get("doi")) or ""
    if ("pangaea" in repository or doi.startswith("10.1594/pangaea")) and not biological:
        return "out_of_scope", {"method": "rule", "rule": "repository_prior_pangaea", "matched": ["PANGAEA"]}
    if ("optica" in publisher or "optica" in repository) and not biological and not row.get("linked_records"):
        return "out_of_scope", {"method": "rule", "rule": "repository_prior_optica", "matched": ["Optica"]}

    techniques = sorted(set(row.get("techniques") or []))
    if techniques and biological:
        methods = sorted({term for term in METHOD_TERMS if term in text})
        label = "methods" if methods and not any(x in text for x in ("data for", "dataset", "source data")) else "in_scope"
        return label, {"method": "rule", "rule": "technique_plus_biology", "matched": techniques + biological[:8]}
    return "unsure", {"method": "rule", "rule": "insufficient_evidence", "matched": []}


def _best(rows):
    """Newest explicit version, then newest year, then concept DOI row."""
    return max(rows, key=lambda x: (family_key(x)[1], int(x.get("year") or 0),
                                    not bool(re.search(r"\.v\d+$", x.get("doi") or "", re.I))))


def collapse_families(rows, record_scopes=None):
    """Collapse deposit DOI rows to families without discarding version metadata."""
    record_scopes = record_scopes or {}
    groups = defaultdict(list)
    rules = defaultdict(set)
    for row in rows:
        key, _, rule = family_key(row)
        groups[key].append(row)
        rules[key].add(rule)

    families = []
    for group_id, members in groups.items():
        current = dict(_best(members))
        dois = sorted({norm_doi(x.get("doi")) for x in members if norm_doi(x.get("doi"))})
        links = sorted({rid for x in members for rid in (x.get("linked_records") or [])})
        scopes = [record_scopes.get(rid) for rid in links]
        declared = next((_declared_parent(x) for x in members if _declared_parent(x)), None)
        canonical = declared or (group_id if group_id in dois else norm_doi(current.get("doi")))
        family_id = canonical or group_id
        current["family_id"] = family_id
        current["canonical_doi"] = canonical
        current["doi"] = current["canonical_doi"]
        current["version_dois"] = [d for d in dois if d != current["canonical_doi"]]
        current["linked_records"] = links
        current["file_formats"] = sorted({f for x in members for f in (x.get("file_formats") or [])})
        contents = {x.get("content") for x in members if x.get("content")}
        if contents:
            current["content"] = "raw_traces" if "raw_traces" in contents else (next(iter(contents)) if len(contents) == 1 else "mixed")
        current["family_evidence"] = {"method": "doi_family", "version": VERSION,
                                      "rules": sorted(rules[group_id]), "member_count": len(members)}
        current["relevance"], current["relevance_evidence"] = classify_relevance(current, scopes)
        families.append(current)
    return sorted(families, key=lambda x: (x.get("title") or "", x.get("family_id") or ""))


def annotate_record_links(records, families):
    """Attach family/relevance metadata to existing record links in place."""
    by_doi = {}
    for family in families:
        for doi in [family.get("canonical_doi")] + family.get("version_dois", []):
            if doi:
                by_doi[doi] = family
    for record in records:
        da = record["data_availability"]
        if record.get("curation", {}).get("level") in ("curated", "author_verified"):
            continue
        for link in da.get("datasets", []) + da.get("code", []):
            family = by_doi.get(norm_doi(link.get("id")))
            if not family:
                continue
            link["family_id"] = family["family_id"]
            link["canonical_doi"] = family.get("canonical_doi")
            link["version_dois"] = family.get("version_dois", [])
            link["relevance"] = family["relevance"]
            link["relevance_evidence"] = family["relevance_evidence"]
        counted = [d for d in da.get("datasets", []) if not d.get("journal_mirror") and d.get("relevance", "in_scope") in COUNTED_RELEVANCE]
        da["has_linked_dataset"] = bool(counted)
        da["has_any_data"] = bool(counted or da.get("supplementary_files") or da.get("status") in ("source_data_supplement", "journal_supplement"))
        da["raw_traces_available"] = any(d.get("content") == "raw_traces" for d in counted)
        da["repositories"] = sorted({d.get("repository") for d in counted + da.get("code", []) if d.get("repository")})
        if not counted and da.get("status") == "public_repository":
            statement = _fold(da.get("statement"))
            supplements = da.get("supplementary_files") or []
            if any("source data" in _fold(item) for item in supplements):
                da["status"] = "source_data_supplement"
            elif supplements:
                da["status"] = "journal_supplement"
            elif da.get("code"):
                da["status"] = "code_only"
            elif "upon request" in statement or "on request" in statement:
                da["status"] = "on_request"
            elif re.search(r"not (available|shared)|no data", statement):
                da["status"] = "not_available"
            elif da.get("fulltext_checked"):
                da["status"] = "not_stated"
            else:
                da["status"] = "unknown_no_fulltext"
