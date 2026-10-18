"""Assemble schema-shaped SMASH-SIM records from classified articles.

Grounding rules (no fabricated data):

* a record is only built when the text grounds a **model** (a named family,
  software, force field or solvent) and a **protocol mode**;
* every extracted value keeps its source unit and its provenance;
* identifiers are written only when a resolver confirmed them;
* when no gazetteer entity matches, the system is named from the publication
  title and that name is marked ``inferred`` rather than presented as curated;
* reduced-unit results always carry reduced units (never a physical unit).
"""
import re
from collections import Counter
from datetime import date

from sim import extract as ex
from sim import identifiers
from sim.classify import article_text
from sim.gazetteer_sim import match_entities


#: a result whose unit_system is `reduced` may only carry one of these units
REDUCED_UNITS = {"epsilon", "sigma", "LJ units", "reduced units", "simulation units"}

PDB_PATTERN = re.compile(
    r"(?:pdb|protein data bank|entry|accession code)\s*[:#(]?\s*(?P<id>[1-9][A-Za-z0-9]{3})\b")

MODEL_KEYS = ("family", "software", "force_field", "solvent")


def _source(article):
    source = {"kind": "publication"}
    for key, value in (("doi", article.get("doi")), ("pmid", article.get("pmid")),
                       ("title", article.get("title")), ("year", article.get("year")),
                       ("journal", article.get("journal"))):
        if value:
            source[key] = value
    authors = [a for a in (article.get("authors") or []) if a][:25]
    if authors:
        source["authors"] = authors
    if article.get("doi"):
        source["url"] = f"https://doi.org/{article['doi']}"
    source["retrieved"] = date.today().isoformat()
    return source


def _merge_dicts(primary, secondary):
    """`primary` (Methods text) wins; `secondary` (abstract) fills the gaps."""
    merged = dict(secondary or {})
    for key, value in (primary or {}).items():
        if key == "evidence":
            merged["evidence"] = (secondary or {}).get("evidence", []) + value
        elif value not in (None, [], {}):
            merged[key] = value
    return merged


def _structure_block(text, method, confidence):
    """Structure source and PDB ids, each verified against RCSB before writing."""
    source = None
    if re.search(r"alphafold", text, re.I):
        source = "AlphaFold"
    matches = list(PDB_PATTERN.finditer(text))
    if matches and source is None:
        source = "PDB"
    if source is None and re.search(r"secondary structure|sequence[- ]based|"
                                    r"nearest[- ]neighbou?r|two[- ]state model", text, re.I):
        source = "predicted_secondary_structure"
    if source is None and re.search(r"\bdesigned\b|de novo design|synthetic construct", text, re.I):
        source = "designed"
    structures = []
    for match in matches[:3]:  # a record needs at most a few distinct entries
        pdb_id = match.group("id").upper()
        if any(row["id"] == pdb_id for row in structures):
            continue
        structures.append({
            "scheme": "pdb", "id": pdb_id, "verified": identifiers.verify_pdb(pdb_id),
            "evidence": [ex.evidence("system.structures", method, text, match, confidence)],
        })
    return source, structures


def _entities(text):
    rows = []
    for entity in match_entities(text):
        row = {"name": entity["name"], "entity_type": entity["entity_type"],
               "role": "tethered_construct"}
        verified = identifiers.verified_only(entity.get("identifiers"))
        if verified:
            row["identifiers"] = verified
        if entity.get("evidence"):
            row["evidence"] = entity["evidence"]
        rows.append(row)
    return rows


def _molecule_type(entities, fallback):
    types = {row["entity_type"] for row in entities}
    nucleic = types & {"dna", "rna"}
    protein = types & {"protein", "protein_complex", "peptide"}
    if nucleic and protein:
        return "DNA_protein" if "dna" in nucleic else "RNA_protein"
    if nucleic == {"dna", "rna"}:
        return "complex"
    if "dna" in nucleic:
        return "DNA"
    if "rna" in nucleic:
        return "RNA"
    if protein:
        return "protein"
    if types:
        return "complex"
    return fallback or "complex"


def _results(abstract_results, methods_results, limit=12):
    """Abstract values first, then observables the Methods text adds."""
    rows = list(abstract_results)
    seen = {row["quantity"] for row in rows}
    for row in methods_results:
        if row["quantity"] in seen:
            continue
        rows.append(row)
        seen.add(row["quantity"])
    return rows[:limit]


def _fair(record):
    source, system = record["source"], record["system"]
    model, protocol = record["model"], record["protocol"]

    def fraction(values):
        return round(sum(1 for value in values if value) / len(values), 3) if values else 0.0

    sections = {
        "publication": fraction([source.get(k) for k in
                                 ("doi", "pmid", "title", "authors", "year", "journal")]),
        "system": fraction([system.get("name"), system.get("molecule_type"),
                            bool(system.get("entities")), bool(system.get("structure_source"))]),
        "model": fraction([model.get(k) for k in MODEL_KEYS] + [model.get("unit_system")]),
        "protocol": fraction([protocol.get("mode"), protocol.get("pulling_speed"),
                              protocol.get("spring_constant"), protocol.get("temperature"),
                              protocol.get("n_trajectories"),
                              (protocol.get("geometry") or {}).get("force_application_geometry")]),
        "results": 1.0 if record.get("results") else 0.0,
        "data": 1.0 if (record["data_availability"].get("has_linked_dataset")
                        or record["data_availability"].get("has_any_data")) else 0.0,
    }
    sections["overall"] = round(sum(sections.values()) / len(sections), 3)
    return sections


