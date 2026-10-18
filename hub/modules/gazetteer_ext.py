"""Entity grounding for the technique modules.

Two sources are combined, module-local entries first:

1. **Module-local systems** (below).  These are the systems the agent briefs
   name explicitly plus the frequent ones a module needs and the shared
   vocabulary lacks.  They live here rather than in ``gazetteer.py`` so the
   module branch cannot affect the SMFS pipeline.
2. **The shared gazetteer** (``hub/gazetteer.py``) -- the project's curated
   force-spectroscopy vocabulary (~230 systems with gene/Rfam/ChEBI/GO/
   Cell-Ontology lookups that the SMFS pipeline resolves at build time).  The
   briefs ask the modules to *use* it, so it is imported read-only and its
   entity types are mapped into each module's schema vocabulary by
   :data:`SHARED_TYPES`.  Types with no sensible slot for a module are dropped
   rather than mis-typed.

The channel module deliberately does **not** consume the shared vocabulary: the
shared list is force-spectroscopy-centric (motors, cytoskeleton, adhesion) and
carries no ion-channel targets, so merging it would only attach generic
"protein" entities to single-channel records.

Identifiers are attached through :mod:`modules.identifiers`, which only reports
``verified: true`` for codes a resolver actually confirmed; an unconfirmed code
keeps its place in the record but is flagged, so nothing is silently invented.
"""
import re
from functools import lru_cache

from modules import identifiers


def _term(name, type_, patterns, uniprot=None, rfam=None, go=None):
    """A module-local system.  Identifiers are resolver-checked, never assumed."""
    ids = []
    for scheme, value in (("uniprot", uniprot), ("rfam", rfam), ("go", go)):
        if value:
            ids.append(identifiers.identifier(scheme, value))
    return {"name": name, "type": type_, "patterns": patterns, "identifiers": ids}


# ---------------------------------------------------------------- smFRET systems
# The brief names: DNA Holliday junctions, Rev/RRE, the riboswitch families, the
# ribosome and its translation factors, SNAREs, LacY, LeuT, GltPh, BetP, Hsp90,
# Hsp70, PBP/SBP domains, and IDPs (alpha-synuclein, tau, ProTalpha, H1,
# NLS/importin, p53 TAD).
FRET_SYSTEMS = [
    _term("DNA Holliday junction", "DNA", [r"holliday junction"]),
    _term("Nucleosome", "complex", [r"\bnucleosomes?\b"], go="GO:0000786"),
    _term("RRE RNA", "RNA", [r"\brre\b|rev response element"], rfam="RF00036"),
    _term("TAR RNA", "RNA", [r"\btar rna\b|trans[- ]activation response element"], rfam="RF00250"),
    _term("Rev peptide", "protein", [r"\brev peptide\b|\brev protein\b"], uniprot="P04618"),
    _term("SAM riboswitch", "RNA", [r"sam riboswitch|s-adenosylmethionine riboswitch"], rfam="RF00162"),
    _term("TPP riboswitch", "RNA", [r"tpp riboswitch|thiamine pyrophosphate riboswitch"], rfam="RF00059"),
    _term("FMN riboswitch", "RNA", [r"fmn riboswitch|flavin mononucleotide riboswitch"], rfam="RF00050"),
    _term("Purine riboswitch", "RNA", [r"purine riboswitch|adenine riboswitch"], rfam="RF00167"),
    _term("SNARE complex", "complex", [r"\bsnare"]),
    _term("LacY", "protein", [r"\blacy\b"], uniprot="P02920"),
    _term("LeuT", "protein", [r"\bleut\b|leucine transporter"], uniprot="O67854"),
    _term("GltPh", "protein", [r"\bgltph\b|glutamate transporter homologue"], uniprot="O59010"),
    _term("BetP", "protein", [r"\bbetp\b|glycine betaine transporter"], uniprot="P54582"),
    _term("Maltose-binding protein (MBP/SBP domain)", "protein",
          [r"maltose[- ]binding protein|\bmbp\b|substrate[- ]binding protein domain"], uniprot="P0AEX9"),
    _term("Elongation factor G (EF-G)", "protein", [r"\bef[- ]?g\b|elongation factor g"], uniprot="P0A6M8"),
    _term("Elongation factor Tu (EF-Tu)", "protein", [r"\bef[- ]?tu\b|elongation factor tu"], uniprot="P0CE47"),
    _term("Linker histone H1.2", "protein", [r"\bh1\.2\b|linker histone"], uniprot="P16403"),
    _term("Importin alpha (NLS receptor)", "protein",
          [r"importin[- ]?(alpha|α)|karyopherin[- ]?alpha|nuclear localization signal|\bnls\b"], uniprot="P52292"),
    _term("Prothymosin alpha", "protein", [r"prothymosin|protα|pro[- ]?tα"], uniprot="P06454"),
    _term("p53", "protein", [r"\bp53\b"], uniprot="P04637"),
    _term("p53 transactivation domain (TAD)", "protein",
          [r"p53 (transactivation|n[- ]terminal) domain|\bp53 tad\b|\btad\b.{0,20}p53"], uniprot="P04637"),
    _term("alpha-synuclein", "protein", [r"alpha[- ]synuclein|α-synuclein"], uniprot="P37840"),
    _term("tau", "protein", [r"\btau protein\b|\btau\b"], uniprot="P10636"),
    _term("Hsp90", "protein", [r"\bhsp90\b"], uniprot="P07900"),
    _term("Hsp70", "protein", [r"\bhsp70\b"], uniprot="P0DMV8"),
]


