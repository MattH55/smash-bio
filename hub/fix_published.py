"""One-off: apply the audit fixes (2026-10-15) to the already-published website data, without a full
rebuild (out/records.jsonl is a OneDrive cloud-only file on this machine). The same fixes are in
s07/s09, so the next full build produces identical output.

1. Item 7: decode HTML entities / strip inline tags in every JSON string of website/data/**/*.js,
   website/sim/data/*.js and the downloads (CSV, JSONL.gz).
2. Item 9: stats.js field coverage "with OA full text" uses the fulltext_checked set (same as the total).
3. Item 10: smash-smfs-datasets.csv gains journal_mirror and counted_in_site_total columns, and the
   script checks that counted_in_site_total reproduces stats.totals.deposits.
"""
import csv
import gzip
import io
import json
import re
from pathlib import Path

from common import clean_obj, clean_text
from harvester_cleanup import COUNTED_RELEVANCE

WEB = Path(__file__).resolve().parent.parent / "website"
STR = re.compile(r'"(?:[^"\\]|\\.)*"')


def fix_js(p: Path) -> int:
    t = p.read_text(encoding="utf-8")
    n = 0

    def sub(m):
        nonlocal n
        s = json.loads(m.group(0))
        c = clean_text(s)
        if c != s:
            n += 1
            return json.dumps(c, ensure_ascii=False)
        return m.group(0)

    out = STR.sub(sub, t)
    if n:
        p.write_text(out, encoding="utf-8")
    return n


def load_payload(p: Path):
    t = p.read_text(encoding="utf-8")
    m = re.search(r"registerShard\(\d+,(.*)\);\s*$", t, re.S)
    if m:
        return json.loads(m.group(1))
    return json.loads(t[t.index("=") + 1 :].strip().rstrip(";"))


def main():
    files = sorted((WEB / "data").glob("*.js")) + sorted((WEB / "data" / "records").glob("r-*.js")) + sorted((WEB / "sim" / "data").glob("*.js"))
    total = 0
    for p in files:
        if p.name == "schema.js":
            continue
        n = fix_js(p)
        total += n
        if n:
            print(f"item 7: {p.relative_to(WEB)}: {n} strings decoded")
    print("item 7: total strings decoded:", total)

    # item 9
    import s07_build_site as s07

    recs = [r for p in sorted((WEB / "data" / "records").glob("r-*.js")) for r in load_payload(p)]
    sp = WEB / "data" / "stats.js"
    st = load_payload(sp)
    fresh = s07.build_stats(recs, load_payload(WEB / "data" / "datasets.js"))
    old_n = st.get("n_fulltext")
    st["field_coverage"], st["n_fulltext"] = fresh["field_coverage"], fresh["n_fulltext"]
    s07.js(sp, "SMASH.stats", st)
    print(f"item 9: n_fulltext {old_n} -> {st['n_fulltext']}; totals.fulltext_checked = {st['totals']['fulltext_checked']}")

    # item 10
    dl = WEB / "downloads"
    dsets = {d.get("family_id"): d for d in load_payload(WEB / "data" / "datasets.js")}
    cp = dl / "smash-smfs-datasets.csv"
    rows = list(csv.reader(io.StringIO(cp.read_text(encoding="utf-8"))))
    head, body = rows[0], rows[1:]
    if "journal_mirror" not in head:
        head += ["journal_mirror", "counted_in_site_total"]
        missing = 0
        for r in body:
            d = dsets.get(r[0])
            if d is None:
                missing += 1
            mirror = bool(d and d.get("journal_mirror"))
            rel = r[head.index("relevance")] or "in_scope"
            r += [str(mirror), str(rel in COUNTED_RELEVANCE and not mirror)]
        print(f"item 10: {len(body)} rows; {missing} without a datasets.js entry (journal_mirror then False)")
    ti = head.index("title")
    for r in body:
        r[ti] = clean_text(r[ti])
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([head] + body)
    cp.write_text(buf.getvalue(), encoding="utf-8")
    counted = sum(r[head.index("counted_in_site_total")] == "True" for r in body)
    print(f"item 10: counted_in_site_total = {counted}; site total stats.totals.deposits = {st['totals']['deposits']}"
          f" -> {'reproduced' if counted == st['totals']['deposits'] else 'MISMATCH'}")

    sp2 = dl / "smash-smfs-summary.csv"
    rows = list(csv.reader(io.StringIO(sp2.read_text(encoding="utf-8"))))
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([[clean_text(c) for c in r] for r in rows])
    sp2.write_text(buf.getvalue(), encoding="utf-8")
    gz = dl / "smash-smfs-records.jsonl.gz"
    if gz.exists():
        # split on "\n" only: splitlines() also splits on U+2028 inside JSON strings. Write to a temp
        # file and swap only after it re-reads completely, so a failure never truncates the download.
        recs_dl = [json.loads(ln) for ln in gzip.open(gz, "rt", encoding="utf-8").read().split("\n") if ln.strip()]
        tmp = gz.with_suffix(".gz.tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            for r in recs_dl:
                f.write(json.dumps(clean_obj(r), ensure_ascii=False) + "\n")
        assert sum(1 for ln in gzip.open(tmp, "rt", encoding="utf-8").read().split("\n") if ln.strip()) == len(recs_dl)
        tmp.replace(gz)
        print("item 7: downloads cleaned (summary CSV, records JSONL.gz)")


if __name__ == "__main__":
    main()
