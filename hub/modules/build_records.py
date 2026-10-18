"""Assemble schema-valid module records from classified articles.

A record is only produced when the required schema fields can be grounded in
the text: entities for the biological system, a technique, and (for FRET) a
donor/acceptor label pair. Otherwise the article yields no record rather than a
guessed one.
"""
import datetime
import re
from functools import lru_cache

from modules.extract import extract_results, extract_software
from modules.fulltext import data_availability, parsed_for
from modules.gazetteer_ext import match_entities


# Named dye pairs with known donor/acceptor roles (auditable domain knowledge).
# Only the common, commercially standard smFRET pairs are listed; an unlisted
# combination yields no record rather than a guessed donor/acceptor assignment.
DYE_PAIRS = [
    ("Cy3", "Cy5"), ("Cy3B", "Cy5"), ("Cy3", "Cy5.5"),
    ("Cy3", "ATTO 647N"), ("Cy3", "ATTO 655"), ("Cy3", "Alexa 647"),
    ("Cy3B", "ATTO 647N"),
    ("ATTO 488", "ATTO 590"), ("ATTO 488", "ATTO 647N"), ("ATTO 488", "Cy5"),
    ("ATTO 532", "ATTO 647N"), ("ATTO 550", "ATTO 647"), ("ATTO 550", "ATTO 647N"),
    ("ATTO 565", "ATTO 647N"),
    ("Alexa 488", "Alexa 594"), ("Alexa 488", "Cy5"),
    ("Alexa 546", "Alexa 647"), ("Alexa 555", "Alexa 647"),
    ("LD555", "LD655"), ("DyLight 550", "DyLight 650"),
    ("TMR", "ATTO 647N"), ("TMR", "Cy5"), ("TAMRA", "ATTO 647N"),
    ("JF549", "JF646"),
]


@lru_cache(maxsize=None)
def _dye_pattern(name):
    """Tolerant regex for a dye name (vendor spellings, optional 'Fluor')."""
    if name.startswith("Alexa "):
        return r"alexa\s*(?:fluor\s*)?" + re.escape(name.split()[-1])
    if name.startswith("ATTO "):
        return r"atto\s*" + re.escape(name.split()[-1])
    if name.startswith("DyLight "):
        return r"dylight\s*(?:\(r\)\s*)?" + re.escape(name.split()[-1])
    if name == "Cy3":
        return r"cy\s*3(?![b\d])"
    if name == "Cy3B":
        return r"cy\s*3\s*b"
    if name == "Cy5":
        return r"cy\s*5(?!\s*\.?\s*5)"
    if name == "Cy5.5":
        return r"cy\s*5\s*\.?\s*5"
    return re.escape(name)


def _sentence(text, match):
    return (text[max(0, match.start() - 40):match.end() + 20])[:400]


def detect_fluorophores(text):
    """Return [donor, acceptor] fluorophore dicts when a known pair is named."""
    text = text or ""
    for donor, acceptor in DYE_PAIRS:
        m1 = re.search(_dye_pattern(donor), text, re.I)
        m2 = re.search(_dye_pattern(acceptor), text, re.I)
        if m1 and m2:
            return [
                {"role": "donor", "name": donor, "labeling_site": "stated"},
                {"role": "acceptor", "name": acceptor, "labeling_site": "stated"},
            ]
    return []


def technique_block(article, spec):
    tags = set(article.get("techniques_detected") or [])
    tier = article.get("tier")
    if spec.slug == "fret":
        if tier == "methods":
            primary = "smfret_methods"
        elif "in_cell" in tags:
            primary = "smfret_in_cell"
        elif "zmw" in tags:
            primary = "smfret_nanopore_or_zmw"
        elif "tirf_widefield" in tags:
            primary = "smfret_tirf_widefield"
        elif tags & {"alex", "pie"}:
            primary = "smfret_confocal_scanning_immobilized"
        else:
            primary = "smfret_confocal_burst"
        block = {"primary": primary}
        if "alex" in tags:
            block["excitation_scheme"] = "ALEX"
        elif "pie" in tags:
            block["excitation_scheme"] = "PIE"
        elif "mfd" in tags:
            block["excitation_scheme"] = "MFD"
        if "tirf_widefield" in tags:
            block["geometry"] = "TIRF_immobilized"
            block["detection"] = "camera"
        elif "confocal_burst" in tags:
            block["geometry"] = "confocal_diffusion"
            block["detection"] = "point_detector"
        return block
    if spec.slug == "spt":
        return {"primary": "SPT"}
    if spec.slug == "mp":
        return {"primary": "MP"}
    if spec.slug == "channel":
        # detector tags -> schema configuration vocabulary
        config = next((CONFIGURATIONS[tag] for tag in CONFIGURATIONS if tag in tags), "other")
        return {"primary": "SC", "configuration": config}
    return {}


# classify.py emits short detector tags; the schema uses the fuller names.
CONFIGURATIONS = {
    "cell_attached": "cell_attached",
    "inside_out": "inside_out",
    "outside_out": "outside_out",
    "planar_bilayer": "planar_lipid_bilayer",
    "droplet_interface": "droplet_interface_bilayer",
}


def _publication(article, spec):
    pub = {
        "title": article.get("title") or "",
    }
    for key, src in (("doi", "doi"), ("pmid", "pmid"), ("pmcid", "pmcid"),
                     ("journal", "journal"), ("year", "year"),
                     ("abstract", "abstract"), ("open_access", "is_oa")):
        if article.get(src) is not None:
            pub[key] = article[src]
    if article.get("authors"):
        pub["authors"] = article["authors"]
    return pub


