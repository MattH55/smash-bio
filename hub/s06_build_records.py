"""Step 6 - assemble schema-conformant SMASH-BIO records (schema v3.1.0).

Inputs : out/articles_classified.jsonl, out/links.json, out/datasets_raw.jsonl,
         full-text cache (s05), legacy curated YAML (publications_metadata/)
Output : out/records.jsonl, out/datasets_hub.jsonl, out/uniprot_cache.json
"""
import datetime
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

import extract as X
from common import HTTP_CACHE, OUT, get, load_json, load_jsonl, norm_doi, pmap, save_json, save_jsonl
from gazetteer import G, ORGANISMS
from harvester_cleanup import COUNTED_RELEVANCE, VERSION as CLEANUP_VERSION, annotate_record_links, collapse_families
from s05_fulltext import FT_CACHE

ROOT = Path(__file__).resolve().parent.parent
HUB_DIR = Path(__file__).resolve().parent
TODAY = datetime.date.today().isoformat()

def _split_top(p):
    """Split a regex on top-level '|' (outside groups/classes)."""
    out, depth, cls, cur, i = [], 0, False, "", 0
    while i < len(p):
        ch = p[i]
        if ch == "\\":
            cur += p[i:i + 2]; i += 2; continue
        if cls:
            cls = ch != "]"
        elif ch == "[":
            cls = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "|" and depth == 0:
            out.append(cur); cur = ""; i += 1; continue
        cur += ch; i += 1
    return out + [cur]


def gaz_compile(p):
    """Acronym alternatives (e.g. CDH23, RPA) stay case-sensitive; word alternatives (cadherin-23) are case-insensitive."""
    def sensitive(a):
        letters = re.sub(r"\\[bBdDsSwW]|[^A-Za-z]", "", a)
        return bool(re.search(r"[A-Z]{2,}", a)) or (any(c.isupper() for c in letters) and len(letters) <= 6)
    alts = [a if sensitive(a) else f"(?i:{a})" for a in _split_top(p)]
    return re.compile("|".join(alts))


GAZ = [(gaz_compile(g["pattern"]), g) for g in G]
ORG_RX = [(re.compile(p, re.I), n, t) for p, n, t in ORGANISMS]
TAXON_FIX = {562: 83333, 4932: 559292}  # map species to reference strain used by UniProt reviewed entries
TECH_PRIORITY = ["optical_tweezers", "magnetic_tweezers", "torque_tweezers", "acoustic_force_spectroscopy", "centrifuge_force",
                 "nanopore_force", "hydrodynamic_stretching", "biomembrane_force_probe", "micropipette", "tension_sensors",
                 "microneedle", "afm_smfs", "force_spectroscopy_unspecified"]
DATA_TYPES = {"dataset", "software", "collection", "other", "workflow", "model", "image", "audiovisual", "computationalnotebook", None}
REPO_NAMES = [("zenodo", "Zenodo"), ("figshare", "Figshare"), ("dryad", "Dryad"), ("17632", "Mendeley Data"), ("mendeley", "Mendeley Data"),
              ("osf", "OSF"), ("4121", "4TU.ResearchData"), ("4tu", "4TU.ResearchData"), ("7910/dvn", "Harvard Dataverse"),
              ("dataverse", "Dataverse"), ("darus", "DaRUS (Stuttgart)"), ("github", "GitHub"), ("gitlab", "GitLab"),
              ("biostudies", "BioStudies"), ("empiar", "EMPIAR"), ("ethz", "ETH Research Collection"), ("34973", "Radboud Data Repository"),
              ("pangaea", "PANGAEA"), ("codeocean", "Code Ocean"), ("bitbucket", "Bitbucket"), ("huggingface", "Hugging Face"),
              ("5522/04", "UCL Research Data"), ("15131/shef", "ORDA (Sheffield)"), ("48420", "Manchester Figshare"),
              ("25405", "Leeds"), ("sbgrid", "SBGrid Data Bank")]


def repo_name(s, publisher=None):
    s2 = (s or "").lower()
    for k, n in REPO_NAMES:
        if k in s2:
            return n
    return publisher or "other"


# ---------------------------------------------------------------- UniProt resolution
UNI = load_json(OUT / "uniprot_cache.json", {}) or {}
# drop gene lookups cached before the primary-gene-name check was added
UNI = {k: v for k, v in UNI.items() if not k.startswith("gene|") or (v and v.get("primary_gene_checked"))}


def uniprot_lookup(key):
    if key in UNI:
        return UNI[key]
    kind, a, b = key.split("|")
    if kind == "acc":
        d = get(f"https://rest.uniprot.org/uniprotkb/{a}.json", {"fields": "accession,protein_name,gene_names,organism_name,organism_id"})
        res = None
        if d and d.get("primaryAccession"):
            res = {"acc": d["primaryAccession"], "name": ((d.get("proteinDescription") or {}).get("recommendedName") or {}).get("fullName", {}).get("value"),
                   "organism": (d.get("organism") or {}).get("scientificName"), "taxon": (d.get("organism") or {}).get("taxonId")}
    else:
        # gene_exact also matches synonyms (CDH1 -> FZR1, HTT -> SLC6A4); accept only a PRIMARY gene-name match
        q = f"gene_exact:{a} AND organism_id:{b} AND reviewed:true"
        d = get("https://rest.uniprot.org/uniprotkb/search", {"query": q, "fields": "accession,protein_name,gene_names,organism_name,organism_id", "size": 10, "format": "json"})
        res = None
        for r in (d or {}).get("results") or []:
            prim = [((g.get("geneName") or {}).get("value") or "") for g in r.get("genes") or []]
            if a.upper() not in (p.upper() for p in prim):
                continue
            pd = r.get("proteinDescription") or {}
            res = {"acc": r["primaryAccession"], "name": ((pd.get("recommendedName") or {}).get("fullName") or {}).get("value"),
                   "organism": (r.get("organism") or {}).get("scientificName"), "taxon": (r.get("organism") or {}).get("taxonId"),
                   "gene": a, "primary_gene_checked": True}
            break
    UNI[key] = res
    return res


# ---------------------------------------------------------------- helpers
def q(value, unit, snippet=None, method="regex_fulltext_methods", conf="medium", **kw):
    d = {"value": value, "unit": unit, **kw}
    if snippet:
        d["evidence"] = {"method": method, "snippet": snippet[:300], "confidence": conf}
    return d


def find_all(rx_list, text):
    return [n for n, rx in rx_list if rx.search(text or "")]


TAXA = load_json(OUT / "taxonomy_cache.json", {}) or {}
KEEP_RANKS = {"species", "subspecies", "strain", "varietas", "forma", "serotype", "isolate", "genus", "no rank"}


def taxon_info(t):
    t = str(t)
    if t not in TAXA:
        d = get(f"https://www.ebi.ac.uk/ena/taxonomy/rest/tax-id/{t}")
        TAXA[t] = {"name": d.get("scientificName"), "rank": d.get("rank")} if isinstance(d, dict) and d.get("scientificName") else None
    return TAXA[t]


def organisms_for(a, ann, text):
    found = {}
    for e in ann:
        if e["type"] != "Organisms" or not e.get("uri"):
            continue
        m = re.search(r"taxonomy/(\d+)", e["uri"])
        if not m:
            continue
        secs = " ".join(e["sections"]).lower()
        w = 3 if ("abstract" in secs or "title" in secs) else (1 if "method" in secs else 0)
        if w == 0:
            continue
        t = int(m.group(1))
        info = TAXA.get(str(t))
        # accept a text-mined organism only if the mention names its genus ("Escherichia", "E. coli" ~ Escherichia coli);
        # bare common words ("bacterium", "Cana", "virus") are rejected - common names (human, mouse, yeast...)
        # are covered by the curated ORGANISMS patterns instead.
        if not (info and info.get("name")) or not info["name"][0].isupper() or re.match(r"(uncultured|unidentified|environmental|synthetic)", info["name"], re.I):
            continue
        sci = [w.lower() for w in re.findall(r"[A-Za-z]+", info["name"])]
        ment = [w.lower() for w in re.findall(r"[A-Za-z]+", e["text"])]
        if not sci or not ment:
            continue
        genus = sci[0]
        if not (ment[0] == genus or (len(ment) >= 2 and len(ment[0]) == 1 and ment[0] == genus[0] and ment[1] in sci)):
            continue
        f = found.setdefault(t, {"name": e["text"], "ncbi_taxon": t, "score": 0, "src": "europepmc_textmining"})
        f["score"] += w * e["n"]
    for rx, name, t in ORG_RX:
        m = rx.search(text)
        if m:
            f = found.setdefault(t, {"name": name, "ncbi_taxon": t, "score": 0, "src": "gazetteer"})
            f["score"] += 4
            f["name"] = name
    # drop generic / noisy taxa
    for bad in (9606,) if not re.search(r"\bhuman|homo sapiens|patient|HeLa|HEK|U2OS|Jurkat|recombinant human", text, re.I) else ():
        if bad in found and found[bad]["score"] < 4:
            found.pop(bad)
    for generic in (2, 2759, 10239, 629395, 1, 131567, 33208, 40674):  # bacteria, eukaryota, viruses ...
        found.pop(generic, None)
    for t in list(found):
        info = TAXA.get(str(t))  # prefetched in main(); unknown taxa keep their text form
        if info:
            if info["rank"] not in KEEP_RANKS or (info["rank"] == "no rank" and found[t]["src"] != "gazetteer"):
                found.pop(t)
                continue
            found[t]["name"] = info["name"]
    # drop a bare genus (e.g. "Homo", "Mus sp.") when a species of that genus is present
    species_genera = {f["name"].split()[0] for f in found.values() if len(f["name"].split()) >= 2 and not f["name"].endswith(" sp.")}
    for t in list(found):
        nm = found[t]["name"]
        if (len(nm.split()) == 1 or nm.endswith(" sp.")) and nm.split()[0] in species_genera:
            found.pop(t)
    # merge strain-level duplicates of the same species name
    seen = {}
    for t, f in sorted(found.items(), key=lambda x: -x[1]["score"]):
        key = " ".join(f["name"].split()[:2])
        if key in seen:
            seen[key]["score"] += f["score"]
        else:
            seen[key] = f
    out = sorted(seen.values(), key=lambda x: -x["score"])[:4]
    return [{"name": o["name"], "ncbi_taxon": o["ncbi_taxon"], "evidence": {"method": o["src"], "confidence": "high" if o["score"] >= 4 else "medium"}} for o in out if o["score"] >= 2]


