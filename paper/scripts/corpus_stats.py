#!/usr/bin/env python3
"""Compute every corpus number quoted in manuscript.md.

Reads only the release files in paper/data/ (see MANIFEST.txt) and prints one
JSON document. Nothing here mutates the data. Definitions follow
hub/s07_build_site.py::build_stats so the numbers agree with stats.html;
`--check` compares the overlapping totals against the site's own stats.js.

Usage:  python -I paper/scripts/corpus_stats.py [--check] > paper/out/corpus_stats.json
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
DATA = PAPER / "data"
ID_SCHEMES = ("uniprot", "rfam", "genbank", "chebi")
REPO_FAMILIES = ("Zenodo", "Figshare", "Dryad", "GitHub")
MIN_CHECKED_PER_YEAR = 10  # Fig. 3A: years with fewer checked papers are not drawn


def load_records() -> list[dict]:
    with gzip.open(DATA / "smash-smfs-records.jsonl.gz", "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


TECH_LABELS = {  # display names as on the site (website/js/app.js)
    "optical_tweezers": "Optical tweezers", "magnetic_tweezers": "Magnetic tweezers",
    "torque_tweezers": "Torque / rotational tweezers", "afm_smfs": "AFM force spectroscopy",
    "acoustic_force_spectroscopy": "Acoustic force spectroscopy", "centrifuge_force": "Centrifuge force microscopy",
    "nanopore_force": "Nanopore tweezers", "hydrodynamic_stretching": "Hydrodynamic / flow stretching",
    "biomembrane_force_probe": "Biomembrane force probe", "micropipette": "Micropipette manipulation",
    "tension_sensors": "Molecular tension sensors", "microneedle": "Glass microneedles",
    "force_spectroscopy_unspecified": "Force spectroscopy (unspecified)",
}


def pct(n: int, d: int) -> float:
    return round(100 * n / d, 1) if d else 0.0


def repo_family(name: str) -> str:
    return name if name in REPO_FAMILIES else "other"


def smfs_stats(recs: list[dict], deposits: list[dict]) -> dict:
    da = lambda r: r["data_availability"]  # noqa: E731
    counted = [d for d in deposits if d["counted_in_site_total"] == "True"]
    fulltext = [r for r in recs if da(r).get("fulltext_checked")]
    years = [r["publication"]["year"] for r in recs if r["publication"].get("year")]
    out: dict = {
        "n_records": len(recs),
        "n_core": sum(r["scope"]["tier"] == "core" for r in recs),
        "n_methods": sum(r["scope"]["tier"] == "methods" for r in recs),
        "n_primary_research_methods_preprint": sum(
            r["scope"]["article_kind"] in ("primary_research", "methods", "preprint") for r in recs),
        "year_min": min(years), "year_max": max(years),
        "n_with_dataset": sum(bool(da(r)["has_linked_dataset"]) for r in recs),
        "n_with_any_data": sum(bool(da(r).get("has_any_data")) for r in recs),
        "n_with_code": sum(bool(da(r).get("has_linked_code")) for r in recs),
        "n_with_raw_traces": sum(bool(da(r).get("raw_traces_available")) for r in recs),
        "n_not_checked": sum(da(r)["status"] == "unknown_no_fulltext" for r in recs),
        "n_fulltext_checked": len(fulltext),
        "data_status": dict(Counter(da(r)["status"] for r in recs).most_common()),
        "n_open_access": sum(bool(r["publication"].get("open_access")) for r in recs),
        "n_deposits": len(counted),
        "n_deposits_all_labels": len(deposits),
        "deposits_by_repository": dict(Counter(repo_family(d["repository"]) for d in counted).most_common()),
        "deposits_by_resource_type": dict(Counter((d["resource_type"] or "unspecified").lower() for d in counted).most_common()),
        "n_deposits_unlinked": sum(not d["linked_records"] for d in counted),
        "n_curated": sum(r["curation"]["level"] == "curated" for r in recs),
        "n_author_verified": sum(r["curation"]["level"] == "author_verified" for r in recs),
        "curation_levels": dict(Counter(r["curation"]["level"] for r in recs).most_common()),
    }

    # per technique (Table 2) ------------------------------------------------
    by_tech: dict[str, dict] = {}
    for tech, n in Counter(r["technique"]["primary"] for r in recs).most_common():
        rs = [r for r in recs if r["technique"]["primary"] == tech]
        checked = [r for r in rs if da(r)["status"] != "unknown_no_fulltext"]
        with_ds = sum(bool(da(r)["has_linked_dataset"]) for r in rs)
        raw = sum(bool(da(r).get("raw_traces_available")) for r in rs)
        by_tech[tech] = {
            "records": n, "checked": len(checked),
            "with_dataset": with_ds, "pct_with_dataset": pct(with_ds, n),
            "pct_with_dataset_of_checked": pct(sum(bool(da(r)["has_linked_dataset"]) for r in checked), len(checked)),
            "raw_traces": raw, "pct_raw_traces": pct(raw, n),
        }
    out["by_technique"] = by_tech
    out["n_techniques"] = sum(k != "force_spectroscopy_unspecified" for k in by_tech)

    # identifiers and organisms ---------------------------------------------
    ids_all: dict[str, set] = defaultdict(set)
    ids_ver: dict[str, set] = defaultdict(set)
    for r in recs:
        for e in r["biological_system"]["entities"]:
            for i in e.get("identifiers", []):
                ids_all[i["scheme"]].add(i["id"])
                if i.get("verified"):
                    ids_ver[i["scheme"]].add(i["id"])
    out["identifiers_verified"] = {s: len(v) for s, v in sorted(ids_ver.items())}
    out["identifiers_any"] = {s: len(v) for s, v in sorted(ids_all.items())}
    out["n_systems_resolved"] = sum(len(ids_ver[s]) for s in ID_SCHEMES)
    out["n_systems_resolved_note"] = "distinct verified UniProt/Rfam/GenBank/ChEBI IDs"
    out["n_records_with_uniprot"] = sum(
        any(i["scheme"] == "uniprot" for e in r["biological_system"]["entities"] for i in e.get("identifiers", []))
        for r in recs)
    taxa = {o["ncbi_taxon"] for r in recs for o in r["biological_system"].get("organisms") or [] if o.get("ncbi_taxon")}
    out["n_organisms"] = len(taxa)

    # results ----------------------------------------------------------------
    results = [x for r in recs for x in r.get("results") or []]
    out["n_results_extracted"] = len(results)
    out["n_records_with_results"] = sum(bool(r.get("results")) for r in recs)
    out["results_per_observable_top10"] = dict(Counter(x["quantity"] for x in results).most_common(10))
    out["results_extraction"] = dict(Counter(x["source"]["extraction"] for x in results))

    # completeness -----------------------------------------------------------
    ov = [r["fair_completeness"]["overall"] for r in recs]
    ov_ft = [r["fair_completeness"]["overall"] for r in fulltext]
    ov_no = [r["fair_completeness"]["overall"] for r in recs if not da(r).get("fulltext_checked")]
    out["fair_completeness"] = {
        "mean_all": round(statistics.mean(ov), 3), "median_all": round(statistics.median(ov), 3),
        "mean_fulltext": round(statistics.mean(ov_ft), 3), "median_fulltext": round(statistics.median(ov_ft), 3),
        "mean_not_fulltext": round(statistics.mean(ov_no), 3), "median_not_fulltext": round(statistics.median(ov_no), 3),
        "n_fulltext": len(ov_ft),
        "note": "fulltext = records whose open-access full text was read (fulltext_checked)",
    }

    # availability by year ---------------------------------------------------
    by_year: dict[int, Counter] = defaultdict(Counter)
    for r in recs:
        if r["scope"]["article_kind"] in ("primary_research", "methods", "preprint"):
            y = r["publication"].get("year")
            if y and y >= 2000:
                c = by_year[y]
                c["n"] += 1
                c["checked"] += da(r)["status"] != "unknown_no_fulltext"
                c["with_dataset"] += bool(da(r)["has_linked_dataset"])
                c["public_repository"] += da(r)["status"] == "public_repository"
    out["availability_by_year"] = [
        {"year": y, "n": c["n"], "n_checked": c["checked"], "n_with_dataset": c["with_dataset"],
         "n_public_repository": c["public_repository"],
         "share_with_dataset_of_checked": round(c["with_dataset"] / c["checked"], 4) if c["checked"] else None,
         "drawn_in_fig3a": c["checked"] >= MIN_CHECKED_PER_YEAR}
        for y, c in sorted(by_year.items())]
    out["availability_by_year_note"] = "primary research + methods + preprints, 2000 onward"

    # Table 3 field coverage (Fig. 3C): same field definitions as build_stats
    hw = lambda r: r["hardware"]  # noqa: E731
    fields = {
        "Instrument make": lambda r: hw(r).get("make_of_setup"),
        "Laser wavelength": lambda r: (hw(r).get("optical") or {}).get("laser_wavelength"),
        "Trap / cantilever stiffness": lambda r: (hw(r).get("optical") or {}).get("trap_stiffness") or (hw(r).get("afm") or {}).get("spring_constant"),
        "Calibration method": lambda r: hw(r).get("calibration_technique"),
        "Detection device": lambda r: hw(r).get("detection_device"),
        "Temperature": lambda r: hw(r).get("temperature"),
        "Acquisition rate": lambda r: hw(r).get("acquisition_rate"),
        "Bead size": lambda r: r["assay"].get("bead_size"),
        "Attachment chemistry": lambda r: r["assay"].get("attachment_chemistry"),
        "Trap control mode": lambda r: r["assay"].get("trap_control"),
        "Buffer pH": lambda r: r["solution"].get("pH"),
        "Buffer components": lambda r: r["solution"].get("components"),
        "UniProt-linked construct": lambda r: any(i["scheme"] == "uniprot" for e in r["biological_system"]["entities"] for i in e.get("identifiers", [])),
        "Organism": lambda r: r["biological_system"].get("organisms"),
        "Linked dataset": lambda r: da(r)["has_linked_dataset"],
    }
    out["field_coverage_pct"] = {
        k: {"all": pct(sum(bool(f(r)) for r in recs), len(recs)),
            "fulltext": pct(sum(bool(f(r)) for r in fulltext), len(fulltext))}
        for k, f in fields.items()}
    out["field_cov"] = {re.sub(r"\W+", "_", k.lower()).strip("_"): v for k, v in out["field_coverage_pct"].items()}
    out["fair_sections_mean"] = {
        s: {"all": round(statistics.mean(r["fair_completeness"][s] for r in recs), 3),
            "fulltext": round(statistics.mean(r["fair_completeness"][s] for r in fulltext), 3)}
        for s in ("hardware", "assay", "construct", "solution", "data")}

    # derived shares quoted in the text ---------------------------------------
    n_checked = len(recs) - out["n_not_checked"]
    out["n_checked"] = n_checked
    out["n_deposits_linked"] = out["n_deposits"] - out["n_deposits_unlinked"]
    out["pct_not_checked"] = pct(out["n_not_checked"], len(recs))
    out["pct_fulltext_checked"] = pct(len(fulltext), len(recs))
    out["pct_with_dataset"] = pct(out["n_with_dataset"], len(recs))
    out["pct_with_dataset_of_checked"] = pct(out["n_with_dataset"], n_checked)
    out["pct_records_with_uniprot"] = pct(out["n_records_with_uniprot"], len(recs))
    out["pct_core"] = pct(out["n_core"], len(recs))
    out["pct_with_results"] = pct(out["n_records_with_results"], len(recs))
    yr = {y["year"]: y for y in out["availability_by_year"]}
    out["share_pct_by_year"] = {
        str(y): round(100 * v["n_with_dataset"] / v["n_checked"], 1) for y, v in yr.items() if v["n_checked"]}
    pre = [100 * v["n_with_dataset"] / v["n_checked"] for y, v in yr.items() if 2004 <= y <= 2018]
    out["max_share_pct_2004_2018"] = round(max(pre), 1)
    out["n_kinds"] = dict(Counter(r["scope"]["article_kind"] for r in recs))

    # pipeline funnel (Fig. 2) ----------------------------------------------
    out["pipeline_funnel"] = {
        "records_retained": len(recs),
        "with_data_link": out["n_with_any_data"],
        "with_resolved_system": out["n_records_with_uniprot"],
        "fulltext_read": len(fulltext),
        "with_extracted_results": out["n_records_with_results"],
    }
    return out


def harvest_funnel() -> dict:
    """Pre-scope counts come from the hub's own run logs (copied to data/hub_logs/), not from the release."""
    cl = (DATA / "hub_logs" / "classify_log.txt").read_text(encoding="utf-8")
    bl = (DATA / "hub_logs" / "build_log.txt").read_text(encoding="utf-8")
    tiers = {k: int(v) for k, v in re.findall(r"'(\w+)': (\d+)", cl.splitlines()[0])}
    removed = int(re.search(r"removed after review \(not SMFS\): (\d+)", bl).group(1))
    retained = tiers["core"] + tiers["methods"]
    return {
        "n_harvested_classified": sum(tiers.values()), "scope_tiers": tiers,
        "n_retained_before_review": retained, "n_removed_after_review": removed,
        "n_released": retained - removed,
        "source": "hub/out/classify_log.txt and build_log.txt, run of 2026-10-09/10",
    }


