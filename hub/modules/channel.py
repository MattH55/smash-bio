"""Single-channel electrophysiology module."""
from modules.base import ModuleSpec, ta


CHANNEL = ModuleSpec(
    slug="channel",
    name="single-channel electrophysiology",
    short="SC",
    nav_label="Single-channel recording",
    record_prefix="SC",
    schema_file="smash-channel-record.schema.json",
    results_schema_file="smash-channel-results.schema.json",
    version="1.0.0",
    schema_subdir="modules",
    harvest_queries={
        "channel_generic": ta(
            "single-channel recording", "single channel recording",
            "single-channel current", "single channel conductance",
            "single-channel conductance",
        ),
        "channel_config": ta(
            "cell-attached patch", "inside-out patch", "outside-out patch",
            "planar lipid bilayer", "droplet interface bilayer",
        ),
        "channel_patch": ta(
            "patch clamp", "patch-clamp", "single channel kinetics",
        ),
    },
    technique_patterns={
        "cell_attached": r"cell[- ]attached",
        "inside_out": r"inside[- ]out",
        "outside_out": r"outside[- ]out",
        "planar_bilayer": r"planar (?:lipid )?bilayer|black lipid membrane|\bblm\b",
        "droplet_interface": r"droplet interface bilayer|\bdib\b",
        "single_channel": r"single[- ]channel|single channel",
    },
    bio_pattern=r"\b(ion channel|channel|receptor|transporter|porin|toxin|"
                r"hemolysin|aquaporin|connexin|k\+|na\+|cl-|ca2\+| acetylcholine|"
                r"gaba|nmda|ampa|cf?tr|trpv|kv|nav|bk|sk|pore|conductance)\b",
    single_molecule_pattern=r"single[- ]channel|single channel|unitary (current|conductance)|"
                             r"open probability|dwell time|patch (clamp|pipette)|bilayer",
    methods_pattern=r"\b(idealization|algorithm|software|analysis (method|tool)|"
                    r"kinetic (model|scheme)|maximum likelihood|benchmark)\b",
    out_of_scope_pattern=r"\b(nanopore sequencing|dna sequencing|analyte sensing|"
                         r"whole[- ]cell (current|recording) only|maldi|electrochemical sensor)\b",
    observables=(
        "unitary_conductance_pS", "unitary_current_pA", "open_probability",
        "mean_open_time_ms", "mean_closed_time_ms", "burst_duration_ms",
        "n_open_states", "n_closed_states", "transition_rate_s-1",
        "subconductance_level_pS", "ec50_M", "reversal_potential_mV", "dwell_time_ms",
    ),
    observable_patterns={
        "unitary_conductance_pS": r"(?:unitary|single[- ]channel) conductance[^.]{0,40}?([0-9]*\.?[0-9]+)\s*ps",
        "unitary_current_pA": r"(?:unitary|single[- ]channel) current[^.]{0,40}?([0-9]*\.?[0-9]+)\s*pa",
        "open_probability": r"open probability[^.]{0,40}?([0-9]*\.?[0-9]+)\s*(?:\(|,|\s|$)",
        "mean_open_time_ms": r"mean open time[^.]{0,40}?([0-9]*\.?[0-9]+)\s*ms",
        "mean_closed_time_ms": r"mean closed time[^.]{0,40}?([0-9]*\.?[0-9]+)\s*ms",
        "burst_duration_ms": r"burst duration[^.]{0,40}?([0-9]*\.?[0-9]+)\s*ms",
        "subconductance_level_pS": r"subconductance (?:level|state)[^.]{0,40}?([0-9]*\.?[0-9]+)\s*ps",
        "ec50_M": r"\bec50\b[^.]{0,40}?([0-9]*\.?[0-9]+)\s*(?:pm|nm|um|m)\b",
        "reversal_potential_mV": r"reversal potential[^.]{0,40}?(-?[0-9]*\.?[0-9]+)\s*mv",
    },
    raw_formats=("abf", "heka_dat", "nwb", "qub_qdf", "ldt", "csv"),
    repositories=("DANDI", "Zenodo", "Figshare", "OSF", "Dryad"),
    extra={"path": "/channel/", "related_resources": ("Channelpedia", "GtoPdb")},
)