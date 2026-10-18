# Optical Tweezers Measurements of Biological Systems - Metadata Framework

## Overview

This document provides a comprehensive metadata framework for optical tweezers measurements of biological systems, based on the FAIR data principles outlined in:

**Reference Article:** Heller, I., Hoekstra, T.P., Hashemi Shabestari, M., Hijnen, M.T.J., Wuite, G.J.L. (2025). FAIR data for optical tweezers experiments. Biophysical Journal. DOI: 10.1016/j.bpj.2025.02.014 (S0006-3495(25)00141-9)

---

## Table 3: Minimum Metadata Standards for Optical Tweezers Experiments

### 1. HARDWARE CONDITIONS

| Metadata Field | Units | Description |
|----------------|-------|-------------|
| **Trap stiffness (κ)** | pN/nm | Typical range: 0.1–0.3 pN/nm per 100 mW of trap power |
| **Bead diameter** | μm | Typical range: 0.2–5 μm (polystyrene or silica) |
| **Bead material** | - | Polystyrene, silica, or other materials |
| **Bead surface chemistry** | - | Streptavidin-coated, anti-digoxigenin, protein-coated, etc. |
| **Trap laser wavelength** | nm | Typically 750–1200 nm (near-infrared) |
| **Trap laser power** | mW | Power at specimen plane |
| **Number of traps** | - | Single, dual, quadruple |
| **Trap configuration** | - | Surface-based, micropipette-based, dual-trap |
| **Objective numerical aperture (NA)** | - | Typically 1.2–1.4 |
| **Position detector type** | - | Quadrant photodiode (QPD), camera-based |
| **Position resolution** | nm | Sub-nanometer typical |
| **Force resolution** | pN | Sub-piconewton typical |
| **Data acquisition rate** | Hz | Sampling frequency |
| **Fluorescence capability** | - | Wide-field, TIRF, confocal, STED |
| **Fluorescence excitation wavelengths** | nm | Laser lines used |
| **Microfluidics channels** | - | Number and configuration |

### 2. SAMPLE INFORMATION

| Metadata Field | Units | Description |
|----------------|-------|-------------|
| **Biological system type** | - | DNA, RNA, protein, cell, etc. |
| **Sample source/origin** | - | Species, cell line, commercial source |
| **DNA/RNA sequence** | - | Sequence or reference |
| **DNA/RNA length** | bp or kb | Total length |
| **DNA/RNA topology** | - | Linear, circular, supercoiled |
| **Handle type** | - | DNA handles, polymer handles |
| **Handle length** | bp or nm | Length of handles |
| **Handle attachment chemistry** | - | Biotin-streptavidin, digoxigenin, etc. |
| **Protein name** | - | Full name and abbreviation |
| **Protein source** | - | Expression system, purification method |
| **Protein concentration** | nM or μM | Working concentration |
| **Protein labeling** | - | Fluorophore, tag type |
| **Cell type** | - | Cell line, primary cells |
| **Cell passage number** | - | If applicable |

### 3. EXPERIMENTAL CONDITIONS

| Metadata Field | Units | Description |
|----------------|-------|-------------|
| **Buffer composition** | - | Complete buffer recipe |
| **Salt concentration** | mM | KCl, NaCl, MgCl2, etc. |
| **pH** | - | Buffer pH |
| **Temperature** | °C | Experimental temperature |
| **Nucleotide state** | - | ATP, ATPγS, ADP, no nucleotide |
| **Nucleotide concentration** | mM | Working concentration |
| **Oxygen scavenging system** | - | Components and concentrations |
| **Surface passivation** | - | BSA, Pluronic, PEG, etc. |
| **Crowding agents** | - | PEG, Ficoll, etc. |

### 4. MEASUREMENT PARAMETERS

| Metadata Field | Units | Description |
|----------------|-------|-------------|
| **Operation mode** | - | Passive, force-clamp, force-ramp, force-jump |
| **Force range** | pN | Minimum and maximum forces applied |
| **Loading rate** | pN/s or nm/s | For force-ramp experiments |
| **Clamp force** | pN | For force-clamp experiments |
| **Extension range** | nm or μm | Range of molecule extension |
| **Tension** | pN | Applied tension during imaging |
| **Measurement duration** | s or min | Total observation time |
| **Number of molecules** | - | Sample size |
| **Number of measurements** | - | Replicates per molecule |

