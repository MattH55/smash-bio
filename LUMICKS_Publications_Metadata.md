# LUMICKS Publications Metadata Extraction

## Document Scope

This document extracts detailed metadata from publications using the LUMICKS C-Trap system, following the format established in Belan et al. 2021 (STAR Protocols). 

**Current Status:**
- **17 major studies** documented with full metadata
- **Key methodological citations** extracted for each study
- Focus on peer-reviewed journal articles from the LUMICKS knowledge library

**Metadata Categories Extracted:**
- Citation information
- Constructs (DNA substrates, handles, beads)
- Instrument Configuration (C-Trap settings, optical tweezers, microscopy, microfluidics)
- Experimental Conditions (buffers, proteins, probes)
- Experimental Protocol
- Results and Key Findings
- Key Features (advantages, limitations, applications)
- Key Citations (methodological references)

**Note on Citations:**
For each publication, we extract the most relevant methodological citations, especially those related to:
- C-Trap and optical tweezers methods
- DNA substrate preparation
- Single-molecule fluorescence techniques
- Related single-molecule studies

Complete citation lists for each publication can be found in the original papers.

---

## STUDY 1: Cutts et al. 2025 (LUMICKS C-Trap) - Topoisomerase 2A Decatenation

### Citation
Cutts, E.E., Saravanan, S., Girvan, P., Ambrose, B., Fisher, G.L.M., Rueda, D.S., & Aragon, L. (2025). Substrate accessibility regulation of human TopIIα decatenation by cohesin. Nature Communications, 16, Article number: 7200. DOI: 10.1038/s41467-025-62505-3

### Constructs - Lambda DNA Braids

**Base Substrate**
- Template: Lambda DNA (λ DNA), 48.5 kb
- End-caps: Biotinylated at one strand's ends
- Attachment: Biotinylated ends bind to streptavidin-coated beads

**Braid Generation Strategy**
- Method: Manual manipulation using quadruple optical traps
- Two λ-DNA molecules tethered between separate bead pairs
- Controlled bead movements in Z-plane to thread one DNA under/over the other
- Creates right-handed or left-handed braid crossings (single or multiple crossings)
- Braids resemble type-A catenanes with larger crossing angles
- Verification: Shortened contour length and force coupling between bead pairs

**Handles**
- Total length: 48.5 kb λ DNA per molecule
- Attachment:
  - 5' end: Biotinylated (binds to streptavidin beads)
  - 3' end: Biotinylated (binds to streptavidin beads)
- Two independent DNA molecules, each tethered between separate bead pairs

**Beads**
- Type: Streptavidin-coated polystyrene beads
- Configuration: Four beads total (beads 1-2 for DNA1, beads 3-4 for DNA2)
- Size: Not explicitly stated (typical ~2-4.5 μm for C-Trap)

### Instrument Configuration - LUMICKS C-Trap (Quadruple Trap)

**System Components**
- Manufacturer: LUMICKS (Amsterdam, Netherlands)
- Model: C-Trap with quadruple-trap capability (Q-Trap)
- Core capabilities:
  - Quadruple optical tweezers (four independent traps)
  - Confocal fluorescence microscopy
  - Multi-channel laminar-flow microfluidics (6 channels)
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Number of traps: Four independent traps
- Trap configuration:
  - Beads 1 & 2: First DNA molecule
  - Beads 3 & 4: Second DNA molecule
- Force range:
  - Moderate force: ~5 pN (for braid formation and observation)
  - Force threshold: ~28 pN (above which TOP2α activity declines)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths:
  - Alexa Fluor 555 (AF555) for TOP2α labeling
  - YOYO-1 for DNA visualization
- Single-photon counter module
- Pixel size: ~100 nm (typical confocal resolution)
- Objectives: Research-grade inverted optical microscope objectives

**Microfluidics**
- Design: 6-channel laminar flow cell
- Channel usage:
  - Channels 1 & 2: Bead capture and DNA tethering
  - Channels 3-6: Buffer exchange, TOP2α, ATP, fluorescent dyes
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein localization

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Braid formation buffer: Not explicitly detailed (likely PBS or standard buffer)
- Assay buffer:
  - TOP2α-AF555: Purified human TOP2α labeled with Alexa Fluor 555
  - Label efficiency: ~30-70%; at least 50% of enzyme dimers have ≥ one fluorophore
  - ATP: 1 mM (commonly used)
  - YOYO-1: For DNA visualization
- Temperature: Not explicitly stated (likely room temperature ~25°C)

**Fluorescent Probes**
- TOP2α-AF555: Alexa Fluor 555-labeled human Topoisomerase IIα
- YOYO-1: DNA intercalating dye for DNA visualization

**Oxygen Scavenging System**
- Not explicitly detailed in available sources

### Experimental Protocol

**Braid Formation Procedure**
1. Capture streptavidin beads in channel 1
2. Tether two λ-DNA molecules between bead pairs in channel 2
3. Move to buffer channel; verify DNA tethers via force-extension curves
4. Generate braid via controlled bead movements:
   - Move both DNA molecules into same Z-plane, aligned in parallel
   - Move bead 3 down in Z, pass under DNA1 between beads 1 & 2
   - Move bead 3 above DNA1, pass over it, aligning DNA2 with DNA1
   - Creates right-handed or left-handed braid crossing
5. Maintain ~5 pN force after braid formation

**TOP2α Activity Assay**
1. Introduce TOP2α-AF555 + ATP (and possibly YOYO-1)
2. Monitor:
   - Forces on beads over time (force drop when decatenation occurs)
   - Fluorescence imaging: location of enzyme, braid junction, DNA structure
   - Recovery of DNA extension consistent with naked DNA
3. Force-extension curves confirm resolution

**Force-Extension Curve Analysis**
- dsDNA model: Worm-like chain (WLC) model
- Braid verification: Shortened contour length compared to unbraided DNA
- Decatenation verification: Extension returns to naked DNA behavior

### Results - Typical Data

**Force-Extension Measurements**
- Unbraided λ dsDNA: Standard WLC behavior
- Braided DNA: Shortened contour length, force coupling between bead pairs
- After decatenation: Extension returns to naked DNA behavior

**Key Findings**
- Force threshold: ~28 pN (above which TOP2α activity declines sharply)
- Chiral preference: Right-handed braid crossings resolved more efficiently
- Loading requirement: TOP2α must bind directly at DNA crossover points for efficient decatenation
- Cohesin effect: Cohesin binds stably to DNA braids and inhibits TOP2α activity
- Condensin I: Does not block decatenation in the same way as cohesin

**Imaging Data**
- TOP2α-AF555 binding: Often observed at braid junction before resolution
- After resolution: Enzyme may relocate along separated DNA strands
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Features

**Advantages**
- Direct visualization of decatenation in real-time
- Controlled force and geometry
- Ability to test different braid geometries (right- vs left-handed)
- Combined force and fluorescence readouts
- Can test effect of other proteins (cohesin, condensin)

**Limitations**
- Manual braid formation requires skill
- Limited to in vitro conditions
- Force threshold may vary with conditions

**Applications Demonstrated**
- TOP2α decatenation mechanism
- Force-dependent activity regulation
- Chiral preference in DNA topology resolution
- Cohesin-mediated regulation of decatenation
- Comparison with condensin effects

---

## STUDY 2: Ha et al. 2024 (LUMICKS C-Trap) - Chromatin Remodeler Target Search

### Citation
Carcamo, C., et al. (2024). Dynamic 1D Search and Processive Nucleosome Translocations by RSC and ISW2. eLife, 13, e91433. DOI: 10.7554/eLife.91433

### Constructs - Lambda DNA with Nucleosome Arrays

**Base Substrate**
- Template: Lambda DNA (λ DNA), ~48.6 kb (48,502 bp)
- End-caps: Biotinylated at one end, digoxigenin at other end (or biotin both ends)

**End-labeling Strategy**
- One end: 3×-biotin oligos
- Other end: 3×-digoxigenin (or biotin both ends)
- Method: Adaptor oligos, anneal (25- to 50-fold molar excess), ligate with T4 DNA ligase
- Heat denature, purify

**Nucleosome Array Reconstitution**
- Method: Salt-gradient dialysis
- Histone octamers: Purified yeast histone octamers
- Labeling: Some fraction labeled (e.g. H2A with Cy3) for visualizing nucleosomes
- Salt gradient: Mix λ DNA with histone octamer in high salt buffer (e.g. 2 M NaCl), gradually dialyze into lower salt (e.g. 50-100 mM NaCl) over >16 h
- Octamer:DNA molar ratios: 40:1, 20:1, 10:1, 5:1 to produce sparse arrays (~10 nucleosomes per λ DNA)
- Verification: Electrophoretic mobility shift assay (EMSA) on agarose gel (0.5% agarose, 0.5× TBE)

**Handles**
- Total length: ~48.6 kb λ DNA
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin (binds to anti-digoxigenin beads) or biotin both ends

**Beads**
- Type: 
  - Streptavidin-coated polystyrene beads (for biotin end)
  - Anti-digoxigenin beads (for digoxigenin end)
- Size: Not explicitly stated (typical ~2-4.5 μm for C-Trap)

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel laminar-flow microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range:
  - Tension: ~5 pN (maintained during imaging)
  - Tension allowed to fluctuate slightly during imaging
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths:
  - Cy3 (for nucleosomes, H2A-Cy3)
  - JFX650 (for remodelers, HaloTag-JFX650)
- Two-color confocal fluorescence imaging to separately detect remodeler and nucleosome signals
- Pixel size: ~100 nm (typical confocal resolution)

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching
- Surface passivation: BSA + Tween or Pluronic to reduce sticking

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein and nucleosome localization

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Salt concentrations: 
  - Typical: ~50 mM KCl
  - Also tested: 100 mM, up to 150-200 mM to assess salt sensitivity
- Nucleotide states:
  - No nucleotide
  - ATPγS (non-hydrolysable) at ~1 mM
  - ATP (hydrolysable) at ~1 mM
- Tension: Maintain DNA stretched ~5 pN
- Temperature: Not explicitly stated (likely room temperature)

**Fluorescent Probes**
- RSC, ISW2, SWR1: Catalytic ATPase subunit fused to HaloTag for fluorescent labeling (JFX650 dye)
- Nucleosomes: H2A-Cy3 for visualizing nucleosomes

**Oxygen Scavenging System**
- Not explicitly detailed in available sources

### Experimental Protocol

**DNA Preparation**
1. Start with λ DNA (~48.6 kb)
2. End-labeling:
   - One end with 3×-biotin oligos
   - Other end with 3×-digoxigenin (or biotin both ends)
   - Use adaptor oligos, anneal (25- to 50-fold molar excess), ligate with T4 DNA ligase
   - Heat denature, purify

**Nucleosome Array Reconstitution**
1. Use salt-gradient dialysis: mix λ DNA with histone octamer (some labeled H2A-Cy3) in high salt buffer (e.g. 2 M NaCl)
2. Gradually dialyze into lower salt (e.g. 50-100 mM NaCl) over >16 h
3. Test range of octamer:DNA molar ratios (e.g. 40:1, 20:1, 10:1, 5:1) to produce sparse arrays
4. After reconstitution, shift into low-salt buffer
5. Verify nucleosome assembly by EMSA on agarose gel

**Remodeler Purification & Fluorescent Labeling**
1. Fuse ATPase subunit of RSC, ISW2 (or SWR1) to HaloTag
2. Express and purify full multiprotein complex using standard chromatography, glycerol gradients
3. Label with fluorescent HaloTag ligand (e.g. JFX650)
4. Verify labeling efficiency via SDS-PAGE, gel scanning for fluorophore vs protein

**Optical Tweezers & Imaging Setup**
1. Use dual-optical trap system to hold beads: attach DNA ends to beads via biotin-streptavidin and digoxigenin-anti-dig beads
2. Stretch DNA to ~5 pN tension before imaging
3. Maintain traps at fixed position during fluorescence acquisition
4. Use microfluidics chamber with laminar flow to deliver proteins, nucleosomes, buffer

**Imaging & Data Acquisition**
1. Label nucleosomes (Cy3-H2A) and remodeler (e.g. JFX650)
2. Use two-color confocal fluorescence imaging
3. Collect kymographs: imaging over time along DNA tether; scan line along DNA to produce space-time trajectories
4. Use frame rates sufficient to resolve diffusive behaviors (e.g. 20-frame rolling windows ~0.85 s to calculate instantaneous diffusion coefficients)

### Results - Typical Data

**Force-Extension Measurements**
- λ dsDNA with nucleosomes: Modified WLC behavior
- Nucleosome positions: Visualized via Cy3-H2A fluorescence

**Key Findings**
- Diffusion on free DNA: 1D diffusion coefficients for remodelers
- Classification: Non-diffusive, low diffusion, high diffusion
- Salt dependence: Sliding is more salt-resistant than hopping
- Nucleotide state: ATP binding increases chromatin-associated diffusion; hydrolysis needed for stable remodeling
- Interaction with nucleosomes: Collisions, binding, colocalization, bypass or blockade
- ATP-dependent translocation: Movement of nucleosomes with remodelers over long distances (kbp), speed ~30 bp/s
- Directionality: RSC/SWI/SNF push nucleosomes away from NDRs; INO80/ISW2 move nucleosomes toward NDRs

**Imaging Data**
- Kymographs: Space-time trajectories of remodeler and nucleosome positions
- Temporal resolution: Frame rates sufficient to resolve diffusive behaviors
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Features

