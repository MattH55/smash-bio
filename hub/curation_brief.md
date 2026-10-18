# SMASH-BIO AI-assisted curation brief

You are reviewing automatically extracted metadata for single-molecule force spectroscopy (SMFS) papers
against the paper's own open-access text, and writing a corrected record for each.

## Input
A batch file `hub/curation_batches/batch_NN.json` = list of packets:
`{"record": <auto-extracted record subset>, "methods_text": "...", "data_statement": "..."}`.
The record's abstract is in `record.publication.abstract`. Use ONLY the abstract, methods_text and data_statement
as evidence. Do not use outside knowledge to add values (you may use it to recognise that an auto value is wrong).

## Output
For each packet write `hub/curated_json/<record_id>.json` (UTF-8 JSON, one file per record) with this shape —
omit any field you cannot support with text; never guess:

```json
{
  "publication": {"doi": "<copy from record>"},
  "curation": {"level": "ai_assisted", "curators": ["Claude (AI-assisted curation)"],
               "notes": "1-3 sentences: what the experiment is and anything notable (e.g. two techniques, multiple constructs)"},
  "technique": {"primary": "<optical_tweezers|magnetic_tweezers|torque_tweezers|afm_smfs|acoustic_force_spectroscopy|centrifuge_force|nanopore_force|hydrodynamic_stretching|biomembrane_force_probe|micropipette|tension_sensors|microneedle>",
                "secondary": [], "force_application_geometry": "<see list>", "correlative_modalities": []},
  "hardware": {
    "make_of_setup": "LUMICKS | JPK / Bruker | Bruker | Asylum Research / Oxford Instruments | Picotwist | Depixus | Impetux | custom | ...",
    "model_number": "C-Trap", "custom_built": true,
    "detection_device": ["QPD"], "objective_lens": {"make": "Nikon", "magnification": 60, "numerical_aperture": 1.2, "immersion": "water"},
    "temperature": {"value": 296.15, "unit": "K", "evidence": {"method": "llm_review", "snippet": "<verbatim ≤300 chars>", "confidence": "high"}},
    "acquisition_rate": {"value": 78.125, "unit": "kHz", "evidence": {...}},
    "filter_frequency": {"value": 10, "unit": "Hz", "evidence": {...}},
    "calibration_technique": ["power_spectrum_passive"],
    "optical": {"laser_wavelength": {...nm}, "laser_power_at_source": {...mW}, "laser_power_at_objective": {...mW},
                "spatial_laser_control": ["AOD"], "number_of_traps": 2, "trap_stiffness": {...pN/nm, "uncertainty": 0.02}},
    "magnetic": {"magnet_type": "permanent_pair", "bead_product": "Dynabeads M-270", "camera_frame_rate": {...Hz}, "rotation_control": true},
    "afm": {"cantilever_model": "MLCT", "spring_constant": {...pN/nm}, "pulling_speed": {...nm/s}}
  },
  "assay": {
    "experiment_class": ["<see list>"], "bead_geometry": "two_bead_dumbbell",
    "bead_size": {"value": 2100, "unit": "nm", "evidence": {...}}, "bead_material": "polystyrene",
    "bead_functionalization": ["streptavidin", "anti-digoxigenin"], "attachment_chemistry": ["biotin–streptavidin", "digoxigenin–anti-digoxigenin"],
    "trap_control": ["force_ramp", "constant_distance"], "loading_rate": {...pN/s}, "pulling_speed": {...nm/s},
    "handle_sequences": [{"length_bp": 2500, "annotations": "<verbatim>"}], "n_molecules": 25
  },
  "biological_system": {
    "system_class": ["<same as assay.experiment_class>"],
    "organisms": [{"name": "Homo sapiens", "ncbi_taxon": 9606}],
    "entities": [
      {"name": "Titin I27 octamer", "entity_type": "protein", "role": "tethered_construct",
       "identifiers": [{"scheme": "uniprot", "id": "Q8WZ42", "verified": false}],
       "organism": {"name": "Homo sapiens", "ncbi_taxon": 9606}, "region": "I27 (residues …)", "mutations": ["C47S"],
       "length": {"value": 89, "unit": "aa"},
       "fluorescent_labels": [{"identifier": "Cy3", "sequence_location": "…"}],
       "evidence": {"method": "llm_review", "snippet": "<verbatim>", "confidence": "high"}}
    ],
    "cell": {"cell_identity": "HeLa"}, "cytoskeleton": {"structure_type": "microtubule"}
  },
  "solution": {"buffer": "HEPES", "pH": 7.5,
               "components": [{"name": "KCl", "concentration": {"value": 150, "unit": "mM"}}],
               "nucleotides": ["ATP"], "oxygen_scavenging": "glucose oxidase, catalase",
               "small_molecules": [{"name": "…", "concentration": {"value": 10, "unit": "nM"}}]},
  "results": [
    {"quantity": "unfolding_force", "value": 18.5, "unit": "pN", "uncertainty": 1.2, "uncertainty_type": "SEM",
     "applies_to": {"entity": "…", "transition": "N->U"}, "conditions": {"pulling_speed_nm_per_s": 100},
     "model": "eWLC", "source": {"location": "abstract", "snippet": "<verbatim>", "extraction": "manual", "confidence": "high"}}
  ]
}
```