def build_record(article, spec, number, fulltext=None):
    """Return (record, None) or (None, reason)."""
    abstract = article_text(article)
    methods = (fulltext or {}).get("methods_text", "")[:20000]
    method_abs, method_ft = "regex_title_abstract", "regex_fulltext_methods"
    confidence_abs, confidence_ft = "low", "medium"

    model = _merge_dicts(ex.detect_model(methods, spec, method_ft, confidence_ft) if methods else None,
                         ex.detect_model(abstract, spec, method_abs, confidence_abs))
    if not any(model.get(key) for key in MODEL_KEYS):
        return None, "no-model-evidence"
    model.setdefault("family", "other")
    model.setdefault("family_group", spec.family_group.get(model["family"], "other"))

    unit_system, conversions = ex.detect_unit_system(
        methods or abstract, spec, method_ft if methods else method_abs,
        confidence_ft if methods else confidence_abs)
    model["unit_system"] = unit_system
    if conversions:
        model["unit_conversions"] = conversions

    protocol = _merge_dicts(ex.detect_protocol(methods, spec, method_ft, confidence_ft) if methods else None,
                            ex.detect_protocol(abstract, spec, method_abs, confidence_abs))
    if not protocol.get("mode"):
        forcing = re.search(spec.forcing_pattern, abstract, re.I)
        if not forcing and methods:
            forcing = re.search(spec.forcing_pattern, methods, re.I)
        if not forcing:
            return None, "no-protocol-evidence"
        protocol["mode"] = "other"
        protocol.setdefault("evidence", []).append({
            "field": "protocol.mode", "method": method_ft if methods else method_abs,
            "snippet": forcing.group(0)[:400], "confidence": "low"})

    results = _results(ex.extract_results(abstract, spec, method_abs, confidence_abs),
                       ex.extract_results(methods, spec, method_ft, confidence_ft) if methods else [])
    for row in results:
        if row["unit_system"] == "reduced" and row["unit"] not in REDUCED_UNITS:
            row["unit_system"] = "physical"  # a `reduced` result may not carry a physical unit

    entities = _entities(" ".join(filter(None, [abstract, methods[:6000]])))
    molecule_type = _molecule_type(entities, article.get("molecule_type"))
    title = (article.get("title") or "").strip()
    system = {"molecule_type": molecule_type,
              "name": entities[0]["name"] if entities else (title[:120] or "unnamed system")}
    if entities:
        system["entities"] = entities
        system["evidence"] = [{"field": "system.name", "method": "gazetteer",
                               "snippet": (entities[0].get("evidence") or {}).get("snippet", "")[:400],
                               "confidence": "medium"}]
    else:
        system["evidence"] = [{"field": "system.name", "method": "inferred",
                               "snippet": (title or abstract)[:400], "confidence": "low"}]
    structure_source, structures = _structure_block(
        " ".join(filter(None, [abstract, methods[:6000]])), method_abs, confidence_abs)
    construct = (ex.detect_construct(methods, spec, method_ft, confidence_ft) if methods else None)
    if construct is None:
        construct = ex.detect_construct(abstract, spec, method_abs, confidence_abs)
    if construct:
        system["construct"] = construct
    if structure_source:
        system["structure_source"] = structure_source
    if structures:
        system["structures"] = structures

    if fulltext:
        from sim.fulltext import data_availability
        data = data_availability(fulltext)
    else:
        data = ex.detect_data(abstract, spec, method_abs, confidence_abs)

    record = {
        "record_id": spec.record_id(number),
        "schema_version": spec.version,
        "category": "simulation",
        "source": _source(article),
        "system": system,
        "model": model,
        "protocol": protocol,
        "results": results,
        "data_availability": data,
        "curation": {"status": "auto_extracted", "date": date.today().isoformat(),
                     "notes": "Automatic extraction from the title/abstract"
                              + (" and open-access Methods text." if methods
                                 else "; no open-access Methods text was found.")},
        "provenance": [{"field": "record", "method": method_ft if methods else method_abs,
                        "snippet": (title or abstract)[:400], "confidence": "low"}],
    }
    record["fair_completeness"] = _fair(record)
    return record, None


def apply_overrides(record, overrides):
    """Apply hand-curated field overrides (sim/curated_overrides.json), keyed by DOI.

    Dotted keys ("protocol.geometry.anchor_a") replace that field; the curator note is kept
    on the record so the correction is visible.
    """
    o = overrides.get(str(record.get("source", {}).get("doi") or record.get("doi") or "").lower())
    if not o:
        return record
    for key, value in o.items():
        if key.startswith("_") or key == "curator_note":
            continue
        node = record
        parts = key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = value
    record.setdefault("curation", {})["notes"] = o.get("curator_note", "")
    record["curation"]["level"] = "curated"
    return record


def build_records(articles, spec, start=1, fulltext_index=None):
    """Build one record per in-scope article. Returns (records, skipped_counter)."""
    import json
    from pathlib import Path

    ov_path = Path(__file__).with_name("curated_overrides.json")
    overrides = {k.lower(): v for k, v in json.loads(ov_path.read_text(encoding="utf-8")).items()} if ov_path.exists() else {}
    from sim.fulltext import parsed_for

    index = fulltext_index or {}
    records, skipped = [], Counter()
    number = start
    for article in articles:
        fulltext = parsed_for(article.get("epmc_id"), index) if index else None
        record, reason = build_record(article, spec, number, fulltext=fulltext)
        if record is None:
            skipped[reason] += 1
            continue
        records.append(apply_overrides(record, overrides))
        number += 1
    return records, skipped