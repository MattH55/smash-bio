"""Step 4 - discover data deposits and text-mined entities for in-scope articles.

Sources (all recorded with provenance in `linked_by`):
  epmc_datalinks   Europe PMC data-links (BioStudies, PDBe, EMPIAR, Scholix-fed repository links...)
  epmc_annotations Europe PMC text-mined Accession Numbers / Organisms / Gene_Proteins / Experimental Methods
  scholix          OpenAIRE ScholeXplorer article->dataset/software links (Crossref + DataCite + EBI + OpenAIRE)
  datacite_related DataCite deposits whose relatedIdentifiers point to the article DOI
Output: out/links.json  {epmc_id: {...}}
"""
import re
import sys

from common import OUT, get, load_json, load_jsonl, norm_doi, pmap, save_json

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
ANN = "https://www.ebi.ac.uk/europepmc/annotations_api/annotationsByArticleIds"
SCHOLIX = "https://api.scholexplorer.openaire.eu/v3/Links"
DC = "https://api.datacite.org/dois"

DATA_SCHEMES = {"doi", "url", "handle", "ark"}
SECTION_OK = re.compile(r"abstract|method|result|data|availab|supplement|material|figure|table|title|caption|discussion", re.I)


def datalinks(a):
    src, ext = a["epmc_id"].split(":", 1)
    d = get(f"{EPMC}/{src}/{ext}/datalinks", {"format": "json"})
    out = []
    for cat in ((d or {}).get("dataLinkList") or {}).get("Category", []):
        for sec in cat.get("Section", []):
            for ln in (sec.get("Linklist") or {}).get("Link", []):
                tgt = ln.get("Target") or {}
                ident = tgt.get("Identifier") or {}
                out.append({
                    "category": cat.get("Name"),
                    "id": ident.get("ID"), "scheme": ident.get("IDScheme"), "url": ident.get("IDURL"),
                    "title": tgt.get("Title"), "publisher": (tgt.get("Publisher") or {}).get("Name"),
                    "target_type": (tgt.get("Type") or {}).get("Name"),
                    "relation": (ln.get("RelationshipType") or {}).get("Name"),
                    "obtained_by": ln.get("ObtainedBy") or sec.get("ObtainedBy"),
                    "provider": (ln.get("LinkProvider") or {}).get("Name"),
                })
    return out


def annotations(batch):
    ids = ",".join(f"{a['epmc_id'].split(':')[0]}:{a['epmc_id'].split(':')[1]}" for a in batch)
    d = get(ANN, {"articleIds": ids, "format": "JSON"}) or []
    res = {}
    for art in d:
        key = f"{art.get('source')}:{art.get('extId')}"
        ents = {}
        for an in art.get("annotations", []):
            typ = an.get("type")
            if typ not in ("Accession Numbers", "Organisms", "Gene_Proteins", "Experimental Methods", "Chemicals", "Diseases", "Resources"):
                continue
            section = an.get("section") or ""
            uri = (an.get("tags") or [{}])[0].get("uri")
            k = (typ, (an.get("exact") or "").strip(), uri)
            e = ents.setdefault(k, {"type": typ, "text": k[1], "uri": uri, "sections": set(), "n": 0})
            e["n"] += 1
            e["sections"].add(section.split(" (")[0])
        res[key] = [{**e, "sections": sorted(e["sections"])} for e in ents.values()]
    return res


