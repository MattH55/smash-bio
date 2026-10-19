"""SMASH-MOTOR schema definitions (v1.0.0) and their writer.

SMASH-MOTOR is a separate module, like SMASH-SIM: its own record type (MOTOR-######), its own record and results
schemas under website/schema/motor/, its own downloads. Each MOTOR record links the SMASH-BIO study it was derived
from (`smfs_record_id`). Shared definitions (Publication, Evidence, DataAvailability, technique and geometry
vocabularies) are referenced from the published SMFS 3.1.0 schemas, which are never modified.

    python hub/motors/spec.py          # (re)writes website/schema/motor/*.schema.json
"""
from __future__ import annotations

import json
from pathlib import Path

VERSION = "1.0.0"
SCHEMA_DIR = Path(__file__).resolve().parents[2] / "website" / "schema" / "motor"
BASE = "https://smash-bio.org/schema/motor/"
SMFS = "../smash-smfs-record.schema.json"

# columns of the motor Table 3 (hub/motors/table3_motor.yaml); kept here so the schema does not depend on the YAML
EXPERIMENT_TYPES = ["optical_trap_single_bead", "optical_trap_three_bead", "optical_trap_dna_tether", "magnetic_tweezers",
                    "flow_stretching", "sm_fluorescence", "gliding_ensemble"]
FAMILIES = ["kinesin", "dynein", "myosin_processive", "helicase_translocase", "rna_polymerase", "dna_polymerase_replisome",
            "ribosome", "viral_packaging", "smc_loop_extruder", "chromatin_remodeller", "other"]
LOAD_DIRECTION = ["hindering", "assisting", "sideways", "mixed", "none", "other"]
FEEDBACK = ["passive_trap", "force_clamp", "position_clamp", "velocity_clamp", "force_ramp", "none", "other"]
UNIPROT_AC = r"^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})(-[0-9]+)?$"

# Observables: the existing SMFS motor quantities are reused under the same names and canonical units; the rest are new.
REUSED = {"step_size": "nm", "stall_force": "pN", "detachment_force": "pN", "velocity": "nm/s", "processivity_run_length": "nm",
          "dwell_time": "s", "pause_frequency": "1/s", "pause_duration": "s", "torque": "pN nm", "loading_rate": "pN/s",
          "number_of_steps_or_intermediates": "1"}
NEW = {"force_velocity_curve": "—", "load_distance_parameter": "nm", "substep_size": "nm", "coupling_ratio": "steps/ATP",
       "randomness_parameter": "1", "backstep_ratio": "1", "kcat": "1/s", "km": "uM", "rotation_per_step": "deg",
       "number_of_rate_limiting_steps": "1"}


def enum(values: list[str], description: str) -> dict:
    return {"enum": values + ([] if "other" in values else ["other"]), "description": description}


def text(d: str) -> dict:
    return {"type": "string", "description": d}


def strings(d: str) -> dict:
    return {"type": "array", "items": {"type": "string"}, "description": d}


def num(d: str, minimum: float | None = 0) -> dict:
    return {"type": "number", "description": d, **({"minimum": minimum} if minimum is not None else {})}


def count(d: str) -> dict:
    return {"type": "integer", "minimum": 0, "description": d}


def obj(props: dict, d: str, required: list[str] | None = None) -> dict:
    o = {"type": "object", "additionalProperties": False, "properties": props, "description": d}
    if required:
        o["required"] = required
    return o


