"""
Script to update website/js/data.js:
1. Remove citation counts from all entries
2. Update curated studies with experimentally extracted parameters
"""

import json
import re

# Read the data.js file
with open('website/js/data.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract the JSON part from the JS file
json_match = re.search(r'const SMASH_DATA = ({.*});?\s*$', content, re.DOTALL)
if not json_match:
    print("ERROR: Could not find SMASH_DATA in data.js")
    exit(1)

json_str = json_match.group(1)
data = json.loads(json_str)

# ────────────────────────────────────────────────────────────────────────────
# 1. Remove citations from top_cited entries
# ────────────────────────────────────────────────────────────────────────────
for entry in data.get('top_cited', []):
    entry.pop('citations', None)

# ────────────────────────────────────────────────────────────────────────────
# 2. Remove citations from all publications entries
# ────────────────────────────────────────────────────────────────────────────
for entry in data.get('publications', []):
    entry.pop('citations', None)

# ────────────────────────────────────────────────────────────────────────────
# 3. Remove citations from curated_studies and update with extracted params
# ────────────────────────────────────────────────────────────────────────────

# Extracted parameter updates by study ID
updates = {

    # ── Study 01: TopII decatenation (Cutts 2025) ──────────────────────────
    "TOPII-2025-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "Q-Trap", "system_type": "commercial"},
            "optical_traps": {
                "number_of_traps": 4,
                "trap_configuration": "quadruple-trap",
                "laser_wavelength_nm": 1064.0,
                "laser_power_mW": None
            },
            "trap_stiffness": {"value": 0.30, "unit": "pN/nm"},
            "bead": {"diameter_um": None, "material": "polystyrene", "surface_chemistry": "streptavidin"},
            "fluorescence": {
                "capability": "confocal",
                "excitation_wavelengths_nm": [488, 532, 638],
                "excitation_powers_mW": [0.2, 5.0, 0.9],
                "detector_type": "APD",
                "dyes": ["YOYO-1 (DNA)", "Alexa Fluor 555 (TOP2α)", "ATTO647N (Cohesin/Condensin I)"]
            },
            "microfluidics": {"enabled": True, "number_of_channels": 6, "flow_control": "pressure"}
        },
        "sample": {
            "biological_system_type": "DNA-protein",
            "organism": "Homo sapiens",
            "preparation_method": "Recombinant expression",
            "nucleic_acid": {
                "type": "dsDNA",
                "name": "Lambda DNA braids",
                "length_kb": 48.5,
                "topology": "linear",
                "labeling": "biotinylated at one end of one strand"
            },
            "protein": {
                "name": "Topoisomerase IIα (TOP2α)",
                "abbreviation": "TOP2α",
                "expression_system": "",
                "concentration_nM": 2.0
            }
        },
        "experimental_conditions": {
            "buffer": {
                "name": "Decatenation assay buffer",
                "composition": "50 mM Tris pH 7.5, 125 mM potassium glutamate, 2.5 mM MgCl2, 0.5 mg/mL BSA",
                "pH": 7.5,
                "additives": "1 mM ATP or 1 mM ATPγS"
            },
            "temperature_C": None
        },
        "measurements": {
            "operation_mode": "force-clamp",
            "force_range_pN": {"min": 3.0, "max": 45.0},
            "tension_pN": 5.0,
            "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"},
            "data_acquisition_rate_Hz": 1000,
            "pixel_size_nm": 100
        },
        "notes": "Q-Trap (quadruple optical trap). Standard assay: mean ~5 pN (3-7 pN). Higher forces: 5, 15, 25, 30, 45 pN. FE curves up to 30 pN. Trap 1&2 stiffness ~0.30 pN/nm. Lambda DNA biotinylated at one end. YOYO-1 0.1 nM for DNA imaging."
    },

    # ── Study 02: Chromatin remodelers (Carcamo 2024) ──────────────────────
    "REMOD-2024-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "C-Trap", "system_type": "commercial"},
            "optical_traps": {
                "number_of_traps": 2,
                "trap_configuration": "dual-trap",
                "laser_wavelength_nm": 1064.0,
                "laser_power_mW": None
            },
            "trap_stiffness": {"value": None, "unit": "pN/nm"},
            "bead": {"diameter_um": 4.38, "material": "polystyrene", "surface_chemistry": "streptavidin",
                     "manufacturer": "Spherotech"},
            "fluorescence": {
                "capability": "confocal",
                "excitation_wavelengths_nm": [],
                "detector_type": "APD"
            },
            "microfluidics": {"enabled": True, "number_of_channels": None, "flow_control": "pressure"}
        },
        "sample": {
            "biological_system_type": "chromatin",
            "organism": "Saccharomyces cerevisiae",
            "preparation_method": "Recombinant expression",
            "nucleic_acid": {
                "type": "dsDNA",
                "name": "Lambda DNA with nucleosome arrays",
                "length_kb": 48.5,
                "topology": "linear"
            },
            "protein": {
                "name": "RSC, ISW2, SWR1 chromatin remodelers",
                "abbreviation": "",
                "expression_system": "",
                "concentration_nM": None
            }
        },
        "experimental_conditions": {
            "buffer": {"name": "", "pH": None},
            "temperature_C": None
        },
        "measurements": {
            "operation_mode": "force-clamp",
            "force_range_pN": {"min": None, "max": None},
            "tension_pN": 5.0,
            "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}
        },
        "notes": "LUMICKS C-Trap. SPHERO 4.38 µm streptavidin beads (Spherotech), Trap 1. Full buffer/concentration details not available."
    },

    # ── Study 07: FANCD2-FANCI (Rueda/Passmore 2024) ───────────────────────
    "FANCD2-2024-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "C-Trap", "system_type": "commercial"},
            "optical_traps": {
                "number_of_traps": 2,
                "trap_configuration": "dual-trap",
                "laser_wavelength_nm": 1064.0,
                "laser_power_mW": None
            },
            "trap_stiffness": {"value": 0.25, "unit": "pN/nm",
                               "notes": "range 0.2–0.3 pN/nm"},
            "bead": {"diameter_um": 4.58, "material": "polystyrene", "surface_chemistry": "streptavidin",
                     "notes": "4.8 µm or 4.35 µm depending on experiment"},
            "fluorescence": {
                "capability": "confocal",
                "excitation_wavelengths_nm": [488, 532, 638],
                "detector_type": "APD",
                "dyes": ["eGFP (RPA)", "LD555-CoA/Cy3 (FANCD2-FANCI)", "LD655-CoA/Cy5 (FANCD2-FANCI)"]
            },
            "microfluidics": {"enabled": True, "number_of_channels": None, "flow_control": "pressure"}
        },
        "sample": {
            "biological_system_type": "DNA-protein",
            "organism": "Homo sapiens",
            "preparation_method": "Recombinant expression",
            "nucleic_acid": {
                "type": "dsDNA",
                "name": "Lambda DNA with ss-dsDNA junctions",
                "length_kb": 48.5,
                "topology": "linear",
                "labeling": "biotin-labeled",
                "variants": "Lambda 48.5 kbp; Lambda with 17.8 knt ssDNA gap; 15 kb four-way junction DNA"
            },
            "protein": {
                "name": "FANCD2-FANCI complex (D2-I)",
                "abbreviation": "D2-I",
                "expression_system": "",
                "concentration_nM": 5.0
            }
        },
        "experimental_conditions": {
            "buffer": {
                "name": "Buffer A",
                "composition": "20 mM HEPES pH 7.5, 75 mM NaCl, 0.5 mg/mL BSA, 1 mM TCEP",
                "pH": 7.5
            },
            "temperature_C": 22.0
        },
        "measurements": {
            "operation_mode": "force-clamp",
            "force_range_pN": {"min": 1.0, "max": 15.0},
            "tension_pN": None,
            "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}
        },
        "notes": "Two bead sizes: 4.8 µm or 4.35 µm. Trap stiffness 0.2–0.3 pN/nm. Loading at <1 pN; kymograph at 15 pN. FE curves at 0.2 µm/s pulling rate. eGFP-RPA at 800 pM."
    },

    # ── Study 08: ORC/MCM (Dekker 2023) ────────────────────────────────────
    "ORC-2023-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "Q-Trap", "system_type": "commercial"},
            "optical_traps": {
                "number_of_traps": 2,
                "trap_configuration": "dual-trap",
                "laser_wavelength_nm": 1064.0,
                "laser_power_mW": None
            },
            "trap_stiffness": {"value": 0.3, "unit": "pN/nm"},
            "bead": {"diameter_um": 1.76, "material": "polystyrene", "surface_chemistry": "streptavidin",
                     "manufacturer": "Spherotech"},
            "fluorescence": {
                "capability": "confocal",
                "excitation_wavelengths_nm": [488, 638],
                "excitation_powers_uW": [2, 7],
                "detector_type": "APD",
                "dyes": ["AF488 (H2A histones)", "JF646 (ORC, MCM)"]
            },
            "microfluidics": {"enabled": True, "number_of_channels": None, "flow_control": "pressure"}
        },
        "sample": {
            "biological_system_type": "chromatin",
            "organism": "Saccharomyces cerevisiae",
            "preparation_method": "Recombinant expression",
            "nucleic_acid": {
                "type": "dsDNA",
                "name": "10.4 kbp DNA with ARS1 origin",
                "length_kb": 10.4,
                "topology": "linear",
                "labeling": "biotinylated"
            },
            "protein": {
                "name": "ORC (Origin Recognition Complex)",
                "abbreviation": "ORC",
                "expression_system": "",
                "concentration_nM": 5.0
            }
        },
        "experimental_conditions": {
            "buffer": {
                "name": "Reaction Buffer (RB)",
                "composition": "25 mM HEPES-KOH pH 7.6, 100 mM potassium glutamate, 10 mM magnesium acetate, 100 µg/mL BSA, 1 mM DTT, 0.01% NP-40-S, 10% glycerol, 5 mM ATP",
                "pH": 7.6,
                "additives": "Photobleaching reducers: 2 mM COT, 2 mM NBA, 2 mM TROLOX"
            },
            "temperature_C": 30.0
        },
        "measurements": {
            "operation_mode": "force-clamp",
            "force_range_pN": {"min": 2.0, "max": 40.0},
            "tension_pN": 2.0,
            "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}
        },
        "notes": "LUMICKS Q-Trap (hybrid OT + confocal). 1.76 µm streptavidin beads (Spherotech). DNA held at 2 pN for fluorescence. Nucleosome unwrapping FD curves: 8-40 pN. MCM/Cdt1 80 nM; Cdc6 10 nM. ARS1 vs mutated origin compared."
    },

    # ── Study 17: NDF-FACT (Li 2025) ────────────────────────────────────────
    "NDF-2025-001": {
        "hardware": {
            "instrument": {"manufacturer": "Custom-built", "model": "Dual-trap optical tweezers",
                           "system_type": "custom",
                           "notes": "NOT a LUMICKS commercial instrument"},
            "optical_traps": {
                "number_of_traps": 2,
                "trap_configuration": "dual-trap",
                "laser_wavelength_nm": None,
                "laser_power_mW": None
            },
            "trap_stiffness": {"value": 0.34, "unit": "pN/nm", "notes": "range 0.28–0.40 pN/nm"},
            "bead": {"diameter_um": 1.0, "material": "polystyrene",
                     "surface_chemistry": "oligo (Pol II assay) / streptavidin (nucleosome unwrapping)"},
            "fluorescence": {
                "capability": "none",
                "excitation_wavelengths_nm": [],
                "detector_type": ""
            },
            "microfluidics": {"enabled": False, "number_of_channels": None, "flow_control": ""}
        },
        "sample": {
            "biological_system_type": "chromatin",
            "organism": "Homo sapiens / Saccharomyces cerevisiae",
            "preparation_method": "Recombinant expression",
            "nucleic_acid": {
                "type": "dsDNA",
                "name": "Nucleosome/chromatin templates with DNA handles",
                "length_kb": None,
                "topology": "linear",
                "notes": "Nucleosome unwrapping: 570 bp + 700 bp handles; Pol II assay: 2 kb + 845 bp ruler + 601 NPS + 1.5 kb biotin handles"
            },
            "protein": {
                "name": "NDF, FACT, Pol II",
                "abbreviation": "",
                "expression_system": "",
                "concentration_nM": 50.0
            }
        },
        "experimental_conditions": {
            "buffer": {
                "name": "Pulling buffer / TB50",
                "composition": "20 mM Tris pH 7.5 (or 8.0 for Pol II), 50 mM KCl, 100 mM NaCl, 5 mM MgCl2, 1 mM DTT, 10 mM NaN3, 0.1 mg/mL BSA",
                "pH": 7.5,
                "additives": "0.02% NP-40; passivation with 0.5% Pluronic F-127 + 1 mg/mL BSA; 0.5 mM each NTP for Pol II assay"
            },
            "temperature_C": None
        },
        "measurements": {
            "operation_mode": "passive force-extension",
            "force_range_pN": {"min": 0.0, "max": None},
            "tension_pN": None,
            "fluorescence_imaging": {"enabled": False, "acquisition_mode": ""}
        },
        "notes": "CUSTOM dual-trap instrument (not LUMICKS). 1 µm polystyrene beads. NDF 50 nM, FACT 50 nM. Pulling rate: 20 nm/s. Two assays: (1) nucleosome mechanical unwrapping, (2) Pol II transcription through nucleosome."
    },

    # ── Study 18: Shu complex / RAD51 (2024) ───────────────────────────────
    "SHU-2024-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "C-Trap", "system_type": "commercial"},
            "optical_traps": {
                "number_of_traps": 2,
                "trap_configuration": "dual-trap",
                "laser_wavelength_nm": 1064.0,
                "laser_power_mW": None
            },
            "trap_stiffness": {"value": None, "unit": "pN/nm"},
            "bead": {"diameter_um": 4.88, "material": "polystyrene", "surface_chemistry": "streptavidin"},
            "fluorescence": {
                "capability": "confocal",
                "excitation_wavelengths_nm": [488, 561, 638],
                "emission_filters_nm": ["500-550", "575-625", "650-750"],
                "detector_type": "APD",
                "dyes": ["Cy3 (RAD51, N-terminal)", "AF488 (RPA)", "JF503 (HaloTag-SWSAP1)"]
            },
            "microfluidics": {"enabled": True, "number_of_channels": None, "flow_control": "pressure"}
        },
        "sample": {
            "biological_system_type": "DNA-protein",
            "organism": "Homo sapiens",
            "preparation_method": "Recombinant expression",
            "nucleic_acid": {
                "type": "ssDNA",
                "name": "Lambda ssDNA (from biotinylated lambda dsDNA)",
                "length_kb": 20.452,
                "topology": "linear",
                "labeling": "biotinylated lambda dsDNA converted to ssDNA"
            },
            "protein": {
                "name": "RAD51 (Cy3-labeled)",
                "abbreviation": "RAD51",
                "expression_system": "",
                "concentration_nM": 80.0
            }
        },
        "experimental_conditions": {
            "buffer": {
                "name": "Imaging buffer",
                "composition": "20 mM Tris pH 7.5, 100 mM NaCl, 2 mM ATP, 5 mM MgCl2, 5 mM CaCl2, 10 mM DTT, 1 mM Trolox-quinone",
                "pH": 7.5
            },
            "temperature_C": None
        },
        "measurements": {
            "operation_mode": "force-clamp",
            "force_range_pN": {"min": 10.0, "max": 25.0},
            "tension_pN": None,
            "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}
        },
        "notes": "LUMICKS C-Trap. 4.88 µm streptavidin beads. Lambda ssDNA generated by pulling >60 pN. 10 pN for ssDNA generation/RPA visualization; 25 pN for RPA at higher tension. AF488-RPA 10 nM; SWSAP1-SWS1 15 nM."
    },

    # ── Study 19: DNA Pol exchange (2024) ───────────────────────────────────
    "POLX-2024-001": {
        "hardware": {
            "instrument": {"manufacturer": "LUMICKS", "model": "C-Trap", "system_type": "commercial",
                           "notes": "3-color confocal + dual-trap OT + 5-channel microfluidics"},
            "optical_traps": {
                "number_of_traps": 2,
                "trap_configuration": "dual-trap",
                "laser_wavelength_nm": 1064.0,
                "laser_power_mW": None
            },
            "trap_stiffness": {"value": None, "unit": "pN/nm"},
            "bead": {"diameter_um": 1.76, "material": "polystyrene", "surface_chemistry": "streptavidin",
                     "manufacturer": "Spherotech Inc"},
            "fluorescence": {
                "capability": "confocal",
                "excitation_wavelengths_nm": [532],
                "detector_type": "APD",
                "dyes": ["SNAP-Surface 549 (T7 DNAP, ~60% labeling efficiency)"]
            },
            "microfluidics": {"enabled": True, "number_of_channels": 5, "flow_control": "pressure"}
        },
        "sample": {
            "biological_system_type": "DNA-protein",
            "organism": "Bacteriophage T7 / E. coli",
            "preparation_method": "Recombinant expression",
            "nucleic_acid": {
                "type": "dsDNA",
                "name": "pKYB1 replication fork DNA construct",
                "length_kb": 8.393,
                "topology": "linear",
                "labeling": "biotinylated",
                "notes": "25 nt 5'-end overhang mimicking replication fork"
            },
            "protein": {
                "name": "T7 DNA polymerase (SNAP-tagged)",
                "abbreviation": "T7 DNAP",
                "expression_system": "",
                "concentration_nM": 30.0
            }
        },
        "experimental_conditions": {
            "buffer": {
                "name": "Replication buffer",
                "composition": "20 mM Tris-HCl pH 7.5, 100 mM NaCl, 3 mM MgCl2, 1 mM DTT, 0.02% BSA",
                "pH": 7.5
            },
            "temperature_C": None
        },
        "measurements": {
            "operation_mode": "force-clamp",
            "force_range_pN": {"min": 10.0, "max": 50.0},
            "tension_pN": None,
            "fluorescence_imaging": {"enabled": True, "acquisition_mode": "kymograph"}
        },
        "notes": "LUMICKS C-Trap with 5-channel microfluidics. 1.76 µm streptavidin beads (Spherotech). pKYB1 8393 bp replication fork construct. T7 DNAP 30 nM + Thioredoxin (2-4× excess). Polymerization: 10-20 pN; Exonuclease: 40-50 pN."
    }
}


