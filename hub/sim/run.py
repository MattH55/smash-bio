"""CLI driver for the Simulations category.

    python -m sim.run --step all
    python -m sim.run --step classify
    python -m sim.run --step identifiers          # warm the shared resolver table

Intermediates and outputs default to ``hub/out/sim``; pass ``--out-dir`` to keep
a small smoke run away from the real corpus. Site files (``website/sim/`` and
``website/downloads/sim/``) are only written by the ``outputs`` step when no
``--out-dir`` was given.
"""
import argparse
from pathlib import Path

from common import OUT, load_jsonl, save_jsonl
from modules.base import hub_dir


STEPS = ("harvest", "classify", "fulltext", "datasets", "records", "match",
         "outputs", "identifiers", "audit", "all")


def run(step="all", limit=None, min_year=1986, out_dir=None, page_size=1000,
        max_fulltext=None, smfs_path=None):
    from sim.spec import SIM

    spec = SIM
    explicit_out = out_dir is not None
    out_dir = Path(out_dir or (OUT / spec.slug))
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"slug": spec.slug, "step": step, "out_dir": str(out_dir)}
    raw = out_dir / f"{spec.slug}_articles_raw.jsonl"
    classified = out_dir / f"{spec.slug}_articles_classified.jsonl"
    records_path = out_dir / f"{spec.slug}_records.jsonl"

    if step in ("harvest", "all"):
        from sim import harvest as harvest_mod
        rows = harvest_mod.harvest(spec, min_year=min_year, limit=limit,
                                   page_size=page_size, out_path=raw)
        summary["harvested"] = len(rows)

    if step in ("classify", "all") and raw.exists():
        from sim import classify as classify_mod
        kept, tiers = classify_mod.classify_all(load_jsonl(raw), spec)
        save_jsonl(classified, kept)
        summary["tiers"] = dict(tiers)
        summary["kept"] = len(kept)

    if step in ("fulltext", "all") and classified.exists():
        from sim import fulltext as fulltext_mod
        index = fulltext_mod.build_index(load_jsonl(classified), spec, out_dir,
                                         max_articles=max_fulltext)
        summary["fulltext_parsed"] = len(index)

    if step in ("records", "all") and classified.exists():
        from sim import build_records as records_mod
        from sim import fulltext as fulltext_mod
        articles = [a for a in load_jsonl(classified) if a.get("tier") in ("core", "methods")]
        summary["in_scope"] = len(articles)
        records, skipped = records_mod.build_records(
            articles, spec, fulltext_index=fulltext_mod.load_index(spec, out_dir))
        from sim import ingest as ingest_mod
        entries, rows = ingest_mod.load_entries()
        dataset_rows = ingest_mod.dataset_records(entries, rows, spec, start=len(records) + 1)
        summary["dataset_records"] = len(dataset_rows)
        records.extend(dataset_rows)
        save_jsonl(records_path, records)
        summary["records"] = len(records)
        summary["skipped"] = dict(skipped)

    if step in ("datasets", "all"):
        from sim import ingest as ingest_mod
        entries, rows = ingest_mod.run(offline=explicit_out)
        summary["datasets"] = {entry["id"]: entry["status"] for entry in entries}

    if step in ("match", "all") and records_path.exists():
        from sim import match as match_mod
        summary["matches"] = match_mod.write_matches(
            load_jsonl(records_path), spec, out_dir=out_dir,
            smfs_path=Path(smfs_path or (OUT / "records.jsonl")))

    if step in ("outputs", "all") and records_path.exists():
        from sim import build_outputs as outputs_mod
        summary["outputs"] = outputs_mod.write_outputs(
            load_jsonl(records_path), spec,
            downloads_dir=(out_dir / "downloads") if explicit_out else None,
            data_dir=(out_dir / "data") if explicit_out else None)

    if step in ("identifiers", "all"):
        from sim import identifiers as ids
        from sim.gazetteer_sim import SIM_SYSTEMS
        pairs, seen = [], set()
        for term in SIM_SYSTEMS:
            for item in term["identifiers"]:
                pair = (item["scheme"], item["id"])
                if pair not in seen:
                    seen.add(pair)
                    pairs.append(pair)
        done, table = ids.warm(pairs)
        summary["identifiers_warmed"] = done
        summary["identifiers_unverified"] = sorted(
            key for key, row in table.items() if not row.get("verified"))

    if step in ("audit", "all") and raw.exists() and classified.exists():
        from sim import audit as audit_mod
        audit_rows = audit_mod.build_sample(load_jsonl(raw), load_jsonl(classified), spec)
        path = audit_mod.write_sample(
            audit_rows, hub_dir().parent / "docs" / "sim" / "scope_audit_sample.csv")
        summary["audit_sample"] = {"path": str(path), "n": len(audit_rows)}

    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the SMASH-SIM Simulations category.")
    parser.add_argument("--step", default="all", choices=STEPS)
    parser.add_argument("--limit", type=int, default=None, help="max hits per query tag")
    parser.add_argument("--page-size", type=int, default=1000, help="Europe PMC page size")
    parser.add_argument("--min-year", type=int, default=1986)
    parser.add_argument("--max-fulltext", type=int, default=None,
                        help="cap the number of full texts fetched in the fulltext step")
    parser.add_argument("--out-dir", default=None,
                        help="write intermediates/outputs here instead of hub/out/sim and website/")
    parser.add_argument("--smfs-path", default=None, help="path to hub/out/records.jsonl")
    args = parser.parse_args(argv)
    print(run(step=args.step, limit=args.limit, min_year=args.min_year,
              out_dir=args.out_dir, page_size=args.page_size,
              max_fulltext=args.max_fulltext, smfs_path=args.smfs_path))


if __name__ == "__main__":
    main()