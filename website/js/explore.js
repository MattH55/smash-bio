// Explore page: faceted search over SMASH.index
(function () {
  const S = window.SMASH;
  const rows = S.index || [];
  const PER = 25;

  // facet definitions: key -> {label, get(row) -> array of values, fmt}
  const FACETS = [
    { key: 'tech', label: 'Technique', get: r => [r.tech, ...r.tech2], fmt: S.tl, open: true },
    { key: 'st', label: 'Data availability', get: r => [r.st], fmt: S.sl, open: true, order: k => (S.STATUS[k] || {}).rank },
    { key: 'cls', label: 'Experiment class (Table 3)', get: r => r.cls, fmt: S.cl, open: true },
    { key: 'ent', label: 'Molecule / system', get: r => r.ent, fmt: x => x, limit: 10 },
    { key: 'et', label: 'Entity type', get: r => r.et, fmt: x => x.replace(/_/g, ' ') },
    { key: 'org', label: 'Organism', get: r => r.org, fmt: x => x, limit: 8 },
    { key: 'vend', label: 'Instrument make', get: r => r.vend ? [r.vend] : [], fmt: x => x === 'custom' ? 'Custom-built' : x, limit: 8 },
    { key: 'repo', label: 'Repository', get: r => r.repo, fmt: x => x, limit: 8 },
    { key: 'mod', label: 'Correlative modality', get: r => r.mod, fmt: x => x.replace(/_/g, ' ') },
    { key: 'geo', label: 'Force geometry', get: r => r.geo ? [r.geo] : [], fmt: x => x.replace(/_/g, ' '), limit: 8 },
    { key: 'obs', label: 'Reported result', get: r => r.obs, fmt: x => S.OBS[x] || x, limit: 8 },
    { key: 'kind', label: 'Article type', get: r => [r.kind], fmt: x => S.KIND[x] || x },
    { key: 'cur', label: 'Curation level', get: r => [r.cur], fmt: x => S.CURATION[x] || x },
  ];
  const TOGGLES = [
    { key: 'ds', label: 'Has linked public dataset', test: r => r.ds },
    { key: 'raw', label: 'Raw force traces deposited', test: r => r.raw },
    { key: 'code', label: 'Has linked code', test: r => r.code },
    { key: 'res', label: 'Has extracted results', test: r => r.nres > 0 },
    { key: 'oa', label: 'Open access', test: r => r.oa },
  ];

  rows.forEach(r => {
    r._h = [r.t, r.a, r.j, r.doi, r.pm, r.ent.join(' '), r.tm.join(' '), r.org.join(' '), r.uni.join(' '), S.tl(r.tech), r.cls.map(S.cl).join(' '), r.vend, r.kw]
      .filter(Boolean).join(' ').toLowerCase();
  });

  // ---------------------------------------------------------- state <-> URL
  const state = { q: '', sel: {}, tog: {}, y0: null, y1: null, sort: 'year', page: 1, view: S.store.get('view', 'cards') };
  const p = S.qs();
  state.q = p.get('q') || '';
  FACETS.forEach(f => { const v = p.getAll(f.key); if (v.length) state.sel[f.key] = new Set(v); });
  TOGGLES.forEach(t => { if (p.get(t.key) === '1') state.tog[t.key] = true; });
  if (p.get('y0')) state.y0 = +p.get('y0');
  if (p.get('y1')) state.y1 = +p.get('y1');
  if (p.get('sort')) state.sort = p.get('sort');
  if (window.innerWidth < 960) state.view = 'cards';

  function writeURL() {
    const u = new URLSearchParams();
    if (state.q) u.set('q', state.q);
    Object.entries(state.sel).forEach(([k, set]) => set.forEach(v => u.append(k, v)));
    Object.keys(state.tog).forEach(k => state.tog[k] && u.set(k, '1'));
    if (state.y0) u.set('y0', state.y0);
    if (state.y1) u.set('y1', state.y1);
    if (state.sort !== 'year') u.set('sort', state.sort);
    history.replaceState(null, '', location.pathname + (u.toString() ? '?' + u : ''));
  }

  // ---------------------------------------------------------- filtering
  const terms = () => state.q.toLowerCase().split(/\s+/).filter(Boolean);
  function passes(r, skip) {
    const ts = terms();
    for (const t of ts) if (!r._h.includes(t)) return false;
    for (const f of FACETS) {
      if (f.key === skip) continue;
      const s = state.sel[f.key];
      if (s && s.size) { const vals = f.get(r); if (!vals.some(v => s.has(v))) return false; }
    }
    for (const t of TOGGLES) if (state.tog[t.key] && t.key !== skip && !t.test(r)) return false;
    if (skip !== 'year') {
      if (state.y0 && (r.y || 0) < state.y0) return false;
      if (state.y1 && (r.y || 9999) > state.y1) return false;
    }
    return true;
  }
  const DATA_RANK = r => (r.raw ? -1 : 0) + ((S.STATUS[r.st] || {}).rank ?? 9);
  const SORTS = {
    year: (a, b) => (b.y || 0) - (a.y || 0) || b.cit - a.cit,
    cited: (a, b) => b.cit - a.cit,
    fair: (a, b) => b.fair - a.fair || (b.y || 0) - (a.y || 0),
    data: (a, b) => DATA_RANK(a) - DATA_RANK(b) || (b.y || 0) - (a.y || 0),
    title: (a, b) => (a.t || '').localeCompare(b.t || ''),
  };

  // ---------------------------------------------------------- facets UI
  const facetEl = document.getElementById('facets');
  const expanded = {};
  function renderFacets() {
    let html = `<div class="filter-group"><div class="facet-list" style="margin-top:0">` +
      TOGGLES.map(t => {
        const n = rows.filter(r => passes(r, t.key) && t.test(r)).length;
        return `<label class="facet${n ? '' : ' zero'}"><input type="checkbox" data-tog="${t.key}" ${state.tog[t.key] ? 'checked' : ''}><span class="fname">${t.label}</span><span class="fcount">${S.fmt(n)}</span></label>`;
      }).join('') + `</div></div>`;
    const years = rows.map(r => r.y).filter(Boolean);
    const ymin = Math.min(...years), ymax = Math.max(...years);
    html += `<details class="filter-group" open><summary>Publication year</summary>
      <div class="range-row"><input type="number" id="y0" min="${ymin}" max="${ymax}" placeholder="${ymin}" value="${state.y0 || ''}" aria-label="From year">
      <span class="muted">–</span><input type="number" id="y1" min="${ymin}" max="${ymax}" placeholder="${ymax}" value="${state.y1 || ''}" aria-label="To year"></div></details>`;
    FACETS.forEach(f => {
      const counts = new Map();
      rows.forEach(r => { if (passes(r, f.key)) new Set(f.get(r)).forEach(v => { if (v) counts.set(v, (counts.get(v) || 0) + 1); }); });
      const sel = state.sel[f.key] || new Set();
      sel.forEach(v => { if (!counts.has(v)) counts.set(v, 0); });
      let items = [...counts.entries()];
      items.sort(f.order ? (a, b) => f.order(a[0]) - f.order(b[0]) : (a, b) => b[1] - a[1]);
      const lim = f.limit && !expanded[f.key] ? f.limit : Infinity;
      const shown = items.filter((it, i) => i < lim || sel.has(it[0]));
      if (!items.length) return;
      const isOpen = f.open || sel.size || S.store.get('open:' + f.key, false);
      html += `<details class="filter-group" data-f="${f.key}" ${isOpen ? 'open' : ''}><summary>${f.label}${sel.size ? ` <span class="badge badge-accent">${sel.size}</span>` : ''}</summary><div class="facet-list">` +
        shown.map(([v, n]) => `<label class="facet${n ? '' : ' zero'}"><input type="checkbox" data-f="${f.key}" value="${S.esc(v)}" ${sel.has(v) ? 'checked' : ''}><span class="fname" title="${S.esc(f.fmt(v))}">${S.esc(f.fmt(v))}</span><span class="fcount">${S.fmt(n)}</span></label>`).join('') +
        `</div>${items.length > shown.length || expanded[f.key] ? `<button class="facet-more" data-more="${f.key}">${expanded[f.key] ? 'Show fewer' : `Show all ${items.length}`}</button>` : ''}</details>`;
    });
    facetEl.innerHTML = html;
  }
  facetEl.addEventListener('change', e => {
    const t = e.target;
    if (t.dataset.tog) { state.tog[t.dataset.tog] = t.checked; }
    else if (t.dataset.f) {
      const s = state.sel[t.dataset.f] || (state.sel[t.dataset.f] = new Set());
      t.checked ? s.add(t.value) : s.delete(t.value);
    } else if (t.id === 'y0' || t.id === 'y1') { state[t.id] = t.value ? +t.value : null; }
    state.page = 1; update();
  });
  facetEl.addEventListener('click', e => {
    const b = e.target.closest('[data-more]');
    if (b) { expanded[b.dataset.more] = !expanded[b.dataset.more]; renderFacets(); }
  });
  facetEl.addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.f) S.store.set('open:' + d.dataset.f, d.open); }, true);

  // ---------------------------------------------------------- active chips
  function renderActive() {
    const chips = [];
    if (state.q) chips.push(['q', null, `“${state.q}”`]);
    TOGGLES.forEach(t => state.tog[t.key] && chips.push(['tog', t.key, t.label]));
    FACETS.forEach(f => (state.sel[f.key] || new Set()).forEach(v => chips.push([f.key, v, f.fmt(v)])));
    if (state.y0 || state.y1) chips.push(['year', null, `${state.y0 || '…'}–${state.y1 || '…'}`]);
    const el = document.getElementById('active');
    el.innerHTML = chips.map(([k, v, l], i) => `<button class="chip active" data-i="${i}">${S.esc(l)} <span class="x">✕</span></button>`).join('') +
      (chips.length > 1 ? `<button class="chip" data-clear="1">Clear all</button>` : '');
    el.onclick = e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.clear) { state.q = ''; state.sel = {}; state.tog = {}; state.y0 = state.y1 = null; document.getElementById('q').value = ''; }
      else {
        const [k, v] = chips[+b.dataset.i];
        if (k === 'q') { state.q = ''; document.getElementById('q').value = ''; }
        else if (k === 'tog') delete state.tog[v];
        else if (k === 'year') state.y0 = state.y1 = null;
        else state.sel[k].delete(v);
      }
      state.page = 1; update();
    };
    const nf = chips.filter(c => c[0] !== 'q').length;
    document.getElementById('nf').textContent = nf ? `(${nf})` : '';
  }

  // ---------------------------------------------------------- results
  let current = [];
  function card(r) {
    return `<article class="result-card">
      <h3><a href="record.html?id=${r.id}">${S.esc(r.t || 'Untitled')}</a></h3>
      <div class="side">${S.statusPill(r.st)}${r.raw ? '<span class="badge badge-good"><i class="fas fa-wave-square"></i> raw traces</span>' : ''}
        <span class="fair-mini" title="Table 3 metadata completeness">FAIR <span class="bar"><span style="width:${Math.round(r.fair * 100)}%"></span></span>${Math.round(r.fair * 100)}%</span></div>
      <div class="meta"><span>${S.esc(r.a)}</span><span>${r.y || ''}</span><span>${S.esc(r.j || '')}</span>${r.kind !== 'primary_research' ? `<span class="badge">${S.esc(S.KIND[r.kind] || r.kind)}</span>` : ''}${r.cur === 'curated' || r.cur === 'author_verified' ? `<span class="badge badge-good"><i class="fas fa-star"></i> ${r.cur === 'curated' ? 'curated' : 'author verified'}</span>` : r.cur === 'ai_assisted' ? '<span class="badge badge-accent" title="Fields reviewed by an LLM against the open full text; not yet human-checked"><i class="fas fa-wand-magic-sparkles"></i> AI-assisted</span>' : ''}</div>
      <div class="system"><b>${S.esc(S.tl(r.tech))}</b>${r.ent.length ? ' · ' + S.esc(r.ent.slice(0, 4).join(', ')) : ''}${r.org.length ? ' · <i>' + S.esc(r.org.slice(0, 2).join(', ')) + '</i>' : ''}${r.vend ? ' · ' + S.esc(r.vend === 'custom' ? 'custom instrument' : r.vend) : ''}</div>
      <div class="badges">${r.cls.slice(0, 3).map(c => `<span class="badge">${S.esc(S.cl(c))}</span>`).join('')}${r.repo.map(x => `<span class="badge badge-accent">${S.esc(x)}</span>`).join('')}${r.nres ? `<span class="badge"><i class="fas fa-ruler"></i> ${r.nres} result${r.nres > 1 ? 's' : ''}</span>` : ''}</div>
    </article>`;
  }
  function table(list) {
    return `<div class="data-table-wrap"><table class="data-table"><thead><tr><th>Year</th><th>Title</th><th>Technique</th><th>System</th><th>Organism</th><th>Data</th><th>FAIR</th></tr></thead><tbody>` +
      list.map(r => `<tr><td class="num">${r.y || ''}</td><td class="t-title"><a href="record.html?id=${r.id}">${S.esc(r.t)}</a><div class="muted small">${S.esc(r.a)} · ${S.esc(r.j || '')}</div></td>
        <td>${S.esc(S.TECH[r.tech] ? S.TECH[r.tech].short : r.tech)}</td><td>${S.esc(r.ent.slice(0, 2).join(', '))}</td><td><i>${S.esc(r.org[0] || '')}</i></td>
        <td>${S.statusPill(r.st)}</td><td class="num">${Math.round(r.fair * 100)}%</td></tr>`).join('') + `</tbody></table></div>`;
  }
  function renderResults() {
    const el = document.getElementById('results');
    const start = (state.page - 1) * PER, list = current.slice(start, start + PER);
    document.getElementById('count').innerHTML = `<b>${S.fmt(current.length)}</b> of ${S.fmt(rows.length)} studies` +
      (current.length ? ` · ${S.fmt(current.filter(r => r.ds).length)} with a linked dataset` : '');
    if (!list.length) { el.innerHTML = `<div class="empty"><i class="fas fa-flask"></i>No studies match these filters.</div>`; document.getElementById('pagination').innerHTML = ''; return; }
    el.innerHTML = state.view === 'table' ? table(list) : `<div class="result-list">${list.map(card).join('')}</div>`;
    renderPagination();
  }
  function renderPagination() {
    const pages = Math.ceil(current.length / PER), cur = state.page;
    const btn = (lbl, pg, dis, act, aria) => `<button ${dis ? 'disabled' : ''} class="${act ? 'active' : ''}" data-p="${pg}" aria-label="${aria || 'Page ' + pg}">${lbl}</button>`;
    let h = btn('<i class="fas fa-chevron-left"></i>', cur - 1, cur === 1, false, 'Previous page');
    const nums = new Set([1, pages, cur - 1, cur, cur + 1].filter(n => n >= 1 && n <= pages));
    let last = 0;
    [...nums].sort((a, b) => a - b).forEach(n => { if (n - last > 1) h += '<button disabled>…</button>'; h += btn(n, n, false, n === cur); last = n; });
    h += btn('<i class="fas fa-chevron-right"></i>', cur + 1, cur === pages, false, 'Next page');
    const pg = document.getElementById('pagination');
    pg.innerHTML = pages > 1 ? h : '';
    pg.onclick = e => { const b = e.target.closest('button[data-p]'); if (b && !b.disabled) { state.page = +b.dataset.p; renderResults(); window.scrollTo({ top: 0, behavior: 'smooth' }); } };
  }

  function update() {
    current = rows.filter(r => passes(r)).sort(SORTS[state.sort] || SORTS.year);
    renderFacets(); renderActive(); renderResults(); writeURL();
  }

  // ---------------------------------------------------------- controls
  const qEl = document.getElementById('q');
  qEl.value = state.q;
  let deb;
  qEl.addEventListener('input', () => { clearTimeout(deb); deb = setTimeout(() => { state.q = qEl.value.trim(); state.page = 1; update(); }, 180); });
  const sortEl = document.getElementById('sort');
  sortEl.value = state.sort;
  sortEl.onchange = () => { state.sort = sortEl.value; state.page = 1; update(); };
  const viewBtn = document.getElementById('view-btn');
  const setViewLabel = () => { viewBtn.querySelector('span').textContent = state.view === 'table' ? 'Cards' : 'Table'; viewBtn.querySelector('i').className = 'fas ' + (state.view === 'table' ? 'fa-list' : 'fa-table'); };
  setViewLabel();
  viewBtn.onclick = () => { state.view = state.view === 'table' ? 'cards' : 'table'; S.store.set('view', state.view); setViewLabel(); renderResults(); };
  const fEl = document.getElementById('filters'), scrim = document.getElementById('scrim');
  const openF = o => { fEl.classList.toggle('open', o); scrim.classList.toggle('open', o); document.body.style.overflow = o ? 'hidden' : ''; };
  document.getElementById('open-filters').onclick = () => openF(true);
  document.getElementById('close-filters').onclick = () => openF(false);
  scrim.onclick = () => openF(false);
  document.getElementById('dl-csv').onclick = () => {
    const head = ['record_id', 'year', 'title', 'first_author', 'journal', 'doi', 'technique', 'experiment_classes', 'entities', 'uniprot', 'organisms', 'instrument', 'data_status', 'has_dataset', 'raw_traces', 'repositories', 'fair'];
    const q = v => `"${String(v == null ? '' : v).replace(/"/g, '""')}"`;
    const lines = [head.join(',')].concat(current.map(r => [r.id, r.y, r.t, r.a, r.j, r.doi, r.tech, r.cls.join(';'), r.ent.join(';'), r.uni.join(';'), r.org.join(';'), r.vend, r.st, r.ds, r.raw, r.repo.join(';'), r.fair].map(q).join(',')));
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' }));
    a.download = `smash-bio-selection-${current.length}.csv`; a.click();
  };
  document.addEventListener('keydown', e => { if (e.key === '/' && document.activeElement !== qEl) { e.preventDefault(); qEl.focus(); } });

  update();
})();
