// Explore page: faceted filtering over the compact simulation records.
document.addEventListener('DOMContentLoaded', function () {
  const records = SIM.data().records || [];
  document.getElementById('sim-banner').innerHTML = SIM.banner();
  const ids = ['f-molecule', 'f-family', 'f-unit', 'f-mode', 'f-match', 'f-data'];
  const state = { q: '', molecule: '', family: '', unit: '', mode: '', match: '', data: '', sort: 'year' };
  const body = document.getElementById('f-results');

  const values = (key) => {
    const set = new Set();
    records.forEach((record) => {
      if (key === 'match') {
        (record.match_levels || []).forEach((level) => set.add(level));
        if (!record.matches) { set.add('none'); }
      } else {
        set.add(record[key] == null ? 'unknown' : record[key]);
      }
    });
    return Array.from(set).sort();
  };

  const fill = (id, key, anyLabel) => {
    const select = document.getElementById(id);
    select.innerHTML = `<option value="">${anyLabel}</option>`
      + values(key).map((value) => `<option value="${SIM.esc(value)}">${SIM.esc(SIM.label(value))}</option>`).join('');
    select.addEventListener('change', () => { state[key] = select.value; render(); });
  };
  fill('f-molecule', 'molecule_type', 'Any molecule');
  fill('f-family', 'family', 'Any model family');
  fill('f-unit', 'unit_system', 'Any unit system');
  fill('f-mode', 'mode', 'Any protocol');
  fill('f-match', 'match', 'Any match level');
  fill('f-data', 'data', 'Any data status');

  const query = document.getElementById('f-q');
  query.addEventListener('input', () => { state.q = query.value.toLowerCase().trim(); render(); });
  document.getElementById('f-sort').addEventListener('change', (event) => {
    state.sort = event.target.value; render();
  });
  document.getElementById('f-reset').addEventListener('click', () => {
    window.location.search = '';
  });

  function matches(record) {
    if (state.molecule && record.molecule_type !== state.molecule) { return false; }
    if (state.family && record.family !== state.family) { return false; }
    if (state.unit && record.unit_system !== state.unit) { return false; }
    if (state.mode && record.mode !== state.mode) { return false; }
    if (state.data && record.data !== state.data) { return false; }
    if (state.match) {
      const levels = (record.match_levels || []).slice();
      if (!record.matches) { levels.push('none'); }
      if (!levels.includes(state.match)) { return false; }
    }
    if (state.q) {
      const haystack = [record.system, record.title, record.doi, record.journal,
                        (record.software || []).join(' '), record.id,
                        record.family, record.mode].join(' ').toLowerCase();
      if (!haystack.includes(state.q)) { return false; }
    }
    return true;
  }

  function render() {
    let rows = records.filter(matches);
    if (state.sort === 'system') {
      rows = rows.slice().sort((a, b) => String(a.system).localeCompare(String(b.system)));
    } else if (state.sort === 'matches') {
      rows = rows.slice().sort((a, b) => (b.matches || 0) - (a.matches || 0));
    } else if (state.sort === 'fair') {
      rows = rows.slice().sort((a, b) => (b.fair || 0) - (a.fair || 0));
    } else {
      rows = rows.slice().sort((a, b) => (b.year || 0) - (a.year || 0));
    }
    document.getElementById('f-count').textContent =
      rows.length + ' of ' + records.length + ' simulation records';
    body.innerHTML = rows.length ? rows.map(SIM.compactCard).join('')
      : '<p class="sim-empty">No simulation matches these filters.</p>';
    const url = new URLSearchParams();
    Object.entries(state).forEach(([key, value]) => {
      if (value && key !== 'sort') { url.set(key, value); }
    });
    if (state.q) { url.set('q', state.q); }
    history.replaceState(null, '', url.toString() ? '?' + url.toString() : location.pathname);
  }

  // restore a shared view
  const url = new URLSearchParams(location.search);
  [['q', 'q'], ['molecule', 'f-molecule'], ['family', 'f-family'], ['unit', 'f-unit'],
   ['mode', 'f-mode'], ['match', 'f-match'], ['data', 'f-data']].forEach(([key, control]) => {
    const value = url.get(key);
    if (!value) { return; }
    if (key === 'q') { state.q = value; query.value = value; }
    else { state[key] = value; document.getElementById(control).value = value; }
  });
  render();
});