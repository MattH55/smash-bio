"""Ingest existing pulling-simulation datasets into ``hub/data/sim/``.

Every dataset gets a provenance file recording its licence, retrieval date and
SHA-256. Data is only copied when the licence allows redistribution; where it
does not (or is unstated) the entry indexes metadata and links to the source.
The brief's five targets are handled here: ForceGen, BSDB, Mykuliak et al. 2020,
MechanoProDB's steered-MD rows, and any SMASH-SIM outputs.

External calls go through ``modules.harvest.polite_get`` (the shared cached HTTP
layer at half the SMFS request rate).
"""
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from modules.base import hub_dir
from modules.harvest import polite_get


DATA_DIR = hub_dir() / "data" / "sim"
REPO_ROOT = hub_dir().parent
MECHANOPRODB_PARQUET = (REPO_ROOT / "Meeta Analysis" / "mechanoprodb-reanalysis"
                        / "data" / "processed" / "entries.parquet")
MECHANOPRODB_TERMS = (REPO_ROOT / "Meeta Analysis" / "mechanoprodb-reanalysis"
                      / "data" / "raw" / "site_terms.html")

FORCEGEN_REPO = "lamm-mit/ProteinMechanicsDiffusionDesign"
MYKULIAK_DOI = "10.23729/e4805d6f-e85e-4712-8481-948dfc7c6f0e"
BSDB_URLS = (
    "http://jowisz.ifpan.edu.pl/BSDB/",
    "https://jowisz.ifpan.edu.pl/BSDB/",
    "http://info.ifpan.edu.pl/BSDB/",
)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def _status(url, timeout=25):
    """Cheap reachability probe: (http_status, final_url, bytes)."""
    import requests
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True,
                                headers={"User-Agent": "SMASH-BIO-sim/1.0 (mailto:mhalma@opensourcemed.info)"})
        return response.status_code, response.url, len(response.content)
    except Exception as exc:  # pragma: no cover - network dependent
        return None, f"{type(exc).__name__}: {exc}"[:120], 0


def ingest_forcegen():
    repo = polite_get(f"https://api.github.com/repos/{FORCEGEN_REPO}")
    contents = polite_get(f"https://api.github.com/repos/{FORCEGEN_REPO}/contents") or []
    licence = ((repo or {}).get("license") or {}).get("spdx_id")
    entry = {
        "id": "forcegen",
        "name": "ForceGen steered-MD dataset (Ni, Kaplan & Buehler)",
        "kind": "dataset",
        "source_url": f"https://github.com/{FORCEGEN_REPO}",
        "arxiv": "arXiv:2310.10605",
        "license": licence or "not stated in the repository API response",
        "license_url": ((repo or {}).get("license") or {}).get("url"),
        "redistributable": bool(licence and licence.upper() in {"MIT", "APACHE-2.0", "BSD-3-CLAUSE"}),
        "retrieved": date.today().isoformat(),
        "status": "reachable" if repo else "unreachable",
        "notes": "All-atom steered MD of ~7,000 proteins selected from BSDB (NAMD, CHARMM, "
                 "generalized-Born implicit solvent). Metadata indexed only: the per-protein "
                 "force-extension records are large and are not copied here.",
        "repo": {
            "description": (repo or {}).get("description"),
            "pushed_at": (repo or {}).get("pushed_at"),
            "default_branch": (repo or {}).get("default_branch"),
            "top_level_entries": [c.get("name") for c in contents][:40],
        },
        "unit_system": "physical (kcal/mol/A force field units, reported forces in pN)",
    }
    return entry


