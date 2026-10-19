"""Assign Table 3 type, module, sub-module and facets for one SMFS record.

``classify`` is pure: it does not modify ``record``. Curated and author
classifications are returned unchanged. A keyword whose priority is above
``PROCESSIVITY_PRIORITY`` (110) keeps the primary module; processivity is then
stored on the record and, when the motor is processive, ``processive_motors``
is added as a secondary module. That is what keeps a CRISPR translocation
study in gene editing.
"""
from __future__ import annotations

import re
from typing import Any

PROCESSIVITY_PRIORITY = 110
PROCESSIVE_RESULTS = {"step_size", "processivity_run_length", "velocity", "run_length"}
TRAP_TO_MODE = {
    "force_ramp": "force_ramp",
    "constant_velocity": "force_ramp",
    "force_clamp": "force_clamp",
    "constant_force": "force_clamp",
    "constant_distance": "distance_clamp",
    "passive_mode": "distance_clamp",
    "force_jump": "force_jump",
    "oscillatory": "oscillatory_microrheology",
}
FLUORO = {
    "confocal_fluorescence": "confocal",
    "TIRF": "TIRF",
    "widefield_fluorescence": "widefield",
    "smFRET": "smFRET",
    "IRM": "IRM",
    "STED": "STED",
}
NA_TRACKS = {"dna", "rna"}


