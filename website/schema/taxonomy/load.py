"""Load the versioned experiment-module taxonomy.

The YAML and CSV files under ``taxonomy/`` are the source of truth. Callers
get one ``Taxonomy`` object and do not re-read the files.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


def _csv(name: str) -> list[dict[str, str]]:
    path = ROOT / name
    with path.open(encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def _boolish(text: str) -> bool | None:
    if text == "":
        return None
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    raise ValueError(f"expected true, false, or blank, got {text!r}")


@dataclass
class Module:
    id: str
    label: str
    table3_type: str
    priority: int
    description: str
    submodules: list[str]
    observable_profile: dict[str, list[str]]
    canonical_systems: list[str]
    parent_sources: list[str] = field(default_factory=list)


@dataclass
class Submodule:
    id: str
    label: str
    module: str
    keywords: list[str]
    canonical_systems: list[str]


@dataclass
class KeywordRule:
    id: str
    pattern: str
    regex: re.Pattern[str]
    field: str
    module: str
    submodule: str
    priority: int


@dataclass
class ClassRule:
    experiment_class: str
    table3_type: str
    module: str
    submodule: str
    entity_type: str


@dataclass
class GeometryRule:
    geometry: str
    module: str
    bead_geometry: str
    assay_type: str


@dataclass
class ModeRule:
    id: str
    pattern: str
    regex: re.Pattern[str]
    measurement_mode: str


@dataclass
class Motor:
    name: str
    synonyms: list[str]
    uniprot: str
    processive: bool | None
    motor_track: str
    family: str
    note: str
    regex: re.Pattern[str]


@dataclass
class Taxonomy:
    version: str
    modules: list[Module]
    submodules: list[Submodule]
    facets: dict[str, list[str]]
    class_rules: list[ClassRule]
    keywords: list[KeywordRule]
    geometry: list[GeometryRule]
    modes: list[ModeRule]
    motors: list[Motor]

    def module(self, module_id: str) -> Module:
        for item in self.modules:
            if item.id == module_id:
                return item
        raise KeyError(module_id)

    def by_id(self) -> dict[str, Module]:
        return {item.id: item for item in self.modules}


def load_taxonomy(root: Path | None = None) -> Taxonomy:
    base = root or ROOT
    version = (base / "VERSION").read_text(encoding="utf-8").strip()
    raw_modules = yaml.safe_load((base / "modules.yaml").read_text(encoding="utf-8"))
    raw_subs = yaml.safe_load((base / "submodules.yaml").read_text(encoding="utf-8"))
    facets = yaml.safe_load((base / "facets.yaml").read_text(encoding="utf-8"))
    modules = [
        Module(
            id=item["id"],
            label=item["label"],
            table3_type=item["table3_type"],
            priority=int(item["priority"]),
            description=item.get("description") or "",
            submodules=list(item.get("submodules") or []),
            observable_profile={k: list(v) for k, v in (item.get("observable_profile") or {}).items()},
            canonical_systems=list(item.get("canonical_systems") or []),
            parent_sources=list(item.get("parent_sources") or []),
        )
        for item in raw_modules
    ]
    submodules = [
        Submodule(
            id=item["id"],
            label=item["label"],
            module=item["module"],
            keywords=list(item.get("keywords") or []),
            canonical_systems=list(item.get("canonical_systems") or []),
        )
        for item in raw_subs
    ]
    keywords = []
    for row in _rows(base / "rules" / "keyword_to_module.csv"):
        keywords.append(
            KeywordRule(
                id=row["id"],
                pattern=row["pattern"],
                regex=re.compile(row["pattern"], re.I),
                field=row["field"],
                module=row["module"],
                submodule=row["submodule"],
                priority=int(row["priority"]),
            )
        )
    class_rules = [
        ClassRule(
            experiment_class=row["experiment_class"],
            table3_type=row["table3_type"],
            module=row["module"],
            submodule=row["submodule"],
            entity_type=row["entity_type"],
        )
        for row in _rows(base / "rules" / "class_to_module.csv")
    ]
    geometry = [
        GeometryRule(
            geometry=row["geometry"],
            module=row["module"],
            bead_geometry=row["bead_geometry"],
            assay_type=row["assay_type"],
        )
        for row in _rows(base / "rules" / "geometry_to_facets.csv")
    ]
    modes = [
        ModeRule(
            id=row["id"],
            pattern=row["pattern"],
            regex=re.compile(row["pattern"], re.I),
            measurement_mode=row["measurement_mode"],
        )
        for row in _rows(base / "rules" / "mode_phrases.csv")
    ]
    motors = []
    for row in _rows(base / "gazetteer_motors.csv"):
        names = [row["name"], *[part for part in row["synonyms"].split("|") if part]]
        # Longest name first so "kinesin-1" wins over a shorter synonym when both hit.
        names.sort(key=len, reverse=True)
        pattern = "|".join(rf"\b{re.escape(name)}\b" for name in names)
        motors.append(
            Motor(
                name=row["name"],
                synonyms=[part for part in row["synonyms"].split("|") if part],
                uniprot=row["uniprot"],
                processive=_boolish(row["processive"]),
                motor_track=row["motor_track"],
                family=row["family"],
                note=row["note"],
                regex=re.compile(pattern, re.I),
            )
        )
    return Taxonomy(version, modules, submodules, facets, class_rules, keywords, geometry, modes, motors)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]
