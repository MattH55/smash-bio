// Schema page: render documentation tables from the JSON Schemas
(function () {
  const S = window.SMASH, E = S.esc, sc = S.schemas || {};
  const R = sc['smash-smfs-record.schema'], X = sc['smash-smfs-results.schema'];
  if (!R || !X) return;
  const $ = id => document.getElementById(id);
  const typeOf = p => {
    if (!p) return '';
    if (p.$ref) return p.$ref.split('/').pop();
    if (p.enum) return 'enum';
    if (p.const) return 'const';
    if (p.type === 'array') return (p.items && (p.items.$ref ? p.items.$ref.split('/').pop() : p.items.enum ? 'enum' : p.items.type)) + '[]';
    return Array.isArray(p.type) ? p.type.join(' | ') : (p.type || 'object');
  };
  const desc = p => {
    let d = p.description || '';
    const en = p.enum || (p.items && p.items.enum);
    if (en) d += (d ? '<br>' : '') + en.map(e => `<code>${E(e)}</code>`).join(' ');
    if (p.examples) d += (d ? '<br>' : '') + '<span class="muted">e.g. ' + E(JSON.stringify(p.examples[0])) + '</span>';
    return d;
  };
  const propTable = (props, req = []) => `<thead><tr><th>Field</th><th>Type</th><th>Description / values</th></tr></thead><tbody>` +
    Object.entries(props).map(([k, p]) => `<tr><td>${E(k)}${req.includes(k) ? ' <span class="badge badge-accent">req</span>' : ''}</td><td class="mono small">${E(typeOf(p))}</td><td>${desc(p)}</td></tr>`).join('') + '</tbody>';

  // Table 3 mapping
  const T3 = [
    ['Hardware', 'Make of setup', 'hardware.make_of_setup', 'all'], ['Hardware', 'Model number', 'hardware.model_number', 'all'],
    ['Hardware', 'Spatial laser control', 'hardware.optical.spatial_laser_control', 'all (optical)'], ['Hardware', 'Detection device', 'hardware.detection_device', 'all'],
    ['Hardware', 'Objective lens', 'hardware.objective_lens', 'all'], ['Hardware', 'Optical filters', 'hardware.optical_filters', 'all'],
    ['Hardware', 'Laser power at source / objective', 'hardware.optical.laser_power_at_source / _at_objective', 'all (optical)'],
    ['Hardware', 'Trap stiffness ± uncertainty', 'hardware.optical.trap_stiffness (+ uncertainty)', 'all (optical); AFM → afm.spring_constant'],
    ['Hardware', 'Temperature', 'hardware.temperature', 'all'], ['Hardware', 'Laser wavelength', 'hardware.optical.laser_wavelength', 'all (optical)'],
    ['Hardware', 'Acquisition rate', 'hardware.acquisition_rate', 'all'], ['Hardware', 'Line scanning rate', 'hardware.line_scanning_rate', 'all (confocal)'],
    ['Hardware', 'Filter frequency', 'hardware.filter_frequency', 'all'], ['Hardware', 'Calibration technique', 'hardware.calibration_technique', 'all'],
    ['Assay', 'Bead geometry', 'assay.bead_geometry', 'force generation / rheology'], ['Assay', 'Bead size ± uncertainty', 'assay.bead_size', 'all'],
    ['Assay', 'Bead functionalization', 'assay.bead_functionalization, assay.attachment_chemistry', 'all'], ['Assay', 'Trap control', 'assay.trap_control', 'all'],
    ['Assay', 'Force profile / extension profile', 'assay.force_profile, assay.extension_profile → TraceSet', 'all'], ['Assay', 'Handle sequences', 'assay.handle_sequences', 'all'],
    ['Assay', 'Flow pressure / linear flow speed', 'assay.flow_pressure, assay.linear_flow_speed_at_bead', 'all'],
    ['Construct', 'Sequence identity (FASTA, PDB, UniProt)', 'biological_system.entities[].sequence / identifiers', 'unfolding; DNA–protein'],
    ['Construct', 'Fluorescent labels (location, identifier, λabs/λem, QY, efficiency)', 'entities[].fluorescent_labels', 'unfolding; DNA–protein'],
    ['Construct', 'Structure type (actin, IF, microtubule)', 'biological_system.cytoskeleton.structure_type', 'force generation'],
    ['Construct', 'Protein unit(s) (gene symbol, FASTA, PDB, UniProt)', 'biological_system.cytoskeleton.protein_units', 'force generation'],
    ['Construct', 'Perturbations to structure', 'cytoskeleton.perturbations_to_structure', 'force generation'],
    ['Construct', 'Cell identity (Cell Ontology, HCA)', 'biological_system.cell.cell_ontology / human_cell_atlas', 'rheology'],
    ['Construct', 'Cell genome (FASTA / GenBank)', 'biological_system.cell.cell_genome', 'rheology'], ['Construct', 'Perturbations to cell', 'biological_system.cell.perturbations', 'rheology'],
    ['Solution', 'Factors in solution: identity, concentration', 'solution.components', 'all'], ['Solution', 'Small molecule (name, CAS, SMILES), concentration', 'solution.small_molecules', 'all'],
    ['Solution', 'Protein/peptide (FASTA, PDB, UniProt), labels', 'solution.proteins_in_solution', 'all'], ['Solution', 'Nucleic acid (FASTA, GenBank, PDB), labels', 'solution.nucleic_acids_in_solution', 'all'],
    ['SMASH-BIO', 'Technique, geometry, modalities', 'technique.*', 'extension'], ['SMASH-BIO', 'Organisms', 'biological_system.organisms', 'extension'],
    ['SMASH-BIO', 'Results', 'results[] (results schema)', 'extension'], ['SMASH-BIO', 'Data availability & linked datasets', 'data_availability.*', 'extension'],
  ];
  $('t3-map').innerHTML = `<thead><tr><th>Table 3 section</th><th>Table 3 field</th><th>Schema path</th><th>Applies to</th></tr></thead><tbody>` +
    T3.map(r => `<tr><td style="font-family:var(--font)">${E(r[0])}</td><td>${E(r[1])}</td><td class="mono small">${E(r[2])}</td><td class="t3col">${E(r[3])}</td></tr>`).join('') + '</tbody>';

  $('top-props').innerHTML = propTable(R.properties, R.required);
  const DEFS = ['Publication', 'Technique', 'Assay', 'BiologicalSystem', 'MolecularEntity', 'FluorescentLabel', 'Solution', 'DataAvailability', 'DatasetLink', 'Annotations', 'Quantity', 'Identifier'];
  $('defs').innerHTML = DEFS.map(k => {
    const d = R.$defs[k];
    return `<h3 id="def-${k}">${E(k)}</h3>${d.description ? `<p>${E(d.description)}</p>` : ''}<div class="table-scroll"><table class="schema-table">${propTable(d.properties || {}, d.required || [])}</table></div>`;
  }).join('');

  $('tech-table').innerHTML = `<thead><tr><th>Value</th><th>Technique</th><th>Force applied by</th></tr></thead><tbody>` +
    R.$defs.TechniqueName.enum.map(k => `<tr><td>${E(k)}</td><td style="font-family:var(--font)">${E(S.tl(k))}</td><td>${E((S.TECH[k] || {}).blurb || '')}</td></tr>`).join('') + '</tbody>';
  $('geom-list').innerHTML = R.$defs.Technique.properties.force_application_geometry.enum.map(g => `<span class="badge">${E(g)}</span>`).join('');

  const H = R.$defs.Hardware.properties;
  $('hw-blocks').innerHTML = ['optical', 'magnetic', 'afm', 'acoustic', 'centrifuge', 'nanopore', 'hydrodynamic', 'bfp_micropipette', 'tension_sensor'].map(k =>
    `<h3><code>hardware.${k}</code></h3>${H[k].description ? `<p>${E(H[k].description)}</p>` : ''}<div class="table-scroll"><table class="schema-table">${propTable(H[k].properties)}</table></div>`).join('');

  const T3COL = { unfolding_protein: 'Unfolding', unfolding_nucleic_acid: 'Unfolding', nucleic_acid_mechanics: 'Unfolding', nucleic_acid_protein_interaction: 'DNA–protein',
    chromatin_mechanics: 'DNA–protein', translation_transcription_replication: 'Force generation', force_generation_motor: 'Force generation', force_generation_polymerization: 'Force generation',
    receptor_ligand_adhesion: 'Extension', membrane_mechanics: 'Rheology', rheology_cell: 'Rheology', rheology_material: 'Rheology', methods_calibration: 'Extension' };
  $('class-table').innerHTML = `<thead><tr><th>Class</th><th>Label</th><th>Table 3 column</th></tr></thead><tbody>` +
    R.$defs.ExperimentClass.enum.map(k => `<tr><td>${E(k)}</td><td style="font-family:var(--font)">${E(S.cl(k))}</td><td class="t3col">${E(T3COL[k] || '')}</td></tr>`).join('') + '</tbody>';

  $('result-props').innerHTML = propTable(X.$defs.Result.properties, X.$defs.Result.required);
  $('result-example').textContent = JSON.stringify({
    quantity: 'unfolding_force', label: 'I27 unfolding force', value: 204, unit: 'pN', uncertainty: 26, uncertainty_type: 'SD', statistic: 'most_probable', n_events: 412,
    applies_to: { entity: 'Titin (Ig/FnIII domains, e.g. I27/I91)', region: 'I27', transition: 'N->U' },
    conditions: { pulling_speed_nm_per_s: 400, temperature_K: 298 }, model: 'Bell-Evans', method: 'Gaussian fit to rupture-force histogram',
    data_ref: { dataset_doi: '10.5281/zenodo.xxxxxxx', file: 'I27_400nms.h5' }, source: { location: 'results_text', extraction: 'manual', confidence: 'high' }
  }, null, 2);
  const units = X.$defs.ObservableUnits.const;
  $('obs-table').innerHTML = `<thead><tr><th>Observable</th><th>Label</th><th>Canonical unit</th></tr></thead><tbody>` +
    X.$defs.Observable.enum.map(k => `<tr><td>${E(k)}</td><td style="font-family:var(--font)">${E(S.OBS[k] || k.replace(/_/g, ' '))}</td><td class="mono small">${E(units[k] || '')}</td></tr>`).join('') + '</tbody>';
  $('trace-props').innerHTML = propTable(X.$defs.TraceSet.properties, X.$defs.TraceSet.required);
  $('trace-example').textContent = JSON.stringify({
    record_id: 'SMFS-000123', file: 'molecule_07.h5', format: 'lumicks_h5', molecule_id: 'mol07', sampling_rate_Hz: 78125, downsampled_from_Hz: null,
    channels: [
      { name: 'time', unit: 's', path_in_file: 'Force HF/Force 1x (timestamps)' },
      { name: 'force', unit: 'pN', path_in_file: 'Force HF/Force 1x', calibrated: true, calibration: { stiffness_pN_per_nm: 0.31, method: 'power_spectrum_passive' } },
      { name: 'trap_separation', unit: 'um', path_in_file: 'Distance/Distance 1' }],
    protocol_segments: [{ start_s: 0, end_s: 12.5, mode: 'pull 100 nm/s' }, { start_s: 12.5, end_s: 25, mode: 'relax 100 nm/s' }],
    events: [{ t_s: 7.82, force_pN: 18.4, delta_contour_length_nm: 29.1, type: 'unfolding' }]
  }, null, 2);

  const STD = {
    public_repository: 'At least one dataset deposit (Zenodo, Figshare, Dryad, OSF, Mendeley Data, Dataverse, 4TU, BioStudies…) is linked to the article.',
    source_data_supplement: 'Source data files accompany the article (e.g. Nature “Source Data”).', journal_supplement: 'Data only in journal supplementary files or journal-hosted Figshare mirrors.',
    code_only: 'Only analysis code (GitHub, Zenodo software) is linked.', on_request: 'Data statement says data are available from the authors on request.',
    not_available: 'Statement says no new data were generated (typical of reviews/theory).', not_stated: 'Full text checked; no data statement and no deposit found.',
    unknown_no_fulltext: 'Full text not openly available, so the statement could not be checked (repository links are still searched).'
  };
  $('status-table').innerHTML = `<thead><tr><th>status</th><th>Label</th><th>Meaning</th></tr></thead><tbody>` +
    Object.entries(STD).map(([k, v]) => `<tr><td>${E(k)}</td><td style="font-family:var(--font)">${E(S.sl(k))}</td><td>${E(v)}</td></tr>`).join('') + '</tbody>';
  const EVD = [
    ['author_submitted', 'Submitted or confirmed by the authors', 'highest'], ['manual_curation', 'Entered by a SMASH-BIO curator from the paper', 'high'], ['llm_review', 'Reviewed by an LLM against the open full text; verbatim snippet required; not yet human-checked', 'medium'],
    ['regex_fulltext_methods', 'Extracted from open-access Methods text; snippet stored', 'medium'], ['regex_title_abstract', 'Extracted from title/abstract', 'medium'],
    ['gazetteer', 'Biological system matched by the SMASH-BIO dictionary; IDs resolved via UniProt/Rfam/ChEBI', 'medium'],
    ['europepmc_textmining', 'Europe PMC text-mined entity (organisms, genes/proteins, accessions)', 'low–high'],
    ['datacite / scholix / europepmc_datalinks', 'Dataset links from registries', 'high'], ['fulltext_statement', 'Repository link parsed from the data-availability statement', 'high'],
  ];
  $('evidence-table').innerHTML = `<thead><tr><th>evidence.method</th><th>Meaning</th><th>Typical confidence</th></tr></thead><tbody>` +
    EVD.map(r => `<tr><td>${E(r[0])}</td><td>${E(r[1])}</td><td>${E(r[2])}</td></tr>`).join('') +
    `<tr><td>curation.level</td><td colspan="2"><code>auto_abstract</code> · <code>auto_fulltext</code> · <code>ai_assisted</code> · <code>curated</code> · <code>author_verified</code></td></tr></tbody>`;
})();