**Advantages**
- Direct visualization of remodeler search and translocation
- Controlled tension and buffer conditions
- Ability to test different nucleotide states
- Combined force and fluorescence readouts
- Can distinguish sliding vs hopping via salt dependence

**Limitations**
- Nucleosome reconstitution requires careful optimization
- Photobleaching concerns require careful illumination control
- Limited to in vitro conditions

**Applications Demonstrated**
- RSC, ISW2, SWR1 1D search behavior
- Nucleosome translocation mechanisms
- ATP binding vs hydrolysis effects
- Directional preferences of different remodelers
- Salt-dependent diffusion modes

---

## STUDY 3: Wang et al. 2025 (LUMICKS C-Trap) - Mammalian Transcription Elongation

### Citation
Wang, Y., et al. (2025). Kinetic control of mammalian transcription elongation. Nature Structural & Molecular Biology. DOI: 10.1038/s41594-025-01707-1

### Constructs - Synthetic Nucleic Acid Scaffold

**Base Substrate**
- Template: Synthetic DNA template, biotinylated at both ends
- RNA primer: Labeled with ATTO647N on 5' end
- Downstream template: Seven repeated sequence units for probe hybridization

**Scaffold Design**
- DNA template: Biotinylated at both ends for tethering
- RNA primer: ATTO647N-labeled at 5' end
- Non-template strand (NTS) DNA: Added after initial assembly
- Downstream repeats: Seven repeated sequence units that hybridize with Cy3-labeled DNA probe

**Handles**
- Total length: Not explicitly stated (synthetic scaffold, shorter than λ DNA)
- Attachment:
  - 5' end: Biotinylated (binds to streptavidin beads)
  - 3' end: Biotinylated (binds to streptavidin beads)

**Beads**
- Type: Streptavidin-coated polystyrene beads
- Size: ~2.14 μm diameter
- Configuration: Two beads, one per trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal or line-scan fluorescence microscopy
  - Multi-channel laminar-flow microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range:
  - Tension: ~5 pN (to keep DNA taut)
  - Monitoring setup rather than force-stalling
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal line scanning through center between beads
- Laser wavelengths:
  - ATTO647N (for RNA primer)
  - Cy3 (for DNA probe hybridized to nascent RNA)
- Line-scan interval: ~0.2 s per line
- Kymograph generation: Position vs. time

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Channel usage:
  - Channel 1: Beads
  - Channel 3: Imaging buffer / verification of EC presence (ATTO647N RNA primer signal)
  - Channel 4: Transcription buffer + elongation factors + NTPs and probe oligonucleotides
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for RNA tracking

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)
- Custom line-tracking algorithm (greedy tracking) for kymograph analysis

### Experimental Conditions

**Buffer Conditions**
- Imaging buffer:
  - Oxygen scavenging system (protocatechuic acid + protocatechuate-3,4-dioxygenase)
  - RNase inhibitor
  - Reducing agent (DTT)
  - Triplet-state quenching cocktail (Trolox + other small quenchers)
- Transcription buffer:
  - Elongation factors + NTPs
  - Probe oligonucleotides (Cy3-labeled)
- Temperature: Not explicitly stated (likely room temperature)

**Protein Components**
- Pol II: Purified mammalian Pol II (26 subunits, ~1.6 MDa) from Sus scrofa thymus
- Elongation factors (All-factors mix):
  - P-TEFb
  - DSIF
  - PAF1C
  - RTF1
  - SPT6
  - IWS1
  - TFIIS
  - ELOF1

**Fluorescent Probes**
- ATTO647N: Labeled at 5' end of RNA primer
- Cy3-labeled DNA oligo probe: Binds nascent transcript repeat sequences

**NTPs**
- Not explicitly detailed (standard NTP mix for transcription)

### Experimental Protocol

**Assembly of Elongation Complexes (ECs)**
1. Anneal nucleic acid scaffold (DNA + RNA primer) with temperature steps
2. Mix in Pol II, allowing for hybridization and extension
3. Add non-template strand (NTS) DNA
4. Use T4 DNA ligase to seal nicks (generate fully duplex downstream and upstream DNA around EC)

**Single-Molecule Platform Setup**
1. Tether EC-tethered DNA construct between two streptavidin-coated polystyrene beads (~2.14 μm diameter)
2. Each bead held in one optical trap
3. Hold DNA tether under ~5 pN tension to keep it taut
4. Place EC such that trap geometry allows tracking extension as Pol II elongates

**Data Acquisition**
1. Monitor force and extension data from tweezer module
2. Collect fluorescence photon counts (ATTO647N, Cy3) from confocal scanning
3. Generate kymographs: position vs. time of RNA / probe signals
4. Apply custom line-tracking algorithm (greedy tracking) to define movement of fluorescence spots over time
5. Segment trajectories via Bayesian framework:
   - Active elongation: slope ≥1 nt/s
   - Pauses or backtracking: slope <1 nt/s or negative

**Perturbations: Factor Omissions, Phosphorylation States**
1. Modular removal of specific elongation factors (e.g. omitting P-TEFb, DSIF, PAF1C, SPT6, RTF1)
2. Phosphorylation manipulations:
   - ΔP-TEFb: Omit from EC assembly + use inhibitor (flavopiridol) during transcription
   - Prevent DSIF phosphorylation (DSIF^P−)
   - Permit only Pol II + DSIF phosphorylation (Pol II^P+ & DSIF^P+)

### Results - Typical Data

**Force-Extension Measurements**
- EC-tethered DNA: Extension changes as Pol II elongates
- Movement readout: Change in tether length via fluorescent probe movement

**Key Findings**
- Multiple speed "gears": Pol II speed shifts depending on associated factors and phosphorylation
- P-TEFb role: Phosphorylation boosts elongation speed ~5-fold when present
- DSIF phosphorylation: Stabilizes binding to Pol II and enables faster active-elongating state
- PAF1C effect: Binding correlates with immediate acceleration
- Hierarchical factor interactions: Factors act synergistically, not additively
- Pausing behaviors: Segments with slopes <1 nt/s classified as paused or stalled
- TFIIS role: Required to rescue backtracked or arrested Pol II

**Imaging Data**
- Kymographs: Position vs. time trajectories of RNA / probe signals
- Temporal resolution: ~0.2 s per line scan
- Spatial resolution: Confocal microscopy limit

### Key Features

**Advantages**
- Real-time visualization of transcription elongation
- Controlled factor composition
- Ability to test phosphorylation states
- Combined force and fluorescence readouts
- Modular factor addition/removal

**Limitations**
- Requires purified Pol II and all elongation factors
- Limited to in vitro conditions
- Synthetic scaffold may not fully recapitulate chromatin context

**Applications Demonstrated**
- Pol II elongation speed regulation
- Factor hierarchy and synergy
- Phosphorylation-dependent control
- Pausing and backtracking mechanisms
- Kinetic control of gene expression

---

## STUDY 4: von Appen et al. 2025 (LUMICKS C-Trap) - LEM2-BAF Nuclear Envelope Hydrogel

### Citation
von Appen, A., et al. (2025). A self-enforcing protein-DNA surface hydrogel safeguards nuclear integrity. [Publication details to be confirmed]

### Constructs - Double-Stranded DNA

**Base Substrate**
- Template: Standard double-stranded DNA (dsDNA)
- Configuration: Torsionally relaxed (not constrained)
- Length: Not explicitly stated in available sources

**Handles**
- Attachment method: Not explicitly detailed
- Likely biotinylated ends for streptavidin bead attachment

**Beads**
- Type: Streptavidin-coated beads (inferred)
- Size: Not explicitly stated

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Fluorescence microscopy
  - Multi-channel flow cell for exchanging reagents

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Force range:
  - DNA melting force: ~65 pN (standard overstretching plateau for torsionally relaxed dsDNA)
  - Tests show DNA melting/overstretching at ~65 pN
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence microscopy (inferred)
- Specific wavelengths not detailed

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Not explicitly detailed in available sources
- Standard buffer conditions for DNA force measurements (inferred)

**Protein Components**
- LEM2: Full length vs IDR deletion vs LEM motif mutant
- BAF: Barrier-to-Autointegration Factor
- Concentrations: Not explicitly detailed

**Fluorescent Probes**
- Not explicitly detailed

**Oxygen Scavenging System**
- Not explicitly detailed

### Experimental Protocol

**Force-Extension Measurements**
1. Tether DNA between optical traps
2. Apply force to DNA in presence of LEM2 + BAF
3. Monitor force-extension behavior
4. Compare to classic DNA melting behavior (~65 pN)

**Key Observations**
- DNA melting/overstretching occurs at ~65 pN (standard for torsionally relaxed dsDNA)
- LEM2-BAF co-condensate can protect DNA beyond melting point
- IDR of LEM2 required for stiffening effect
- Deleting IDR abolishes stiffening effect under load

### Results - Typical Data

**Force-Extension Measurements**
- Standard dsDNA: Overstretching plateau around 65 pN
- With LEM2-BAF: DNA shielded beyond melting point
- Unconventional DNA stiffening effect under load
- IDR deletion: Abolishes stiffening effect

**Key Findings**
- Force threshold: ~65 pN (DNA melting point)
- LEM2-BAF co-condensate: Protects DNA beyond melting point
- IDR requirement: Intrinsically disordered region of LEM2 required for effect
- Mechanical reinforcement: Collective assembly induces DNA stiffening
- Cellular relevance: Forms elastic surface hydrogel at nuclear periphery

**Imaging Data**
- Cryo-electron tomography: Shows continuous surface hydrogel at nuclear periphery
- Spatial resolution: Cryo-ET resolution

### Key Features

**Advantages**
- Direct measurement of DNA mechanical properties
- Ability to test protein-DNA co-condensate effects
- Combined force and structural readouts

**Limitations**
- Several experimental parameters not fully detailed:
  - DNA length
  - Loading rate/pulling speed
  - Buffer composition
  - Protein concentrations
  - Trap stiffness and calibration details

**Applications Demonstrated**
- Nuclear envelope mechanical protection
- Protein-DNA co-condensate mechanics
- IDR-mediated mechanical reinforcement
- Nuclear integrity under mechanical stress

---

## STUDY 5: Yan et al. 2024 (LUMICKS C-Trap) - Live Cell Membrane Tension Propagation

### Citation
Yan, S., et al. (2024). Cell protrusions and contractions generate long-range membrane tension propagation. [Publication details to be confirmed]

### Constructs - Live Cell Membrane Tethers

**Base Substrate**
- Template: Live cells (neutrophils, HL-60 cells)
- Membrane tethers: Pulled from cell membrane using optical tweezers
- Configuration: Dual tether assays (two tethers at different positions)

**Tether Generation Strategy**
- Method: Optical tweezers pull membrane tethers from cell surface
- Two tethers: "Static tether" to monitor, and second one for measurement
- Positions: Widely separated membrane points (adjacent and opposite sides of cell)

**Handles**
- Cell type: Neutrophils, HL-60 neutrophil-like cells
- Membrane composition: Native plasma membrane with actin cortex

**Beads**
- Type: Not explicitly detailed (likely functionalized beads for membrane attachment)
- Configuration: Dual trap setup for two independent tethers

### Instrument Configuration - LUMICKS C-Trap (Dual Trap)

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap with dual-trap capability
- Core capabilities:
  - Dual optical tweezers
  - Optogenetics control
  - Live cell imaging
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Number of traps: Two independent traps
- Force range:
  - Baseline membrane tether force: ~15 pN (in HL-60 cells)
  - Force application: Variable for tension propagation studies
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Live cell imaging
- Fluorescence microscopy for actin cortex visualization
- Temporal resolution: <1 second delay for tension propagation

**Optogenetics**
- Light-activated control over actin polymerization (protrusion)
- Light-activated control over actomyosin contractility (contraction)
- Endogenous cortical force activation (not external force only)

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Tension correlation: High correlation between tension signals at widely separated points

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Cell Culture**
- Cell types: Neutrophils, HL-60 neutrophil-like cells
- Culture conditions: Standard cell culture conditions

**Buffer Conditions**
- Cell culture medium: Standard for cell type
- Temperature: 37°C (physiological)

**Pharmacological Perturbations**
- Latrunculin B: Disassemble actin cortex
- Osmotic treatments: Weaken membrane-cortex attachments (MCAs)

**Optogenetics Activation**
- Actin polymerization: Local optogenetic activation
- Actomyosin contraction: Local optogenetic activation
- Timing: Controlled light activation

### Experimental Protocol

**Dual Tether Assay Setup**
1. Culture cells (neutrophils, HL-60)
2. Pull two membrane tethers from cell surface at different positions
3. Monitor baseline membrane tether force (~15 pN)
4. Establish "static tether" for monitoring

**Tension Propagation Assay**
1. Apply local optogenetic activation (actin protrusion or actomyosin contraction)
2. Monitor tension changes at both tether positions
3. Measure correlation and timing of tension propagation
4. Test with pure membrane pulling (without cortex engagement)
5. Test with cortex disruption (latrunculin B, osmotic treatments)

**Controls**
- Pure membrane pulling: Forces applied only to plasma membrane via tether
- Cortex disruption: Latrunculin B or osmotic treatments
- Comparison: With vs without cortex engagement

### Results - Typical Data

**Force Measurements**
- Baseline tether force: ~15 pN (HL-60 cells)
- Tension propagation: Nearly simultaneous tension rises (<1 second delay)
- Spatial correlation: High correlation between widely separated points during cortex-mediated perturbations