# ---------------------------------------------------------------- tracking systems
SPT_SYSTEMS = [
    _term("Kinesin-1", "protein", [r"kinesin[- ]1|kif5b"], uniprot="P33176"),
    _term("Myosin Va", "protein", [r"myosin ?v\b|myo5a"], uniprot="Q9Y4I1"),
    _term("Integrin beta-1", "protein", [r"integrin ?β1|integrin beta[- ]?1"], uniprot="P05556"),
    _term("DNA mismatch-repair protein MutS", "protein", [r"\bmuts\b"], uniprot="P23909"),
    _term("Nuclear pore complex", "complex", [r"nuclear pore complex|\bnpc\b"], go="GO:0005643"),
    _term("Chromatin locus (TetO/LacO array)", "DNA",
          [r"chromatin locus|tet operator|\bteto\b|\blaco\b|lac operator"]),
    _term("GPI-anchored protein", "protein", [r"\bgpi[- ]anchored\b|gpi anchor"]),
    _term("VSV-G glycoprotein", "protein", [r"\bvsv[- ]g\b|vesicular stomatitis"], uniprot="P03522"),
]


# ---------------------------------------------------------------- mass photometry
MP_SYSTEMS = [
    _term("Streptavidin", "protein", [r"streptavidin"], uniprot="P22629"),
    _term("Ferritin heavy chain", "protein", [r"ferritin heavy chain|\bfth1\b"], uniprot="P02794"),
    _term("Ferritin light chain", "protein", [r"ferritin light chain|\bftl\b"], uniprot="P02792"),
    _term("Ferritin", "protein", [r"\bferritin\b"]),
    _term("Hsp90", "protein", [r"\bhsp90\b"], uniprot="P07900"),
    # calibration standards named in the brief
    _term("Bovine serum albumin (BSA)", "protein", [r"bovine serum albumin|\bbsa\b"], uniprot="P02769"),
    _term("Beta-amylase", "protein", [r"β-amylase|beta-amylase"], uniprot="P10537"),
    _term("Thyroglobulin", "protein", [r"thyroglobulin"], uniprot="P01267"),
    _term("AAV2 capsid (VP1/VP2/VP3)", "AAV",
          [r"\baav\b|capsid protein vp[123]|adeno[- ]associated virus"], uniprot="P03135"),
]


# ---------------------------------------------------------------- single channel
# GtoPdb target ids are *not* attached: the Guide to Pharmacology service
# (guidetopharmacology.org/services/targets) did not answer during this build, so
# no target id could be verified.  See REPORT-modules.md.
CHANNEL_SYSTEMS = [
    _term("Kv1.2", "ion_channel", [r"\bkv ?1\.2\b|kcna2"], uniprot="P16389"),
    _term("KcsA", "ion_channel", [r"\bkcs?a\b|ph[- ]gated potassium channel"], uniprot="P0A334"),
    _term("MscL", "ion_channel", [r"\bmscl\b|large[- ]conductance mechanosensitive"], uniprot="P0A742"),
    _term("MscS", "ion_channel", [r"\bmscs\b|small[- ]conductance mechanosensitive"], uniprot="P0C0S1"),
    _term("BK channel", "ion_channel", [r"\bbk\b.{0,20}channel|kcnma1|slo1|maxi[- ]k"], uniprot="Q12791"),
    _term("hERG (Kv11.1)", "ion_channel", [r"\bherg\b|kcnh2"], uniprot="Q12809"),
    _term("NaV1.5", "ion_channel", [r"\bnav ?1\.5\b|scn5a"], uniprot="Q14524"),
    _term("TRPV1", "ion_channel", [r"\btrpv1\b"], uniprot="Q8NER1"),
    _term("TRAAK (K2P4.1)", "ion_channel", [r"\btraak\b|kcnk4"], uniprot="Q9NYG8"),
    _term("CFTR", "transporter", [r"\bcftr\b"], uniprot="P13569"),
    _term("Aquaporin-1", "transporter", [r"aquaporin[- ]?1|\baqp1\b"], uniprot="P29972"),
    _term("Connexin-43", "ion_channel", [r"connexin[- ]?43|\bcx43\b|gja1"], uniprot="P17302"),
    _term("Pannexin-1", "ion_channel", [r"pannexin[- ]?1|\bpanx1\b"], uniprot="Q96RD7"),
    _term("OmpF", "transporter", [r"\bompf\b"], uniprot="P02931"),
    _term("VDAC1", "ion_channel", [r"\bvdac ?1?\b|voltage[- ]dependent anion channel"], uniprot="P21796"),
    _term("AcrB multidrug efflux pump", "transporter", [r"\bacrb\b|multidrug efflux"], uniprot="P31224"),
    _term("GABA-A receptor alpha1", "receptor", [r"gaba[- ]?a.{0,20}alpha1|gabra1"], uniprot="P14867"),
    _term("NMDA receptor (GluN1)", "receptor", [r"\bnmda\b|glun ?1|grin1"], uniprot="Q05586"),
    _term("AMPA receptor (GluA2)", "receptor", [r"\bampa\b|glua ?2|gria2"], uniprot="P42262"),
    _term("alpha-hemolysin", "pore_forming_toxin", [r"alpha[- ]?hemolysin|α-hemolysin"], uniprot="P09616"),
]


