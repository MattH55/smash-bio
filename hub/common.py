"""Shared helpers for the SMASH-BIO force-spectroscopy hub pipeline.

Every HTTP GET is cached on disk (keyed by URL) so the pipeline can be re-run
cheaply and incrementally. Delete hub/cache/http to force a refresh.
"""
import hashlib
import html
import json
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode

import requests

HUB = Path(__file__).resolve().parent
CACHE = HUB / "cache"
# The raw HTTP cache is large; keep it outside OneDrive by default.
HTTP_CACHE = Path(os.environ.get("SMASH_HUB_CACHE",
                                 Path(os.environ.get("LOCALAPPDATA", HUB)) / "smash-bio-hub-cache" / "http"))
OUT = HUB / "out"
for p in (CACHE, HTTP_CACHE, OUT):
    p.mkdir(parents=True, exist_ok=True)

UA = "SMASH-BIO-hub/1.0 (mailto:mhalma@opensourcemed.info; force-spectroscopy data hub)"
_local = threading.local()
_host_locks = {}
_host_last = {}
_MIN_INTERVAL = {  # seconds between requests per host
    "www.ebi.ac.uk": 0.08,
    "api.datacite.org": 0.12,
    "api.scholexplorer.openaire.eu": 0.2,
    "zenodo.org": 0.7,
    "api.figshare.com": 0.3,
    "rest.uniprot.org": 0.05,
    "eutils.ncbi.nlm.nih.gov": 0.4,
    "query.wikidata.org": 1.0,
    "en.wikipedia.org": 0.2,
    "api.crossref.org": 0.1,
}


def _session():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = UA
        s.trust_env = False  # skip slow per-request .netrc / proxy lookups
        _local.s = s
    return s


def _throttle(url):
    host = url.split("/")[2]
    lock = _host_locks.setdefault(host, threading.Lock())
    with lock:
        wait = _MIN_INTERVAL.get(host, 0.1) - (time.time() - _host_last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _host_last[host] = time.time()


def cache_path(url):
    h = hashlib.sha1(url.encode()).hexdigest()
    return HTTP_CACHE / h[:2] / (h + ".json")


def get(url, params=None, as_json=True, retries=5, timeout=90, use_cache=True):
    """GET with on-disk cache. Returns parsed JSON (or text), None on 404."""
    if params:
        url = url + ("&" if "?" in url else "?") + urlencode(params, doseq=True)
    cp = cache_path(url)
    if use_cache and cp.exists():
        try:
            d = json.loads(cp.read_text(encoding="utf-8"))
            return d["body"]
        except Exception:
            pass
    body = None
    for attempt in range(retries):
        _throttle(url)
        try:
            r = _session().get(url, timeout=timeout)
            if r.status_code == 404:
                body = None
                break
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt + random.random())
                continue
            r.raise_for_status()
            body = r.json() if as_json else r.text
            break
        except (requests.RequestException, ValueError):
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt + random.random())
    else:
        return None
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps({"url": url, "body": body}), encoding="utf-8")
    return body


def pmap(fn, items, workers=8, desc=""):
    """Parallel map preserving input order, with simple progress output."""
    items = list(items)
    out = [None] * len(items)
    done = 0
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fn, it): i for i, it in enumerate(items)}
        for f in as_completed(futs):
            i = futs[f]
            try:
                out[i] = f.result()
            except Exception as e:  # keep going; record the failure
                out[i] = {"_error": repr(e)}
            done += 1
            if desc and (done % 250 == 0 or done == len(items)):
                print(f"  {desc}: {done}/{len(items)}", flush=True)
    return out


def norm_doi(d):
    if not d:
        return None
    d = d.strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/", "https://dx.doi.org/", "doi:"):
        if d.startswith(p):
            d = d[len(p):]
    return d.strip().rstrip(".") or None


_INLINE_TAG = re.compile(r"</?(?:i|b|em|strong|sub|sup|u|sc|scp|italic|bold|span|p|br|mml:[a-z]+|inline-formula|named-content)(?:\s[^<>]*)?/?>", re.I)


def clean_text(s):
    """Decode HTML entities (&lt;i&gt;, &amp;, &apos;) and drop inline markup tags, keeping the text.

    Only a fixed list of inline tags is removed, so a literal comparison such as "<5 pN" survives.
    Applied to every string written to the website (s07, s09): the site escapes text itself, so
    escaped entities would otherwise show up literally ("&apos;").
    """
    if not isinstance(s, str) or ("&" not in s and "<" not in s):
        return s
    out = s
    for _ in range(2):  # double-escaped sources ("&amp;lt;i&amp;gt;")
        out = html.unescape(out)
    return re.sub(r"\s{2,}", " ", _INLINE_TAG.sub("", out))


def clean_obj(o):
    if isinstance(o, str):
        return clean_text(o)
    if isinstance(o, dict):
        return {k: clean_obj(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean_obj(v) for v in o]
    return o


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def save_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, obj, indent=None):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")
