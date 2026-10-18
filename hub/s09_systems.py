"""Step 9 - biological-system pages: aggregate studies per system and attach descriptions + link-outs.

Systems are the canonical gazetteer entries (gazetteer.py). AI-curated/curated entities are mapped to a
system when they share a UniProt accession with it. Descriptions come from UniProt (function annotation,
CC BY 4.0) and English Wikipedia (summary extract, CC BY-SA 4.0), found via Wikidata (UniProt ID -> article)
or a curated title map; both are attributed on the page. Output: website/data/systems.js (SMASH.systems).
Called from s07_build_site.py (website/data is rebuilt there), or standalone.
"""
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

from common import clean_obj, OUT, get, load_json, load_jsonl, pmap, save_json
from gazetteer import G

WEB = Path(__file__).resolve().parent.parent / "website"

# Wikipedia titles for non-protein / generic systems (redirects are followed by the summary API)
WIKI_TITLES = {
    "λ-phage DNA (48.5 kb)": "Lambda phage", "pBR322 plasmid DNA": "PBR322", "pUC19 plasmid DNA": "PUC19",
    "M13mp18 phage DNA": "M13 bacteriophage", "ΦX174 phage DNA": "Phi X 174",
    "Widom 601 nucleosome positioning sequence": "Nucleosome positioning region", "G-quadruplex / i-motif": "G-quadruplex",
    "DNA hairpin": "Stem-loop", "RNA hairpin / stem-loop": "Stem-loop", "RNA pseudoknot": "Pseudoknot",
    "Programmed ribosomal frameshift element": "Ribosomal frameshift", "Riboswitch": "Riboswitch",
    "Adenine riboswitch (add)": "Purine riboswitch", "preQ1 riboswitch": "PreQ1 riboswitch", "SAM riboswitch": "SAM riboswitch element",
    "TPP riboswitch": "TPP riboswitch", "Fluoride riboswitch": "Fluoride riboswitch", "glmS ribozyme": "GlmS glucosamine-6-phosphate activated ribozyme",
    "Group I intron ribozyme": "Group I catalytic intron", "HIV-1 TAR RNA": "Trans-activation response element (HIV)",
    "HIV-1 Rev response element": "Rev response element", "tRNA": "Transfer RNA", "mRNA": "Messenger RNA",
    "double-stranded RNA": "Double-stranded RNA", "single-stranded DNA": "DNA", "double-stranded DNA": "DNA",
    "supercoiled DNA": "DNA supercoil", "Holliday junction": "Holliday junction", "R-loop": "R-loop", "Telomeric DNA": "Telomere",
    "DNA origami": "DNA origami", "DNA triplex": "Triple-stranded DNA", "non-B DNA conformation": "Z-DNA",
    "Chromatin fiber / nucleosome array": "Chromatin", "Nucleosome": "Nucleosome", "Mitotic chromosome": "Chromosome",
    "Immunoglobulin-like domain": "Immunoglobulin domain", "EF-hand calcium-binding domain": "EF hand", "Ankyrin repeats": "Ankyrin repeat",
    "Intrinsically disordered protein": "Intrinsically disordered proteins", "Nascent polypeptide (co-translational folding)": "Cotranslational folding",
    "Mechanosensitive channel": "Mechanosensitive channels", "SNARE complex (syntaxin-1/SNAP-25/VAMP2)": "SNARE (protein)",
    "Cohesin–dockerin complex": "Dockerin", "SpyTag/SpyCatcher": "SpyCatcher", "Antibody–antigen": "Antibody",
    "Spider silk (spidroin)": "Spider silk", "Mussel foot protein": "Mussel adhesive protein", "Elastin / elastin-like polypeptide": "Elastin",
    "Fibrinogen / fibrin": "Fibrin", "Biotin": "Biotin", "Digoxigenin": "Digoxigenin", "Streptavidin": "Streptavidin", "Avidin": "Avidin",
    "Kinesin": "Kinesin", "Myosin": "Myosin", "Helicase": "Helicase", "Proteasome": "Proteasome", "Sec translocon": "Translocon",
    "Actin filament": "Microfilament", "Microtubule (αβ-tubulin)": "Microtubule", "Intermediate filament (vimentin)": "Intermediate filament",
    "Keratin intermediate filament": "Keratin", "Kinetochore (Ndc80/Dam1)": "Kinetochore", "Arp2/3 complex": "Arp2/3 complex",
    "F1Fo ATP synthase": "ATP synthase", "Bacterial flagellar motor": "Flagellar motor", "Type IV pilus / PilT retraction motor": "Type IV pilus",
    "Viral DNA packaging motor": "Viral DNA packaging motor", "Axonemal dynein / cilia": "Axonemal dynein", "Formin": "Formins",
    "ESCRT-III": "ESCRT", "Ribosome": "Ribosome", "Reverse transcriptase": "Reverse transcriptase", "DNA polymerase / replisome": "Replisome",
    "CMG / MCM2-7 replicative helicase": "Minichromosome maintenance", "SMC complex (loop extrusion)": "Structural maintenance of chromosomes",
    "CRISPR–Cas effector": "CRISPR", "Cas12a": "Cas12a", "Restriction endonuclease": "Restriction enzyme", "Nucleotide excision repair machinery": "Nucleotide excision repair",
    "Chromatin remodeler": "Chromatin remodeling", "Core histones": "Histone", "Telomerase": "Telomerase", "Retroviral integrase": "Integrase",
    "Viral nucleocapsid protein": "Capsid", "Nucleocapsid (N) protein": "Nucleocapsid", "DNA ligase": "DNA ligase", "Exonuclease": "Exonuclease",
    "Transcription factor": "Transcription factor", "DNA-binding small molecule / intercalator": "Intercalation (biochemistry)",
    "Polyvalent cation (DNA condensing)": "Polyamine", "Biomolecular condensate": "Biomolecular condensate",
    "Membrane tether/nanotube": None, "Cadherin (classical)": "Cadherin", "Myosin V": "Myosin V",
    "Synthetic polymer / mechanophore": "Mechanochemistry", "Nascent polypeptide (co-translational folding)": "Protein folding", "Lipid vesicle / bilayer": "Lipid bilayer", "Red blood cell": "Red blood cell",
    "T cell": "T cell", "B cell": "B cell", "Neutrophil": "Neutrophil", "Macrophage": "Macrophage", "Platelet": "Platelet", "Fibroblast": "Fibroblast",
    "Neuron": "Neuron", "Cardiomyocyte / muscle fibre": "Cardiac muscle cell", "Stem cell": "Stem cell", "Epithelial cell": "Epithelium",
    "Endothelial cell": "Endothelium", "Cancer cell line": "Immortalised cell line", "Embryo / oocyte / whole organism": "Embryo",
    "Cell nucleus": "Cell nucleus", "Cytoplasm (microrheology)": "Microrheology", "Bacterial cell / adhesin": "Bacterial adhesin",
    "Yeast cell / adhesin": "Yeast", "Virus / capsid": "Capsid", "Sperm cell": "Sperm", "Organelle": "Organelle",
    "Extracellular matrix / hydrogel": "Extracellular matrix", "Polysaccharide / glycan": "Polysaccharide", "Polyethylene glycol (linker)": "Polyethylene glycol",
    "Synthetic polymer / mechanophore": "Mechanophore", "Transcription factor": "Transcription factor", "Ribonuclease H (E. coli)": "RNase H",
    "Protein G B1 domain (GB1)": "Protein G", "Protein L (B1 domain)": "Protein L", "T4 lysozyme": "T4 lysozyme",
    "Titin (Ig/FnIII domains, e.g. I27/I91)": "Titin", "Ubiquitin": "Ubiquitin", "Calmodulin": "Calmodulin", "Green fluorescent protein": "Green fluorescent protein",
    "Talin-1": "Talin (protein)", "Vinculin": "Vinculin", "Filamin A": "FLNA", "von Willebrand factor": "Von Willebrand factor",
    "Cytoplasmic dynein-1": "Dynein", "Kinesin-1": "Kinesin", "Myosin V": "Myosin V", "Myosin VI": "Myosin VI", "RNA polymerase II": "RNA polymerase II",
    "RNA polymerase (bacterial)": "Prokaryotic RNA polymerase", "T7 RNA polymerase": "T7 RNA polymerase", "φ29 DNA polymerase": "Phi29 DNA polymerase",
    "RecBCD": "RecBCD", "RecA recombinase": "RecA", "Cas9 (S. pyogenes)": "Cas9", "Lac repressor": "Lac repressor", "Bacteriorhodopsin": "Bacteriorhodopsin",
}
OBS_UNIT = {"unfolding_force": "pN", "refolding_force": "pN", "rupture_force": "pN", "unbinding_force": "pN", "unzipping_force": "pN",
            "overstretching_force": "pN", "equilibrium_force": "pN", "stall_force": "pN", "adhesion_force": "pN", "tether_force": "pN",
            "step_size": "nm", "persistence_length": "nm", "contour_length_increment": "nm", "distance_to_transition_state": "nm",
            "velocity": "nm/s", "bond_lifetime": "s", "dwell_time": "s", "folding_free_energy": "kBT", "torque": "pN·nm", "molecular_stiffness": "pN/nm"}
