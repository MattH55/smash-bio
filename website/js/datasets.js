// Datasets page
(function () {
  const S = window.SMASH, E = S.esc, all = S.datasets || [];
  const PER = 30;
  let page = 1;
  const el = id => document.getElementById(id);
  const linked = all.filter(d => (d.linked_records || []).length && !d.journal_mirror);
  el('ds-stats').innerHTML = [
    ['Deposits indexed', all.filter(d => !d.journal_mirror).length, 'excluding journal mirrors'],
    ['Linked to a study', linked.length, 'via DataCite, Scholix, statements'],
    ['With raw traces', all.filter(d => d.content === 'raw_traces').length, 'HDF5, TDMS, JPK, Igor…'],
    ['Repositories', new Set(all.map(d => d.repository).filter(Boolean)).size, 'distinct hosts'],
  ].map(([l, v, s]) => `<div class="stat-tile"><div class="label">${l}</div><div class="value">${S.fmt(v)}</div><div class="sub">${s}</div></div>`).join('');

  const repos = [...new Set(all.map(d => d.repository).filter(Boolean))].sort();
  el('drepo').innerHTML = '<option value="">All repositories</option>' + repos.map(r => `<option>${E(r)}</option>`).join('');
  const techs = [...new Set(all.flatMap(d => d.techniques || []))].filter(t => S.TECH[t]);
  el('dtech').innerHTML = '<option value="">All techniques</option>' + techs.map(t => `<option value="${t}">${E(S.tl(t))}</option>`).join('');
  const q0 = S.qs();
  if (q0.get('repo')) el('drepo').value = q0.get('repo');

  function filtered() {
    const q = el('dq').value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const repo = el('drepo').value, tech = el('dtech').value, ln = el('dlink').value, raw = el('draw').checked, mir = el('dmirror').checked;
    return all.filter(d => {
      if (!mir && d.journal_mirror) return false;
      if (repo && d.repository !== repo) return false;
      if (tech && !(d.techniques || []).includes(tech)) return false;
      const isL = (d.linked_records || []).length > 0;
      if (ln === 'linked' && !isL) return false;
      if (ln === 'unlinked' && isL) return false;
      if (raw && d.content !== 'raw_traces') return false;
      const h = [d.title, d.doi, d.url, (d.creators || []).join(' '), d.repository, d.description].join(' ').toLowerCase();
      return q.every(t => h.includes(t));
    }).sort((a, b) => (b.year || 0) - (a.year || 0));
  }
  function render() {
    const list = filtered();
    el('dcount').innerHTML = `<b>${S.fmt(list.length)}</b> deposits`;
    const pg = list.slice((page - 1) * PER, page * PER);
    el('dlist').innerHTML = pg.length ? pg.map(d => {
      const url = d.doi ? `https://doi.org/${d.doi}` : d.url;
      const recs = (d.linked_records || []).map((id, i) => `<a href="record.html?id=${id}">${E((d.linked_titles || [])[i] || id)}</a>`).join('<br>');
      return `<article class="result-card">
        <h3><a href="${E(url)}" target="_blank" rel="noopener" class="ext">${E(d.title || d.doi || d.url)}</a></h3>
        <div class="side"><span class="badge badge-accent"><i class="fas fa-box-archive"></i> ${E(d.repository || 'repository')}</span>${d.content === 'raw_traces' ? '<span class="badge badge-good">raw traces</span>' : ''}</div>
        <div class="meta"><span>${E((d.creators || []).slice(0, 3).join('; '))}</span><span>${d.year || ''}</span><span>${E(d.resource_type || '')}</span>${d.n_files ? `<span>${S.fmt(d.n_files)} files${d.total_size_bytes ? ' · ' + S.bytes(d.total_size_bytes) : ''}</span>` : ''}${d.doi ? `<span class="mono">${E(d.doi)}</span>` : ''}</div>
        ${(d.file_formats || []).length ? `<div class="badges">${d.file_formats.map(f => `<span class="badge">${E(f)}</span>`).join('')}</div>` : ''}
        <div class="system">${recs ? `<i class="fas fa-link" style="color:var(--accent-2)"></i> ${recs}` : `<span class="muted"><i class="fas fa-link-slash"></i> Not linked to an indexed study${(d.related_articles || []).length ? ` · cites <a href="https://doi.org/${E(d.related_articles[0])}" target="_blank" rel="noopener">${E(d.related_articles[0])}</a>` : ''}</span>`}</div>
      </article>`;
    }).join('') : '<div class="empty"><i class="fas fa-box-open"></i>No deposits match.</div>';
    const pages = Math.ceil(list.length / PER);
    el('dpag').innerHTML = pages > 1 ? `<button ${page === 1 ? 'disabled' : ''} data-p="${page - 1}" aria-label="Previous"><i class="fas fa-chevron-left"></i></button><button disabled>${page} / ${pages}</button><button ${page === pages ? 'disabled' : ''} data-p="${page + 1}" aria-label="Next"><i class="fas fa-chevron-right"></i></button>` : '';
  }
  el('dpag').onclick = e => { const b = e.target.closest('button[data-p]'); if (b && !b.disabled) { page = +b.dataset.p; render(); scrollTo({ top: 0, behavior: 'smooth' }); } };
  ['dq', 'drepo', 'dtech', 'dlink', 'draw', 'dmirror'].forEach(id => el(id).addEventListener(id === 'dq' ? 'input' : 'change', () => { page = 1; render(); }));
  render();
})();
