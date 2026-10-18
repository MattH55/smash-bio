"""Phase 6 verification for the Simulations category.

Four checks that a reader can re-run:

* **grounding** — every extracted value's evidence snippet must appear in the
  source text the record was built from (title/abstract, or the open-access
  Methods text when it was used);
* **units** — no value marked `reduced` carries a physical unit, and a
  `reduced_with_stated_conversion` model must state its conversion;
* **identifiers** — a published record may only carry resolver-verified codes;
* **site assets** — every local file a `/sim/` page references exists.

It also prints a deterministic spot-check sample. Run it from ``hub/``::

    python -m sim.verify
"""
import gzip
import json
import random
import re
from pathlib import Path

from modules.base import hub_dir
from sim import identifiers, schema
from sim.extract import clean_text


PHYSICAL_UNITS = {"pN", "nN", "nm", "angstrom", "kBT", "kcal/mol", "kJ/mol", "1/s", "pN/s",
                  "nm/s", "pN/nm", "s", "ms", "us", "ns", "ps", "N/m", "um", "pN nm"}


def _normalise(text):
    return re.sub(r"\s+", " ", clean_text(text)).strip().lower()


def source_texts(out_dir):
    """doi -> source text, from the classified corpus and the parsed full texts."""
    from common import load_jsonl
    from sim.fulltext import load_index, parsed_for
    from sim.spec import SIM

    index = load_index(SIM, out_dir)
    texts = {}
    for article in load_jsonl(Path(out_dir) / "sim_articles_classified.jsonl"):
        parts = [article.get("title"), article.get("abstract")]
        parsed = parsed_for(article.get("epmc_id"), index) or {}
        if parsed.get("methods_text"):
            parts.append(parsed["methods_text"])
        key = article.get("doi") or article.get("epmc_id")
        if key:
            texts[key] = _normalise(" ".join(filter(None, parts)))
    return texts


def grounding_failures(records, texts):
    failures, checked, skipped = [], 0, 0
    for record in records:
        key = record["source"].get("doi") or record["source"].get("pmid")
        text = texts.get(key)
        if not text:
            skipped += 1
            continue
        for result in record.get("results") or []:
            for evidence in result.get("provenance") or []:
                snippet = _normalise(evidence.get("snippet"))
                if not snippet:
                    continue
                checked += 1
                if snippet not in text:
                    failures.append((record["record_id"], result["quantity"], snippet[:80]))
    return {"checked": checked, "skipped_records": skipped, "failures": failures}


def unit_failures(records):
    failures = []
    for record in records:
        for result in record.get("results") or []:
            if result.get("unit_system") == "reduced" and result["unit"] in PHYSICAL_UNITS:
                failures.append((record["record_id"], result["quantity"], result["unit"]))
        if record["model"].get("unit_system") == "reduced_with_stated_conversion":
            conversions = record["model"].get("unit_conversions") or {}
            if not any(key for key in conversions if key not in ("statement", "evidence")):
                failures.append((record["record_id"], "claimed stated conversion but none recorded", ""))
    return failures


def identifier_failures(records):
    failures = []
    for record in records:
        for entity in record["system"].get("entities") or []:
            for item in entity.get("identifiers") or []:
                if not item.get("verified"):
                    failures.append((record["record_id"], item.get("scheme"), item.get("id")))
    return failures


def site_asset_failures(website):
    website = Path(website)
    missing = []
    pattern = re.compile(r'(?:src|href)="([^"#:]+)"')
    for page in sorted((website / "sim").glob("*.html")):
        for target in pattern.findall(page.read_text(encoding="utf-8")):
            if target.startswith(("http", "mailto:", "data:")):
                continue
            if not (page.parent / target).exists():
                missing.append((page.name, target))
    return missing


