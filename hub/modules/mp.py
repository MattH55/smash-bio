"""Mass-photometry module."""
from modules.base import ModuleSpec, ta


MP = ModuleSpec(
    slug="mp",
    name="mass photometry",
    short="MP",
    nav_label="Mass photometry",
    record_prefix="MP",
    schema_file="smash-mp-record.schema.json",
    results_schema_file="smash-mp-results.schema.json",
    version="1.0.0",
    schema_subdir="modules",
    harvest_queries={
        "mp_generic": ta(
            "mass photometry", "mass photometric", "mass-sensitive particle tracking",
            "MSPT",
        ),
        "isac": ta(
            "interferometric scattering", "iSCAT", "interferometric scattering microscopy",
        ),
        "mp_applications": ta(
            "molecular mass", "oligomeric state", "AAV full empty", "capsid empty",
            "mass measurement of single molecules",
        ),
    },
    technique_patterns={
        "mass_photometry": r"mass photometry|mass photometric|refeyn|discovermp",
        "isac": r"iscat|interferometric scattering",
        "mspt": r"mass[- ]sensitive particle tracking|\bmspt\b",
    },
    bio_pattern=r"\b(protein|complex|oligomer|antibody|igg|aav|capsid|virus|"
                r"dna|rna|nucleic|membrane protein|receptor|chaperone|enzyme|"
                r"vsv[- ]g|ferritin|streptavidin|bsa|ribosome|exosome|vesicle)\b",
    single_molecule_pattern=r"single[- ]molecule|individual (molecule|particle|protein)|"
                             r"mass photometry|contrast|molecular mass distribution",
    methods_pattern=r"\b(instrument|calibration|benchmark|apparatus|software|"
                    r"algorithm|framework|simulation)\b",
    out_of_scope_pattern=r"\b(materials?|catalyst|nanoparticle synthesis|"
                         r"surface plasmon|thin film|optical trapping of(?![^.]{0,40}bio))\b",
    observables=(
        "molecular_mass_kDa", "relative_abundance", "oligomeric_state",
        "dissociation_constant_M", "binding_stoichiometry", "mass_resolution_kDa",
        "event_count", "aav_full_fraction", "diffusion_coefficient_um2_s-1",
    ),
    observable_patterns={
        "molecular_mass_kDa": r"mass of[^.]{0,40}?([0-9]*\.?[0-9]+)\s*kda",
        "relative_abundance": r"(?:relative abundance|population)[^.]{0,40}?([0-9]*\.?[0-9]+)\s*%",
        "dissociation_constant_M": r"\b(?:kd|dissociation constant)\b[^.]{0,40}?([0-9]*\.?[0-9]+)\s*(?:pm|nm|nm|m)\b",
        "mass_resolution_kDa": r"mass resolution[^.]{0,40}?([0-9]*\.?[0-9]+)\s*kda",
        "aav_full_fraction": r"(?:full|empty)[^.]{0,20}?(?:fraction|percentage)[^.]{0,20}?([0-9]*\.?[0-9]+)\s*%",
        "diffusion_coefficient_um2_s-1": r"diffusion coefficient[^.]{0,40}?([0-9]*\.?[0-9]+)\s*(?:um2/s|µm2/s)",
    },
    raw_formats=("csv", "h5", "mp", "tiff", "json"),
    repositories=("Zenodo", "Figshare", "OSF", "Dryad", "MBDB"),
    extra={"path": "/mp/"},
)