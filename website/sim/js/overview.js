// Overview page: live counts by molecule type and model family, plus recent records.
document.addEventListener('DOMContentLoaded', function () {
  const d = SIM.data();
  const meta = d.meta || {};
  const aggregation = meta.aggregation || {};
  document.getElementById('sim-banner').innerHTML = SIM.banner();

  const set = (id, value) => {
    const node = document.getElementById(id);
    if (node) { node.textContent = value; }
  };
  set('k-records', meta.n_records || 0);
  set('k-datasets', Object.keys(aggregation.source_kind || {}).length + ' source kinds');
  set('k-families', Object.keys(aggregation.model_family || {})
    .filter((name) => name !== 'other').length + ' named');
  // Match levels per record (data/matches.js): 'homolog' = shared token in the molecule name only;
  // 'same_molecule_*' = shared identifier (UniProt/Rfam/...). A matched geometry needs '*_same_geometry'.
  const recs = d.records || [];
  const lv = (r) => r.match_levels || [];
  const linked = recs.filter((r) => lv(r).length).length;
  const sameMol = recs.filter((r) => lv(r).some((l) => l.startsWith('same_molecule'))).length;
  const nameOnly = recs.filter((r) => lv(r).length && lv(r).every((l) => l === 'homolog')).length;
  const sameGeom = recs.filter((r) => lv(r).some((l) => l.endsWith('same_geometry'))).length;
  set('k-matched', linked + ' / ' + (meta.n_records || 0));
  set('k-matched-sub', sameMol + ' same molecule (shared ID) · ' + nameOnly + ' by molecule name only · ' + sameGeom + ' matched geometry');
  set('k-results', (d.records || []).reduce((sum, record) => sum + (record.nres || 0), 0));

  const total = meta.n_records || 0;
  SIM.bars(document.getElementById('chart-molecule'),
           Object.entries(aggregation.molecule_type || {}), total);
  SIM.bars(document.getElementById('chart-family'),
           Object.entries(aggregation.model_family || {}), total);

  const recent = (d.records || []).slice()
    .sort((a, b) => (b.year || 0) - (a.year || 0))
    .slice(0, 6);
  const node = document.getElementById('sim-recent');
  node.innerHTML = recent.length ? recent.map(SIM.compactCard).join('')
    : '<p class="sim-empty">No simulation records have been indexed yet.</p>';

  const downloads = document.getElementById('sim-downloads');
  if (downloads) {
    downloads.innerHTML = '<a class="btn btn-secondary btn-sm" href="../downloads/sim/smash-sim-records.jsonl.gz">'
      + 'simulation records (jsonl.gz)</a> <a class="btn btn-secondary btn-sm" '
      + 'href="../downloads/sim/smash-sim-summary.csv">summary (csv)</a>';
  }
});