**Key Findings**
- Rapid global propagation: Membrane tension propagates rapidly across whole cell when actin cortex is engaged
- Timing: <1 second delay for tension propagation during actin-driven protrusions or actomyosin contractions
- Pure membrane pulling: Fails to induce global tension propagation
- Cortex requirement: Forces must engage actin cortex for efficient tension propagation
- Membrane-cortex attachments (MCAs): Act as coupling points for tension transmission

**Imaging Data**
- Temporal resolution: <1 second for tension propagation
- Spatial resolution: Cell-wide measurements
- Correlation analysis: High correlation during cortex-mediated perturbations

### Key Features

**Advantages**
- Direct measurement of membrane tension in live cells
- Optogenetics allows endogenous force activation
- Dual tether setup enables spatial correlation measurements
- Combined force and live cell imaging

**Limitations**
- Requires optogenetics setup
- Cell type specific (neutrophils, HL-60)
- Complex cell preparation

**Applications Demonstrated**
- Membrane tension propagation mechanisms
- Actin cortex role in tension transmission
- Membrane-cortex attachment dynamics
- Global mechanical integration in cells
- Cell shape and migration coordination

---

## STUDY 6: Liu et al. (LUMICKS C-Trap) - DNA Replication and Transcription (smCFFM)

### Citation
Liu, S., et al. Single-molecule correlative fluorescence-force microscopy (smCFFM) studies. [Multiple publications, details to be confirmed]

### Constructs - DNA and Chromatin Substrates

**Base Substrate**
- Template: Long DNA templates (λ DNA or synthetic)
- Chromatin: Nucleosome arrays assembled on DNA
- Configuration: Tethered between beads for force application

**DNA Preparation**
- Long DNA templates: For replication and transcription studies
- End-labeling: Biotinylated or digoxigenin-labeled ends
- Chromatin assembly: In situ nucleosome reconstitution using histone chaperone Nap1

**Nucleosome Assembly**
- Method: In situ reconstitution using Nap1 chaperone
- Timing: Minutes (rapid assembly)
- Density: Tunable nucleosome density
- Labeling: Fluorescently labeled histones (e.g. H2A-Cy3)

**Handles**
- Total length: Variable (long templates for replication/transcription)
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Optical tweezers (dual or multiple traps)
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging (smCFFM)

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual or multiple traps
- Force range: Variable (typically 5-20 pN for replication/transcription)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths:
  - Cy3 (for nucleosomes, H2A-Cy3)
  - Other fluorophores for protein labeling
- Multi-color imaging for simultaneous detection

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein and nucleosome localization

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Salt concentrations: Variable (typically 50-150 mM)
- Temperature: Room temperature or 37°C depending on application

**Protein Components**
- Replication: CMG helicase, replisome components
- Transcription: RNA polymerase, transcription factors
- Chromatin: Histone octamers, chromatin remodelers (PRC2, etc.)

**Fluorescent Probes**
- Histones: H2A-Cy3 or other labeled histones
- Proteins: Fluorescently labeled replication/transcription factors
- DNA: Intercalating dyes if needed

**NTPs/Nucleotides**
- For replication: dNTPs
- For transcription: NTPs
- ATP: For helicase and remodeler activity

### Experimental Protocol

**DNA Preparation**
1. Prepare long DNA templates (λ DNA or synthetic)
2. End-label with biotin and digoxigenin
3. Verify labeling efficiency

**Chromatin Assembly (if applicable)**
1. Use Nap1 chaperone for in situ nucleosome reconstitution
2. Assemble nucleosomes on DNA template within minutes
3. Verify nucleosome assembly

**Single-Molecule Setup**
1. Tether DNA/chromatin between optical traps
2. Apply appropriate force (typically 5-20 pN)
3. Introduce proteins (replication/transcription machinery)
4. Monitor force and fluorescence simultaneously

**Data Acquisition**
1. Collect force-extension data
2. Collect fluorescence kymographs
3. Correlate force changes with protein binding/movement
4. Analyze replication/transcription dynamics

### Results - Typical Data

**Force-Extension Measurements**
- DNA/chromatin: WLC behavior modified by nucleosomes
- Protein binding: Force changes upon protein binding
- Replication/transcription: Extension changes during processive movement

**Key Findings**
- CMG helicase: Ring conformations when encountering fork junctions or DNA damage
- Nucleosome effects: How nucleosomes influence replication and transcription
- PRC2 binding: Modes on chromatin, interactions with adjacent/non-adjacent nucleosomes
- Chromatin mechanics: Nucleosome positioning and stability influence processes

**Imaging Data**
- Kymographs: Space-time trajectories of proteins and nucleosomes
- Temporal resolution: Frame rates sufficient to resolve dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Features

**Advantages**
- Direct visualization of replication/transcription in real-time
- Combined force and fluorescence readouts (smCFFM)
- Rapid chromatin assembly (Nap1 method)
- Tunable nucleosome density
- Can test effects of chromatin on processes

**Limitations**
- Requires purified proteins
- Limited to in vitro conditions
- Complex setup for multi-protein systems

**Applications Demonstrated**
- DNA replication mechanisms
- Transcription dynamics
- Chromatin effects on processes
- Protein-DNA/chromatin interactions
- Mechanical properties of chromatin

---

## STUDY 7: Rueda et al. 2024 (LUMICKS C-Trap) - FANCD2-FANCI DNA Repair

### Citation
Passmore, L.A., Rueda, D.S., et al. (2024). FANCD2-FANCI surveys DNA and recognizes double- to single-stranded junctions. Nature, [Volume and pages to be confirmed]. DOI: 10.1038/s41586-024-07770-w

### Constructs - Lambda DNA with ss-dsDNA Junctions

**Base Substrate**
- Template: Lambda DNA (λ DNA), ~48.5 kb
- Junctions: Double-stranded to single-stranded DNA (ds-ssDNA) junctions
- Configuration: Tethered DNA with defined ss-dsDNA boundaries

**Junction Generation Strategy**
- Method: Not explicitly detailed (likely enzymatic or force-induced)
- Creates ss-dsDNA boundaries mimicking stalled replication forks or damaged sites
- Verification: Fluorescence or force-extension analysis

**Handles**
- Total length: ~48.5 kb λ DNA
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Not explicitly stated (typically 5-10 pN for diffusion studies)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths: Not explicitly detailed (likely for FANCD2-FANCI labeling)
- Single-molecule tracking for diffusion analysis

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein localization and tracking

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)
- Tracking algorithms: For diffusion coefficient calculation

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Salt concentrations: Not explicitly detailed
- Temperature: Room temperature or 37°C

**Protein Components**
- FANCD2-FANCI (D2-I): Heterodimer complex
- Variants tested:
  - Wild-type D2-I
  - Phosphomimetic D2-I variants
  - Monoubiquitinated D2-I (ubD2-I)
  - KR helix mutants (for junction recognition)

**Fluorescent Probes**
- FANCD2-FANCI: Fluorescently labeled (method not explicitly detailed)

**Oxygen Scavenging System**
- Not explicitly detailed

### Experimental Protocol

**DNA Preparation**
1. Prepare λ DNA with ss-dsDNA junctions
2. End-label with biotin and digoxigenin
3. Verify junction formation

**Single-Molecule Assay**
1. Tether DNA between optical traps
2. Apply appropriate force (typically 5-10 pN for diffusion)
3. Introduce FANCD2-FANCI complex
4. Monitor binding, diffusion, and stalling at junctions

**Data Acquisition**
1. Track FANCD2-FANCI movement along DNA
2. Identify stalling events at ss-dsDNA junctions
3. Classify stalls as persistent or transient
4. Calculate diffusion coefficients and dwell times

**Analysis**
1. Diffusion coefficient calculation: Mean ~0.14 ± 0.07 µm²/s
2. Sliding speed: Mean ~0.81 ± 0.14 µm/s
3. Dwell time analysis:
   - Persistent stalls: ~50 seconds or more
   - Transient stalls: ~7 seconds
4. Junction recognition: KR helix engagement analysis

### Results - Typical Data

**Force-Extension Measurements**
- DNA with junctions: Modified behavior at ss-dsDNA boundaries
- Protein binding: Force changes upon FANCD2-FANCI binding

**Key Findings**
- Sliding clamp behavior: D2-I forms clamp around dsDNA and diffuses along it
- Mean diffusion coefficient: ~0.14 ± 0.07 µm²/s on λ-DNA
- Mean sliding speed: ~0.81 ± 0.14 µm/s
- Stalling at junctions: Two types observed:
  - Persistent stalls: Long-lived, essentially immobile (~50+ seconds)
  - Transient stalls: Shorter duration (~7 seconds), then diffusion away
- Junction recognition: KR helix in FANCD2 critical for recognizing ss/ds boundary
- Monoubiquitination: Does not significantly alter diffusion speed or residence times on dsDNA
- Structural insights: Cryo-EM shows distinct conformations for sliding vs junction-bound states

**Imaging Data**
- Single-molecule tracking: Trajectories of FANCD2-FANCI along DNA
- Junction stalling: Direct visualization of stalling events
- Temporal resolution: Sufficient to resolve diffusion and stalling dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Features

**Advantages**
- Direct visualization of DNA scanning and junction recognition
- Single-molecule resolution for diffusion analysis
- Ability to distinguish persistent vs transient stalls
- Combined structural (cryo-EM) and dynamic (single-molecule) data
- Can test effects of modifications (ubiquitination, phosphorylation)

**Limitations**
- Requires purified FANCD2-FANCI complex
- Limited to in vitro conditions
- Junction generation method not fully detailed

**Applications Demonstrated**
- Fanconi Anemia pathway mechanisms
- DNA repair initiation
- Junction recognition mechanisms
- Protein diffusion on DNA
- Stalled replication fork protection

---

## STUDY 8: Dekker et al. 2023 (LUMICKS C-Trap) - Chromatin Replication Origins

### Citation
Dekker, N., Diffley, J.F.X., et al. (2023). A chromatinized origin reduces the mobility of ORC and MCM through interactions and spatial constraint. Nature Communications, 14, Article number: [to be confirmed]. DOI: 10.1038/s41467-023-42524-8

### Constructs - DNA with Replication Origins and Nucleosomes

**Base Substrate**
- Template: Long DNA molecules (10.4 kbp) containing ARS1 (yeast replication origin)
- Nucleosome positioning: Flanking nucleosome positioning sites
- Configuration: Chromatinized or bare (nucleosome-free) origins

**Origin Design**
- ARS1: Yeast replication origin consensus sequence
- Flanking regions: Nucleosome positioning sites
- Chromatinization: Salt gradient dialysis for nucleosome assembly

**Nucleosome Assembly**
- Method: Salt gradient dialysis
- Histone octamers: Purified yeast histone octamers
- Labeling: Fluorescently labeled histones (e.g. H2A-Cy3) for visualization
- Density: Regularly spaced nucleosomes with nucleosome-free regions (NFRs) at ARS consensus sites

**Handles**
- Total length: 10.4 kbp DNA molecules
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Not explicitly stated (typically 5-10 pN for binding/diffusion studies)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths:
  - Cy3 (for nucleosomes, H2A-Cy3)
  - Other fluorophores for ORC and MCM labeling
- Multi-color imaging for simultaneous detection

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein and nucleosome localization

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)
- Tracking algorithms: For diffusion and binding analysis

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Salt concentrations: Variable (typically 50-150 mM)
- Temperature: Room temperature or physiological (30°C for yeast)

**Protein Components**
- ORC: Origin Recognition Complex
- MCM: Minichromosome Maintenance complex
- Cofactors: Cdt1, Cdc6 (for MCM loading)
- Chromatin remodelers: INO80, ISW1a, ISW2, Chd1 (for nucleosome organization)

**Fluorescent Probes**
- Histones: H2A-Cy3 or other labeled histones
- ORC: Fluorescently labeled
- MCM: Fluorescently labeled
- Detection: Single vs double hexamer stoichiometry

**Nucleotides**
- ATP: For helicase and remodeler activity
- Other NTPs: As needed

### Experimental Protocol

**DNA Preparation**
1. Prepare 10.4 kbp DNA containing ARS1
2. Include flanking nucleosome positioning sites
3. End-label with biotin and digoxigenin

**Chromatin Assembly**
1. Use salt gradient dialysis for nucleosome assembly
2. Assemble regularly spaced nucleosomes with NFRs at ARS sites
3. Verify nucleosome assembly (EMSA or other methods)

**Single-Molecule Assay**
1. Tether DNA/chromatin between optical traps
2. Apply appropriate force (typically 5-10 pN)
3. Introduce ORC and monitor binding
4. Introduce MCM with cofactors (Cdt1, Cdc6)
5. Monitor loading, diffusion, and spatial distribution

**Data Acquisition**
1. Track ORC and MCM binding and diffusion
2. Measure binding efficiency (chromatinized vs bare)
3. Calculate diffusion constants
4. Analyze spatial distributions and confinement
5. Detect single vs double hexamer formation

**Analysis**
1. Binding efficiency: Comparable for chromatinized vs bare origins
2. Mobility: Reduced on chromatinized origins
3. Spatial constraint: MCM confinement near origin on chromatinized DNA
4. Double hexamer formation: Increased near origin in presence of nucleosomes

### Results - Typical Data

**Force-Extension Measurements**
- DNA/chromatin: WLC behavior modified by nucleosomes
- Protein binding: Force changes upon ORC/MCM binding