def spot_check(records, count=15, seed=20261011):
    rng = random.Random(seed)
    sample = rng.sample(records, min(count, len(records)))
    rows = []
    for record in sample:
        links = (record.get("links") or {}).get("experimental_matches") or []
        rows.append({
            "record_id": record["record_id"],
            "system": record["system"]["name"],
            "model": record["model"].get("family"),
            "software": [item["name"] for item in record["model"].get("software") or []],
            "unit_system": record["model"].get("unit_system"),
            "mode": record["protocol"].get("mode"),
            "n_results": len(record.get("results") or []),
            "results": [(r["quantity"], r.get("value"), r["unit"]) for r in record.get("results") or []],
            "n_links": len(links),
            "match_levels": sorted({link["match_level"] for link in links}),
            "source": record["source"].get("doi") or record["source"].get("url"),
        })
    return rows


def run(out_dir=None, website=None, write_report=True):
    out_dir = Path(out_dir or (hub_dir() / "out" / "sim"))
    website = Path(website or (hub_dir().parent / "website"))
    records = [json.loads(line) for line in
               (out_dir / "sim_records.jsonl").read_text(encoding="utf-8").splitlines()
               if line.strip()]
    validator = schema.validator()
    invalid = [record["record_id"] for record in records if next(validator.iter_errors(record), None)]

    published = []
    gz = website / "downloads" / "sim" / "smash-sim-records.jsonl.gz"
    if gz.exists():
        with gzip.open(gz, "rt", encoding="utf-8") as handle:
            published = [json.loads(line) for line in handle if line.strip()]

    report = {
        "n_records": len(records),
        "n_invalid": len(invalid),
        "invalid": invalid,
        "n_published": len(published),
        "grounding": grounding_failures(records, source_texts(out_dir)),
        "units": unit_failures(records),
        "identifiers": identifier_failures(records),
        "site_assets": site_asset_failures(website),
        "spot_check": spot_check(records),
        "identifiers_table": str(Path(identifiers.TABLE_PATH)),
    }
    if write_report:
        path = hub_dir().parent / "docs" / "sim" / "verification.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(report), encoding="utf-8")
        report["report_path"] = str(path)
    return report


def _render(report):
    grounding = report["grounding"]
    lines = [
        "# Simulations category — verification",
        "",
        "Produced by `python -m sim.verify`. Re-run it after any pipeline change.",
        "",
        "## Summary",
        "",
        f"- records built: **{report['n_records']}**, schema failures: **{report['n_invalid']}**",
        f"- records published in the download: **{report['n_published']}**",
        f"- evidence snippets checked against the source text: **{grounding['checked']}** "
        f"(failures: **{len(grounding['failures'])}**; records without source text: "
        f"{grounding['skipped_records']})",
        f"- reduced-unit violations: **{len(report['units'])}**",
        f"- unverified identifiers in published records: **{len(report['identifiers'])}**",
        f"- missing local assets referenced by `/sim/` pages: **{len(report['site_assets'])}**",
        "",
        "## Spot-check sample (15 records)",
        "",
        "| record | system | model | units | n results | results | experiment links |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["spot_check"]:
        results = "; ".join(f"{quantity}={value} {unit}" for quantity, value, unit in row["results"])
        lines.append(f"| {row['record_id']} | {row['system'][:40]} | {row['model']} | "
                     f"{row['unit_system']} | {row['n_results']} | {results[:80]} | "
                     f"{row['n_links']} ({', '.join(row['match_levels']) or 'none'}) |")
    lines += ["", "## Failures", ""]
    for section in ("units", "identifiers", "site_assets"):
        for failure in report[section]:
            lines.append(f"- {section}: {failure}")
    for failure in grounding["failures"]:
        lines.append(f"- grounding: {failure}")
    if not (report["units"] or report["identifiers"] or report["site_assets"]
            or grounding["failures"]):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main():  # pragma: no cover - manual verification step
    report = run()
    print(json.dumps({key: value for key, value in report.items() if key != "spot_check"}, indent=1))


if __name__ == "__main__":  # pragma: no cover
    main()