def entities_for(title_abs, methods_text, orgs):
    ents, seen = [], set()
    org_taxa = [o["ncbi_taxon"] for o in orgs]
    for rx, g in GAZ:
        m = rx.search(title_abs)
        if not m:
            continue
        if g["name"] in seen:
            continue
        # skip generic entries when a specific sibling already matched (e.g. Kinesin vs Kinesin-1)
        base = g["name"].split(" (")[0]
        if any(e["name"].startswith(base) or base.split()[-1] in e["name"] for _, e in ents if e["entity_type"] == g["entity_type"]) and g["name"] in ("Kinesin", "Myosin", "Helicase", "Cadherin (classical)", "DNA polymerase / replisome", "RNA polymerase (bacterial)", "double-stranded DNA", "single-stranded DNA"):
            continue
        seen.add(g["name"])
        e = {"name": g["name"], "entity_type": g["entity_type"], "role": "unspecified", "identifiers": [],
             "evidence": {"method": "gazetteer", "snippet": X.snip(title_abs, m, 60), "confidence": "medium"}}
        lk = g["lookup"]
        if "gene" in lk:
            hit, used = None, None
            for t in [TAXON_FIX.get(t, t) for t in org_taxa[:2]] + [lk["taxon"]]:
                hit = uniprot_lookup(f"gene|{lk['gene']}|{t}")
                if hit:
                    used = t
                    break
            if hit:
                e["identifiers"].append({"scheme": "uniprot", "id": hit["acc"], "verified": True})
                e["gene_symbol"] = lk["gene"]
                e["organism"] = {"name": hit["organism"], "ncbi_taxon": hit["taxon"]}
                if used == lk["taxon"] and lk["taxon"] not in [TAXON_FIX.get(t, t) for t in org_taxa]:
                    e["evidence"]["note"] = "organism not stated in abstract; default ortholog assigned"
                    e["evidence"]["confidence"] = "low"
        elif "uniprot" in lk:
            hit = uniprot_lookup(f"acc|{lk['uniprot']}|")
            e["identifiers"].append({"scheme": "uniprot", "id": lk["uniprot"], "verified": bool(hit)})
            if hit:
                e["organism"] = {"name": hit["organism"], "ncbi_taxon": hit["taxon"]}
        for scheme in ("genbank", "rfam", "chebi", "cl", "go"):
            if scheme in lk:
                e["identifiers"].append({"scheme": scheme, "id": lk[scheme], "verified": False})
        if "ncbitaxon" in lk:
            e["organism"] = {"ncbi_taxon": lk["ncbitaxon"]}
        ents.append((g["system_class"], e))
    return ents


def experiment_classes(text, ents, tech):
    t = text.lower()
    cls = set()
    types = Counter(e["entity_type"] for _, e in ents)
    hinted = Counter(c for c, _ in ents)
    if re.search(r"unfold|refold|folding|mechanical stability|mechanostab|misfold|unzip|hairpin|pseudoknot|riboswitch|g-quadruplex|energy landscape", t):
        if types["dna"] + types["rna"] > 0 and re.search(r"unzip|hairpin|pseudoknot|riboswitch|quadruplex|rna fold|rna (structure|tertiary)|i-motif", t):
            cls.add("unfolding_nucleic_acid")
        if types["protein"] + types["protein_complex"] > 0 or re.search(r"protein (un)?fold|polyprotein|domain unfold", t):
            if re.search(r"protein|domain|polyprotein|polypeptide|chaperone", t):
                cls.add("unfolding_protein")
    if re.search(r"(dna|rna|chromatin|nucleosome)[- ](binding|protein|interaction|bound)|bind(s|ing)? (to )?(ds|ss)?(dna|rna)|protein[- ](dna|rna)|nucleoprotein|filament formation|recombinase|repair|condensation|compaction|loop extrusion|bridging", t) \
            or hinted["nucleic_acid_protein"] >= 1 and types["dna"] + types["rna"] + types["nucleoprotein"] > 0:
        cls.add("nucleic_acid_protein_interaction")
    if re.search(r"nucleosome|chromatin|histone|chromosome", t):
        cls.add("chromatin_mechanics")
    if re.search(r"transcription|replication|translation|ribosom|polymerase|replisome|helicase|translocase", t):
        cls.add("translation_transcription_replication")
    if re.search(r"motor|kinesin|myosin|dynein|stall force|stepping|step size|processiv|power stroke|packaging|force generation|force-generating|translocat", t):
        cls.add("force_generation_motor")
    if re.search(r"polymeriz|depolymeriz|filament (growth|elongation)|microtubule (growth|dynamics|plus[- ]end)|actin (polymer|network)|treadmill", t):
        cls.add("force_generation_polymerization")
    if re.search(r"elasticity|persistence length|overstretch|supercoil|plectonem|twist|torsion|stretch modulus|force[- ]extension (behavior|curve|of (ds|ss)?dna)|b-dna|s-dna|dna mechanics|melting", t) \
            and types["dna"] + types["rna"] > 0:
        cls.add("nucleic_acid_mechanics")
    if re.search(r"catch[- ]bond|slip[- ]bond|receptor|ligand|adhesi|antibod|antigen|integrin|selectin|cadherin|bond lifetime|unbinding|rupture|binding strength|biotin|lectin|glycan", t):
        cls.add("receptor_ligand_adhesion")
    if re.search(r"membrane (tether|tube|tension|nanotube|mechanics|bending)|lipid bilayer|vesicle|bending rigidity|fusion pore", t):
        cls.add("membrane_mechanics")
    if re.search(r"rheolog|viscoelast|cell (mechanics|stiffness|deformab|elasticity)|cytoplasm|cortical|deformability|red blood|erythrocyte|elastic modulus|young'?s modulus|nucle(us|ar) mechanics|stiffness of (the )?cells?", t) \
            or types["cell"] > 0 and re.search(r"stiff|elastic|viscos|deform|mechanic", t):
        cls.add("rheology_cell")
    if re.search(r"hydrogel|biomaterial|silk|extracellular matrix|fibrin network|collagen fib|mucus", t) and re.search(r"rheolog|viscoelast|modulus", t):
        cls.add("rheology_material")
    if not cls:
        for c in hinted:
            cls.add({"unfolding": "unfolding_protein", "nucleic_acid_protein": "nucleic_acid_protein_interaction",
                     "force_generation": "force_generation_motor", "rheology": "rheology_cell",
                     "adhesion": "receptor_ligand_adhesion", "nucleic_acid_mechanics": "nucleic_acid_mechanics"}[c])
    return sorted(cls)


TABLE3_COLUMN = {
    "unfolding_protein": "Nucleic acid or protein unfolding", "unfolding_nucleic_acid": "Nucleic acid or protein unfolding",
    "nucleic_acid_mechanics": "Nucleic acid or protein unfolding", "nucleic_acid_protein_interaction": "DNA-protein interactions",
    "chromatin_mechanics": "DNA-protein interactions", "translation_transcription_replication": "Force generation by motors",
    "force_generation_motor": "Force generation by motors", "force_generation_polymerization": "Force generation by motors",
    "receptor_ligand_adhesion": "Receptor-ligand / adhesion (extension)", "membrane_mechanics": "Rheology",
    "rheology_cell": "Rheology", "rheology_material": "Rheology", "methods_calibration": "Methods",
}