### 5. CALIBRATION INFORMATION

| Metadata Field | Units | Description |
|----------------|-------|-------------|
| **Calibration method** | - | Power spectrum, step response, etc. |
| **Calibration bead diameter** | μm | Bead used for calibration |
| **Drag coefficient (γ)** | pN·s/nm | Hydrodynamic drag |
| **Corner frequency (fc)** | Hz | From power spectrum fit |
| **Calibration temperature** | °C | Temperature during calibration |
| **Calibration buffer** | - | Buffer used for calibration |
| **Position sensitivity** | nm/V | Volts-to-nanometers conversion |

### 6. DATA PROCESSING

| Metadata Field | Units | Description |
|----------------|-------|-------------|
| **Analysis software** | - | Name and version |
| **Filtering method** | - | Low-pass, median, etc. |
| **Filter cutoff frequency** | Hz | If filtering applied |
| **Fitting model** | - | WLC, FJC, custom |
| **Persistence length** | nm | If applicable |
| **Contour length** | nm | If applicable |
| **Statistical methods** | - | Tests, confidence intervals |

---

## Biological Systems Studied with Optical Tweezers

### Category 1: DNA and Chromatin

| System | Typical Forces | Key Measurements | Common Substrates |
|--------|---------------|------------------|-------------------|
| DNA stretching | 0.1–65 pN | Force-extension curves | λ DNA (48.5 kb), synthetic constructs |
| DNA overstretching | 65–70 pN | B-S transition | Torsionally relaxed dsDNA |
| DNA unzipping | 10–20 pN | Sequence-dependent forces | DNA hairpins, hybrid ss-dsDNA |
| Nucleosome unwrapping | 3–30 pN | Unwrapping intermediates | Reconstituted chromatin arrays |
| Chromatin fiber mechanics | 1–50 pN | Higher-order structure | Chromatin fibers |
| DNA supercoiling | Variable | Plectoneme formation | Rotationally constrained DNA |

### Category 2: DNA-Protein Interactions

| System | Typical Forces | Key Measurements | Example Proteins |
|--------|---------------|------------------|------------------|
| Protein binding | 1–10 pN | Binding kinetics, diffusion | RPA, SSB, histones |
| Helicase unwinding | 5–30 pN | Unwinding rate, step size | RecBCD, UvrD, CMG |
| Polymerase activity | 1–20 pN | Transcription/replication rate | RNA Pol II, DNA Pol |
| Nuclease activity | 5–20 pN | Cleavage events | Cas9, Cas12a, restriction enzymes |
| Repair proteins | 5–15 pN | Damage recognition, diffusion | OGG1, FANCD2, ATL |
| SMC complexes | 1–20 pN | Loop extrusion, compaction | Cohesin, condensin, Smc5/6 |

### Category 3: Protein Folding and Mechanics

| System | Typical Forces | Key Measurements | Examples |
|--------|---------------|------------------|----------|
| Protein unfolding | 5–50 pN | Unfolding force, pathway | Titin, ubiquitin, GFP |
| Protein refolding | 1–20 pN | Refolding rate | Various domains |
| Intrinsically disordered proteins | 0.1–10 pN | Compaction, phase separation | FUS, α-synuclein |
| Protein-protein interactions | 5–50 pN | Binding strength | Receptor-ligand pairs |

### Category 4: Molecular Motors

| System | Typical Forces | Key Measurements | Examples |
|--------|---------------|------------------|----------|
| Kinesin | 5–8 pN | Stall force, velocity | Kinesin-1, Kinesin-14 |
| Dynein | 1–2 pN | Step size, processivity | Cytoplasmic dynein |
| Myosin | 2–10 pN | Force, power stroke | Myosin II, V |
| RNA Pol II | 15–25 pN | Stall force, pausing | Transcription elongation |
| Replicative helicases | 5–20 pN | Unwinding force | CMG, DnaB |

