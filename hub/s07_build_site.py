"""Step 7 - emit static website data files from out/records.jsonl.

website/data/index.js          compact rows for explorer/search (SMASH.index, SMASH.meta)
website/data/records/r-NNN.js  full records in shards of 100 (SMASH.registerShard)
website/data/datasets.js       repository deposits (SMASH.datasets)
website/data/stats.js          precomputed aggregates for Insights (SMASH.stats)
website/data/schema.js         JSON schemas for the Schema page (SMASH.schemas)
website/downloads/*            full JSONL, CSV summary, schemas
"""
import csv
import datetime
import gzip
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from common import OUT, clean_obj, clean_text, load_jsonl
from harvester_cleanup import COUNTED_RELEVANCE

WEB = Path(__file__).resolve().parent.parent / "website"
DATA = WEB / "data"
SHARD = 100


def js(path, var, obj):
    path.write_text(f"{var} = " + json.dumps(clean_obj(obj), ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")


def prune(o):
    """Drop null values recursively (so published records validate) and decode HTML entities in text."""
    if isinstance(o, str):
        return clean_text(o)
    if isinstance(o, dict):
        return {k: prune(v) for k, v in o.items() if v is not None}
    if isinstance(o, list):
        return [prune(v) for v in o if v is not None]
    return o


def J(xs):
    return ";".join(str(x) for x in (xs or []) if x)


def first_author(a):
    if not a:
        return ""
    return a[0] + (" et al." if len(a) > 1 else "")


def index_row(r, shard):
    p, t, bs, da = r["publication"], r["technique"], r["biological_system"], r["data_availability"]
    ents = [e["name"] for e in bs["entities"] if e.get("evidence", {}).get("method") != "europepmc_textmining"][:5]
    tm = [e["name"] for e in bs["entities"] if e.get("evidence", {}).get("method") == "europepmc_textmining"][:3]
    return {
        "id": r["record_id"], "sh": shard, "t": p.get("title"), "a": first_author(p.get("authors")), "y": p.get("year"),
        "j": p.get("journal"), "doi": p.get("doi"), "pm": p.get("pmid"),
        "tech": t["primary"], "tech2": t.get("secondary") or [], "geo": t.get("force_application_geometry"),
        "mod": t.get("correlative_modalities") or [],
        "cls": bs.get("system_class") or [], "ent": ents, "tm": tm,
        "et": sorted({e["entity_type"] for e in bs["entities"]}),
        "org": [o["name"] for o in bs.get("organisms") or []][:3],
        "uni": sorted({i["id"] for e in bs["entities"] for i in e.get("identifiers", []) if i["scheme"] == "uniprot" and e.get("evidence", {}).get("method") != "europepmc_textmining"})[:6],
        "vend": r["hardware"].get("make_of_setup"),
        "st": da["status"], "ds": da.get("has_linked_dataset"), "anydata": da.get("has_any_data"),
        "code": da.get("has_linked_code"), "raw": da.get("raw_traces_available"),
        "repo": da.get("repositories") or [], "nds": len([d for d in da.get("datasets", []) if not d.get("journal_mirror")]),
        "fair": r["fair_completeness"]["overall"], "kind": r["scope"]["article_kind"], "tier": r["scope"]["tier"],
        "nres": len(r.get("results") or []), "obs": sorted({x["quantity"] for x in r.get("results") or []}),
        "cur": r["curation"]["level"], "oa": p.get("open_access"), "cit": p.get("cited_by") or 0,
        "kw": " ".join(filter(None, [" ".join(filter(None, p.get("keywords") or []))[:120],
                                     " ".join(a.split(" ")[0] for a in (p.get("authors") or [])[:8] if a)])).lower(),
    }


CAT = ["tech", "geo", "st", "kind", "cur", "tier", "vend", "j"]            # dictionary-encoded scalars
CATL = ["tech2", "mod", "cls", "et", "org", "repo", "obs", "ent", "tm", "uni"]  # dictionary-encoded lists
BOOL = ["ds", "anydata", "code", "raw", "oa"]
PLAIN = ["t", "a", "y", "doi", "pm", "sh", "fair", "nres", "nds", "cit", "kw"]


def pack_index(rows):
    """Columnar, dictionary-encoded index (decoded by SMASH.unpackIndex in js/app.js)."""
    dicts, cols = {"idn": [int(r["id"][5:]) for r in rows]}, {}
    for k in CAT + CATL:
        vals = Counter(v for r in rows for v in (r[k] if k in CATL else [r[k]]) if v is not None)
        d = [v for v, _ in vals.most_common()]
        dicts[k] = d
        pos = {v: i for i, v in enumerate(d)}
        cols[k] = [([pos[v] for v in r[k] if v is not None] if k in CATL else (pos[r[k]] if r[k] is not None else -1)) for r in rows]
    for k in BOOL:
        cols[k] = "".join("1" if r[k] else "0" for r in rows)
    for k in PLAIN:
        cols[k] = [r[k] for r in rows]
    ids = dicts.pop("idn")
    return {"n": len(rows), "ids": ids, "dicts": dicts, "cols": cols, "cat": CAT, "catl": CATL, "bool": BOOL, "plain": PLAIN}


SITE_URL = "https://smash-bio.org/"
MAIN_PAGES = [("", "1.0", "weekly"), ("explore.html", "0.9", "weekly"), ("datasets.html", "0.8", "weekly"),
              ("stats.html", "0.7", "monthly"), ("schema.html", "0.8", "monthly"), ("submit.html", "0.5", "monthly"),
              ("about.html", "0.5", "monthly"), ("sitemap.html", "0.3", "monthly"),
              ("pull/index.html", "0.6", "monthly"), ("pull/benchmarks.html", "0.4", "monthly"),
              ("pull/about.html", "0.4", "monthly")]


def write_sitemap(recs, built, systems=()):
    """sitemap.xml = sitemap index -> sitemap-pages.xml, sitemap-systems.xml, sitemap-records-N.xml (2,000 URLs each).
    Small child files make Search Console report each part separately. Also writes robots.txt.

    ``lastmod`` describes the underlying page/data, not merely the time this file was
    regenerated.  ``changefreq`` and ``priority`` are retained for non-Google consumers.
    """
    from xml.sax.saxutils import escape
    for old in WEB.glob("sitemap-*.xml"):
        old.unlink()

    NL = chr(10)
    # plain XML for crawlers (no XSLT: Chrome is removing it and shows a warning banner); humans get sitemap.html
    HEAD = '<?xml version="1.0" encoding="UTF-8"?>' + NL
    NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'

    def urlset(fname, urls):
        body = "".join(
            "<url>" + f"<loc>{escape(u)}</loc><lastmod>{lm}</lastmod>" +
            (f"<changefreq>{freq}</changefreq>" if freq else "") +
            (f"<priority>{priority}</priority>" if priority else "") +
            f"</url>{NL}"
            for u, lm, freq, priority in urls
        )
        (WEB / fname).write_text(f"{HEAD}<urlset {NS}>{NL}{body}</urlset>{NL}", encoding="utf-8")
        return fname

    def page_lastmod(page):
        path = WEB / (page or "index.html")
        return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else built

    pages = [(SITE_URL + p, page_lastmod(p), freq, priority) for p, priority, freq in MAIN_PAGES]
    pages.append((SITE_URL + "systems.html", page_lastmod("systems.html"), "weekly", "0.8"))
    files = [urlset("sitemap-pages.xml", pages)]
    if systems:
        files.append(urlset("sitemap-systems.xml", [(f"{SITE_URL}system.html?s={sy['slug']}", built, "monthly", "0.6") for sy in systems]))
    rec_urls = [(f"{SITE_URL}record.html?id={r['record_id']}", (r.get("curation") or {}).get("last_updated") or built, "monthly", "0.7")
                for r in sorted(recs, key=lambda r: r["record_id"])]
    for k in range(0, len(rec_urls), 2000):
        files.append(urlset(f"sitemap-records-{k // 2000 + 1}.xml", rec_urls[k:k + 2000]))
    idx = "".join(f"<sitemap><loc>{SITE_URL}{f}</loc><lastmod>{built}</lastmod></sitemap>{NL}" for f in files)
    (WEB / "sitemap.xml").write_text(f"{HEAD}<sitemapindex {NS}>{NL}{idx}</sitemapindex>{NL}", encoding="utf-8")
    robots = ["User-agent: *", "Allow: /", "Disallow: /nc_assets/", "", f"Sitemap: {SITE_URL}sitemap.xml", ""]
    (WEB / "robots.txt").write_text(NL.join(robots), encoding="utf-8")
    write_html_sitemap(recs, systems, built)
    from validate_sitemap import validate_sitemaps
    validate_sitemaps(WEB, expected_records=len(recs), expected_systems=len(systems))
    return len(rec_urls) + len(systems) + len(MAIN_PAGES) + 1


def clean_markup(value):
    """Turn stored HTML tags and entities into plain text for a human-readable page."""
    import html as _html
    sub = str.maketrans("0123456789+-=()aeoxhklmnpstv", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜᵥ")
    sup = str.maketrans("0123456789+-=()ni", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ")
    s = "" if value is None else str(value)
    for _ in range(3):
        nxt = _html.unescape(s)
        if nxt == s:
            break
        s = nxt

    def subsup(match):
        inner = re.sub(r"<[^>]+>", "", match.group(2))
        return inner.translate(sub if match.group(1).lower() == "sub" else sup)

    s = re.sub(r"<\s*(sub|sup)\s*>(.*?)<\s*/\s*\1\s*>", subsup, s, flags=re.I | re.S)
    s = re.sub(r"<\s*br\s*/?\s*>", " ", s, flags=re.I)
    s = re.sub(r"</?[A-Za-z][^>]*>", "", s)
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def write_html_sitemap(recs, systems, built):
    """Human-readable sitemap page with plain links to every page, system and study (also helps crawler discovery)."""
    from html import escape as h
    head_tpl = (WEB / "about.html").read_text(encoding="utf-8")
    head = head_tpl[:head_tpl.index("</head>")]
    head = re.sub(r"<title>.*?</title>", "<title>Sitemap | SMASH-BIO</title>", head, flags=re.S)
    head = re.sub(r'<meta name="description"[^>]*>', "", head)
    head = head.replace("<title>", '<meta name="description" content="Every page, biological system and force-spectroscopy study in the SMASH-BIO hub.">\n  <title>', 1)
    pages = [("index.html", "Home"), ("explore.html", "Explore studies"), ("systems.html", "Biological systems"), ("datasets.html", "Datasets"),
             ("stats.html", "Insights"), ("schema.html", "Schema"), ("submit.html", "Submit a record"), ("about.html", "About")]
    by_year = defaultdict(list)
    for r in sorted(recs, key=lambda r: (-(r["publication"].get("year") or 0), r["publication"].get("title") or "")):
        by_year[r["publication"].get("year") or "Undated"].append(r)
    parts = [head, "</head>\n<body>\n  <nav id=\"site-nav\"></nav>\n",
             '  <header class="page-header"><div class="container"><h1>Sitemap</h1>',
             f'<p>All {len(pages)} pages, {len(systems)} biological systems and {len(recs):,} studies. Updated {built}. '
             'Search engines: use <a href="sitemap.xml">sitemap.xml</a>.</p></div></header>\n',
             '  <main class="container prose" style="padding-bottom:60px;max-width:var(--maxw)">\n<h2>Pages</h2><ul>',
             "".join(f'<li><a href="{u}">{t}</a></li>' for u, t in pages), "</ul>\n<h2>Biological systems</h2><ul class=\"sm-cols\">",
             "".join(f'<li><a href="system.html?s={h(s["slug"])}">{h(clean_markup(s["name"]))}</a> <span class="muted">({s["n"]})</span></li>'
                     for s in sorted(systems, key=lambda s: s["name"].lower())), "</ul>\n<h2>Studies by year</h2>\n",
             '<p class="small">' + " · ".join(f'<a href="#y{y}">{y}</a>' for y in by_year) + "</p>\n"]
    for y, rs in by_year.items():
        parts.append(f'<h3 id="y{y}">{y} <span class="muted">({len(rs)})</span></h3><ul>')
        parts.append("".join(f'<li><a href="record.html?id={r["record_id"]}">{h(clean_markup(r["publication"].get("title") or r["record_id"]))}</a></li>' for r in rs))
        parts.append("</ul>\n")
    parts.append('  </main>\n  <footer id="site-footer"></footer>\n</body>\n</html>\n')
    (WEB / "sitemap.html").write_text("".join(parts), encoding="utf-8")


def build_stats(recs, dsets):
    st = {}
    counted_dsets = [d for d in dsets if d.get("relevance", "in_scope") in COUNTED_RELEVANCE and not d.get("journal_mirror")]
    years = sorted({r["publication"].get("year") for r in recs if r["publication"].get("year")})
    prim = [r for r in recs if r["scope"]["article_kind"] in ("primary_research", "methods", "preprint")]
    st["totals"] = {
        "records": len(recs), "primary": len(prim),
        "with_dataset": sum(r["data_availability"]["has_linked_dataset"] for r in recs),
        "with_any_data": sum(r["data_availability"].get("has_any_data", False) for r in recs),
        "with_code": sum(r["data_availability"].get("has_linked_code", False) for r in recs),
        "raw_traces": sum(r["data_availability"].get("raw_traces_available", False) for r in recs),
        "fulltext_checked": sum(r["data_availability"].get("fulltext_checked", False) for r in recs),
        "deposits": len(counted_dsets), "unlinked_deposits": sum(1 for d in counted_dsets if not d.get("linked_records")),
        "deposits_all_labels": len(dsets),
        "results": sum(len(r.get("results") or []) for r in recs),
        "with_uniprot": sum(any(i["scheme"] == "uniprot" for e in r["biological_system"]["entities"] for i in e.get("identifiers", [])) for r in recs),
        "curated": sum(r["curation"]["level"] == "curated" for r in recs),
        "year_min": years[0] if years else None, "year_max": years[-1] if years else None,
    }
    # data availability by year (primary research, 2000+)
    by_year = defaultdict(Counter)
    for r in prim:
        y = r["publication"].get("year")
        if y and y >= 2000:
            by_year[y][r["data_availability"]["status"]] += 1
    st["status_by_year"] = {y: dict(c) for y, c in sorted(by_year.items())}
    # checked-only share with public repo by year
    st["repo_share_by_year"] = {}
    for y, c in sorted(by_year.items()):
        checked = sum(v for k, v in c.items() if k != "unknown_no_fulltext")
        if checked >= 10:
            st["repo_share_by_year"][y] = {"checked": checked, "repo": c.get("public_repository", 0), "share": round(c.get("public_repository", 0) / checked, 4)}
    by_tech = defaultdict(Counter)
    for r in prim:
        by_tech[r["technique"]["primary"]][r["data_availability"]["status"]] += 1
    st["status_by_tech"] = {k: dict(v) for k, v in by_tech.items()}
    st["tech_counts"] = dict(Counter(r["technique"]["primary"] for r in recs).most_common())
    st["tech_by_year"] = {}
    tby = defaultdict(Counter)
    for r in recs:
        y = r["publication"].get("year")
        if y:
            tby[y][r["technique"]["primary"]] += 1
    st["tech_by_year"] = {y: dict(c) for y, c in sorted(tby.items())}
    st["class_counts"] = dict(Counter(c for r in recs for c in r["biological_system"]["system_class"]).most_common())
    st["entity_counts"] = dict(Counter(e["name"] for r in recs for e in r["biological_system"]["entities"]
                                       if e.get("evidence", {}).get("method") != "europepmc_textmining").most_common(40))
    st["organism_counts"] = dict(Counter(o["name"] for r in recs for o in r["biological_system"].get("organisms") or []).most_common(20))
    st["vendor_counts"] = dict(Counter(r["hardware"].get("make_of_setup") for r in recs if r["hardware"].get("make_of_setup")).most_common(20))
    st["repo_counts"] = dict(Counter(rp for r in recs for rp in r["data_availability"].get("repositories") or []).most_common(20))
    st["format_counts"] = dict(Counter(f for r in recs for d in r["data_availability"]["datasets"] for f in d.get("file_formats") or []).most_common(20))
    st["obs_counts"] = dict(Counter(x["quantity"] for r in recs for x in r.get("results") or []).most_common())
    # completeness distribution
    bins = Counter(min(9, int(r["fair_completeness"]["overall"] * 10)) for r in recs)
    st["fair_hist"] = [bins.get(i, 0) for i in range(10)]
    sec = ["hardware", "assay", "construct", "solution", "data"]
    st["fair_sections"] = {s: round(sum(r["fair_completeness"][s] for r in recs) / len(recs), 3) for s in sec}
    st["fair_sections_fulltext"] = {s: round(sum(r["fair_completeness"][s] for r in recs if r["curation"]["level"] != "auto_abstract") /
                                              max(1, sum(r["curation"]["level"] != "auto_abstract" for r in recs)), 3) for s in sec}
    # Table 3 field coverage (hardware/assay details)
    def cov(fn):
        return round(sum(1 for r in recs if fn(r)) / len(recs), 4)
    # records whose open-access full text was actually read: the same set as totals["fulltext_checked"]
    ftx = [r for r in recs if r["data_availability"].get("fulltext_checked")]

    def covf(fn):
        return round(sum(1 for r in ftx if fn(r)) / max(1, len(ftx)), 4)
    fields = {
        "Instrument make": lambda r: r["hardware"].get("make_of_setup"),
        "Laser wavelength": lambda r: (r["hardware"].get("optical") or {}).get("laser_wavelength"),
        "Trap / cantilever stiffness": lambda r: (r["hardware"].get("optical") or {}).get("trap_stiffness") or (r["hardware"].get("afm") or {}).get("spring_constant"),
        "Calibration method": lambda r: r["hardware"].get("calibration_technique"),
        "Detection device": lambda r: r["hardware"].get("detection_device"),
        "Temperature": lambda r: r["hardware"].get("temperature"),
        "Acquisition rate": lambda r: r["hardware"].get("acquisition_rate"),
        "Bead size": lambda r: r["assay"].get("bead_size"),
        "Attachment chemistry": lambda r: r["assay"].get("attachment_chemistry"),
        "Trap control mode": lambda r: r["assay"].get("trap_control"),
        "Buffer pH": lambda r: r["solution"].get("pH"),
        "Buffer components": lambda r: r["solution"].get("components"),
        "UniProt-linked construct": lambda r: any(i["scheme"] == "uniprot" for e in r["biological_system"]["entities"] for i in e.get("identifiers", [])),
        "Organism": lambda r: r["biological_system"].get("organisms"),
        "Linked dataset": lambda r: r["data_availability"]["has_linked_dataset"],
    }
    st["field_coverage"] = {k: {"all": cov(f), "fulltext": covf(f)} for k, f in fields.items()}
    st["n_fulltext"] = len(ftx)
    return st


def main():
    recs = [prune(r) for r in load_jsonl(OUT / "records.jsonl")]
    for r in recs:
        for x in r.get("results") or []:
            if (x.get("source") or {}).get("location") == "results":
                x["source"]["location"] = "results_text"
    dsets = load_jsonl(OUT / "datasets_hub.jsonl")
    # clear old data files but keep the folders: OneDrive often locks directories, which makes rmtree fail midway
    (DATA / "records").mkdir(parents=True, exist_ok=True)
    for old in list(DATA.rglob("*.js")):
        old.unlink()
    recs.sort(key=lambda r: r["record_id"])
    index = []
    for i in range(0, len(recs), SHARD):
        n = i // SHARD
        chunk = recs[i:i + SHARD]
        for r in chunk:
            index.append(index_row(r, n))
        (DATA / "records" / f"r-{n:03d}.js").write_text(
            f"SMASH.registerShard({n}," + json.dumps(chunk, ensure_ascii=False, separators=(",", ":")) + ");\n", encoding="utf-8")
    meta = {"built": datetime.date.today().isoformat(), "n": len(recs), "schema_version": "3.1.0"}
    (DATA / "index.js").write_text("SMASH.meta=" + json.dumps(meta) + ";\nSMASH.index=SMASH.unpackIndex(" +
                                   json.dumps(pack_index(index), ensure_ascii=False, separators=(",", ":")) + ");\n", encoding="utf-8")
    rid_title = {r["record_id"]: r["publication"].get("title") for r in recs}
    for d in dsets:
        d["linked_titles"] = [rid_title.get(x) for x in d.get("linked_records", [])[:3]]
    slim_ds = []
    for d in dsets:
        e = {k: v for k, v in d.items() if v not in (None, "", [], False) and k not in ("rights", "publisher")}
        if e.get("description"):
            e["description"] = e["description"][:220]
        if e.get("creators"):
            e["creators"] = e["creators"][:4]
        slim_ds.append(e)
    # The public table contains countable biological families only. The CSV below
    # intentionally retains all relevance labels for audit and curation.
    public_dsets = [d for d in dsets if d.get("relevance", "in_scope") in COUNTED_RELEVANCE]
    js(DATA / "datasets.js", "SMASH.datasets", public_dsets)
    stats = build_stats(recs, dsets)
    # featured: recent primary studies with linked public data, preferring raw traces, curated and richest annotation
    cand = [(r, row) for r, row in zip(recs, index) if row["ds"] and row["kind"] == "primary_research" and row["ent"]]
    cand.sort(key=lambda x: (x[1]["cur"] == "curated", x[1]["raw"], x[1]["y"] or 0, x[1]["fair"]), reverse=True)
    stats["featured"] = [{k: row[k] for k in ("id", "t", "a", "y", "j", "tech", "cls", "ent", "org", "st", "repo", "raw", "fair")} for _, row in cand[:6]]
    from s09_systems import build_systems
    systems = build_systems(recs, verbose=False)
    js(DATA / "systems.js", "SMASH.systems", systems)
    # light index for the browse page (full studies lists stay in systems.js)
    js(DATA / "systems-index.js", "SMASH.systems", [{
        "slug": x["slug"], "name": x["name"], "entity_type": x["entity_type"], "n": x["n"], "n_dataset": x["n_dataset"], "years": x["years"],
        "techniques": dict(list(x["techniques"].items())[:1]), "gene": x["gene"], "organisms": {k: 0 for k in list(x["organisms"])[:3]},
        "uniprot": {"acc": x["uniprot"]["acc"], "protein": x["uniprot"].get("protein"), "function": (x["uniprot"].get("function") or "")[:320]} if x["uniprot"] else None,
        "wikipedia": {"title": x["wikipedia"]["title"], "extract": (x["wikipedia"].get("extract") or "")[:320]} if x["wikipedia"] else None,
    } for x in systems])
    stats["top_systems"] = [{"slug": x["slug"], "name": x["name"], "type": x["entity_type"], "n": x["n"], "n_dataset": x["n_dataset"],
                             "acc": (x.get("uniprot") or {}).get("acc")} for x in systems if x["entity_type"] not in ("small_molecule", "synthetic")][:12]
    stats["n_systems"] = len(systems)
    js(DATA / "stats.js", "SMASH.stats", stats)
    print("systems:", len(systems), "| sitemap URLs:", write_sitemap(recs, meta["built"], systems))
    schemas = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (WEB / "schema").glob("*.json")}
    js(DATA / "schema.js", "SMASH.schemas", schemas)

    dl = WEB / "downloads"
    dl.mkdir(exist_ok=True)
    with gzip.open(dl / "smash-smfs-records.jsonl.gz", "wt", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(dl / "smash-smfs-summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["record_id", "doi", "pmid", "year", "title", "first_author", "journal", "technique", "secondary_techniques", "geometry",
                    "experiment_classes", "entities", "uniprot", "organisms", "instrument", "data_status", "has_linked_dataset", "has_any_data",
                    "has_code", "raw_traces", "repositories", "dataset_ids", "n_results", "fair_overall", "article_kind", "curation"])
        for r, row in zip(recs, index):
            w.writerow([row["id"], row["doi"], row["pm"], row["y"], row["t"], row["a"], row["j"], row["tech"], J(row["tech2"]), row["geo"],
                        J(row["cls"]), J(row["ent"]), J(row["uni"]), J(row["org"]), row["vend"] or "", row["st"],
                        row["ds"], row["anydata"], row["code"], row["raw"], J(row["repo"]),
                        J(d.get("id") for d in r["data_availability"]["datasets"] + r["data_availability"]["code"]),
                        row["nres"], row["fair"], row["kind"], row["cur"]])
    with open(dl / "smash-smfs-datasets.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["family_id", "canonical_doi_or_url", "version_dois", "title", "repository", "year", "resource_type", "relevance",
                    "relevance_rule", "techniques", "linked_records", "file_formats", "content", "n_files", "total_size_bytes",
                    "journal_mirror", "counted_in_site_total"])
        for d in dsets:
            w.writerow([d.get("family_id"), d.get("canonical_doi") or d.get("url"), J(d.get("version_dois") or []),
                        clean_text(d.get("title")), d.get("repository"), d.get("year"), d.get("resource_type"), d.get("relevance"),
                        (d.get("relevance_evidence") or {}).get("rule"),
                        J(d.get("techniques") or []), J(d.get("linked_records") or []), J(d.get("file_formats") or []),
                        d.get("content"), d.get("n_files"), d.get("total_size_bytes"), bool(d.get("journal_mirror")),
                        d.get("relevance", "in_scope") in COUNTED_RELEVANCE and not d.get("journal_mirror")])
    sizes = {p.name: p.stat().st_size for p in [DATA / "index.js", DATA / "datasets.js", DATA / "stats.js", dl / "smash-smfs-records.jsonl.gz"]}
    print("records:", len(recs), "shards:", (len(recs) + SHARD - 1) // SHARD, "sizes:", sizes)


if __name__ == "__main__":
    main()