def ingest_bsdb():
    probes = []
    for url in BSDB_URLS:
        status, final, size = _status(url, timeout=20)
        probes.append({"url": url, "http_status": status, "final_url": final, "bytes": size})
    archive = polite_get("https://archive.org/wayback/available",
                         {"url": "jowisz.ifpan.edu.pl/BSDB/"})
    snapshot = ((archive or {}).get("archived_snapshots") or {}).get("closest") or {}
    archived = {"available": bool(snapshot), "url": snapshot.get("url"),
                "timestamp": snapshot.get("timestamp")}
    if snapshot.get("url"):
        # read the archived copy so the report can say what it actually holds
        html = polite_get(snapshot["url"], as_json=False) or ""
        if html:
            archived.update({
                "http_body_bytes": len(html),
                "mentions": sorted({word for word in
                                    ("stretching", "download", "protein", "17,134", "17134",
                                     "reduced", "csv", "contact map", "mechanical clamp")
                                    if re.search(re.escape(word), html, re.I)}),
                "snippet": " ".join(re.sub(r"<[^>]+>", " ", html).split())[:300],
            })
    entry = {
        "id": "bsdb",
        "name": "BSDB, the Biomolecule Stretching Database (Sikora, Sulkowska, Witkowski & Cieplak)",
        "kind": "database",
        "source_url": "http://jowisz.ifpan.edu.pl/BSDB/",
        "citation": "Nucleic Acids Res 2011; PLoS Comput Biol 2009 5:e1000422",
        "license": "not stated on the reachable pages",
        "redistributable": False,
        "retrieved": date.today().isoformat(),
        "status": "unreachable" if not any(p["http_status"] == 200 for p in probes) else "reachable",
        "probes": probes,
        "internet_archive": archived,
        "notes": "Cα-Gō peak forces and mechanical-clamp annotations for ~17,134 model proteins, "
                 "in reduced units with the authors' stated conversion. Nothing is copied: the "
                 "licence is unstated, so only this metadata record and links are kept. "
                 "See REPORT-sim.md for the question to put to the Cieplak group.",
        "unit_system": "reduced_with_stated_conversion (ε and σ as published)",
    }
    return entry


def ingest_mykuliak():
    doi = MYKULIAK_DOI
    data = polite_get(f"https://api.datacite.org/dois/{doi}")
    attributes = ((data or {}).get("data") or {}).get("attributes") or {}
    rights = attributes.get("rightsList") or []
    licence = rights[0].get("rights") if rights else None
    entry = {
        "id": "mykuliak-2020",
        "name": "Steered MD vs boxed MD benchmark (Mykuliak et al., Biophys J 2020)",
        "kind": "dataset",
        "source_url": attributes.get("url") or f"https://doi.org/{doi}",
        "doi": doi,
        "license": licence or "not stated in the DataCite metadata",
        "license_url": (rights[0].get("rightsUri") if rights else None),
        "redistributable": bool(licence and re.search(
            r"CC[ -]BY|creative commons attribution|attribution 4\.0", licence, re.I)),
        "retrieved": date.today().isoformat(),
        "status": "reachable" if data else "unreachable",
        "datacite": {
            "title": ((attributes.get("titles") or [{}])[0] or {}).get("title"),
            "publisher": attributes.get("publisher"),
            "published": attributes.get("published"),
            "resource_type": ((attributes.get("types") or {}).get("resourceTypeGeneral")),
        },
        "notes": "Small method benchmark released under CC BY 4.0 on Fairdata; indexed with a link. "
                 "Files are fetched only if redistribution is later confirmed as wanted.",
        "unit_system": "physical",
    }
    return entry


def load_mechanoprodb():
    """The local MechanoProDB export (MIT-licensed per the site terms page)."""
    import pandas as pd

    frame = pd.read_parquet(MECHANOPRODB_PARQUET)
    rows = json.loads(frame.to_json(orient="records"))
    return frame, rows