CONV = {("nN", "pN"): 1000, ("Å", "nm"): 0.1, ("µm", "nm"): 1000, ("ms", "s"): 0.001, ("µs", "s"): 1e-6, ("kcal/mol", "kBT"): 1 / 0.593,
        ("kJ/mol", "kBT"): 1 / 2.479, ("µm/s", "nm/s"): 1000}


def slug(name):
    s = name.lower().replace("λ", "lambda").replace("φ", "phi").replace("Φ", "phi").replace("α", "alpha").replace("β", "beta")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


def uniprot_info(acc):
    d = get(f"https://rest.uniprot.org/uniprotkb/{acc}.json",
            {"fields": "accession,protein_name,gene_names,organism_name,organism_id,length,cc_function,xref_pdb,xref_alphafolddb"})
    if not isinstance(d, dict) or not d.get("primaryAccession"):
        return None
    func = ""
    for c in d.get("comments", []) or []:
        if c.get("commentType") == "FUNCTION":
            func = " ".join(t.get("value", "") for t in c.get("texts", []))
            break
    func = re.sub(r"\s*\((PubMed|ECO):[^)]*\)", "", func).strip()
    pd = d.get("proteinDescription") or {}
    xr = d.get("uniProtKBCrossReferences") or []
    return {"acc": d["primaryAccession"],
            "protein": ((pd.get("recommendedName") or {}).get("fullName") or {}).get("value"),
            "gene": ((d.get("genes") or [{}])[0].get("geneName") or {}).get("value"),
            "organism": (d.get("organism") or {}).get("scientificName"), "taxon": (d.get("organism") or {}).get("taxonId"),
            "length": (d.get("sequence") or {}).get("length"), "function": func[:1200],
            "n_pdb": sum(1 for x in xr if x.get("database") == "PDB"),
            "alphafold": any(x.get("database") == "AlphaFoldDB" for x in xr)}


