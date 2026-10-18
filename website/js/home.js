// Home page: stat tiles, technique cards, featured studies
(function () {
  const S = window.SMASH, st = S.stats;
  if (!st) return;
  const T = st.totals;
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set('s-records', S.fmt(T.records));
  set('s-years', `${T.year_min}–${T.year_max} · ${S.fmt(T.fulltext_checked)} full texts checked`);
  set('s-ds', S.fmt(T.with_dataset));
  set('s-ds-sub', `${(100 * T.with_dataset / T.records).toFixed(1)}% · ${S.fmt(T.raw_traces)} with raw traces`);
  set('s-dep', S.fmt(T.deposits));
  set('s-dep-sub', `${S.fmt(T.unlinked_deposits)} not yet linked to a paper`);
  set('s-res', S.fmt(T.results));

  const grid = document.getElementById('tech-grid');
  Object.entries(st.tech_counts).sort((a, b) => (a[0] === 'force_spectroscopy_unspecified') - (b[0] === 'force_spectroscopy_unspecified') || b[1] - a[1]).forEach(([k, n]) => {
    const info = S.TECH[k] || { label: k, icon: 'fa-chart-line', blurb: '' };
    const sbt = st.status_by_tech[k] || {};
    const tot = Object.values(sbt).reduce((a, b) => a + b, 0) || 1;
    const share = (sbt.public_repository || 0) / tot;
    const a = document.createElement('a');
    a.className = 'card tech-card'; a.href = `explore.html?tech=${k}`;
    a.innerHTML = `<div class="tc-top"><span class="tc-icon"><i class="fas ${info.icon}"></i></span><span class="tc-count">${S.fmt(n)}</span></div>
      <h3>${S.esc(info.label)}</h3><p>${S.esc(info.blurb)}</p>
      <div class="meter" title="${(share * 100).toFixed(1)}% of primary studies have a public dataset"><span style="width:${Math.max(1, share * 100)}%"></span></div>
      <div class="meter-label">${(share * 100).toFixed(1)}% with public data</div>`;
    grid.appendChild(a);
  });

  const sg = document.getElementById('sys-grid');
  if (sg && st.top_systems) {
    const ICON = { protein: 'fa-cubes', protein_complex: 'fa-cubes', dna: 'fa-dna', rna: 'fa-dna', nucleoprotein: 'fa-dna', cytoskeletal_filament: 'fa-grip-lines', cell: 'fa-circle-nodes', membrane: 'fa-circle-nodes', virus: 'fa-virus' };
    set('n-systems', S.fmt(st.n_systems));
    sg.innerHTML = st.top_systems.map(x => `<a class="card sys-card" href="system.html?s=${encodeURIComponent(x.slug)}">
        <div class="chip-row"><span class="badge"><i class="fas ${ICON[x.type] || 'fa-flask'}"></i> ${S.esc(x.type.replace(/_/g, ' '))}</span>${x.acc ? `<span class="badge">${S.esc(x.acc)}</span>` : ''}</div>
        <h3>${S.esc(x.name)}</h3>
        <div class="nums"><span><b>${S.fmt(x.n)}</b> studies</span><span><b>${S.fmt(x.n_dataset)}</b> with data</span></div></a>`).join('');
  }

  const feat = document.getElementById('featured');
  (st.featured || []).forEach(r => {
    const d = document.createElement('article');
    d.className = 'result-card';
    d.innerHTML = `<h3><a href="record.html?id=${r.id}">${S.esc(r.t)}</a></h3>
      <div class="side">${S.statusPill(r.st)}${r.raw ? '<span class="badge badge-good"><i class="fas fa-wave-square"></i> raw traces</span>' : ''}</div>
      <div class="meta"><span>${S.esc(r.a)}</span><span>${r.y || ''}</span><span>${S.esc(r.j || '')}</span></div>
      <div class="system"><b>${S.esc(S.tl(r.tech))}</b> · ${S.esc((r.ent || []).slice(0, 3).join(', '))}${r.org && r.org.length ? ' · <i>' + S.esc(r.org[0]) + '</i>' : ''}</div>
      <div class="badges">${(r.cls || []).slice(0, 3).map(c => `<span class="badge">${S.esc(S.cl(c))}</span>`).join('')}${(r.repo || []).map(x => `<span class="badge badge-accent">${S.esc(x)}</span>`).join('')}</div>`;
    feat.appendChild(d);
  });
})();
