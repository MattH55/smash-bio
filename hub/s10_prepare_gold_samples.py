"""Prepare reproducible, blinded Milestone-1 gold-set annotation samples.

This step writes source/context fields only.  Human labels, reviewer identities,
dates, and adjudication fields are deliberately left blank.  Deposit families
are expanded back to their member identifiers before sampling so reviewers can
assign independent family IDs rather than being shown the harvester result.
"""
import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from datetime import date
from pathlib import Path


HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
GOLD = HERE / "gold"
DEFAULT_SEED = 20261010
ANNOTATION_PREFIXES = ("human_", "adjudicated_")
ANNOTATION_FIELDS = {"annotator", "annotation_date", "second_reviewer", "adjudication_notes", "file_opened"}


def load_jsonl(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def template_fields(name):
    with (GOLD / f"{name}.template.csv").open(encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_fields(name):
    return [field for field in template_fields(name)
            if not field.startswith(ANNOTATION_PREFIXES) and field not in ANNOTATION_FIELDS]


def source_digest(path, fields):
    digest = hashlib.sha256()
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            payload = json.dumps([row.get(field, "") for field in fields], ensure_ascii=False, separators=(",", ":"))
            digest.update((payload + "\n").encode("utf-8"))
    return digest.hexdigest()


def decade(year):
    try:
        return str((int(year) // 10) * 10)
    except (TypeError, ValueError):
        return "unknown"


def stratified_sample(rows, size, key, rng, initial=()):
    """Round-robin shuffled strata, preserving any required initial rows."""
    if size > len(rows):
        raise ValueError(f"requested {size} rows from a population of {len(rows)}")
    selected = []
    seen = set()
    for row in initial:
        identity = id(row)
        if identity not in seen and len(selected) < size:
            selected.append(row)
            seen.add(identity)

    buckets = defaultdict(list)
    for row in rows:
        if id(row) not in seen:
            buckets[key(row)].append(row)
    for bucket in buckets.values():
        rng.shuffle(bucket)

    keys = sorted(buckets, key=str)
    rng.shuffle(keys)
    while len(selected) < size:
        progressed = False
        for bucket_key in keys:
            if buckets[bucket_key] and len(selected) < size:
                selected.append(buckets[bucket_key].pop())
                progressed = True
        if not progressed:
            break
    return selected


def study_rows(records, size, rng):
    curated = [r for r in records if r.get("curation", {}).get("level") in ("curated", "author_verified")]
    rng.shuffle(curated)
    required_curated = curated[:min(15, len(curated), size)]

    def study_stratum(record):
        technique = record.get("technique", {}).get("primary") or "unknown"
        return technique, decade(record.get("publication", {}).get("year"))

    sampled = stratified_sample(records, size, study_stratum, rng, required_curated)
    result = []
    for record in sampled:
        publication = record.get("publication", {})
        technique = record.get("technique", {}).get("primary") or ""
        result.append({
            "source_record_id": record.get("record_id", ""),
            "publication_doi": publication.get("doi") or "",
            "technique": technique,
            "publication_year": publication.get("year") or "",
        })
    return result


def expand_deposit_members(families):
    """Return neutral member rows without exposing predicted family/relevance."""
    members = []
    seen = set()
    for family in families:
        identifiers = []
        canonical = family.get("canonical_doi")
        if canonical:
            identifiers.append(canonical)
        identifiers.extend(family.get("version_dois") or [])
        if not identifiers:
            identifier = family.get("url") or family.get("doi") or family.get("family_id")
            if identifier:
                identifiers.append(identifier)
        for identifier in identifiers:
            normalized = str(identifier).strip()
            if not normalized or normalized.lower() in seen:
                continue
            seen.add(normalized.lower())
            members.append({
                "source_deposit_id": normalized,
                "doi_or_url": normalized,
                "repository": family.get("repository") or "",
                "linked_study_record_id": ";".join(sorted(family.get("linked_records") or [])),
                "_year": family.get("year"),
            })
    return members


def deposit_rows(families, size, rng):
    members = expand_deposit_members(families)
    sampled = stratified_sample(
        members,
        size,
        lambda row: (row.get("repository") or "unknown", decade(row.get("_year"))),
        rng,
    )
    return [{k: v for k, v in row.items() if not k.startswith("_")} for row in sampled]


def write_rows(name, rows, force=False):
    destination = GOLD / f"{name}.csv"
    if destination.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {destination}; use --force to replace it")
    fields = template_fields(name)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for source in rows:
            writer.writerow({field: source.get(field, "") for field in fields})
    return destination


def write_manifest(seed, study_count, deposit_count, member_count, paths):
    records_path = OUT / "records.jsonl"
    families_path = OUT / "datasets_hub.jsonl"
    manifest = {
        "schema_version": 1,
        "created": date.today().isoformat(),
        "seed": seed,
        "requested_rows": {"studies": study_count, "deposits": deposit_count, "files": 0},
        "deposit_member_population": member_count,
        "sources": {
            "records.jsonl": {"sha256": sha256(records_path)},
            "datasets_hub.jsonl": {"sha256": sha256(families_path)},
        },
        "batches": {},
        "limitations": [
            "files.csv is header-only because stable file IDs and file URLs are not retained by the pipeline",
            "human, reviewer, and adjudication fields are intentionally blank at generation time",
        ],
    }
    for path in paths:
        name = path.stem
        immutable_fields = source_fields(name)
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        manifest["batches"][path.name] = {
            "rows": len(rows),
            "sha256_at_generation": sha256(path),
            "source_fields": immutable_fields,
            "source_sha256": source_digest(path, immutable_fields),
        }
    destination = GOLD / "sample_manifest.json"
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return destination


def prepare(study_count=150, deposit_count=300, seed=DEFAULT_SEED, force=False):
    rng = random.Random(seed)
    records = load_jsonl(OUT / "records.jsonl")
    families = load_jsonl(OUT / "datasets_hub.jsonl")
    studies = study_rows(records, study_count, rng)
    deposits = deposit_rows(families, deposit_count, rng)
    destinations = [GOLD / f"{name}.csv" for name in ("studies", "deposits", "files")]
    existing = [path for path in destinations if path.exists()]
    if existing and not force:
        names = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"refusing to overwrite {names}; use --force to replace them")
    paths = [
        write_rows("studies", studies, force),
        write_rows("deposits", deposits, force),
        # No file-level URLs are retained by the current harvester.  Preserve the
        # agreed schema but do not invent file records or content-tier labels.
        write_rows("files", [], force),
    ]
    member_count = len(expand_deposit_members(families))
    paths.append(write_manifest(seed, study_count, deposit_count, member_count, paths))
    return paths, member_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--studies", type=int, default=150)
    parser.add_argument("--deposits", type=int, default=300)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--force", action="store_true", help="replace existing working annotation CSVs")
    args = parser.parse_args()
    paths, member_count = prepare(args.studies, args.deposits, args.seed, args.force)
    print(f"study sample: {args.studies}; deposit sample: {args.deposits} from {member_count} member identifiers")
    for path in paths:
        print(path)
    print("files.csv is header-only: the current harvester does not retain file-level URLs; file-tier sampling remains blocked")


if __name__ == "__main__":
    main()