def classify(record: dict, taxonomy: Any, methods_text: str = "") -> tuple[dict, list[dict]]:
    """Return ``(classification, new_provenance_entries)``.

    Provenance entries are only the new ones. Their ``evidence_ref`` indexes
    assume they will be appended to ``record["provenance"]``.
    """
    existing = record.get("classification") or {}
    if any((item.get("method") in {"curated", "author"}) for item in existing.get("modules") or []):
        return existing, []

    base_len = len(record.get("provenance") or [])
    new: list[dict] = []

    def evidence(snippet: str, method: str = "regex_title_abstract", confidence: str = "medium") -> int:
        new.append({
            "field": "classification",
            "method": method,
            "snippet": (snippet or "")[:400],
            "confidence": confidence,
        })
        return base_len + len(new) - 1

    modules_by_id = taxonomy.by_id()
    text = _text(record)
    entity_types = _entity_types(record)
    classes = _classes(record)
    matched_motors = _motors(record, taxonomy)

    # --- 1. class defaults -------------------------------------------------
    picks: list[dict] = []
    for name in classes:
        rows = [row for row in taxonomy.class_rules if row.experiment_class == name]
        chosen = _choose_class_rows(rows, entity_types, text)
        for row, note in chosen:
            module_id = None if row.module == "*" else row.module
            priority = 90 if module_id is None else modules_by_id[module_id].priority
            ref = evidence(f"experiment class {name}. {note}".strip(), "inferred", "medium")
            picks.append({
                "module": module_id,
                "submodules": [row.submodule] if row.submodule else [],
                "priority": priority,
                "table3": row.table3_type,
                "ref": ref,
            })
    if not picks:
        ref = evidence("no experiment class on the record", "inferred", "low")
        tier = ((record.get("scope") or {}).get("tier"))
        module_id = "methods" if tier == "methods" else "methods"
        picks.append({"module": module_id, "submodules": ["calibration"] if tier == "methods" else [],
                      "priority": 0, "table3": "extended", "ref": ref, "queue": "no experiment class"})

    picks.sort(key=lambda item: (-item["priority"], item["module"] or ""))
    primary = dict(picks[0])
    secondaries: list[dict] = []

    # --- 2. keywords -------------------------------------------------------
    hay = _haystacks(record)
    for rule in sorted(taxonomy.keywords, key=lambda item: -item.priority):
        blob = hay.get(rule.field, hay["any"])
        match = rule.regex.search(blob or "")
        if not match:
            continue
        module_id, sub = _keyword_target(rule, entity_types)
        ref = evidence(f"{rule.id}: {match.group(0)}", "regex_title_abstract", "medium")
        same = primary["module"] == module_id
        if rule.priority > primary["priority"] and not same:
            if primary["module"] and primary["module"] != module_id:
                secondaries.append(primary)
            primary = {"module": module_id, "submodules": [sub] if sub else [], "priority": rule.priority,
                       "table3": modules_by_id[module_id].table3_type, "ref": ref}
        elif same and sub and sub not in primary["submodules"]:
            primary["submodules"].append(sub)
            primary["ref"] = ref

    # --- 3. processivity ---------------------------------------------------
    geometry_bead, _assay = _facets(record, taxonomy, primary["module"] or "force_generation")
    proc, conflict = _processivity(record, matched_motors, geometry_bead)
    force_context = primary.get("table3") == "force_generation" or bool(matched_motors) or primary["module"] in {None, "processive_motors", "force_generation"}
    queue: list[str] = [primary["queue"]] if primary.get("queue") else []
    if force_context and proc != "not_applicable":
        target = {"processive": "processive_motors", "non_processive": "force_generation"}.get(proc, "force_generation")
        if proc == "unknown":
            queue.append("processivity unknown")
        if conflict:
            queue.append("processivity conflict")
        can_replace = primary["module"] in {None, "processive_motors", "force_generation"} and primary["priority"] < PROCESSIVITY_PRIORITY
        if primary["module"] is None or can_replace:
            snippet = _processivity_snippet(matched_motors, geometry_bead, proc)
            if conflict:
                snippet = "processivity conflict; " + snippet
            ref = evidence(snippet, "gazetteer" if matched_motors else "inferred",
                           "low" if proc == "unknown" else "medium")
            primary = {"module": target, "submodules": _family_subs(matched_motors, target) or primary["submodules"],
                       "priority": PROCESSIVITY_PRIORITY, "table3": "force_generation", "ref": ref}
        elif proc == "processive" and primary["module"] != "processive_motors":
            secondaries.append({"module": "processive_motors", "submodules": _family_subs(matched_motors, "processive_motors"),
                                "ref": evidence("processive motor kept as a secondary module", "gazetteer", "medium")})
    else:
        proc = "not_applicable"
        if primary["module"] is None:
            primary["module"] = "force_generation"
            primary["table3"] = "force_generation"

    if matched_motors and not primary["submodules"]:
        primary["submodules"] = _family_subs(matched_motors, primary["module"])

    if primary["module"] == "processive_motors" and any(motor.motor_track in NA_TRACKS for motor in matched_motors):
        if not any(item["module"] == "nucleic_acid_protein" for item in secondaries):
            secondaries.append({"module": "nucleic_acid_protein", "submodules": [],
                                "ref": evidence("nucleic-acid track; secondary module nucleic_acid_protein", "gazetteer", "medium")})

    # --- 4. facets ---------------------------------------------------------
    bead, assay = _facets(record, taxonomy, primary["module"])
    if "filament_polymerisation" in primary["submodules"]:
        assay = "polymerisation"
        bead = bead or "polymerisation_assay"
    modes = _modes(record, taxonomy, methods_text)
    fluoro = []
    for name in ((record.get("technique") or {}).get("correlative_modalities") or []):
        mapped = FLUORO.get(name)
        if mapped and mapped not in fluoro:
            fluoro.append(mapped)

    module_rows = [_module_row(primary, "primary")]
    seen = {primary["module"]}
    for item in secondaries:
        if not item["module"] or item["module"] in seen:
            continue
        seen.add(item["module"])
        module_rows.append(_module_row(item, "secondary"))

    classification = {
        "table3_type": modules_by_id[primary["module"]].table3_type,
        "modules": module_rows,
        "measurement_modes": modes,
        "correlative_fluorescence": {"present": bool(fluoro), "modalities": fluoro},
        "processivity": proc if proc in taxonomy.facets["processivity"] else "unknown",
        "taxonomy_version": taxonomy.version,
    }
    if assay:
        classification["assay_type"] = assay
    if bead:
        classification["bead_geometry"] = bead
    if queue:
        classification["review_reasons"] = queue
    return classification, new


