// Coverage page: computed from the published records and the match table, so the numbers
// always describe the same corpus the downloads contain.
document.addEventListener('DOMContentLoaded', function () {
  const d = SIM.data();
  const meta = d.meta || {};
  const aggregation = meta.aggregation || {};
  const records = d.records || [];
  const matches = SIM.matches();
  document.getElementById('sim-banner').innerHTML = SIM.banner();

  const byId = {};
  records.forEach((record) => { byId[record.id] = record; });

  // one row per (molecule type, model family, match level) -> distinct experimental systems
  const coverage = {};
  const matchedSystems = new Set();
  matches.forEach((match) => {
    const record = byId[match.sim_record_id];
    if (!record) { return; }
    const key = [record.molecule_type || 'unknown', record.family || 'unknown',
                 match.match_level].join(' · ');
    coverage[key] = coverage[key] || new Set();
    coverage[key].add(match.experimental_source + ':' + match.experimental_record_id);
    matchedSystems.add(match.experimental_source + ':' + match.experimental_record_id);
  });

  const kpis = [
    ['Simulation records', meta.n_records, Object.keys(aggregation.source_kind || {}).length + ' source kinds'],
    ['Experimental systems covered', matchedSystems.size, 'distinct records reached by a simulation'],
    ['Simulation ↔ experiment links', meta.n_matches, 'each with a match level'],
    ['Records with a linked experiment', Object.values(byId).filter((r) => r.matches).length,
     'of ' + (meta.n_records || 0) + ' records'],
  ];
  document.getElementById('sim-stats-kpis').innerHTML = kpis.map(([label, value, sub]) =>
    `<div class="stat-tile"><div class="label">${label}</div><div class="value">${value}</div>`
    + `<div class="sub">${sub}</div></div>`).join('');

  const coverageEntries = Object.entries(coverage)
    .map(([key, set]) => [key, set.size])
    .filter(([, value]) => value);
  SIM.bars(document.getElementById('chart-coverage'), coverageEntries,
           coverageEntries.reduce((sum, [, value]) => sum + value, 0));
  SIM.bars(document.getElementById('chart-match'),
           Object.entries(aggregation.match_level || {}), meta.n_records);
  SIM.bars(document.getElementById('chart-families'),
           Object.entries(aggregation.model_family || {}), meta.n_records);
  SIM.bars(document.getElementById('chart-units'),
           Object.entries(aggregation.unit_system || {}), meta.n_records);
  SIM.bars(document.getElementById('chart-modes'),
           Object.entries(aggregation.protocol_mode || {}), meta.n_records);

  const count = (key) => records.filter((record) => record[key]).length;
  SIM.bars(document.getElementById('chart-data'), [
    ['trajectories', count('trajectories')],
    ['force–extension curves', count('force_curves')],
    ['input files (topology, parameters)', count('input_files')],
    ['analysis scripts', count('scripts')],
    ['linked dataset in a repository',
     (aggregation.data_status || {}).public_repository || 0],
  ], meta.n_records);

  const perSystem = {};
  records.forEach((record) => {
    const key = record.system || record.id;
    perSystem[key] = (perSystem[key] || 0) + 1;
  });
  SIM.bars(document.getElementById('chart-systems'),
           Object.entries(perSystem).sort((a, b) => b[1] - a[1]).slice(0, 15),
           Math.max(1, ...Object.values(perSystem)));

  const unmatched = records.filter((record) => !record.matches);
  const node = document.getElementById('chart-unmatched');
  node.innerHTML = unmatched.length
    ? '<ul class="prose">' + unmatched.map((record) =>
        `<li><a href="system.html?system=${encodeURIComponent(record.system || '')}">`
        + `${SIM.esc(record.system || record.id)}</a> <span class="muted small">`
        + `${SIM.esc(SIM.label(record.family))} · ${SIM.esc(record.year || '')}</span></li>`).join('')
      + '</ul>'
    : '<p class="sim-empty">Every indexed simulation matched at least one experimental record.</p>';
});