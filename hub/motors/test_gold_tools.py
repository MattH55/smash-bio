"""Tests for the Motors gold-set tooling and the v3.2.0 schema (run: python -m pytest hub/motors)."""
import copy
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motors import sample_gold, validate_gold  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs" / "motors" / "gold" / "TEMPLATE.yaml"


def fake(i, fam, tech, year):
    return {"record_id": f"MOTOR-{i:06d}", "smfs_record_id": f"SMFS-{i:06d}", "publication": {"doi": f"10.1/x{i}", "title": f"T{i}", "year": year},
            "technique": {"primary": tech}, "family": fam}


def test_allocate_sums_and_caps():
    a = sample_gold.allocate({"a": 70, "b": 20, "c": 3}, 50)
    assert sum(a.values()) == 50 and all(a[k] <= v for k, v in {"a": 70, "b": 20, "c": 3}.items())
    assert sample_gold.allocate({"a": 5, "b": 3}, 50) == {"a": 5, "b": 3}


def test_sample_is_deterministic_and_stratified():
    recs = [fake(i, "kinesin", "optical_tweezers" if i % 3 else "magnetic_tweezers", 1995 + i % 30) for i in range(200)]
    s1 = sample_gold.sample(recs, ["kinesin"], 50, 7)
    s2 = sample_gold.sample(copy.deepcopy(recs), ["kinesin"], 50, 7)
    assert s1 == s2 and s1["kinesin"]["sampled"] == 50
    assert sample_gold.sample(recs, ["kinesin"], 50, 8) != s1


def test_stub_has_source_fields_only():
    t = sample_gold.stub(TEMPLATE.read_text(encoding="utf-8"), {"record_id": "MOTOR-000042", "smfs_record_id": "SMFS-000007", "doi": "10.1/abc", "title": 'A "quoted" title'})
    d = yaml.safe_load(t)
    assert d["record_id"] == "MOTOR-000042" and d["smfs_record_id"] == "SMFS-000007" and d["doi"] == "10.1/abc" and d["title"] == 'A "quoted" title'
    assert d["motor"]["family"] is None and d["results"] == []


def check(d, tmp_path, name="MOTOR-000001.yaml"):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    md, mv, rv = validate_gold._schemas()
    return validate_gold.check(p, md, mv, rv)


def base():
    d = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    d["record_id"] = "MOTOR-000001"
    return d


def test_template_validates_unannotated(tmp_path):
    errs, complete = check(base(), tmp_path)
    assert errs == [] and not complete


def test_filled_annotation_validates(tmp_path):
    d = base()
    d.update(annotator="MH", annotation_date="2026-10-19", sections_read=["abstract", "methods", "figure_legends"],
             is_processive_motor_study=True, not_reported=["load.vertical_component_considered"])
    d["motor"]["family"] = "kinesin"
    d["motor"]["assay_type"] = "single_molecule"
    d["motor"]["chemistry"]["nucleotide"] = {"species": "ATP", "concentration_uM": 1000}
    d["motor"]["probe_link"]["motors_per_probe"] = "single"
    d["results"] = [{"quantity": "stall_force", "value": 6.0, "unit": "pN", "conditions": {"load_direction": "hindering", "atp_uM": 1000}},
                    {"quantity": "force_velocity_curve", "value": [{"force_pN": 0, "velocity_nm_s": 800}, {"force_pN": 4, "velocity_nm_s": 300}],
                     "unit": "—"}]
    errs, complete = check(d, tmp_path)
    assert errs == [] and complete


def test_bad_enum_and_paths_are_errors(tmp_path):
    d = base()
    d["motor"]["family"] = "myosin_ii"
    d["not_reported"] = ["load.nonexistent"]
    errs, _ = check(d, tmp_path)
    assert any("motor.family" in e for e in errs) and any("not a motor field" in e for e in errs)


def test_filled_and_not_reported_conflict(tmp_path):
    d = base()
    d["motor"]["load"]["direction"] = "hindering"
    d["not_reported"] = ["load.direction"]
    errs, _ = check(d, tmp_path)
    assert any("both filled" in e for e in errs)


def test_curve_value_must_be_array_and_scalar_must_not(tmp_path):
    d = base()
    d["results"] = [{"quantity": "force_velocity_curve", "value": 3.0, "unit": "—"},
                    {"quantity": "stall_force", "value": [{"force_pN": 1, "velocity_nm_s": 2}], "unit": "pN"}]
    errs, _ = check(d, tmp_path)
    assert any(e.startswith("results[0]") for e in errs) and any(e.startswith("results[1]") for e in errs)


def test_annotation_order_first_four_then_seeded_random():
    fams = ["kinesin", "dynein", "myosin_processive", "helicase_translocase", "ribosome", "rna_polymerase", "viral_packaging"]
    o1 = sample_gold.annotation_order(fams, 20261019)
    assert o1[:4] == ["kinesin", "dynein", "myosin_processive", "helicase_translocase"]
    assert sorted(o1[4:]) == ["ribosome", "rna_polymerase", "viral_packaging"]
    assert o1 == sample_gold.annotation_order(list(reversed(fams)), 20261019)