def sim_stats() -> dict:
    summ = load_csv(DATA / "sim" / "smash-sim-summary.csv")
    matches = load_csv(DATA / "sim" / "smash-sim-matches.csv")
    exp_with_match = {m["experimental_record_id"] for m in matches if m["experimental_source"] == "SMASH-BIO"}
    sim_with_match = {m["sim_record_id"] for m in matches}
    years = [int(r["year"]) for r in summ if r["year"]]
    return {
        "n_sim_records": len(summ),
        "by_model_family": dict(Counter(r["model_family"] for r in summ).most_common()),
        "by_model_group": dict(Counter(r["model_group"] for r in summ).most_common()),
        "by_unit_system": dict(Counter(r["unit_system"] for r in summ).most_common()),
        "n_links": len(matches),
        "links_by_match_level": dict(Counter(m["match_level"] for m in matches).most_common()),
        "links_by_experimental_source": dict(Counter(m["experimental_source"] for m in matches).most_common()),
        "n_links_smashbio": sum(m["experimental_source"] == "SMASH-BIO" for m in matches),
        "n_links_mechanoprodb": sum(m["experimental_source"] == "MechanoProDB" for m in matches),
        "n_sim_records_with_a_link": len(sim_with_match),
        "n_smashbio_records_linked": len(exp_with_match),
        "links_with_both_forces": sum(bool(m["force_sim_pN"]) and bool(m["force_experimental_pN"]) for m in matches),
        "year_min": min(years) if years else None, "year_max": max(years) if years else None,
    }


