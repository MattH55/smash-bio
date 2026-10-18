// System page: all simulations of one molecule, grouped by model family, beside matched experiments.
document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('sim-banner').innerHTML = SIM.banner();
  const params = new URLSearchParams(location.search);
  const wanted = (params.get('system') || '').toLowerCase();
  const records = (SIM.data().full || []).filter((record) =>
    String(record.system.name || '').toLowerCase() === wanted);
  const body = document.getElementById('sys-body');

  if (!records.length) {
    const systems = SIM.systems();
    body.innerHTML = '<p class="sim-empty">No indexed simulation for that system.</p>'
      + '<h2>Systems with simulations</h2><ul class="prose">'
      + systems.slice(0, 60).map((entry) =>
          `<li><a href="system.html?system=${encodeURIComponent(entry.system)}">`
          + `${SIM.esc(entry.system)}</a> <span class="muted small">(${entry.records.length})</span></li>`).join('')
      + '</ul>';
    return;
  }

  const name = records[0].system.name;
  const moleculeType = records[0].system.molecule_type;
  document.getElementById('sys-crumb').textContent = name;
  document.getElementById('sys-title').textContent = name;
  document.title = (window.SMASH && SMASH.text ? SMASH.text(name) : name) + ' | SMASH-BIO Simulations (beta)';
  const matched = SIM.matches().filter((match) =>
    records.some((record) => record.record_id === match.sim_record_id));
  const experimentHref = '../system.html?s=' + encodeURIComponent(window.SMASH.slug(name));
  document.getElementById('sys-lede').innerHTML =
    `${records.length} simulation record${records.length === 1 ? '' : 's'} `
    + `(${SIM.esc(SIM.label(moleculeType))}) · ${matched.length} experimental link`
    + `${matched.length === 1 ? '' : 's'}. `
    + `<a href="${experimentHref}">Experimental studies of this name</a> stay on the force-spectroscopy system page.`;

  const groups = {};
  records.forEach((record) => {
    const family = record.model.family || 'other';
    (groups[family] = groups[family] || []).push(record);
  });

  const unitNote = (record) => {
    const system = record.model.unit_system;
    if (system === 'reduced') {
      return '<div class="sim-axis-note">Reduced units, no stated conversion: these values are never '
        + 'placed on a shared physical axis.</div>';
    }
    if (system === 'reduced_with_stated_conversion') {
      const conversions = record.model.unit_conversions || {};
      const parts = Object.entries(conversions)
        .filter(([key]) => key !== 'statement' && key !== 'evidence')
        .map(([key, value]) => `${SIM.label(key)} = ${value.value} ${value.unit}`);
      return '<div class="sim-axis-note">Reduced units with the stated conversion: '
        + SIM.esc(parts.join(', ') || 'see the paper') + '.</div>';
    }
    return '';
  };

  const resultRows = (record) => (record.results || []).map((result) => {
    let shown = result.value;
    if (shown == null && result.min != null) { shown = '≥ ' + result.min; }
    if (shown == null && result.max != null) { shown = '≤ ' + result.max; }
    return `<tr><td>${SIM.esc(SIM.label(result.quantity))}</td>`
      + `<td class="num">${SIM.esc(shown == null ? '' : shown)}</td>`
      + `<td>${SIM.esc(result.unit)}</td>`
      + `<td>${SIM.esc(result.unit_system === 'reduced' ? 'reduced' : '')}</td></tr>`;
  }).join('');

  const experimentRows = (record) => {
    const links = (record.links || {}).experimental_matches || [];
    if (!links.length) {
      return '<tr><td colspan="4" class="muted">No experimental record matched this simulation.</td></tr>';
    }
    return links.map((link) =>
      `<tr><td>${SIM.esc(link.molecule || link.record_id)}</td>`
      + `<td class="num">${link.force_pN == null ? '' : SIM.esc(link.force_pN)}</td>`
      + `<td>${SIM.esc(link.source || '')}</td>`
      + `<td>${SIM.esc(SIM.label(link.match_level))}</td></tr>`).join('');
  };

  body.innerHTML = Object.entries(groups).map(([family, familyRecords]) => {
    const blocks = familyRecords.map((record) => `
      <div class="card sim-card" style="margin-bottom:14px">
        <div class="sim-meta">${SIM.tag(SIM.label(family))}
          ${SIM.tag(SIM.label(record.model.unit_system), 'reduced')}
          <span class="muted small">${SIM.esc(record.record_id)}</span></div>
        <h3>${SIM.esc(record.source.title || 'Untitled')}</h3>
        <p class="muted small">${SIM.esc(record.source.journal || '')} ${SIM.esc(record.source.year || '')}
          ${record.source.doi ? ' · <a href="https://doi.org/' + SIM.esc(record.source.doi) + '" rel="noopener">doi</a>' : ''}
          ${record.source.url ? ' · <a href="' + SIM.esc(record.source.url) + '" rel="noopener">source</a>' : ''}</p>
        <dl class="sim-kv">
          <div><dt>Model</dt><dd>${SIM.esc(SIM.label(record.model.family))}
            ${record.model.force_field ? ' · ' + SIM.esc(record.model.force_field) : ''}
            ${record.model.solvent ? ' · ' + SIM.esc(record.model.solvent) + ' solvent' : ''}</dd></div>
          <div><dt>Software</dt><dd>${SIM.esc((record.model.software || []).map((s) => s.name).join(', ') || 'not stated')}</dd></div>
          <div><dt>Protocol</dt><dd>${SIM.esc(SIM.label(record.protocol.mode))}
            ${record.protocol.pulling_speed ? ' · ' + SIM.esc(record.protocol.pulling_speed.value + ' ' + record.protocol.pulling_speed.unit) : ''}</dd></div>
          <div><dt>Geometry</dt><dd>${SIM.esc(SIM.label((record.protocol.geometry || {}).force_application_geometry || 'not stated'))}</dd></div>
          <div><dt>Construct</dt><dd>${SIM.esc((record.system.construct || {}).residue_range || (record.system.construct || {}).nucleotide_range || 'not stated')}</dd></div>
          <div><dt>Data</dt><dd>${SIM.esc(SIM.label(record.data_availability.status))}</dd></div>
        </dl>
        ${unitNote(record)}
        <div class="sim-vs">
          <div class="sim-side-sim"><h4>Simulation — reported values</h4>
            <table class="sim-table"><thead><tr><th>Quantity</th><th>Value</th><th>Unit</th><th>Units</th></tr></thead>
            <tbody>${resultRows(record) || '<tr><td colspan="4" class="muted">No numeric result extracted.</td></tr>'}</tbody></table></div>
          <div class="sim-side-exp"><h4>Experiment — matched records</h4>
            <table class="sim-table"><thead><tr><th>Molecule</th><th>Force (pN)</th><th>Source</th><th>Match</th></tr></thead>
            <tbody>${experimentRows(record)}</tbody></table>
            <div class="sim-axis-note">Experimental values come from the force-spectroscopy index
              (and MechanoProDB where noted) and are shown beside — never merged into — the
              simulation.</div></div>
        </div>
      </div>`).join('');
    return `<section class="section"><h2>${SIM.esc(SIM.label(family))}
      <span class="muted small">(${familyRecords.length})</span></h2>${blocks}</section>`;
  }).join('');
});