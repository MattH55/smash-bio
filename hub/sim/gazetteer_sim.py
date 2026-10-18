"""Entity grounding for the Simulations category.

Two sources, category-local entries first:

1. the systems the pulling-simulation literature names most often (titin I27,
   SOD1, ubiquitin, barnase, GB1, the classic nucleic-acid pulling targets),
   which need simulation-specific naming;
2. the project's shared force-spectroscopy gazetteer (``hub/gazetteer.py``),
   imported read-only, with its entity types passed through into the SMFS
   ``MolecularEntity`` vocabulary.

Identifiers come from :mod:`sim.identifiers`; only codes a resolver confirmed
are ever written into a record (see ``build_records``).
"""
import re
from functools import lru_cache

from modules.gazetteer_ext import GENERIC_SHARED
from sim import identifiers


#: entity types the published SMFS MolecularEntity enum accepts
ENTITY_TYPES = {
    "protein", "protein_complex", "peptide", "dna", "rna", "nucleoprotein",
    "cytoskeletal_filament", "membrane", "cell", "virus", "small_molecule",
    "polysaccharide", "synthetic",
}


def _term(name, entity_type, patterns, uniprot=None, rfam=None, go=None, chebi=None):
    ids = []
    for scheme, value in (("uniprot", uniprot), ("rfam", rfam), ("go", go), ("chebi", chebi)):
        if value:
            ids.append(identifiers.identifier(scheme, value))
    return {"name": name, "entity_type": entity_type, "patterns": patterns, "identifiers": ids}


SIM_SYSTEMS = [
    # proteins
    _term("Titin I27 domain", "protein",
          [r"\bi27\b|ig27 domain|titin (?:domain )?i27"], uniprot="Q8WZ42"),
    _term("Titin (Ig/FnIII domains)", "protein", [r"\btitin\b|connectin"], uniprot="Q8WZ42"),
    _term("Ubiquitin", "protein", [r"\bubiquitin\b|polyubiquitin"], uniprot="P0CG48"),
    _term("Cu/Zn superoxide dismutase (SOD1)", "protein",
          [r"\bsod1\b|superoxide dismutase[- ]?1"], uniprot="P00441"),
    _term("Barnase", "protein", [r"\bbarnase\b"], uniprot="P00648"),
    _term("T4 lysozyme", "protein", [r"\bt4 lysozyme\b"], uniprot="P00720"),
    _term("Protein G B1 domain (GB1)", "protein",
          [r"\bgb1\b|protein g b1|b1 domain of protein g"], uniprot="P06654"),
    _term("Spectrin repeat", "protein", [r"spectrin (?:repeat|domain)"], uniprot="P02549"),
    _term("Green fluorescent protein (GFP)", "protein",
          [r"\bgfp\b|green fluorescent protein"], uniprot="P42212"),
    _term("Calmodulin", "protein", [r"\bcalmodulin\b"], uniprot="P0DP23"),
    _term("Soybean trypsin inhibitor / I27-like domain", "protein",
          [r"soybean trypsin inhibitor|kunitz domain"]),
    # nucleic acids
    _term("DNA hairpin", "dna", [r"\bdna hairpins?\b|hairpin dna"]),
    _term("G-quadruplex / i-motif", "dna", [r"g[- ]quadruplex(?:es)?|\bi[- ]motif\b"]),
    _term("Double-stranded DNA (overstretching)", "dna",
          [r"\bdsdna\b|double[- ]stranded dna|overstretch\w*"]),
    _term("λ-phage DNA", "dna", [r"λ[- ]?(?:phage )?dna|lambda[- ]dna"]),
    _term("RNA hairpin", "rna", [r"\brna hairpins?\b|hairpin rna|rna stem[- ]loop"]),
    _term("RNA pseudoknot", "rna", [r"\bpseudoknots?\b"]),
    _term("Riboswitch", "rna", [r"\briboswitch(?:es)?\b"]),
    _term("tRNA", "rna", [r"\btrna\b"], rfam="RF00005"),
    # complexes
    _term("Nucleosome", "nucleoprotein", [r"\bnucleosomes?\b|chromatin fib\w+"]),
]


@lru_cache(maxsize=1)
def _shared_index():
    """The shared gazetteer as (compiled regex, entry) pairs."""
    from gazetteer import G
    return [(re.compile(entry["pattern"], re.I), entry) for entry in G]


def _shared_identifiers(lookup):
    rows = []
    for scheme in ("uniprot", "rfam", "chebi", "go", "cl", "genbank"):
        value = lookup.get(scheme)
        if value:
            rows.append(identifiers.identifier(scheme, value))
    if "uniprot" not in lookup and "gene" in lookup:
        accession = identifiers.shared.gene_accession(lookup["gene"], lookup.get("taxon"))
        if accession:
            rows.append(identifiers.identifier("uniprot", accession))
    return rows


def _base(name):
    return name.split(" (")[0]


def _sibling_of(name, existing):
    """True when `name` is a more/less specific version of an entity already found.

    "Titin" and "Titin I27 domain" are the same system at two granularities, so
    the first (most specific, because category-local terms are matched in order)
    wins. "DNA hairpin" and "Double-stranded DNA" are not siblings.
    """
    base = _base(name).strip().lower()
    for other in existing:
        other_base = _base(other["name"]).strip().lower()
        if base.startswith(other_base) or other_base.startswith(base):
            return True
    return False


def _add(entities, seen, name, entity_type, ids, text, match):
    if name in seen or entity_type not in ENTITY_TYPES or _sibling_of(name, entities):
        return
    seen.add(name)
    entity = {"name": name, "entity_type": entity_type}
    if ids:
        entity["identifiers"] = [dict(i) for i in ids]
    entity["evidence"] = {
        "field": f"system.entities[{len(entities)}]",
        "method": "gazetteer",
        "snippet": text[max(0, match.start() - 30):match.end() + 30][:400],
        "confidence": "medium",
    }
    entities.append(entity)


def match_entities(text, spec=None):
    """Entities grounded in `text`, category-local entries first."""
    text = text or ""
    entities, seen = [], set()
    for term in SIM_SYSTEMS:
        match = None
        for pattern in term["patterns"]:
            match = re.search(pattern, text, re.I)
            if match:
                break
        if match is None:
            continue
        if len(entities) >= 6:
            break
        _add(entities, seen, term["name"], term["entity_type"], term["identifiers"], text, match)
    for regex, entry in _shared_index():
        if len(entities) >= 6:
            break
        match = regex.search(text)
        if not match:
            continue
        if entry["name"] in GENERIC_SHARED and any(
                _base(entry["name"]).split()[-1] in e["name"] for e in entities):
            continue
        _add(entities, seen, entry["name"], entry["entity_type"],
             _shared_identifiers(entry["lookup"]), text, match)
    return entities