def hardware_from(text, techs, src_method):
    hw, ev = {}, []
    if not text:
        return hw
    vend = [n for n, rx in X.VENDOR_RX if rx.search(text)]
    models = sorted({m.group(0) for m in X.MODEL_RX.finditer(text)})
    custom = bool(X.CUSTOM_RX.search(text))
    if vend:
        hw["make_of_setup"] = vend[0]
        hw["vendors_mentioned"] = vend[:4]
    elif custom:
        hw["make_of_setup"] = "custom"
    if custom:
        hw["custom_built"] = True
    if models:
        hw["model_number"] = models[0]
    det = X.find_all if False else [n for n, rx in X.DETECTION_RX if rx.search(text)]
    if det:
        hw["detection_device"] = det[:4]
    cal = [n for n, rx in X.CALIB_RX if rx.search(text)]
    if cal:
        hw["calibration_technique"] = cal
    # objective
    obj = {}
    m = X.R_NA.search(text)
    if m and 0.3 < float(m.group(1)) <= 1.7:
        obj["numerical_aperture"] = float(m.group(1))
    m = X.R_MAG.search(text)
    if m and re.search(r"objective", text[max(0, m.start() - 120): m.end() + 120], re.I):
        obj["magnification"] = int(m.group(1))
    m = X.R_IMMERSION.search(text)
    if m:
        obj["immersion"] = m.group(1).lower()
    m = X.R_OBJ_MAKE.search(text)
    if m:
        obj["make"] = m.group(1).title()
    if obj:
        hw["objective_lens"] = obj
    # temperature
    # measurement temperature: anchored on experiment/measurement context, ignoring sample-prep sentences (4 °C storage, 37 °C growth...)
    meas_anchor = re.compile(r"(experiments?|measurements?|assays?|pulling|stretching|force spectroscopy|tweezers|recordings?|data) "
                             r"(were|was) (all )?(performed|carried out|conducted|done|recorded|acquired|measured)|"
                             r"(measured|performed|recorded|conducted) at (a )?(constant |controlled )?(room )?temperature|"
                             r"temperature[- ]controlled|sample temperature|measurement temperature", re.I)
    prep = re.compile(r"overnight|dialy|incubat|stor(ed|age)|grown|growth|culture|induc|centrifug|lysis|anneal|heat|melt|ligat|digest|expression", re.I)
    temps = [(v, s) for v, s in X.window_find(text, meas_anchor, X.R_TEMP, w=90, conv=lambda m: _temp_k(m), valid=lambda v: 283 <= v <= 318)
             if not prep.search(s)]
    if not temps and re.search(r"room temperature", text, re.I):
        hw["temperature"] = q(None, "K", "room temperature", src_method, "low", note="room temperature (≈293–298 K)")
    best = X.most_common(temps)
    if best:
        hw["temperature"] = q(round(best[0], 2), "K", best[1], src_method)
    # acquisition and filter
    acq = X.window_find(text, X.R_ACQ_ANCHOR, X.R_FREQ, w=80, conv=lambda m: _hz(m), valid=lambda v: 1 <= v <= 1e7)
    best = X.most_common(acq)
    if best:
        hw["acquisition_rate"] = q(round(best[0] / 1000, 4), "kHz", best[1], src_method)
    flt = X.window_find(text, X.R_FILTER_ANCHOR, X.R_FREQ, w=60, conv=lambda m: _hz(m), valid=lambda v: 0.1 <= v <= 1e6)
    best = X.most_common(flt)
    if best:
        hw["filter_frequency"] = q(round(best[0], 3), "Hz", best[1], src_method)
    # optical
    if {"optical_tweezers", "torque_tweezers"} & set(techs):
        o = {}
        wl = X.window_find(text, X.R_LASER, X.R_WAVELENGTH, w=120, conv=lambda m: float(m.group(1)))
        best = X.most_common(wl)
        if best:
            o["laser_wavelength"] = q(best[0], "nm", best[1], src_method, "high" if best[0] in (1064, 1070, 1047) else "medium")
        pw = X.window_find(text, X.R_LASER, X.R_POWER, w=80, conv=lambda m: _num(m.group(1)) * (1000 if m.group(2) == "W" else 1), valid=lambda v: 0.5 <= v <= 20000)
        if pw:
            o["laser_power_at_source"] = q(max(v for v, _ in pw), "mW", pw[0][1], src_method, "low",
                                           note="largest laser power mentioned; source vs. objective not disambiguated")
        st = X.window_find(text, X.R_STIFF_ANCHOR, X.R_STIFF, w=110, conv=_stiff, valid=lambda v: 0.001 <= v[0] <= 5)
        if st:
            v, s = st[0]
            o["trap_stiffness"] = q(v[0], "pN/nm", s, src_method, uncertainty=v[1]) if v[1] is None else q(v[0], "pN/nm", s, src_method, uncertainty=v[1], uncertainty_type="unspecified")
        steer = [n for n, rx in X.STEER_RX if rx.search(text)]
        if steer:
            o["spatial_laser_control"] = steer
        m = re.search(r"\b(dual|two|double|single|one|three|four|quadruple|multiple)[- ](optical )?(beam |laser )?traps?\b", text, re.I)
        if m:
            o["number_of_traps"] = {"dual": 2, "two": 2, "double": 2, "single": 1, "one": 1, "three": 3, "four": 4, "quadruple": 4}.get(m.group(1).lower())
        if o:
            hw["optical"] = {k: v for k, v in o.items() if v is not None}
    if {"magnetic_tweezers", "torque_tweezers"} & set(techs):
        mg = {}
        m = X.BEAD_PRODUCT_RX.search(text)
        if m:
            mg["bead_product"] = m.group(0)
        if re.search(r"electromagnet|magnetic coils?", text, re.I):
            mg["magnet_type"] = "electromagnet"
        elif re.search(r"(pair of|two) (permanent |NdFeB |neodymium )?magnets|permanent magnets", text, re.I):
            mg["magnet_type"] = "permanent_pair"
        elif re.search(r"cylindrical|ring magnet", text, re.I):
            mg["magnet_type"] = "cylindrical_ring"
        fr = X.window_find(text, re.compile(r"camera|frame rate|fps|frames", re.I), X.R_FREQ, w=60, conv=lambda m: _hz(m), valid=lambda v: 1 <= v <= 1e5)
        if fr:
            mg["camera_frame_rate"] = q(fr[0][0], "Hz", fr[0][1], src_method)
        m = re.search(r"(\d{2,5})\s*(?:DNA )?tethers? (were )?(tracked|measured|in parallel|simultaneously)|(?:up to|hundreds of|thousands of)\s*(\d+)?\s*(beads|tethers|molecules) (in parallel|simultaneously)", text, re.I)
        if m and m.group(1):
            mg["parallel_tethers"] = int(m.group(1))
        if re.search(r"rotat\w+ (the )?magnets?|magnet rotation|twist", text, re.I):
            mg["rotation_control"] = True
        if mg:
            hw["magnetic"] = mg
    if {"afm_smfs", "force_spectroscopy_unspecified"} & set(techs) or re.search(r"cantilever", text, re.I):
        af = {}
        m = X.R_CANTILEVER.search(text)
        if m:
            af["cantilever_model"] = m.group(0)
        sk = X.window_find(text, re.compile(r"spring constant|cantilever stiffness|force constant", re.I), X.R_SPRING_AFM, w=90, conv=_spring)
        if sk:
            af["spring_constant"] = q(sk[0][0], "pN/nm", sk[0][1], src_method)
        sp = X.window_find(text, X.R_SPEED_ANCHOR, X.R_SPEED, w=60, conv=_speed, valid=lambda v: 0.1 <= v <= 1e7)
        if sp:
            af["pulling_speed"] = q(sp[0][0], "nm/s", sp[0][1], src_method)
        if re.search(r"cantilever|AFM|atomic force", text, re.I) and af:
            hw["afm"] = af
    if "nanopore_force" in techs:
        nn = {}
        m = re.search(r"\b(MspA|α-hemolysin|alpha-hemolysin|aHL|CsgG|FraC|ClyA|solid-state|SiN|graphene) (nano)?pore", text, re.I)
        if m:
            nn["pore"] = m.group(1)
        m = re.search(NUM_RX_V, text)
        if m:
            nn["bias_voltage"] = q(_num(m.group(1)), "mV", X.snip(text, m, 50), src_method)
        if nn:
            hw["nanopore"] = nn
    if "acoustic_force_spectroscopy" in techs:
        m = re.search(X.NUM + X.SP + r"MHz", text)
        if m:
            hw["acoustic"] = {"resonance_frequency": q(_num(m.group(1)), "MHz", X.snip(text, m, 50), src_method)}
    if "hydrodynamic_stretching" in techs:
        m = re.search(X.NUM + X.SP + r"(" + X.MU + r"l|µL|μL|ml|mL)" + X.SP + r"(?:/|per\s)" + X.SP + r"(min|h|s)\b", text, re.I)
        if m:
            hw["hydrodynamic"] = {"flow_rate": q(_num(m.group(1)), f"{m.group(2)}/{m.group(3)}", X.snip(text, m, 50), src_method)}
    return hw


NUM_RX_V = re.compile(r"(\d{2,3})\s*mV\b")


def _num(s):
    return float(s.replace(",", ".")) if s else None


def _temp_k(m):
    v = _num(m.group(1))
    return v + 273.15 if m.group(3) != "K" else v


def _hz(m):
    v, u = _num(m.group(1)), m.group(2)
    return v * {"MHz": 1e6, "kHz": 1e3}.get(u, 1)


def _stiff(m):
    v, unc, u = _num(m.group(1)), _num(m.group(2)), m.group(3).lower().replace(" ", "")
    f = 1.0
    if "μm" in u or "um" in u or "µm" in u:
        f = 1e-3
    elif u.startswith("fn"):
        f = 1e-3
    elif u in ("n/m", "mn/m"):
        f = 1000.0 if u == "n/m" else 1.0
    return (round(v * f, 5), round(unc * f, 5) if unc else None)


def _spring(m):
    v, u = _num(m.group(1)), m.group(3).lower()
    return round(v * (1000 if u == "n/m" else 1), 4)


def _speed(m):
    v, u = _num(m.group(1)), m.group(3)
    return v * (1000 if not u.startswith("n") else 1)


def assay_from(text, techs, src_method):
    a = {}
    if not text:
        return a
    beads = X.window_find(text, X.R_BEAD_ANCHOR, X.R_BEAD, w=50, conv=lambda m: (_num(m.group(1)) * (1000 if not m.group(3).lower().startswith("n") else 1), _num(m.group(2))),
                          valid=lambda v: 100 <= v[0] <= 20000, maxhits=10)
    m270 = X.R_MAG_BEAD_SIZE.search(text)
    if beads:
        sizes = Counter(v[0] for v, _ in beads)
        val = sizes.most_common(1)[0][0]
        snipb = next(s for v, s in beads if v[0] == val)
        a["bead_size"] = q(val, "nm", snipb, src_method, note="most frequent bead diameter mentioned" + ("; several sizes mentioned" if len(sizes) > 1 else ""))
        if len(sizes) > 1:
            a["bead_sizes_mentioned_nm"] = sorted(sizes)
    elif m270:
        size = {"M-270": 2800, "M270": 2800, "M-280": 2800, "M280": 2800, "M-450": 4500, "M450": 4500, "MYONE": 1000}.get(m270.group(1).upper().replace("-", "-"), None)
        if size:
            a["bead_size"] = q(size, "nm", X.snip(text, m270, 40), "inferred", "medium", note="nominal diameter of named bead product")
    mat = [n for n, rx in X.BEAD_MAT_RX if rx.search(text)]
    if mat:
        a["bead_material"] = mat[0]
    fun = [n for n, rx in X.FUNCT_RX if rx.search(text)]
    if fun:
        a["bead_functionalization"] = fun
    att = [n for n, rx in X.ATTACH_RX if rx.search(text)]
    if att:
        a["attachment_chemistry"] = att
    ctrl = [n for n, rx in X.CONTROL_RX if rx.search(text)]
    if ctrl:
        a["trap_control"] = ctrl
    lr = X.R_LOADING.search(text)
    if lr:
        v = _num(lr.group(1)) * (1000 if lr.group(3) == "nN" else 1)
        a["loading_rate"] = q(v, "pN/s", X.snip(text, lr, 60), src_method, **({"max": _num(lr.group(2)) * (1000 if lr.group(3) == "nN" else 1)} if lr.group(2) else {}))
    sp = X.window_find(text, X.R_SPEED_ANCHOR, X.R_SPEED, w=60, conv=_speed, valid=lambda v: 0.1 <= v <= 1e7)
    if sp:
        a["pulling_speed"] = q(sp[0][0], "nm/s", sp[0][1], src_method)
    hm = X.HANDLE_RX.search(text)
    if hm:
        L = _num(hm.group(1)) * (1000 if hm.group(2).lower().startswith("kb") else 1)
        a["handle_sequences"] = [{"length_bp": int(L), "annotations": X.snip(text, hm, 60)}]
    if re.search(r"three[- ]bead", text, re.I):
        a["bead_geometry"] = "three_bead"
    elif re.search(r"quadruple|four[- ]trap|q-?trap", text, re.I):
        a["bead_geometry"] = "four_bead"
    elif re.search(r"dumbbell|two beads|dual[- ]trap|between (two|a pair of) (beads|microspheres)", text, re.I):
        a["bead_geometry"] = "two_bead_dumbbell"
    elif re.search(r"polymeriz", text, re.I) and "optical_tweezers" in techs:
        a["bead_geometry"] = "polymerization_assay"
    elif set(techs) & {"magnetic_tweezers", "acoustic_force_spectroscopy", "centrifuge_force"}:
        a["bead_geometry"] = "bead_surface"
    m = re.search(X.NUM + X.SP + r"mbar", text)
    if m:
        a["flow_pressure"] = q(_num(m.group(1)), "mbar", X.snip(text, m, 50), src_method)
    m = re.search(r"(\d{1,5})\s*(individual |different |single )?(molecules|tethers|DNA molecules|proteins|traces|curves|pulling cycles)\b", text, re.I)
    if m and re.search(r"\bn\s*=|total of|from|analy[sz]ed|recorded|measured", text[max(0, m.start() - 50): m.start()], re.I):
        a["n_molecules"] = int(m.group(1))
    return a