def apply_classification(record: dict, taxonomy: Any, methods_text: str = "") -> dict:
    """Copy ``record``, attach classification, and bump ``schema_version``."""
    import copy
    out = copy.deepcopy(record)
    classification, provenance = classify(out, taxonomy, methods_text)
    _annotate_motors(out, _motors(out, taxonomy))
    stored = {k: v for k, v in classification.items() if k != "review_reasons"}
    out["classification"] = stored
    out.setdefault("provenance", []).extend(provenance)
    out["schema_version"] = "3.2.0"
    reasons = classification.get("review_reasons") or []
    if reasons:
        out["_module_review"] = reasons
    return out


def _module_row(item: dict, role: str) -> dict:
    row = {"module_id": item["module"], "role": role, "submodules": list(dict.fromkeys(item.get("submodules") or [])),
           "method": "rule"}
    if item.get("ref") is not None:
        row["evidence_ref"] = item["ref"]
    return row


def _text(record: dict) -> str:
    pub = record.get("publication") or {}
    return f"{pub.get('title') or ''} {pub.get('abstract') or ''}"


def _haystacks(record: dict) -> dict[str, str]:
    pub = record.get("publication") or {}
    title = pub.get("title") or ""
    abstract = pub.get("abstract") or ""
    names = " ".join((entity.get("name") or "") for entity in _entities(record))
    return {"title": title, "abstract": abstract, "entity": names, "any": f"{title} {abstract} {names}"}


def _entities(record: dict) -> list[dict]:
    return list(((record.get("biological_system") or {}).get("entities")) or [])


def _entity_types(record: dict) -> set[str]:
    types = {entity.get("entity_type") for entity in _entities(record) if entity.get("entity_type")}
    blob = _text(record)
    if re.search(r"\bDNA\b", blob):
        types.add("dna")
    if re.search(r"\bRNA\b", blob):
        types.add("rna")
    return types


def _classes(record: dict) -> list[str]:
    assay = (record.get("assay") or {}).get("experiment_class") or []
    system = (record.get("biological_system") or {}).get("system_class") or []
    seen: list[str] = []
    for name in list(assay) + list(system):
        if name not in seen:
            seen.append(name)
    return seen


def _choose_class_rows(rows: list, entity_types: set[str], text: str) -> list[tuple]:
    if not rows:
        return []
    specific = [row for row in rows if row.entity_type and row.entity_type in entity_types]
    if specific:
        return [(row, f"entity type {row.entity_type}") for row in specific]
    plain = [row for row in rows if not row.entity_type]
    if plain:
        return [(row, "") for row in plain]
    # Nucleic-acid class but no DNA/RNA entity. Prefer a word in the text, else queue both later.
    lowered = text.lower()
    picked = []
    for row in rows:
        if row.entity_type == "dna" and "dna" in lowered:
            picked.append((row, "text mentions DNA; entity type was not set"))
        elif row.entity_type == "rna" and "rna" in lowered:
            picked.append((row, "text mentions RNA; entity type was not set"))
    if picked:
        return picked
    return [(rows[0], "polymer type not stated; first mapping kept and the record is queued")]


def _keyword_target(rule, entity_types: set[str]) -> tuple[str, str]:
    if rule.id == "k_gq" and "rna" in entity_types and "dna" not in entity_types:
        return "rna_structure", "g_quadruplexes"
    return rule.module, rule.submodule


def _motors(record: dict, taxonomy) -> list:
    blob = _haystacks(record)["any"]
    found = []
    for motor in taxonomy.motors:
        if motor.regex.search(blob):
            found.append(motor)
    # Prefer a specific name over a generic one that is its substring: drop a
    # motor whose name is contained in a longer matched name.
    names = [motor.name.lower() for motor in found]
    return [motor for motor in found if not any(motor.name.lower() != other and motor.name.lower() in other for other in names)]


