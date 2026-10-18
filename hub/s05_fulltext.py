"""Step 5 - parse open-access full text (Europe PMC JATS XML) for in-scope articles.

Extracts per article:
  data_availability  statement text (+ code availability)
  repo_links         repository DOIs/URLs found anywhere outside the reference list
  supplementary      supplementary-material file names / captions (journal-hosted data)
  methods_text       Methods / Materials section text (trimmed) for parameter extraction
Only the extracted pieces are cached (outside OneDrive), never the whole XML.
Output: <cache>/fulltext/<PMCID>.json and out/fulltext_index.json
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from common import HTTP_CACHE, OUT, get, load_jsonl, pmap, save_json

FT_CACHE = HTTP_CACHE.parent / "fulltext"
FT_CACHE.mkdir(parents=True, exist_ok=True)
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"

DA_TITLE = re.compile(r"data (and (code|software|materials?) )?(availability|access|sharing|deposition)|availability of (data|materials)|"
                      r"code availability|software availability|accession (numbers?|codes?)|data and materials|resource availability|"
                      r"lead contact|materials availability|deposited data", re.I)
METHODS_TITLE = re.compile(r"method|materials|experimental (procedures|section|setup|details)|procedures|instrumentation|"
                           r"optical (tweezers|trap)|magnetic tweezers|force spectroscopy|data analysis|sample preparation|"
                           r"star\s*\+?\s*methods", re.I)

REPO_RX = re.compile(
    r"(10\.5281/zenodo\.\d+|10\.6084/m9\.figshare\.[\w.]+|10\.5061/dryad\.[\w.]+|10\.17632/[\w.]+|10\.17605/osf\.io/\w+|"
    r"10\.4121/[\w.-]+|10\.7910/dvn/\w+|10\.18419/darus-\d+|10\.25378/[\w.]+|10\.5878/[\w.-]+|10\.6019/[\w.-]+|"
    r"10\.3929/ethz-[\w-]+|10\.15131/shef\.data\.[\w.]+|10\.5522/04/[\w.]+|10\.5287/bodleian:\w+|10\.14469/hpc/\d+|"
    r"10\.34973/[\w.-]+|10\.48420/[\w.]+|10\.25405/data\.[\w.]+|10\.15125/bath-\d+|10\.6075/j0\w+|10\.1594/pangaea\.\d+|"
    r"zenodo\.org/(records?|deposit|communities)/[\w./-]+|figshare\.com/[\w./-]+|datadryad\.org/[\w./?=:-]+|osf\.io/\w{5}\b|"
    r"github\.com/[\w.-]+/[\w.-]+|gitlab\.[\w.]+/[\w./-]+|data\.mendeley\.com/datasets/[\w./-]+|dataverse\.[\w.]+/[\w./?=:-]+|"
    r"ebi\.ac\.uk/biostudies/[\w./-]+|ebi\.ac\.uk/empiar/[\w./-]+|data\.4tu\.nl/[\w./-]+|researchdata\.[\w.]+/[\w./-]+|"
    r"sbgrid\.org/[\w./-]+|bitbucket\.org/[\w./-]+|codeocean\.com/[\w./-]+|huggingface\.co/datasets/[\w./-]+|"
    r"\b(EMD-\d{4,5}|EMPIAR-\d{5}|S-BSST\d+|S-BIAD\d+)\b|\bPDB (ID|code|entry|accession)?s?:?\s*([0-9][A-Za-z0-9]{3})\b)", re.I)


def text_of(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


def strip_ns(xml):
    xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', "", xml)
    xml = re.sub(r"<(/?)\w+:(\w+)", r"<\1\2", xml)
    # attribute prefixes (xlink:href, xml:lang ...) -> xlink_href so the tree parses without namespaces
    return re.sub(r"(\s)([A-Za-z]+):([\w-]+)=", r"\1\2_\3=", xml)


def parse(xml):
    try:
        root = ET.fromstring(strip_ns(xml))
    except ET.ParseError:
        return None
    res = {"data_availability": [], "repo_links": [], "supplementary": [], "methods_text": "", "has_methods": False}
    # data availability: sections, notes, custom-meta, fn
    for sec in root.iter("sec"):
        title = text_of(sec.find("title"))
        stype = sec.get("sec-type") or ""
        if DA_TITLE.search(title) or "availability" in stype or "data-availability" in stype:
            res["data_availability"].append({"title": title or stype, "text": text_of(sec)[:4000]})
    for tag in ("notes", "fn", "custom-meta"):
        for el in root.iter(tag):
            t = text_of(el)
            ttl = text_of(el.find("title")) or text_of(el.find("meta-name")) or el.get("notes-type") or el.get("fn-type") or ""
            if DA_TITLE.search(ttl) or re.match(r"(data|code) availability", t, re.I):
                res["data_availability"].append({"title": ttl, "text": t[:4000]})
    # methods text
    chunks = []
    body = root.find(".//body")
    if body is not None:
        for sec in body.iter("sec"):
            title = text_of(sec.find("title"))
            if METHODS_TITLE.search(title) or (sec.get("sec-type") or "").startswith(("methods", "materials")):
                chunks.append(f"## {title}\n" + text_of(sec))
        if not chunks:  # short communications without headed methods: keep whole body
            chunks.append(text_of(body)[:30000])
        else:
            res["has_methods"] = True
    mt, seen = "", set()
    for c in chunks:
        if c[:200] in seen:
            continue
        seen.add(c[:200])
        mt += c + "\n"
    res["methods_text"] = mt[:60000]
    # repository links outside references
    for r in root.iter("ref-list"):
        r.clear()
    full = text_of(root)
    links = set()
    for el in root.iter("ext-link"):
        h = el.get("xlink_href") or el.get("href") or ""
        for m in REPO_RX.finditer(h):
            links.add(m.group(0))
    for m in REPO_RX.finditer(full):
        links.add(m.group(0))
    res["repo_links"] = sorted(links)
    for sm in root.iter("supplementary-material"):
        media = sm.find(".//media")
        href = (media.get("xlink_href") or media.get("href")) if media is not None else sm.get("href")
        res["supplementary"].append({"href": href, "label": text_of(sm.find("label")),
                                     "caption": text_of(sm.find("caption"))[:300]})
    return res


def fetch(pmcid):
    cp = FT_CACHE / f"{pmcid}.json"
    if cp.exists():
        return json.loads(cp.read_text(encoding="utf-8"))
    xml = get(f"{EPMC}/{pmcid}/fullTextXML", as_json=False, use_cache=False)
    res = parse(xml) if xml and xml.lstrip().startswith("<") and len(xml) > 2000 else None
    out = {"pmcid": pmcid, "ok": res is not None, **(res or {})}
    cp.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def fetch_batch(pmcids):
    """NCBI efetch returns many PMC articles per call (much faster than per-article Europe PMC)."""
    todo = [p for p in pmcids if not (FT_CACHE / f"{p}.json").exists()]
    if todo:
        xml = get(EFETCH, {"db": "pmc", "id": ",".join(p.replace("PMC", "") for p in todo), "retmode": "xml"},
                  as_json=False, use_cache=False, timeout=180)
        found = {}
        for m in re.finditer(r"<article[\s>].*?</article>", xml or "", re.S):
            art = m.group(0)
            idm = re.search(r'<article-id pub-id-type="(?:pmc|pmcid)">(?:PMC)?(\d+)</article-id>', art)
            if idm:
                found["PMC" + idm.group(1)] = art
        for p in todo:
            art = found.get(p)
            res = parse(art) if art and "<body" in art else None
            out = {"pmcid": p, "ok": res is not None, **(res or {})}
            (FT_CACHE / f"{p}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return {p: json.loads((FT_CACHE / f"{p}.json").read_text(encoding="utf-8")).get("ok") for p in pmcids}


def main():
    arts = [a for a in load_jsonl(OUT / "articles_classified.jsonl")
            if a["tier"] in ("core", "methods") and a.get("pmcid")]
    print("full texts to fetch:", len(arts))
    ids = sorted({a["pmcid"] for a in arts})
    batches = [ids[i:i + 20] for i in range(0, len(ids), 20)]
    ok = {}
    for r in pmap(fetch_batch, batches, workers=2, desc="fulltext batches"):
        if isinstance(r, dict) and "_error" not in r:
            ok.update(r)
    idx = {}
    for a in arts:
        if ok.get(a["pmcid"]):
            idx[a["epmc_id"]] = a["pmcid"]
    save_json(OUT / "fulltext_index.json", idx)
    print("parsed full texts:", len(idx))


if __name__ == "__main__":
    main()
