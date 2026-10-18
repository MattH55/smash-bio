"""Match simulation records to experimental records.

SMASH-BIO first, then MechanoProDB. A match needs a shared resolver-backed
identifier (UniProt, PDB, Rfam or GenBank) and, for the strongest level, the
same pulling geometry in the experimental representation the sim schema reuses.
Nothing is matched on a fuzzy name alone except the explicitly weaker `homolog`
level, which requires a shared distinctive molecule token and identifiers that
disagree or are absent.

Outputs: a match table (parquet + CSV) and a coverage table that shows where
simulation coverage is missing.
"""
import json
import re
from pathlib import Path

from common import load_jsonl
from modules.base import hub_dir
from sim.gazetteer_sim import SIM_SYSTEMS


MECHANOPRODB_ENTRIES = hub_dir() / "data" / "sim" / "mechanoprodb_entries.json"
IDENTIFIER_SCHEMES = ("uniprot", "pdb", "rfam", "genbank")
FORCE_QUANTITIES = ("unfolding_force", "rupture_force", "unbinding_force",
                    "unzipping_force", "overstretching_force", "equilibrium_force")
GENERIC_TOKENS = {"protein", "domain", "complex", "dna", "rna", "hairpin", "human",
                  "bovine", "domains", "structure", "repeat", "repeats", "average",
                  "minimized", "nmr", "the", "and", "e.coli", "linked", "chain"}

#: never report more than this many experimental matches for one simulation
MAX_MATCHES_PER_RECORD = 20
#: never report more than this many name-based (`homolog`) matches for one simulation
MAX_HOMOLOG_MATCHES = 5

#: category-local system names (base form, lower case): only a record's *primary*
#: entity is used for matching, and only when it comes from this curated list. The
#: broader shared gazetteer lists context molecules and reagents (streptavidin
#: handles, spike-protein mentions) whose identifiers would otherwise match
#: hundreds of unrelated experiments.
LOCAL_SYSTEMS = {term["name"].split(" (")[0].strip().lower() for term in SIM_SYSTEMS}


def _range(text):
    """First residue range in a string, as (start, end) ints."""
    import re
    match = re.search(r"([0-9]+)\s*[-–]\s*([0-9]+)", str(text or ""))
    return (int(match.group(1)), int(match.group(2))) if match else None


def _ranges_compatible(a, b):
    """True/None: do two construct ranges overlap, or is it unknown?"""
    first, second = _range(a), _range(b)
    if not first or not second:
        return None
    return not (first[1] < second[0] or second[1] < first[0])


def _tokens(name):
    """Distinctive tokens of a molecule name (split on any non-alphanumeric run)."""
    return {token for token in re.split(r"[^a-z0-9]+", str(name or "").lower())
            if len(token) >= 3 and token not in GENERIC_TOKENS}


def _drop_none(row):
    return {key: value for key, value in row.items() if value is not None}


def _homolog_tokens(record):
    """Tokens of the record's grounded entity names: a name match needs all of them."""
    keys = []
    for entity in record["system"].get("entities") or []:
        tokens = _tokens(entity["name"])
        if tokens:
            keys.append(tokens)
    return keys


def load_smash(smfs_path):
    """Experimental SMASH-BIO records as matchable dicts."""
    rows = []
    for record in load_jsonl(smfs_path):
        entities = (record.get("biological_system") or {}).get("entities") or []
        identifiers = []
        molecule = None
        region = None
        for entity in entities:
            if molecule is None:
                molecule, region = entity.get("name"), entity.get("region")
            for item in entity.get("identifiers") or []:
                if item.get("scheme") in IDENTIFIER_SCHEMES and item.get("verified"):
                    identifiers.append((item["scheme"], str(item["id"]).upper()))
        force = None
        for result in record.get("results") or []:
            if result.get("quantity") in FORCE_QUANTITIES and result.get("value") is not None:
                force = float(result["value"])
                break
        rows.append({
            "record_id": record.get("record_id"), "source": "SMASH-BIO",
            "molecule": molecule, "region": region, "identifiers": identifiers,
            "geometry": (record.get("technique") or {}).get("force_application_geometry"),
            "force_pN": force, "molecule_type": None,
            "url": f"https://smash-bio.org/record.html?id={record.get('record_id')}",
        })
    return rows