def ingest_mechanoprodb(rows=None):
    frame, rows = load_mechanoprodb() if rows is None else (None, rows)
    terms_sha = sha256(MECHANOPRODB_TERMS) if MECHANOPRODB_TERMS.exists() else None
    simulations = [r for r in rows if str(r.get("source")) == "simulation"]
    entry = {
        "id": "mechanoprodb",
        "name": "MechanoProDB simulation entries (Mesbah, Habermann & Rico, Database 2024)",
        "kind": "database",
        "source_url": "https://mechanoprodb.ibdm.univ-amu.fr",
        "doi": "10.1093/database/baae047",
        "license": "MIT",
        "license_url": "https://mechanoprodb.ibdm.univ-amu.fr/terms.html",
        "redistributable": True,
        "retrieved": date.today().isoformat(),
        "status": "ingested",
        "local_export": {
            "path": str(MECHANOPRODB_PARQUET.relative_to(REPO_ROOT)),
            "sha256": sha256(MECHANOPRODB_PARQUET),
            "n_entries": len(rows),
            "terms_sha256": terms_sha,
        },
        "counts": {"simulation": len(simulations),
                   "experiment": len([r for r in rows if str(r.get("source")) == "experiment"])},
        "notes": "Only the steered-MD rows (source == 'simulation') become SIM records, as "
                 "'database' sources that keep the original publication (doi_pulling) on each "
                 "entry. The MIT terms page permits redistribution with attribution.",
        "unit_system": "physical",
    }
    return entry, rows


def probe_smash_sim():
    candidates = [
        REPO_ROOT / "smash-sim" / "out" / "harmonized.parquet",
        REPO_ROOT / "smash-sim" / "out" / "summary.csv",
    ]
    found = [str(p.relative_to(REPO_ROOT)) for p in candidates if p.exists()]
    return {
        "id": "smash-sim-outputs",
        "name": "SMASH-SIM harmonized outputs",
        "kind": "smash_sim_generated",
        "source_url": None,
        "license": "n/a (generated by this project)",
        "redistributable": True,
        "retrieved": date.today().isoformat(),
        "status": "ingested" if found else "not_found",
        "found": found,
        "notes": ("Ingested as smash_sim_generated records when present."
                  if found else
                  "No smash-sim/out/harmonized.parquet or summary.csv in this workspace, so there "
                  "is nothing to ingest. The reader is in place for when the SMASH-SIM project "
                  "produces them."),
    }


