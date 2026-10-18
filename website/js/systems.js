// Systems browse page
(function () {
  const S = window.SMASH, E = S.esc, all = S.systems || [];
  const GROUPS = {
    protein: { label: 'Proteins', icon: 'fa-cubes', types: ['protein', 'protein_complex', 'peptide'] },
    na: { label: 'Nucleic acids & chromatin', icon: 'fa-dna', types: ['dna', 'rna', 'nucleoprotein'] },
    cyto: { label: 'Filaments', icon: 'fa-grip-lines', types: ['cytoskeletal_filament'] },
    cell: { label: 'Cells, membranes & viruses', icon: 'fa-circle-nodes', types: ['cell', 'membrane', 'virus'] },
    other: { label: 'Small molecules, glycans & synthetic', icon: 'fa-flask', types: ['small_molecule', 'polysaccharide', 'synthetic'] },
  };
  const groupOf = t => Object.keys(GROUPS).find(g => GROUPS[g].types.includes(t)) || 'other';
  const firstSentence = s => { if (!s) return ''; const m = s.match(/^.{40,260}?[.!?](\s|$)/); return m ? m[0] : s.slice(0, 220); };
  const descOf = s => firstSentence((s.uniprot && s.uniprot.function) || (s.wikipedia && s.wikipedia.extract) || '');
  const topTech = s => { const k = Object.keys(s.techniques || {})[0]; return k ? S.tl(k) : ''; };

  let group = S.qs().get('type') || '';
  const el = id => document.getElementById(id);
  el('sfilters').innerHTML = `<button class="chip ${group ? '' : 'active'}" data-g="">All <span class="muted">${all.length}</span></button>` +
    Object.entries(GROUPS).map(([k, g]) => `<button class="chip ${group === k ? 'active' : ''}" data-g="${k}"><i class="fas ${g.icon}"></i> ${g.label} <span class="muted">${all.filter(s => groupOf(s.entity_type) === k).length}</span></button>`).join('');
  el('sfilters').onclick = e => {
    const b = e.target.closest('[data-g]'); if (!b) return;
    group = b.dataset.g;
    el('sfilters').querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c === b));
    render();
  };
  const SORTS = { n: (a, b) => b.n - a.n, ds: (a, b) => b.n_dataset - a.n_dataset || b.n - a.n, name: (a, b) => a.name.localeCompare(b.name),
    recent: (a, b) => ((b.years || [0, 0])[1] - (a.years || [0, 0])[1]) || b.n - a.n };
  function render() {
    const q = el('sq').value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const list = all.filter(s => (!group || groupOf(s.entity_type) === group) &&
      q.every(t => [s.name, s.gene, (s.uniprot || {}).protein, (s.wikipedia || {}).title, Object.keys(s.organisms || {}).join(' ')].join(' ').toLowerCase().includes(t)))
      .sort(SORTS[el('ssort').value]);
    el('scount').innerHTML = `<b>${S.fmt(list.length)}</b> systems`;
    el('sgrid').innerHTML = list.map(s => `<a class="card sys-card" href="system.html?s=${encodeURIComponent(s.slug)}">
        <div class="chip-row"><span class="badge"><i class="fas ${GROUPS[groupOf(s.entity_type)].icon}"></i> ${E(s.entity_type.replace(/_/g, ' '))}</span>${s.uniprot ? `<span class="badge">${E(s.uniprot.acc)}</span>` : ''}</div>
        <h3>${E(s.name)}</h3>
        <p class="desc">${E(descOf(s)) || '<span class="muted">No description available.</span>'}</p>
        <div class="nums"><span><b>${S.fmt(s.n)}</b> studies</span><span><b>${S.fmt(s.n_dataset)}</b> with data</span><span>${E(topTech(s))}</span></div>
      </a>`).join('') || '<div class="empty"><i class="fas fa-dna"></i>No systems match.</div>';
  }
  el('sq').addEventListener('input', render);
  el('ssort').addEventListener('change', render);
  render();
})();
