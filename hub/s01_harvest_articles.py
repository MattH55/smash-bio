"""Step 1 - harvest candidate force-spectroscopy articles from Europe PMC.

Each query carries a technique tag; a record hit by several queries keeps all
tags (used later as technique evidence). Output: out/articles_raw.jsonl
"""
from common import OUT, get, load_json, norm_doi, save_jsonl

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def ta(*phrases):
    return "(" + " OR ".join(f'TITLE_ABS:"{p}"' for p in phrases) + ")"


QUERIES = {
    "optical_tweezers": ta("optical tweezers", "optical tweezer", "optical trap", "optical traps", "optical trapping",
                           "laser tweezers", "laser trap", "laser trapping", "dual-trap", "dual-beam optical trap",
                           "C-Trap", "optical pincers", "photonic force microscope", "holographic optical tweezers"),
    "magnetic_tweezers": ta("magnetic tweezers", "magnetic tweezer", "magnetic trap", "magnetic force spectroscopy",
                            "magnetic pulling", "magnetic force clamp", "magnetic trapping"),
    "torque_tweezers": ta("magneto-optical tweezers", "torque tweezers", "magnetic torque tweezers",
                          "freely orbiting magnetic tweezers", "angular optical trap", "optical torque wrench",
                          "electromagnetic torque tweezers"),
    "afm_smfs": ta("single-molecule force spectroscopy", "single molecule force spectroscopy", "SMFS",
                   "AFM-based force spectroscopy", "AFM force spectroscopy", "AFM pulling", "AFM-SMFS",
                   "single-molecule AFM", "atomic force microscope-based single-molecule",
                   "single-cell force spectroscopy", "dynamic force spectroscopy", "high-speed force spectroscopy"),
    "force_spectroscopy_generic": ta("force spectroscopy"),
    "acoustic_force_spectroscopy": ta("acoustic force spectroscopy", "acoustic force", "acoustic tweezers"),
    "centrifuge_force": ta("centrifuge force microscope", "centrifugal force microscope", "centrifuge force microscopy",
                           "centrifugal force microscopy", "centrifugal force spectroscopy", "centrifuge force spectroscopy"),
    "nanopore_force": ta("nanopore force spectroscopy", "nanopore tweezers", "SPRNT", "nanopore unzipping",
                         "nanopore unfolding", "nanopore-based force") + ' OR (TITLE_ABS:"nanopore" AND (TITLE_ABS:"unzipping" OR TITLE_ABS:"force spectroscopy" OR TITLE_ABS:"co-translocational unfolding"))',
    "hydrodynamic_stretching": ta("flow stretching", "flow-stretching", "flow-stretched", "DNA curtains", "DNA curtain",
                                  "hydrodynamic stretching", "hydrodynamic force", "flow-induced stretching",
                                  "tethered bead flow", "single-molecule flow stretching", "flow-extension"),
    "biomembrane_force_probe": ta("biomembrane force probe", "micropipette aspiration adhesion frequency",
                                  "micropipette adhesion frequency"),
    "tension_sensors": ta("tension gauge tether", "molecular tension sensor", "molecular tension probe",
                          "DNA tension probe", "DNA-based tension", "molecular force sensor", "FRET-based tension sensor",
                          "molecular tension fluorescence microscopy", "DNA origami force clamp", "nanoscopic force clamp",
                          "DNA force gauge"),
    "microneedle": ta("glass microneedle", "microneedle manipulation") + ' AND (TITLE_ABS:"single molecule" OR TITLE_ABS:"single-molecule")',
    "generic_smfs": ta("force-extension", "force extension curve", "overstretching", "DNA unzipping", "mechanical unfolding",
                       "mechanical unzipping", "forced unfolding", "single-molecule mechanics", "single-molecule manipulation",
                       "catch bond", "catch-bond", "rupture force", "force-clamp", "force clamp", "single-molecule stretching",
                       "stall force", "mechanochemistry single molecule", "mechanical stability of proteins",
                       "force-dependent unfolding", "force-dependent unbinding"),
}

FILTER = " AND (SRC:MED OR SRC:PMC OR SRC:PPR) AND PUB_YEAR:[1986 TO 2026]"


def harvest(tag, q):
    rows, cursor = [], "*"
    while True:
        d = get(EPMC, {"query": q + FILTER, "format": "json", "pageSize": 1000,
                       "resultType": "core", "cursorMark": cursor})
        if not d:
            print("  !! failed page", tag, cursor)
            break
        res = d.get("resultList", {}).get("result", [])
        rows.extend(res)
        nxt = d.get("nextCursorMark")
        if not res or not nxt or nxt == cursor:
            break
        cursor = nxt
    print(f"{tag}: {len(rows)} (hitCount {d.get('hitCount') if d else '?'})", flush=True)
    return rows