**Key Findings**
- ORC binding efficiency: Comparable whether origin is chromatinized or bare
- ORC mobility: Significantly reduced on chromatinized origins
- MCM loading: Efficient even when origin is chromatinized
- MCM spatial constraint: Much more constrained on chromatinized DNA, diffusion away from origin severely limited
- Double hexamer formation: More MCM double hexamers formed near origin in presence of nucleosomes
- Nucleosome organization: ORC helps organize nucleosomes around origins via chromatin remodelers
- Chromatin architecture: Not just passive; actively contributes to origin function

**Imaging Data**
- Single-molecule tracking: Trajectories of ORC and MCM
- Spatial distribution: Binding events and confinement analysis
- Temporal resolution: Sufficient to resolve diffusion and binding dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)
- Stoichiometry: Detection of single vs double hexamers

### Key Features

**Advantages**
- Direct visualization of origin licensing in real-time
- Can compare chromatinized vs bare origins
- Combined force and fluorescence readouts
- Single-molecule resolution for diffusion analysis
- Can test effects of chromatin organization

**Limitations**
- Requires purified ORC and MCM complexes
- Limited to in vitro conditions
- Complex multi-protein system

**Applications Demonstrated**
- DNA replication origin licensing
- Chromatin effects on replication initiation
- ORC and MCM dynamics
- Nucleosome organization around origins
- Spatial constraint mechanisms

---

## STUDY 9: Aragon et al. 2023 (LUMICKS C-Trap) - SMC Complexes Chromosome Organization

### Citation
Aragon, L., et al. (2023). New Insights in Chromosome Organization: Single Molecule Analysis of Eukaryotic SMC Complexes. [Webinar/Publication details to be confirmed]

### Constructs - DNA Substrates for SMC Complexes

**Base Substrate**
- Template: Various DNA substrates (dsDNA, ssDNA, hybrid ss-dsDNA)
- Configuration: Tethered DNA for single-molecule analysis
- Length: Variable (likely λ DNA ~48.5 kb for some experiments)

**Substrate Types**
- Double-stranded DNA (dsDNA)
- Single-stranded DNA (ssDNA)
- Hybrid substrates: Segments of ssDNA next to dsDNA (fork-like structures)
- Supercoiled DNA
- Catenated DNA

**Handles**
- Total length: Variable
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual or quadruple optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual or multiple traps
- Force range: Variable (typically 5-20 pN)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths: Not explicitly detailed (likely for SMC complex labeling)
- Multi-color imaging for simultaneous detection

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein localization

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Salt concentrations: Variable (typically 50-150 mM)
- Temperature: Room temperature or physiological

**Protein Components**
- Yeast cohesin: Purified complex
- Human Smc5/6: Purified complex
- Condensin: Purified complex (inferred)
- Fluorescent labeling: SMC complexes labeled for visualization

**Fluorescent Probes**
- SMC complexes: Fluorescently labeled (method not explicitly detailed)

**Nucleotides**
- ATP: For SMC complex activity
- ATPγS: Non-hydrolysable analog for testing ATP binding effects

### Experimental Protocol

**DNA Preparation**
1. Prepare DNA substrates (dsDNA, ssDNA, hybrid)
2. End-label with biotin and digoxigenin
3. Verify substrate integrity

**Single-Molecule Assay**
1. Tether DNA between optical traps
2. Apply appropriate force (typically 5-20 pN)
3. Introduce SMC complexes (cohesin, Smc5/6, condensin)
4. Monitor binding, mobility, and DNA interactions

**Data Acquisition**
1. Track SMC complex binding and movement
2. Measure binding kinetics and mobility
3. Analyze DNA bridging (two independent DNA molecules)
4. Test effects on Topoisomerase IIα decatenation

### Results - Typical Data

**Force-Extension Measurements**
- DNA substrates: WLC behavior modified by SMC binding
- Protein binding: Force changes upon SMC complex binding

**Key Findings**
- Cohesin: Binding behaviors, mobility on different substrates, DNA bridging, loop formation
- Smc5/6: 
  - Distinct mobility on dsDNA vs static binding on ssDNA
  - Binding preference for fork-like structures
  - Importance in replication/repair contexts
- DNA bridging: SMC complexes can bridge two independent DNA molecules
- Topoisomerase IIα: Effects of SMC complexes on decatenation activity
- Force dependence: Binding and activity under various force conditions
- ATP requirements: ATP-dependent vs ATP-independent behaviors

**Imaging Data**
- Single-molecule tracking: Trajectories of SMC complexes
- Binding localization: Where complexes bind on DNA
- Temporal resolution: Sufficient to resolve binding and movement dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Features

**Advantages**
- Direct visualization of SMC complex behavior
- Can test different DNA substrates (dsDNA, ssDNA, hybrid)
- Combined force and fluorescence readouts
- Can study DNA bridging and loop formation
- Can test effects on other enzymes (Topoisomerase IIα)

**Limitations**
- Requires purified SMC complexes
- Limited to in vitro conditions
- Complex multi-protein systems

**Applications Demonstrated**
- Chromosome organization mechanisms
- SMC complex DNA binding and mobility
- DNA bridging and loop formation
- Replication and repair contexts
- Topological DNA management

---

## STUDY 10: Banerjee et al. 2022 (LUMICKS C-Trap) - FUS Phase Separation and ALS

### Citation
Banerjee, P., et al. (2022). Decoding the onset of Amyotrophic Lateral Sclerosis (ALS): Liquid-liquid phase transition of Intrinsically Disordered Proteins. [Webinar/Publication details to be confirmed]

### Constructs - Protein Droplets and DNA

**Base Substrate**
- Template: Lambda DNA (λ DNA) for co-condensation studies
- Protein: FUS (Fused in Sarcoma) protein
- Configuration: Protein droplets or DNA-protein co-condensates

**Droplet Formation**
- Method: Liquid-liquid phase separation (LLPS)
- FUS protein: With or without RNA
- Conditions: Variable salt, crowding agents (PEG)

**DNA Co-condensation**
- Method: FUS adsorption onto DNA followed by collapse
- DNA state: Single-stranded (ssDNA) or double-stranded (dsDNA)
- Force conditions: Stretching (ssDNA) or relaxed (dsDNA)

**Handles**
- For DNA studies: λ DNA with biotinylated ends
- Attachment: Biotinylated ends bind to streptavidin beads

**Beads**
- Type: Streptavidin-coated beads (for DNA studies)
- Size: Typical ~2-4.5 μm for C-Trap
- For droplet manipulation: Functionalized beads for droplet trapping

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (for droplet manipulation and DNA stretching)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths:
  - For FUS labeling (method not explicitly detailed)
  - For DNA visualization if needed
- FRAP (Fluorescence Recovery After Photobleaching): For internal mobility measurements

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for droplet and protein visualization

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Low crowding: Low concentration of inert crowders (e.g. low PEG)
- High crowding: Higher PEG concentrations
- Salt concentrations: Variable (low salt, intermediate salt, high salt for reentrant phase separation)
- Temperature: Room temperature

**Protein Components**
- FUS: Wild-type and ALS-associated mutants
- Variants: Phosphorylation states, mutations (e.g. P525L)
- RNA: For FUS-RNA condensates

**Fluorescent Probes**
- FUS: Fluorescently labeled (method not explicitly detailed)
- DNA: Intercalating dyes if needed

**Crowding Agents**
- PEG: Polyethylene glycol at various concentrations

### Experimental Protocol

**Droplet Formation**
1. Prepare FUS protein (with or without RNA)
2. Adjust buffer conditions (salt, crowding)
3. Allow phase separation to form droplets

**Optical Tweezers Assays**
1. Trap and manipulate droplets using optical tweezers
2. Push droplets together to test fusion behavior
3. Measure fusion times and resistance
4. Perform FRAP: Photobleach region, measure recovery time

**DNA Co-condensation Assays**
1. Tether λ DNA between optical traps
2. Apply force (stretching for ssDNA, relaxed for dsDNA)
3. Introduce FUS protein
4. Monitor FUS adsorption and co-condensate formation

**Data Acquisition**
1. Droplet fusion: Time to fusion, resistance to fusion
2. FRAP: Recovery time for internal mobility
3. DNA co-condensation: Force-extension behavior, condensate formation

### Results - Typical Data

**Droplet Fusion Measurements**
- Low crowding: Droplets behave like liquids, fuse easily
- High crowding: Droplets become gelatinous, resist fusion

**FRAP Measurements**
- Low crowding: Fast recovery (high internal fluidity)
- High crowding: Dramatically slower recovery (gel-like or viscoelastic behavior)

**DNA Co-condensation**
- FUS adsorption: Forms "sticky polymer" on DNA
- Collapse: Reversible co-condensate formation
- Force dependence: Behavior under stretching vs relaxed conditions

**Key Findings**
- Material states: Crowding tunes liquid-like vs gel-like behavior
- Surface gelation: Gelation begins at droplet-dilute phase interface
- Phosphorylation: Reduces liquid-to-solid transition
- Reentrant phase separation: Phase separates at low salt, dissolves at intermediate salt, re-phase separates at high salt
- ALS mutations: Altered phase behavior and aggregation propensity

**Imaging Data**
- Droplet visualization: Size, shape, fusion behavior
- FRAP: Internal mobility measurements
- Temporal resolution: Sufficient to resolve fusion and recovery dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Features

**Advantages**
- Direct measurement of droplet material properties
- Can test effects of crowding, salt, mutations
- Combined force and fluorescence readouts
- Can study DNA-protein co-condensation
- Relevant for understanding ALS pathology

**Limitations**
- Requires purified FUS protein
- Limited to in vitro conditions
- Complex phase behavior

**Applications Demonstrated**
- ALS pathology mechanisms
- Phase separation physics
- Protein aggregation
- DNA-protein co-condensation
- Material properties of biomolecular condensates

---

## STUDY 11: Tessmer et al. 2020 (LUMICKS C-Trap) - ATL and NER

### Citation
Rill, N., Mukhortava, A., Lorenz, C., Tessmer, I., et al. (2020). Alkyltransferase-like protein clusters scan DNA rapidly over long distances and recruit NER to alkyl-DNA lesions. PNAS, [Volume and pages to be confirmed]. DOI: [to be confirmed]

### Constructs - DNA with Alkyl Lesions

**Base Substrate**
- Template: DNA with alkylated guanine lesions (e.g. O6-alkyl-G)
- Configuration: Tethered DNA for single-molecule analysis
- Length: Variable (likely λ DNA for some experiments)

**Lesion Types**
- O6-alkylguanine: Alkylated guanine lesions
- Other alkyl lesions: As needed for specific studies

**Handles**
- Total length: Variable
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Atomic force microscopy (AFM) integration (inferred)
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (typically 5-10 pN for diffusion studies)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Atomic force microscopy: For structural analysis
- Laser wavelengths: Not explicitly detailed (likely for ATL and UvrA labeling)

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein localization and tracking

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)
- Tracking algorithms: For diffusion coefficient calculation

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Salt concentrations: Not explicitly detailed
- Temperature: Room temperature or 37°C

**Protein Components**
- ATL: Alkyltransferase-like protein (monomeric and oligomeric forms)
- UvrA: Damage recognition protein in NER
- ATL-UvrA complex: Co-translocating complex

**Fluorescent Probes**
- ATL: Fluorescently labeled (method not explicitly detailed)
- UvrA: Fluorescently labeled (method not explicitly detailed)

**Oxygen Scavenging System**
- Not explicitly detailed

### Experimental Protocol

**DNA Preparation**
1. Prepare DNA with alkylated guanine lesions (e.g. O6-alkyl-G)
2. End-label with biotin and digoxigenin
3. Verify lesion incorporation

**Single-Molecule Assay**
1. Tether DNA between optical traps
2. Apply appropriate force (typically 5-10 pN for diffusion)
3. Introduce ATL (monomer or oligomer)
4. Monitor binding, diffusion, and lesion recognition
5. Introduce UvrA and monitor recruitment

**Data Acquisition**
1. Track ATL movement along DNA (sliding/diffusion)
2. Identify lesion recognition events (cluster dissociation, monomer binding)
3. Monitor ATL-UvrA complex formation and co-translocation
4. Measure binding lifetimes and diffusion coefficients

**Analysis**
1. Diffusion analysis: Rapid bidirectional sliding along DNA
2. Lesion recognition: Cluster dissociation, monomer binding, DNA distortion
3. UvrA recruitment: ATL-UvrA complex formation and stabilization at lesions

### Results - Typical Data

**Force-Extension Measurements**
- DNA with lesions: Modified behavior at lesion sites
- Protein binding: Force changes upon ATL/UvrA binding

**Key Findings**
- ATL forms: Both monomeric and oligomeric complexes on DNA
- Oligomeric clusters: Rapidly diffuse (slide) bidirectionally along undamaged DNA
- Lesion recognition: Upon encountering alkylated guanine, cluster dissociates, leaving monomeric ATL bound
- DNA distortion: Stronger distortion at lesions, target base stabilized in binding pocket
- UvrA recruitment: ATL directly interacts with UvrA, forms ATL-UvrA complex
- Co-translocation: ATL-UvrA complex slides along DNA until stabilizing at lesion
- Mechanism: ATL helps convert subtle lesions into more recognizable damaged DNA for NER

