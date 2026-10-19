"""Stamp schema 3.2.0 classifications onto the published corpus and write module pages.

Reads ``website/downloads/smash-smfs-records.jsonl.gz``, assigns modules, and
writes the gzip, the summary columns, ``smash-smfs-modules.csv``, the static
module pages, and the explorer index. The v1.0.0-paper tag is not moved.
"""
from __future__ import annotations

import csv
import gzip
import html
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "taxonomy"))
sys.path.insert(0, str(ROOT / "hub"))

from classify_modules import apply_classification  # noqa: E402
from load import load_taxonomy  # noqa: E402
from s07_build_site import DATA, WEB, index_row, js, pack_index  # noqa: E402

TAX = load_taxonomy()
GZ = WEB / "downloads" / "smash-smfs-records.jsonl.gz"
SUMMARY = WEB / "downloads" / "smash-smfs-summary.csv"
MODULES_CSV = WEB / "downloads" / "smash-smfs-modules.csv"
QUEUE = ROOT / "hub" / "curation_queue_modules.csv"
REPORT = ROOT / "hub" / "out" / "modules_report.md"


def main() -> None:
    print("classifying", GZ)
    records = []
    fingerprints = []
    with gzip.open(GZ, "rt", encoding="utf-8") as handle:
        for line in handle:
            raw = json.loads(line)
            fingerprints.append((
                raw["record_id"],
                list((raw.get("biological_system") or {}).get("system_class") or []),
                (raw.get("technique") or {}).get("primary"),
            ))
            records.append(apply_classification(raw, TAX))
    for (record_id, classes, technique), record in zip(fingerprints, records):
        if record["record_id"] != record_id:
            raise SystemExit("record_id changed")
        if list((record.get("biological_system") or {}).get("system_class") or []) != classes:
            raise SystemExit(f"{record_id} experiment class changed")
        if (record.get("technique") or {}).get("primary") != technique:
            raise SystemExit(f"{record_id} technique changed")
    ids = [r["record_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate record_id")
    for record in records:
        primaries = [m for m in record["classification"]["modules"] if m["role"] == "primary"]
        if len(primaries) != 1:
            raise SystemExit(f"{record['record_id']} has {len(primaries)} primary modules")
        if record["schema_version"] != "3.2.0":
            raise SystemExit(record["record_id"])
    reviews = {record["record_id"]: list(record.get("_module_review") or []) for record in records}
    with gzip.open(GZ, "wt", encoding="utf-8") as handle:
        for record in records:
            record.pop("_module_review", None)
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print("records", len(records))
    _summary(records)
    _modules_csv(records)
    _queue_and_report(records, reviews)
    _shards_and_index(records)
    _pages(records)
    _schema_js()
    _copy_taxonomy()
    print("module pages written")


def _summary(records: list[dict]) -> None:
    by_id = {r["record_id"]: r for r in records}
    extra = ["table3_type", "primary_module", "secondary_modules", "submodules", "assay_type", "bead_geometry", "measurement_modes", "processivity"]
    with SUMMARY.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    for name in extra:
        if name not in fields:
            fields.append(name)
    seen = set()
    for row in rows:
        record = by_id.get(row["record_id"])
        if record:
            row.update(_summary_fields(record))
            seen.add(row["record_id"])
    with SUMMARY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    missing = set(by_id) - seen
    if missing:
        raise SystemExit(f"summary is missing {len(missing)} records")


def _summary_fields(record: dict) -> dict:
    modules = record["classification"]["modules"]
    primary = next(m for m in modules if m["role"] == "primary")
    secondary = [m["module_id"] for m in modules if m["role"] == "secondary"]
    return {
        "table3_type": record["classification"]["table3_type"],
        "primary_module": primary["module_id"],
        "secondary_modules": ";".join(secondary),
        "submodules": ";".join(primary.get("submodules") or []),
        "assay_type": record["classification"].get("assay_type") or "",
        "bead_geometry": record["classification"].get("bead_geometry") or "",
        "measurement_modes": ";".join(record["classification"].get("measurement_modes") or []),
        "processivity": record["classification"].get("processivity") or "",
    }


def _modules_csv(records: list[dict]) -> None:
    buckets: dict[tuple, list] = defaultdict(list)
    for record in records:
        year = (record.get("publication") or {}).get("year") or ""
        module = _primary(record)
        linked = bool((record.get("data_availability") or {}).get("has_linked_dataset"))
        buckets[(module, year)].append(linked)
    with MODULES_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["module", "year", "records", "with_linked_dataset", "data_availability_share"])
        for (module, year), flags in sorted(buckets.items(), key=lambda item: (item[0][0], str(item[0][1]))):
            share = sum(flags) / len(flags)
            writer.writerow([module, year, len(flags), sum(flags), f"{share:.4f}"])