def slim(r):
    """Keep only fields we need from the Europe PMC core record."""
    ji = r.get("journalInfo") or {}
    j = ji.get("journal") or {}
    authors = [a.get("fullName") for a in (r.get("authorList") or {}).get("author", []) if a.get("fullName")]
    affs = []
    for a in (r.get("authorList") or {}).get("author", [])[:3]:
        for af in (a.get("authorAffiliationDetailsList") or {}).get("authorAffiliation", []):
            if af.get("affiliation"):
                affs.append(af["affiliation"])
    return {
        "epmc_id": f"{r.get('source')}:{r.get('id')}",
        "source": r.get("source"),
        "pmid": r.get("pmid"),
        "pmcid": r.get("pmcid"),
        "doi": norm_doi(r.get("doi")),
        "title": r.get("title"),
        "abstract": r.get("abstractText"),
        "authors": authors,
        "affiliations": affs[:4],
        "journal": j.get("title") or (r.get("bookOrReportDetails") or {}).get("publisher") or r.get("journalTitle"),
        "year": int(r["pubYear"]) if r.get("pubYear", "").isdigit() else None,
        "pub_date": r.get("firstPublicationDate"),
        "pub_types": (r.get("pubTypeList") or {}).get("pubType", []),
        "keywords": (r.get("keywordList") or {}).get("keyword", []),
        "mesh": [m.get("descriptorName") for m in (r.get("meshHeadingList") or {}).get("meshHeading", [])],
        "is_oa": r.get("isOpenAccess") == "Y",
        "in_pmc": r.get("inPMC") == "Y",
        "has_tm_accessions": r.get("hasTMAccessionNumbers") == "Y",
        "tm_accession_types": (r.get("tmAccessionTypeList") or {}).get("accessionType", []),
        "has_suppl": r.get("hasSuppl") == "Y",
        "has_data_links": r.get("hasDbCrossReferences") == "Y" or r.get("hasLabsLinks") == "Y",
        "db_xrefs": (r.get("dbCrossReferenceList") or {}).get("dbName", []),
        "cited_by": r.get("citedByCount", 0),
        "license": r.get("license"),
        "grants": [g.get("agency") for g in (r.get("grantsList") or {}).get("grant", []) if g.get("agency")][:6],
        "lang": r.get("language"),
    }


def seed_dois():
    """DOIs already in the legacy SMASH-BIO dataset and OT DOI list (kept as seeds)."""
    import csv, re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    dois = set()
    js = (root / "legacy_site_v2/data.js").read_text(encoding="utf-8") if (root / "legacy_site_v2/data.js").exists() else ""
    for m in re.finditer(r'"doi":\s*"([^"]+)"', js):
        dois.add(norm_doi(m.group(1)))
    p = root / "OT_experiments-dois.csv"
    if p.exists():
        for row in csv.reader(open(p, encoding="utf-8", errors="ignore")):
            for c in row:
                if c.strip().lower().startswith(("10.", "https://doi")):
                    dois.add(norm_doi(c))
    return {d for d in dois if d}


def main():
    by_id = {}
    for tag, q in QUERIES.items():
        for r in harvest(tag, q):
            s = slim(r)
            if s["epmc_id"] in by_id:
                by_id[s["epmc_id"]]["query_tags"].append(tag)
            else:
                s["query_tags"] = [tag]
                by_id[s["epmc_id"]] = s
    # seeds: legacy DOIs not already harvested
    have = {r["doi"] for r in by_id.values() if r["doi"]}
    missing = sorted(seed_dois() - have)
    print("legacy seed DOIs not yet harvested:", len(missing))
    for i in range(0, len(missing), 50):
        chunk = missing[i:i + 50]
        q = "(" + " OR ".join(f'DOI:"{d}"' for d in chunk) + ")"
        d = get(EPMC, {"query": q, "format": "json", "pageSize": 1000, "resultType": "core"})
        for r in (d or {}).get("resultList", {}).get("result", []):
            s = slim(r)
            if s["epmc_id"] not in by_id:
                s["query_tags"] = ["legacy_seed"]
                by_id[s["epmc_id"]] = s
    # de-duplicate preprint/published pairs by DOI (keep MED over PPR)
    rows = list(by_id.values())
    rank = {"MED": 0, "PMC": 1, "PPR": 2}
    rows.sort(key=lambda r: rank.get(r["source"], 3))
    seen, out = {}, []
    for r in rows:
        k = r["doi"] or r["epmc_id"]
        if k in seen:
            seen[k]["query_tags"] = sorted(set(seen[k]["query_tags"] + r["query_tags"]))
            continue
        seen[k] = r
        out.append(r)
    save_jsonl(OUT / "articles_raw.jsonl", out)
    print("total unique candidate articles:", len(out))


if __name__ == "__main__":
    main()