def load_mechanoprodb(path=None):
    """MechanoProDB *experimental* rows (the simulation rows are SIM records)."""
    path = Path(path or MECHANOPRODB_ENTRIES)
    if not path.exists():
        return []
    rows = []
    for row in json.loads(path.read_text(encoding="utf-8")):
        if str(row.get("source")) != "experiment":
            continue
        identifiers = [("pdb", str(row["pdb_id"]).upper())] if row.get("pdb_id") else []
        rows.append({
            "record_id": f"MPDB:{row.get('id')}", "source": "MechanoProDB",
            "molecule": row.get("name"), "region": row.get("domain_coords"),
            "identifiers": identifiers, "geometry": None,
            "force_pN": float(row["force_pN"]) if row.get("force_pN") is not None else None,
            "molecule_type": "protein",
            "url": (row.get("doi_pulling") or "https://mechanoprodb.ibdm.univ-amu.fr"),
        })
    return rows


def _index(experimental):
    by_identifier, by_token = {}, {}
    for row in experimental:
        for scheme, value in row["identifiers"]:
            by_identifier.setdefault(f"{scheme}:{value}", []).append(row)
        for token in _tokens(row["molecule"]):
            by_token.setdefault(token, []).append(row)
    return by_identifier, by_token


def _sim_identifiers(record):
    """Identifiers of the primary, category-local entity (plus verified PDB entries)."""
    rows = []
    entities = record["system"].get("entities") or []
    if entities:
        primary = entities[0]
        base = primary["name"].split(" (")[0].strip().lower()
        if base in LOCAL_SYSTEMS:
            for item in primary.get("identifiers") or []:
                if item.get("scheme") in IDENTIFIER_SCHEMES and item.get("verified"):
                    rows.append((item["scheme"], str(item["id"]).upper()))
    for structure in record["system"].get("structures") or []:
        if structure.get("scheme") == "pdb" and structure.get("verified"):
            rows.append(("pdb", str(structure["id"]).upper()))
    return sorted(set(rows))


def _sim_force(record):
    for result in record.get("results") or []:
        if result.get("quantity") in FORCE_QUANTITIES and result.get("value") is not None:
            return float(result["value"])
    return None


def _level(sim, exp, shared_identifier):
    geometry_sim = (sim["protocol"].get("geometry") or {}).get("force_application_geometry")
    geometry_exp = exp.get("geometry")
    overlap = _ranges_compatible((sim["system"].get("construct") or {}).get("residue_range"),
                                 exp.get("region"))
    if shared_identifier:
        # `same_construct_same_geometry` is only claimed when the construct is actually
        # confirmed to overlap: no evidence is not evidence of the same construct.
        if geometry_sim and geometry_exp and geometry_sim == geometry_exp and overlap is True:
            return "same_construct_same_geometry"
        return "same_molecule_different_geometry"
    return "homolog"