### Category 5: Cell and Membrane Mechanics

| System | Typical Forces | Key Measurements | Applications |
|--------|---------------|------------------|--------------|
| Membrane tether extraction | 10–50 pN | Tether force, membrane tension | Cell mechanics |
| Cell indentation | 1–100 pN | Cell stiffness, viscoelasticity | Cancer cell mechanics |
| Receptor-ligand bonds | 10–200 pN | Bond rupture force | Adhesion molecules |
| Red blood cell mechanics | 1–50 pN | Deformability | Malaria, sickle cell |

### Category 6: Cytoskeletal Components

| System | Typical Forces | Key Measurements | Examples |
|--------|---------------|------------------|----------|
| Actin polymerization | 1–10 pN | Polymerization force | Actin filaments |
| Microtubule dynamics | 1–10 pN | Polymerization/depolymerization | Tubulin |
| Kinetochore-MT interactions | 1–10 pN | Grip strength | Ndc80, DAM1 |

### Category 7: Pathogens and Host Interactions

| System | Typical Forces | Key Measurements | Examples |
|--------|---------------|------------------|----------|
| Bacterial adhesion | 10–100 pN | Adhesion force | E. coli, K. pneumoniae |
| Viral entry | Variable | Binding strength | HIV, influenza |
| Bacterial flagella | 0.1–1 pN | Motility force | Bacterial motility |

### Category 8: RNA Structures

| System | Typical Forces | Key Measurements | Examples |
|--------|---------------|------------------|----------|
| RNA folding | 5–30 pN | Folding intermediates | Riboswitches, aptamers |
| Pseudoknot mechanics | 10–50 pN | Unfolding force | SARS-CoV-2 frameshift |
| RNA-protein interactions | 5–20 pN | Binding kinetics | NCp7, ribosome |

---

## Representative Studies by Biological Category

### DNA Repair and Replication

| Study | System | Key Parameters | Reference |
|-------|--------|----------------|-----------|
| FANCD2-FANCI DNA scanning | ss-dsDNA junctions | D = 0.14 ± 0.07 μm²/s | Nature 2024 |
| ORC/MCM origin licensing | Chromatinized origins | 10.4 kbp DNA | Nat Commun 2023 |
| RecBCD helicase | dsDNA unwinding | ~20 kbp DNA | JMB 2024 |
| RPA migration on ssDNA | λ ssDNA | D = 20,000 nt²/s at 3 pN | JMB 2024 |
| Cas12a mechanics | λ DNA targets | 10-50 pN | NAR 2021 |

### Transcription

| Study | System | Key Parameters | Reference |
|-------|--------|----------------|-----------|
| Mammalian Pol II | Synthetic scaffold | ~5 pN tension | NSMB 2025 |
| NDF-FACT condensates | Chromatin | Phase separation | NCB 2025 |

### Chromatin and Nuclear Organization

| Study | System | Key Parameters | Reference |
|-------|--------|----------------|-----------|
| RSC/ISW2 remodelers | λ DNA + nucleosomes | ~5 pN, kymographs | eLife 2024 |
| TopII decatenation | λ DNA braids | ~5-28 pN | Nat Commun 2025 |
| LEM2-BAF hydrogel | dsDNA | ~65 pN (melting) | 2025 |

### SMC Complexes

| Study | System | Key Parameters | Reference |
|-------|--------|----------------|-----------|
| Cohesin DNA bridging | dsDNA, ssDNA | Variable force | 2023 |
| Smc5/6 fork binding | Hybrid substrates | 5-20 pN | 2023 |
| Bacterial ParABS | parS sites | DNA condensation | 2022 |

### Molecular Motors and Transport

| Study | System | Key Parameters | Reference |
|-------|--------|----------------|-----------|
| Kinesin force generation | Microtubules | 5-8 pN stall | Various |
| Dynein processivity | Microtubules | 1-2 pN | Science Adv |
| Kinetochore grip | Microtubules | Directional asymmetry | 2024 |

### Cell Mechanics