**Imaging Data**
- Single-molecule tracking: Trajectories of ATL and ATL-UvrA complexes
- Lesion recognition: Direct visualization of cluster dissociation and monomer binding
- Temporal resolution: Sufficient to resolve diffusion and binding dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)
- AFM: Structural analysis of DNA distortion

### Key Features

**Advantages**
- Direct visualization of DNA damage search and recognition
- Single-molecule resolution for diffusion analysis
- Can study both ATL and UvrA dynamics
- Combined structural (AFM) and dynamic (single-molecule) data
- Relevant for understanding NER mechanisms

**Limitations**
- Requires purified ATL and UvrA
- Limited to in vitro conditions
- Complex multi-protein system

**Applications Demonstrated**
- Nucleotide excision repair mechanisms
- DNA damage recognition
- Protein-DNA scanning mechanisms
- Lesion-specific repair pathways
- Cancer prevention (alkylating agent damage)

---

## STUDY 12: Moreno-Herrero et al. 2022 (LUMICKS C-Trap) - ParABS and SMC Bacterial Chromosome Segregation

### Citation
Moreno-Herrero, F., et al. (2022). Insights into Bacterial DNA Condensation and chromosome organization. [Webinar/Publication details to be confirmed]

### Constructs - DNA with parS Sites

**Base Substrate**
- Template: DNA containing parS sites (specific DNA sequences near origin of replication)
- Configuration: Tethered DNA for single-molecule analysis
- Length: Variable

**parS Sites**
- Specific DNA sequences: Near origin of replication
- ParB binding: Nucleates on parS sites
- CTP binding: ParB binds CTP, forms clamp

**Handles**
- Total length: Variable
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (typically 5-10 pN)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths: Not explicitly detailed (likely for ParB and SMC labeling)
- Single-molecule tracking for dynamics

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein localization

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Salt concentrations: Variable
- Temperature: Room temperature or physiological (37°C for bacteria)

**Protein Components**
- ParB: DNA-binding protein that nucleates on parS
- CTP: Cytidine triphosphate (binds to ParB)
- SMC-ScpAB: Bacterial condensin complex
- ParA: ATPase for segrosome movement

**Fluorescent Probes**
- ParB: Fluorescently labeled (method not explicitly detailed)
- SMC: Fluorescently labeled (method not explicitly detailed)

**Nucleotides**
- CTP: For ParB clamp formation
- ATP: For ParA and SMC activity

### Experimental Protocol

**DNA Preparation**
1. Prepare DNA containing parS sites
2. End-label with biotin and digoxigenin
3. Verify parS site integrity

**Single-Molecule Assay**
1. Tether DNA between optical traps
2. Apply appropriate force (typically 5-10 pN)
3. Introduce ParB with CTP
4. Monitor ParB binding, spreading, and segrosome formation
5. Introduce SMC and monitor recruitment and activity

**Data Acquisition**
1. Track ParB binding and spreading from parS sites
2. Monitor CTP binding and hydrolysis
3. Measure SMC recruitment and DNA compaction
4. Analyze interactions between ParB and SMC

### Results - Typical Data

**Force-Extension Measurements**
- DNA with ParB: Modified behavior upon ParB binding and spreading
- SMC compaction: DNA compaction under SMC activity

**Key Findings**
- ParB binding: Nucleates on parS sites, binds CTP, forms clamp
- ParB spreading: Spreads over DNA, creating large nucleoprotein complex (segrosome)
- CTP binding and hydrolysis: Critical for ParB clamp formation and dynamics
- SMC recruitment: Recruited to DNA via ParB-parS complexes
- SMC compaction: Helps with chromosome compaction and alignment
- Positive feedback: SMC has positive feedback on ParB complex stability
- Without SMC: ParB complexes less stable, spread less, shorter lifetimes

**Imaging Data**
- Single-molecule tracking: Trajectories of ParB and SMC
- Segrosome formation: Visualization of ParB spreading
- Temporal resolution: Sufficient to resolve binding and spreading dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Features

**Advantages**
- Direct visualization of bacterial chromosome organization
- Can study ParB spreading and SMC recruitment
- Combined force and fluorescence readouts
- Relevant for understanding bacterial chromosome segregation

**Limitations**
- Requires purified ParB and SMC complexes
- Limited to in vitro conditions
- Complex multi-protein system

**Applications Demonstrated**
- Bacterial chromosome segregation
- ParABS partitioning system
- SMC complex function in bacteria
- Origin of replication organization
- Chromosome compaction mechanisms

---

## STUDY 13: Montoya et al. 2021 (LUMICKS C-Trap) - Cas12a Gene Editing

### Citation
Paul, B., Chaubet, L., Verver, D.E., & Montoya, G. (2021). Mechanics of CRISPR-Cas12a and engineered variants on λ-DNA. Nucleic Acids Research, 50(9), 5208-5224. DOI: 10.1093/nar/gkac348

### Constructs - Lambda DNA with Target Sites

**Base Substrate**
- Template: Lambda DNA (λ DNA), ~48.5 kb
- Target sites: Specific PAM sequences and target sequences
- Configuration: Tethered between beads for single-molecule analysis

**Target Design**
- PAM sequences: Required for Cas12a recognition
- Target sequences: Complementary to crRNA
- Off-target sites: Partial matches also studied

**Handles**
- Total length: ~48.5 kb λ DNA
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range:
  - Low force: ~10 pN (for binding studies)
  - High force: ~50 pN (for some mutant studies)
  - Cleavage: ≤5 pN (required for cleavage)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths:
  - Cy5 (for crRNA labeling)
  - Other fluorophores as needed
- Single-molecule tracking for binding localization

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for RNP localization
- Cleavage detection: Tether breakage under tension

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Mg²⁺: Required for catalysis (present for cleavage, absent for binding-only studies)
- Salt concentrations: Variable
- Temperature: Room temperature or 37°C

**Protein Components**
- Cas12a: Wild-type and engineered variants
- Variants tested:
  - Cas12a_M1 (REC-Sub mutant): Altered non-specific ssDNA cleavage
  - Cas12a_M2 (Q1025G/E1028G): Eliminated indiscriminate ssDNA cleavage
  - Cas12a_M3 (K1013G/R1014G): Nickase (single-strand cutting)
  - Cas12a_KO: Catalytically dead control

**RNA Components**
- crRNA: Guide RNA labeled with Cy5
- crRNA-1: Specific crRNA sequence used

**Fluorescent Probes**
- crRNA: Cy5-labeled
- Cas12a: May be labeled (method not explicitly detailed)

**Nucleotides**
- Not required for binding
- Mg²⁺: Required for cleavage activity

### Experimental Protocol

**DNA Preparation**
1. Prepare λ DNA with target sites
2. End-label with biotin and digoxigenin
3. Verify target site integrity

**RNP Assembly**
1. Prepare Cas12a-crRNA RNP complex
2. Label crRNA with Cy5
3. Verify RNP formation

**Single-Molecule Assay**
1. Tether λ DNA between optical traps
2. Apply force (~10 pN for binding studies)
3. Introduce Cas12a-crRNA RNP complex
4. Monitor binding via fluorescence
5. Test cleavage: Apply force ≤5 pN, monitor tether breakage
6. Test at different forces: Low (≤5 pN) vs high (~50 pN)

**Data Acquisition**
1. Track RNP binding along DNA (fluorescence)
2. Identify target vs off-target binding sites
3. Monitor cleavage events (tether breakage)
4. Measure binding lifetimes and cleavage efficiency
5. Test engineered variants under same conditions

### Results - Typical Data

**Force-Extension Measurements**
- DNA with bound RNP: Modified behavior upon binding
- Cleavage: Tether breakage indicates double-strand break (DSB)

**Key Findings**
- Binding: At low forces (~10 pN), wt Cas12a binds target site and two major off-target sites
- High force binding: At higher forces, many additional off-target binding events (mechanical distortions facilitate partial matching)
- Cleavage: Occurs only at low forces (≤5 pN), not at high force
- Force requirement: DNA flexibility required for conformational transitions leading to cleavage
- Off-target cleavage: Despite off-target binding, actual cleavage occurs only at unique target site
- Engineered variants:
  - M1: Altered non-specific ssDNA cleavage, similar dsDNA cleavage to wt
  - M2: Eliminated indiscriminate ssDNA cleavage, DSBs only at high forces (~50 pN)
  - M3: Nickase (primarily cuts one strand)
- Search mode: 1-dimensional hopping along DNA and diffusive contacts

**Imaging Data**
- Single-molecule tracking: RNP localization along DNA
- Binding sites: Target and off-target sites identified
- Temporal resolution: Sufficient to resolve binding and cleavage dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Features

**Advantages**
- Direct visualization of Cas12a binding and cleavage
- Can test effects of force on activity
- Can compare wild-type vs engineered variants
- Combined force and fluorescence readouts
- Relevant for improving gene editing specificity

**Limitations**
- Requires purified Cas12a and crRNA
- Limited to in vitro conditions
- Complex RNP system

**Applications Demonstrated**
- CRISPR-Cas12a mechanism
- Off-target binding and cleavage
- Force-dependent activity
- Engineered variant design
- Gene editing safety and specificity

---

## STUDY 14: Van Houten et al. 2023 (LUMICKS C-Trap) - Nuclear Extracts DNA Repair

### Citation
Van Houten, B., et al. (2023). Single-molecule analysis of cancer DNA-protein interactions from nuclear extracts. [Webinar/Publication details to be confirmed]

### Constructs - DNA Substrates for Repair Proteins

**Base Substrate**
- Template: Lambda DNA (λ DNA), ~48.5 kb
- Damage types: Undamaged, nicked, damaged bases (e.g. oxidative damage), nucleosome-wrapped
- Configuration: Tethered between beads for single-molecule analysis

**Substrate Types**
- Undamaged DNA
- Nicked DNA
- Oxidatively damaged DNA (e.g. 8-oxoguanine)
- Nucleosome-wrapped DNA
- Other damage types as needed

**Handles**
- Total length: ~48.5 kb λ DNA
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (typically 5-10 pN)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths:
  - GFP (for GFP-tagged proteins)
  - HaloTag ligands (for HaloTag-tagged proteins)
  - Other fluorophores as needed
- Kymograph generation: Position vs time trajectories

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching
- Channel usage: For introducing nuclear extracts and buffer exchange

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein localization and tracking

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)
- Custom analysis scripts: For kinetic parameter extraction

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Salt concentrations: Variable
- Temperature: Room temperature or 37°C

**Nuclear Extracts**
- Source: Cells transfected with fluorescently tagged protein
- Protein expression: Overexpression of tagged protein
- Endogenous proteins: Present in extracts (cofactors, modifications, interacting partners)
- Comparison conditions:
  1. Purified protein (isolated)
  2. Purified protein spiked into nuclear extracts
  3. Protein expressed in cells, extract used directly (SMADNE approach)

**Protein Components**
- OGG1: 8-oxoguanine DNA glycosylase 1 (GFP-tagged)
- PARP1: Poly(ADP-ribose) polymerase 1
- DNA ligase III/XRCC1: At nicks
- TDG: Thymine DNA glycosylase
- UV-DDB: Ultraviolet damage DNA binding protein
- Cancer variants: Mutant proteins from cancer cells

**Fluorescent Probes**
- GFP: For GFP-tagged proteins
- HaloTag ligands: For HaloTag-tagged proteins
- Other tags: As needed

### Experimental Protocol

**Cell Preparation**
1. Transfect cells with fluorescently tagged protein (GFP, HaloTag, etc.)
2. Prepare nuclear extracts from transfected cells
3. Verify protein expression and extract quality

**DNA Preparation**
1. Prepare DNA substrates (undamaged, nicked, damaged, nucleosome-wrapped)
2. End-label with biotin and digoxigenin
3. Verify substrate integrity

**Single-Molecule Assay (SMADNE)**
1. Tether λ DNA between optical traps
2. Move to appropriate channel
3. Introduce nuclear extract containing fluorescently tagged protein
4. Monitor binding behavior via fluorescence
5. Collect kymographs (position vs time)

**Data Acquisition**
1. Record binding events (on/off binding)
2. Track protein movement (diffusion modes: sliding/hopping/non-specific)
3. Measure binding lifetimes
4. Calculate diffusion coefficients
5. Map positional information

**Analysis**
1. Extract kinetic parameters: Binding durations, frequencies
2. Classify diffusion modes: Sliding, hopping, non-specific binding
3. Compare: Purified vs extract conditions
4. Test cancer variants: Compare to wild-type

### Results - Typical Data

**Force-Extension Measurements**
- DNA with bound proteins: Modified behavior upon binding
- Damage recognition: Force changes at damage sites

**Key Findings - OGG1 Example**
- Undamaged DNA:
  - Purified OGG1: Weighted average binding lifetime ≈ 5.7 seconds, ~21% show diffusion
  - Nuclear extracts: OGG1 binds much less efficiently
- Damaged DNA (oxidative damage):
  - Binding lifetimes more similar across conditions
  - ~2.2 s in nuclear extracts vs ~7.8 s in purified protein (wild-type)
  - Catalytically dead mutant (K249Q): ~15.4 s in extracts vs ~10.7 s when purified
  - Suggests catalytic activity plays role in dissociation kinetics
- Other proteins: PARP1, DNA ligase III/XRCC1, TDG, UV-DDB also studied

**Imaging Data**
- Kymographs: Position vs time trajectories
- Binding events: On/off binding visualized
- Diffusion: Sliding/hopping modes identified
- Temporal resolution: Sufficient to resolve binding and movement dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Features

