"""Tests for hub/motors/classify.py and build_records.py (run: python -m pytest hub/motors)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motors.build_records import build  # noqa: E402
from motors.classify import classify  # noqa: E402
from motors.schema import validate  # noqa: E402


def ent(name, snippet=None):
    return {"name": name, "entity_type": "protein", "evidence": {"method": "gazetteer", "snippet": snippet or name}}


def smfs(rid, title, entities, classes=("force_generation_motor",), abstract=""):
    return {"record_id": rid, "publication": {"title": title, "abstract": abstract, "doi": "10.1/x", "year": 2020},
            "technique": {"primary": "optical_tweezers", "force_application_geometry": "dumbbell_dual_trap"},
            "assay": {"experiment_class": list(classes)}, "biological_system": {"system_class": list(classes), "entities": entities},
            "data_availability": {"status": "not_stated", "has_linked_dataset": False}, "curation": {"level": "auto_abstract"}}


def test_specific_entity_wins():
    c = classify("Kinesin-1 stepping under load", "", [ent("Kinesin-1")])
    assert c.family == "kinesin" and c.route == "entity_specific" and c.confidence == "high"


def test_generic_entity_lower_certainty():
    c = classify("A helicase study", "", [ent("Helicase")])
    assert c.family == "helicase_translocase" and c.route == "entity_generic" and c.certainty < 0.8


def test_title_fallback_only_without_entities():
    c = classify("Processive stepping of myosin VI on actin", "", [])
    assert c.family == "myosin_processive" and c.route == "title" and c.confidence == "low"


def test_myosin_ii_excluded():
    c = classify("Cardiac myosin under load", "", [ent("β-cardiac myosin (MYH7)")])
    assert c.family is None and "excluded" in c.reason


def test_generic_myosin_never_resolves():
    assert classify("Myosin mechanics", "", [ent("Myosin")]).candidate is None


def test_gliding_assay_is_included_and_labelled():
    c = classify("Kinesin gliding assay on patterned surfaces", "microtubule gliding assay", [ent("Kinesin")])
    assert c.family == "kinesin" and c.assay_type == "gliding_or_ensemble"


def test_gliding_with_optical_trap_is_single_molecule():
    c = classify("Kinesin in a gliding assay and an optical trap", "", [ent("Kinesin-1")])
    assert c.assay_type == "single_molecule"


def test_no_experiment_class_needed():
    c = classify("RecBCD unwinding", "", [ent("RecBCD")])
    assert c.family == "helicase_translocase"


def test_ambiguity_lowers_certainty():
    c = classify("Transcription-translation coupling", "", [ent("RNA polymerase II"), ent("Ribosome")])
    assert c.certainty <= 0.5


def test_build_links_smfs_and_validates():
    recs = [smfs("SMFS-000002", "Dynein stepping", [ent("Cytoplasmic dynein-1", "…cytoplasmic dynein…")]),
            smfs("SMFS-000001", "DNA overstretching", [ent("λ-DNA")], ["nucleic_acid_mechanics"]),
            smfs("SMFS-000003", "RecBCD unwinding", [ent("RecBCD")], ["nucleic_acid_protein_interaction"])]
    id_map: dict = {}
    out, reasons = build(recs, id_map)
    assert [(r["record_id"], r["smfs_record_id"], r["family"]) for r in out] == [
        ("MOTOR-000001", "SMFS-000002", "dynein"), ("MOTOR-000002", "SMFS-000003", "helicase_translocase")]
    assert out[0]["evidence"]["family"]["snippet"] == "…cytoplasmic dynein…"
    good, bad = validate(out)
    assert not bad, bad


def test_ids_are_stable_across_builds():
    recs = [smfs("SMFS-000005", "Kinesin-1 stepping", [ent("Kinesin-1")])]
    id_map = {"SMFS-000005": "MOTOR-000042", "SMFS-000004": "MOTOR-000041"}
    out, _ = build(recs, id_map)
    assert out[0]["record_id"] == "MOTOR-000042"


def test_smfs_input_is_not_modified():
    import copy
    recs = [smfs("SMFS-000002", "Dynein stepping", [ent("Cytoplasmic dynein-1")])]
    before = copy.deepcopy(recs)
    build(recs, {})
    assert recs == before
