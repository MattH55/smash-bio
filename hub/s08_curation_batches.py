"""Step 8 (optional) - package high-value records for AI-assisted curation.

Selects primary-research records that have a linked public dataset AND open-access methods
text, and writes compact packets (current auto-extracted record + Methods text + data
statement) to curation_batches/batch_NN.json. Reviewer output goes to curated_json/<record>.json
(schema v3 subset, curation.level = "ai_assisted") and is merged by step 6.
"""
import json
import sys
from pathlib import Path

from common import OUT, load_json, load_jsonl
from s05_fulltext import FT_CACHE

HUB = Path(__file__).resolve().parent
BATCH_DIR = HUB / "curation_batches"
PER_BATCH = int(sys.argv[2]) if len(sys.argv) > 2 else 8
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 160


def main():
    recs = load_jsonl(OUT / "records.jsonl")
    done = {p.stem for p in (HUB / "curated_json").glob("*.json")}
    cand = [r for r in recs if r["scope"]["article_kind"] == "primary_research" and r["data_availability"]["has_linked_dataset"]
            and r["curation"]["level"] == "auto_fulltext" and r["publication"].get("pmcid") and r["record_id"] not in done]
    cand.sort(key=lambda r: (r["data_availability"].get("raw_traces_available", False), r["publication"].get("year") or 0), reverse=True)
    cand = cand[:LIMIT]
    BATCH_DIR.mkdir(exist_ok=True)
    for p in BATCH_DIR.glob("batch_*.json"):
        p.unlink()
    for b in range(0, len(cand), PER_BATCH):
        packets = []
        for r in cand[b:b + PER_BATCH]:
            ft = json.loads((FT_CACHE / f"{r['publication']['pmcid']}.json").read_text(encoding="utf-8"))
            slim = {k: r[k] for k in ("record_id", "technique", "hardware", "assay", "biological_system", "solution", "results")}
            slim["publication"] = {k: r["publication"].get(k) for k in ("doi", "title", "year", "journal", "abstract")}
            slim["data_availability"] = {"status": r["data_availability"]["status"],
                                         "datasets": [{k: d.get(k) for k in ("id", "title", "repository", "file_formats", "content")} for d in r["data_availability"]["datasets"]]}
            packets.append({"record": slim, "methods_text": ft.get("methods_text", "")[:45000],
                            "data_statement": " ".join(d["text"] for d in ft.get("data_availability", []))[:3000]})
        (BATCH_DIR / f"batch_{b // PER_BATCH:02d}.json").write_text(json.dumps(packets, ensure_ascii=False), encoding="utf-8")
    print(f"{len(cand)} records in {(len(cand) + PER_BATCH - 1) // PER_BATCH} batches -> {BATCH_DIR}")


if __name__ == "__main__":
    main()