def solution_from(text, src_method):
    s = {}
    if not text:
        return s
    phs = [float(m.group(1)) for m in X.R_PH.finditer(text) if 3 <= float(m.group(1)) <= 11]
    if phs:
        s["pH"] = Counter(phs).most_common(1)[0][0]
    m = X.R_BUFFER.search(text)
    if m:
        s["buffer"] = m.group(1)
    comps, seen = [], set()
    for m in X.R_SALT.finditer(text):
        name = m.group(3)
        key = (name.lower(), m.group(1))
        if key in seen or len(comps) >= 14:
            continue
        seen.add(key)
        comps.append({"name": name, "concentration": {"value": _num(m.group(1)), "unit": m.group(2).replace("μ", "µ").replace("uM", "µM")}})
    if comps:
        s["components"] = comps
        nts = sorted({c["name"] for c in comps if re.match(r"(ATP|ADP|AMP|GTP|GDP|GMP|dNTP|NTP)", c["name"], re.I)})
        if nts:
            s["nucleotides"] = nts
    ox = sorted({m.group(0).lower() for m in X.R_OXY.finditer(text)})
    if ox:
        s["oxygen_scavenging"] = ", ".join(ox[:4])
    return s


def labels_from(text):
    return sorted({m.group(0) for m in X.DYES.finditer(text or "")})[:10]


# ---------------------------------------------------------------- data links
DEPOSIT_REPOS = {"Zenodo", "Figshare", "Dryad", "Mendeley Data", "OSF", "4TU.ResearchData", "Harvard Dataverse", "Dataverse",
                 "DaRUS (Stuttgart)", "BioStudies", "ETH Research Collection", "Radboud Data Repository", "PANGAEA",
                 "UCL Research Data", "ORDA (Sheffield)", "Manchester Figshare", "Leeds", "SBGrid Data Bank", "EMPIAR"}
CODE_REPOS = {"GitHub", "GitLab", "Bitbucket", "Code Ocean", "Hugging Face"}
REFERENCE_DBS = re.compile(r"emdb|electron microscopy data bank|pdb|uniprot|intact|ena\b|genbank|geo\b|arrayexpress|bioproject|"
                           r"biosample|interpro|pfam|chebi|ensembl|alphafold|refseq|omim|reactome|rhea|metabolights|pride", re.I)
NON_DATA = re.compile(r"altmetric|wikipedia|faculty opinions|f1000|kudos|sciety|publons|hal open archive|europe pmc|pubmed|"
                      r"genome database|goa project|glygen|flybase|xenbase|informatics|wormbase|zfin|tair|dictybase|"
                      r"rat genome|mouse genome|saccharomyces|candida genome|pombase|orcid|crossref|researchgate|"
                      r"mendeley reader|plumx|dimensions|scite|semantic scholar|openalex|bioRxiv|medRxiv|arxiv", re.I)
SUPP_TITLE = re.compile(r"^(supplement(al|ary)?( material| information| data| file)?s?|supporting (information|material|data)|"
                        r"additional file|s\d+\s|fig(ure)?\.?\s*s?\d|table\s*s?\d|movie\s*s?\d|video\s*s?\d|data[_ ]sheet|image[_ ]\d|"
                        r"presentation[_ ]\d|table[_ ]\d|appendix|peer review|review history|source data)", re.I)


def classify_deposit(e, article_title=""):
    """-> 'deposit' (author data/code deposit), 'journal_supplement', 'accession', or 'drop'."""
    rid = (e.get("id") or "").lower()
    repo = e.get("repository") or ""
    pub = " ".join(filter(None, [repo, e.get("publisher_name") or ""]))
    title = re.sub(r"<[^>]+>", "", e.get("title") or "").strip()
    rtype = str(e.get("resource_type") or "").lower()
    if rid.startswith("50|") or rid.startswith("dedup"):
        return "drop"  # OpenAIRE-internal id without a resolvable PID
    if NON_DATA.search(pub) or NON_DATA.search(rid):
        return "drop"
    if "biostudies" in rid or repo == "BioStudies":
        return "journal_supplement" if "s-epmc" in rid else "deposit"
    if REFERENCE_DBS.search(pub) and repo not in DEPOSIT_REPOS:
        return "accession"
    if rtype in ("text", "journalarticle", "preprint", "peerreview", "book", "bookchapter", "conferencepaper"):
        return "drop"
    if e.get("journal_mirror") or rid.startswith("10.60893/") or SUPP_TITLE.search(title):
        return "journal_supplement"
    if repo == "Figshare" and rtype in ("image", "audiovisual", "presentation"):
        return "journal_supplement"
    if repo == "Figshare" and (".c." in rid or "figshare.c." in rid) and norm_title(title) == norm_title(article_title):
        return "journal_supplement"  # journal-created collection mirroring the article
    if repo in DEPOSIT_REPOS or repo in CODE_REPOS:
        return "deposit"
    if rid.startswith("10.") and rtype in ("dataset", "software", "collection", "model", "workflow", "computationalnotebook", "other", ""):
        return "deposit"
    return "drop"


def dataset_entry(id_, scheme, url, title, publisher, rtype, relation, linked_by, **kw):
    rid = norm_doi(id_) if scheme == "doi" else id_
    return {"id": rid, "scheme": scheme, "url": url or (f"https://doi.org/{rid}" if scheme == "doi" else (id_ if str(id_).startswith("http") else f"https://{id_}")),
            "title": title, "repository": repo_name((rid or "") + " " + (url or ""), publisher), "resource_type": rtype,
            "relation": relation, "linked_by": [linked_by], "publisher_name": publisher, **kw}


def collect_links(a, L, ft, ds_by_doi, ds_by_title):
    data, code, acc = {}, {}, {}

    def put(e):
        kind = classify_deposit(e, a.get("title") or "")
        if kind == "drop":
            return
        if kind == "accession":
            acc[(str(e.get("repository") or e.get("publisher_name") or "db").lower(), e["id"])] = {"scheme": "url" if str(e["id"]).startswith("http") else "other", "id": e["id"]}
            return
        if kind == "journal_supplement":
            e["journal_mirror"] = True
        e.pop("publisher_name", None)
        tgt = code if (str(e.get("resource_type") or "").lower() == "software" or e["repository"] in ("GitHub", "GitLab", "Bitbucket", "Code Ocean")) else data
        k = (e["id"] or "").lower().rstrip("/.")
        if not k:
            return
        if k in tgt:
            tgt[k]["linked_by"] = sorted(set(tgt[k]["linked_by"] + e["linked_by"]))
            for f in ("title", "year", "license", "resource_type"):
                if not tgt[k].get(f) and e.get(f):
                    tgt[k][f] = e[f]
        else:
            tgt[k] = e

    for d in L.get("datacite_related", []):
        rt = (d.get("target_type") or "")
        if rt.lower() in ("text", "journalarticle", "preprint", "conferencepaper", "book", "bookchapter", "dissertation", "peerreview"):
            continue
        meta = ds_by_doi.get(d["id"], {})
        put(dataset_entry(d["id"], "doi", d.get("url"), d.get("title"), d.get("publisher"), rt, d.get("relation"), "datacite_related",
                          year=d.get("year"), license=(d.get("rights") or [None])[0], journal_mirror=meta.get("journal_supplement_mirror", False)))
    for s in L.get("scholix", []):
        if not s.get("id"):
            continue
        sch = "doi" if (s.get("scheme") or "").lower() == "doi" or str(s["id"]).startswith("10.") else "url"
        if sch == "url" and not str(s["id"]).startswith("http"):
            if (s.get("scheme") or "").lower() in ("pdb", "uniprot", "ena", "genbank", "pmid", "pmc"):
                acc[(s["scheme"].lower(), s["id"])] = {"scheme": s["scheme"].lower(), "id": s["id"]}
                continue
        put(dataset_entry(s["id"], sch, s.get("url"), s.get("title"), s.get("publisher"), s.get("target_type"), s.get("relation"), "scholix"))
    for l in L.get("epmc_datalinks", []):
        sch = (l.get("scheme") or "").lower()
        cat = l.get("category") or ""
        if l.get("obtained_by") == "tm_accession" or sch in ("pdb", "uniprot", "ena", "bioproject", "geo", "arrayexpress", "refseq", "refsnp", "interpro", "pfam", "omim", "chebi", "ensembl", "emdb", "alphafold"):
            acc[(sch or cat.lower(), l.get("id"))] = {"scheme": sch or cat.lower(), "id": l.get("id")}
            continue
        if (l.get("target_type") or "").lower() in ("dataset", "software", "") and l.get("id"):
            put(dataset_entry(l["id"], "doi" if str(l["id"]).startswith("10.") else (sch or "url"), l.get("url"), l.get("title"),
                              l.get("publisher") or cat, l.get("target_type"), l.get("relation"), "europepmc_datalinks"))
    for e in L.get("epmc_annotations", []):
        if e["type"] == "Accession Numbers" and e.get("uri") and not any("reference" in s.lower() for s in e["sections"]):
            m = re.search(r"identifiers\.org/(?:ebi/|pdbe/)?([\w.]+):(.+)$", e["uri"])
            if m:
                sch, aid = m.group(1).lower(), m.group(2)
                if sch == "doi":
                    if re.match(r"10\.(5281|6084|5061|17632|17605|4121|7910|18419|34973|48420|25405|5522|15131|3929)", aid.lower()):
                        put(dataset_entry(aid, "doi", None, None, None, "Dataset", "References", "fulltext_statement"))
                    continue
                if sch in ("pdb", "pdbe"):
                    sch = "pdb"
                acc[(sch, aid)] = {"scheme": sch, "id": aid}
    statement = ""
    supp = []
    if ft and ft.get("ok"):
        statement = " ".join(d["text"] for d in ft.get("data_availability", []))
        seen_txt = set()
        parts = []
        for d in ft.get("data_availability", []):
            k = d["text"][:120]
            if k not in seen_txt:
                seen_txt.add(k)
                parts.append(d["text"])
        statement = " ".join(parts)
        links = sorted(set(re.sub(r"[.,;)\]]+$", "", l) for l in ft.get("repo_links", [])), key=len)
        kept = []
        for l in links:
            if any(l.startswith(k) for k in kept) and "github" in l.lower():
                continue
            kept.append(l)
        for l in kept:
            ll = l.lower()
            if re.match(r"(emd-|empiar-|s-bsst|s-biad)", ll):
                acc[(ll.split("-")[0], l)] = {"scheme": "emdb" if ll.startswith("emd") else ("empiar" if ll.startswith("empiar") else "biostudies"), "id": l}
                continue
            if ll.startswith("pdb"):
                mm = re.search(r"([0-9][A-Za-z0-9]{3})$", l)
                if mm:
                    acc[("pdb", mm.group(1).upper())] = {"scheme": "pdb", "id": mm.group(1).upper()}
                continue
            if ll.startswith("10."):
                put(dataset_entry(l, "doi", None, None, None, None, None, "fulltext_statement"))
            else:
                put(dataset_entry("https://" + l if not l.startswith("http") else l, "url", None, None, None,
                                  "Software" if re.search(r"github|gitlab|bitbucket|codeocean", ll) else "Dataset", None, "fulltext_statement"))
        supp = [s.get("label") or s.get("href") for s in ft.get("supplementary", []) if (s.get("label") or s.get("href"))]
        supp = list(dict.fromkeys(supp))[:30]
    # title match against harvested deposits
    nt = norm_title(a.get("title"))
    for d in ds_by_title.get(nt, []):
        put(dataset_entry(d["doi"], "doi", d.get("url"), d.get("title"), d.get("publisher"), d.get("resource_type"), "title_match", "title_match",
                          year=d.get("year"), journal_mirror=d.get("journal_supplement_mirror")))
    # resolve repository DOIs that lack metadata
    return data, code, acc, statement, supp