def wikidata_titles(accs):
    """UniProt accession -> English Wikipedia title via Wikidata (protein item or the gene item encoding it)."""
    out = {}
    accs = sorted(accs)
    for i in range(0, len(accs), 80):
        vals = " ".join(f'"{a}"' for a in accs[i:i + 80])
        q = ("SELECT ?u ?t WHERE { VALUES ?u {" + vals + "} ?p wdt:P352 ?u . "
             "{ ?a schema:about ?p ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?t } UNION "
             "{ ?g wdt:P688 ?p . ?a schema:about ?g ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?t } }")
        d = get("https://query.wikidata.org/sparql", {"query": q, "format": "json"})
        for b in ((d or {}).get("results") or {}).get("bindings", []):
            out.setdefault(b["u"]["value"], b["t"]["value"])
    return out


def wiki_summary(title):
    d = get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'), safe='')}")
    if not isinstance(d, dict) or d.get("type") not in ("standard",):
        return None
    return {"title": d.get("title"), "extract": (d.get("extract") or "")[:900],
            "url": ((d.get("content_urls") or {}).get("desktop") or {}).get("page")}


def build_systems(recs, verbose=True):
    gaz = {g["name"]: g for g in G}
    uni = load_json(OUT / "uniprot_cache.json", {}) or {}
    # default accession per gazetteer entry
    default_acc = {}
    for g in G:
        lk = g["lookup"]
        if "uniprot" in lk:
            default_acc[g["name"]] = lk["uniprot"]
        elif "gene" in lk:
            hit = uni.get(f"gene|{lk['gene']}|{lk['taxon']}")
            if hit:
                default_acc[g["name"]] = hit["acc"]
    acc_to_sys = {}
    for name, acc in default_acc.items():
        acc_to_sys.setdefault(acc, name)

    agg = defaultdict(lambda: {"records": [], "tech": Counter(), "cls": Counter(), "years": Counter(), "orgs": Counter(),
                               "accs": Counter(), "ds": 0, "results": defaultdict(list)})
    for r in recs:
        names = set()
        for e in r["biological_system"]["entities"]:
            ev = (e.get("evidence") or {}).get("method")
            if ev == "europepmc_textmining":
                continue
            nm = e["name"] if e["name"] in gaz else None
            if not nm:
                for i in e.get("identifiers") or []:
                    if i.get("scheme") == "uniprot" and i["id"] in acc_to_sys:
                        nm = acc_to_sys[i["id"]]
                        break
            if not nm:
                continue
            names.add(nm)
            for i in e.get("identifiers") or []:
                if i.get("scheme") == "uniprot":
                    agg[nm]["accs"][i["id"]] += 1
        for nm in names:
            a = agg[nm]
            p = r["publication"]
            a["records"].append((r["record_id"], p.get("year") or 0, p.get("title"), r["data_availability"]["has_linked_dataset"],
                                 r["technique"]["primary"], r["curation"]["level"]))
            a["tech"][r["technique"]["primary"]] += 1
            for c in r["biological_system"].get("system_class") or []:
                a["cls"][c] += 1
            if p.get("year"):
                a["years"][p["year"]] += 1
            for o in r["biological_system"].get("organisms") or []:
                a["orgs"][o["name"]] += 1
            a["ds"] += bool(r["data_availability"]["has_linked_dataset"])
            # results only attributable when the study involves a single catalogued system
            if len(names) == 1:
                for x in r.get("results") or []:
                    tgt = OBS_UNIT.get(x["quantity"])
                    if not tgt or x.get("value") is None:
                        continue
                    f = 1 if x["unit"] == tgt else CONV.get((x["unit"], tgt))
                    if f:
                        a["results"][x["quantity"]].append((round(x["value"] * f, 4), r["record_id"]))

    keep = {n: a for n, a in agg.items() if len(a["records"]) >= 2}
    if verbose:
        print("systems with >=2 studies:", len(keep))
    accs = {default_acc[n] for n in keep if n in default_acc}
    infos = dict(zip(sorted(accs), pmap(uniprot_info, sorted(accs), workers=6, desc="uniprot function")))
    wd = wikidata_titles(accs)
    titles = {}
    for n in keep:
        acc = default_acc.get(n)
        if n in WIKI_TITLES and WIKI_TITLES[n] is None:
            titles[n] = None  # deliberately no Wikipedia summary (no article on the right concept)
            continue
        titles[n] = WIKI_TITLES.get(n) or (wd.get(acc) if acc else None) or re.sub(r"\s*\(.*?\)", "", n)
    uniq = sorted({t for t in titles.values() if t})
    wiki = dict(zip(uniq, pmap(wiki_summary, uniq, workers=4, desc="wikipedia")))

    out = []
    for n, a in keep.items():
        g = gaz[n]
        lk = g["lookup"]
        acc = default_acc.get(n)
        info = infos.get(acc) if acc else None
        w = wiki.get(titles[n]) if titles[n] else None
        recs_sorted = sorted(a["records"], key=lambda x: (-x[3], -x[1]))
        res = {}
        for q, vals in a["results"].items():
            v = sorted(x[0] for x in vals)
            if v:
                res[q] = {"n": len(v), "min": v[0], "median": round(statistics.median(v), 3), "max": v[-1], "unit": OBS_UNIT[q],
                          "records": [x[1] for x in vals][:12]}
        ids = []
        if acc:
            ids.append({"scheme": "uniprot", "id": acc})
        for s in ("genbank", "rfam", "chebi", "cl", "go"):
            if s in lk:
                ids.append({"scheme": s, "id": lk[s]})
        out.append({
            "slug": slug(n), "name": n, "entity_type": g["entity_type"], "default_class": g["system_class"],
            "n": len(a["records"]), "n_dataset": a["ds"],
            "years": [min(a["years"]), max(a["years"])] if a["years"] else None,
            "by_year": dict(sorted(a["years"].items())),
            "techniques": dict(a["tech"].most_common()), "classes": dict(a["cls"].most_common(6)),
            "organisms": dict(a["orgs"].most_common(6)), "uniprot_seen": dict(a["accs"].most_common(8)),
            "identifiers": ids, "gene": lk.get("gene") or (info or {}).get("gene"), "taxon": lk.get("taxon"),
            "uniprot": info, "wikipedia": w, "results": res,
            "studies": [{"id": x[0], "y": x[1], "t": x[2], "ds": x[3], "tech": x[4], "cur": x[5]} for x in recs_sorted[:400]],
        })
    out.sort(key=lambda s: -s["n"])
    # unique slugs
    seen = Counter()
    for s in out:
        seen[s["slug"]] += 1
        if seen[s["slug"]] > 1:
            s["slug"] += f"-{seen[s['slug']]}"
    return out


if __name__ == "__main__":
    recs = load_jsonl(OUT / "records.jsonl")
    systems = build_systems(recs)
    (WEB / "data" / "systems.js").write_text("SMASH.systems=" + json.dumps(clean_obj(systems), ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print("systems:", len(systems), "with wiki:", sum(1 for s in systems if s["wikipedia"]), "with uniprot fn:", sum(1 for s in systems if (s["uniprot"] or {}).get("function")))