def check_against_site(stats: dict) -> list[str]:
    """Compare overlapping totals with the site's stats.js; return mismatches."""
    txt = (DATA / "site_stats.js").read_text(encoding="utf-8")
    site = json.loads(re.match(r"SMASH\.stats = (\{.*\});?\s*$", txt, re.S).group(1))["totals"]
    pairs = {"records": "n_records", "with_dataset": "n_with_dataset", "with_any_data": "n_with_any_data",
             "with_code": "n_with_code", "raw_traces": "n_with_raw_traces", "fulltext_checked": "n_fulltext_checked",
             "deposits": "n_deposits", "unlinked_deposits": "n_deposits_unlinked", "results": "n_results_extracted",
             "with_uniprot": "n_records_with_uniprot", "curated": "n_curated",
             "year_min": "year_min", "year_max": "year_max"}
    return [f"{a}: site={site[a]} ours={stats['smfs'][b]}" for a, b in pairs.items() if site[a] != stats["smfs"][b]]


def main() -> int:
    stats = {"smfs": smfs_stats(load_records(), load_csv(DATA / "smash-smfs-datasets.csv")),
             "harvest": harvest_funnel(), "sim": sim_stats()}
    assert stats["harvest"]["n_released"] == stats["smfs"]["n_records"], "hub logs and release disagree"
    if "--check" in sys.argv:
        bad = check_against_site(stats)
        print("site cross-check:", "OK" if not bad else bad, file=sys.stderr)
        if bad:
            return 1
    json.dump(stats, sys.stdout, indent=1, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