def _queue_and_report(records: list[dict], reviews: dict[str, list[str]]) -> None:
    keyword_hits = Counter()
    queue_rows = []
    for record in records:
        text = " ".join((entry.get("snippet") or "") for entry in record.get("provenance") or [])
        for entry in record.get("provenance") or []:
            snippet = entry.get("snippet") or ""
            if snippet.startswith("k_"):
                keyword_hits[snippet.split(":", 1)[0]] += 1
        reasons = list(reviews.get(record["record_id"]) or [])
        for reason in dict.fromkeys(reasons):
            queue_rows.append((record["record_id"], reason, _primary(record), text[:240]))
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["record_id", "reason", "current_guess", "evidence"])
        writer.writerows(queue_rows)

    lines = ["# Module assignment report", "", f"Taxonomy {TAX.version}. Records: {len(records)}.", ""]
    lines.append("| Module | Records | Rule | Curated | Unknown processivity | Conflicts | Assay | Mode | Bead |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    by_module = defaultdict(list)
    for record in records:
        by_module[_primary(record)].append(record)
    for module in TAX.modules:
        rows = by_module.get(module.id, [])
        n = len(rows) or 1
        def share(pred, rows=rows, n=len(rows)):
            return f"{(100 * sum(1 for r in rows if pred(r)) / n):.1f}%" if rows else "0"
        conflicts = share(lambda r: "processivity conflict" in reviews.get(r["record_id"], []))
        lines.append(
            f"| {module.id} | {len(rows)} | {share(lambda r: _method(r) == 'rule')} | {share(lambda r: _method(r) in {'curated', 'author'})} | "
            f"{share(lambda r: r['classification'].get('processivity') == 'unknown')} | {conflicts} | "
            f"{share(lambda r: r['classification'].get('assay_type'))} | {share(lambda r: r['classification'].get('measurement_modes'))} | "
            f"{share(lambda r: r['classification'].get('bead_geometry'))} |"
        )
    lines += ["", "## Sub-modules", ""]
    sub_counts = Counter()
    for record in records:
        for sub in _subs(record):
            sub_counts[( _primary(record), sub)] += 1
    for module in TAX.modules:
        for sub in module.submodules:
            lines.append(f"- {module.id} / {sub}: {sub_counts[(module.id, sub)]}")
    missed = [rule.id for rule in TAX.keywords if keyword_hits[rule.id] == 0]
    lines += ["", "## Keyword rules with no hit", "", ", ".join(missed) or "(none)", ""]
    lines.append(f"Curation queue rows: {len(queue_rows)}.")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("queue", len(queue_rows), "report", REPORT)


def _shards_and_index(records: list[dict]) -> None:
    by_id = {r["record_id"]: r for r in records}
    index = []
    shard_dir = DATA / "records"
    for path in sorted(shard_dir.glob("r-*.js")):
        text = path.read_text(encoding="utf-8")
        start = text.index("[")
        end = text.rindex("]") + 1
        shard_no = int(path.stem.split("-")[1])
        rows = json.loads(text[start:end])
        replaced = []
        for row in rows:
            stamped = by_id.get(row["record_id"])
            replaced.append(stamped if stamped else row)
            if stamped:
                index.append(index_row(stamped, shard_no))
        path.write_text(f"SMASH.registerShard({shard_no}," + json.dumps(replaced, ensure_ascii=False, separators=(",", ":")) + ");\n", encoding="utf-8")
    if len(index) != len(records):
        raise SystemExit(f"index {len(index)} != records {len(records)}")
    meta = {"built": "2026-10-18", "n": len(records), "schema_version": "3.2.0"}
    packed = pack_index(index)
    (DATA / "index.js").write_text(
        "SMASH.meta=" + json.dumps(meta) + ";\nSMASH.index=SMASH.unpackIndex(" + json.dumps(packed, ensure_ascii=False, separators=(",", ":")) + ");\n",
        encoding="utf-8",
    )
    module_of = {r["record_id"]: _primary(r) for r in records}
    (DATA / "module_of.js").write_text("SMASH.moduleOf=" + json.dumps(module_of, separators=(",", ":")) + ";\n", encoding="utf-8")
    labels = {m.id: {"label": m.label, "table3": m.table3_type, "description": m.description, "submodules": m.submodules} for m in TAX.modules}
    (DATA / "modules.js").write_text("SMASH.moduleMeta=" + json.dumps(labels, ensure_ascii=False) + ";\n", encoding="utf-8")


def _pages(records: list[dict]) -> None:
    by_module = defaultdict(list)
    for record in records:
        by_module[_primary(record)].append(record)
    groups = [
        ("Unfolding", "unfolding"),
        ("DNA–protein", "dna_protein"),
        ("Force generation", "force_generation"),
        ("Rheology", "rheology"),
        ("Extended", "extended"),
    ]
    cards = []
    for title, table in groups:
        members = [m for m in TAX.modules if m.table3_type == table]
        bits = []
        for module in members:
            rows = by_module[module.id]
            linked = sum(1 for r in rows if (r.get("data_availability") or {}).get("has_linked_dataset"))
            share = (100 * linked / len(rows)) if rows else 0
            bits.append(
                f'<a class="card tech-card" href="modules/{html.escape(module.id)}.html"><h3>{html.escape(module.label)}</h3>'
                f'<p>{html.escape(module.description)}</p><p class="muted">{len(rows)} records · {share:.0f}% with a linked dataset</p></a>'
            )
        cards.append(f'<h2>{html.escape(title)}</h2><div class="card-grid">{"".join(bits)}</div>')
    note = (
        "<p>Modules follow Halma 2025 (Table 3), Haghizadeh, Iftikhar, Dandpat and Simpson 2023 "
        "(biological questions) and Malinowska, van Mameren, Peterman, Wuite and Heller 2024 "
        "(measurement modes and assays). The full references are in the taxonomy citation file.</p>"
    )
    _write_page(WEB / "modules.html", "Experiment modules", "Thirteen experiment modules", "".join(cards) + "<h2>How modules are defined</h2>" + note, prefix="")
    out_dir = WEB / "modules"
    out_dir.mkdir(exist_ok=True)
    for module in TAX.modules:
        rows = by_module[module.id]
        years = [((r.get("publication") or {}).get("year")) for r in rows]
        years = [y for y in years if isinstance(y, int)]
        linked = sum(1 for r in rows if (r.get("data_availability") or {}).get("has_linked_dataset"))
        share = (100 * linked / len(rows)) if rows else 0
        span = f"{min(years)}–{max(years)}" if years else "—"
        subs = Counter(sub for r in rows for sub in _subs(r))
        tabs = "".join(
            f'<a class="chip" href="../explore.html?module={html.escape(module.id)}&sub={html.escape(sub)}">{html.escape(sub.replace("_", " "))} · {subs[sub]}</a>'
            for sub in module.submodules
        )
        measured = _measured(rows)
        note_extra = ""
        if module.id in {"processive_motors", "force_generation"}:
            other = "force_generation" if module.id == "processive_motors" else "processive_motors"
            note_extra = (
                '<p class="notice">A one-bead run length and a three-bead working stroke are not the same measurement '
                "(Halma 2025). "
                f'<a href="{other}.html">The other force-generation module</a> is kept separate so the two are not pooled.</p>'
            )
        queued = sum(1 for r in rows if r["classification"].get("processivity") == "unknown" or "no experiment class" in " ".join((e.get("snippet") or "") for e in r.get("provenance") or []))
        body = (
            f'<p>{html.escape(module.description)}</p>'
            f'<div class="stat-row"><div class="stat-tile"><div class="label">Records</div><div class="value">{len(rows)}</div></div>'
            f'<div class="stat-tile"><div class="label">Years</div><div class="value" style="font-size:1.4rem">{html.escape(span)}</div></div>'
            f'<div class="stat-tile"><div class="label">Linked dataset</div><div class="value">{share:.0f}%</div></div></div>'
            f'{note_extra}<h2>Sub-modules</h2><div class="chip-row"><a class="chip" href="../explore.html?module={html.escape(module.id)}">All</a>{tabs}</div>'
            f'<h2>What has been measured</h2>{measured}'
            f'<h2>Breakdowns</h2>{_breakdowns(rows)}'
            f'<h2>Canonical systems</h2><p>{" ".join(_system_link(s, module.id) for s in module.canonical_systems) or "None listed for this module."}</p>'
            f'<p><a href="../submit.html?module={html.escape(module.id)}">Records needing curation ({queued})</a></p>'
            f'<p><a href="../explore.html?module={html.escape(module.id)}">Open these records in Explore</a></p>'
        )
        _write_page(out_dir / f"{module.id}.html", module.label, module.label, body, prefix="../")


def _system_name(record: dict) -> str:
    entities = ((record.get("biological_system") or {}).get("entities")) or []
    for entity in entities:
        if entity.get("name") and (entity.get("evidence") or {}).get("method") != "europepmc_textmining":
            return entity["name"]
    return entities[0]["name"] if entities and entities[0].get("name") else ""


def _loading(record: dict) -> str:
    assay = record.get("assay") or {}
    rate = assay.get("loading_rate") or assay.get("pulling_speed") or assay.get("loading_rate_text")
    if isinstance(rate, dict):
        value = rate.get("value")
        unit = rate.get("unit") or ""
        return f"{value} {unit}".strip() if value is not None else ""
    return str(rate or "")


def _measured(rows: list[dict]) -> str:
    groups: dict[tuple, list] = defaultdict(list)
    for record in rows:
        assay = record["classification"].get("assay_type") or ""
        technique = (record.get("technique") or {}).get("primary") or ""
        buffer = (record.get("solution") or {}).get("buffer") or ""
        system = _system_name(record)
        loading = _loading(record)
        for result in record.get("results") or []:
            mode = result.get("measurement_mode") or ""
            key = (system, result.get("quantity"), mode, assay, technique, loading, buffer)
            if result.get("value") is not None:
                groups[key].append(result.get("value"))
    if not groups:
        return "<p>No extracted results for this module yet.</p>"
    items = sorted(groups.items(), key=lambda item: -len(item[1]))[:12]
    body = ["<div class=\"data-table-wrap\"><table class=\"data-table\"><thead><tr><th>System</th><th>Observable</th><th>Assay</th><th>Mode</th><th>Technique</th><th>Loading rate</th><th>Buffer</th><th>Values</th></tr></thead><tbody>"]
    for (system, quantity, mode, assay, technique, loading, buffer), values in items:
        shown = ", ".join(str(v) for v in values[:6])
        body.append(
            "<tr>"
            f"<td>{html.escape(system)}</td><td>{html.escape(str(quantity))}</td><td>{html.escape(assay)}</td>"
            f"<td>{html.escape(mode)}</td><td>{html.escape(technique)}</td><td>{html.escape(loading)}</td>"
            f"<td>{html.escape(str(buffer)[:80])}</td><td>{html.escape(shown)}</td></tr>"
        )
    body.append("</tbody></table></div><p class=\"muted\">Each row keeps one system, assay and measurement mode. Values are not pooled across modes.</p>")
    return "".join(body)


def _breakdowns(rows: list[dict]) -> str:
    tech_assay = Counter(((record.get("technique") or {}).get("primary") or "unknown", record["classification"].get("assay_type") or "unset") for record in rows)
    modes = Counter(mode for record in rows for mode in (record["classification"].get("measurement_modes") or ["unset"]))
    fluo = Counter(name for record in rows for name in (((record["classification"].get("correlative_fluorescence") or {}).get("modalities")) or ["none"]))
    years = Counter((record.get("publication") or {}).get("year") for record in rows if isinstance((record.get("publication") or {}).get("year"), int))
    def table(title, pairs):
        body = "".join(f"<tr><td>{html.escape(str(a))}</td><td>{html.escape(str(b))}</td><td class=\"num\">{n}</td></tr>" for (a, b), n in pairs)
        return f"<h3>{html.escape(title)}</h3><table class=\"data-table\"><tbody>{body}</tbody></table>"
    year_rows = "".join(f"<tr><td>{year}</td><td class=\"num\">{n}</td></tr>" for year, n in sorted(years.items())[-12:])
    return (
        table("Technique × assay", tech_assay.most_common(8))
        + f"<h3>Measurement mode</h3><table class=\"data-table\"><tbody>{''.join(f'<tr><td>{html.escape(k)}</td><td class=\"num\">{n}</td></tr>' for k, n in modes.most_common())}</tbody></table>"
        + f"<h3>Correlative fluorescence</h3><table class=\"data-table\"><tbody>{''.join(f'<tr><td>{html.escape(k)}</td><td class=\"num\">{n}</td></tr>' for k, n in fluo.most_common())}</tbody></table>"
        + f"<h3>Records over time</h3><table class=\"data-table\"><tbody>{year_rows}</tbody></table>"
    )


def _system_link(token: str, module_id: str) -> str:
    if token.startswith("UniProt:"):
        acc = token.split(":", 1)[1]
        return (
            f'<a href="https://www.uniprot.org/uniprotkb/{html.escape(acc)}/entry">{html.escape(token)}</a> '
            f'<a href="../explore.html?q={html.escape(acc)}&module={html.escape(module_id)}">records</a>'
        )
    ident = token.split(":")[-1]
    return f'<a href="../explore.html?q={html.escape(ident)}&module={html.escape(module_id)}">{html.escape(token)}</a>'


def _write_page(path: Path, title: str, heading: str, body: str, prefix: str) -> None:
    path.write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)} | SMASH-BIO</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{prefix}css/style.css">
  <script src="{prefix}js/app.js"></script>
</head>
<body>
  <nav id="site-nav"></nav>
  <header class="page-header"><div class="container"><h1>{html.escape(heading)}</h1></div></header>
  <main class="container" style="padding-bottom:48px">{body}</main>
  <footer id="site-footer"></footer>
  <script>SMASH.renderChrome();</script>
</body>
</html>
""", encoding="utf-8")


def _schema_js() -> None:
    schemas = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (WEB / "schema").glob("*.json")}
    js(DATA / "schema.js", "SMASH.schemas", schemas)


def _copy_taxonomy() -> None:
    dest = WEB / "schema" / "taxonomy"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(ROOT / "taxonomy", dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def _primary(record: dict) -> str:
    return next(m["module_id"] for m in record["classification"]["modules"] if m["role"] == "primary")


def _subs(record: dict) -> list[str]:
    return next(m.get("submodules") or [] for m in record["classification"]["modules"] if m["role"] == "primary")


def _method(record: dict) -> str:
    return next(m.get("method") or "rule" for m in record["classification"]["modules"] if m["role"] == "primary")


if __name__ == "__main__":
    main()
