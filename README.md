# SMASH-BIO: Single-Molecule Analysis Standardized Hierarchy for Biophysical Observations

A comprehensive metadata framework for standardizing optical tweezers biological measurements based on the metadata standards proposed in Table 3 of the Biophysical Journal article on optical tweezers metadata.

## Overview

This repository contains a complete metadata system for documenting optical tweezers experiments on biological systems, including:

- **207 optical tweezers publications** from Table S6 with structured YAML metadata (DOI-based)
- **35 curated LUMICKS C-Trap publications** (2020-2025) with detailed structured YAML metadata
- **JSON Schema** for metadata validation
- **Python utilities** for metadata processing
- **YAML templates** for creating new metadata entries

## Repository Structure

```
SMASH-BIO/
├── README.md                           # This file
├── LUMICKS_Publications_Metadata.md    # Detailed publication summaries
├── Optical_Tweezers_Biological_Measurements_Metadata.md  # Comprehensive metadata guide
├── optical_tweezers_metadata_schema.json   # JSON Schema for validation
├── optical_tweezers_metadata_template.yaml # Blank template for new entries
├── optical_tweezers_metadata.py        # Python utilities
├── example_FANCD2_DNA_scanning.yaml    # Detailed example metadata
├── generate_metadata_files.py          # Script for LUMICKS publications
├── generate_all_metadata.py            # Script for all DOI-based publications
├── OT_experiments-dois.csv             # Source DOIs (207 publications)
├── publications_metadata/              # LUMICKS curated publications (35 files)
│   ├── _index.yaml
│   ├── study_01_TopII_decatenation_Cutts_2025.yaml
│   └── ... (35 study files)
└── doi_metadata/                       # All DOI-based publications (207 files)
    ├── _index.yaml                     # Comprehensive index with statistics
    ├── ot_0001_10.1063_5.0060276.yaml
    └── ... (207 YAML files)
```

## Metadata Categories

The metadata framework captures six major categories based on the Biophysical Journal Table 3 standards:

### 1. Hardware Specifications
- Instrument manufacturer and model
- Optical trap configuration (dual/quadruple)
- Laser wavelength and power
- Trap stiffness calibration
- Bead properties
- Fluorescence detection capabilities
- Microfluidics system

### 2. Sample Information
- Biological system type (DNA-protein, chromatin, cell, etc.)
- Source organism and preparation method
- Nucleic acid details (type, length, topology)
- Protein information (expression system, concentration)

### 3. Experimental Conditions
- Buffer composition and pH
- Temperature
- Ionic strength
- Additives (ATP, oxygen scavenging systems)

### 4. Measurement Parameters
- Operation mode (force-clamp, force-extension, etc.)
- Force range and tension settings
- Data acquisition rates
- Fluorescence imaging parameters

### 5. Results and Key Findings
- Primary measurements recorded
- Derived quantities (binding rates, diffusion coefficients)
- Key scientific findings

### 6. Data Availability
- Repository links (Zenodo, GitHub, etc.)
- File formats
- Data processing software

## DOI Metadata Statistics (207 Publications)

| System Type | Count |
|-------------|-------|
| molecular-physics | 84 |
| biophysics | 65 |
| DNA-protein | 22 |
| DNA | 15 |
| biomolecule-force | 11 |
| force-spectroscopy | 10 |

### By Research Category
| Category | Count |
|----------|-------|
| biophysics | 98 |
| molecular-physics | 95 |
| DNA | 37 |
| force-spectroscopy | 26 |

### Top Journals
| Journal | Count |
|---------|-------|
| Biophysical Journal | 16 |
| PNAS | 11 |
| Scientific Reports | 11 |
| Journal of Visualized Experiments | 11 |
| Nature Communications | 9 |
| Acta Physica Sinica | 7 |
| Applied Physics Letters | 6 |
| Physical Review Letters | 6 |

## LUMICKS Publications Summary (35 Curated Studies)

| System Type | Count | Years |
|-------------|-------|-------|
| DNA-protein | 21 | 2020-2025 |
| Chromatin | 6 | 2023-2025 |
| Cytoskeleton | 2 | 2024-2025 |
| Cell mechanics | 2 | 2024-2025 |
| Membrane | 1 | 2025 |
| Motor protein | 1 | 2025 |
| Protein folding | 2 | 2025 |

### Featured Studies by Year

**2025 (18 studies)**
- TopIIα decatenation regulation by cohesin (Nature Communications)
- RNA Pol II transcription kinetics (Nature Structural & Molecular Biology)
- LEM2-BAF nuclear integrity (Nature)
- Condensin I-TopIIα interplay (Nature Communications)
- H4K16 chromatin destabilization (Molecular Cell)
- HSV-1 helicase-primase mechanisms (Cell)

**2024 (10 studies)**
- FANCD2-FANCI DNA scanning (Nature)
- Chromatin remodelers RSC, ISW2, SWR1 (eLife)
- Membrane tension propagation (Cell)
- Kinetochore-microtubule interactions (Science)
- Shu complex-RAD51-RPA dynamics (Nature Communications)

**2020-2023 (7 studies)**
- ORC-MCM chromatin mobility (Nature Communications)
- CRISPR-Cas12a mechanics (Nucleic Acids Research)
- SMC complex DNA organization
- DNA repair protein dynamics

## Usage

### Generate All Metadata Files
```bash
python generate_metadata_files.py
```

### Validate Metadata Files
```bash
python optical_tweezers_metadata.py
```

### Create New Metadata Entry
1. Copy `optical_tweezers_metadata_template.yaml`
2. Fill in required fields
3. Validate against `optical_tweezers_metadata_schema.json`

## Key Technologies Represented

- **LUMICKS C-Trap**: Correlative optical tweezers with confocal fluorescence
- **Dual-trap systems**: Most common configuration (2 traps)
- **Quadruple-trap systems**: For DNA braid experiments (4 traps)
- **Kymograph imaging**: Primary fluorescence acquisition mode
- **Force-clamp and force-extension**: Standard measurement protocols

## Typical Experimental Parameters

| Parameter | Typical Range |
|-----------|--------------|
| Laser wavelength | 1064 nm |
| Trap stiffness | 0.2-0.5 pN/nm |
| Bead diameter | 2.0-4.5 μm |
| Force range | 1-65 pN |
| Tension (DNA/protein) | 5-10 pN |
| Temperature | 20-37°C |

## References

1. LUMICKS Publications: https://lumicks.com/publications/
2. Biophysical Journal - Optical Tweezers Metadata Standards (Table 3)
3. Individual publication DOIs in each YAML metadata file

## License

This metadata collection is provided for research and educational purposes.

## Contact

For questions about this metadata framework or to contribute additional studies, please open an issue or submit a pull request.
