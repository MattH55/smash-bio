"""Single-particle-tracking module."""
from modules.base import ModuleSpec, ta


SPT = ModuleSpec(
    slug="spt",
    name="single-particle tracking",
    short="SPT",
    nav_label="Single-particle tracking",
    record_prefix="SPT",
    schema_file="smash-spt-record.schema.json",
    results_schema_file="smash-spt-results.schema.json",
    version="1.0.0",
    schema_subdir="modules",
    harvest_queries={
        "spt_generic": ta(
            "single-particle tracking", "single particle tracking",
            "single-molecule tracking", "single molecule tracking", "SPT",
        ),
        "spt_probe_specific": ta(
            "quantum dot tracking", "gold nanoparticle tracking",
            "PALM tracking", "u-track", "TrackMate", "Spot-On",
        ),
        "spt_membrane": ta(
            "receptor diffusion", "membrane diffusion", "membrane protein tracking",
            "live-cell tracking", "chromatin locus tracking",
        ),
    },
    technique_patterns={
        "single_particle_tracking": r"single[- ]particle tracking|single[- ]molecule tracking|\bspt\b",
        "palm_tracker": r"palm[- ]?track|spt[- ]palm|photoactivatable.{0,40}track",
        "quantum_dot": r"quantum[- ]dot.{0,40}(track|label)|qdot",
        "gold_nanoparticle": r"gold nanoparticle.{0,40}(track|label)|nanorod.{0,40}track",
        "spot_on_style": r"spot[- ]on|vb ?spt|diffusion[- ]state",
    },
    bio_pattern=r"\b(receptor|protein|channel|transporter|dna|rna|chromatin|"
                r"nucleosome|virus|vesicle|motor|kinesin|myosin|dynein|actin|"
                r"microtubule|membrane|cell|bacteri|organelle|mrna|ribosome|"
                r"transcription factor|growth factor|integrin|gpi)\b",
    single_molecule_pattern=r"single[- ]particle|single[- ]molecule|individual (molecule|particle)|"
                             r"trajector|track(ing|ed)?|diffusion coefficient|camera[- ]based",
    methods_pattern=r"\b(software|algorithm|tool|benchmark|simulation|tracking (method|framework)|"
                    r"open[- ]source|pipeline)\b",
    out_of_scope_pattern=r"\b(materials? (science|physics)|catalyst|colloidal (crystal|suspension)|"
                         r"ocean|turbulence|traffic|animal (herd|flock)|swarm robotics)\b",
    observables=(
        "diffusion_coefficient_um2_s-1", "anomalous_exponent_alpha", "bound_fraction",
        "residence_time_s", "confinement_radius_nm", "velocity_nm_s-1", "run_length_nm",
        "step_size_nm", "localization_precision_nm", "mean_track_length_frames",
        "n_diffusive_states",
    ),
    observable_patterns={
        "diffusion_coefficient_um2_s-1": r"diffusion coefficient[^.]{0,40}?([0-9]*\.?[0-9]+)\s*(?:um2/s|µm2/s|um²/s)",
        "anomalous_exponent_alpha": r"anomalous (?:exponent|diffusion)[^.]{0,40}?([0-9]*\.?[0-9]+)",
        "bound_fraction": r"bound fraction[^.]{0,40}?([0-9]*\.?[0-9]+)",
        "residence_time_s": r"(?:residence|dwell) time[^.]{0,40}?([0-9]*\.?[0-9]+)\s*(?:s|ms)",
        "confinement_radius_nm": r"confinement (?:radius|diameter)[^.]{0,40}?([0-9]*\.?[0-9]+)\s*nm",
        "velocity_nm_s-1": r"velocity[^.]{0,40}?([0-9]*\.?[0-9]+)\s*nm/s",
        "run_length_nm": r"run length[^.]{0,40}?([0-9]*\.?[0-9]+)\s*nm",
        "step_size_nm": r"step size[^.]{0,40}?([0-9]*\.?[0-9]+)\s*nm",
        "localization_precision_nm": r"localization precision[^.]{0,40}?([0-9]*\.?[0-9]+)\s*nm",
        "n_diffusive_states": r"([0-9]+)\s+(?:diffusive|diffusion) states",
    },
    raw_formats=("csv", "trackmate_xml", "matlab", "ome-tiff", "tiff", "nd2", "czi"),
    repositories=("BioImage Archive", "Image Data Resource", "Zenodo", "Figshare", "Dryad", "OSF"),
    extra={"path": "/spt/"},
)