## Rules
1. **Every numeric value needs a verbatim evidence snippet** copied from the text (≤300 chars). If a value is
   only in a figure or not stated, leave it out. Do not convert ranges into single values — use `min`/`max`.
2. **Units:** store temperature in K (°C + 273.15), acquisition in kHz, filter in Hz, bead size in nm, stiffness and
   spring constants in pN/nm (N/m × 1000), laser power in mW, wavelength in nm.
3. **Fix the auto record.** Auto values were regex-extracted and are often wrong (e.g. a 4 °C dialysis step taken as
   the measurement temperature, the wrong protein, a vendor that only supplied beads). Your file *replaces* the
   hardware, assay and solution sections, and replaces the entity list — so include correct auto values you agree with.
4. **Entities:** list the tethered construct(s), handles (as `role: handle`), binding partners/motors, and the track
   (e.g. microtubule). Copy UniProt/PDB IDs that appear in the text, and keep auto-assigned UniProt IDs only when
   the protein and organism match the paper (set `verified: false`). If the organism is not stated, omit it.
5. **Results:** only numbers reported in the abstract or methods/results text provided, using the observable vocabulary:
   unfolding_force, refolding_force, rupture_force, unbinding_force, unzipping_force, overstretching_force, equilibrium_force,
   detachment_force, stall_force, tether_force, adhesion_force, contour_length, contour_length_increment, persistence_length,
   stretch_modulus, torsional_modulus, torque, step_size, velocity, processivity_run_length, dwell_time, rate_constant_zero_force,
   unfolding_rate, folding_rate, binding_rate_kon, unbinding_rate_koff, dissociation_constant_Kd, bond_lifetime,
   distance_to_transition_state, activation_free_energy, folding_free_energy, binding_free_energy, molecular_stiffness,
   cell_stiffness, elastic_modulus, viscosity, membrane_tension, bending_rigidity, loading_rate, other.
6. **Controlled values:**
   - experiment_class: unfolding_protein, unfolding_nucleic_acid, nucleic_acid_protein_interaction, nucleic_acid_mechanics,
     force_generation_motor, force_generation_polymerization, receptor_ligand_adhesion, membrane_mechanics, rheology_cell,
     rheology_material, chromatin_mechanics, translation_transcription_replication, methods_calibration
   - force_application_geometry: dumbbell_dual_trap, single_trap_surface_tether, three_bead_assay, four_trap_braid,
     bead_on_surface_magnetic, freely_orbiting_magnetic, cantilever_tip_surface, cantilever_cell_surface, bead_on_surface_acoustic,
     bead_on_surface_centrifugal, nanopore_translocation, flow_tethered_end, doubly_tethered_curtain, micropipette_bead,
     biomembrane_force_probe, cell_surface_tension_sensor, dna_origami_clamp, in_vivo_trapped_organelle, membrane_tether_extrusion, other
   - trap_control: force_ramp, force_clamp, constant_force, constant_distance, passive_mode, force_jump, constant_velocity, oscillatory, rotation, custom
   - calibration_technique: power_spectrum_passive, power_spectrum_active, equipartition, stokes_drag, step_response,
     thermal_noise_cantilever, sader, allan_variance, image_based_variance, flow_calibration, dna_force_extension_reference, manufacturer, other
   - detection_device: QPD, PSD, camera_CMOS, camera_CCD, camera_sCMOS, camera_EMCCD, photodiode, BFP_interferometry, cantilever_deflection, ionic_current, other
   - correlative_modalities: confocal_fluorescence, widefield_fluorescence, TIRF, smFRET, STED, IRM, brightfield_video, darkfield, Raman, electrophysiology, high_speed_AFM_imaging, label_free_scattering
7. If the paper is not actually a force-spectroscopy study, write only
   `{"publication": {"doi": …}, "curation": {"level": "ai_assisted", "curators": [...], "notes": "NOT SMFS: <reason>"}}`.
8. Validate each file parses as JSON (e.g. `python -c "import json,sys;json.load(open(sys.argv[1],encoding='utf-8'))" file`).