def _processivity(record: dict, motors: list, bead: str) -> tuple[str, bool]:
    gazetteer = None
    if any(motor.processive is True for motor in motors):
        gazetteer = "processive"
    elif motors and all(motor.processive is False for motor in motors):
        gazetteer = "non_processive"
    assay_value = None
    if bead == "three_bead":
        assay_value = "non_processive"
    quantities = {item.get("quantity") for item in (record.get("results") or [])}
    assay_type_translocation = False
    if (bead == "one_bead" or assay_type_translocation) and quantities & PROCESSIVE_RESULTS:
        assay_value = "processive"
    # Translocation is not known yet (facets depend on the module). Use geometry
    # bead plus an explicit assay label when the caller stored one.
    stated = (record.get("assay") or {}).get("assay_type")
    if (bead == "one_bead" or stated == "translocation") and quantities & PROCESSIVE_RESULTS:
        assay_value = "processive"
    if gazetteer and assay_value and gazetteer != assay_value:
        return gazetteer, True
    if gazetteer:
        return gazetteer, False
    if assay_value:
        return assay_value, False
    if motors or bead in {"one_bead", "three_bead"}:
        return "unknown", False
    return "unknown", False


def _processivity_snippet(motors: list, bead: str, proc: str) -> str:
    names = ", ".join(f"{motor.name}={motor.processive}" for motor in motors[:4]) or "no gazetteer motor"
    return f"processivity {proc}; bead {bead or 'unset'}; {names}"[:400]


def _family_subs(motors: list, module_id: str) -> list[str]:
    wanted = {
        "cytoskeletal_walkers": "processive_motors",
        "nucleic_acid_motors": "processive_motors",
        "packaging_motors": "processive_motors",
        "protein_unfoldases": "processive_motors",
        "nonprocessive_myosins": "force_generation",
        "rotary": "force_generation",
    }
    subs = []
    for motor in motors:
        home = wanted.get(motor.family)
        sub = "rotary_motors" if motor.family == "rotary" else motor.family
        if home == module_id and sub and sub not in subs:
            subs.append(sub)
    return subs


def _facets(record: dict, taxonomy, module_id: str) -> tuple[str, str]:
    geometry = (record.get("technique") or {}).get("force_application_geometry") or ""
    if not geometry:
        return "", ""
    specific = [row for row in taxonomy.geometry if row.geometry == geometry and row.module == module_id]
    wild = [row for row in taxonomy.geometry if row.geometry == geometry and row.module == "*"]
    row = (specific or wild or [None])[0]
    if row is None:
        return "", ""
    return row.bead_geometry, row.assay_type


def _modes(record: dict, taxonomy, methods_text: str) -> list[str]:
    found: list[str] = []
    blob = methods_text or ""
    for rule in taxonomy.modes:
        if blob and rule.regex.search(blob) and rule.measurement_mode not in found:
            found.append(rule.measurement_mode)
    for name in ((record.get("assay") or {}).get("trap_control") or []):
        mode = TRAP_TO_MODE.get(name)
        if mode and mode not in found:
            found.append(mode)
    order = taxonomy.facets["measurement_mode"]
    return [mode for mode in order if mode in found]


def _annotate_motors(record: dict, motors: list) -> None:
    """Fill processive and motor_track on entities whose name matches a motor.

    Existing non-null values are left as they are. Called from ``classify`` on
    the object it was given; ``apply_classification`` passes a copy.
    """
    if not motors:
        return
    for entity in _entities(record):
        name = entity.get("name") or ""
        for motor in motors:
            if motor.regex.search(name):
                if "processive" not in entity and motor.processive is not None:
                    entity["processive"] = motor.processive
                if "motor_track" not in entity and motor.motor_track:
                    entity["motor_track"] = motor.motor_track
                break
