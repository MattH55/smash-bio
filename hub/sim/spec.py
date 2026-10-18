"""The SimSpec contract and the single Simulations-category spec.

Only two attributes are needed for the shared harvester
(``modules.harvest.harvest``) to work unchanged: ``slug`` and
``harvest_queries``. Everything else drives classification, extraction and
record building. The harvest query fragments are the ones named in the brief,
verbatim, so the search strategy is auditable against the brief.
"""
from dataclasses import dataclass, field


def ta(*phrases):
    """Europe PMC TITLE_ABS OR-query over the given phrases."""
    return "(" + " OR ".join(f'TITLE_ABS:"{p}"' for p in phrases) + ")"


@dataclass(frozen=True)
class SimSpec:
    slug: str
    name: str
    short: str
    nav_label: str
    record_prefix: str
    schema_file: str
    results_schema_file: str
    version: str
    schema_subdir: str
    harvest_queries: dict
    molecule_patterns: dict           # molecule_type -> regex
    forcing_pattern: str             # evidence of force-driven pulling
    simulation_pattern: str          # evidence it is a simulation/model
    model_family_patterns: dict      # family -> regex
    family_group: dict               # family -> protein|nucleic_acid|other
    software_patterns: dict          # name -> regex
    solvent_patterns: dict           # solvent -> regex
    mode_patterns: dict              # protocol mode -> regex
    out_of_scope_pattern: str
    observables: tuple
    observable_patterns: dict        # observable -> regex with groups value/unit
    unit_aliases: dict               # unit text -> (normalised unit, unit_system)
    reduced_markers: tuple           # phrases that mark reduced (model) units
    conversion_patterns: dict        # unit_conversions key -> regex with groups value/unit
    artifact_patterns: dict          # artifact -> regex with group value
    raw_formats: tuple
    repositories: tuple
    citation_dois: tuple = ()
    extra: dict = field(default_factory=dict)

    @property
    def record_id_pattern(self):
        return rf"^{self.record_prefix}-[0-9]{{6}}$"

    def record_id(self, number):
        return f"{self.record_prefix}-{int(number):06d}"

    def page_path(self):
        return f"/{self.slug}/"

    def out_prefix(self):
        return self.slug