**Advantages**
- Native context: Nuclear extracts contain endogenous proteins, cofactors, modifications
- Real-time single-molecule resolution
- Can test cancer variants directly from cells
- Comparison: Purified vs native conditions
- Can study multiple proteins in same system

**Limitations**
- Complex "soup": More background binding, difficult to assign causality
- Overexpression: Non-physiological levels may alter dynamics
- Requires specialized instrumentation (C-Trap)
- Careful DNA substrate preparation needed

**Applications Demonstrated**
- DNA repair protein dynamics
- Cancer-associated mutations
- Native vs purified protein behavior
- Chromatin effects on repair
- Base excision repair mechanisms
- Nucleotide excision repair mechanisms

---

---

## STUDY 15: Pangeni et al. 2024 (LUMICKS C-Trap) - RPA Migration on ssDNA

### Citation
Pangeni, S., Biswas, G., Kaushik, V., Kuppa, S., Yang, O., Lin, C-T., Mishra, G., Levy, Y., Antony, E., & Ha, T. (2024). Rapid Long-distance Migration of RPA on Single Stranded DNA Occurs Through Intersegmental Transfer Utilizing Multivalent Interactions. Journal of Molecular Biology, 436(6), 168491. DOI: [to be confirmed]

### Constructs - Single-Stranded DNA

**Base Substrate**
- Template: Lambda DNA (λ DNA), ~48.5 kb, denatured to single-stranded DNA
- Configuration: Tethered between beads for single-molecule analysis
- State: Single-stranded DNA (ssDNA)

**Handles**
- Total length: ~48.5 kb λ DNA (denatured)
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range:
  - Low force: 3 pN (for high diffusion studies)
  - Variable: Tested at different tensions
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths: Not explicitly detailed (likely for RPA labeling on different domains)
- Single-molecule tracking for diffusion analysis

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for RPA localization and tracking

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)
- Tracking algorithms: For diffusion coefficient and jump size calculation

### Experimental Conditions

**Buffer Conditions**
- Salt concentrations: Variable (100 mM KCl for high diffusion, higher salt for reduced mobility)
- Temperature: Room temperature or physiological

**Protein Components**
- RPA: Saccharomyces cerevisiae RPA (yeast RPA, yRPA)
- Variants:
  - Full-length RPA
  - Trimeric core deletion (increased mobility)
- Labeling: Fluorescently labeled on different domains

**Fluorescent Probes**
- RPA: Fluorescently labeled (method not explicitly detailed, labeled on different domains)

**Crowding Conditions**
- Unlabeled RPA: Up to 100-fold excess for crowding studies

### Experimental Protocol

**DNA Preparation**
1. Prepare λ DNA (~48.5 kb)
2. Denature to single-stranded DNA
3. End-label with biotin and digoxigenin
4. Verify ssDNA state

**Single-Molecule Assay**
1. Tether ssDNA between optical traps
2. Apply force (3 pN for high diffusion, variable for force dependence)
3. Introduce fluorescently labeled RPA
4. Monitor RPA binding and movement via fluorescence
5. Track trajectories and calculate diffusion coefficients

**Data Acquisition**
1. Track RPA movement along ssDNA
2. Calculate diffusion coefficients (D)
3. Measure jump sizes (Δnt) for intersegmental transfer
4. Test force dependence: Different tensions
5. Test salt dependence: Different KCl concentrations
6. Test crowding: With excess unlabeled RPA

**Analysis**
1. Diffusion coefficient: Up to ~20,000 nucleotides²/sec at 3 pN, 100 mM KCl
2. Jump size distribution: Wide range, decreases with increasing force
3. Force dependence: Diffusion slows with increasing tension
4. Salt dependence: Higher salt reduces mobility, increases binding site size
5. Crowding effects: Mobility drops sharply with excess RPA

### Results - Typical Data

**Force-Extension Measurements**
- ssDNA: Extended behavior under tension
- RPA binding: Modified behavior upon binding

**Key Findings**
- High diffusion: Diffusion coefficient up to ~20,000 nt²/sec at 3 pN, 100 mM KCl
- Mechanism: Intersegmental transfer via multivalent interactions
- Jump sizes: Wide distribution, large jumps become rarer with increasing force
- Force effect: Increasing force stretches ssDNA, prevents loop formation, reduces diffusion
- Salt effect: Higher KCl strengthens interactions, increases binding site size (22-nt to 30-nt occlusion), reduces mobility
- Trimeric core: Deletion increases mobility ~15-fold
- Crowding: With 100-fold excess unlabeled RPA, D drops from ~13,000 to ~900 nt²/s

**Imaging Data**
- Single-molecule tracking: Trajectories of RPA along ssDNA
- Jump detection: Intersegmental transfer events identified
- Temporal resolution: Sufficient to resolve diffusion and jump dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Citations

**Methodological References**
- Optical tweezers and fluorescence microscopy methods for single-molecule studies
- RPA purification and labeling protocols
- Single-molecule tracking and analysis methods

### Key Features

**Advantages**
- Direct visualization of RPA diffusion mechanism
- Can test effects of force, salt, and crowding
- Single-molecule resolution for jump size analysis
- Combined force and fluorescence readouts
- Relevant for understanding DNA replication and repair

**Limitations**
- Requires purified RPA
- Limited to in vitro conditions
- Complex analysis of jump distributions

**Applications Demonstrated**
- RPA dynamics on ssDNA
- Intersegmental transfer mechanisms
- Multivalent protein-DNA interactions
- DNA replication and repair contexts
- Force and salt modulation of protein mobility

---

## STUDY 16: Fazio et al. 2024 (LUMICKS C-Trap) - RecBCD Helicase Regulation

### Citation
Fazio, N., Mersch, J., Hao, Y., & Lohman, T.M. (2024). E. coli RecB Nuclease Domain Regulates RecBCD Helicase Activity but not Single Stranded DNA Translocase Activity. Journal of Molecular Biology, [Volume and pages to be confirmed]. DOI: [to be confirmed]

### Constructs - Double-Stranded DNA

**Base Substrate**
- Template: Long DNA (~20 kbp) for single-molecule studies
- Configuration: Tethered between beads for single-molecule analysis
- State: Double-stranded DNA (dsDNA) with blunt ends or other configurations

**Handles**
- Total length: ~20 kbp DNA
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy (inferred)
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (for unwinding studies)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging (inferred)
- Laser wavelengths: Not explicitly detailed

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Salt concentrations: Variable
- Temperature: Room temperature or 37°C

**Protein Components**
- RecBCD: Wild-type E. coli RecBCD helicase
- Variants:
  - RecB^ΔNuc CD: Nuclease domain deletion
  - RecB^D1080A CD: Nuclease-dead mutant (retains domain structure)

**Nucleotides**
- ATP: For helicase activity

### Experimental Protocol

**DNA Preparation**
1. Prepare long DNA (~20 kbp) with blunt ends or other configurations
2. End-label with biotin and digoxigenin
3. Verify DNA integrity

**Single-Molecule Assay**
1. Tether DNA between optical traps
2. Apply appropriate force
3. Introduce RecBCD (wild-type or variant)
4. Monitor unwinding via force-extension measurements
5. Track pausing behavior

**Additional Methods**
- Stopped-flow fluorescence: For translocation and unwinding kinetics
- Cryo-EM: For structural analysis of DNA binding
- Thermodynamic binding: For base pair melting measurements

**Data Acquisition**
1. Track unwinding rates
2. Measure translocation rates along ssDNA
3. Identify pausing events
4. Compare wild-type vs variants

### Results - Typical Data

**Force-Extension Measurements**
- DNA unwinding: Extension changes during unwinding
- Pausing: Pause events detected

**Key Findings**
- Nuclease domain deletion: Slows unwinding by ~25-45%, but translocation rate unchanged
- Base pair melting: RecB^ΔNuc CD melts ~4 bp vs ~11 bp in wild-type (ATP-independent)
- Initiation: Slower initiation from blunt ends without nuclease domain
- Pausing: Significant pausing even without chi sequences
- Nuclease-dead mutant: Similar to wild-type (structure, not activity, is important)
- Mechanism: Nuclease domain allosterically influences base pair melting, not translocation

**Imaging Data**
- Cryo-EM: Structural analysis of DNA binding and base pair melting
- Temporal resolution: Sufficient to resolve unwinding and pausing dynamics

### Key Citations

**Methodological References**
- Optical tweezers methods for helicase studies
- Stopped-flow fluorescence techniques
- Cryo-EM methods for DNA-protein complexes
- RecBCD purification and characterization

### Key Features

**Advantages**
- Direct measurement of unwinding vs translocation
- Can test effects of domain deletions
- Combined structural (cryo-EM) and dynamic (single-molecule) data
- Relevant for understanding helicase mechanisms

**Limitations**
- Requires purified RecBCD variants
- Limited to in vitro conditions
- Complex multi-subunit system

**Applications Demonstrated**
- Helicase mechanism
- Domain function in multi-domain proteins
- DNA repair pathways
- Base pair melting mechanisms

---

## STUDY 17: Li et al. 2025 (LUMICKS C-Trap) - NDF-FACT Transcription Condensates

### Citation
Li, Z., Burgos-Bravo, F., et al. (2025). Phase-separated NDF-FACT condensates facilitate transcription elongation on chromatin. Nature Cell Biology, [Volume and pages to be confirmed]. DOI: 10.1038/s41556-025-01778-8

### Constructs - Chromatin Templates

**Base Substrate**
- Template: DNA with nucleosomes
- Configuration: Tethered between beads for single-molecule analysis
- State: Chromatinized DNA with nucleosomes

**Nucleosome Assembly**
- Method: Standard nucleosome reconstitution
- Histone modifications: H3K36me3 (for NDF binding via PWWP domain)

**Handles**
- Total length: Variable
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (for transcription studies)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths: Not explicitly detailed (likely for NDF, FACT, Pol II labeling)

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for condensate and protein localization

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Physiological salt conditions: For condensate formation
- Temperature: Room temperature or physiological

**Protein Components**
- NDF: Nucleosome-destabilizing factor (Glyr1/N-PAC/NP60)
  - N-terminal PWWP domain: Binds H3K36me3
  - C-terminal dehydrogenase-like domain: Contributes to nucleosome destabilization
- FACT complex: Spt16 and SSRP1 subunits
- RNA Pol II: Elongation complexes
- Variants:
  - NDF_K161A, NDF_R162A: Disrupt condensate formation
  - NDF truncations: Reduce catalytic activity but retain condensate formation

**Fluorescent Probes**
- NDF: Fluorescently labeled
- FACT: Fluorescently labeled
- Pol II: Fluorescently labeled or detected

### Experimental Protocol

**Chromatin Preparation**
1. Prepare DNA with nucleosomes
2. Include H3K36me3 modifications
3. Verify nucleosome assembly

**Condensate Formation**
1. Mix NDF and FACT under physiological salt
2. Verify condensate formation (spherical droplets)
3. Test with Pol II elongation complexes

**Single-Molecule Assay**
1. Tether chromatin between optical traps
2. Apply appropriate force
3. Introduce NDF, FACT, and Pol II
4. Monitor condensate formation and association with Pol II
5. Track transcription through nucleosomes

**Data Acquisition**
1. Monitor condensate formation
2. Track condensate association with Pol II
3. Measure transcription efficiency
4. Identify pausing at specific superhelical locations (SHLs)
5. Test variants: K161A, R162A, truncations

### Results - Typical Data

**Force-Extension Measurements**
- Chromatin: Modified behavior with nucleosomes
- Transcription: Extension changes during elongation

**Key Findings**
- Synergy: NDF + FACT together eliminate pausing upstream of SHL-1, ~20-fold enhancement vs FACT alone
- Phase separation: NDF + FACT form condensates under physiological salt, enhanced by Pol II
- Condensate association: Condensates form at Pol II and travel with it through nucleosomes
- Pausing reduction: In condensates, pausing at SHL-5 and SHL-7 reduced
- Histone retention: FACT preserves histones via hexasome-like intermediates
- Mutations: K161A/R162A disrupt condensates, lose synergy
- Truncations: Reduce catalytic activity, fail to enhance transcription despite condensate formation
- In vivo: NDF and Spt16 form nuclear puncta colocalizing with active transcription

**Imaging Data**
- Condensate visualization: Spherical droplets
- Association tracking: Condensates with Pol II
- Temporal resolution: Sufficient to resolve transcription and condensate dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Citations

**Methodological References**
- C-Trap methods for transcription studies
- Phase separation assays
- Chromatin reconstitution methods
- Single-molecule transcription protocols

### Key Features

**Advantages**
- Direct visualization of condensate formation and function
- Can test effects of mutations on phase separation
- Combined force and fluorescence readouts
- Relevant for understanding transcription regulation

**Limitations**
- Requires purified NDF, FACT, and Pol II
- Limited to in vitro conditions
- Complex multi-component system

**Applications Demonstrated**
- Transcription elongation mechanisms
- Phase separation in gene regulation
- Chromatin remodeling during transcription
- FACT complex function
- Nucleosome barrier passage

---

## Notes on Metadata Extraction

This metadata extraction is based on available information from web searches, publications, and LUMICKS knowledge library content. Some details may be incomplete or require access to full publication methods sections and supplementary materials for complete accuracy.

For complete experimental protocols, please refer to:
1. Original publications and their supplementary materials
2. LUMICKS application notes and protocols
3. Direct contact with corresponding authors for specific experimental details

## Key Methodological Citations

