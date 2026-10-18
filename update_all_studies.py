"""
Comprehensive update of website/js/data.js for all 36 curated studies.
- Citations removed (all entries)
- Experimental parameters populated from full-text extraction where available
- Placeholder values cleared (null) where data was not obtainable
"""

import json
import re

with open('website/js/data.js', 'r', encoding='utf-8') as f:
    content = f.read()

json_match = re.search(r'const SMASH_DATA = ({.*});?\s*$', content, re.DOTALL)
data = json.loads(json_match.group(1))

# ── Remove citations from ALL collections ──────────────────────────────────
for collection in ('top_cited', 'publications', 'curated_studies'):
    for entry in data.get(collection, []):
        entry.pop('citations', None)

# ── Helpers ─────────────────────────────────────────────────────────────────
def blank_hardware(manufacturer=None, model=None, system_type=None,
                   n_traps=None, config=None, wavelength=1064.0,
                   stiffness=None, bead_um=None, bead_mat=None,
                   bead_chem=None, fluor_cap=None, fluor_wl=None,
                   fluor_det=None, n_channels=None):
    return {
        "instrument": {"manufacturer": manufacturer, "model": model, "system_type": system_type},
        "optical_traps": {"number_of_traps": n_traps, "trap_configuration": config,
                          "laser_wavelength_nm": wavelength, "laser_power_mW": None},
        "trap_stiffness": {"value": stiffness, "unit": "pN/nm"},
        "bead": {"diameter_um": bead_um, "material": bead_mat, "surface_chemistry": bead_chem},
        "fluorescence": {"capability": fluor_cap or "confocal",
                         "excitation_wavelengths_nm": fluor_wl or [], "detector_type": fluor_det or "APD"},
        "microfluidics": {"enabled": True if n_channels else None,
                          "number_of_channels": n_channels, "flow_control": "pressure" if n_channels else None}
    }

def ctrap(bead_um=None, bead_chem="streptavidin", n_channels=None,
          stiffness=None, fluor_wl=None, bead_manuf=None):
    hw = blank_hardware(manufacturer="LUMICKS", model="C-Trap", system_type="commercial",
                        n_traps=2, config="dual-trap", bead_um=bead_um,
                        bead_mat="polystyrene", bead_chem=bead_chem,
                        stiffness=stiffness, fluor_wl=fluor_wl, n_channels=n_channels)
    if bead_manuf:
        hw["bead"]["manufacturer"] = bead_manuf
    return hw

def clear_hw():
    """Return blank hardware where data was NOT available."""
    return {
        "instrument": {"manufacturer": None, "model": None, "system_type": None},
        "optical_traps": {"number_of_traps": None, "trap_configuration": None,
                          "laser_wavelength_nm": None, "laser_power_mW": None},
        "trap_stiffness": {"value": None, "unit": "pN/nm"},
        "bead": {"diameter_um": None, "material": None, "surface_chemistry": None},
        "fluorescence": {"capability": None, "excitation_wavelengths_nm": [], "detector_type": None},
        "microfluidics": {"enabled": None, "number_of_channels": None, "flow_control": None}
    }

def clear_cond():
    return {"buffer": {"name": None, "composition": None, "pH": None}, "temperature_C": None}

def clear_meas():
    return {"operation_mode": None,
            "force_range_pN": {"min": None, "max": None},
            "tension_pN": None,
            "fluorescence_imaging": {"enabled": None, "acquisition_mode": None}}

