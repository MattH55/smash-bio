// Submit page: build a schema v3 JSON record in the browser
(async function () {
  const S = window.SMASH, E = S.esc, $ = id => document.getElementById(id);
  const R = (S.schemas || {})['smash-smfs-record.schema'], X = (S.schemas || {})['smash-smfs-results.schema'];
  const opts = (sel, vals, fmt, blank = true) => { $(sel).innerHTML = (blank ? '<option value="">—</option>' : '') + vals.map(v => `<option value="${E(v)}">${E(fmt ? fmt(v) : v.replace(/_/g, ' '))}</option>`).join(''); };
  opts('f-tech', R.$defs.TechniqueName.enum, S.tl, false);
  opts('f-geom', R.$defs.Technique.properties.force_application_geometry.enum);
  opts('f-cal', R.$defs.Hardware.properties.calibration_technique.items.enum);
  opts('f-ctrl', R.$defs.Assay.properties.trap_control.items.enum);
  const chipSet = (id, vals, fmt) => {
    $(id).innerHTML = vals.map(v => `<button type="button" class="chip" data-v="${E(v)}">${E(fmt ? fmt(v) : v.replace(/_/g, ' '))}</button>`).join('');
    $(id).onclick = e => { const b = e.target.closest('.chip'); if (b) b.classList.toggle('active'); };
  };
  const C = R.properties.classification.properties;
  opts('f-module', C.modules.items.properties.module_id.enum, null, false);
  const subs = C.modules.items.properties.submodules.items.enum;
  const fillSubs = () => {
    const meta = (S.moduleMeta || {})[$('f-module').value] || {};
    const allowed = (meta.submodules || []).filter(id => subs.includes(id));
    opts('f-sub', allowed.length ? allowed : subs);
  };
  $('f-module').onchange = fillSubs;
  if (S.qs().get('module') && C.modules.items.properties.module_id.enum.includes(S.qs().get('module'))) $('f-module').value = S.qs().get('module');
  fillSubs();
  opts('f-assay', C.assay_type.enum);
  opts('f-beadgeo', C.bead_geometry.enum);
  opts('f-proc', C.processivity.enum, null, false);
  chipSet('f-modes', C.measurement_modes.items.enum);
  chipSet('f-classes', R.$defs.ExperimentClass.enum, S.cl);
  chipSet('f-mods', R.$defs.Technique.properties.correlative_modalities.items.enum);
  const chipsOf = id => [...$(id).querySelectorAll('.chip.active')].map(b => b.dataset.v);

  const ETYPES = R.$defs.MolecularEntity.properties.entity_type.enum, ROLES = R.$defs.MolecularEntity.properties.role.enum;
  function addEntity(e = {}) {
    const d = document.createElement('div');
    d.className = 'form-grid ent-row'; d.style.cssText = 'border-bottom:1px solid var(--border);padding-bottom:14px;margin-bottom:14px';
    d.innerHTML = `<div class="field"><label>Name</label><input type="text" class="e-name" value="${E(e.name || '')}"></div>
      <div class="field"><label>Type</label><select class="e-type">${ETYPES.map(t => `<option ${t === e.entity_type ? 'selected' : ''}>${t}</option>`).join('')}</select></div>
      <div class="field"><label>Role</label><select class="e-role">${ROLES.map(t => `<option ${t === e.role ? 'selected' : ''}>${t}</option>`).join('')}</select></div>
      <div class="field"><label>Identifiers (scheme:id, comma-separated)</label><input type="text" class="e-ids" placeholder="uniprot:Q8WZ42, pdb:1TIT" value="${E((e.identifiers || []).map(i => i.scheme + ':' + i.id).join(', '))}"></div>
      <div class="field"><label>Organism (NCBI taxon id)</label><input type="text" class="e-org" value="${E(e.organism && e.organism.ncbi_taxon || '')}"></div>
      <div class="field"><label>Region / mutations</label><input type="text" class="e-region" placeholder="I27; C47S"></div>
      <div class="field full"><label>Sequence (FASTA)</label><textarea class="e-seq mono"></textarea></div>
      <div class="field"><label>Fluorescent label & location</label><input type="text" class="e-label" placeholder="Cy3 @ residue 32"></div>
      <div class="field" style="justify-content:flex-end"><button type="button" class="btn btn-ghost btn-sm e-del"><i class="fas fa-trash"></i> Remove</button></div>`;
    d.querySelector('.e-del').onclick = () => d.remove();
    $('entities').appendChild(d);
  }
  function addResult(x = {}) {
    const d = document.createElement('div');
    d.className = 'form-grid res-row'; d.style.cssText = 'border-bottom:1px solid var(--border);padding-bottom:14px;margin-bottom:14px';
    const units = X.$defs.ObservableUnits.const;
    d.innerHTML = `<div class="field"><label>Observable</label><select class="r-q">${X.$defs.Observable.enum.map(o => `<option value="${o}" ${o === x.quantity ? 'selected' : ''}>${E(S.OBS[o] || o.replace(/_/g, ' '))}</option>`).join('')}</select></div>
      <div class="field"><label>Value ± uncertainty <span class="r-unit muted"></span></label><div style="display:flex;gap:6px"><input type="number" step="any" class="r-v" value="${x.value ?? ''}"><input type="number" step="any" class="r-u" placeholder="±" value="${x.uncertainty ?? ''}"></div></div>
      <div class="field"><label>Applies to (entity / transition)</label><input type="text" class="r-a"></div>
      <div class="field"><label>Model</label><select class="r-m"><option value="">—</option>${X.$defs.Result.properties.model.enum.map(m => `<option>${m}</option>`).join('')}</select></div>
      <div class="field"><label>Conditions</label><input type="text" class="r-c" placeholder="400 nm/s, 298 K"></div>
      <div class="field" style="justify-content:flex-end"><button type="button" class="btn btn-ghost btn-sm r-del"><i class="fas fa-trash"></i> Remove</button></div>`;
    const setU = () => { d.querySelector('.r-unit').textContent = '(' + (units[d.querySelector('.r-q').value] || 'unit') + ')'; };
    d.querySelector('.r-q').onchange = setU; setU();
    d.querySelector('.r-del').onclick = () => d.remove();
    $('results-rows').appendChild(d);
  }
  $('add-ent').onclick = () => addEntity();
  $('add-res').onclick = () => addResult();

  // prefill from an existing record (corrections)
  const from = S.qs().get('from');
  if (from) {
    const r = await S.getRecord(from).catch(() => null);
    if (r) {
      const p = r.publication, h = r.hardware || {}, o = h.optical || {}, a = r.assay || {};
      const set = (id, v) => { if (v != null && v !== '') $(id).value = v; };
      set('f-title', p.title); set('f-doi', p.doi); set('f-year', p.year); set('f-journal', p.journal); set('f-authors', (p.authors || []).join('; '));
      set('f-tech', r.technique.primary); set('f-geom', r.technique.force_application_geometry);
      set('f-make', h.make_of_setup); set('f-model', h.model_number); set('f-det', (h.detection_device || []).join(', '));
      set('f-wl', o.laser_wavelength && o.laser_wavelength.value); set('f-k', o.trap_stiffness && o.trap_stiffness.value);
      set('f-temp', h.temperature && h.temperature.value); set('f-acq', h.acquisition_rate && h.acquisition_rate.value);
      set('f-filt', h.filter_frequency && h.filter_frequency.value); set('f-cal', (h.calibration_technique || [])[0]);
      set('f-bead', a.bead_size && a.bead_size.value); set('f-func', (a.bead_functionalization || []).join('; ')); set('f-ctrl', (a.trap_control || [])[0]);
      set('f-buf', r.solution.buffer); set('f-ph', r.solution.pH);
      const ds = (r.data_availability.datasets || [])[0]; if (ds) set('f-ds', ds.id);
      const cd = (r.data_availability.code || [])[0]; if (cd) set('f-code', cd.id);
      (r.biological_system.system_class || []).forEach(c => { const b = $('f-classes').querySelector(`[data-v="${c}"]`); if (b) b.classList.add('active'); });
      (r.technique.correlative_modalities || []).forEach(c => { const b = $('f-mods').querySelector(`[data-v="${c}"]`); if (b) b.classList.add('active'); });
      (r.biological_system.entities || []).filter(e => (e.evidence || {}).method !== 'europepmc_textmining').forEach(addEntity);
      (r.results || []).forEach(addResult);
      const n = $('prefill-note'); n.style.display = 'flex';
      n.querySelector('div').innerHTML = `Pre-filled from <a href="record.html?id=${E(from)}">${E(from)}</a>. Automatic values may be wrong — please check every field.`;
    }
  }
  if (!$('entities').children.length) addEntity();

  // build record
  const num = id => $(id).value === '' ? null : +$(id).value;
  const q = (v, unit, extra = {}) => v == null ? undefined : { value: v, unit, ...extra, evidence: { method: 'author_submitted', confidence: 'high' } };
  const clean = o => JSON.parse(JSON.stringify(o, (k, v) => (v === '' || v == null || (Array.isArray(v) && !v.length)) ? undefined : v));
  $('sub-form').onsubmit = ev => {
    ev.preventDefault();
    const ents = [...document.querySelectorAll('.ent-row')].map(d => ({
      name: d.querySelector('.e-name').value.trim(), entity_type: d.querySelector('.e-type').value, role: d.querySelector('.e-role').value,
      identifiers: d.querySelector('.e-ids').value.split(',').map(s => s.trim()).filter(Boolean).map(s => { const [scheme, ...rest] = s.split(':'); return { scheme: scheme.toLowerCase(), id: rest.join(':') }; }),
      organism: d.querySelector('.e-org').value ? { ncbi_taxon: +d.querySelector('.e-org').value } : undefined,
      region: d.querySelector('.e-region').value, sequence: d.querySelector('.e-seq').value,
      fluorescent_labels: d.querySelector('.e-label').value ? [{ identifier: d.querySelector('.e-label').value }] : undefined,
      evidence: { method: 'author_submitted', confidence: 'high' }
    })).filter(e => e.name);
    const units = X.$defs.ObservableUnits.const;
    const res = [...document.querySelectorAll('.res-row')].map(d => {
      const qn = d.querySelector('.r-q').value, v = d.querySelector('.r-v').value;
      return v === '' ? null : { quantity: qn, value: +v, unit: units[qn] || '', uncertainty: d.querySelector('.r-u').value === '' ? undefined : +d.querySelector('.r-u').value,
        applies_to: { entity: d.querySelector('.r-a').value }, model: d.querySelector('.r-m').value, method: d.querySelector('.r-c').value,
        source: { location: 'results_text', extraction: 'author_submitted', confidence: 'high' } };
    }).filter(Boolean);
    const tech = $('f-tech').value, optical = ['optical_tweezers', 'torque_tweezers'].includes(tech);
    const rec = clean({
      record_id: 'SMFS-000000', schema_version: R.properties.schema_version.const,
      classification: {
        table3_type: ((S.moduleMeta || {})[$('f-module').value] || {}).table3 || 'extended',
        modules: [{ module_id: $('f-module').value, role: 'primary', method: 'author', submodules: $('f-sub').value ? [$('f-sub').value] : [] }],
        assay_type: $('f-assay').value || undefined,
        bead_geometry: $('f-beadgeo').value || undefined,
        measurement_modes: chipsOf('f-modes'),
        processivity: $('f-proc').value,
        taxonomy_version: '1.0.0',
        correlative_fluorescence: { present: chipsOf('f-mods').length > 0, modalities: [] }
      },
      curation: { level: 'author_verified', last_updated: new Date().toISOString().slice(0, 10), curators: [$('f-email').value] },
      publication: { title: $('f-title').value, doi: $('f-doi').value, year: num('f-year'), journal: $('f-journal').value, authors: $('f-authors').value.split(';').map(s => s.trim()).filter(Boolean) },
      technique: { primary: tech, force_application_geometry: $('f-geom').value, correlative_modalities: chipsOf('f-mods') },
      hardware: {
        make_of_setup: $('f-make').value, model_number: $('f-model').value, detection_device: $('f-det').value ? $('f-det').value.split(',').map(s => s.trim()) : [],
        objective_lens: $('f-obj').value ? { model: $('f-obj').value } : undefined, temperature: q(num('f-temp'), 'K'), acquisition_rate: q(num('f-acq'), 'kHz'),
        filter_frequency: q(num('f-filt'), 'Hz'), calibration_technique: $('f-cal').value ? [$('f-cal').value] : [],
        optical: optical ? { laser_wavelength: q(num('f-wl'), 'nm'), laser_power_at_objective: q(num('f-pw'), 'mW'), trap_stiffness: q(num('f-k'), 'pN/nm', num('f-ku') != null ? { uncertainty: num('f-ku'), uncertainty_type: 'SD' } : {}) } : undefined,
        afm: tech === 'afm_smfs' ? { spring_constant: q(num('f-k'), 'pN/nm') } : undefined
      },
      assay: { experiment_class: chipsOf('f-classes'), bead_size: q(num('f-bead'), 'nm'), bead_functionalization: $('f-func').value.split(';').map(s => s.trim()).filter(Boolean),
        trap_control: $('f-ctrl').value ? [$('f-ctrl').value] : [], handle_sequences: $('f-handles').value ? [{ fasta: $('f-handles').value }] : [], loading_rate_text: $('f-lr').value },
      biological_system: { system_class: chipsOf('f-classes'), entities: ents },
      solution: { buffer: $('f-buf').value, pH: num('f-ph'), small_molecules: $('f-sm').value.split('\n').filter(Boolean).map(l => { const [name, idf, c] = l.split(';').map(s => s.trim()); return { name, [idf && /^\d+-\d+-\d$/.test(idf) ? 'cas' : 'smiles']: idf, concentration: c ? { value: +c, unit: 'nM' } : undefined }; }) },
      results: res,
      data_availability: {
        status: $('f-ds').value ? 'public_repository' : ($('f-code').value ? 'code_only' : 'not_stated'), has_linked_dataset: !!$('f-ds').value,
        datasets: $('f-ds').value ? [{ id: $('f-ds').value, file_formats: $('f-fmt').value.split(',').map(s => s.trim()).filter(Boolean), content: $('f-raw').value === '1' ? 'raw_traces' : 'unknown', linked_by: ['manual'] }] : [],
        code: $('f-code').value ? [{ id: $('f-code').value, linked_by: ['manual'] }] : [], raw_traces_available: $('f-raw').value === '1'
      }
    });
    const txt = JSON.stringify(rec, null, 2);
    $('out').style.display = 'block'; $('out').textContent = txt;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([txt], { type: 'application/json' }));
    a.download = `smash-record-${(rec.publication.doi || 'new').replace(/[^\w.-]+/g, '_')}.json`; a.click();
    const cp = $('copy-json'); cp.disabled = false;
    cp.onclick = () => navigator.clipboard && navigator.clipboard.writeText(txt).then(() => { cp.innerHTML = '<i class="fas fa-check"></i> Copied'; });
    $('mail').href = `mailto:mhalma@opensourcemed.info?subject=${encodeURIComponent('SMASH-BIO record: ' + (rec.publication.title || ''))}&body=${encodeURIComponent('Please find the SMASH-BIO JSON record attached.\nDOI: ' + (rec.publication.doi || '') + (from ? '\nCorrection to: ' + from : ''))}`;
  };
})();
