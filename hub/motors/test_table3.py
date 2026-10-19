"""Tests for the motor Table 3 grid and completeness (run: python -m pytest hub/motors)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motors import spec  # noqa: E402
from motors.table3 import check_paths, completeness, experiment_types, grid, render  # noqa: E402


def test_every_path_resolves_in_the_schemas():
    assert check_paths() == []


def test_columns_match_schema_enum():
    assert experiment_types() == spec.EXPERIMENT_TYPES


def test_grid_shape_and_codes():
    g = grid()
    assert {r["section"] for r in g["rows"]} == {"hardware", "assay", "construct", "solution"}
    assert all(set(r["cells"].values()) <= {"R", "O", "-"} for r in g["rows"])
    assert all(len(r["cells"]) == len(g["columns"]) for r in g["rows"])


def motor(**kw):
    return {"family": "kinesin", **kw}


def test_core_basis_without_experiment_type():
    c = completeness(motor(), {})
    assert c["basis"] == "core" and c["assay"] is None and 0 < c["construct"] < 1


def test_type_specific_rows_count():
    smfs = {"hardware": {"magnetic": {"field": "x"}, "detection_device": ["camera_CMOS"], "acquisition_rate": {"value": 60, "unit": "Hz"}}}
    c = completeness(motor(experiment_type="magnetic_tweezers"), smfs)
    assert c["basis"] == "magnetic_tweezers" and c["hardware"] > 0
    # the trap stiffness row is "-" for magnetic tweezers, so it can never lower the score
    c2 = completeness(motor(experiment_type="magnetic_tweezers"), {**smfs, "hardware": {**smfs["hardware"], "optical": {"trap_stiffness": {"value": 0.1, "unit": "pN/nm"}}}})
    assert c2["hardware"] == c["hardware"]


def test_alternative_path_temperature():
    a = completeness(motor(experiment_type="flow_stretching"), {"hardware": {"temperature": {"value": 296, "unit": "K"}}})
    b = completeness(motor(experiment_type="flow_stretching", chemistry={"temperature_C": 23}), {})
    assert a["hardware"] == b["hardware"] > 0


def test_empty_quantity_does_not_count():
    a = completeness(motor(experiment_type="flow_stretching"), {"hardware": {"temperature": {"value": None, "unit": "K"}}})
    assert a["hardware"] == 0


def test_render_has_all_rows():
    md = render()
    assert md.count("\n| ") >= len(grid()["rows"]) + len(grid()["observables"])