# Apply updates to curated studies
for study in data.get('curated_studies', []):
    study_id = study.get('id', '')
    
    # Remove citations from all curated studies
    study.pop('citations', None)
    
    # Apply extracted parameter updates
    if study_id in updates:
        u = updates[study_id]
        if 'hardware' in u:
            study['hardware'] = u['hardware']
        if 'sample' in u:
            study['sample'] = u['sample']
        if 'experimental_conditions' in u:
            study['experimental_conditions'] = u['experimental_conditions']
        if 'measurements' in u:
            study['measurements'] = u['measurements']
        if 'notes' in u:
            study['notes'] = u['notes']
        print("  Updated: " + study_id)
    else:
        print("  No update: " + study_id)

# Serialize back to JS
json_output = json.dumps(data, indent=2, ensure_ascii=False)

total = data['statistics']['total_publications']
new_content = ("// SMASH-BIO Complete Data\n"
               "// Biophysics-focused publications from extracted_metadata and publications_metadata\n"
               "// Total: " + str(total) + " entries\n"
               "// Note: Citation counts removed (unreliable). Experimental parameters updated 2026-03-15.\n\n"
               "const SMASH_DATA = " + json_output + ";\n")

with open('website/js/data.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("data.js updated successfully!")
print("Citations removed from all entries")
print(str(len(updates)) + " curated studies updated with extracted parameters")
