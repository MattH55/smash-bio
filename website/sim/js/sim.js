// SMASH-SIM front-end helpers. Navigation and the footer come from the shared
// js/app.js, which prefixes links when the page is under /sim/. This file keeps
// the Simulation label, the separation banner, and the record cards.
window.SIM = (function () {
  const S = window.SMASH || {};

  const esc = (value) => (S.esc ? S.esc(value) : String(value == null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;'));

  const label = (value) => String(value == null ? '' : value)
    .replace(/_/g, ' ');

  const data = () => (S.sim || { meta: { aggregation: {} }, records: [], full: [] });

  function tag(text, kind) {
    return `<span class="sim-tag ${kind ? 'sim-tag-' + kind : ''}">${esc(text)}</span>`;
  }

  function banner() {
    return `<div class="sim-banner">${tag('Simulation')}${tag('Beta', 'beta')}
      <span><strong>This section is a beta feature.</strong> Simulations are not experiments.
      Every record here comes from a simulation (or a simulation database) and is kept separate
      from the experimental force-spectroscopy records. Where an experimental record is shown for
      comparison it is labelled <em>Experiment</em> and the two are never merged.</span></div>`;
  }

  function bars(container, entries, total) {
    const rows = entries.filter(([, value]) => value)
      .sort((a, b) => b[1] - a[1])
      .map(([name, value]) => {
        const pct = total ? Math.round((value / total) * 100) : 0;
        return `<div class="sim-bar-row"><span>${esc(label(name))}</span>
          <span class="sim-bar" style="width:${pct}%"></span>
          <span class="num">${value}</span></div>`;
      });
    container.innerHTML = rows.length ? `<div class="sim-bars">${rows.join('')}</div>`
      : '<p class="sim-empty">No data yet.</p>';
  }

  function compactCard(record) {
    const badges = [
      tag(record.kind === 'database' ? 'Database entry' : 'Simulation'),
      record.unit_system === 'reduced' || record.unit_system === 'reduced_with_stated_conversion'
        ? tag(label(record.unit_system), 'reduced') : '',
      record.matches ? tag(record.matches + ' experiment link' + (record.matches === 1 ? '' : 's'), 'match') : '',
    ].filter(Boolean).join(' ');
    const unitHint = record.unit_system === 'reduced'
      ? '<div class="sim-axis-note">Reduced units with no stated conversion: these values are never placed on a physical axis.</div>'
      : '';
    return `<article class="card sim-card">
      <div class="sim-meta">${badges}</div>
      <h3><a href="system.html?system=${encodeURIComponent(record.system || '')}">${esc(record.system || record.title)}</a></h3>
      <p class="muted small">${esc(record.title || '')}</p>
      <dl class="sim-kv">
        <div><dt>Model</dt><dd>${esc(label(record.family))}${record.software && record.software.length ? ' · ' + esc(record.software.join(', ')) : ''}</dd></div>
        <div><dt>Protocol</dt><dd>${esc(label(record.mode))}</dd></div>
        <div><dt>Molecule</dt><dd>${esc(label(record.molecule_type))}</dd></div>
        <div><dt>Data</dt><dd>${esc(label(record.data))}${record.trajectories ? ' · trajectories' : ''}</dd></div>
      </dl>
      ${unitHint}
      <div class="sim-meta small muted">
        <span>${esc(record.year || '')}${record.journal ? ' · ' + esc(record.journal) : ''}</span>
        ${record.doi ? `<a href="https://doi.org/${esc(record.doi)}" rel="noopener">doi</a>` : ''}
        <span>·</span><a href="index.html">${esc(record.id)}</a>
      </div>
    </article>`;
  }

  function recordsById() {
    const map = {};
    (data().full || []).forEach((record) => { map[record.record_id] = record; });
    return map;
  }

  document.addEventListener('DOMContentLoaded', () => {
    const slot = document.getElementById('sim-banner');
    if (slot && !slot.innerHTML) { slot.innerHTML = banner(); }
  });

  return { esc, label, tag, banner, bars, compactCard, recordsById, data,
           matches: () => S.simMatches || [], systems: () => S.simSystems || [] };
})();