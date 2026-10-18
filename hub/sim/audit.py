"""Stratified scope-audit sample for the Simulations category (brief Phase 3).

The classifier's tier is a rule-based decision, so it has to be auditable. This
module writes a 45-paper sample with an empty ``human_label`` column, stratified
by the classifier tier and, within a tier, round-robin across molecule types so
the sample is not all proteins. The sample is deterministic (fixed seed).
"""
import csv
import random
import re
from collections import defaultdict
from pathlib import Path


COLUMNS = [
    "audit_id", "epmc_id", "pmid", "doi", "title", "journal", "year", "query_tags",
    "auto_tier", "molecule_type", "model_families", "model_signal", "is_review",
    "is_methods_paper", "scope_reasons", "human_label", "human_notes", "url",
]

#: tier -> how many papers the sample takes from it (45 in total)
QUOTAS = (("core", 20), ("methods", 10), ("out_of_scope", 15))


def _model_signal(article, spec):
    text = " ".join(filter(None, [article.get("title"), article.get("abstract")]))
    signal = []
    for name, pattern in spec.software_patterns.items():
        if re.search(pattern, text, re.I):
            signal.append(f"software:{name}")
    for family, pattern in spec.model_family_patterns.items():
        if re.search(pattern, text, re.I):
            signal.append(f"family:{family}")
    if re.search(r"charmm|amber|opls|gromos|martini|awsem", text, re.I):
        signal.append("force_field")
    return ";".join(signal)


def build_sample(raw, classified, spec, seed=20261011):
    """Return the audit rows (list of dicts), deterministically sampled."""
    by_id = {row.get("epmc_id"): row for row in classified}
    pools = defaultdict(list)
    for article in raw:
        row = by_id.get(article.get("epmc_id")) or {}
        pools[row.get("tier", "out_of_scope")].append((article, row))

    rng = random.Random(seed)
    sample = []
    for tier, quota in QUOTAS:
        pool = pools.get(tier, [])
        buckets = defaultdict(list)
        for article, row in pool:
            buckets[row.get("molecule_type") or "unknown"].append((article, row))
        for bucket in buckets.values():
            bucket.sort(key=lambda pair: pair[0].get("epmc_id") or "")
            rng.shuffle(bucket)
        ordered, keys = [], sorted(buckets)
        while any(buckets[key] for key in keys):
            for key in keys:
                if buckets[key]:
                    ordered.append((key, buckets[key].pop()))
        chosen = ordered[:quota]
        for molecule_type, (article, row) in chosen:
            sample.append({
                "epmc_id": article.get("epmc_id"), "pmid": article.get("pmid"),
                "doi": article.get("doi"), "title": (article.get("title") or "").strip(),
                "journal": article.get("journal"), "year": article.get("year"),
                "query_tags": ";".join(sorted(set(article.get("query_tags") or []))),
                "auto_tier": tier, "molecule_type": molecule_type,
                "model_families": ";".join(row.get("model_families") or []),
                "model_signal": _model_signal(article, spec),
                "is_review": row.get("is_review", ""),
                "is_methods_paper": row.get("is_methods_paper", ""),
                "scope_reasons": ";".join(row.get("scope_reasons") or []),
                "human_label": "", "human_notes": "",
                "url": (f"https://doi.org/{article['doi']}" if article.get("doi")
                        else f"https://europepmc.org/article/{article.get('source') or 'MED'}/"
                             f"{article.get('epmc_id')}"),
            })
        if len(chosen) < quota:
            print(f"  ! only {len(chosen)} {tier} papers available (wanted {quota})")
    for index, row in enumerate(sample, start=1):
        row["audit_id"] = f"A{index:03d}"
    return sample


def write_sample(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in COLUMNS})
    return path