BY_MODULE = {
    "fret": FRET_SYSTEMS,
    "spt": SPT_SYSTEMS,
    "mp": MP_SYSTEMS,
    "channel": CHANNEL_SYSTEMS,
}


# shared-gazetteer entity_type -> module schema vocabulary (missing key => drop)
SHARED_TYPES = {
    "fret": {"dna": "DNA", "rna": "RNA", "protein": "protein",
             "protein_complex": "complex", "nucleoprotein": "complex"},
    "spt": {"dna": "DNA", "rna": "RNA", "protein": "protein",
            "protein_complex": "complex", "nucleoprotein": "complex",
            "cytoskeletal_filament": "protein", "membrane": "vesicle",
            "virus": "virus", "cell": "other"},
    "mp": {"dna": "DNA", "rna": "RNA", "protein": "protein",
           "protein_complex": "protein_complex", "nucleoprotein": "protein_complex",
           "cytoskeletal_filament": "protein", "membrane": "membrane_protein",
           "virus": "virus"},
}

# shared entries that should yield to a more specific sibling (as in s06)
GENERIC_SHARED = {
    "Kinesin", "Myosin", "Helicase", "Cadherin (classical)", "Ribosome",
    "double-stranded DNA", "single-stranded DNA", "Transcription factor",
    "Virus / capsid", "Antibody–antigen", "Lipid vesicle / bilayer",
    "Immunoglobulin-like domain", "Chromatin remodeler", "Polymer",
}


@lru_cache(maxsize=1)
def _shared():
    """The shared gazetteer as (compiled regex, entry) pairs."""
    from gazetteer import G
    return [(re.compile(entry["pattern"], re.I), entry) for entry in G]


def _shared_identifiers(lookup):
    """Identifiers for a shared entry, verified through the resolver table."""
    rows = []
    for scheme in ("uniprot", "rfam", "chebi", "go", "cl", "genbank"):
        value = lookup.get(scheme)
        if value:
            rows.append(identifiers.identifier(scheme, value))
    if "uniprot" not in lookup and "gene" in lookup:
        acc = identifiers.gene_accession(lookup["gene"], lookup.get("taxon"))
        if acc:
            rows.append(identifiers.identifier("uniprot", acc))
    return rows


def _first_hit(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match
    return None


def _add(entities, seen, name, type_, ids, text, match):
    if name in seen:
        return
    seen.add(name)
    entity = {"name": name, "type": type_}
    if ids:
        entity["identifiers"] = [dict(i) for i in ids]
    entity["evidence"] = {
        "field": f"biological_system.entities[{len(entities)}]",
        "method": "gazetteer",
        "snippet": text[max(0, match.start() - 30):match.end() + 30][:400],
        "confidence": "medium",
    }
    entities.append(entity)


def _base(name):
    return name.split(" (")[0]


def match_entities(text, spec):
    """Return the molecular entities grounded in `text` for one module.

    Module-local systems are matched first so their curated types and verified
    identifiers win over the broader shared entries of the same name.
    """
    text = text or ""
    entities, seen = [], set()

    for term in BY_MODULE.get(spec.slug, []):
        match = _first_hit(term["patterns"], text)
        if match is None:
            continue
        _add(entities, seen, term["name"], term["type"], term["identifiers"], text, match)

    type_map = SHARED_TYPES.get(spec.slug)
    if type_map:
        for rx, entry in _shared():
            mapped = type_map.get(entry["entity_type"])
            if not mapped or entry["name"] in seen:
                continue
            match = rx.search(text)
            if not match:
                continue
            base = _base(entry["name"])
            if entry["name"] in GENERIC_SHARED and any(
                    e["name"].startswith(base) or base.split()[-1] in e["name"] for e in entities):
                continue
            _add(entities, seen, entry["name"], mapped,
                 _shared_identifiers(entry["lookup"]), text, match)
    return entities