// System page: one biological system across all studies
(function () {
  const S = window.SMASH, E = S.esc, root = document.getElementById('system');
  const q = S.qs(), key = q.get('s') || S.slug(q.get('name') || '');
  const s = (S.systems || []).find(x => x.slug === key);
  if (!s) {
    const nm = q.get('name') || key.replace(/-/g, ' ');
    root.innerHTML = `<div class="empty"><i class="fas fa-dna"></i>No system page for “${E(nm)}” yet (systems need at least two studies).<br><br>
      <a class="btn btn-secondary btn-sm" href="explore.html?q=${encodeURIComponent(nm)}">Search studies for “${E(nm)}”</a> <a class="btn btn-ghost btn-sm" href="systems.html">All systems</a></div>`;
    return;
  }
  document.title = `${S.text(s.name)} | SMASH-BIO`;
  const md = document.querySelector('meta[name="description"]');
  if (md) md.setAttribute('content', `${S.text(s.name)}: ${s.n} single-molecule force spectroscopy studies, reported forces, open datasets and database links.`);

  const u = s.uniprot || {}, w = s.wikipedia;
  const topT = Object.keys(s.techniques || {});
  const pct = s.n ? (100 * s.n_dataset / s.n).toFixed(0) : 0;

  // link-outs grouped
  const L = S.linkouts({ identifiers: s.identifiers, gene: s.gene, taxon: s.taxon, name: s.name, wikipedia: w });
  const groups = {};
  L.forEach(l => (groups[l.group] = groups[l.group] || []).push(l));
  const linkHtml = Object.entries(groups).map(([g, ls]) => `<div class="linkout-group"><div class="lg-title">${E(g)}</div><div class="chip-row">${ls.map(l => `<a class="idlink ext" href="${E(l.url)}" target="_blank" rel="noopener">${E(l.label)}</a>`).join('')}</div></div>`).join('');

  const desc = [];
  if (u.function) desc.push(`<div class="desc-block"><div class="lg-title" style="font-size:.74rem;text-transform:uppercase;letter-spacing:.05em;color:var(--text-3);font-weight:600;margin-bottom:6px">Function</div>${E(u.function)}
      <div class="attrib">From <a href="https://www.uniprot.org/uniprotkb/${E(u.acc)}/entry" target="_blank" rel="noopener">UniProt ${E(u.acc)}</a> (${E(u.protein || '')}, <i>${E(u.organism || '')}</i>) · CC BY 4.0</div></div>`);
  if (w && w.extract) desc.push(`<div class="desc-block"><div class="lg-title" style="font-size:.74rem;text-transform:uppercase;letter-spacing:.05em;color:var(--text-3);font-weight:600;margin-bottom:6px">Overview</div>${E(w.extract)}
      <div class="attrib">From Wikipedia, <a href="${E(w.url)}" target="_blank" rel="noopener">${E(w.title)}</a> · CC BY-SA 4.0</div></div>`);
  if (!desc.length) desc.push('<p class="muted">No external description available for this system.</p>');

  const facts = [];
  if (u.length) facts.push(['Sequence length', `${S.fmt(u.length)} aa`]);
  if (u.n_pdb) facts.push(['Experimental structures', `${S.fmt(u.n_pdb)} PDB entries`]);
  if (u.alphafold) facts.push(['Predicted structure', 'AlphaFold DB model available']);
  if (u.acc && u.alphafold) facts.push(['Simulate', `<a href="pull/index.html#m=protein&src=af:${encodeURIComponent(u.acc)}">Pull this protein in your browser</a> <span class="muted small">(SMASH-Pull beta, AlphaFold model)</span>`]);
  if (s.gene) facts.push(['Gene', `${E(s.gene)}${u.organism ? ` · <i>${E(u.organism)}</i>` : ''}`]);
  const orgs = Object.entries(s.organisms || {});
  if (orgs.length) facts.push(['Organisms in studies', orgs.map(([o, n]) => `<i>${E(o)}</i> <span class="muted">(${n})</span>`).join(', ')]);
  const cls = Object.entries(s.classes || {});
  if (cls.length) facts.push(['Experiment classes', cls.map(([c, n]) => `<span class="badge">${E(S.cl(c))} · ${n}</span>`).join(' ')]);
  const useen = Object.keys(s.uniprot_seen || {}).filter(a => a !== u.acc);
  if (useen.length) facts.push(['Other UniProt entries used', useen.map(a => `<a class="idlink" href="https://www.uniprot.org/uniprotkb/${E(a)}/entry" target="_blank" rel="noopener">${E(a)}</a>`).join(' ') + ' <span class="muted small">(orthologs / isoforms in individual studies)</span>']);

  const res = Object.entries(s.results || {}).sort((a, b) => b[1].n - a[1].n);
  const resHtml = res.length ? `<div class="data-table-wrap"><table class="data-table"><thead><tr><th>Observable</th><th>Reports</th><th>Range</th><th>Median</th><th>Studies</th></tr></thead><tbody>` +
    res.map(([k, r]) => `<tr><td>${E(S.OBS[k] || k)}</td><td class="num">${r.n}</td><td class="num">${r.min === r.max ? S.fmt(r.min) : `${S.fmt(r.min)}–${S.fmt(r.max)}`} ${E(r.unit)}</td><td class="num">${S.fmt(r.median)} ${E(r.unit)}</td>
      <td>${r.records.slice(0, 6).map(id => `<a class="idlink" href="record.html?id=${id}">${id.slice(5)}</a>`).join(' ')}</td></tr>`).join('') + `</tbody></table></div>
    <p class="notice" style="margin-top:10px"><i class="fas fa-circle-info"></i>Values extracted from abstracts (and AI-reviewed full texts) of studies focused on this system, converted to common units. Conditions (constructs, loading rates, buffers) differ between studies — open each record before comparing.</p>`
    : '<p class="muted">No numerical results have been extracted for this system yet.</p>';

  const techRows = Object.entries(s.techniques || {}).map(([k, n]) => [k, n, S.tl(k)]);

  root.innerHTML = `<div class="breadcrumb"><a href="systems.html">Systems</a><span>/</span><span>${E(s.name)}</span></div>
    <h1 class="record-title">${E(s.name)}</h1>
    <div class="chip-row" style="margin-bottom:18px"><span class="badge badge-accent">${E(s.entity_type.replace(/_/g, ' '))}</span>
      ${u.protein && u.protein !== s.name ? `<span class="badge">${E(u.protein)}</span>` : ''}${s.years ? `<span class="badge">${s.years[0]}–${s.years[1]}</span>` : ''}</div>
    <div class="stat-row" style="margin-bottom:18px">
      <div class="stat-tile"><div class="label">Studies in the hub</div><div class="value">${S.fmt(s.n)}</div><div class="sub">${s.years ? `${s.years[0]}–${s.years[1]}` : ''}</div></div>
      <div class="stat-tile"><div class="label">With a public dataset</div><div class="value">${S.fmt(s.n_dataset)}</div><div class="sub">${pct}% of studies</div></div>
      <div class="stat-tile"><div class="label">Main technique</div><div class="value" style="font-size:1.15rem;margin-top:8px">${E(topT[0] ? S.tl(topT[0]) : '–')}</div><div class="sub">${topT.length} technique${topT.length === 1 ? '' : 's'} used</div></div>
      <div class="stat-tile"><div class="label">Results extracted</div><div class="value">${S.fmt(res.reduce((a, [, r]) => a + r.n, 0))}</div><div class="sub">${res.length} observable${res.length === 1 ? '' : 's'}</div></div>
    </div>
    <div class="record-layout sys-layout"><div class="record-main">
      <section class="panel"><div class="panel-head"><h2><i class="fas fa-book-open"></i>About this system</h2></div><div class="panel-body">${desc.join('')}</div></section>
      <section class="panel"><div class="panel-head"><h2><i class="fas fa-ruler-combined"></i>What force spectroscopy has measured</h2></div><div class="panel-body">${resHtml}</div></section>
      <section class="panel"><div class="panel-head"><h2><i class="fas fa-chart-column"></i>Studies over time</h2></div><div class="panel-body"><div id="yr-chart"></div></div></section>
      <section class="panel" id="studies"><div class="panel-head"><h2><i class="fas fa-list"></i>Studies</h2>
        <label class="facet" style="padding:0"><input type="checkbox" id="only-ds"> With public data only</label></div>
        <div class="panel-body"><div id="study-list"></div>
        <a class="btn btn-secondary btn-sm" style="margin-top:12px" href="explore.html?ent=${encodeURIComponent(s.name)}">Open in Explore with filters <i class="fas fa-arrow-right"></i></a></div></section>
    </div>
    <aside class="record-aside">
      <div class="card"><h3 style="margin-bottom:12px">Links out</h3>${linkHtml || '<p class="muted small">No external identifiers.</p>'}</div>
      ${facts.length ? `<div class="card">${facts.map(([k, v]) => `<div class="kv" style="grid-template-columns:1fr"><div class="k" style="padding-bottom:2px">${E(k)}</div><div class="v" style="padding-top:0">${v}</div></div>`).join('')}</div>` : ''}
      <div class="card"><h3 style="margin-bottom:10px">Modules</h3><div id="mod-list" class="chip-row"></div></div>
      <div class="card"><h3 style="margin-bottom:10px">Techniques</h3><div id="tech-bars"></div></div>
    </aside></div>`;

  const modCounts = {};
  (s.studies || []).forEach(x => {
    const id = (S.moduleOf || {})[x.id];
    if (id) modCounts[id] = (modCounts[id] || 0) + 1;
  });
  const modHost = document.getElementById('mod-list');
  modHost.innerHTML = Object.entries(modCounts).sort((a, b) => b[1] - a[1]).map(([id, n]) => {
    const label = (S.moduleMeta && S.moduleMeta[id] && S.moduleMeta[id].label) || id.replace(/_/g, ' ');
    return `<a class="badge" href="modules/${E(id)}.html">${E(label)} <span class="muted">${n}</span></a>`;
  }).join('') || '<span class="muted small">Module index not loaded.</span>';
  S.hbars(document.getElementById('tech-bars'), techRows, { link: k => `explore.html?ent=${encodeURIComponent(s.name)}&tech=${k}` });
  const yrs = Object.keys(s.by_year || {});
  if (yrs.length) {
    const y0 = +yrs[0], y1 = +yrs[yrs.length - 1], cats = [];
    for (let y = y0; y <= y1; y++) cats.push(String(y));
    S.stackedColumns(document.getElementById('yr-chart'), { cats, series: [{ label: 'Studies', color: '--series-1', values: cats.map(y => s.by_year[y] || 0) }], height: 200, yLabel: 'Studies per year' });
    const lg = document.querySelector('#yr-chart .legend'); if (lg) lg.remove(); // single series: the title names it
  }
  const STAT = { curated: 'curated', author_verified: 'author verified', ai_assisted: 'AI-assisted' };
  const renderStudies = () => {
    const only = document.getElementById('only-ds').checked;
    const list = s.studies.filter(x => !only || x.ds);
    document.getElementById('study-list').innerHTML = list.slice(0, 200).map(x => `<div class="study-row"><span class="muted num">${x.y || ''}</span>
        <a href="record.html?id=${x.id}">${E(x.t || x.id)}</a>
        <span class="chip-row">${x.ds ? '<span class="badge badge-good"><i class="fas fa-database"></i> data</span>' : ''}${STAT[x.cur] ? `<span class="badge">${STAT[x.cur]}</span>` : ''}<span class="badge">${E(S.TECH[x.tech] ? S.TECH[x.tech].short : x.tech)}</span></span></div>`).join('') +
      (list.length > 200 ? `<p class="muted small" style="margin-top:8px">Showing 200 of ${S.fmt(list.length)} — open in Explore for all.</p>` : '') || '<p class="muted">No studies.</p>';
  };
  document.getElementById('only-ds').onchange = renderStudies;
  renderStudies();
  mountSimulations(s);
})();

