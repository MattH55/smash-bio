"""Step 2 - harvest force-spectroscopy datasets/software from data repositories.

DataCite indexes Zenodo, Figshare, Dryad, Mendeley Data, OSF, Harvard/other
Dataverses, 4TU.ResearchData, ETH Research Collection, etc. We query it with
technique phrases, keep Dataset/Software/Collection/Other deposits, and record
their related identifiers (article DOIs / PMIDs) for linking in step 3.
Output: out/datasets_raw.jsonl
"""
import re

from common import OUT, get, norm_doi, save_jsonl

DC = "https://api.datacite.org/dois"

PHRASES = {
    "optical_tweezers": ["optical tweezers", "optical tweezer", "optical trap", "optical trapping", "laser tweezers",
                         "dual-trap", "C-Trap", "lumicks", "pylake", "dual optical trap"],
    "magnetic_tweezers": ["magnetic tweezers", "magnetic tweezer", "magnetic trap", "magnetic force spectroscopy"],
    "torque_tweezers": ["torque tweezers", "magneto-optical tweezers", "angular optical trap"],
    "afm_smfs": ["single-molecule force spectroscopy", "single molecule force spectroscopy", "SMFS",
                 "AFM force spectroscopy", "AFM-SMFS", "force spectroscopy", "single-cell force spectroscopy",
                 "dynamic force spectroscopy"],
    "acoustic_force_spectroscopy": ["acoustic force spectroscopy"],
    "centrifuge_force": ["centrifuge force microscope", "centrifugal force microscope", "centrifuge force microscopy"],
    "nanopore_force": ["nanopore tweezers", "nanopore force spectroscopy", "SPRNT"],
    "hydrodynamic_stretching": ["DNA curtains", "flow stretching", "flow-stretching", "hydrodynamic stretching"],
    "biomembrane_force_probe": ["biomembrane force probe"],
    "tension_sensors": ["tension gauge tether", "molecular tension sensor", "molecular tension probe", "DNA tension probe"],
    "generic_smfs": ["force-extension", "force extension curves", "DNA overstretching", "DNA unzipping",
                     "mechanical unfolding", "catch bond", "rupture force", "force clamp", "single-molecule manipulation",
                     "single-molecule mechanics", "stall force", "kymograph optical"],
}

KEEP_TYPES = {"Dataset", "Software", "Collection", "Other", "Workflow", "Model", "Image", "Audiovisual",
              "ComputationalNotebook", "PhysicalObject", None}


def harvest_phrase(phrase):
    rows, url = [], None
    params = {"query": f'"{phrase}"', "page[size]": 1000, "page[cursor]": 1,
              "affiliation": "false", "disable-facets": "true"}
    d = get(DC, params)
    while d and d.get("data"):
        rows.extend(d["data"])
        nxt = (d.get("links") or {}).get("next")
        if not nxt or len(rows) >= 20000:
            break
        d = get(nxt)
    return rows


IMG_TITLE = re.compile(r"^(supplementary )?(figure|fig\.?|table|movie|video|appendix|s\d+ (fig|table|movie|video|text|appendix))\b", re.I)
JOURNAL_MIRRORS = ("public library of science", "plos", "frontiers", "taylor & francis", "sage", "the royal society",
                   "american chemical society", "acs", "royal society of chemistry", "optica", "wiley", "springer",
                   "biophysical society", "elife", "pnas", "national academy of sciences", "f1000", "cell press")


def slim(item, tag, phrase):
    a = item["attributes"]
    titles = [t.get("title") for t in a.get("titles", []) if t.get("title")]
    desc = " ".join(d.get("description", "") or "" for d in a.get("descriptions", []) if isinstance(d.get("description"), str))
    types = a.get("types") or {}
    rel = []
    for r in a.get("relatedIdentifiers") or []:
        rid, rtype = r.get("relatedIdentifier"), r.get("relatedIdentifierType")
        if not rid:
            continue
        if rtype == "DOI":
            rid = norm_doi(rid)
        elif rtype == "URL" and "doi.org/" in rid.lower():
            rid, rtype = norm_doi(rid), "DOI"
        rel.append({"id": rid, "type": rtype, "relation": r.get("relationType"),
                    "resource_type": r.get("resourceTypeGeneral")})
    publisher = a.get("publisher") if isinstance(a.get("publisher"), str) else (a.get("publisher") or {}).get("name")
    t0 = titles[0] if titles else ""
    rtg = types.get("resourceTypeGeneral")
    mirror = bool(IMG_TITLE.search(t0)) or (publisher or "").lower().startswith(JOURNAL_MIRRORS)
    return {
        "doi": norm_doi(a.get("doi")),
        "title": t0,
        "description": desc[:3000],
        "creators": [c.get("name") for c in a.get("creators", []) if c.get("name")][:30],
        "publisher": publisher,
        "year": a.get("publicationYear"),
        "resource_type": rtg,
        "resource_type_detail": types.get("resourceType"),
        "subjects": [s.get("subject") for s in a.get("subjects", []) if s.get("subject")][:20],
        "url": a.get("url"),
        "sizes": a.get("sizes", []),
        "formats": a.get("formats", []),
        "rights": [r.get("rightsIdentifier") or r.get("rights") for r in a.get("rightsList", [])],
        "related": rel,
        "client": (item.get("relationships", {}).get("client", {}).get("data") or {}).get("id"),
        "version_of": a.get("versionOfCount"),
        "journal_supplement_mirror": mirror,
        "query_tags": [tag],
        "matched_phrases": [phrase],
    }


def main():
    by_doi = {}
    for tag, phrases in PHRASES.items():
        for ph in phrases:
            items = harvest_phrase(ph)
            kept = 0
            for it in items:
                a = it.get("attributes", {})
                rtg = (a.get("types") or {}).get("resourceTypeGeneral")
                if rtg not in KEEP_TYPES:
                    continue
                s = slim(it, tag, ph)
                if not s["doi"]:
                    continue
                if s["doi"] in by_doi:
                    o = by_doi[s["doi"]]
                    o["query_tags"] = sorted(set(o["query_tags"] + [tag]))
                    o["matched_phrases"] = sorted(set(o["matched_phrases"] + [ph]))
                else:
                    by_doi[s["doi"]] = s
                    kept += 1
            print(f"{tag:28s} {ph!r:45s} hits={len(items):6d} new={kept}", flush=True)
    rows = list(by_doi.values())
    save_jsonl(OUT / "datasets_raw.jsonl", rows)
    print("unique deposits:", len(rows))


if __name__ == "__main__":
    main()
