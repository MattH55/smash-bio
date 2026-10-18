"""Resolver-backed identifier verification for the technique modules.

The agent briefs require that an identifier only reaches a record once it has
been resolved, so nothing here is ever guessed.  Two sources are consulted, in
order:

1. ``modules/verified_identifiers.json`` -- a small, committed, human-auditable
   table produced by :func:`warm` (``python -m modules.identifiers``).  It holds
   the codes that were actually confirmed against UniProt / Rfam / ChEBI / GO /
   Cell Ontology / ENA.
2. the SMFS pipeline's own ``out/uniprot_cache.json`` (read-only), which already
   records the accessions resolved for the shared gazetteer.

Anything not confirmed by one of those is reported as ``verified: false`` rather
than being dropped, so an unverified code is visible instead of silent.  The
network is only touched by :func:`warm`, never while building records, which
keeps the test suite offline and the pipeline deterministic.
"""
import json
from pathlib import Path

from common import OUT, get

#: identifier schemes this project can resolve
SCHEMES = ("uniprot", "rfam", "chebi", "go", "cl", "genbank", "gtopdb")

TABLE_PATH = Path(__file__).resolve().parent / "verified_identifiers.json"
SMFS_UNIPROT_CACHE = OUT / "uniprot_cache.json"


def _load_table():
    if TABLE_PATH.exists():
        try:
            return json.loads(TABLE_PATH.read_text(encoding="utf-8"))
        except ValueError:  # pragma: no cover - corrupt table, fall back to empty
            return {}
    return {}


def _load_smfs_accessions():
    """Accessions the SMFS pipeline already resolved (`acc|<id>|` cache keys)."""
    try:
        cache = json.loads(SMFS_UNIPROT_CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    found = set()
    for key, value in cache.items():
        if key.startswith("acc|") and value and value.get("acc"):
            found.add(str(value["acc"]).upper())
    return found


_TABLE = _load_table()
_SMFS_ACCESSIONS = _load_smfs_accessions()


def key(scheme, value):
    return f"{scheme}:{value}"


def verify(scheme, value, expect=True):
    """True when `value` under `scheme` was confirmed by a resolver."""
    if not value:
        return False
    record = _TABLE.get(key(scheme, value))
    if record is not None:
        return bool(record.get("verified", expect))
    if scheme == "uniprot":
        return str(value).upper() in _SMFS_ACCESSIONS
    return False


def identifier(scheme, value, **extra):
    """Schema-shaped Identifier with a resolver-checked ``verified`` flag."""
    row = {"scheme": scheme, "id": value, "verified": verify(scheme, value)}
    row.update(extra)
    return row


# ---------------------------------------------------------------- warm-up (network)
def _check_uniprot(acc):
    d = get(f"https://rest.uniprot.org/uniprotkb/{acc}.json",
            {"fields": "accession"}, retries=1, timeout=20)
    return bool(d and d.get("primaryAccession") == acc)


def _check_ebi(domain, acc, query=None):
    """EBI Search: the entry id must equal the accession we asked about."""
    query = query or acc
    d = get(f"https://www.ebi.ac.uk/ebisearch/ws/rest/{domain}",
            {"query": query, "format": "json", "size": "3"}, retries=1, timeout=20)
    ids = [e.get("id") for e in (d or {}).get("entries", [])]
    return acc in ids or acc.replace(":", "_") in ids


def _check_chebi(acc):
    # EBI Search indexes ChEBI by the bare numeric id ('15956'), not 'CHEBI:15956'.
    numeric = acc.split(":")[-1]
    return _check_ebi("chebi", numeric, query=numeric)


def _check_cell_ontology(acc):
    """OLS4 exact match on the obo_id (CL:0000232)."""
    d = get("https://www.ebi.ac.uk/ols4/api/ontologies/cl/terms",
            {"obo_id": acc, "exact": "true"}, retries=1, timeout=20)
    terms = ((d or {}).get("_embedded") or {}).get("terms") or []
    return any(t.get("obo_id") == acc for t in terms)


def _check_genbank(acc):
    """NCBI nuccore esummary returns a uid only for a resolvable accession."""
    d = get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            {"db": "nuccore", "id": acc, "retmode": "json"}, retries=1, timeout=20)
    result = (d or {}).get("result") or {}
    return bool(result.get("uids"))


_CHECKERS = {
    "uniprot": _check_uniprot,
    "rfam": lambda a: _check_ebi("rfam", a),
    "chebi": _check_chebi,
    "go": lambda a: _check_ebi("go", a),
    "cl": _check_cell_ontology,
    "genbank": _check_genbank,
}


def gene_accession(gene, taxon):
    """UniProt accession the SMFS pipeline already resolved for a gene symbol."""
    try:
        cache = json.loads(SMFS_UNIPROT_CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    record = cache.get(f"gene|{gene}|{taxon}")
    return (record or {}).get("acc")


def warm(pairs, verbose=True, limit=None):
    """Confirm (scheme, value) pairs online and update the committed table."""
    table = dict(_load_table())
    done = 0
    for scheme, value in pairs:
        if limit is not None and done >= limit:
            break
        if not value or key(scheme, value) in table:
            continue
        checker = _CHECKERS.get(scheme)
        if checker is None:
            continue
        try:
            ok = bool(checker(value))
        except Exception as exc:  # pragma: no cover - network flake
            ok = False
            if verbose:
                print(f"  ! {scheme}:{value} failed ({exc!r})", flush=True)
        table[key(scheme, value)] = {"scheme": scheme, "id": value, "verified": ok}
        # checkpoint after every pair so an interrupted run keeps its progress
        TABLE_PATH.write_text(json.dumps(table, ensure_ascii=False, indent=1, sort_keys=True),
                              encoding="utf-8")
        done += 1
        if verbose:
            print(f"  {'ok ' if ok else 'NO '} {scheme}:{value}", flush=True)
    return done, table


def _cli():
    """Confirm every identifier declared by the shared and module gazetteers."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from gazetteer import G
    from modules import gazetteer_ext

    pairs = []
    for entry in G:
        for scheme, value in entry["lookup"].items():
            if scheme in _CHECKERS:
                pairs.append((scheme, value))
    for module_terms in gazetteer_ext.BY_MODULE.values():
        for term in module_terms:
            for item in term["identifiers"]:
                if item["scheme"] in _CHECKERS:
                    pairs.append((item["scheme"], item["id"]))
    seen, unique = set(), []
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            unique.append(pair)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print(f"verifying {len(unique)} identifiers (limit={limit}) ...", flush=True)
    done, table = warm(unique, limit=limit)
    bad = [k for k, v in table.items() if not v.get("verified")]
    print(f"checked {done} new; {len(table)} in table; {len(bad)} unverified", flush=True)
    for name in bad:
        print(f"  unverified: {name}", flush=True)


if __name__ == "__main__":  # pragma: no cover - manual build step
    _cli()