### Optical Tweezers and C-Trap Methods

1. **Meijering, A.E.C., Bakx, J.A.M., Man, T., Heller, I., Wuite, G.J.L., & Peterman, E.J.G. (2022).** Implementation of 3D Multi-Color Fluorescence Microscopy in a Quadruple Trap Optical Tweezers System. In *Optical Tweezers: Methods and Protocols* (2nd ed., Vol. 2478, Methods in Molecular Biology), pages 75-100. DOI: 10.1007/978-1-0716-2229-2_5

2. **Belan, O., Moore, G., Kaczmarczyk, A., Newton, M.D., Anand, R., Boulton, S.J., & Rueda, D.S. (2021).** Generation of versatile ss-dsDNA hybrid substrates for single-molecule analysis. STAR Protocols, 2(2): 100588. DOI: 10.1016/j.xpro.2021.100588

3. **Aitken, C.E., Marshall, R.A., & Puglisi, J.D. (2008).** An oxygen scavenging system for improvement of dye stability in single-molecule fluorescence experiments. Biophysical Journal, 94: 1826-1835. DOI: 10.1529/biophysj.107.117689

### DNA Substrate Preparation

4. **King, G.A., Spakman, D., Peterman, E.J.G., & Wuite, G.J.L. (2022).** Principles for generating negatively supercoiled DNA using dual-trap optical tweezers. In *Optical Tweezers: Methods and Protocols* (2nd ed., Vol. 2478, Methods in Molecular Biology), pages 243-272.

5. **Man, T., Geldhof, J.J., Peterman, E.J.G., Wuite, G.J.L., & Heller, I. (2022).** One-Dimensional STED Microscopy in Optical Tweezers. In *Optical Tweezers: Methods and Protocols* (2nd ed., Vol. 2478, Methods in Molecular Biology), pages 101-122. DOI: 10.1007/978-1-0716-2229-2_6

### Single-Molecule Analysis Methods

6. **Heller, I., Hoekstra, T.P., King, G.A., Peterman, E.J.G., & Wuite, G.J.L. (2014).** Optical Tweezers Analysis of DNA-Protein Complexes. Chemical Reviews, 114(6): 3087-3119. DOI: 10.1021/cr4003006

7. **Hashemi Shabestari, M., Meijering, A.E.C., Roos, W.H., Wuite, G.J.L., & Peterman, E.J.G. (2017).** Recent Advances in Biological Single-Molecule Applications of Optical Tweezers and Fluorescence Microscopy. In *Single-Molecule Enzymology: Nanomechanical Manipulation and Hybrid Methods* (Vol. 582, Methods in Enzymology), pages 85-119. DOI: 10.1016/bs.mie.2016.09.047

### Related Single-Molecule Studies

8. **Belan, O., Barroso, C., Kaczmarczyk, A., Anand, R., Federico, S., O'Reilly, N., Newton, M.D., Maeots, E., Enchev, R.I., & Martinez-Perez, E. (2021).** Single-molecule analysis reveals cooperative stimulation of Rad51 filament nucleation and growth by mediator proteins. Molecular Cell, 81: 1058-1073.e7. DOI: 10.1016/j.molcel.2020.12.020

9. **Autour, A., Jeng, S.C.Y., Cawte, A.D., Abdolahzadeh, A., Galli, A., Panchapakesan, S.S.S., Rueda, D., Ryckelynck, M., & Unrau, P.J. (2018).** Fluorogenic RNA Mango aptamers for imaging small non-coding RNAs in mammalian cells. Nature Communications, 9: 656. DOI: 10.1038/s41467-018-02993-8

---

*Note: This citations list focuses on key methodological references. Each study in this document may cite many additional papers. For complete citation lists, please refer to the original publications.*

---

## STUDY 18: Shu Complex et al. 2024 (LUMICKS C-Trap) - Shu Complex RAD51 DNA Repair

### Citation
[Authors to be confirmed] (2024). The human Shu complex promotes RAD51 activity by modulating RPA dynamics on ssDNA. Nature Communications, [Volume and pages to be confirmed]. DOI: 10.1038/s41467-024-51595-0

### Constructs - Single-Stranded DNA with RAD51 Filaments

**Base Substrate**
- Template: Single-stranded DNA (ssDNA)
- Configuration: Tethered between beads for single-molecule analysis
- State: ssDNA with RPA coating

**Handles**
- Total length: Variable
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (for DNA-protein interaction studies)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths: Not explicitly detailed (likely for RAD51, Shu complex, RPA labeling)
- Single-molecule tracking for filament dynamics

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein localization and tracking

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Salt concentrations: Variable
- Temperature: Room temperature or 37°C

**Protein Components**
- Shu complex: Composed of SWSAP1, SWS1, SPIDR, and PDS5B
- RAD51: Recombinase protein
- RPA: Replication protein A
- Variants: SWSAP1 mutants (cancer-associated mutations)

**Fluorescent Probes**
- RAD51: Fluorescently labeled
- Shu complex: Fluorescently labeled
- RPA: Fluorescently labeled

### Experimental Protocol

**DNA Preparation**
1. Prepare ssDNA substrates
2. End-label with biotin and digoxigenin
3. Verify DNA integrity

**Single-Molecule Assay**
1. Tether ssDNA between optical traps
2. Apply appropriate force
3. Introduce RPA to coat ssDNA
4. Introduce RAD51 and monitor filament formation
5. Introduce Shu complex and monitor effects on RAD51 and RPA dynamics

**Data Acquisition**
1. Track RAD51 filament formation and dynamics
2. Monitor RPA diffusion on ssDNA
3. Measure effects of Shu complex on RAD51 activity
4. Test D-loop reactions on RPA-coated ssDNA
5. Test cancer-associated mutations

### Results - Typical Data

**Force-Extension Measurements**
- ssDNA with proteins: Modified behavior upon protein binding
- RAD51 filaments: Force changes upon filament formation

**Key Findings**
- Shu complex function: Heterodimeric complex that decorates RAD51 filaments along their length
- SWSAP1-SWS1 binding: Binds to RAD51 and maintains ssDNA-RAD51 interaction
- RPA dynamics: Shu complex stimulates RPA diffusion on ssDNA
- D-loop reactions: Enables RAD51 D-loop reactions on RPA-coated ssDNA
- Cancer mutations: SWSAP1 mutated in breast, uterine/endometrial, and prostate cancers
- Therapeutic vulnerability: CRISPR/Cas9 knockout cells sensitive to PARP inhibitors (Olaparib) and APE1 inhibition
- Mutations: Certain mutations inhibit Shu complex formation

**Imaging Data**
- Single-molecule tracking: Trajectories of RAD51 filaments and Shu complex
- RPA diffusion: Visualization of RPA dynamics on ssDNA
- Temporal resolution: Sufficient to resolve filament and protein dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Citations

**Methodological References**
- C-Trap methods for RAD51 filament visualization
- RPA dynamics measurement techniques
- Single-molecule DNA repair assays
- Shu complex purification and characterization

### Key Features

**Advantages**
- Direct visualization of large RAD51 filaments
- Can test effects of Shu complex on RAD51 and RPA
- Single-molecule resolution for dynamics analysis
- Combined force and fluorescence readouts
- Relevant for understanding cancer mechanisms

**Limitations**
- Requires purified Shu complex components
- Limited to in vitro conditions
- Complex multi-protein system

**Applications Demonstrated**
- Homologous recombination mechanisms
- RAD51 filament dynamics
- RPA modulation by Shu complex
- Cancer therapeutic targets
- DNA repair pathway regulation

---

## STUDY 19: DNA Polymerase Exchange et al. 2024 (LUMICKS C-Trap) - DNA Polymerase Dynamics

### Citation
[Authors to be confirmed] (2024). Mapping fast DNA polymerase exchange during replication. Nature Communications, [Volume and pages to be confirmed]. DOI: 10.1038/s41467-024-49612-3

### Constructs - DNA Replication Forks

**Base Substrate**
- Template: DNA replication fork substrates
- Configuration: Tethered between beads for single-molecule analysis
- State: Double-stranded DNA with replication fork structures

**Handles**
- Total length: Variable
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (for replication studies)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths: Not explicitly detailed (likely for DNA polymerase labeling)
- Correlative detection: Simultaneous force and fluorescence

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for polymerase localization
- Activity detection: DNA length changes (ssDNA vs dsDNA elasticity)

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA replication
- Salt concentrations: Variable
- Temperature: Room temperature or 37°C

**Protein Components**
- DNA polymerase: T7 bacteriophage DNA polymerase (model system)
- Other replisome components: As needed

**Nucleotides**
- dNTPs: For DNA synthesis
- Other nucleotides: As needed

**Fluorescent Probes**
- DNA polymerase: Fluorescently labeled

### Experimental Protocol

**DNA Preparation**
1. Prepare replication fork substrates
2. End-label with biotin and digoxigenin
3. Verify fork structure

**Single-Molecule Assay**
1. Tether replication fork between optical traps
2. Apply appropriate force
3. Introduce DNA polymerase
4. Monitor replication activity via force-extension (DNA length changes)
5. Track polymerase engagement via fluorescence at junctions

**Data Acquisition**
1. Measure DNA length changes (ssDNA vs dsDNA elasticity)
2. Track polymerase binding/unbinding events
3. Identify catalytic activities: polymerization, exonucleolysis, pause
4. Measure exchange dynamics: Unbinding and rebinding rates
5. Test memory effect: Activity preservation across binding events

**Analysis**
1. Exchange dynamics: Rapid unbinding and rebinding
2. Activity per binding: Each polymerase performs predominantly one catalytic function per binding event
3. Memory effect: Catalytic activity preserved across rebinding events

### Results - Typical Data

**Force-Extension Measurements**
- Replication fork: Modified behavior during replication
- DNA length changes: ssDNA vs dsDNA elasticity changes indicate activity

**Key Findings**
- Rapid exchange: DNA polymerases rapidly unbind and rebind during replication
- Activity per binding: Each polymerase molecule performs predominantly one catalytic function (polymerization, exonucleolysis, or pause) per binding event
- Memory effect: DNA polymerase molecules exhibit memory - catalytic activity preserved across binding events
- Replisome dynamics: Replisomes are highly dynamic with rapidly exchanging components
- Model system: T7 DNA polymerase used to understand replication fidelity

**Imaging Data**
- Correlative detection: Simultaneous force (DNA length) and fluorescence (polymerase position)
- Temporal resolution: Sufficient to resolve rapid exchange dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Citations

**Methodological References**
- Correlative optical tweezers-fluorescence microscopy methods
- DNA replication fork preparation
- Single-molecule replication assays
- T7 DNA polymerase characterization

### Key Features

**Advantages**
- Direct visualization of polymerase exchange dynamics
- Correlative force and fluorescence detection
- Can track individual binding events and activities
- Relevant for understanding replisome dynamics

**Limitations**
- Requires purified DNA polymerase
- Limited to in vitro conditions
- Model system (T7) may differ from eukaryotic systems

**Applications Demonstrated**
- DNA replication mechanisms
- Replisome dynamics
- Polymerase exchange and memory
- Replication fidelity
- Single-molecule enzymology

---

## STUDY 20: Kinetochore Segregation et al. 2024 (LUMICKS C-Trap) - Kinetochore Chromosome Segregation

### Citation
Barford, D., et al. (2024). Kinetochores grip microtubules with directionally asymmetric grip behavior. [Journal and details to be confirmed]

### Constructs - Microtubules and Kinetochore Complexes

**Base Substrate**
- Template: Microtubules
- Configuration: Kinetochore protein complexes reconstituted in vitro
- State: Microtubules with attached kinetochore complexes

**Kinetochore Components**
- Ndc80 complex: Directly binds microtubules
- CENP-A: Histone variant for centromere identification
- DAM1 complex: Forms microtubule-encircling rings
- Aurora B kinase: For error correction and tension sensing

**Handles**
- Microtubule attachment: Via kinetochore complexes
- Bead attachment: Not explicitly detailed (likely via microtubule or kinetochore)

**Beads**
- Type: Not explicitly detailed
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging
  - Cryo-EM integration (for structural analysis)

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (for mechanical stress studies)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- TIRF microscopy: For kinetochore analysis
- Cryo-EM: For structural analysis
- Laser wavelengths: Not explicitly detailed

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal/TIRF scanning for kinetochore localization
- Single-molecule localization: For kinetochore analysis

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for microtubule/kinetochore interactions
- Salt concentrations: Variable
- Temperature: Room temperature or physiological

**Protein Components**
- Kinetochore complexes: Reconstituted from budding yeast
- Microtubules: Purified microtubules
- Components: Ndc80, CENP-A, DAM1, Aurora B kinase

**Fluorescent Probes**
- Kinetochore components: Fluorescently labeled
- Microtubules: May be labeled

### Experimental Protocol

**Kinetochore Reconstitution**
1. Purify kinetochore components from budding yeast
2. Reconstitute kinetochore complexes in vitro
3. Verify complex formation

**Single-Molecule Assay**
1. Attach microtubules to optical traps
2. Attach kinetochore complexes
3. Apply mechanical stress (force)
4. Monitor grip behavior under different force directions
5. Test side-attached vs end-attached configurations

**Data Acquisition**
1. Measure grip strength: Plus end vs minus end pulling
2. Monitor molecular rearrangements in kinetochore subcomplexes
3. Test biorientation mechanisms
4. Analyze attachment stability