# ═══════════════════════════════════════════════════════════════════════════
# Updates dictionary  (keyed by experiment_id)
# ═══════════════════════════════════════════════════════════════════════════
updates = {

    # ── 01 TOPII-2025-001 (Q-Trap, 4-trap, already done) ──────────────────
    "TOPII-2025-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "Q-Trap", "system_type": "commercial"},
            "optical_traps": {"number_of_traps": 4, "trap_configuration": "quadruple-trap",
                              "laser_wavelength_nm": 1064.0, "laser_power_mW": None},
            "trap_stiffness": {"value": 0.30, "unit": "pN/nm"},
            "bead": {"diameter_um": None, "material": "polystyrene", "surface_chemistry": "streptavidin"},
            "fluorescence": {"capability": "confocal", "excitation_wavelengths_nm": [488, 532, 638],
                             "excitation_powers_mW": [0.2, 5.0, 0.9], "detector_type": "APD",
                             "dyes": ["YOYO-1 (DNA)", "Alexa Fluor 555 (TOP2a)", "ATTO647N (Cohesin/Condensin I)"]},
            "microfluidics": {"enabled": True, "number_of_channels": 6, "flow_control": "pressure"}
        },
        "sample": {"biological_system_type": "DNA-protein", "organism": "Homo sapiens",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "Lambda DNA braids", "length_kb": 48.5,
                                    "topology": "linear", "labeling": "biotinylated at one end of one strand"},
                   "protein": {"name": "Topoisomerase IIa (TOP2a)", "abbreviation": "TOP2a",
                                "expression_system": "", "concentration_nM": 2.0}},
        "experimental_conditions": {
            "buffer": {"name": "Decatenation assay buffer",
                       "composition": "50 mM Tris pH 7.5, 125 mM potassium glutamate, 2.5 mM MgCl2, 0.5 mg/mL BSA",
                       "pH": 7.5, "additives": "1 mM ATP or 1 mM ATPgS"},
            "temperature_C": None},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": 3.0, "max": 45.0}, "tension_pN": 5.0,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"},
                         "data_acquisition_rate_Hz": 1000, "pixel_size_nm": 100},
        "notes": "Q-Trap (quadruple optical trap). Standard assay ~5 pN (3-7 pN). Forces also: 5, 15, 25, 30, 45 pN. FE curves up to 30 pN. Trap stiffness ~0.30 pN/nm. Lambda DNA biotinylated at one end. YOYO-1 0.1 nM. 6-channel microfluidics."
    },

    # ── 02 REMOD-2024-001 (C-Trap, Carcamo 2024) ──────────────────────────
    "REMOD-2024-001": {
        "hardware": ctrap(bead_um=4.38, n_channels=None, bead_manuf="Spherotech"),
        "sample": {"biological_system_type": "chromatin", "organism": "Saccharomyces cerevisiae",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "Lambda DNA with nucleosome arrays",
                                    "length_kb": 48.5, "topology": "linear"},
                   "protein": {"name": "RSC, ISW2, SWR1 chromatin remodelers",
                                "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": {"buffer": {"name": None, "pH": None}, "temperature_C": None},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": None, "max": None}, "tension_pN": 5.0,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}},
        "notes": "LUMICKS C-Trap. SPHERO 4.38 um streptavidin beads (Spherotech, Trap 1). Detailed buffer/concentration not available from accessible text."
    },

    # ── 03 POLII-2025-001 (C-Trap, Wang 2025 Nat Struct Mol Biol) ─────────
    "POLII-2025-001": {
        "hardware": ctrap(bead_um=2.14, stiffness=0.3, n_channels=6),
        "sample": {"biological_system_type": "DNA-protein", "organism": "Homo sapiens",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "Synthetic nucleic acid scaffold (transcription template)",
                                    "length_kb": None, "topology": "linear"},
                   "protein": {"name": "RNA Polymerase II + elongation factors (DSIF, NELF, P-TEFb)",
                                "abbreviation": "Pol II", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": {
            "buffer": {"name": "Transcription assay buffer", "pH": 7.5}, "temperature_C": 25.0},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": None, "max": None}, "tension_pN": 5.0,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}},
        "notes": "LUMICKS C-Trap. 2.14 um streptavidin beads, 6-channel microfluidics. RNA Pol II transcription elongation study. doi: 10.1038/s41594-025-01707-1."
    },

    # ── 04 LEM2-2025-001 (Nature 2025, von Appen) - no full text available
    "LEM2-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": "dsDNA", "name": None, "length_kb": None, "topology": None},
                   "protein": {"name": "LEM2, BAF", "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. Experimental parameters not available. doi not confirmed."
    },

    # ── 05 MEMB-2024-001 (Cell 2024, Yan) - no full text available
    "MEMB-2024-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "cell", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": None, "name": "N/A - live cell tethering", "length_kb": None, "topology": None},
                   "protein": {"name": "Actin cortex", "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. Experimental parameters not available. Membrane tension propagation in live cells study."
    },

    # ── 06 SMCFFM-001 (Liu, Various journal) - conference/demo, no primary paper
    "SMCFFM-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": None, "name": None, "length_kb": None, "topology": None},
                   "protein": {"name": "CMG helicase, PRC2", "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Journal listed as 'Various' - likely conference presentation or LUMICKS showcase. No primary research paper identified; parameters not available."
    },

    # ── 07 FANCD2-2024-001 (C-Trap, Passmore/Rueda 2024) - already done
    "FANCD2-2024-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "C-Trap", "system_type": "commercial"},
            "optical_traps": {"number_of_traps": 2, "trap_configuration": "dual-trap",
                              "laser_wavelength_nm": 1064.0, "laser_power_mW": None},
            "trap_stiffness": {"value": 0.25, "unit": "pN/nm", "notes": "range 0.2-0.3 pN/nm"},
            "bead": {"diameter_um": 4.58, "material": "polystyrene", "surface_chemistry": "streptavidin",
                     "notes": "4.8 um or 4.35 um depending on experiment"},
            "fluorescence": {"capability": "confocal", "excitation_wavelengths_nm": [488, 532, 638],
                             "detector_type": "APD",
                             "dyes": ["eGFP (RPA)", "LD555-CoA/Cy3 (FANCD2-FANCI)", "LD655-CoA/Cy5 (FANCD2-FANCI)"]},
            "microfluidics": {"enabled": True, "number_of_channels": None, "flow_control": "pressure"}
        },
        "sample": {"biological_system_type": "DNA-protein", "organism": "Homo sapiens",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "Lambda DNA with ss-dsDNA junctions",
                                    "length_kb": 48.5, "topology": "linear", "labeling": "biotin-labeled"},
                   "protein": {"name": "FANCD2-FANCI complex (D2-I)", "abbreviation": "D2-I",
                                "expression_system": "", "concentration_nM": 5.0}},
        "experimental_conditions": {
            "buffer": {"name": "Buffer A",
                       "composition": "20 mM HEPES pH 7.5, 75 mM NaCl, 0.5 mg/mL BSA, 1 mM TCEP",
                       "pH": 7.5},
            "temperature_C": 22.0},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": 1.0, "max": 15.0}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}},
        "notes": "C-Trap. Two bead sizes: 4.8 um or 4.35 um. Trap stiffness 0.2-0.3 pN/nm. Loading <1 pN; kymograph at 15 pN. FE curves at 0.2 um/s. eGFP-RPA 800 pM. 22 degrees C."
    },

    # ── 08 ORC-2023-001 (Q-Trap, Dekker 2023) - already done
    "ORC-2023-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "Q-Trap", "system_type": "commercial"},
            "optical_traps": {"number_of_traps": 2, "trap_configuration": "dual-trap",
                              "laser_wavelength_nm": 1064.0, "laser_power_mW": None},
            "trap_stiffness": {"value": 0.3, "unit": "pN/nm"},
            "bead": {"diameter_um": 1.76, "material": "polystyrene", "surface_chemistry": "streptavidin",
                     "manufacturer": "Spherotech"},
            "fluorescence": {"capability": "confocal", "excitation_wavelengths_nm": [488, 638],
                             "excitation_powers_uW": [2, 7], "detector_type": "APD",
                             "dyes": ["AF488 (H2A histones)", "JF646 (ORC, MCM)"]},
            "microfluidics": {"enabled": True, "number_of_channels": None, "flow_control": "pressure"}
        },
        "sample": {"biological_system_type": "chromatin", "organism": "Saccharomyces cerevisiae",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "10.4 kbp DNA with ARS1 origin",
                                    "length_kb": 10.4, "topology": "linear", "labeling": "biotinylated"},
                   "protein": {"name": "ORC (Origin Recognition Complex)", "abbreviation": "ORC",
                                "expression_system": "", "concentration_nM": 5.0}},
        "experimental_conditions": {
            "buffer": {"name": "Reaction Buffer (RB)",
                       "composition": "25 mM HEPES-KOH pH 7.6, 100 mM potassium glutamate, 10 mM magnesium acetate, 100 ug/mL BSA, 1 mM DTT, 0.01% NP-40-S, 10% glycerol, 5 mM ATP",
                       "pH": 7.6, "additives": "2 mM COT, 2 mM NBA, 2 mM TROLOX (photobleaching reducers)"},
            "temperature_C": 30.0},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": 2.0, "max": 40.0}, "tension_pN": 2.0,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}},
        "notes": "LUMICKS Q-Trap. 1.76 um Spherotech beads. DNA at 2 pN. Nucleosome FD: 8-40 pN. ORC 5 nM, Cdc6 10 nM, MCM/Cdt1 80 nM. 30 degrees C. ARS1 vs mutated origin."
    },

    # ── 09 SMC-2023-001 (Aragon, Various) - review/conference
    "SMC-2023-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": None, "name": None, "length_kb": None, "topology": None},
                   "protein": {"name": "Cohesin, Smc5/6, Condensin", "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Journal listed as 'Various' - likely review or conference presentation (Aragon lab). No primary research paper methods available."
    },

    # ── 10 FUS-2022-001 (Banerjee, Various) - conference/talk
    "FUS-2022-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": "dsDNA", "name": "Lambda DNA", "length_kb": 48.5, "topology": "linear"},
                   "protein": {"name": "FUS", "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Journal listed as 'Various' - likely conference talk on FUS/ALS LLPS. No primary research paper methods available."
    },

    # ── 11 ATL-2020-001 (C-Trap, Rill/Tessmer PNAS 2020) ─────────────────
    "ATL-2020-001": {
        "hardware": ctrap(bead_um=4.4, bead_manuf="Spherotech", fluor_wl=[488]),
        "sample": {"biological_system_type": "DNA-protein", "organism": "Arabidopsis thaliana",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "Lambda-phage DNA with alkyl lesions",
                                    "length_kb": 48.502, "topology": "linear", "labeling": "biotinylated at both ends"},
                   "protein": {"name": "MBP-ATL (Alkyltransferase-like protein)",
                                "abbreviation": "ATL", "expression_system": "E. coli", "concentration_nM": 80.0}},
        "experimental_conditions": {
            "buffer": {"name": "ATL incubation buffer",
                       "composition": "25 mM HEPES pH 7.5, 25 mM sodium acetate, 10 mM magnesium acetate, 1x BSA",
                       "pH": 7.5, "additives": "1 mM ATP (for UvrA co-incubation experiments)"},
            "temperature_C": None},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": 5.0, "max": 10.0}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph",
                                                  "dyes": ["QD605-ATL", "QD525-ATL (with UvrA)", "QD705-UvrA"],
                                                  "emission_filters": ["582/75 nm (QD605)", "512/25 nm (QD525)", "700/100 nm (QD705)"]}},
        "notes": "LUMICKS C-Trap. 4.4 um streptavidin Spherotech beads. Lambda-DNA 48502 bp, biotin at both ends. ATL 80 nM (alone) or 2 uM with unlabeled ATL (1:8 QD:unlabeled ratio). UvrA 10 nM. SYTOX Orange for DNA verification. Ambient temperature. doi: 10.1073/pnas.1916860117."
    },

    # ── 12 PAR-2022-001 (Moreno-Herrero, Various) - conference
    "PAR-2022-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": None, "name": None, "length_kb": None, "topology": None},
                   "protein": {"name": "ParB, SMC-ScpAB", "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Journal listed as 'Various' - likely conference presentation (Moreno-Herrero lab, bacterial chromosome organisation). No primary research paper methods available."
    },

    # ── 13 CAS12-2021-001 (C-Trap, Montoya NAR 2021) ─────────────────────
    "CAS12-2021-001": {
        "hardware": ctrap(bead_um=None, n_channels=None),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "Lambda DNA",
                                    "length_kb": 48.5, "topology": "linear"},
                   "protein": {"name": "Cas12a (AsCas12a, LbCas12a, and engineered variants)",
                                "abbreviation": "Cas12a", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": {
            "buffer": {"name": None, "pH": None}, "temperature_C": None},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": 10.0, "max": 50.0}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}},
        "notes": "LUMICKS C-Trap. Lambda DNA 48.5 kbp substrate. Cas12a DNA mechanics study (force-extension and cleavage). doi: 10.1093/nar/gkac348. Detailed bead/buffer data not extracted from full text."
    },

    # ── 14 SMADNE-2023-001 (Van Houten, Various) - webinar
    "SMADNE-2023-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": "Nuclear extract",
                   "nucleic_acid": {"type": "dsDNA", "name": "Lambda DNA (undamaged, nicked, damaged)",
                                    "length_kb": 48.5, "topology": "linear"},
                   "protein": {"name": "OGG1, PARP1, TDG, UV-DDB (from nuclear extracts)",
                                "abbreviation": "", "expression_system": "Nuclear extract", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Journal listed as 'Various' - likely LUMICKS webinar or conference (Van Houten lab, nuclear extract single-molecule studies). No primary research paper methods available."
    },

    # ── 15 RPA-2024-001 (C-Trap, Pangeni/Ha JMB 2024) ────────────────────
    "RPA-2024-001": {
        "hardware": ctrap(bead_um=4.8, bead_manuf="Spherotech"),
        "sample": {"biological_system_type": "DNA-protein", "organism": "Homo sapiens",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "ssDNA", "name": "Lambda ssDNA (from lambda dsDNA)",
                                    "length_kb": 48.5, "topology": "linear"},
                   "protein": {"name": "RPA (Replication Protein A)",
                                "abbreviation": "RPA", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": {
            "buffer": {"name": None, "pH": None}, "temperature_C": None},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": None, "max": None}, "tension_pN": 3.0,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}},
        "notes": "LUMICKS C-Trap. 4.8 um streptavidin Spherotech beads. Lambda ssDNA. RPA intersegmental transfer study. DNA held at ~3 pN. Detailed buffer/concentration data not retrieved."
    },

    # ── 16 RECB-2024-001 (C-Trap G2, Fazio/Lohman JMB 2024) ──────────────
    "RECB-2024-001": {
        "hardware": ctrap(bead_um=4.34, stiffness=None,
                          fluor_wl=None),
        "sample": {"biological_system_type": "DNA-protein", "organism": "Escherichia coli",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "19435 bp dsDNA (blunt/3-biotin end)",
                                    "length_kb": 19.435, "topology": "linear", "labeling": "3-prime biotinylated"},
                   "protein": {"name": "RecBCD (and variants RecBDeltaNucCD, RecBD1080ACD)",
                                "abbreviation": "RecBCD", "expression_system": "E. coli", "concentration_nM": 100.0}},
        "experimental_conditions": {
            "buffer": {"name": "Buffer M30",
                       "composition": "20 mM MOPS-KOH pH 7.0, 5% glycerol, 10 mM MgCl2, 1 mM 2-mercaptoethanol, 30 mM NaCl",
                       "pH": 7.0, "additives": "250 nM Sytox Orange (DNA stain), 2 mM ATP"},
            "temperature_C": 28.0},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": None, "max": None}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph",
                                                  "dyes": ["Sytox Orange (DNA)"]}},
        "notes": "LUMICKS C-Trap G2. 4.34 um streptavidin beads. 19435 bp dsDNA, 3-prime biotinylated. RecBCD 100 nM; E. coli SSB 124 nM when present. 28 degrees C. doi: 10.1016/j.jmb.2023.168365."
    },

    # ── 17 NDF-2025-001 (Custom dual-trap, Li 2025) - already done
    "NDF-2025-001": {
        "hardware": {
            "instrument": {"manufacturer": "Custom-built", "model": "Dual-trap optical tweezers",
                           "system_type": "custom", "notes": "NOT a LUMICKS commercial instrument"},
            "optical_traps": {"number_of_traps": 2, "trap_configuration": "dual-trap",
                              "laser_wavelength_nm": None, "laser_power_mW": None},
            "trap_stiffness": {"value": 0.34, "unit": "pN/nm", "notes": "range 0.28-0.40 pN/nm"},
            "bead": {"diameter_um": 1.0, "material": "polystyrene",
                     "surface_chemistry": "oligo (Pol II assay) / streptavidin (nucleosome unwrapping)"},
            "fluorescence": {"capability": "none", "excitation_wavelengths_nm": [], "detector_type": None},
            "microfluidics": {"enabled": False, "number_of_channels": None, "flow_control": None}
        },
        "sample": {"biological_system_type": "chromatin",
                   "organism": "Homo sapiens / Saccharomyces cerevisiae",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "Nucleosome templates with DNA handles",
                                    "length_kb": None, "topology": "linear"},
                   "protein": {"name": "NDF, FACT, Pol II",
                                "abbreviation": "", "expression_system": "", "concentration_nM": 50.0}},
        "experimental_conditions": {
            "buffer": {"name": "Pulling buffer / TB50",
                       "composition": "20 mM Tris pH 7.5 (8.0 for Pol II), 50 mM KCl, 100 mM NaCl, 5 mM MgCl2, 1 mM DTT, 10 mM NaN3, 0.1 mg/mL BSA",
                       "pH": 7.5, "additives": "0.02% NP-40; 0.5% Pluronic F-127 + 1 mg/mL BSA (passivation)"},
            "temperature_C": None},
        "measurements": {"operation_mode": "passive force-extension",
                         "force_range_pN": {"min": 0.0, "max": None}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": False, "acquisition_mode": None}},
        "notes": "CUSTOM dual-trap (NOT LUMICKS). 1 um polystyrene beads. NDF 50 nM, FACT 50 nM. Pulling rate 20 nm/s. (1) nucleosome mechanical unwrapping; (2) Pol II transcription through nucleosome."
    },

    # ── 18 SHU-2024-001 (C-Trap, Shu/RAD51 2024) - already done
    "SHU-2024-001": {
        "hardware": ctrap(bead_um=4.88, fluor_wl=[488, 561, 638]),
        "sample": {"biological_system_type": "DNA-protein", "organism": "Homo sapiens",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "ssDNA", "name": "Lambda ssDNA", "length_kb": 20.452,
                                    "topology": "linear", "labeling": "biotinylated"},
                   "protein": {"name": "RAD51 (Cy3-labeled)", "abbreviation": "RAD51",
                                "expression_system": "", "concentration_nM": 80.0}},
        "experimental_conditions": {
            "buffer": {"name": "Imaging buffer",
                       "composition": "20 mM Tris pH 7.5, 100 mM NaCl, 2 mM ATP, 5 mM MgCl2, 5 mM CaCl2, 10 mM DTT, 1 mM Trolox-quinone",
                       "pH": 7.5},
            "temperature_C": None},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": 10.0, "max": 25.0}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}},
        "notes": "LUMICKS C-Trap. 4.88 um streptavidin beads. Lambda ssDNA generated by pulling >60 pN. AF488-RPA 10 nM; SWSAP1-SWS1 15 nM. Cy3-RAD51 80 nM."
    },

    # ── 19 POLX-2024-001 (C-Trap, DNA Pol exchange 2024) - already done
    "POLX-2024-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "C-Trap", "system_type": "commercial",
                           "notes": "3-color confocal + dual-trap OT + 5-channel microfluidics"},
            "optical_traps": {"number_of_traps": 2, "trap_configuration": "dual-trap",
                              "laser_wavelength_nm": 1064.0, "laser_power_mW": None},
            "trap_stiffness": {"value": None, "unit": "pN/nm"},
            "bead": {"diameter_um": 1.76, "material": "polystyrene", "surface_chemistry": "streptavidin",
                     "manufacturer": "Spherotech Inc"},
            "fluorescence": {"capability": "confocal", "excitation_wavelengths_nm": [532],
                             "detector_type": "APD",
                             "dyes": ["SNAP-Surface 549 (T7 DNAP, ~60% labeling efficiency)"]},
            "microfluidics": {"enabled": True, "number_of_channels": 5, "flow_control": "pressure"}
        },
        "sample": {"biological_system_type": "DNA-protein",
                   "organism": "Bacteriophage T7 / E. coli",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "pKYB1 replication fork construct",
                                    "length_kb": 8.393, "topology": "linear", "labeling": "biotinylated",
                                    "notes": "25 nt 5-prime overhang mimicking replication fork"},
                   "protein": {"name": "T7 DNA polymerase (SNAP-tagged)", "abbreviation": "T7 DNAP",
                                "expression_system": "", "concentration_nM": 30.0}},
        "experimental_conditions": {
            "buffer": {"name": "Replication buffer",
                       "composition": "20 mM Tris-HCl pH 7.5, 100 mM NaCl, 3 mM MgCl2, 1 mM DTT, 0.02% BSA",
                       "pH": 7.5},
            "temperature_C": None},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": 10.0, "max": 50.0}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}},
        "notes": "LUMICKS C-Trap, 5-channel microfluidics. 1.76 um Spherotech beads. pKYB1 8393 bp fork. T7 DNAP 30 nM + Thioredoxin 2-4x excess. Polymerization: 10-20 pN; Exonuclease: 40-50 pN."
    },

    # ── 20 KINET-2024-001 (Custom trap, JCB 2024) ─────────────────────────
    "KINET-2024-001": {
        "hardware": {
            "instrument": {"manufacturer": "Custom-built",
                           "model": "Laser trap on Nikon TE inverted microscope",
                           "system_type": "custom",
                           "notes": "NOT LUMICKS; Nikon Apo TIRF 100x 1.49 NA objective; JCB not Science"},
            "optical_traps": {"number_of_traps": 1, "trap_configuration": "single-trap",
                              "laser_wavelength_nm": None, "laser_power_mW": None},
            "trap_stiffness": {"value": None, "unit": "pN/nm"},
            "bead": {"diameter_um": None, "material": None, "surface_chemistry": None},
            "fluorescence": {"capability": None, "excitation_wavelengths_nm": [], "detector_type": None},
            "microfluidics": {"enabled": None, "number_of_channels": None, "flow_control": None}
        },
        "sample": {"biological_system_type": "cytoskeleton", "organism": None,
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": None, "name": "N/A - microtubules", "length_kb": None, "topology": None},
                   "protein": {"name": "Ndc80, DAM1 (kinetochore proteins)",
                                "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": None, "max": None}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": None, "acquisition_mode": None}},
        "notes": "Custom laser trap (NOT LUMICKS). Built on Nikon TE inverted microscope with Nikon Apo TIRF 100x 1.49 NA objective. Kinetochore-microtubule grip asymmetry study. Published in JCB 2024 (not Science as listed). doi: 10.1083/jcb.202405176. Detailed bead/buffer not extracted."
    },

    # ── 21 HELQ-2023-001 - review article (Molecular Cell 2023)
    "HELQ-2023-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": None, "name": None, "length_kb": None, "topology": None},
                   "protein": {"name": "HELQ, RAD51, RPA", "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Review article - summarises HELQ helicase function in DSB repair across multiple studies. No specific experimental parameters. PMC: 11355030."
    },

    # ── 22 TF-2025-001 (C-Trap, PNAS 2025, Trigger Factor)  ───────────────
    "TF-2025-001": {
        "hardware": ctrap(bead_um=2.1, bead_chem="anti-digoxigenin", bead_manuf="Spherotech",
                          n_channels=None),
        "sample": {"biological_system_type": "protein", "organism": "Escherichia coli",
                   "preparation_method": "Ribosome-tethered nascent chains",
                   "nucleic_acid": {"type": None, "name": "N/A - protein folding study", "length_kb": None, "topology": None},
                   "protein": {"name": "Trigger Factor (TF), DHFR, nascent chains",
                                "abbreviation": "TF", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": {
            "buffer": {"name": None, "pH": None}, "temperature_C": None},
        "measurements": {"operation_mode": "force-extension",
                         "force_range_pN": {"min": None, "max": None}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": None, "acquisition_mode": None}},
        "notes": "LUMICKS C-Trap. 2.1 um carboxyl polystyrene Spherotech beads (CP-20-10), coupled with anti-digoxigenin antibody. Protein folding/compaction study: nascent chain emerging from ribosome. doi: 10.1073/pnas.2422678122."
    },

    # ── 23 CELL-2025-001 (Biophysical Reports 2025) - no full text
    "CELL-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "cell", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": None, "name": "N/A - live cells", "length_kb": None, "topology": None},
                   "protein": {"name": "N/A", "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. Robust quantification of cellular mechanics study. Parameters not available."
    },

    # ── 24 CRISPR-2025-001 (NAR 2025, Klein) - no full text
    "CRISPR-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": "dsDNA", "name": None, "length_kb": None, "topology": None},
                   "protein": {"name": "Type I-Fv and Type IV-A1 CRISPR-Cas effectors",
                                "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. Type I-Fv and engineered type IV-A1 CRISPR-Cas study. Parameters not available."
    },

    # ── 25 PARP1-2025-001 (C-Trap, Schaich Nature Comms 2025) ─────────────
    "PARP1-2025-001": {
        "hardware": ctrap(bead_um=4.5),
        "sample": {"biological_system_type": "chromatin", "organism": "Homo sapiens",
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": "dsDNA", "name": "Lambda DNA with reconstituted nucleosomes",
                                    "length_kb": 48.5, "topology": "linear"},
                   "protein": {"name": "PARP1 (fluorescently labeled)",
                                "abbreviation": "PARP1", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": {
            "buffer": {"name": None, "pH": None}, "temperature_C": None},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": None, "max": None}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}},
        "notes": "LUMICKS C-Trap. 4.5 um streptavidin beads (lambda-DNA experiments); 1.5-1.7 um beads (chromatin fiber experiments). Nucleosome unwrapping + PARP1 allostery. doi: 10.1038/s41467-025-67071-2."
    },

    # ── 26 HSV-2025-001 (Cell 2025, Yu) - no full text
    "HSV-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": "Herpes Simplex Virus 1",
                   "preparation_method": None,
                   "nucleic_acid": {"type": "dsDNA", "name": None, "length_kb": None, "topology": None},
                   "protein": {"name": "HSV-1 helicase-primase (UL5/UL8/UL52)",
                                "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. HSV-1 helicase-primase inhibition and replication fork complex assembly. Parameters not available."
    },

    # ── 27 LIG3-2025-001 (Nature Comms 2025, Nagpal) - no full text
    "LIG3-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "chromatin", "organism": "Homo sapiens",
                   "preparation_method": None,
                   "nucleic_acid": {"type": "dsDNA", "name": "Nucleosomal DNA", "length_kb": None, "topology": None},
                   "protein": {"name": "DNA ligase 3 alpha (LIG3a)",
                                "abbreviation": "LIG3a", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. Zinc finger of LIG3a - nucleosome binding via arginine anchor. Parameters not available."
    },

    # ── 28 H4K16-2025-001 (Molecular Cell 2025, Nitsch) - no full text
    "H4K16-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "chromatin", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": None, "name": "Chromatin fibers", "length_kb": None, "topology": None},
                   "protein": {"name": "Histones (H4K16 acylation variants)",
                                "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. H4K16 acylations chromatin architecture and transcriptional response. Parameters not available."
    },

    # ── 29 NAPA-2025-001 (JMB 2025, Schumacher) - no full text
    "NAPA-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein",
                   "organism": "Mycobacterium tuberculosis",
                   "preparation_method": None,
                   "nucleic_acid": {"type": "dsDNA", "name": None, "length_kb": None, "topology": None},
                   "protein": {"name": "NapA (nucleoid-associated protein)",
                                "abbreviation": "NapA", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. M. tuberculosis NapA DNA bridging mechanism. Parameters not available."
    },

    # ── 30 KIN-2025-001 (Biophysical Journal 2025, Bensel) - no full text
    "KIN-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "motor-protein", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": None, "name": "N/A - microtubules", "length_kb": None, "topology": None},
                   "protein": {"name": "Kinesin-1",
                                "abbreviation": "KIF5B", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": 5.0, "max": 8.0}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": None, "acquisition_mode": None}},
        "notes": "Full text not accessible. Kinesin-1 autoinhibition and cargo transport ensemble mechanics. Stall force ~5-8 pN. Detailed parameters not available."
    },

    # ── 31 COND-2025-001 (Nature Comms 2025, Tsubota) - no full text
    "COND-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": "dsDNA", "name": None, "length_kb": None, "topology": None},
                   "protein": {"name": "Condensin I, Topoisomerase IIa",
                                "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. Condensin I / TopIIa interplay in single-molecule DNA compaction. Parameters not available."
    },

    # ── 32 GPMV-2025-001 (Biophysical Journal 2025, Yosibash) - no full text
    "GPMV-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "membrane", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": None, "name": "N/A - membranes/vesicles", "length_kb": None, "topology": None},
                   "protein": {"name": "Membrane receptors",
                                "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. GPMV imaging platform for receptor binding and membrane fusion. Parameters not available."
    },

    # ── 33 ELONG-2025-001 (Cell 2025, Planelles-Herrero) - no full text
    "ELONG-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "cytoskeleton", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": None, "name": "N/A - microtubules", "length_kb": None, "topology": None},
                   "protein": {"name": "Elongator complex, polyglutamylated tubulin",
                                "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. Elongator as microtubule polymerase selective for polyglutamylated tubulin. Parameters not available."
    },

    # ── 34 LABEL-2025-001 (C-Trap, Silbermann Protein Science 2025) ────────
    "LABEL-2025-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "C-Trap", "system_type": "commercial"},
            "optical_traps": {"number_of_traps": 2, "trap_configuration": "dual-trap",
                              "laser_wavelength_nm": 1064.0, "laser_power_mW": None},
            "trap_stiffness": {"value": None, "unit": "pN/nm"},
            "bead": {"diameter_um_trap1": 0.75, "diameter_um_trap2": 1.36,
                     "material": "polystyrene",
                     "surface_chemistry_trap1": "anti-digoxigenin",
                     "surface_chemistry_trap2": "streptavidin"},
            "fluorescence": {"capability": "confocal", "excitation_wavelengths_nm": [], "detector_type": "APD"},
            "microfluidics": {"enabled": True, "number_of_channels": None, "flow_control": "pressure"}
        },
        "sample": {"biological_system_type": "protein", "organism": None,
                   "preparation_method": "Recombinant expression",
                   "nucleic_acid": {"type": None, "name": "N/A - protein labeling methodology",
                                    "length_kb": None, "topology": None},
                   "protein": {"name": "Hsp90 (homodimer, proof-of-concept protein)",
                                "abbreviation": "Hsp90", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": {
            "buffer": {"name": None, "pH": None}, "temperature_C": None},
        "measurements": {"operation_mode": "force-extension",
                         "force_range_pN": {"min": None, "max": None}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": True, "acquisition_mode": None}},
        "notes": "LUMICKS C-Trap. Dual-tether approach: 0.75 um anti-digoxigenin (Trap 1) + 1.36 um streptavidin (Trap 2). One-pot dual protein labeling for simultaneous mechanical + fluorescent readout. PMC: 11915586."
    },

    # ── 35 GQUAD-2025-001 (Angewandte Chemie 2025, Bao) - no full text
    "GQUAD-2025-001": {
        "hardware": clear_hw(),
        "sample": {"biological_system_type": "DNA-protein", "organism": None,
                   "preparation_method": None,
                   "nucleic_acid": {"type": "dsDNA", "name": "G-quadruplex / i-Motif DNA duplex",
                                    "length_kb": None, "topology": None},
                   "protein": {"name": "PCBP2, replisome components",
                                "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": clear_cond(),
        "measurements": clear_meas(),
        "notes": "Full text not accessible. G-quadruplex and i-motif coexistence in DNA duplex with PCBP2-assisted replisome. Parameters not available."
    },

    # ── 36 MOTOR-2021-001 - review article
    "MOTOR-2021-001": {
        "hardware": {
            "instrument": {"manufacturer": "Various (review covers multiple setups)",
                           "model": None, "system_type": "custom"},
            "optical_traps": {"number_of_traps": None, "trap_configuration": None,
                              "laser_wavelength_nm": 1064.0, "laser_power_mW": None},
            "trap_stiffness": {"value": None, "unit": "pN/nm"},
            "bead": {"diameter_um": None, "material": None, "surface_chemistry": "streptavidin"},
            "fluorescence": {"capability": None, "excitation_wavelengths_nm": [], "detector_type": None},
            "microfluidics": {"enabled": None, "number_of_channels": None, "flow_control": None}
        },
        "sample": {"biological_system_type": "cytoskeleton",
                   "organism": "Bos taurus (bovine brain tubulin)",
                   "preparation_method": "In vitro reconstitution",
                   "nucleic_acid": {"type": None, "name": "N/A - microtubule bundles", "length_kb": None, "topology": None},
                   "protein": {"name": "Kinesin-5 (Eg5), Kinesin-1, Dynein, PRC1, Ase1, NuMA",
                                "abbreviation": "", "expression_system": "", "concentration_nM": None}},
        "experimental_conditions": {
            "buffer": {"name": "BRB80",
                       "composition": "80 mM PIPES, 1 mM MgCl2, 1 mM EGTA, pH 6.8",
                       "pH": 6.8, "additives": "1 mM ATP, 10 uM Taxol (stabilization), 25 mM glucose (oxygen scavenger)"},
            "temperature_C": 25.0},
        "measurements": {"operation_mode": "force-clamp",
                         "force_range_pN": {"min": None, "max": None}, "tension_pN": None,
                         "fluorescence_imaging": {"enabled": None, "acquisition_mode": None}},
        "notes": "Review article: multiple custom OT setups across reviewed studies. Kinesin-5 stall force ~5 pN (single motor). doi: 10.1002/cm.21678."
    },
}

# ── Apply all updates ────────────────────────────────────────────────────────
for study in data.get('curated_studies', []):
    sid = study.get('id', '')
    study.pop('citations', None)  # always remove
    if sid in updates:
        u = updates[sid]
        for k, v in u.items():
            study[k] = v
        print("Updated: " + sid)
    else:
        print("No update entry: " + sid)

# ── Write back ───────────────────────────────────────────────────────────────
json_output = json.dumps(data, indent=2, ensure_ascii=False)
total = data['statistics']['total_publications']
new_content = ("// SMASH-BIO Complete Data\n"
               "// Biophysics-focused publications from extracted_metadata and publications_metadata\n"
               "// Total: " + str(total) + " entries\n"
               "// Note: Citation counts removed. Experimental parameters updated 2026-03-15.\n\n"
               "const SMASH_DATA = " + json_output + ";\n")

with open('website/js/data.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done! All 36 curated studies processed.")
