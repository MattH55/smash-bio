// Insights page
(function () {
  const S = window.SMASH, st = S.stats;
  if (!st) return;
  const T = st.totals, $ = id => document.getElementById(id);
  $('kpis').innerHTML = [
    ['Studies indexed', S.fmt(T.records), `${S.fmt(T.primary)} primary research`],
    ['Linked public dataset', (100 * T.with_dataset / T.records).toFixed(1) + '%', `${S.fmt(T.with_dataset)} studies`],
    ['Raw traces deposited', S.fmt(T.raw_traces), 'HDF5 / TDMS / JPK / Igor files'],
    ['Construct linked to UniProt', (100 * T.with_uniprot / T.records).toFixed(0) + '%', `${S.fmt(T.with_uniprot)} studies`],
  ].map(([l, v, s]) => `<div class="stat-tile"><div class="label">${l}</div><div class="value">${v}</div><div class="sub">${s}</div></div>`).join('');

  // status series: fixed categorical order; "no statement/none" and "not checked" are neutral
  const SER = [
    { key: 'public_repository', label: 'Public repository', color: '--series-1' },
    { key: 'source_data_supplement', label: 'Source data file', color: '--series-2' },
    { key: 'journal_supplement', label: 'Journal supplement', color: '--series-3' },
    { key: 'code_only', label: 'Code only', color: '--series-4' },
    { key: 'on_request', label: 'On request', color: '--series-5' },
    { key: 'none', label: 'No statement / no data', color: '--series-muted', keys: ['not_stated', 'not_available'] },
    { key: 'unknown_no_fulltext', label: 'Not checked', color: '--surface-3' },
  ];
  const val = (c, s) => (s.keys || [s.key]).reduce((a, k) => a + (c[k] || 0), 0);
  const years = Object.keys(st.status_by_year);
  S.stackedColumns($('c-status-year'), { cats: years, series: SER.map(s => ({ ...s, values: years.map(y => val(st.status_by_year[y], s)) })), yLabel: 'Papers per year by data availability' });

  const ry = Object.keys(st.repo_share_by_year);
  S.lineChart($('c-repo-share'), { cats: ry, values: ry.map(y => st.repo_share_by_year[y].share), label: 'Public repository',
    extra: i => `<div class="tt-row"><span>Papers checked</span><b>${S.fmt(st.repo_share_by_year[ry[i]].checked)}</b></div>` });

  const techRows = Object.entries(st.status_by_tech).map(([k, c]) => [k, S.TECH[k] ? S.TECH[k].short === 'SMFS' ? 'Unspecified' : S.TECH[k].label : k, SER.map(s => val(c, s))])
    .filter(r => r[2].reduce((a, b) => a + b, 0) >= 10).sort((a, b) => b[2].reduce((x, y) => x + y) - a[2].reduce((x, y) => x + y));
  S.stackedHBars($('c-status-tech'), { rows: techRows, series: SER });

  const cov = Object.entries(st.field_coverage).map(([k, v]) => [k, v.all, v.fulltext]);
  S.pairedHBars($('c-coverage'), { rows: cov, series: [{ label: 'All records', color: '--series-muted' }, { label: `With OA methods text (${S.fmt(st.n_fulltext)})`, color: '--series-1' }] });

  const top = (o, n) => Object.entries(o).slice(0, n);
  S.hbars($('c-entities'), top(st.entity_counts, 15), { link: k => 'explore.html?ent=' + encodeURIComponent(k) });
  S.hbars($('c-classes'), Object.entries(st.class_counts).map(([k, v]) => [k, v, S.cl(k)]), { link: k => 'explore.html?cls=' + k });
  if (S.index && $('c-modules')) {
    const counts = {}, linked = {};
    S.index.forEach(r => {
      if (!r.module) return;
      counts[r.module] = (counts[r.module] || 0) + 1;
      if (r.ds) linked[r.module] = (linked[r.module] || 0) + 1;
    });
    const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, v]) => {
      const label = (S.moduleMeta && S.moduleMeta[k] && S.moduleMeta[k].label) || k.replace(/_/g, ' ');
      const share = v ? Math.round(100 * (linked[k] || 0) / v) : 0;
      return [k, v, `${label} · ${share}% with data`];
    });
    S.hbars($('c-modules'), rows, { link: k => 'explore.html?module=' + k });
  }
  S.hbars($('c-orgs'), top(st.organism_counts, 12), { link: k => 'explore.html?org=' + encodeURIComponent(k) });
  S.hbars($('c-vendors'), top(st.vendor_counts, 12).map(([k, v]) => [k, v, k === 'custom' ? 'Custom-built' : k]), { link: k => 'explore.html?vend=' + encodeURIComponent(k) });
  S.hbars($('c-repos'), top(st.repo_counts, 12), { link: k => 'explore.html?repo=' + encodeURIComponent(k) });
  S.hbars($('c-formats'), top(st.format_counts, 12));
  S.hbars($('c-obs'), top(st.obs_counts, 14).map(([k, v]) => [k, v, S.OBS[k] || k]), { link: k => 'explore.html?obs=' + k });

  // technique by year: top 4 techniques + Other (fixed slot order)
  const tY = st.tech_by_year, ys = Object.keys(tY).filter(y => +y >= 1990);
  const topT = Object.keys(st.tech_counts).filter(k => k !== 'force_spectroscopy_unspecified').slice(0, 4);
  const ser = topT.map((k, i) => ({ label: S.tl(k), color: `--series-${i + 1}`, values: ys.map(y => tY[y][k] || 0) }));
  ser.push({ label: 'Other / unspecified', color: '--series-muted', values: ys.map(y => Object.entries(tY[y]).filter(([k]) => !topT.includes(k)).reduce((a, [, v]) => a + v, 0)) });
  S.stackedColumns($('c-tech-year'), { cats: ys, series: ser, height: 240, yLabel: 'Studies per year by technique' });
})();