// Simulation-versus-experiment panel. Runs only when SMASH.simSystems names this
// system. Simulation results and experimental matches stay in separate tables.
// A reduced value keeps the unit the source wrote. A homolog link is name-based only.
function mountSimulations(system) {
  const S = window.SMASH, E = S.esc;
  const entries = (S.simSystems || []).filter(entry =>
    S.slug(entry.system) === system.slug || String(entry.system).toLowerCase() === String(system.name).toLowerCase());
  if (!entries.length) return;
  const host = document.getElementById('studies');
  if (!host) return;
  const LEVEL = {
    same_construct_same_geometry: 'Same construct, same geometry',
    same_molecule_different_geometry: 'Same molecule, different geometry',
    homolog: 'Homolog (name-based only)'
  };
  const wanted = new Set(entries.map(entry => String(entry.system).toLowerCase()));
  const full = ((S.sim && S.sim.full) || []).filter(record =>
    wanted.has(String((record.system || {}).name || '').toLowerCase()));
  const label = value => String(value == null ? '' : value).replace(/_/g, ' ');
  const matchLabel = level => LEVEL[level] || label(level);

  const shown = value => {
    if (value == null || value === '') return '';
    return value;
  };
  const resultRows = record => (record.results || []).map(result => {
    let value = result.value;
    if (value == null && result.min != null) value = '≥ ' + result.min;
    if (value == null && result.max != null) value = '≤ ' + result.max;
    const units = result.unit_system === 'reduced' || result.unit_system === 'reduced_with_stated_conversion'
      ? label(result.unit_system) : '';
    return `<tr><td>${E(label(result.quantity))}</td><td class="num">${E(shown(value))}</td><td>${E(result.unit || '')}</td><td>${E(units)}</td></tr>`;
  }).join('');
  const experimentRows = record => {
    const links = ((record.links || {}).experimental_matches || []).slice(0, 12);
    if (!links.length) return '<tr><td colspan="4" class="muted">No experimental record matched this simulation.</td></tr>';
    return links.map(link => `<tr><td>${link.record_id ? `<a href="record.html?id=${E(link.record_id)}">${E(link.molecule || link.record_id)}</a>` : E(link.molecule || '')}</td>
      <td class="num">${link.force_pN == null ? '' : E(link.force_pN)}</td>
      <td>${E(link.source || '')}</td><td>${E(matchLabel(link.match_level))}</td></tr>`).join('');
  };
  const unitNote = record => {
    const units = (record.model || {}).unit_system;
    if (units === 'reduced') {
      return '<div class="sim-axis-note">Reduced units, no stated conversion. These values stay in the simulation table and are not placed on the experimental piconewton scale.</div>';
    }
    if (units === 'reduced_with_stated_conversion') {
      return '<div class="sim-axis-note">Reduced units. Only a conversion stated by the source is stored, and the two tables stay separate.</div>';
    }
    return '';
  };

  const blocks = (full.length ? full : []).map(record => {
    const family = (record.model || {}).family || 'other';
    const links = (record.links || {}).experimental_matches || [];
    const extra = links.length > 12 ? `<p class="muted small">${links.length - 12} further experimental links are on the simulation page.</p>` : '';
    return `<article class="card sim-card" style="margin-top:14px">
      <div class="sim-meta"><span class="sim-tag">Simulation</span><span class="sim-tag">${E(label(family))}</span>
        <span class="muted small">${E(record.record_id || '')}</span></div>
      <h3>${E((record.source || {}).title || 'Untitled')}</h3>
      <p class="muted small">${E((record.source || {}).journal || '')} ${E((record.source || {}).year || '')}</p>
      ${unitNote(record)}
      <div class="sim-vs">
        <div class="sim-side-sim"><h4>Simulation — reported values</h4>
          <table class="sim-table"><thead><tr><th>Quantity</th><th>Value</th><th>Unit</th><th>Units</th></tr></thead>
          <tbody>${resultRows(record) || '<tr><td colspan="4" class="muted">No numeric result extracted.</td></tr>'}</tbody></table></div>
        <div class="sim-side-exp"><h4>Experiment — matched records</h4>
          <table class="sim-table"><thead><tr><th>Molecule</th><th>Force (pN)</th><th>Source</th><th>Match</th></tr></thead>
          <tbody>${experimentRows(record)}</tbody></table>
          ${extra}
          <div class="sim-axis-note">Experimental records stay in this table. They are not added to the simulation results.</div></div>
      </div>
    </article>`;
  }).join('');
  const compareName = entries[0].system;
  host.insertAdjacentHTML('beforebegin', `<section class="panel" id="sim-panel">
    <div class="panel-head"><h2><span class="sim-tag">Simulation</span> <span class="sim-tag sim-tag-beta">Beta</span> Pulling simulations</h2></div>
    <div class="panel-body">
      <p>The simulations section is a beta feature. ${full.length || entries.reduce((n, entry) => n + (entry.records || []).length, 0)} simulation record${(full.length || 0) === 1 ? '' : 's'} for this molecule. This block is not part of the experimental study list above.</p>
      ${blocks || '<p class="muted">Indexed simulations exist for this name. Open the simulation page for the comparison.</p>'}
      <a class="btn btn-secondary btn-sm" style="margin-top:12px" href="sim/system.html?system=${encodeURIComponent(compareName)}">Open the simulation section <i class="fas fa-arrow-right"></i></a>
    </div>
  </section>`);
}
