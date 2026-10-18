"""Methods text for the technique modules.

Reuses step 5 of the SMFS pipeline (``s05_fulltext``) unchanged -- the same
Europe PMC / NCBI fetcher and JATS parser -- so the modules inherit its
behaviour and share its cache instead of downloading the same articles twice.
Only the extracted sections are cached, outside OneDrive
(``%LOCALAPPDATA%/smash-bio-hub-cache/fulltext``).

Per-module state goes where the brief asks (``.cache/modules``): a small index
mapping each module's in-scope articles to the full texts that parsed.
"""
import json
import re
from pathlib import Path

from common import load_json, pmap, save_json
from s05_fulltext import FT_CACHE, fetch_batch

BATCH = 20

# what a "data available" statement usually points at, vs. code-only deposits
DATA_REPO_RX = r"zenodo|figshare|dryad|osf\.io|dataverse|pangaea|empiar|biostudies|4tu|" \
               r"mendeley|metabolights|proteomexchange|massive|geo|sra|pride|pdb|emdb|" \
               r"ebi\.ac\.uk|ncbi\.nlm\.nih\.gov|dandiarchive|mbdb"
CODE_RX = r"github|gitlab|bitbucket|codeocean|huggingface|sourceforge"
REQUEST_RX = r"\b(?:on|upon) (?:reasonable |reasonable_)?request\b|\bavailable from the " \
             r"(?:corresponding |lead )?authors?\b|\bdata are available from"


def index_path(spec, out_dir):
    return Path(out_dir) / f"{spec.slug}_fulltext_index.json"


def build_index(articles, spec, out_dir, max_articles=None):
    """Fetch/parse full texts for the module's in-scope articles; write the index."""
    wanted = sorted({a["pmcid"] for a in articles
                     if a.get("tier") in ("core", "methods") and a.get("pmcid")})
    if max_articles:
        wanted = wanted[:max_articles]
    batches = [wanted[i:i + BATCH] for i in range(0, len(wanted), BATCH)]
    parsed = {}
    for result in pmap(fetch_batch, batches, workers=2, desc=f"{spec.slug} fulltext"):
        if isinstance(result, dict) and "_error" not in result:
            parsed.update(result)
    index = {a["epmc_id"]: a["pmcid"] for a in articles
             if a.get("pmcid") and parsed.get(a["pmcid"])}
    save_json(index_path(spec, out_dir), index)
    return index


def load_index(spec, out_dir):
    return load_json(index_path(spec, out_dir), {}) or {}


def parsed_for(epmc_id, index):
    """The cached parse result for an article, or None when there is no full text."""
    pmcid = (index or {}).get(epmc_id)
    if not pmcid:
        return None
    cached = FT_CACHE / f"{pmcid}.json"
    if not cached.exists():
        return None
    try:
        data = json.loads(cached.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return data if data.get("ok") else None


def methods_for(epmc_id, index):
    return (parsed_for(epmc_id, index) or {}).get("methods_text") or ""


def data_availability(fulltext):
    """Honest availability status: only what the full text actually shows.

    ``fulltext_checked_none`` is the shared-vocabulary status for "we read the
    full text and found no deposit"; abstracts alone stay ``unknown_no_fulltext``.
    """
    if not fulltext:
        return {"status": "unknown_no_fulltext"}
    links = [l for l in fulltext.get("repo_links") or []]
    data_links = [l for l in links if re.search(DATA_REPO_RX, l, re.I)]
    code_links = [l for l in links if re.search(CODE_RX, l, re.I)]
    statements = " ".join((s.get("text") or s.get("title") or "")
                          for s in fulltext.get("data_availability") or [])
    supplement = fulltext.get("supplementary") or []
    row = {"status": "fulltext_checked_none",
           "has_linked_dataset": bool(data_links),
           "has_any_data": bool(data_links or supplement)}
    if data_links:
        row["status"] = "public_repository"
    elif supplement:
        row["status"] = "journal_supplement"
    elif code_links:
        row["status"] = "code_only"
    elif re.search(REQUEST_RX, statements, re.I):
        row["status"] = "on_request"
    if statements:
        row["statement"] = " ".join(statements.split())[:500]
    return row