**Analysis**
1. Directional asymmetry: Sixfold stronger grip when pulled toward plus ends
2. Molecular rearrangements: Correlate with grip behavior
3. Biorientation: Role in stabilizing correct attachments

### Results - Typical Data

**Force Measurements**
- Grip strength: Directionally asymmetric
- Plus end pulling: Sixfold stronger grip
- Minus end pulling: Weaker grip

**Key Findings**
- Directional grip: Side-attached kinetochores grip sixfold more strongly when pulled toward microtubule plus ends vs minus ends
- Molecular rearrangements: Correlate with grip behavior in kinetochore subcomplexes
- Biorientation: Promotes accurate biorientation during early mitosis
- Attachment stability: Stabilizes correct attachments before sister chromatids find plus ends
- Mechanical stress: Kinetochores withstand microtubule forces during cell division

**Imaging Data**
- TIRF microscopy: Kinetochore analysis
- Cryo-EM: Structural analysis
- Single-molecule localization: Kinetochore properties
- Temporal resolution: Sufficient to resolve attachment dynamics
- Spatial resolution: ~100 nm (confocal/TIRF microscopy limit)

### Key Citations

**Methodological References**
- C-Trap methods for kinetochore studies
- Microtubule-kinetochore reconstitution
- TIRF microscopy for kinetochore analysis
- Cryo-EM for structural analysis
- Single-molecule localization methods

### Key Features

**Advantages**
- Direct measurement of kinetochore grip behavior
- Can test effects of force direction
- Combined structural (cryo-EM) and dynamic (single-molecule) data
- Relevant for understanding chromosome segregation

**Limitations**
- Requires reconstituted kinetochore complexes
- Limited to in vitro conditions
- Complex multi-protein system

**Applications Demonstrated**
- Chromosome segregation mechanisms
- Kinetochore-microtubule interactions
- Biorientation mechanisms
- Mitotic error correction
- Mechanical force sensing

---

## STUDY 21: HELQ et al. 2023 (LUMICKS C-Trap) - HELQ DNA Repair

### Citation
[Authors to be confirmed] (2023). Helicase HELQ: Molecular Characters Fit for DSB Repair Function. [Journal and details to be confirmed]

### Constructs - DNA Substrates for DSB Repair

**Base Substrate**
- Template: DNA substrates for double-strand break repair
- Configuration: Tethered between beads for single-molecule analysis
- State: Single-stranded and double-stranded DNA substrates

**Substrate Types**
- Single-stranded DNA: For annealing studies
- Double-stranded DNA: For unwinding studies
- Complementary ssDNA: For annealing reactions

**Handles**
- Total length: Variable
- Attachment:
  - One end: Biotinylated (binds to streptavidin beads)
  - Other end: Digoxigenin or biotin (binds to appropriate beads)

**Beads**
- Type: 
  - Streptavidin-coated beads (for biotin)
  - Anti-digoxigenin beads (for digoxigenin)
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (for DNA unwinding and annealing studies)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence imaging
- Laser wavelengths: Not explicitly detailed (likely for HELQ, RAD51, RPA labeling)
- Real-time visualization: For unwinding and annealing dynamics

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: Confocal scanning for protein localization and tracking

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Standard buffers for DNA/protein interactions
- Salt concentrations: Variable
- Temperature: Room temperature or 37°C

**Protein Components**
- HELQ: Helicase enzyme
- RAD51: Recombinase protein
- RPA: Replication protein A
- Combinations: HELQ alone, HELQ+RAD51, HELQ+RPA

**Fluorescent Probes**
- HELQ: Fluorescently labeled
- RAD51: Fluorescently labeled
- RPA: Fluorescently labeled

### Experimental Protocol

**DNA Preparation**
1. Prepare DNA substrates (ssDNA, dsDNA, complementary ssDNA)
2. End-label with biotin and digoxigenin
3. Verify substrate integrity

**Single-Molecule Assay - Unwinding**
1. Tether dsDNA between optical traps
2. Apply appropriate force
3. Introduce HELQ (alone or with RAD51)
4. Monitor unwinding via force-extension and fluorescence
5. Track RAD51 translocation with HELQ

**Single-Molecule Assay - Annealing**
1. Tether ssDNA between optical traps
2. Apply appropriate force
3. Introduce HELQ and RPA
4. Introduce complementary ssDNA
5. Monitor annealing reactions

**Data Acquisition**
1. Track unwinding rates: HELQ alone vs HELQ+RAD51
2. Monitor RAD51 translocation: With HELQ during unwinding
3. Measure annealing activity: HELQ+RPA stimulated annealing
4. Test sequence independence: Annealing of complementary sequences
5. Test concentration dependence: Low helicase concentrations with RPA

### Results - Typical Data

**Force-Extension Measurements**
- DNA unwinding: Extension changes during unwinding
- Annealing: Force changes during annealing reactions

**Key Findings**
- Dual function: HELQ functions as both helicase (unwinding) and strand annealing enzyme
- HELQ+RAD51: Unwinds DNA approximately three times faster than HELQ alone
- RAD51 translocation: RAD51 translocates with HELQ along DNA filaments during unwinding
- RPA stimulation: RPA stimulates HELQ's DNA annealing activity
- RPA loading: RPA helps load HELQ onto ssDNA at low helicase concentrations
- Sequence independence: HELQ can capture and anneal complementary ssDNA sequences in sequence-independent manner
- DSB repair pathways: Functions in HR, SSA, and MMEJ pathways
- Conservation: Highly conserved from archaea to humans

**Imaging Data**
- Real-time visualization: Unwinding and annealing dynamics
- RAD51 tracking: Translocation with HELQ visualized
- Temporal resolution: Sufficient to resolve unwinding and annealing dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Citations

**Methodological References**
- C-Trap methods for DNA repair studies
- HELQ purification and characterization
- Single-molecule DNA unwinding assays
- Strand annealing measurement techniques

### Key Features

**Advantages**
- Direct visualization of dual-function enzyme
- Can test effects of RAD51 and RPA
- Single-molecule resolution for dynamics analysis
- Combined force and fluorescence readouts
- Relevant for understanding DSB repair mechanisms

**Limitations**
- Requires purified HELQ, RAD51, and RPA
- Limited to in vitro conditions
- Complex multi-protein interactions

**Applications Demonstrated**
- Double-strand break repair mechanisms
- Homologous recombination
- Single-strand annealing
- Microhomology-mediated end joining
- Helicase and annealing enzyme functions

---

## STUDY 22: Trigger Factor et al. 2025 (LUMICKS C-Trap) - Protein Folding

### Citation
[Authors to be confirmed] (2025). Trigger factor accelerates nascent chain compaction and folding. PNAS, [Volume and pages to be confirmed]. DOI: 10.1073/pnas.2422678122

### Constructs - Nascent Polypeptide Chains

**Base Substrate**
- Template: Nascent polypeptide chains during translation
- Configuration: Tethered for single-molecule analysis
- State: Polypeptide chains in various folding states

**Handles**
- Polypeptide attachment: Not explicitly detailed
- Bead attachment: Via polypeptide or ribosome

**Beads**
- Type: Not explicitly detailed
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Correlated single-molecule fluorescence
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Variable (for protein folding studies)
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Correlated single-molecule fluorescence
- Laser wavelengths: Not explicitly detailed (likely for trigger factor and polypeptide labeling)

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Fluorescence: For protein and chaperone localization

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Translation buffer: For ribosome activity
- Salt concentrations: Variable
- Temperature: Room temperature or 37°C

**Protein Components**
- Trigger factor: Chaperone protein
- Ribosome: For translation
- Nascent chains: Polypeptide chains being synthesized

**Fluorescent Probes**
- Trigger factor: Fluorescently labeled
- Nascent chains: May be labeled

### Experimental Protocol

**Translation Setup**
1. Set up ribosome-nascent chain system
2. Tether for single-molecule analysis
3. Initiate translation

**Single-Molecule Assay**
1. Monitor nascent chain synthesis
2. Introduce trigger factor
3. Measure compaction and folding via force-extension
4. Track trigger factor binding via fluorescence
5. Compare with and without trigger factor

**Data Acquisition**
1. Measure compaction: Polypeptide chain collapse
2. Measure folding: Native state formation
3. Track trigger factor binding: Association with nascent chains
4. Compare rates: With vs without trigger factor

### Results - Typical Data

**Force-Extension Measurements**
- Nascent chains: Extension changes during compaction and folding
- Trigger factor effect: Accelerated compaction and folding

**Key Findings**
- Compaction acceleration: Trigger factor accelerates nascent chain compaction
- Folding acceleration: Trigger factor accelerates protein folding
- Mechanism: Enhances polypeptide collapse
- Cotranslational assembly: Implications for cotranslational protein assembly
- Aggregation suppression: May suppress aggregation during translation

**Imaging Data**
- Trigger factor binding: Visualization of chaperone association
- Temporal resolution: Sufficient to resolve compaction and folding dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Citations

**Methodological References**
- C-Trap methods for protein folding studies
- Correlated optical tweezers-fluorescence for translation
- Trigger factor purification and characterization
- Nascent chain analysis methods

### Key Features

**Advantages**
- Direct visualization of cotranslational folding
- Can test effects of chaperones
- Combined force and fluorescence readouts
- Relevant for understanding protein folding mechanisms

**Limitations**
- Requires ribosome-nascent chain system
- Limited to in vitro conditions
- Complex translation system

**Applications Demonstrated**
- Protein folding mechanisms
- Cotranslational folding
- Chaperone function
- Aggregation prevention
- Translation-coupled processes

---

## STUDY 23: Cellular Mechanics et al. 2025 (LUMICKS C-Trap) - Cell Mechanical Properties

### Citation
[Authors to be confirmed] (2025). Robust quantification of cellular mechanics using optical tweezers. Biophysical Reports, [Volume and pages to be confirmed]. DOI: [to be confirmed]

### Constructs - Live Cells

**Base Substrate**
- Template: Live cells
- Configuration: Cells attached to optical traps
- State: Living cells under mechanical stress

**Cell Attachment**
- Method: Not explicitly detailed (likely via beads or direct attachment)
- Bead attachment: Cells attached to functionalized beads

**Beads**
- Type: Functionalized beads for cell attachment
- Size: Typical ~2-4.5 μm for C-Trap

### Instrument Configuration - LUMICKS C-Trap

**System Components**
- Manufacturer: LUMICKS
- Model: C-Trap
- Core capabilities:
  - Dual optical tweezers
  - Confocal fluorescence microscopy (inferred)
  - Multi-channel microfluidics
  - Integration of force spectroscopy and fluorescence imaging
  - Force-feedback control

**Optical Tweezers**
- Laser: 1064 nm (typical for trapping)
- Trap configuration: Dual traps
- Force range: Piconewton-range forces
- Force-feedback control: For precise force application
- Position resolution: Sub-nanometer
- Force measurement: Back focal plane interferometry

**Microscopy**
- Confocal fluorescence microscopy (inferred)
- Laser wavelengths: Not explicitly detailed

**Microfluidics**
- Design: Multi-channel laminar flow cell
- Flow control: Automated valve control for channel switching

**Detection**
- Force measurement: Back focal plane interferometry
- Force resolution: Sub-piconewton
- Distance resolution: Nanometer-scale
- Cell deformation: Measured via force and position

**Software**
- Control software: Bluelake (LUMICKS proprietary)
- Analysis software: Pylake (Python package from LUMICKS)

### Experimental Conditions

**Buffer Conditions**
- Cell culture medium: For maintaining cell viability
- Temperature: 37°C (physiological)

**Cell Types**
- Various cell types: As needed for specific studies

### Experimental Protocol

**Cell Preparation**
1. Culture cells
2. Attach to functionalized beads or prepare for trapping
3. Verify cell viability

**Single-Cell Assay**
1. Trap cell or cell-bead complex
2. Apply piconewton-range forces with force-feedback control
3. Measure cell deformation
4. Measure cell stiffness
5. Measure creep response

**Data Acquisition**
1. Force application: Controlled piconewton forces
2. Deformation measurement: Cell shape changes
3. Stiffness measurement: Force vs deformation
4. Creep response: Time-dependent deformation

### Results - Typical Data

**Force-Deformation Measurements**
- Cell deformation: Measured under applied forces
- Stiffness: Calculated from force-deformation curves
- Creep: Time-dependent response

**Key Findings**
- Robust quantification: Methods for reliable cell mechanics measurement
- Force-feedback control: Enables precise force application
- Deformation: Cell shape changes under force
- Stiffness: Cell mechanical stiffness quantified
- Creep response: Time-dependent mechanical behavior

**Imaging Data**
- Cell visualization: During mechanical testing
- Temporal resolution: Sufficient to resolve deformation dynamics
- Spatial resolution: ~100 nm (confocal microscopy limit)

### Key Citations

**Methodological References**
- C-Trap methods for cell mechanics
- Force-feedback control methods
- Cell attachment protocols
- Cellular mechanics analysis

### Key Features

**Advantages**
- Direct measurement of cell mechanical properties
- Force-feedback control for precise measurements
- Can test various cell types
- Relevant for understanding cell mechanics

**Limitations**
- Requires cell culture and preparation
- Limited to in vitro conditions
- Cell viability must be maintained

**Applications Demonstrated**
- Cell mechanical properties
- Cell deformation under force
- Cell stiffness measurement
- Creep response analysis
- Mechanobiology studies

---

*Note: This citations list focuses on key methodological references. Each study in this document may cite many additional papers. For complete citation lists, please refer to the original publications.*