def annotate(records, experimental):
    """Fill ``links.experimental_matches`` and return the match rows."""
    by_identifier, by_token = _index(experimental)
    matches = []
    for record in records:
        identifiers = _sim_identifiers(record)
        sim_force = _sim_force(record)
        found, seen = [], set()
        candidates = []
        sim_tokens = _tokens(record["system"].get("name"))
        for scheme, value in identifiers:
            for exp in by_identifier.get(f"{scheme}:{value}", []):
                if scheme != "pdb" and not (sim_tokens & _tokens(exp.get("molecule"))):
                    continue  # an identifier alone is not enough: the molecule must agree
                candidates.append((f"{scheme}:{value}", exp))
        if not candidates:
            homolog, seen_homolog = [], set()
            for tokens in _homolog_tokens(record):
                anchor = min(tokens, key=lambda t: len(t))
                for exp in by_token.get(anchor, []):
                    if not tokens <= _tokens(exp.get("molecule")):
                        continue
                    key = (exp["source"], exp["record_id"])
                    if key in seen_homolog:
                        continue
                    seen_homolog.add(key)
                    homolog.append((None, exp))
                    if len(homolog) >= MAX_HOMOLOG_MATCHES:
                        break
                if len(homolog) >= MAX_HOMOLOG_MATCHES:
                    break
            candidates.extend(homolog)
        for shared, exp in candidates:
            key = (exp["source"], exp["record_id"])
            if key in seen:
                continue
            seen.add(key)
            level = _level(record, exp, shared)
            geometry_sim = (record["protocol"].get("geometry") or {}).get(
                "force_application_geometry")
            row = {
                "sim_record_id": record["record_id"], "experimental_record_id": exp["record_id"],
                "experimental_source": exp["source"], "match_level": level,
                "shared_identifier": shared, "molecule": exp.get("molecule"),
                "geometry_sim": geometry_sim,
                "geometry_experimental": exp.get("geometry"),
                "geometry_match": bool(geometry_sim and exp.get("geometry")
                                       and geometry_sim == exp["geometry"]),
                "force_sim_pN": sim_force, "force_experimental_pN": exp.get("force_pN"),
                "delta_force_pN": (None if sim_force is None or exp.get("force_pN") is None
                                   else round(sim_force - exp["force_pN"], 3)),
                "url": exp.get("url"),
            }
            matches.append(row)
            if len(found) >= MAX_MATCHES_PER_RECORD:
                continue
            found.append(_drop_none({
                "record_id": exp["record_id"], "source": exp["source"],
                "molecule": exp.get("molecule"), "url": exp.get("url"),
                "force_pN": exp.get("force_pN"), "match_level": level,
                "evidence": [{"field": "links.experimental_matches",
                              "method": "repository_api" if exp["source"] == "MechanoProDB" else "gazetteer",
                              "snippet": (f"shared {shared}" if shared else "shared molecule name token")
                                         + f"; experimental geometry {exp.get('geometry')}",
                              "confidence": "medium" if shared else "low"}],
            }))
        if found:
            record.setdefault("links", {})["experimental_matches"] = found[:20]
    return records, matches


def coverage(matches, records):
    """Experimental systems covered by at least one simulation, by match level."""
    model_family = {record["record_id"]: record["model"].get("family") for record in records}
    molecule_type = {record["record_id"]: record["system"].get("molecule_type") for record in records}
    seen, rows = set(), {}
    for match in matches:
        key = (match["experimental_source"], match["experimental_record_id"])
        bucket = (molecule_type.get(match["sim_record_id"]),
                  model_family.get(match["sim_record_id"]), match["match_level"])
        if (key, bucket) in seen:
            continue
        seen.add((key, bucket))
        rows[bucket] = rows.get(bucket, 0) + 1
    return [{"molecule_type": key[0], "model_family": key[1], "match_level": key[2],
             "n_experimental_systems": value}
            for key, value in sorted(rows.items(), key=lambda item: str(item[0]))]


def write_matches(records, spec, out_dir=None, smfs_path=None, mechanoprodb_path=None):
    """Annotate records, write matches.parquet + coverage.csv, rewrite the records file."""
    import pandas as pd

    out_dir = Path(out_dir or (hub_dir() / "out" / spec.slug))
    data_dir = hub_dir() / "data" / spec.slug
    data_dir.mkdir(parents=True, exist_ok=True)
    experimental = load_smash(smfs_path) + load_mechanoprodb(mechanoprodb_path)
    records, matches = annotate(records, experimental)
    coverage_rows = coverage(matches, records)

    parquet = data_dir / "matches.parquet"
    pd.DataFrame(matches).to_parquet(parquet, index=False)
    (data_dir / "coverage.csv").write_text(
        "molecule_type,model_family,match_level,n_experimental_systems\n"
        + "\n".join(f"{r['molecule_type']},{r['model_family']},{r['match_level']},"
                    f"{r['n_experimental_systems']}" for r in coverage_rows) + "\n",
        encoding="utf-8")

    from common import save_jsonl
    save_jsonl(out_dir / f"{spec.slug}_records.jsonl", records)
    return {"records": len(records), "matches": len(matches),
            "fewer_than_two_matches": sum(
                1 for r in records if len((r.get("links") or {}).get("experimental_matches") or []) < 2),
            "parquet": str(parquet), "coverage_rows": len(coverage_rows),
            "coverage": coverage_rows}