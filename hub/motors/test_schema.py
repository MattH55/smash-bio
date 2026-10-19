"""SMASH-MOTOR schema tests (run: python -m pytest hub/motors)."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motors import spec  # noqa: E402
from motors.schema import record_validator, result_validator  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MINIMAL = {"record_id": "MOTOR-000001", "schema_version": spec.VERSION, "category": "processive_motor", "smfs_record_id": "SMFS-000001",
           "publication": {"title": "x"}, "family": "kinesin", "assay_type": "single_molecule", "curation": {"level": "auto"}}


def test_written_schemas_match_spec():
    for name, s in (("smash-motor-record.schema.json", spec.record_schema()), ("smash-motor-results.schema.json", spec.results_schema())):
        assert json.loads((spec.SCHEMA_DIR / name).read_text(encoding="utf-8")) == s, f"run python hub/motors/spec.py ({name})"


def test_minimal_record_valid_and_closed():
    v = record_validator()
    assert not list(v.iter_errors(MINIMAL))
    assert list(v.iter_errors({**MINIMAL, "colour": "red"}))
    assert list(v.iter_errors({**MINIMAL, "record_id": "SMFS-000001"}))
    assert list(v.iter_errors({**MINIMAL, "family": "myosin_ii"}))


def test_full_motor_fields_validate():
    rec = {**MINIMAL, "isoform": "K560", "uniprot": ["P33176"], "track": {"track_type": "microtubule", "polarity_marked": True},
           "probe_link": {"attachment": "antibody", "motors_per_probe": "single", "single_motor_verification": "poisson_dilution"},
           "load": {"geometry": "single_bead", "direction": "hindering"}, "feedback": {"mode": "force_clamp"},
           "chemistry": {"nucleotide": {"species": "ATP", "concentration_uM": 1000}, "temperature_C": 23},
           "reporting": {"n_molecules": 12, "step_detection": {"method": "t-test"}},
           "evidence": {"load.direction": {"method": "manual_curation", "snippet": "hindering load", "confidence": "high"}},
           "results": [{"quantity": "stall_force", "value": 6.0, "unit": "pN", "conditions": {"atp_uM": 1000, "load_direction": "hindering"}},
                       {"quantity": "force_velocity_curve", "unit": "—", "value": [{"force_pN": 0, "velocity_nm_s": 800}]}]}
    assert not list(record_validator().iter_errors(rec))


def test_curve_only_for_force_velocity():
    v = result_validator()
    assert list(v.iter_errors({"quantity": "force_velocity_curve", "unit": "—", "value": 3.0}))
    assert list(v.iter_errors({"quantity": "stall_force", "unit": "pN", "value": [{"force_pN": 1, "velocity_nm_s": 2}]}))


def test_shared_quantities_keep_smfs_units():
    smfs = json.loads((ROOT / "website" / "schema" / "smash-smfs-results.schema.json").read_text(encoding="utf-8"))
    su = smfs["$defs"]["ObservableUnits"]["const"]
    assert set(spec.REUSED) <= set(smfs["$defs"]["Observable"]["enum"])
    for q, u in spec.REUSED.items():
        if q in su:  # same canonical unit wherever SMASH-BIO fixes one
            assert su[q] == u, q
    # SMASH-BIO leaves this count without a fixed unit; SMASH-MOTOR states it as dimensionless
    assert [q for q in spec.REUSED if q not in su] == ["number_of_steps_or_intermediates"]


def test_smfs_experiment_class_enum_matches_main():
    """Schema 3.2.0 adds classification. The experiment-class vocabulary stays the one on main."""
    import json
    current = json.loads((ROOT / "website" / "schema" / "smash-smfs-record.schema.json").read_text(encoding="utf-8"))
    assert current["properties"]["schema_version"]["const"] == "3.2.0"
    assert "classification" in current["properties"]
    main = subprocess.run(
        ["git", "show", "main:website/schema/smash-smfs-record.schema.json"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout
    previous = json.loads(main.decode("utf-8"))
    assert current["$defs"]["ExperimentClass"]["enum"] == previous["$defs"]["ExperimentClass"]["enum"]
