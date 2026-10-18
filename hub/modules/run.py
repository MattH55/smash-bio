"""CLI driver for a technique module.

    python -m modules.run fret --step classify
    python -m modules.run spt --step all --limit 500 --min-year 2015

Every step reads and writes under ``hub/out`` by default. Pass ``--out-dir`` to
keep a small smoke run (``--limit``/``--page-size``) away from the real corpus;
only then are the downloads, site data and crossrefs also written there instead
of into ``website/``.
"""
import argparse
from pathlib import Path

from common import OUT, load_jsonl, save_jsonl
from modules.base import MODULES, get_module


STEPS = ("harvest", "classify", "fulltext", "records", "outputs", "crossrefs", "all")


def run(slug, step="all", limit=None, min_year=1986, out_dir=None, page_size=1000,
        max_fulltext=None):
    spec = get_module(slug)
    explicit_out = out_dir is not None
    out_dir = Path(out_dir or OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"slug": slug, "step": step, "out_dir": str(out_dir)}

    if step in ("harvest", "all"):
        from modules import harvest as harvest_mod
        rows = harvest_mod.harvest(spec, min_year=min_year, limit=limit, page_size=page_size,
                                   out_path=out_dir / f"{slug}_articles_raw.jsonl")
        summary["harvested"] = len(rows)

    if step in ("classify", "all"):
        from modules import classify as classify_mod
        articles = load_jsonl(out_dir / f"{slug}_articles_raw.jsonl")
        kept, tiers = classify_mod.classify_all(articles, spec)
        save_jsonl(out_dir / f"{slug}_articles_classified.jsonl", kept)
        summary["tiers"] = dict(tiers)
        summary["kept"] = len(kept)

    if step in ("fulltext", "all"):
        from modules import fulltext as fulltext_mod
        articles = load_jsonl(out_dir / f"{slug}_articles_classified.jsonl")
        index = fulltext_mod.build_index(articles, spec, out_dir, max_articles=max_fulltext)
        summary["fulltext_parsed"] = len(index)

    if step in ("records", "all"):
        from modules import build_records as records_mod
        from modules import fulltext as fulltext_mod
        articles = load_jsonl(out_dir / f"{slug}_articles_classified.jsonl")
        # only the brief's in-scope tiers become records; `peripheral` rows stay
        # in the classified file for the scope audit
        articles = [a for a in articles if a.get("tier") in ("core", "methods")]
        summary["in_scope"] = len(articles)
        records, skipped = records_mod.build_records(
            articles, spec, fulltext_index=fulltext_mod.load_index(spec, out_dir))
        save_jsonl(out_dir / f"{slug}_records.jsonl", records)
        summary["records"] = len(records)
        summary["skipped_ungrounded"] = skipped

    if step in ("outputs", "all"):
        from modules import build_outputs as outputs_mod
        records = load_jsonl(out_dir / f"{slug}_records.jsonl")
        summary["outputs"] = outputs_mod.write_outputs(
            records, spec,
            downloads_dir=(out_dir / "downloads") if explicit_out else None,
            data_dir=(out_dir / "data") if explicit_out else None,
        )

    if step in ("crossrefs", "all"):
        from modules import crossrefs as crossrefs_mod
        if explicit_out:
            rows = crossrefs_mod.collect_all(smfs_path=OUT / "records.jsonl", out_dir=out_dir,
                                             out_path=out_dir / "crossrefs.jsonl")
        else:
            rows = crossrefs_mod.collect_all()
        summary["crossrefs"] = len(rows)

    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a SMASH-BIO technique module.")
    parser.add_argument("slug", choices=sorted(MODULES))
    parser.add_argument("--step", default="all", choices=STEPS)
    parser.add_argument("--limit", type=int, default=None, help="max hits per query tag")
    parser.add_argument("--page-size", type=int, default=1000, help="Europe PMC page size")
    parser.add_argument("--min-year", type=int, default=1986)
    parser.add_argument("--max-fulltext", type=int, default=None,
                        help="cap the number of full texts fetched in the fulltext step")
    parser.add_argument("--out-dir", default=None,
                        help="write intermediates/outputs here instead of hub/out and website/")
    args = parser.parse_args(argv)
    print(run(args.slug, step=args.step, limit=args.limit, min_year=args.min_year,
              out_dir=args.out_dir, page_size=args.page_size,
              max_fulltext=args.max_fulltext))


if __name__ == "__main__":
    main()