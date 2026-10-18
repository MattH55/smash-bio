"""Europe PMC harvest for a technique module.

Reuses the hub's cached/throttled HTTP layer but paces itself at half the SMFS
rate (two agents may share the API budget). The harvest is resumable: results
are merged into the module's JSONL after every query tag, and every HTTP
response is cached on disk by ``common.get``.
"""
import time
from pathlib import Path

import common
from common import save_jsonl
from modules.base import hub_dir


EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
RATE_FACTOR = 2.0  # half the existing pipeline's request rate
_MIN_INTERVAL = {
    "www.ebi.ac.uk": 0.08,
    "api.datacite.org": 0.12,
    "api.scholexplorer.openaire.eu": 0.2,
    "zenodo.org": 0.7,
    "api.figshare.com": 0.3,
    "api.dandiarchive.org": 0.3,
}
_last = {}


def polite_get(url, params=None, as_json=True):
    """A GET that leaves twice the normal gap between requests to the same host."""
    host = url.split("/")[2]
    wait = _MIN_INTERVAL.get(host, 0.1) * RATE_FACTOR - (time.time() - _last.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    body = common.get(url, params=params, as_json=as_json)
    _last[host] = time.time()
    return body


def slim(result):
    return {
        "epmc_id": result.get("id"),
        "source": result.get("source"),
        "pmid": result.get("pmid"),
        "pmcid": result.get("pmcid"),
        "doi": common.norm_doi(result.get("doi")),
        "title": result.get("title"),
        "authors": [a.get("fullName") for a in (result.get("authorList") or {}).get("author", []) if a.get("fullName")][:25],
        "journal": (result.get("journalInfo") or {}).get("journal", {}).get("title") or result.get("bookOrReportDetails", {}).get("publisher"),
        "year": int(result["pubYear"]) if str(result.get("pubYear", "")).isdigit() else None,
        "abstract": result.get("abstractText"),
        "pub_types": (result.get("pubTypeList") or {}).get("pubType", []),
        "keywords": (result.get("keywordList") or {}).get("keyword", []),
        "mesh": [m.get("descriptorName") for m in (result.get("meshHeadingList") or {}).get("meshHeading", [])],
        "is_oa": result.get("isOpenAccess") == "Y",
        "in_pmc": result.get("inPMC") == "Y",
    }


def _dedupe(rows):
    rank = {"MED": 0, "PMC": 1, "PPR": 2}
    rows = sorted(rows, key=lambda r: rank.get(r.get("source"), 3))
    seen, out = {}, []
    for row in rows:
        key = row.get("doi") or row.get("epmc_id")
        if key in seen:
            seen[key]["query_tags"] = sorted(set(seen[key]["query_tags"] + row["query_tags"]))
            continue
        seen[key] = row
        out.append(row)
    return out


def harvest(spec, min_year=1986, max_year=2026, page_size=1000, limit=None, out_path=None):
    """Harvest one module. Returns the deduped article list and writes the JSONL."""
    out_path = Path(out_path or (hub_dir() / "out" / f"{spec.slug}_articles_raw.jsonl"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    by_id = {}
    for tag, fragment in spec.harvest_queries.items():
        query = (f"({fragment}) AND (SRC:MED OR SRC:PMC OR SRC:PPR) "
                 f"AND PUB_YEAR:[{min_year} TO {max_year}]")
        cursor, fetched, page = "*", 0, 0
        while True:
            data = polite_get(EPMC, {"query": query, "format": "json", "pageSize": page_size,
                                     "resultType": "core", "cursorMark": cursor})
            results = (data or {}).get("resultList", {}).get("result", [])
            if not results:
                break
            for result in results:
                row = slim(result)
                if not row["epmc_id"]:
                    continue
                if row["epmc_id"] in by_id:
                    by_id[row["epmc_id"]]["query_tags"].append(tag)
                else:
                    row["query_tags"] = [tag]
                    by_id[row["epmc_id"]] = row
            page += 1
            fetched += len(results)
            next_cursor = (data or {}).get("nextCursorMark")
            print(f"  {spec.slug}/{tag}: page {page} ({fetched} hits)", flush=True)
            if not next_cursor or next_cursor == cursor or (limit and fetched >= limit):
                break
            cursor = next_cursor
        save_jsonl(out_path, _dedupe(list(by_id.values())))
    rows = _dedupe(list(by_id.values()))
    save_jsonl(out_path, rows)
    return rows