SIM = SimSpec(
    slug="sim",
    name="pulling simulations",
    short="Simulations",
    nav_label="Simulations",
    record_prefix="SIM",
    schema_file="smash-sim-record.schema.json",
    results_schema_file="smash-sim-results.schema.json",
    version="1.0.0",
    schema_subdir="sim",
    harvest_queries={
        # brief Phase 3, verbatim
        "proteins_smd": '("steered molecular dynamics" AND (unfolding OR "mechanical unfolding" OR "force spectroscopy"))',
        "proteins_cg": '("coarse-grained" AND ("pulling" OR "mechanical unfolding") AND protein)',
        "proteins_go": '("Go model" AND (stretching OR unfolding OR pulling))',
        "proteins_forceclamp": '("constant velocity pulling" OR "force-clamp simulation")',
        "na_unzip": '(("DNA" OR "RNA") AND (unzipping OR "mechanical unfolding" OR overstretching) '
                     'AND (simulation OR "molecular dynamics" OR oxDNA OR oxRNA OR "coarse-grained"))',
        "na_pseudoknot": '(pseudoknot AND "steered molecular dynamics")',
        "na_riboswitch": '(riboswitch AND (pulling OR "mechanical unfolding") AND simulation)',
        "na_gquad": '("G-quadruplex" AND unfolding AND "steered molecular dynamics")',
    },
    molecule_patterns={
        "RNA_protein": r"\b(ribonucleoprotein|rna[- ]protein|rnp|spliceosome|ribosome|telomerase)\b",
        "DNA_protein": r"\b(dna[- ]protein|nucleoprotein|nucleosome|chromatin|polymerase|helicase|"
                       r"recombinase|integrase|transposase|restriction enzyme|recbcd)\b",
        "RNA": r"\b(rna|riboswitch|ribozyme|aptamer|mrna|trna|rrna|pseudoknot|g[- ]quadruplex|"
               r"hairpin|kissing loop|oxrna|hire[- ]rna)\b",
        "DNA": r"\b(dna|oxdna|duplex|double[- ]stranded|dsdna|ssdna|aptamer|hairpin|g[- ]quadruplex|"
               r"i[- ]motif|triplex|overstretching)\b",
        "protein": r"\b(protein|peptide|polypeptide|enzyme|domain|antibody|receptor|kinase|protease|"
                   r"chaperone|motor protein|titin|ubiquitin|sod1|lysozyme|barnase|spectrin)\b",
    },
    forcing_pattern=r"\b(pull(?:ed|ing)?|unzip(?:ped|ping)?|unfold(?:ed|ing)?|overstretch(?:ed|ing)?|"
                    r"force[- ](?:driven|induced|clamp(?:ed)?|ramp)|constant[- ]velocity|stretch(?:ed|ing)?|"
                    r"mechanically (?:unfold|unzip|pull)|rupture)\b",
    simulation_pattern=r"\b(molecular dynamics|\bmd\b|simulat(?:e|ed|ion|ions|ing)|"
                       r"monte[- ]carlo|coarse[- ]grained|in silico|\bmodel(?:s|led|ling)?\b|\bmd\b|"
                       r"\bsmd\b|computational(?:ly)?)\b",
    model_family_patterns={
        "Go_heavy_atom": r"(heavy[- ]atom|all[- ]heavy[- ]atom|heavy[- ]atom[- ]resolution).{0,60}"
                         r"(\bg[oō]\b|structure[- ]based)|(\bg[oō]\b|structure[- ]based).{0,60}heavy[- ]atom",
        "Go_CA": r"(\bc[αa]\b[- ]?(?:only[- ]?)?g[oō]\b|\bc[αa][- ]?go\b|c[αa][- ]?g[oō][- ]?model|"
                 r"g[oō][- ]?(?:type[- ])?model|structure[- ]based model|native[- ]contact (?:model|map)|"
                 r"\bsmog\b|clementi[- ]nymeyer)",
        "SOP": r"(\bsop\b|self[- ]organized polymer)",
        "AWSEM": r"(\bawsem\b|associative memory.{0,25}water[- ]mediated)",
        "Martini": r"\bmartini\b",
        "all_atom_explicit_solvent": r"(all[- ]atom|fully atomistic|atomistic).{0,80}"
                                     r"(explicit(?:ly)?[- ]?solvat\w*|tip3p|tip4p|spc/e|spce|water box|"
                                     r"explicit water|tip3)|"
                                     r"(explicit(?:ly)?[- ]?solvat\w*|tip3p|tip4p|spc/e|spce|water box)"
                                     r".{0,80}(all[- ]atom|atomistic)",
        "all_atom_implicit_solvent": r"(all[- ]atom|atomistic|fully atomistic).{0,80}"
                                     r"(implicit(?:ly)?[- ]?solvat\w*|generalized born|\bgb\b|"
                                     r"poisson[- ]boltzmann|sa model|implicit water)|"
                                     r"(implicit(?:ly)?[- ]?solvat\w*|generalized born|poisson[- ]boltzmann)"
                                     r".{0,80}(all[- ]atom|atomistic)",
        "oxRNA": r"\boxrna\b",
        "oxDNA": r"\boxdna\b",
        "TIS": r"\btis\b|three[- ]interaction[- ]site",
        "HiRE_RNA": r"hire[- ]?rna|\bhire[- ]rna\b",
        "thermodynamic_nearest_neighbour": r"(nearest[- ]neighbou?r|vienna(?:rna)?|rnafold|"
                                           r"turner (?:model|parameters|rules)|partition function|"
                                           r"thermodynamic (?:model|parameters)|two[- ]state (?:model|"
                                           r"thermodynamics))",
    },
    family_group={
        "Go_CA": "protein", "Go_heavy_atom": "protein", "SOP": "protein", "AWSEM": "protein",
        "Martini": "protein", "all_atom_explicit_solvent": "protein",
        "all_atom_implicit_solvent": "protein", "oxDNA": "nucleic_acid", "oxRNA": "nucleic_acid",
        "TIS": "nucleic_acid", "HiRE_RNA": "nucleic_acid",
        "thermodynamic_nearest_neighbour": "nucleic_acid", "other": "other",
    },
    software_patterns={
        "NAMD": r"\bnamd\b", "GROMACS": r"\bgromacs\b", "OpenMM": r"open\s*mm\b",
        "LAMMPS": r"\blammps\b", "SMOG 2": r"\bsmog\s*2\b", "OpenSMOG": r"open\s*smog",
        "oxDNA": r"\boxdna\b", "oxRNA": r"\boxrna\b", "ViennaRNA": r"vienna\s*rna|viennarna",
        "AMBER": r"\bamber\b", "CHARMM": r"\bcharmm\b", "OpenSMOG/CafeMol": r"cafemol",
        "ESPResSo": r"\bespresso\b", "HOOMD": r"\bhoomd\b", "CAMPARI": r"\bcampari\b",
        "PLUMED": r"\bplumed\b", "GROMOS": r"\bgromos\b",
    },
    solvent_patterns={
        "explicit": r"explicit(?:ly)?[- ]?solvat\w*|tip3p|tip4p|spc/e|spce|explicit water|water box",
        "implicit": r"implicit(?:ly)?[- ]?solvat\w*|generalized born|poisson[- ]boltzmann|sa model",
        "none": r"in vacuum|vacuum|no solvent|solvent[- ]free|gas phase",
    },
    mode_patterns={
        "boxed_MD": r"boxed molecular dynamics|\bbxd\b",
        "force_ramp": r"force[- ]ramp|ramp(?:ed|ing)? (?:force|load)|linearly increasing (?:force|load)|"
                      r"increasing (?:the )?force",
        "constant_force": r"constant[- ]force|force[- ]clamp(?:ed)?|\bforce clamp\b|"
                          r"constant (?:load|tension)|fixed[- ]force",
        "constant_velocity": r"constant[- ]velocity|steered molecular dynamics|\bsmd\b|"
                             r"constant speed|velocity[- ]clamp|constant[- ]velocity pulling|"
                             r"pulled at (?:a )?constant",
        "equilibrium_under_force": r"equilibrium (?:simulation|simulations|md|molecular dynamics)"
                                   r".{0,40}(?:under|at|with) (?:a )?(?:constant )?(?:force|load|tension)|"
                                   r"umbrella sampling|metadynamics|free[- ]energy (?:profile|landscape)|"
                                   r"adaptive biasing force|\babf\b|weighted histogram|\bwham\b",
        "other": r"pulling (?:protocol|simulation|experiment)|steered|forced (?:unfolding|unbinding)",
    },
    out_of_scope_pattern=r"\b(graphene|nanotube|nanowire|metallic glass|alloy|ceramic|concrete|"
                         r"polymer melt|block copolymer|self[- ]assembled monolayer|"
                         r"lithium|battery|semiconductor|solar cell|photovoltaic|"
                         r"unbiased (?:equilibrium )?molecular dynamics|"
                         r"folding@home|protein folding (?:kinetics|rates)? (?:in the absence of|without) force)\b",
    observables=(
        "unfolding_force", "rupture_force", "unbinding_force", "unzipping_force",
        "overstretching_force", "equilibrium_force", "contour_length",
        "contour_length_increment", "persistence_length", "distance_to_transition_state",
        "activation_free_energy", "folding_free_energy", "rate_constant_zero_force",
        "unfolding_rate", "dwell_time", "number_of_steps_or_intermediates", "toughness",
        "work", "loading_rate", "velocity", "molecular_stiffness",
    ),
    observable_patterns={
        # each pattern must expose groups ``value`` and ``unit``
        "unfolding_force": r"(?:unfolding|unfold) force[s]?[^.]{0,60}?"
                           r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>pN|nN|µN|uN)",
        "rupture_force": r"(?:rupture|breaking) force[s]?[^.]{0,60}?"
                         r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>pN|nN|µN|uN)",
        "unbinding_force": r"(?:unbinding|rupture|detachment) force[s]?[^.]{0,60}?"
                           r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>pN|nN|µN|uN)",
        "unzipping_force": r"(?:unzipping|unzip|shearing) force[s]?[^.]{0,60}?"
                           r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>pN|nN|µN|uN)",
        "overstretching_force": r"overstretch\w*[^.]{0,60}?"
                                r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>pN|nN|µN|uN)",
        "equilibrium_force": r"(?:equilibrium|plateau) force[^.]{0,60}?"
                             r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>pN|nN|µN|uN)",
        "contour_length_increment": r"(?:change in (?:the )?contour length|contour[- ]length increment|"
                                    r"Δ\s?lc|delta\s?lc|increase in contour length)[^.]{0,60}?"
                                    r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>nm|Å|angstrom)",
        "contour_length": r"contour length(?!s?\s+increment)[^.]{0,30}?"
                          r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>nm|µm|um|Å)",
        "persistence_length": r"persistence length[^.]{0,30}?"
                              r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>nm|µm|um|Å|pN)",
        "distance_to_transition_state": r"(?:distance to (?:the )?transition state|transition[- ]state "
                                        r"distance|(?:\bx[‡βu]\b)|(?:\bβx\b))[^.]{0,40}?"
                                        r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>nm|Å|σ|sigma)",
        "activation_free_energy": r"(?:activation (?:free )?energy|free[- ]energy barrier|"
                                  r"Δ\s?g[‡\u2021]|delta\s?g\d?)[^.]{0,40}?"
                                  r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>kcal/mol|kcal mol-1|kj/mol|"
                                  r"kJ mol-1|kbt|k b t|kBT|ε|epsilon)",
        "folding_free_energy": r"(?:folding free energy|free energy of folding|Δ\s?g(?:fold)?)[^.]{0,40}?"
                               r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>kcal/mol|kj/mol|kbt|kBT)",
        "rate_constant_zero_force": r"(?:spontaneous|intrinsic|zero[- ]force) (?:unfolding )?rate[^.]{0,40}?"
                                    r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>s-1|s-?1|/s|hz)",
        "unfolding_rate": r"(?:unfolding|rupture) rate[^.]{0,40}?"
                          r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>s-1|s-?1|/s|hz)",
        "dwell_time": r"(?:dwell|residence|waiting) time[^.]{0,40}?"
                      r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>ms|µs|us|ns|s|ps)",
        "number_of_steps_or_intermediates": r"(?:number of\s+)?(?P<value>[0-9]{1,3})\s+"
                                            r"(?:distinct\s+|major\s+|discrete\s+|stable\s+|"
                                            r"partially[- ]folded\s+)?"
                                            r"(?:intermediates|unfolding (?:steps|events|"
                                            r"intermediates))\b",
        "toughness": r"toughness[^.]{0,40}?(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>pN\s?nm|pN·nm|kbt|kBT)",
        "work": r"(?:mechanical work|work done|work performed|work required|reversible work)"
                r"[^.]{0,40}?(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>kbt|kBT|kcal/mol|kj/mol|pN\s?nm)",
        "loading_rate": r"loading rate[^.]{0,40}?(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>pN/s|pN s-1|"
                        r"pN s-?1|nN/s)",
        "velocity": r"(?:pulling|retraction|unzipping) (?:speed|velocity)[^.]{0,40}?"
                    r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>nm/s|nm/ns|nm/µs|nm/us|m/s|µm/s|um/s|nm s-1)",
        "molecular_stiffness": r"(?:molecular )?stiffness[^.]{0,40}?(?P<value>[0-9]*\.?[0-9]+)\s*"
                               r"(?P<unit>pN/nm|n/m)",
    },
    unit_aliases={
        # forces
        "pn": ("pN", "physical"), "nn": ("nN", "physical"), "µn": ("nN", "physical"),
        "un": ("nN", "physical"), "mn": ("mN", "physical"),
        # lengths
        "nm": ("nm", "physical"), "å": ("angstrom", "physical"), "angstrom": ("angstrom", "physical"),
        "a": ("angstrom", "physical"), "µm": ("um", "physical"), "um": ("um", "physical"),
        # energies
        "kbt": ("kBT", "physical"), "k b t": ("kBT", "physical"), "kcal/mol": ("kcal/mol", "physical"),
        "kcal mol-1": ("kcal/mol", "physical"), "kj/mol": ("kJ/mol", "physical"),
        "kj mol-1": ("kJ/mol", "physical"), "kjmol": ("kJ/mol", "physical"),
        "pN nm": ("pN nm", "physical"), "pN·nm": ("pN nm", "physical"),
        # rates and times
        "s-1": ("1/s", "physical"), "/s": ("1/s", "physical"), "hz": ("1/s", "physical"),
        "s": ("s", "physical"),
        "ms": ("ms", "physical"), "µs": ("us", "physical"), "us": ("us", "physical"),
        "ns": ("ns", "physical"), "ps": ("ps", "physical"), "fs": ("fs", "physical"),
        # speeds, load, stiffness
        "nm/s": ("nm/s", "physical"), "nm s-1": ("nm/s", "physical"), "nm/ns": ("nm/ns", "physical"),
        "nm/µs": ("nm/us", "physical"), "nm/us": ("nm/us", "physical"), "m/s": ("m/s", "physical"),
        "µm/s": ("um/s", "physical"), "um/s": ("um/s", "physical"),
        "pN/s": ("pN/s", "physical"), "pN s-1": ("pN/s", "physical"),
        "nN/s": ("nN/s", "physical"), "n/m": ("N/m", "physical"),
        "pN/nm": ("pN/nm", "physical"),
        # reduced / simulation units
        "ε": ("epsilon", "reduced"), "epsilon": ("epsilon", "reduced"),
        "σ": ("sigma", "reduced"), "sigma": ("sigma", "reduced"),
        "lj": ("LJ units", "reduced"), "reduced": ("reduced units", "reduced"),
        "simulation units": ("simulation units", "reduced"), "su": ("simulation units", "reduced"),
    },
    reduced_markers=(
        "reduced units", "reduced unit", "simulation units", "lennard-jones units", "lj units",
        "in units of epsilon", "in units of ε", "in units of sigma", "in units of σ",
        "reduced force", "reduced length", "reduced time", "dimensionless units",
    ),
    conversion_patterns={
        "energy_epsilon": r"(?:energy (?:scale )?)?(?:ε|epsilon)\s*=\s*(?P<value>[0-9]*\.?[0-9]+)\s*"
                          r"(?P<unit>kcal/mol|kcal mol-1|kj/mol|kJ mol-1|kbt|kBT)",
        "length_sigma": r"(?:length (?:scale )?)?(?:σ|sigma)\s*=\s*(?P<value>[0-9]*\.?[0-9]+)\s*"
                        r"(?P<unit>nm|Å|angstrom)",
        "time_tau": r"(?:time (?:scale )?)?(?:τ|tau)\s*=\s*(?P<value>[0-9]*\.?[0-9]+)\s*"
                    r"(?P<unit>ps|ns|µs|us|s)",
        "force_scale": r"(?:force (?:scale )?)\s*[:=]?\s*(?P<value>[0-9]*\.?[0-9]+)\s*"
                       r"(?P<unit>pN|nN|kbt/nm|kBT/nm)",
        "temperature": r"(?:at|temperature (?:of)?\s*)(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>k|kelvin)\b",
    },
    artifact_patterns={
        "trajectories": r"(?:trajector(?:y|ies)|time series|frames?)\s*(?:are|were|is)?\s*"
                        r"(?:available|deposited|provided|shared|uploaded)",
        "force_extension_curves": r"(?:force[- ](?:extension|distance) (?:curves?|profiles?)|"
                                  r"force[- ]extension data)\s*(?:are|were|is)?\s*"
                                  r"(?:available|deposited|provided|shared|published)",
        "input_files": r"(?:input files?|topolog(?:y|ies)|parameter files?|starting structures?|"
                       r"structure files?)\s*(?:are|were|is)?\s*(?:available|deposited|provided|shared|"
                       r"uploaded)",
        "scripts": r"(?:scripts?|code|source code|analysis (?:scripts?|code)|workflow)\s*"
                   r"(?:are|were|is)?\s*(?:available|deposited|provided|shared|released|on github)",
    },
    raw_formats=("xtc", "dcd", "trr", "nc", "netcdf", "gro", "pdb", "psf", "dat", "csv", "npy",
                 "h5", "json", "top", "itp", "in", "conf", "tpr"),
    repositories=("Zenodo", "Figshare", "OSF", "Dryad", "BioStudies", "Fairdata", "GitHub",
                  "Materials Cloud", "institutional"),
    citation_dois=(
        "10.1371/journal.pcbi.1005211",   # Habibi, Rottler & Plotkin 2016, CG force spectroscopy fidelity
        "10.1038/s41467-017-01996-1",     # Sen Mojumdar et al. 2017, SOD1 Cα-Gō pulling
        "10.1063/1.4960973",              # oxDNA2
    ),
    extra={"path": "/sim/", "category_label": "Simulation"},
)