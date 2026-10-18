"""smFRET module: DNA/RNA single-molecule FRET."""
from modules.base import ModuleSpec, ta


FRET = ModuleSpec(
    slug="fret",
    name="single-molecule FRET",
    short="smFRET",
    nav_label="DNA/RNA smFRET",
    record_prefix="FRET",
    schema_file="smash-fret-record.schema.json",
    results_schema_file="smash-fret-results.schema.json",
    version="1.0.0",
    schema_subdir="",
    harvest_queries={
        "smfret_generic": ta(
            "single-molecule FRET", "single molecule FRET", "smFRET",
            "single-pair FRET", "spFRET",
        ),
        "smfret_multiparameter": ta(
            "multiparameter fluorescence", "burst analysis", "ALEX", "PIE",
            "alternating laser excitation", "pulsed interleaved excitation",
        ),
        "smfret_hybrid_force": (
            '(TITLE_ABS:"smFRET" OR TITLE_ABS:"single-molecule FRET") AND '
            '(TITLE_ABS:"optical tweezers" OR TITLE_ABS:"magnetic tweezers" '
            'OR TITLE_ABS:"force spectroscopy")'
        ),
    },
    technique_patterns={
        "smfret_generic": r"single[- ]molecule fret|single molecule fret|\bsmfret\b|single[- ]pair fret|\bspfret\b",
        "confocal_burst": r"confocal.{0,60}(fret|burst)|burst analysis|diffusion[- ]based",
        "tirf_widefield": r"\btirf\b|total internal reflection|wide-?field|\bhilo\b",
        "alex": r"\balex\b|alternating[- ]laser excitation|nsalex|msalex",
        "pie": r"\bpie\b|pulsed interleaved excitation",
        "mfd": r"multiparameter fluorescence detection|\bmfd\b",
        "zmw": r"zero[- ]mode waveguide|\bzmw\b|nanopore.{0,40}fret",
        "in_cell": r"in[- ]cell.{0,40}fret|intracellular.{0,40}fret|live[- ]cell.{0,40}fret",
    },
    bio_pattern=r"\b(dna|rna|nucleic|nucleosome|chromatin|hairpin|g-quadruplex|"
                r"riboswitch|ribosome|trna|mrna|sirna|aptamer|protein|peptide|"
                r"enzyme|polymerase|helicase|nuclease|integrase|rev|rre|snare|"
                r"chaperone|hsp70|hsp90|idp|alpha-synuclein|tau|p53|importin|"
                r"receptor|ligand|membrane|transporter|lacy|leut|gltph|betp)\b",
    single_molecule_pattern=r"single[- ]molecule|single[- ]pair|single molecule|\bsmfret\b|\bspfret\b|"
                             r"single[- ]molecule fret|individual molecule|burst",
    methods_pattern=r"\b(instrument|apparatus|benchmark|blind study|calibration|"
                    r"analysis (tool|software|framework)|open[- ]source software|"
                    r"simulation|algorithm)\b",
    out_of_scope_pattern=r"\b(flim|ensemble fret|bulk fret|biosensor|fret sensor|"
                         r"fluorescence lifetime imaging|quantum dot|semiconductor|"
                         r"plasmonic|forster resonance energy transfer between dyes)\b",
    observables=(
        "fret_efficiency_apparent", "fret_efficiency_accurate", "stoichiometry",
        "interdye_distance_mean_nm", "interdye_distance_R_E_nm", "donor_lifetime_ns",
        "acceptor_lifetime_ns", "anisotropy", "population_fraction", "n_states",
        "transition_rate_s-1", "dwell_time_ms", "radius_of_gyration_nm",
        "end_to_end_distance_nm", "scaling_exponent_nu", "dissociation_constant_M",
        "forster_radius_nm",
    ),
    observable_patterns={
        "fret_efficiency_apparent": r"fret efficiency[^.]{0,40}?([0-9]*\.?[0-9]+)",
        "fret_efficiency_accurate": r"accurate (?:fret )?efficiency[^.]{0,40}?([0-9]*\.?[0-9]+)",
        "stoichiometry": r"stoichiometry[^.]{0,40}?([0-9]*\.?[0-9]+)",
        "interdye_distance_mean_nm": r"(?:interdye|inter-?dye) distance[^.]{0,40}?([0-9]*\.?[0-9]+)\s*nm",
        "donor_lifetime_ns": r"donor (?:fluorescence )?lifetime[^.]{0,40}?([0-9]*\.?[0-9]+)\s*ns",
        "acceptor_lifetime_ns": r"acceptor (?:fluorescence )?lifetime[^.]{0,40}?([0-9]*\.?[0-9]+)\s*ns",
        "anisotropy": r"anisotropy[^.]{0,40}?([0-9]*\.?[0-9]+)",
        "transition_rate_s-1": r"(?:transition|rate constant)[^.]{0,40}?([0-9]*\.?[0-9]+)\s*(?:s-?1|/s|s\^-1)",
        "dwell_time_ms": r"(?:dwell|residence) time[^.]{0,40}?([0-9]*\.?[0-9]+)\s*ms",
        "radius_of_gyration_nm": r"radius of gyration[^.]{0,40}?([0-9]*\.?[0-9]+)\s*nm",
        "end_to_end_distance_nm": r"end[- ]to[- ]end distance[^.]{0,40}?([0-9]*\.?[0-9]+)\s*nm",
        "scaling_exponent_nu": r"scaling exponent[^.]{0,40}?([0-9]*\.?[0-9]+)",
        "dissociation_constant_M": r"\b(?:kd|dissociation constant)\b[^.]{0,40}?([0-9]*\.?[0-9]+)\s*(?:pm|nm|um|m)\b",
        "forster_radius_nm": r"(?:forster|förster) radius[^.]{0,40}?([0-9]*\.?[0-9]+)\s*nm",
    },
    raw_formats=("Photon-HDF5", "ptu", "pt3", "ht3", "spc", "smd", "traces", "h5", "csv", "npy", "tiff"),
    repositories=("Zenodo", "Figshare", "OSF", "Dryad", "institutional"),
    citation_dois=(
        "10.7554/eLife.60416",
        "10.1038/s41592-018-0085-0",
        "10.1016/j.bpj.2015.11.013",
    ),
    extra={"pdb_ihm": True, "path": "/fret/"},
)