| Study | System | Key Parameters | Reference |
|-------|--------|----------------|-----------|
| Membrane tension | Neutrophils, HL-60 | ~15 pN tether force | 2024 |
| Cell stiffness | Various cancer cells | pN-nN range | Various |

### Protein Folding and Phase Separation

| Study | System | Key Parameters | Reference |
|-------|--------|----------------|-----------|
| FUS condensates | DNA + FUS protein | FRAP, fusion | 2022 |
| Trigger factor | Nascent chains | Compaction rate | PNAS 2025 |

---

## Instrument Configurations

### Commercial Systems

| Manufacturer | Model | Key Features |
|--------------|-------|--------------|
| LUMICKS | C-Trap | Dual/Quadruple traps, confocal fluorescence, microfluidics |
| LUMICKS | m-Trap | Magnetic tweezers integration |
| Impetux | LightCapture | Cell mechanics focus |
| JPK/Bruker | NanoTracker | AFM integration |
| MMI | CellManipulator | Laser microdissection integration |

### Custom Systems

| Institution | Features | Applications |
|-------------|----------|--------------|
| Block Lab (Stanford) | High-resolution fleezers | Transcription, molecular motors |
| Bustamante Lab (Berkeley) | Angular optical tweezers | DNA supercoiling |
| Wang Lab (Cornell) | High-bandwidth | Helicase stepping |
| Dekker Lab (Delft) | Magnetic tweezers | DNA topology |

---

## Data Formats and Repositories

### File Formats

| Format | Description | Source |
|--------|-------------|--------|
| HDF5 (.h5) | Hierarchical data format | LUMICKS Bluelake |
| MATLAB (.mat) | MATLAB data files | Custom systems |
| CSV/TXT | Plain text | Universal |
| TIFF | Image stacks | Fluorescence data |

### Analysis Software

| Software | Purpose | Source |
|----------|---------|--------|
| Pylake | LUMICKS data analysis | Python package |
| MATLAB | Custom analysis | MathWorks |
| Igor Pro | Force spectroscopy | WaveMetrics |
| Custom scripts | Publication-specific | Various |

### Data Repositories

| Repository | Type | URL |
|------------|------|-----|
| Zenodo | General data | zenodo.org |
| Dryad | Publication data | datadryad.org |
| Figshare | Research data | figshare.com |
| GitHub | Code/analysis | github.com |

---

## Quality Control Checklist

### Pre-Experiment
- [ ] Trap calibration performed
- [ ] Bead characterization (size, coating)
- [ ] DNA/protein quality verified
- [ ] Buffer preparation documented
- [ ] Temperature equilibration

### During Experiment
- [ ] Force baseline recorded
- [ ] Extension calibration verified
- [ ] Fluorescence calibration (if applicable)
- [ ] Multiple molecules measured
- [ ] Control experiments performed

### Post-Experiment
- [ ] Raw data archived
- [ ] Analysis pipeline documented
- [ ] Fitting parameters recorded
- [ ] Statistical analysis performed
- [ ] Metadata complete

---

## References

### Key Methodological Papers

1. Heller, I., et al. (2025). FAIR data for optical tweezers experiments. Biophysical Journal.
2. Moffitt, J.R., et al. (2008). Recent advances in optical tweezers. Annual Review of Biochemistry, 77, 205-228.
3. Neuman, K.C., & Nagy, A. (2008). Single-molecule force spectroscopy: optical tweezers, magnetic tweezers and atomic force microscopy. Nature Methods, 5(6), 491-505.
4. Hashemi Shabestari, M., et al. (2017). Recent advances in biological single-molecule applications of optical tweezers and fluorescence microscopy. Methods in Enzymology, 582, 85-119.

### Optical Tweezers Reviews

1. Bustamante, C.J., et al. (2021). Optical tweezers in single-molecule biophysics. Nature Reviews Methods Primers, 1, 25.
2. Ritchie, D.B., & Bhattacharyya, A. (2024). Optical tweezers in biomedical research – progress and techniques. PMC11705474.

---

*Document compiled: January 2026*
*Based on FAIR data principles for optical tweezers experiments*
*For updates and corrections, please refer to the original publications*
