"""Check referential integrity of taxonomy 1.0.0.

Run from the repository root: ``python taxonomy/validate.py``.
Exits 0 when every module, sub-module, class and facet reference resolves.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load import load_taxonomy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "website" / "schema" / "smash-smfs-record.schema.json"


def main() -> int:
    tax = load_taxonomy()
    errors: list[str] = []
    if tax.version != "1.0.0":
        errors.append(f"VERSION is {tax.version}, expected 1.0.0")
    if len(tax.modules) != 13:
        errors.append(f"expected 13 modules, found {len(tax.modules)}")
    module_ids = [item.id for item in tax.modules]
    if len(module_ids) != len(set(module_ids)):
        errors.append("duplicate module id")
    sub_pairs = {(item.id, item.module) for item in tax.submodules}
    sub_ids = {item.id for item in tax.submodules}
    if len(tax.submodules) != len(sub_ids):
        errors.append("duplicate submodule id")
    facet_modules = set(tax.facets["table3_type"])
    for module in tax.modules:
        if module.table3_type not in facet_modules:
            errors.append(f"{module.id} has unknown table3_type {module.table3_type}")
        for sub in module.submodules:
            if (sub, module.id) not in sub_pairs:
                errors.append(f"{module.id} lists submodule {sub} that is not defined for it")
    for sub in tax.submodules:
        if sub.module not in module_ids:
            errors.append(f"submodule {sub.id} has unknown parent {sub.module}")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    classes = schema["$defs"]["ExperimentClass"]["enum"]
    mapped = {row.experiment_class for row in tax.class_rules}
    for name in classes:
        if name not in mapped:
            errors.append(f"v3.1 class {name} has no class_to_module row")
    for row in tax.class_rules:
        if row.experiment_class not in classes:
            errors.append(f"class_to_module row for unknown class {row.experiment_class}")
        if row.module != "*" and row.module not in module_ids:
            errors.append(f"class {row.experiment_class} maps to unknown module {row.module}")
        if row.module == "*" and row.submodule:
            errors.append("a '*' module row cannot set a submodule")
        if row.submodule and (row.submodule, row.module) not in sub_pairs:
            errors.append(f"class {row.experiment_class} submodule {row.submodule} is not on {row.module}")
        if row.entity_type and row.entity_type not in {"dna", "rna"}:
            errors.append(f"entity_type {row.entity_type} is not dna or rna")
        if row.table3_type not in facet_modules:
            errors.append(f"class {row.experiment_class} has unknown table3_type")
    geometries = set(schema["$defs"]["Technique"]["properties"]["force_application_geometry"]["enum"])
    seen_geo = {row.geometry for row in tax.geometry}
    if geometries - seen_geo:
        errors.append("geometries missing from geometry_to_facets.csv: " + ", ".join(sorted(geometries - seen_geo)))
    for row in tax.geometry:
        if row.geometry not in geometries:
            errors.append(f"unknown geometry {row.geometry}")
        if row.module not in {"*", *module_ids}:
            errors.append(f"geometry row module {row.module}")
        if row.bead_geometry and row.bead_geometry not in tax.facets["bead_geometry"]:
            errors.append(f"unknown bead_geometry {row.bead_geometry}")
        if row.assay_type and row.assay_type not in tax.facets["assay_type"]:
            errors.append(f"unknown assay_type {row.assay_type}")
    fields = {"title", "abstract", "entity", "any"}
    ids = [row.id for row in tax.keywords]
    if len(ids) != len(set(ids)):
        errors.append("duplicate keyword id")
    patterns = Counter((row.pattern, row.field) for row in tax.keywords)
    for key, count in patterns.items():
        if count > 1:
            errors.append(f"duplicate keyword pattern {key}")
    for row in tax.keywords:
        if row.field not in fields:
            errors.append(f"keyword {row.id} field {row.field}")
        if r"\b" not in row.pattern:
            errors.append(f"keyword {row.id} is not anchored with a word boundary")
        if row.module not in module_ids:
            errors.append(f"keyword {row.id} module {row.module}")
        if row.submodule and (row.submodule, row.module) not in sub_pairs:
            errors.append(f"keyword {row.id} submodule {row.submodule} is not on {row.module}")
    mode_ids = [row.id for row in tax.modes]
    if len(mode_ids) != len(set(mode_ids)):
        errors.append("duplicate mode-phrase id")
    for row in tax.modes:
        if r"\b" not in row.pattern:
            errors.append(f"mode phrase {row.id} is not anchored")
        if row.measurement_mode not in tax.facets["measurement_mode"]:
            errors.append(f"unknown measurement mode {row.measurement_mode}")
    if len(tax.motors) < 60:
        errors.append(f"gazetteer has {len(tax.motors)} rows; expected at least 60")
    names = [row.name for row in tax.motors]
    if len(names) != len(set(names)):
        errors.append("duplicate motor name")
    for row in tax.motors:
        if row.motor_track and row.motor_track not in tax.facets["motor_track"]:
            errors.append(f"motor {row.name} has unknown track {row.motor_track}")
        if not row.note:
            errors.append(f"motor {row.name} has no note")
    if errors:
        print("taxonomy validation failed:")
        for item in errors:
            print(" -", item)
        return 1
    print(f"taxonomy {tax.version}: {len(tax.modules)} modules, {len(tax.submodules)} submodules, "
          f"{len(tax.keywords)} keyword rules, {len(tax.motors)} motors")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
