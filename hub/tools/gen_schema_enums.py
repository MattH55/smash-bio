"""Write taxonomy enums into the SMFS record and results schemas.

The structural ``classification`` object is added once. Enum arrays are
replaced from ``taxonomy/`` on every run so the schema cannot drift from the
taxonomy files. Schema version becomes 3.2.0.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "taxonomy"))
from load import load_taxonomy  # noqa: E402

RECORD = ROOT / "website" / "schema" / "smash-smfs-record.schema.json"
RESULTS = ROOT / "website" / "schema" / "smash-smfs-results.schema.json"

NEW_OBSERVABLES = {
    "fusion_time": "s",
    "molecular_tension": "pN",
    "pause_density": "1/um",
    "kcat": "1/s",
}


def _dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _classification(tax) -> dict:
    module_ids = [item.id for item in tax.modules]
    sub_ids = sorted({item.id for item in tax.submodules})
    return {
        "type": "object",
        "description": "What the experiment studies (Table 3 type, one primary module) and how it was measured (facets). Generated from taxonomy/.",
        "required": ["table3_type", "modules", "processivity", "taxonomy_version"],
        "properties": {
            "table3_type": {"enum": list(tax.facets["table3_type"])},
            "modules": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["module_id", "role", "method"],
                    "properties": {
                        "module_id": {"enum": module_ids},
                        "role": {"enum": list(tax.facets["module_role"])},
                        "submodules": {"type": "array", "items": {"enum": sub_ids}},
                        "method": {"enum": list(tax.facets["module_method"])},
                        "evidence_ref": {"type": "integer", "minimum": 0, "description": "Index into provenance."},
                    },
                },
            },
            "assay_type": {"enum": list(tax.facets["assay_type"])},
            "bead_geometry": {"enum": list(tax.facets["bead_geometry"])},
            "measurement_modes": {"type": "array", "items": {"enum": list(tax.facets["measurement_mode"])}},
            "correlative_fluorescence": {
                "type": "object",
                "required": ["present"],
                "properties": {
                    "present": {"type": "boolean"},
                    "modalities": {"type": "array", "items": {"enum": list(tax.facets["fluorescence_modality"])}},
                },
            },
            "processivity": {"enum": list(tax.facets["processivity"])},
            "taxonomy_version": {"const": tax.version},
        },
        "allOf": [{
            "properties": {
                "modules": {
                    "contains": {
                        "type": "object",
                        "properties": {"role": {"const": "primary"}},
                        "required": ["role"],
                    },
                    "minContains": 1,
                    "maxContains": 1,
                }
            }
        }],
    }


def patch_record(tax) -> None:
    data = json.loads(RECORD.read_text(encoding="utf-8"))
    data["properties"]["schema_version"]["const"] = "3.2.0"
    data["properties"]["classification"] = _classification(tax)
    experiment = data["$defs"]["ExperimentClass"]
    description = experiment.get("description") or ""
    if "deprecated" not in description.lower():
        experiment["description"] = description.rstrip() + " Deprecated in schema 3.2.0: kept populated for old links. Prefer classification.modules."
        experiment["deprecated"] = True
    entity = data["$defs"]["MolecularEntity"]["properties"]
    entity["processive"] = {"type": ["boolean", "null"], "description": "From taxonomy/gazetteer_motors.csv. Null when the gazetteer does not know."}
    entity["motor_track"] = {"enum": list(tax.facets["motor_track"]) + [None], "description": "Filament or polymer the motor runs on."}
    _dump(RECORD, data)


def patch_results() -> None:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    props = data["$defs"]["Result"]["properties"]
    props["measurement_mode"] = {
        "description": "Measurement mode of the sentence this result was read from, when a mode phrase matches.",
        "enum": ["force_extension", "distance_clamp", "force_clamp", "force_ramp", "force_jump", "oscillatory_microrheology", "passive_equilibrium"],
    }
    enum = data["$defs"]["Observable"]["enum"]
    units = data["$defs"]["ObservableUnits"]["const"]
    for name, unit in NEW_OBSERVABLES.items():
        if name not in enum:
            enum.insert(enum.index("other"), name)
        units[name] = unit
    _dump(RESULTS, data)


def main() -> None:
    tax = load_taxonomy()
    patch_record(tax)
    patch_results()
    print("schema enums written for taxonomy", tax.version)


if __name__ == "__main__":
    main()