def norm_title(t):
    t = re.sub(r"<[^>]+>", "", (t or "").lower())
    t = re.sub(r"^(data (for|from)|dataset (for|from)|source data (for|from)|supporting data (for|from)|code (for|from)|data and code (for|from))\s*:?\s*", "", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def enrich_doi(doi):
    """DataCite metadata + (Zenodo/Figshare) file listing for a deposit DOI."""
    d = get(f"https://api.datacite.org/dois/{doi}")
    out = {}
    if d and d.get("data"):
        at = d["data"]["attributes"]
        out = {"title": (at.get("titles") or [{}])[0].get("title"), "year": at.get("publicationYear"),
               "publisher": at.get("publisher") if isinstance(at.get("publisher"), str) else (at.get("publisher") or {}).get("name"),
               "resource_type": (at.get("types") or {}).get("resourceTypeGeneral"),
               "license": next((r.get("rightsIdentifier") or r.get("rights") for r in at.get("rightsList", [])), None),
               "sizes": at.get("sizes"), "formats": at.get("formats")}
    files = []
    m = re.match(r"10\.5281/zenodo\.(\d+)", doi)
    if m:
        z = get(f"https://zenodo.org/api/records/{m.group(1)}")
        if z and isinstance(z, dict):
            for f in (z.get("files") or [])[:200]:
                files.append({"name": f.get("key"), "size_bytes": f.get("size")})
            if not out.get("license"):
                out["license"] = ((z.get("metadata") or {}).get("license") or {}).get("id")
    m = re.match(r"10\.6084/m9\.figshare\.(\d+)", doi)
    if m:
        fz = get(f"https://api.figshare.com/v2/articles/{m.group(1)}")
        if fz and isinstance(fz, dict):
            for f in (fz.get("files") or [])[:200]:
                files.append({"name": f.get("name"), "size_bytes": f.get("size")})
    if files:
        out["files"] = files
    return out


EXT_FORMAT = {"h5": "HDF5 (Lumicks .h5 / generic)", "hdf5": "HDF5", "tdms": "TDMS (LabVIEW)", "csv": "CSV", "txt": "text", "dat": "text/binary .dat",
              "xlsx": "Excel", "xls": "Excel", "mat": "MATLAB .mat", "npy": "NumPy", "npz": "NumPy", "ibw": "Igor .ibw", "pxp": "Igor .pxp",
              "jpk-force": "JPK force", "jpk-force-map": "JPK force map", "jpk-qi-data": "JPK QI", "spm": "Bruker/Nanoscope", "zip": "ZIP archive",
              "tar": "TAR archive", "gz": "gzip", "7z": "7z archive", "tif": "TIFF images", "tiff": "TIFF images", "avi": "video", "mp4": "video",
              "py": "Python code", "ipynb": "Jupyter notebook", "m": "MATLAB code", "r": "R code", "json": "JSON", "pdf": "PDF", "opj": "Origin",
              "opju": "Origin", "vi": "LabVIEW VI", "abf": "Axon ABF", "fast5": "FAST5 (nanopore)", "nd2": "Nikon ND2", "czi": "Zeiss CZI"}
RAW_EXT = {"h5", "hdf5", "tdms", "ibw", "jpk-force", "jpk-force-map", "spm", "abf", "fast5", "dat", "pxp", "npy", "npz", "mat"}


def file_summary(files):
    exts = Counter()
    for f in files or []:
        n = (f.get("name") or "").lower()
        e = n.rsplit(".", 1)[-1] if "." in n else ""
        if n.endswith(".jpk-force"):
            e = "jpk-force"
        exts[e] += 1
    fmts = sorted({EXT_FORMAT.get(e, e) for e in exts if e})
    raw = any(e in RAW_EXT for e in exts)
    code_only = exts and all(e in ("py", "ipynb", "m", "r", "vi", "zip") for e in exts) and any(e in ("py", "ipynb", "m", "r", "vi") for e in exts)
    return fmts, ("raw_traces" if raw else ("code" if code_only else ("processed" if exts else "unknown")))


# ---------------------------------------------------------------- legacy curated YAML
def load_curated():
    out = {}
    for p in sorted((ROOT / "publications_metadata").glob("study_*.yaml")):
        try:
            y = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cit = (y or {}).get("citation") or {}
        doi = norm_doi(cit.get("doi"))
        if doi:
            out[doi] = y
        if cit.get("title"):
            out["title:" + norm_title(cit["title"])] = y  # many legacy YAMLs lack DOIs
    return out


def merge_curated(rec, y):
    hw = y.get("hardware") or {}
    ins = hw.get("instrument") or {}
    ev = {"method": "manual_curation", "confidence": "high"}
    H = rec["hardware"]
    if ins.get("manufacturer"):
        H["make_of_setup"] = ins["manufacturer"]
    if ins.get("model"):
        H["model_number"] = ins["model"]
    ot = hw.get("optical_traps") or {}
    O = H.setdefault("optical", {})
    if ot.get("number_of_traps"):
        O["number_of_traps"] = ot["number_of_traps"]
    if ot.get("laser_wavelength_nm"):
        O["laser_wavelength"] = {"value": ot["laser_wavelength_nm"], "unit": "nm", "evidence": ev}
    if ot.get("laser_power_mW"):
        O["laser_power_at_source"] = {"value": ot["laser_power_mW"], "unit": "mW", "evidence": ev}
    ts = hw.get("trap_stiffness") or {}
    if ts.get("value"):
        O["trap_stiffness"] = {"value": ts["value"], "unit": "pN/nm", "evidence": ev}
    bd = hw.get("bead_diameter") or {}
    if bd.get("value"):
        rec["assay"]["bead_size"] = {"value": float(bd["value"]) * 1000, "unit": "nm", "evidence": ev}
    bp = hw.get("bead_properties") or {}
    if bp.get("material"):
        rec["assay"]["bead_material"] = bp["material"]
    if bp.get("surface_chemistry"):
        rec["assay"]["bead_functionalization"] = sorted(set(rec["assay"].get("bead_functionalization", []) + [bp["surface_chemistry"]]))
    fl = hw.get("fluorescence") or {}
    if fl.get("capability"):
        mods = set(rec["technique"].get("correlative_modalities", []))
        mods.add("confocal_fluorescence" if "confocal" in str(fl["capability"]).lower() else "widefield_fluorescence")
        rec["technique"]["correlative_modalities"] = sorted(mods)
    dyes = fl.get("dyes_used") or []
    s = y.get("sample") or {}
    na = s.get("nucleic_acid") or {}
    if na.get("name"):
        e = {"name": na["name"], "entity_type": "rna" if "rna" in str(na.get("type", "")).lower() else "dna", "role": "tethered_construct",
             "identifiers": [], "evidence": ev}
        if na.get("length_kb"):
            e["length"] = {"value": float(na["length_kb"]) * 1000, "unit": "bp"}
        if na.get("topology"):
            e["topology"] = na["topology"] if na["topology"] in ("linear", "supercoiled", "nicked", "hairpin") else "other"
        rec["biological_system"]["entities"].insert(0, e)
    pr = s.get("protein") or {}
    if pr.get("name"):
        e = {"name": pr["name"], "entity_type": "protein", "role": "binding_partner", "identifiers": [], "evidence": ev}
        if pr.get("concentration_nM"):
            e["concentration"] = {"value": pr["concentration_nM"], "unit": "nM"}
        rec["biological_system"]["entities"].insert(1, e)
    for ap in s.get("additional_proteins") or []:
        if isinstance(ap, dict) and ap.get("name"):
            e = {"name": ap["name"], "entity_type": "protein", "role": "in_solution", "identifiers": [], "evidence": ev}
            if ap.get("concentration_nM"):
                e["concentration"] = {"value": ap["concentration_nM"], "unit": "nM"}
            rec["solution"].setdefault("proteins_in_solution", []).append(e)
    for d in dyes:
        if isinstance(d, dict) and d.get("name"):
            rec["biological_system"].setdefault("fluorescent_labels", []).append({"identifier": d["name"], "sequence_location": d.get("target")})
    ec = y.get("experimental_conditions") or {}
    buf = ec.get("buffer") or {}
    if buf.get("composition"):
        rec["solution"]["buffer"] = buf.get("name") or rec["solution"].get("buffer")
        rec["solution"]["composition_text"] = buf["composition"]
    if buf.get("pH"):
        rec["solution"]["pH"] = buf["pH"]
    if ec.get("temperature_C"):
        H["temperature"] = {"value": round(float(ec["temperature_C"]) + 273.15, 2), "unit": "K", "evidence": ev}
    ms = y.get("measurements") or {}
    if ms.get("operation_mode"):
        mode = str(ms["operation_mode"]).lower().replace("-", "_").replace(" ", "_")
        tc = set(rec["assay"].get("trap_control", []))
        tc.add({"force_clamp": "force_clamp", "force_extension": "force_ramp", "constant_force": "constant_force"}.get(mode, "custom"))
        rec["assay"]["trap_control"] = sorted(tc)
    fr = ms.get("force_range") or {}
    if fr.get("minimum_pN") is not None and fr.get("maximum_pN") is not None:
        rec["technique"]["force_range_pN"] = {"value": None, "min": fr["minimum_pN"], "max": fr["maximum_pN"], "unit": "pN", "evidence": ev}
    fi = ms.get("fluorescence_imaging") or {}
    if fi.get("data_acquisition_rate_Hz"):
        H["acquisition_rate"] = {"value": fi["data_acquisition_rate_Hz"] / 1000, "unit": "kHz", "evidence": ev}
    if y.get("notes"):
        rec["curation"]["notes"] = str(y["notes"]).strip()[:1500]
    rec["curation"]["level"] = "curated"


def load_submitted():
    """Author/curator JSON records (schema v3, e.g. from submit.html) in hub/curated_json/*.json, keyed by DOI."""
    out = {}
    for p in sorted((HUB_DIR / "curated_json").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print("  !! bad submission", p.name, e)
            continue
        doi = norm_doi((d.get("publication") or {}).get("doi"))
        if doi:
            out[doi] = d
    return out


def _deep_merge(dst, src):
    for k, v in src.items():
        if v in (None, "", [], {}):
            continue
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v


BEAD_GEOMS = {"polymerization_assay", "one_bead", "two_bead_dumbbell", "three_bead", "four_bead", "bead_surface", "no_bead"}
ENTITY_TYPES = {"protein", "protein_complex", "peptide", "dna", "rna", "nucleoprotein", "cytoskeletal_filament", "membrane", "cell",
                "virus", "small_molecule", "polysaccharide", "synthetic"}


def normalize_submitted(sub):
    """Map free-text values reviewers used outside the controlled vocabularies; keep the original as *_detail."""
    a = sub.get("assay") or {}
    g = a.get("bead_geometry")
    if g and g not in BEAD_GEOMS:
        a["bead_geometry_detail"] = g
        a["bead_geometry"] = ("bead_surface" if re.search(r"surface|pedestal|on_surface", g) else
                              "one_bead" if re.search(r"single|one", g) else "two_bead_dumbbell" if "dumbbell" in g else None)
        if not a["bead_geometry"]:
            a.pop("bead_geometry")
    mg = ((sub.get("hardware") or {}).get("magnetic") or {})
    if mg.get("magnet_type") and mg["magnet_type"] not in ("permanent_pair", "permanent_single", "electromagnet", "cylindrical_ring", "other"):
        mg["magnet_type_detail"] = mg["magnet_type"]
        mg["magnet_type"] = "electromagnet" if "electro" in mg["magnet_type"] else "other"
    for e in (sub.get("biological_system") or {}).get("entities") or []:
        t = e.get("entity_type")
        if t and t not in ENTITY_TYPES:
            e["entity_type_detail"] = t
            e["entity_type"] = {"complex": "protein_complex", "material": "synthetic", "rna_dna_hybrid": "nucleoprotein" if "protein" in t else "dna",
                                "lipid": "membrane", "bead": "synthetic"}.get(t, "synthetic" if re.search(r"polymer|material|gel|bead", t) else "protein")
    return sub


def merge_submitted(rec, sub):
    """Submitted values override automatic ones section by section; entities/results replace wholesale."""
    sub = normalize_submitted(sub)
    replace = (sub.get("curation") or {}).get("level") == "ai_assisted"  # reviewed sections supersede auto values
    for sec in ("technique", "hardware", "assay", "solution", "annotations"):
        if sub.get(sec):
            if replace and sec in ("hardware", "assay", "solution"):
                keep = {k: v for k, v in rec[sec].items() if k == "experiment_class"}
                rec[sec] = {**keep, **sub[sec]}
            else:
                _deep_merge(rec[sec], sub[sec])
    bs = sub.get("biological_system") or {}
    if bs.get("entities"):
        rec["biological_system"]["entities"] = bs["entities"]
    for k in ("system_class", "organisms", "cell", "cytoskeleton", "fluorescent_labels"):
        if bs.get(k):
            rec["biological_system"][k] = bs[k]
    if sub.get("results"):
        rec["results"] = sub["results"] + [r for r in rec["results"] if r.get("source", {}).get("extraction") != "auto_regex"]
    da = sub.get("data_availability") or {}
    for d in da.get("datasets", []) + da.get("code", []):
        d.setdefault("linked_by", ["manual"])
        d.setdefault("scheme", "doi" if str(d.get("id", "")).startswith("10.") else "url")
        d.setdefault("repository", repo_name(d.get("id", "")))
        d.setdefault("url", f"https://doi.org/{d['id']}" if d["scheme"] == "doi" else d.get("id"))
    if da.get("datasets"):
        have = {x["id"] for x in rec["data_availability"]["datasets"]}
        rec["data_availability"]["datasets"] += [d for d in da["datasets"] if d["id"] not in have]
        rec["data_availability"]["status"] = "public_repository"
    if da.get("code"):
        have = {x["id"] for x in rec["data_availability"]["code"]}
        rec["data_availability"]["code"] += [d for d in da["code"] if d["id"] not in have]
    rec["curation"]["level"] = (sub.get("curation") or {}).get("level") or "author_verified"
    if (sub.get("curation") or {}).get("notes"):
        rec["curation"]["notes"] = sub["curation"]["notes"]
    if (sub.get("curation") or {}).get("curators"):
        rec["curation"]["curators"] = sub["curation"]["curators"]


# ---------------------------------------------------------------- completeness
T3_FIELDS = {
    "hardware": ["make_of_setup", "model_number|custom_built", "detection_device", "objective_lens", "temperature", "acquisition_rate",
                 "filter_frequency", "calibration_technique", "optical.laser_wavelength|magnetic.bead_product|afm.cantilever_model|nanopore.pore",
                 "optical.trap_stiffness|afm.spring_constant|magnetic.magnet_type", "optical.laser_power_at_source|magnetic.camera_frame_rate|afm.pulling_speed",
                 "optical.spatial_laser_control|magnetic.rotation_control"],
    "assay": ["bead_size", "bead_functionalization|attachment_chemistry", "trap_control", "bead_geometry", "handle_sequences|loading_rate|pulling_speed"],
    "construct": ["entities", "identifiers", "organisms", "fluorescent_labels"],
    "solution": ["buffer", "pH", "components", "nucleotides|oxygen_scavenging"],
    "data": ["datasets", "statement", "raw"],
}


def _has(d, path):
    for alt in path.split("|"):
        cur = d
        ok = True
        for p in alt.split("."):
            if isinstance(cur, dict) and cur.get(p) not in (None, [], {}, ""):
                cur = cur[p]
            else:
                ok = False
                break
        if ok:
            return True
    return False


def completeness(rec):
    c = {}
    c["hardware"] = sum(_has(rec["hardware"], f) for f in T3_FIELDS["hardware"]) / len(T3_FIELDS["hardware"])
    c["assay"] = sum(_has(rec["assay"], f) for f in T3_FIELDS["assay"]) / len(T3_FIELDS["assay"])
    bs = rec["biological_system"]
    c["construct"] = (bool(bs["entities"]) + any(e.get("identifiers") for e in bs["entities"]) + bool(bs.get("organisms")) + bool(bs.get("fluorescent_labels"))) / 4
    c["solution"] = sum(_has(rec["solution"], f) for f in T3_FIELDS["solution"]) / len(T3_FIELDS["solution"])
    da = rec["data_availability"]
    c["data"] = (bool(da.get("datasets")) + bool(da.get("statement")) + bool(da.get("raw_traces_available"))) / 3
    c["overall"] = round(sum(c.values()) / 5, 3)
    return {k: round(v, 2) for k, v in c.items()}


# ---------------------------------------------------------------- main
def main():
    arts = [a for a in load_jsonl(OUT / "articles_classified.jsonl") if a["tier"] in ("core", "methods")]
    links = load_json(OUT / "links.json", {}) or {}
    ft_index = load_json(OUT / "fulltext_index.json", {}) or {}
    raw_ds = load_jsonl(OUT / "datasets_raw.jsonl")
    ds_by_doi = {d["doi"]: d for d in raw_ds}
    ds_by_title = defaultdict(list)
    for d in raw_ds:
        if not d.get("journal_supplement_mirror"):
            ds_by_title[norm_title(d["title"])].append(d)
    # related-identifier reverse index from harvested deposits (article DOI -> deposits)
    rev = defaultdict(list)
    for d in raw_ds:
        for r in d["related"]:
            if r["type"] == "DOI" and r["relation"] in ("IsSupplementTo", "IsCitedBy", "IsReferencedBy", "IsDocumentedBy", "IsDescribedBy", "IsSourceOf", "IsDerivedFrom", "Cites", "References", "IsPartOf"):
                rev[r["id"]].append(d)
            elif r["type"] in ("PMID",):
                rev["pmid:" + r["id"]].append(d)
    curated = load_curated()
    submitted = load_submitted()
    print("articles:", len(arts), "curated YAML:", len(curated), "submitted JSON:", len(submitted))

    records, used_ds = [], set()
    # prefetch taxonomy for every text-mined organism (canonical scientific names + rank)
    taxa = set(str(t) for _, _, t in ORGANISMS)
    for L in links.values():
        for e in L.get("epmc_annotations", []):
            secs = " ".join(e.get("sections") or []).lower()
            m = re.search(r"taxonomy/(\d+)", e.get("uri") or "") if e["type"] == "Organisms" and re.search("abstract|title|method", secs) else None
            if m:
                taxa.add(m.group(1))
    todo_t = [t for t in taxa if t not in TAXA]
    print("taxonomy lookups:", len(todo_t))
    pmap(taxon_info, todo_t, workers=6, desc="taxonomy")
    save_json(OUT / "taxonomy_cache.json", TAXA)

    # prefetch every UniProt lookup the main loop will need (default + paper-organism orthologs), in parallel
    pre_uni = set()
    for a in arts:
        ta = " ".join(filter(None, [re.sub(r"<[^>]+>", "", a.get("title") or ""), re.sub(r"<[^>]+>", "", a.get("abstract") or "")]))
        hits = [g for rx, g in GAZ if ("gene" in g["lookup"] or "uniprot" in g["lookup"]) and rx.search(ta)]
        if not hits:
            continue
        taxa = [TAXON_FIX.get(o["ncbi_taxon"], o["ncbi_taxon"]) for o in organisms_for(a, links.get(a["epmc_id"], {}).get("epmc_annotations", []), ta)[:2]]
        for g in hits:
            lk = g["lookup"]
            if "gene" in lk:
                for t in taxa + [lk["taxon"]]:
                    pre_uni.add(f"gene|{lk['gene']}|{t}")
            else:
                pre_uni.add(f"acc|{lk['uniprot']}|")
    todo = [k for k in pre_uni if k not in UNI]
    print("uniprot lookups:", len(todo))
    for k, v in zip(todo, pmap(uniprot_lookup, todo, workers=8, desc="uniprot")):
        pass
    save_json(OUT / "uniprot_cache.json", UNI)

    for i, a in enumerate(sorted(arts, key=lambda x: (-(x.get("year") or 0), x["epmc_id"]))):
        if i % 500 == 0:
            print(f"  annotate: {i}/{len(arts)}", flush=True)
        L = links.get(a["epmc_id"], {})
        ann = L.get("epmc_annotations", [])
        ft = None
        if a["epmc_id"] in ft_index:
            p = FT_CACHE / f"{ft_index[a['epmc_id']]}.json"
            if p.exists():
                ft = json.loads(p.read_text(encoding="utf-8"))
        title_abs = " ".join(filter(None, [re.sub(r"<[^>]+>", "", a.get("title") or ""), re.sub(r"<[^>]+>", "", a.get("abstract") or "")]))
        methods = (ft or {}).get("methods_text") or ""
        params_text = methods if methods else title_abs
        src = "regex_fulltext_methods" if methods else "regex_title_abstract"
        techs = sorted(a["techniques_detected"] or ["force_spectroscopy_unspecified"], key=lambda t: TECH_PRIORITY.index(t) if t in TECH_PRIORITY else 99)
        techs = [t for t in techs if t in TECH_PRIORITY] or ["force_spectroscopy_unspecified"]
        # if AFM + unspecified and full text says optical/magnetic, prefer that
        if techs[0] == "force_spectroscopy_unspecified" and methods:
            for t, rx in (("afm_smfs", r"cantilever|atomic force"), ("optical_tweezers", r"optical (tweezers|trap)"), ("magnetic_tweezers", r"magnetic tweezers")):
                if re.search(rx, methods, re.I):
                    techs = [t]
                    break
        orgs = organisms_for(a, ann, title_abs)
        ents = entities_for(title_abs, methods, orgs)
        classes = experiment_classes(title_abs, ents, techs)
        if a["tier"] == "methods" and not classes:
            classes = ["methods_calibration"]
        # Gene_Proteins from abstract that gazetteer missed (low confidence)
        tm_ents = []
        names_have = " ".join(e["name"].lower() for _, e in ents)
        for e in ann:
            if e["type"] == "Gene_Proteins" and any("abstract" in s.lower() or "title" in s.lower() for s in e["sections"]) and e.get("uri"):
                txt = e["text"].strip()
                # keep gene/protein-symbol-like mentions only (e.g. KIF11, RecQ, Hsp104): short, contains a capital or digit
                if not (3 <= len(txt) <= 12 and re.fullmatch(r"[A-Za-z][A-Za-z0-9\-/αβγδ]*", txt) and re.search(r"[A-Z0-9]", txt[1:] + txt[0])):
                    continue
                if txt.lower() in names_have or txt.lower() in ("dna", "rna", "atp", "adp", "gtp", "afm", "smfs", "key", "smfret", "fret", "pbs", "bsa", "tris", "hepes", "edta", "nacl", "kcl", "pn", "nm"):
                    continue
                m = re.search(r"uniprot(?:kb)?/([A-Z0-9]{6,10})", e["uri"])
                if not m or any(i["id"] == m.group(1) for _, ge in ents for i in ge["identifiers"]) or any(t["identifiers"][0]["id"] == m.group(1) for t in tm_ents):
                    continue
                tm_ents.append({"name": txt, "entity_type": "protein", "role": "unspecified",
                                "identifiers": [{"scheme": "uniprot", "id": m.group(1), "verified": False}],
                                "evidence": {"method": "europepmc_textmining", "confidence": "low",
                                             "note": "text-mined mention; UniProt accession may be a different species/ortholog"}})
        tm_ents = tm_ents[:6]
        cell = {}
        for _, e in ents:
            if e["entity_type"] == "cell":
                cell["cell_identity"] = e["name"]
                for idf in e["identifiers"]:
                    if idf["scheme"] == "cl":
                        cell["cell_ontology"] = idf
                break
        cyto = {}
        for _, e in ents:
            if e["entity_type"] == "cytoskeletal_filament":
                cyto["structure_type"] = "microtubule" if "Microtubule" in e["name"] else ("microfilament_actin" if "Actin" in e["name"] else "intermediate_filament")
                break
        hw = hardware_from(params_text, techs, src)
        assay = assay_from(params_text, techs, src)
        assay["experiment_class"] = classes
        sol = solution_from(params_text, src)
        mods = [n for n, rx in X.MODALITY_RX if rx.search(title_abs + " " + methods[:20000])]
        geom = [n for n, rx in X.GEOMETRY_RX if rx.search(title_abs + " " + methods[:30000]) and set(techs) & X.GEOM_TECH.get(n, set())]
        if not geom and techs[0] in X.TECH_DEFAULT_GEOM:
            geom = [X.TECH_DEFAULT_GEOM[techs[0]]]
        sw = [n for n, rx in X.SOFTWARE_RX if rx.search(methods or title_abs)]
        models = []
        for n, rx in X.MODELS_RX:
            if rx.search(title_abs + " " + methods):
                if n == "WLC" and "eWLC" in models:
                    continue
                if n == "Bell" and "Bell-Evans" in models:
                    continue
                models.append(n)
        dyes = labels_from(title_abs + " " + methods)

        data, code, acc, statement, supp = collect_links(a, L, ft, ds_by_doi, ds_by_title)
        for d in rev.get(a.get("doi") or "-", []) + rev.get("pmid:" + str(a.get("pmid")), []):
            k = d["doi"]
            if k not in data and k not in code:
                e = dataset_entry(d["doi"], "doi", d.get("url"), d.get("title"), d.get("publisher"), d.get("resource_type"), "IsSupplementTo", "datacite_related",
                                  year=d.get("year"), journal_mirror=d.get("journal_supplement_mirror"))
                kind = classify_deposit(e, a.get("title") or "")
                e.pop("publisher_name", None)
                if kind in ("deposit", "journal_supplement"):
                    e["journal_mirror"] = kind == "journal_supplement"
                    (code if (d.get("resource_type") or "") == "Software" else data)[k] = e
        # classify the statement and overall status
        st_cls = X.classify_statement(statement)
        real = [d for d in data.values() if not d.get("journal_mirror")]
        mirrors = [d for d in data.values() if d.get("journal_mirror")]
        supp_data = [s for s in supp if re.search(r"source data|data\s*s?\d|\.(xlsx?|csv|zip|txt|h5|mat)$|dataset", str(s), re.I)]
        if real:
            status = "public_repository"
        elif "public_repository" in st_cls and not code:
            status = "public_repository" if re.search(r"zenodo|figshare|dryad|osf|mendeley|dataverse|4tu|biostudies|doi\.org|accession", statement, re.I) else "on_request" if "on_request" in st_cls else "public_repository"
        elif "source_data_supplement" in st_cls or any(re.search(r"source data", str(s), re.I) for s in supp):
            status = "source_data_supplement"
        elif code:
            status = "code_only"
        elif mirrors or supp_data or "journal_supplement" in st_cls:
            status = "journal_supplement"
        elif "on_request" in st_cls:
            status = "on_request"
        elif "not_available" in st_cls:
            status = "not_available"
        elif ft and ft.get("ok"):
            status = "not_stated"
        else:
            status = "unknown_no_fulltext"

        rec_id = None  # assigned after sorting
        pubtypes = [p.lower() for p in a.get("pub_types") or []]
        kind = "review" if a.get("is_review") else ("preprint" if a["source"] == "PPR" or "preprint" in pubtypes else
                ("correction" if any("erratum" in p or "correction" in p for p in pubtypes) or re.match(r"(correction|erratum|retraction)", a.get("title") or "", re.I) else
                 ("methods" if a["tier"] == "methods" else "primary_research")))
        rec = {
            "record_id": None, "schema_version": "3.1.0",
            "curation": {"level": "auto_fulltext" if methods else "auto_abstract", "last_updated": TODAY},
            "publication": {k: v for k, v in {
                "doi": a.get("doi"), "pmid": a.get("pmid"), "pmcid": a.get("pmcid"),
                "title": re.sub(r"<[^>]+>", "", a.get("title") or "").strip(), "authors": a.get("authors"), "affiliations": a.get("affiliations"),
                "journal": a.get("journal"), "year": a.get("year"), "publication_date": a.get("pub_date"), "abstract": re.sub(r"<[^>]+>", "", a.get("abstract") or ""),
                "keywords": a.get("keywords"), "mesh_terms": a.get("mesh"), "open_access": a.get("is_oa"), "license": a.get("license"),
                "cited_by": a.get("cited_by"), "funders": sorted(set(a.get("grants") or []))}.items() if v not in (None, [], "")},
            "scope": {"tier": a["tier"], "article_kind": kind, "reasons": a.get("scope_reasons")},
            "technique": {"primary": techs[0], "secondary": techs[1:], "force_application_geometry": geom[0] if geom else "other",
                          "correlative_modalities": mods, "multiplexed": bool(set(techs) & {"acoustic_force_spectroscopy", "centrifuge_force"}) or bool(re.search(r"multiplex|parallel|high[- ]throughput|hundreds of", title_abs, re.I)),
                          "evidence_queries": a.get("query_tags")},
            "hardware": hw, "assay": assay,
            "biological_system": {"system_class": classes, "table3_columns": sorted({TABLE3_COLUMN.get(c, c) for c in classes}),
                                  "organisms": orgs, "entities": [e for _, e in ents] + tm_ents,
                                  **({"cell": cell} if cell else {}), **({"cytoskeleton": cyto} if cyto else {}),
                                  **({"fluorescent_labels": [{"identifier": d} for d in dyes]} if dyes else {})},
            "solution": sol,
            "results": X.extract_results(re.sub(r"<[^>]+>", "", a.get("abstract") or "")),
            "data_availability": {"status": status, "has_linked_dataset": bool(real), "statement": statement[:2500],
                                  "statement_classes": st_cls, "datasets": list(real) + list(mirrors), "code": list(code.values()),
                                  "accessions": list(acc.values())[:40], "supplementary_files": supp,
                                  "fulltext_checked": bool(ft and ft.get("ok"))},
            "annotations": {"instrument_vendor": hw.get("make_of_setup"), "analysis_software": sw, "analysis_models": models,
                            "disease_relevance": sorted({e["text"] for e in ann if e["type"] == "Diseases" and any("abstract" in s.lower() for s in e["sections"])})[:8],
                            "keywords": a.get("keywords"), "funding": sorted(set(a.get("grants") or []))},
        }
        cy = curated.get(a.get("doi")) or curated.get("title:" + norm_title(a.get("title")))
        if cy:
            merge_curated(rec, cy)
        if a.get("doi") in submitted:
            merge_submitted(rec, submitted[a["doi"]])
        for d in rec["data_availability"]["datasets"] + rec["data_availability"]["code"]:
            if d.get("scheme") == "doi":
                used_ds.add(d["id"])
        records.append(rec)

    # enrich linked deposit DOIs with DataCite metadata + file listings
    dois = sorted(used_ds)
    print("enriching deposits:", len(dois))
    meta = dict(zip(dois, pmap(enrich_doi, dois, workers=4, desc="deposit metadata")))
    for rec in records:
        da = rec["data_availability"]
        raw_any = False
        for d in da["datasets"] + da["code"]:
            m = meta.get(d["id"]) if d.get("scheme") == "doi" else None
            if isinstance(m, dict):
                for k in ("title", "year", "license", "resource_type"):
                    if m.get(k) and not d.get(k):
                        d[k] = m[k]
                if m.get("publisher") and d.get("repository") in (None, "other"):
                    d["repository"] = repo_name(d["id"], m["publisher"])
                if m.get("files"):
                    d["files"] = m["files"][:60]
                    d["n_files"] = len(m["files"])
                    d["total_size_bytes"] = sum(f.get("size_bytes") or 0 for f in m["files"])
                    d["file_formats"], d["content"] = file_summary(m["files"])
                    raw_any = raw_any or d["content"] == "raw_traces"
            if d.get("repository") == "other" and d.get("id", "").startswith("10."):
                d["repository"] = repo_name(d["id"], (m or {}).get("publisher") if isinstance(m, dict) else None)
        # real dataset may have been a code deposit (resource_type Software after enrichment)
        moved = [d for d in da["datasets"] if (d.get("resource_type") or "").lower() == "software"]
        if moved:
            da["datasets"] = [d for d in da["datasets"] if d not in moved]
            da["code"] += moved
        real = [d for d in da["datasets"] if not d.get("journal_mirror")]
        da["has_linked_dataset"] = bool(real)
        if not real and da["status"] == "public_repository" and da["code"] and not re.search(r"zenodo|figshare|dryad|osf|mendeley|dataverse|4tu|biostudies|accession", da["statement"] or "", re.I):
            da["status"] = "code_only"
        da["has_linked_code"] = bool(da["code"])
        da["raw_traces_available"] = raw_any
        da["repositories"] = sorted({d["repository"] for d in real + da["code"] if d.get("repository")})
        rec["fair_completeness"] = completeness(rec)

    rejected = [r for r in records if str(r["curation"].get("notes") or "").startswith("NOT SMFS")]
    if rejected:
        save_json(OUT / "rejected_by_review.json", [{"doi": r["publication"].get("doi"), "title": r["publication"].get("title"),
                                                      "notes": r["curation"]["notes"]} for r in rejected], indent=1)
        records = [r for r in records if r not in rejected]
        print("removed after review (not SMFS):", len(rejected))
    records.sort(key=lambda r: (-(r["publication"].get("year") or 0), r["publication"].get("title") or ""))
    # stable identifiers: a study keeps its SMFS id across rebuilds (keyed by DOI, else PMID/PMCID/title)
    id_map = load_json(HUB_DIR / "id_map.json", {}) or {}
    nxt = max([int(v[5:]) for v in id_map.values()] + [0]) + 1
    for r in records:
        p = r["publication"]
        key = ("doi:" + p["doi"]) if p.get("doi") else ("pmid:" + p["pmid"]) if p.get("pmid") else ("pmcid:" + p["pmcid"]) if p.get("pmcid") else ("title:" + norm_title(p.get("title")))
        if key not in id_map:
            id_map[key] = f"SMFS-{nxt:06d}"
            nxt += 1
        r["record_id"] = id_map[key]
    save_json(HUB_DIR / "id_map.json", id_map, indent=0)
    save_json(OUT / "uniprot_cache.json", UNI)

    # deposits hub: linked deposits + unlinked SMFS-relevant deposits
    linked = defaultdict(list)
    for r in records:
        for d in r["data_availability"]["datasets"] + r["data_availability"]["code"]:
            linked[(d["id"] or "").lower()].append(r["record_id"])
    from s03_classify import BIO, TECH
    hub_ds = []
    for d in raw_ds:
        k = (d["doi"] or "").lower()
        txt = (d["title"] or "") + " " + (d["description"] or "") + " " + " ".join(d.get("subjects") or [])
        techs = [t for t, rx in TECH.items() if rx.search(txt.lower()) and t not in ("afm_generic",)]
        bio = bool(BIO.search(txt.lower()))
        if k in linked or (techs and not d.get("journal_supplement_mirror") and not SUPP_TITLE.search(d.get("title") or "") and (d.get("resource_type") or "") in ("Dataset", "Software", "Collection", "Other", "Model", "Workflow", "ComputationalNotebook")):
            hub_ds.append({"doi": d["doi"], "title": d["title"], "repository": repo_name(d["doi"] + " " + (d.get("url") or ""), d.get("publisher")),
                           "publisher": d.get("publisher"), "year": d.get("year"), "resource_type": d.get("resource_type"),
                           "techniques": techs, "creators": d.get("creators")[:6], "linked_records": linked.get(k, []),
                           "related_articles": [r["id"] for r in d["related"] if r["type"] == "DOI" and r["relation"] in ("IsSupplementTo", "IsCitedBy", "IsReferencedBy", "IsDescribedBy", "IsDocumentedBy")][:5],
                           "journal_mirror": d.get("journal_supplement_mirror"), "rights": d.get("rights"),
                           "description": re.sub(r"<[^>]+>", " ", d.get("description") or "")[:600]})
    # linked deposits not in harvest (found via article side)
    have = {h["doi"].lower() for h in hub_ds}
    for r in records:
        for d in r["data_availability"]["datasets"] + r["data_availability"]["code"]:
            k = (d["id"] or "").lower()
            if k and k not in have:
                have.add(k)
                hub_ds.append({"doi": d["id"] if d.get("scheme") == "doi" else None, "url": d.get("url"), "title": d.get("title") or d["id"],
                               "repository": d.get("repository"), "year": d.get("year"), "resource_type": d.get("resource_type"),
                               "techniques": [r["technique"]["primary"]], "linked_records": linked.get(k, []),
                               "journal_mirror": d.get("journal_mirror"), "file_formats": d.get("file_formats"), "content": d.get("content"),
                               "n_files": d.get("n_files"), "total_size_bytes": d.get("total_size_bytes"), "license": d.get("license")})
    for h in hub_ds:
        m = meta.get(h.get("doi"))
        if isinstance(m, dict) and m.get("files"):
            h["file_formats"], h["content"] = file_summary(m["files"])
            h["n_files"] = len(m["files"])
            h["total_size_bytes"] = sum(f.get("size_bytes") or 0 for f in m["files"])
    # Milestone 1 cleanup: publish/count one row per DOI family and retain all
    # relevance labels in the download. Linked study scope takes precedence.
    deposit_rows_before_cleanup = len(hub_ds)
    record_scopes = {r["record_id"]: ("methods" if r["scope"]["tier"] == "methods" else "in_scope") for r in records}
    hub_ds = collapse_families(hub_ds, record_scopes)
    annotate_record_links(records, hub_ds)
    save_jsonl(OUT / "records.jsonl", records)
    save_jsonl(OUT / "datasets_hub.jsonl", hub_ds)

    review = [{"kind": "deposit_relevance", "family_id": h["family_id"], "title": h.get("title"),
               "repository": h.get("repository"), "linked_records": h.get("linked_records", []),
               "relevance": h["relevance"], "evidence": h["relevance_evidence"]}
              for h in hub_ds if h["relevance"] == "unsure"]
    save_jsonl(OUT / "harvester_review_queue.jsonl", review)

    primary = [r for r in records if r["scope"]["article_kind"] in ("primary_research", "methods", "preprint")]
    covered = sum(r["data_availability"]["status"] != "unknown_no_fulltext" for r in primary)
    counted = [h for h in hub_ds if h["relevance"] in COUNTED_RELEVANCE and not h.get("journal_mirror")]
    metrics = {
        "milestone": 1, "version": CLEANUP_VERSION, "run_date": TODAY,
        "baseline": {"primary_studies": len(primary), "status_covered": covered,
                     "status_coverage": round(covered / max(1, len(primary)), 4),
                      "deposit_rows": 3760, "linked_deposit_rows": 2938,
                      "raw_trace_rows": 7, "figshare_version_rows_at_least": 537},
        "cleanup": {"candidate_rows_before_family_cleanup": deposit_rows_before_cleanup,
                    "deposit_families_all_labels": len(hub_ds), "unique_biological_deposits": len(counted),
                    "raw_trace_families": sum(h.get("content") == "raw_traces" for h in counted),
                    "relevance": dict(Counter(h["relevance"] for h in hub_ds)),
                    "families_with_multiple_dois": sum(bool(h.get("version_dois")) for h in hub_ds),
                    "review_queue": len(review)},
        "gates": {"family_pairwise_accuracy": {"target": 0.98, "measured": None, "reason": "gold set not yet labelled"},
                  "relevance_in_scope_precision": {"target": 0.95, "measured": None, "reason": "gold set not yet labelled"}},
    }
    save_json(OUT / "harvester_m1_metrics.json", metrics, indent=2)

    st = Counter(r["data_availability"]["status"] for r in records)
    print("records:", len(records), "| status:", dict(st))
    print("with linked dataset:", sum(r["data_availability"]["has_linked_dataset"] for r in records),
          "| with code:", sum(r["data_availability"]["has_linked_code"] for r in records),
          "| raw traces:", sum(r["data_availability"]["raw_traces_available"] for r in records))
    print("hub deposit families:", len(hub_ds), "counted:", len(counted), "review:", len(review),
          "unlinked:", sum(1 for h in hub_ds if not h["linked_records"]))
    print("mean completeness:", round(sum(r["fair_completeness"]["overall"] for r in records) / len(records), 3))


if __name__ == "__main__":
    main()