def record_schema() -> dict:
    defs = {
        "Construct": obj({"truncation": text("Residue range or truncation name."), "tags": strings("e.g. GFP, SNAP, His6, AviTag."),
                          "mutations": strings("Point mutations, e.g. E236A.")}, "Motor construct."),
        "Track": obj({
            "track_type": enum(["microtubule", "actin", "dsDNA", "ssDNA", "RNA", "mRNA", "chromatin"], "Track the motor moves on."),
            "track_type_other": text("Free text when track_type = other."),
            "track_source": text("Source or preparation, e.g. porcine brain tubulin, lambda DNA."),
            "polarity_marked": {"type": "boolean", "description": "Track polarity marked or otherwise known."},
            "lattice_or_sequence": text("Lattice (13-protofilament, GMPCPP, taxol) or nucleic-acid sequence/template."),
            "decorations": strings("MAPs, nucleosomes, SSB, roadblocks."),
        }, "Track."),
        "ProbeLink": obj({
            "attachment": enum(["antibody", "biotin_streptavidin", "his_tag", "gfp_antibody", "snap_or_halo_tag", "dna_tether",
                                "nonspecific_adsorption", "covalent"], "How the motor is linked to the probe."),
            "attachment_other": text("Free text when attachment = other."),
            "motors_per_probe": {"oneOf": [{"type": "number", "minimum": 0}, {"const": "single"}],
                                 "description": "Motors per bead or probe as reported, or 'single' when single-motor conditions are stated."},
            "single_motor_verification": enum(["poisson_dilution", "fraction_moving", "photobleaching", "stated_only", "none_stated"],
                                              "How single-motor conditions were verified."),
            "single_motor_verification_other": text("Free text when single_motor_verification = other."),
        }, "Motor-probe link. Multi-motor beads inflate stall force and run length."),
        "Load": obj({
            "geometry": enum(["single_bead", "three_bead", "dumbbell", "surface_tether", "magnetic_bead", "none"], "Load geometry."),
            "geometry_other": text("Free text when geometry = other."),
            "direction": enum(LOAD_DIRECTION, "Load direction relative to motion."),
            "vertical_component_considered": {"type": "boolean", "description": "Whether the vertical (z) force component was accounted for."},
        }, "Load. Trap stiffness and instrument details stay on the linked SMASH-BIO record."),
        "Feedback": obj({"mode": enum(FEEDBACK, "Feedback (clamp) mode."), "mode_other": text("Free text when mode = other.")},
                        "Feedback mode; it determines which observables are valid."),
        "Chemistry": obj({
            "nucleotide": obj({"species": text("e.g. ATP, GTP, NTPs, dNTPs."), "concentration_uM": num("µM.")}, "Fuel nucleotide."),
            "adp_uM": num("[ADP] in µM."), "pi_uM": num("[Pi] in µM."), "analogues": strings("e.g. AMP-PNP, ATPγS."),
            "mg_mM": num("[Mg2+] in mM."), "ionic_strength_mM": num("mM."), "temperature_C": num("°C.", minimum=None),
            "crowders": strings("e.g. PEG, Ficoll."), "inhibitors": strings("e.g. vanadate, ciliobrevin."),
        }, "Chemistry. Units are fixed by the field names."),
        "Reporting": obj({
            "n_molecules": count("Motors analysed."), "n_runs": count("Runs analysed."), "n_steps": count("Steps analysed."),
            "step_detection": obj({"method": text("e.g. Kerssemakers, t-test, HMM, change-point."), "settings": text("As reported.")},
                                  "Step detection."),
            "fit_models": strings("e.g. Boltzmann F-V, gamma dwell time, Michaelis-Menten."),
        }, "What was analysed and how."),
        "Classification": obj({
            "route": {"enum": ["entity_specific", "entity_generic", "title", "curated"],
                      "description": "How the family was found: a specific or generic gazetteer entity on the SMASH-BIO record, the title, or a curator."},
            "certainty": {"type": "number", "minimum": 0, "maximum": 1,
                          "description": "Route weight x share of the top family among all family hits (hub/motors/classify.py)."},
            "family_hits": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 0},
                            "description": "Score per family; more than one key means the family was ambiguous."},
            "gazetteer": text("Gazetteer file and version used."),
        }, "Automatic family call, kept so it can be audited against the gold set."),
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": BASE + "smash-motor-record.schema.json",
        "title": "SMASH-MOTOR processive-motor record",
        "description": ("One processive-motor study (single-molecule, or gliding / ensemble), derived from one SMASH-BIO record and "
                        f"linked to it by smfs_record_id. Version {VERSION}. Its own record type (MOTOR-######), schemas and downloads; "
                        "shared definitions are referenced from the published SMFS 3.1.0 schemas, which are not modified. Every field "
                        "except identity and family is optional and is left out when the paper does not report it."),
        "type": "object",
        "additionalProperties": False,
        "required": ["record_id", "schema_version", "category", "smfs_record_id", "publication", "family", "assay_type", "curation"],
        "properties": {
            "record_id": {"type": "string", "pattern": "^MOTOR-[0-9]{6}$"},
            "schema_version": {"const": VERSION},
            "category": {"const": "processive_motor", "description": "Fixed label so any consumer can branch on it."},
            "smfs_record_id": {"type": "string", "pattern": "^SMFS-[0-9]{6}$", "description": "The SMASH-BIO record of the same study."},
            "publication": {"$ref": SMFS + "#/$defs/Publication"},
            "technique": obj({"primary": {"$ref": SMFS + "#/$defs/TechniqueName"},
                              "force_application_geometry": {"$ref": SMFS + "#/$defs/Technique/properties/force_application_geometry"}},
                             "Technique, in the SMASH-BIO vocabulary (copied from the linked record)."),
            "assay_type": {"enum": ["single_molecule", "gliding_or_ensemble", "other"],
                           "description": "gliding_or_ensemble: gliding or other ensemble motility assay without a single-molecule readout."},
            "experiment_type": enum(EXPERIMENT_TYPES, "Experiment type: the column of the motor Table 3 (hub/motors/table3_motor.yaml) "
                                    "that decides which fields apply. Left out until it is known."),
            "family": enum(FAMILIES, "Motor family."),
            "family_other": text("Free text when family = other."),
            "isoform": text("Isoform or construct name as the authors give it, e.g. 'kinesin-1 K560'."),
            "uniprot": {"type": "array", "items": {"type": "string", "pattern": UNIPROT_AC}, "description": "UniProt accessions of the motor subunits."},
            "construct": {"$ref": "#/$defs/Construct"},
            "oligomeric_state": text("e.g. monomer, dimer, hexamer, complex with dynactin."),
            "adaptors": strings("Cargo adaptors or activators, e.g. dynactin, BICD2, Hook3, LIS1."),
            "track": {"$ref": "#/$defs/Track"},
            "probe_link": {"$ref": "#/$defs/ProbeLink"},
            "load": {"$ref": "#/$defs/Load"},
            "feedback": {"$ref": "#/$defs/Feedback"},
            "chemistry": {"$ref": "#/$defs/Chemistry"},
            "reporting": {"$ref": "#/$defs/Reporting"},
            "results": {"type": "array", "items": {"$ref": "smash-motor-results.schema.json#/$defs/MotorResult"}},
            "evidence": {"type": "object", "additionalProperties": {"$ref": SMFS + "#/$defs/Evidence"},
                         "description": "Evidence per field, keyed by field path (e.g. 'family', 'load.direction'); values are the SMASH-BIO Evidence object."},
            "classification": {"$ref": "#/$defs/Classification"},
            "fair_completeness": obj({**{s: {"type": ["number", "null"], "minimum": 0, "maximum": 1} for s in ("hardware", "assay", "construct", "solution", "overall")},
                                      "basis": {"type": "string", "description": "experiment_type whose R fields were scored, or 'core' (fields required for every type)."}},
                                     "Fraction of the motor Table 3 fields marked R for this record's experiment type that are filled, per section "
                                     "(hub/motors/table3.py). Measures what is reported and recoverable, not experimental quality."),
            "data_availability": {"$ref": SMFS + "#/$defs/DataAvailability"},
            "curation": obj({"level": {"enum": ["auto", "curated", "author_verified", "gold_annotated"]},
                             "last_updated": {"type": "string", "format": "date"}, "notes": text("Curator notes.")},
                            "Curation level of the motor-specific fields.", required=["level"]),
        },
        "$defs": defs,
    }