def _fair(record):
    available = ("public_repository", "source_data_supplement", "journal_supplement", "code_only")
    groups = {
        "publication": bool(record.get("publication", {}).get("title")),
        "data": record.get("data_availability", {}).get("status") in available,
    }
    scores = {k: (1.0 if v else 0.0) for k, v in groups.items()}
    scores["overall"] = round(sum(scores.values()) / len(scores), 3)
    return scores


def build_record(article, spec, number, software_pool=None, fulltext=None):
    """Return a schema-shaped record dict, or None when required fields are absent.

    `fulltext` is a parsed ``s05_fulltext`` result.  When present its Methods
    section is the primary grounding text (the brief asks for Methods first,
    abstracts otherwise) and the availability block reports what it shows.
    """
    title_abs = " ".join(filter(None, [article.get("title"), article.get("abstract")]))
    methods = (fulltext or {}).get("methods_text") or ""
    text = " ".join(filter(None, [title_abs, methods]))
    source = "regex_fulltext_methods" if methods else "regex_title_abstract"
    entities = match_entities(text, spec)
    record = {
        "record_id": spec.record_id(number),
        "schema_version": spec.version,
        "publication": _publication(article, spec),
        "technique": technique_block(article, spec),
        "results": extract_results(text, spec, method=source,
                                   confidence="medium" if methods else "low"),
        "data_availability": data_availability(fulltext),
        "provenance": [{
            "field": "publication",
            "method": "regex_title_abstract",
            "section": "title+abstract",
            "confidence": "high",
        }],
    }
    if methods:
        record["provenance"].append({
            "field": "biological_system,technique,results",
            "method": "regex_fulltext_methods",
            "section": "methods",
            "confidence": "medium",
        })
    if spec.slug == "fret":
        fluorophores = detect_fluorophores(text)
        if not fluorophores or not entities:
            return None
        mapped = []
        for entity in entities:
            mapped_type = "protein" if entity["type"] in ("complex", "protein") else entity["type"]
            if mapped_type not in ("DNA", "RNA", "protein"):
                continue
            row = {"name": entity["name"], "type": mapped_type}
            if entity.get("identifiers"):
                row["identifiers"] = entity["identifiers"]
            mapped.append(row)
        if not mapped:
            return None
        types = {row["type"] for row in mapped}
        if len(types) == 1:
            molecule_types = [next(iter(types))]
        elif types == {"DNA", "protein"}:
            molecule_types = ["DNA-protein"]
        elif types == {"RNA", "protein"}:
            molecule_types = ["RNA-protein"]
        elif types == {"DNA", "RNA"}:
            molecule_types = ["DNA-RNA"]
        else:
            molecule_types = ["other"]
        record["biological_system"] = {"molecule_types": molecule_types, "entities": mapped}
        record["fret_assays"] = [{
            "assay_id": "auto-1",
            "fluorophores": fluorophores,
            "analysis": {"software": extract_software(text)} if extract_software(text) else {},
        }]
        record["data_flags"] = {"has_raw_traces": False, "has_raw_photon_data": False, "has_raw_movies": False}
        record["fair_completeness"] = _fair(record)
        return record
    if spec.slug == "spt":
        if not entities:
            return None
        record["biological_system"] = {"entities": [{"name": e["name"], "type": _spt_type(e["type"]),
                                                     **({"identifiers": e["identifiers"]} if e.get("identifiers") else {})}
                                                    for e in entities]}
        record["sample"] = {"context": "in_vitro_surface"}
        record["fair_completeness"] = _fair(record)
        return record
    if spec.slug == "mp":
        if not entities:
            return None
        record["biological_system"] = {"entities": [{"name": e["name"], "type": _mp_type(e["type"]),
                                                     **({"identifiers": e["identifiers"]} if e.get("identifiers") else {})}
                                                    for e in entities]}
        record["assay"] = {}
        record["fair_completeness"] = _fair(record)
        return record
    if spec.slug == "channel":
        if not entities:
            return None
        record["biological_system"] = {"entities": [{"name": e["name"], "type": _sc_type(e["type"]),
                                                     **({"identifiers": e["identifiers"]} if e.get("identifiers") else {})}
                                                    for e in entities]}
        record["fair_completeness"] = _fair(record)
        return record
    return None


def _spt_type(t):
    return {"ion_channel": "protein", "receptor": "receptor"}.get(t, t if t in
            ("protein", "DNA", "RNA", "complex", "vesicle", "virus", "receptor") else "other")


def _mp_type(t):
    return {"ion_channel": "protein", "receptor": "protein", "complex": "protein_complex",
            "pore_forming_toxin": "protein"}.get(t, t if t in
            ("protein", "protein_complex", "DNA", "RNA", "virus", "AAV", "membrane_protein") else "other")


def _sc_type(t):
    return {"protein": "ion_channel", "complex": "ion_channel"}.get(t, t if t in
            ("ion_channel", "transporter", "pore_forming_toxin", "receptor") else "other")


def build_records(articles, spec, start=1, software_pool=None, fulltext_index=None):
    """Build records with deterministic, per-module IDs. Skips ungrounded articles.

    `fulltext_index` maps ``epmc_id -> pmcid`` (see :mod:`modules.fulltext`); when
    given, each article's Methods text grounds the record.
    """
    records, skipped = [], 0
    number = start
    for article in articles:
        fulltext = parsed_for(article.get("epmc_id"), fulltext_index)
        record = build_record(article, spec, number, fulltext=fulltext)
        if record is None:
            skipped += 1
            continue
        records.append(record)
        number += 1
    return records, skipped


def stamp(now=None):
    return (now or datetime.date.today()).isoformat()