def scholix(a):
    if not a.get("doi"):
        return []
    d = get(SCHOLIX, {"sourcePid": a["doi"]})
    out = []
    for r in (d or {}).get("result", []):
        tgt = r.get("target") or {}
        ttype = (tgt.get("Type") or tgt.get("type") or "").lower()
        if ttype not in ("dataset", "software", "other"):
            continue
        ids = tgt.get("Identifier") or tgt.get("identifier") or []
        cands = [{"id": i.get("ID") or i.get("id"), "scheme": (i.get("IDScheme") or i.get("schema") or "").lower(),
                  "url": i.get("IDURL") or i.get("url")} for i in ids]
        # prefer a resolvable DOI, then any URL; OpenAIRE-internal ids ("50|...") are a last resort
        cands.sort(key=lambda c: (c["scheme"] != "doi", not str(c["url"] or "").startswith("http"), str(c["id"] or "").startswith("50|")))
        pid = cands[0] if cands else {}
        if pid.get("scheme") == "doi":
            pid["id"] = norm_doi(pid["id"])
        pubs = tgt.get("Publisher") or tgt.get("publisher") or []
        out.append({**pid, "title": tgt.get("Title") or tgt.get("title"), "target_type": ttype,
                    "publisher": (pubs[0].get("name") if pubs and isinstance(pubs[0], dict) else None),
                    "relation": ((r.get("RelationshipType") or r.get("relationshipType") or {}).get("Name")
                                 or (r.get("RelationshipType") or r.get("relationshipType") or {}).get("name")),
                    "providers": [p.get("name") for p in (r.get("LinkProvider") or r.get("linkProvider") or []) if isinstance(p, dict)]})
    return out


def datacite_related(a):
    doi = a.get("doi")
    if not doi:
        return []
    variants = {doi, doi.upper(), f"https://doi.org/{doi}"}
    q = " OR ".join(f'relatedIdentifiers.relatedIdentifier:"{v}"' for v in variants)
    d = get(DC, {"query": q, "page[size]": 100, "disable-facets": "true", "affiliation": "false"})
    out = []
    for it in (d or {}).get("data", []):
        at = it.get("attributes", {})
        types = at.get("types") or {}
        rel = [r.get("relationType") for r in at.get("relatedIdentifiers") or []
               if norm_doi(r.get("relatedIdentifier") or "") == doi]
        out.append({"id": norm_doi(at.get("doi")), "scheme": "doi", "url": at.get("url"),
                    "title": (at.get("titles") or [{}])[0].get("title"),
                    "publisher": at.get("publisher") if isinstance(at.get("publisher"), str) else (at.get("publisher") or {}).get("name"),
                    "target_type": types.get("resourceTypeGeneral"), "relation": rel[0] if rel else None,
                    "year": at.get("publicationYear"), "sizes": at.get("sizes"), "formats": at.get("formats"),
                    "rights": [r.get("rightsIdentifier") or r.get("rights") for r in at.get("rightsList", [])]})
    return out


def main():
    arts = [a for a in load_jsonl(OUT / "articles_classified.jsonl") if a["tier"] in ("core", "methods")]
    print("articles to link:", len(arts))
    links = load_json(OUT / "links.json", {}) or {}
    todo = arts
    steps = sys.argv[1:] or ["datalinks", "annotations", "scholix", "datacite"]
    if "datalinks" in steps:
        res = pmap(datalinks, todo, workers=6, desc="epmc datalinks")
        for a, r in zip(todo, res):
            links.setdefault(a["epmc_id"], {})["epmc_datalinks"] = r if isinstance(r, list) else []
        save_json(OUT / "links.json", links)
    if "annotations" in steps:
        batches = [todo[i:i + 8] for i in range(0, len(todo), 8)]
        res = pmap(annotations, batches, workers=4, desc="epmc annotations (batches)")
        for r in res:
            if isinstance(r, dict) and "_error" not in r:
                for k, v in r.items():
                    links.setdefault(k, {})["epmc_annotations"] = v
        save_json(OUT / "links.json", links)
    if "scholix" in steps:
        res = pmap(scholix, todo, workers=4, desc="scholix")
        for a, r in zip(todo, res):
            links.setdefault(a["epmc_id"], {})["scholix"] = r if isinstance(r, list) else []
        save_json(OUT / "links.json", links)
    if "datacite" in steps:
        res = pmap(datacite_related, todo, workers=4, desc="datacite related")
        for a, r in zip(todo, res):
            links.setdefault(a["epmc_id"], {})["datacite_related"] = r if isinstance(r, list) else []
        save_json(OUT / "links.json", links)
    n = sum(1 for v in links.values() if v.get("scholix") or v.get("datacite_related") or
            any(l.get("target_type") == "dataset" for l in v.get("epmc_datalinks", [])))
    print("articles with any data link:", n)


if __name__ == "__main__":
    main()