def results_schema() -> dict:
    units = {**REUSED, **NEW}
    fv_point = obj({"force_pN": {"type": "number"}, "velocity_nm_s": {"type": "number"},
                    "force_err": {"type": "number", "minimum": 0}, "velocity_err": {"type": "number", "minimum": 0}},
                   "One point of a force-velocity curve (hindering force positive).", required=["force_pN", "velocity_nm_s"])
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": BASE + "smash-motor-results.schema.json",
        "title": "SMASH-MOTOR results",
        "description": (f"Reported motor observables (version {VERSION}). Independent of the SMASH-BIO Result; quantities that also "
                        "exist in SMASH-BIO keep the same name and canonical unit."),
        "$defs": {
            "Observable": {"enum": list(units) + ["other"], "description": "Motor observable vocabulary; canonical units in ObservableUnits."},
            "ObservableUnits": {"const": units},
            "MotorResult": {
                "type": "object", "additionalProperties": False, "required": ["quantity", "unit"],
                "properties": {
                    "quantity": {"$ref": "#/$defs/Observable"},
                    "label": text("Name as written by the authors."),
                    "value": {"type": ["number", "null", "array"], "items": fv_point,
                              "description": "A number; for force_velocity_curve an array of points. Nucleic-acid motors: step_size, velocity "
                                             "and processivity_run_length in nm, nm/s, nm, with the source unit in source.unit_as_reported."},
                    "min": {"type": "number"}, "max": {"type": "number"},
                    "unit": {"type": "string"},
                    "uncertainty": {"type": "number", "minimum": 0},
                    "uncertainty_type": {"enum": ["SD", "SEM", "CI95", "fit_error", "range", "unspecified"]},
                    "statistic": {"enum": ["mean", "median", "mode", "most_probable", "fit_parameter", "single_value", "range"]},
                    "n_molecules": {"type": "integer", "minimum": 0}, "n_events": {"type": "integer", "minimum": 0},
                    "conditions": obj({
                        "load_pN": {"type": "number", "description": "Load in pN (hindering positive)."},
                        "load_direction": {"enum": LOAD_DIRECTION}, "atp_uM": {"type": "number", "minimum": 0},
                        "feedback_mode": {"enum": FEEDBACK}, "temperature_K": {"type": "number", "minimum": 0},
                        "rise_per_unit_nm": {"type": "number", "minimum": 0, "description": "nm per bp or nt used for the conversion."},
                        "rise_assumed": {"type": "boolean", "description": "true when 0.34 nm/bp (B-DNA) was assumed because the paper gives none."},
                        "construct": text("Construct the value applies to, if the study has several."),
                    }, "Conditions the value was measured under; never pooled across conditions."),
                    "model": text("Analysis model, e.g. Boltzmann, gamma, Michaelis-Menten."),
                    "source": obj({"location": {"enum": ["abstract", "results_text", "methods", "table", "figure", "supplement", "dataset"]},
                                   "snippet": {"type": "string", "maxLength": 400},
                                   "extraction": {"enum": ["rule_v1", "manual", "author_submitted", "gold_annotation"]},
                                   "confidence": {"enum": ["high", "medium", "low"]},
                                   "unit_as_reported": text("Unit as written, e.g. bp, nt/s.")}, "Where the value came from."),
                },
                "allOf": [{"if": {"properties": {"quantity": {"const": "force_velocity_curve"}}, "required": ["quantity"]},
                           "then": {"properties": {"value": {"type": "array"}}},
                           "else": {"properties": {"value": {"type": ["number", "null"]}}}}],
            },
        },
    }


def write() -> None:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for name, s in (("smash-motor-record.schema.json", record_schema()), ("smash-motor-results.schema.json", results_schema())):
        (SCHEMA_DIR / name).write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote", (SCHEMA_DIR / name).relative_to(SCHEMA_DIR.parents[2]))


if __name__ == "__main__":
    write()