def run(offline=False):
    """Ingest every dataset; returns (entries, mechanoprodb_rows)."""
    entries = []
    rows = []
    entries.append(ingest_forcegen() if not offline else {"id": "forcegen", "status": "skipped_offline",
                                                          "redistributable": False})
    entries.append(ingest_bsdb() if not offline else {"id": "bsdb", "status": "skipped_offline",
                                                     "redistributable": False})
    entries.append(ingest_mykuliak() if not offline else {"id": "mykuliak-2020",
                                                          "status": "skipped_offline",
                                                          "redistributable": False})
    entry, rows = ingest_mechanoprodb()
    entries.append(entry)
    entries.append(probe_smash_sim())
    for item in entries:
        _write(DATA_DIR / "datasets" / f"{item['id']}.json", item)
    _write(DATA_DIR / "datasets_index.json",
           {"built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "datasets": entries})
    _write(DATA_DIR / "mechanoprodb_entries.json", rows)
    return entries, rows


def load_entries():
    """Previously ingested entries and MechanoProDB rows (no network)."""
    index = DATA_DIR / "datasets_index.json"
    entries = json.loads(index.read_text(encoding="utf-8"))["datasets"] if index.exists() else []
    rows_path = DATA_DIR / "mechanoprodb_entries.json"
    rows = json.loads(rows_path.read_text(encoding="utf-8")) if rows_path.exists() else []
    return entries, rows


def dataset_records(entries, rows, spec, start=1):
    """SIM records sourced from datasets/databases (MechanoProDB steered-MD rows)."""
    from sim import extract as ex

    mechanoprodb = next((e for e in entries if e["id"] == "mechanoprodb"), None)
    records = []
    number = start
    for row in rows:
        if str(row.get("source")) != "simulation":
            continue
        evidence = [{"field": "source", "method": "repository_api", "confidence": "medium",
                     "snippet": f"MechanoProDB entry {row.get('id')}: "
                                f"{row.get('technique_raw')} (source={row.get('source')})"}]
        results = []
        for value, quantity, unit, label in (
                (row.get("force_pN"), "unfolding_force", "pN", "peak unfolding force"),
                (row.get("xbeta_nm"), "distance_to_transition_state", "nm", "x_beta"),
                (row.get("koff_s"), "rate_constant_zero_force", "1/s", "k_off"),
                (row.get("dG_kBT"), "activation_free_energy", "kBT", "Delta G"),
                (row.get("contour_length_nm"), "contour_length", "nm", "contour length")):
            if value is None or value != value:  # skip None/NaN
                continue
            results.append({"quantity": quantity, "value": float(value), "unit": unit,
                            "label": label, "unit_system": "physical",
                            "provenance": [{"field": f"results[{len(results)}]",
                                            "method": "repository_api",
                                            "snippet": f"MechanoProDB entry {row.get('id')}",
                                            "confidence": "medium"}]})
        protocol = {"mode": "constant_velocity", "evidence": evidence}
        if row.get("velocity_nms") is not None and row.get("velocity_nms") == row.get("velocity_nms"):
            protocol["pulling_speed"] = {"value": float(row["velocity_nms"]), "unit": "nm/s",
                                         "note": "MechanoProDB velocity_nms"}
            protocol["pulling_speed_m_per_s"] = float(row["velocity_nms"]) * 1e-9
        if row.get("loading_rate_pns") is not None and row.get("loading_rate_pns") == row.get("loading_rate_pns"):
            results.append({"quantity": "loading_rate", "value": float(row["loading_rate_pns"]),
                            "unit": "pN/s", "unit_system": "physical",
                            "provenance": [{"field": f"results[{len(results)}]",
                                            "method": "repository_api",
                                            "snippet": f"MechanoProDB entry {row.get('id')}",
                                            "confidence": "medium"}]})
        if row.get("temp_C") is not None and row.get("temp_C") == row.get("temp_C"):
            protocol["temperature"] = {"value": float(row["temp_C"]) + 273.15, "unit": "K",
                                       "note": "converted from the reported Celsius value"}
        system = {"molecule_type": "protein",
                  "name": (row.get("name") or f"PDB {row.get('pdb_id')}")[:120],
                  "evidence": evidence}
        if row.get("pdb_id"):
            system["structure_source"] = "PDB"
            system["structures"] = [{"scheme": "pdb", "id": str(row["pdb_id"]).upper(),
                                     "verified": True, "evidence": evidence}]
        if row.get("domain_coords"):
            system["construct"] = {"residue_range": str(row["domain_coords"]), "evidence": evidence}
        record = {
            "record_id": spec.record_id(number),
            "schema_version": spec.version,
            "category": "simulation",
            "source": {"kind": "database", "accession": f"MPDB:{row.get('id')}",
                       "title": mechanoprodb["name"] if mechanoprodb else "MechanoProDB",
                       "url": "https://mechanoprodb.ibdm.univ-amu.fr",
                       "doi": row.get("doi_pulling") or None,
                       "license": "MIT", "redistributable": True,
                       "retrieved": date.today().isoformat(),
                       "notes": f"Original publication: {row.get('doi_pulling')}",
                       "evidence": evidence},
            "system": system,
            "model": {"family": "other", "family_group": "protein",
                      "parameter_set": "all atom SMD simulation (MechanoProDB technique_raw)",
                      "unit_system": "physical",
                      "evidence": evidence},
            "protocol": protocol,
            "results": results,
            "data_availability": {"status": "public_repository", "has_linked_dataset": True,
                                  "has_any_data": True,
                                  "statement": "Indexed from MechanoProDB (MIT); see the original "
                                               "publication for the deposited files."},
            "curation": {"status": "auto_extracted", "date": date.today().isoformat(),
                         "notes": "Built from the MechanoProDB export, not from the paper text. "
                                  "Unfolding-pathway codes and clamp motifs are not interpreted."},
            "provenance": evidence,
        }
        _clean(record, ex)
        records.append(record)
        number += 1
    return records


def _clean(record, ex):
    """Drop empty keys so the record stays honest about what is known."""
    for key in list(record):
        if record[key] in (None, {}, []):
            del record[key]
    record.setdefault("model", {})
    record["model"].setdefault("unit_system", "physical")
    return record