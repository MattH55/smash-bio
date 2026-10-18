// SMASH-Pull simulator page. Wires the inputs to the engine pool, and renders
// the results. Protein forces are model units (ε/Å) and are never shown as pN.
'use strict';
(function () {
  const $ = id => document.getElementById(id);
  const A = window.PullAnalysis, C = window.PullChart, S = window.PullSources, P = window.PullPool;
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const f = (v, d = 2) => Number.isFinite(v) ? (+v).toFixed(d) : '—';
  const PHONE = (navigator.hardwareConcurrency || 4) < 4 || (matchMedia('(pointer: coarse)').matches && Math.min(screen.width, screen.height) < 600);

  const PRESET = {
    protein: {
      afm: { k: 0.1, label: 'Stiff spring (k = 0.1 ε/Å²) moving at constant speed, like an AFM cantilever.' },
      ot: { k: 0.05, label: 'Softer spring (k = 0.05 ε/Å²) at constant speed, like an optical trap; the trap travels further to load the softer spring.' },
      mt: { k: 0, label: 'Constant force on the pulled residue, like magnetic tweezers. Reports extension against time and time to unfold.' }
    },
    proto: {
      quick: { speeds: [0.2], forces: [6], reps: 3, label: 'One condition, 3 replicas: a first look in under a minute for a small domain.' },
      standard: { speeds: [0.05, 0.1, 0.2], forces: [5, 6, 7], reps: 10, label: '3 conditions × 10 replicas: enough for peak statistics and a loading-rate (Bell–Evans) fit. Takes a few minutes for a 90-residue domain on a 6-core laptop.' },
      custom: { label: 'Your own speeds or forces and replica count.' }
    },
    nucleic: {
      ot: { k: 0.3, handle: 2000, label: 'Optical trap: 0.3 pN/nm trap, 2 kbp dsDNA handles.' },
      mt: { k: 0.3, handle: 2000, label: 'Magnetic tweezers: constant force; the molecule hops between folded and open.' },
      afm: { k: 10, handle: 0, label: 'AFM: 10 pN/nm cantilever, no handles.' }
    }
  };
  const NA_EX = {
    hp20: { seq: 'GAGTCCTGGATCCTGTCCGCTTTTGCGGACAGGATCCAGGACTC', construct: 'auto', t: 23, na: 200 },
    hp12: { seq: 'GCGCGGCCGCGCTTTTGCGCGGCCGCGC', construct: 'auto', t: 25, na: 150 },
    rna: { seq: 'GGCGCAUCCGGCGAAAGCCGGAUGCGCC', construct: 'auto', t: 25, na: 150 },
    unzip: { seq: null, construct: 'unzip', t: 25, na: 150 }
  };

  const st = {
    mode: 'protein', pdbText: null, src: null, chains: [], chain: null, range: null,
    structure: null, anchor: null, pull: null, pickNext: 'anchor',
    pInst: 'afm', pProto: PHONE ? 'quick' : 'quick', nInst: 'ot',
    results: null, job: null, frames: null, frameTimer: null
  };
  let viewer;

  // ---------------------------------------------------------------- UI basics
  function seg(id, key, onChange) {
    const el = $(id);
    el.querySelectorAll('button').forEach(b => b.onclick = () => {
      if (b.disabled) return;
      el.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
      st[key] = b.dataset.v; onChange && onChange(b.dataset.v); saveHash();
    });
  }
  function setSeg(id, v) { $(id).querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x.dataset.v === v)); }
  function status(id, msg, kind) { const el = $(id); el.className = 'status' + (kind ? ' ' + kind : ''); el.innerHTML = msg || ''; }
  function setMode(m) {
    st.mode = m;
    $('mode-protein').setAttribute('aria-pressed', m === 'protein');
    $('mode-nucleic').setAttribute('aria-pressed', m === 'nucleic');
    $('in-protein').hidden = m !== 'protein'; $('setup-protein').hidden = m !== 'protein';
    $('in-nucleic').hidden = m !== 'nucleic'; $('setup-nucleic').hidden = m !== 'nucleic';
    $('struct-panel').querySelector('.viewer-wrap').hidden = m !== 'protein';
    $('struct-panel').querySelector('.chart-tools').hidden = m !== 'protein';
    $('h-struct').textContent = m === 'protein' ? 'Structure' : 'Construct';
    $('na-diagram').hidden = m !== 'nucleic';
    $('struct-info').innerHTML = '';
    clearResults();
    updateRunButton();
    if (m === 'nucleic') naPreview();
    else if (st.structure) renderStructureInfo();
  }
  function updateRunButton() {
    $('run-btn').disabled = st.job != null || (st.mode === 'protein' ? !st.structure : !$('na-seq').value.trim());
  }
  function clearResults() {
    $('results').hidden = true; $('results-empty').hidden = false;
    st.results = null; $('frame-row').hidden = true;
    const o = $('color-by').querySelector('option[value=break]'); o.disabled = true;
  }

  // ---------------------------------------------------------------- protein loading
  function scanChains(text) {
    const m = new Map();
    for (const line of text.split(/\r?\n/)) {
      if (line.startsWith('ENDMDL')) break;
      if (line.length >= 54 && line.startsWith('ATOM') && line.slice(12, 16).trim() === 'CA') {
        const c = line[21], r = parseInt(line.slice(22, 26), 10);
        if (!m.has(c)) m.set(c, { chain: c, n: 0, lo: r, hi: r });
        const e = m.get(c); e.n++; e.lo = Math.min(e.lo, r); e.hi = Math.max(e.hi, r);
      }
    }
    return [...m.values()];
  }
  async function loadText(text, src) {
    st.pdbText = text; st.src = src; st.anchor = st.pull = null; st.pickNext = 'anchor';
    st.chains = scanChains(text);
    if (!st.chains.length) { status('load-status', 'No protein Cα atoms in this file (a nucleic-acid structure? use the DNA / RNA mode with its sequence).', 'err'); return; }
    const big = [...st.chains].sort((a, b) => b.n - a.n)[0];
    if (!st.chain || !st.chains.some(c => c.chain === st.chain)) st.chain = big.chain;
    const cur = st.chains.find(c => c.chain === st.chain);
    if (!st.range && cur.n > 400) st.range = [cur.lo, cur.lo + 399];
    $('chain-sel').innerHTML = st.chains.map(c => `<option value="${esc(c.chain)}"${c.chain === st.chain ? ' selected' : ''}>${esc(c.chain)} (${c.n} res)</option>`).join('');
    $('rng-a').value = st.range ? st.range[0] : cur.lo; $('rng-b').value = st.range ? st.range[1] : cur.hi;
    $('chain-pick').hidden = !(st.chains.length > 1 || cur.n > 400 || st.range);
    await parse();
  }
  async function parse() {
    clearResults();
    status('load-status', 'Reading structure…');
    try {
      const req = { op: 'structure', pdb: st.pdbText, chain: st.chain };
      if (st.range) { req.range_start = st.range[0]; req.range_end = st.range[1]; }
      const s = await P.one(req);
      st.structure = s;
      viewer.setStructure(s.coords, s.contacts);
      if (s.prep.is_alphafold) { $('color-by').value = 'plddt'; viewer.colorBy('plddt', s.prep.bfactor); } else { $('color-by').value = 'index'; }
      if (st.anchor == null || !s.residues.includes(st.anchor)) st.anchor = s.residues[0];
      if (st.pull == null || !s.residues.includes(st.pull)) st.pull = s.residues[s.n - 1];
      $('anchor-res').value = st.anchor; $('pull-res').value = st.pull;
      markPoints();
      renderStructureInfo();
      status('load-status', `Loaded <strong>${esc(s.label)}</strong> from ${st.src.url ? `<a href="${esc(st.src.url)}" target="_blank" rel="noopener">${esc(st.src.source)}</a>` : esc(st.src.source)}: ${s.n} residues, ${s.n_contacts} native contacts.`, 'ok');
      saveHash();
    } catch (e) {
      st.structure = null;
      status('load-status', esc(e.message), 'err');
      if (e.code === 'structure_too_large') $('chain-pick').hidden = false;
    }
    updateRunButton();
  }
  function markPoints() {
    const s = st.structure; if (!s) return;
    const m = {};
    const ia = s.residues.indexOf(st.anchor), ip = s.residues.indexOf(st.pull);
    if (ia >= 0) m[ia] = { color: C.css('--series-3') || '#1baf7a', label: 'fixed ' + st.anchor };
    if (ip >= 0) m[ip] = { color: C.css('--series-2') || '#eb6834', label: 'pulled ' + st.pull };
    viewer.setMarks(m);
  }
  function renderStructureInfo() {
    const s = st.structure; if (!s) return;
    const p = s.prep;
    const pl = p.is_alphafold ? A.mean(p.bfactor.filter(Number.isFinite)) : NaN;
    const low = p.is_alphafold ? p.bfactor.filter(b => b < +$('p-plddt').value).length : 0;
    const flags = [];
    if (p.is_alphafold) flags.push(`AlphaFold model, mean pLDDT ${f(pl, 1)}; ${low} residue(s) below the cut-off lose their native contacts.`);
    if (p.disulfides.length) flags.push(`${p.disulfides.length} disulfide bond(s) (${p.disulfides.map(d => d.join('–')).join(', ')}): not covalent in the model, so they can break here although they would not in an experiment.`);
    if (p.metals.length) flags.push(`Metal site(s) not modelled: ${p.metals.map(m => m.name + ' ' + m.residue).join(', ')}.`);
    if (p.ligands.length) flags.push(`Bound ligand(s) not modelled: ${p.ligands.join(', ')}.`);
    if (p.breaks.length) flags.push(`${p.breaks.length} chain break(s) (${p.breaks.slice(0, 4).map(b => b[0] + '→' + b[1]).join(', ')}${p.breaks.length > 4 ? '…' : ''}): the trace is bonded across the gap.`);
    const sep = Math.abs(s.residues.indexOf(st.pull) - s.residues.indexOf(st.anchor));
    $('struct-info').innerHTML = `<dl class="kv">
      <div><dt>Structure</dt><dd>${esc(s.label)}</dd></div>
      <div><dt>Residues</dt><dd>${s.n}</dd></div>
      <div><dt>Native contacts</dt><dd>${s.n_contacts}</dd></div>
      <div><dt>Pulled span</dt><dd>${st.anchor} → ${st.pull} <small>(${sep} res, Lc ${f(3.8 * sep / 10, 1)} nm)</small></dd></div>
    </dl>${flags.length ? `<ul class="notes">${flags.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}${s.notes.length ? `<ul class="notes">${s.notes.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}`;
  }
  async function loadFrom(kind, id) {
    st.range = null; st.chain = null;
    status('load-status', 'Fetching…');
    try {
      let r;
      if (kind === 'pdb') r = await S.pdb(id);
      else if (kind === 'af') r = await S.alphafold(id);
      await loadText(r.text, { ...r, kind, id: r.id || id });
    } catch (e) { status('load-status', esc(e.message), 'err'); }
  }
  async function loadSequence() {
    const c = S.classify($('seq-in').value);
    if (c.kind === 'dna' || c.kind === 'rna') { $('na-seq').value = c.seq; setMode('nucleic'); status('load-status', 'That is a nucleic-acid sequence, so the DNA / RNA model was selected.', 'ok'); naPreview(); return; }
    if (c.kind !== 'protein') { status('load-status', 'Not a protein sequence (allowed: the 20 amino-acid letters, X, B, Z, U, O).', 'err'); return; }
    status('load-status', `Looking up an exact match for ${c.seq.length} residues (CRC64 ${S.crc64(c.seq)})…`);
    try {
      const m = await S.bySequence(c.seq);
      if (!m.hits.length) { status('load-status', 'No UniProt entry has exactly this sequence, so there is no AlphaFold DB model to use. Structure prediction cannot run in a browser: predict the structure elsewhere (for example ColabFold) and upload the PDB file.', 'err'); return; }
      const h = m.hits[0];
      status('load-status', `Exact match: ${esc(h.acc)} ${esc(h.name)} (${esc(h.organism)}). Loading its AlphaFold model…`);
      await loadFrom('af', h.acc);
    } catch (e) { status('load-status', esc(e.message), 'err'); }
  }

  // ---------------------------------------------------------------- nucleic preview
  function randomDuplex(n, seed) {
    let s = seed >>> 0; const out = [];
    for (let i = 0; i < n; i++) { s = (s * 1664525 + 1013904223) >>> 0; out.push('ACGT'[s >>> 30]); }
    return out.join('');
  }
  function naRequest(op) {
    const seq = S.parseFasta($('na-seq').value).seq.replace(/[^ACGTUN]/g, '');
    const cons = $('na-construct').value;
    let pol = $('na-polymer').value;
    if (pol === 'auto') pol = /U/.test(seq) && !/T/.test(seq) ? 'RNA' : 'DNA';
    const inst = PRESET.nucleic[st.nInst];
    const r = {
      op, polymer: pol, construct: cons === 'unzip' ? 'unzip' : 'hairpin',
      temperature_k: +$('na-t').value + 273.15, na_mm: +$('na-na').value, mg_mm: +$('na-mg').value,
      thermo: $('na-thermo').value, trap_k: +$('na-k').value || inst.k, handle_bp: +$('na-handle').value, k0: +$('na-k0').value
    };
    if (cons === 'stem') { r.stem = $('na-stem').value.trim(); r.loop = +$('na-loop').value; } else r.sequence = seq;
    return r;
  }
  let naTimer = null;
  function naPreview() {
    clearTimeout(naTimer);
    naTimer = setTimeout(async () => {
      updateRunButton();
      if (!$('na-seq').value.trim() && $('na-construct').value !== 'stem') { $('na-diagram').innerHTML = ''; $('struct-info').innerHTML = '<p class="muted small">Type or paste a sequence, or pick an example.</p>'; return; }
      try {
        const r = await P.one(naRequest('nucleic_landscape'));
        st.naLandscape = r;
        renderNaInfo(r);
        status('load-status', '', '');
      } catch (e) { $('na-diagram').innerHTML = ''; $('struct-info').innerHTML = ''; status('load-status', esc(e.message), 'err'); }
    }, 250);
  }
  function hairpinSvg(stem, loop) {
    const n = stem.length, w = Math.min(560, 40 + n * 14), comp = { A: 'T', T: 'A', G: 'C', C: 'G', U: 'A' };
    const pol = /U/.test(stem) ? 'RNA' : 'DNA';
    const c = b => pol === 'RNA' && b === 'T' ? 'U' : b;
    const step = Math.min(14, (w - 70) / n);
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} 86" font-family="ui-monospace, monospace" font-size="11">`;
    for (let i = 0; i < n; i++) {
      const x = 14 + i * step;
      s += `<text x="${x}" y="30" fill="${C.css('--text')}">${c(stem[i])}</text><text x="${x}" y="64" fill="${C.css('--text')}">${c(comp[stem[i]] || '?')}</text>`;
      s += `<line x1="${x + 3.5}" x2="${x + 3.5}" y1="35" y2="53" stroke="${C.css('--series-1')}" stroke-width="1.6"/>`;
    }
    const lx = 14 + n * step + 6;
    s += `<path d="M${lx} 26 C ${lx + 34} 26, ${lx + 34} 62, ${lx} 62" fill="none" stroke="${C.css('--series-2')}" stroke-width="2"/><text x="${lx + 30}" y="47" fill="${C.css('--text-2')}">${loop} nt</text>`;
    s += `<text x="0" y="12" fill="${C.css('--text-3')}" font-family="system-ui" font-size="10">5′ handle</text><text x="0" y="82" fill="${C.css('--text-3')}" font-family="system-ui" font-size="10">3′ handle</text></svg>`;
    return s;
  }
  function renderNaInfo(r) {
    const sm = r.summary;
    $('na-diagram').innerHTML = sm.construct === 'hairpin' ? `<div class="chart">${hairpinSvg(r.stem, sm.loop_nt)}</div>` : `<p class="small muted">Duplex of ${sm.n_bp} bp, unzipped from one end (both strands released: ${2 * sm.n_bp} nt).</p>`;
    $('struct-info').innerHTML = `<dl class="kv">
      <div><dt>Stem</dt><dd>${sm.n_bp} bp${sm.construct === 'hairpin' ? ` + ${sm.loop_nt}-nt loop` : ''}</dd></div>
      <div><dt>ΔG fold</dt><dd>${f(sm.dG_fold_kcal, 1)} <small>kcal/mol</small></dd></div>
      <div><dt>F½ (equilibrium)</dt><dd>${sm.F_half_pN == null ? 'n/a' : f(sm.F_half_pN, 1) + ' <small>pN</small>'}</dd></div>
      <div><dt>Δx at F½</dt><dd>${sm.delta_x_at_F_half_nm == null ? 'n/a' : f(sm.delta_x_at_F_half_nm, 1) + ' <small>nm</small>'}</dd></div>
    </dl><ul class="notes">${[...r.input_notes, ...sm.notes].map(x => `<li>${esc(x)}</li>`).join('')}<li>Absolute forces are <strong>experimental</strong>: on the 20-bp benchmark class the model's F½ is about 5 pN above experiment (<a href="benchmarks.html#gate4">Gate 4</a>).</li></ul>`;
  }

  // ---------------------------------------------------------------- running
  function conditions() {
    const pr = PRESET.proto[st.pProto];
    const parse = s => s.split(/[,\s]+/).map(Number).filter(v => Number.isFinite(v) && v > 0);
    if (st.pProto === 'custom') return { speeds: parse($('p-speeds').value), forces: parse($('p-force').value), reps: Math.max(1, Math.min(50, +$('p-reps').value || 1)) };
    return { speeds: pr.speeds, forces: pr.forces, reps: pr.reps };
  }
  function proteinJobs() {
    const s = st.structure, c = conditions();
    const k = +$('p-k').value || PRESET.protein[st.pInst].k || 0.1;
    const dt = +$('p-dt').value || 0.01;
    const ia = s.residues.indexOf(st.anchor), ip = s.residues.indexOf(st.pull);
    const d0 = Math.hypot(...[0, 1, 2].map(q => s.coords[3 * ia + q] - s.coords[3 * ip + q]));
    const contour = 3.8 * Math.abs(ip - ia);
    const extra = st.pInst === 'ot' ? Math.max(0, 8 / k - 80) : 0;
    const travel = Math.max(10, 0.9 * (contour - d0)) + extra;
    const base = {
      op: 'protein_run', pdb: st.pdbText, chain: st.chain, anchor_residue: st.anchor, pull_residue: st.pull,
      dt, temperature: +$('p-kt').value || 0.5, friction: +$('p-gamma').value || 1, plddt_cutoff: +$('p-plddt').value,
      lj_10_12: $('p-contact').value === '10-12', max_samples: 1500
    };
    if (st.range) { base.range_start = st.range[0]; base.range_end = st.range[1]; }
    const jobs = [];
    if (st.pInst === 'mt') {
      const steps = Math.max(1000, +$('p-clamp-steps').value || 300000);
      c.forces.forEach((F, ci) => { for (let r = 0; r < c.reps; r++) jobs.push({ ...base, mode: 'force', force: F, n_steps: steps, seed: r + 1, frames: ci === 0 && r === 0 ? 80 : 0, _cond: F }); });
    } else {
      [...c.speeds].sort((a, b) => a - b).forEach((v, ci) => {
        const steps = Math.ceil(travel / (v * dt));
        for (let r = 0; r < c.reps; r++) jobs.push({ ...base, mode: 'velocity', speed: v, spring_k: k, n_steps: steps, seed: r + 1, frames: ci === 0 && r === 0 ? 80 : 0, _cond: v });
      });
    }
    return jobs;
  }
  function estimateSeconds(jobs, n) {
    // Chrome, Gate 6 measurement: ~0.8 µs per residue-step per worker when every
    // logical core runs a worker; hyperthreads give about half a core each.
    const perStep = 0.8e-6 * n;
    const total = jobs.reduce((s, j) => s + j.n_steps, 0) * perStep;
    return total / Math.max(1, Math.min(P.cores / 2, jobs.length));
  }
  async function run() {
    if (st.mode === 'protein') return runProtein();
    return runNucleic();
  }
  function startJob(jobs, onDone) {
    $('run-btn').disabled = true; $('cancel-btn').hidden = false; $('prog').style.width = '0%';
    const t0 = performance.now();
    st.job = P.runAll(jobs.map(j => { const { _cond, ...r } = j; return r; }), {
      onDone: (i, r, ms, done) => {
        $('prog').style.width = (100 * done / jobs.length).toFixed(1) + '%';
        const el = (performance.now() - t0) / 1000;
        const left = done < jobs.length ? ` · about ${Math.max(1, Math.round(el / done * (jobs.length - done)))} s left` : '';
        status('run-status', `${done} / ${jobs.length} runs done (${el.toFixed(1)} s${left})`);
        onDone && onDone(i, r);
      }
    });
    return st.job.done.then(res => {
      const el = (performance.now() - t0) / 1000;
      st.job = null; $('cancel-btn').hidden = true; updateRunButton();
      return res ? { res, seconds: el } : null;
    });
  }
  async function runProtein() {
    const jobs = proteinJobs();
    if (!jobs.length) { status('run-status', 'Give at least one speed or force.', 'err'); return; }
    const est = estimateSeconds(jobs, st.structure.n);
    status('run-status', `Running ${jobs.length} trajectories on ${Math.min(P.cores, jobs.length)} worker(s), roughly ${Math.max(1, Math.round(est))} s…`);
    const out = await startJob(jobs);
    if (!out) { status('run-status', 'Cancelled.'); return; }
    const errs = out.res.filter(r => r && r.error);
    const runs = out.res.map((r, i) => r && !r.error ? { ...r, _cond: jobs[i]._cond } : null).filter(Boolean);
    if (!runs.length) { status('run-status', 'Every run failed: ' + esc(errs[0]?.error?.message + ' ' + (errs[0]?.error?.detail || '')), 'err'); return; }
    status('run-status', `Done: ${runs.length} trajectories in ${out.seconds.toFixed(1)} s${errs.length ? `; ${errs.length} failed (${esc(errs[0].error.detail || errs[0].error.message)})` : ''}.`, errs.length ? 'err' : 'ok');
    st.results = { kind: 'protein', inst: st.pInst, runs, seconds: out.seconds, config: jobs.map(({ pdb, ...j }) => j) };
    renderProtein();
  }
  async function runNucleic() {
    const L = st.naLandscape;
    if (!L) { status('run-status', 'Fix the sequence first.', 'err'); return; }
    const base = naRequest('nucleic_kinetic');
    const jobs = [];
    if (L.summary.n_bp > 200) {
      status('run-status', 'Kinetics are limited to 200 bp; showing the equilibrium unzipping curve.', '');
      st.results = { kind: 'nucleic', landscape: L, runs: [], clamp: false };
      renderNucleic(); return;
    }
    if (st.nInst === 'mt') {
      const fc = $('na-clamp').value === '' ? L.summary.F_half_pN : +$('na-clamp').value;
      if (!Number.isFinite(fc)) { status('run-status', 'No F½ for this construct; give a clamp force.', 'err'); return; }
      for (let r = 0; r < 4; r++) jobs.push({ ...base, clamp_pn: fc, duration_s: +$('na-dur').value || 0.5, seed: r + 1, max_samples: 4000 });
    } else {
      const n = Math.max(1, Math.min(200, +$('na-cycles').value || 10));
      for (let r = 0; r < n; r++) jobs.push({ ...base, speed_nm_s: +$('na-speed').value || 100, refold: true, seed: r + 1, max_samples: 1500 });
    }
    status('run-status', `Running ${jobs.length} kinetic Monte Carlo trajectories…`);
    const out = await startJob(jobs);
    if (!out) { status('run-status', 'Cancelled.'); return; }
    const runs = out.res.filter(r => r && !r.error);
    const errs = out.res.filter(r => r && r.error);
    if (!runs.length) { status('run-status', esc(errs[0]?.error?.message || 'failed'), 'err'); return; }
    const trunc = runs.filter(r => r.truncated).length;
    status('run-status', `Done: ${runs.length} trajectories in ${out.seconds.toFixed(1)} s.${trunc ? ` ${trunc} hit the event cap (very slow pulling or very low force); their traces end early.` : ''}`, 'ok');
    st.results = { kind: 'nucleic', landscape: L, runs, clamp: st.nInst === 'mt', seconds: out.seconds, config: jobs };
    renderNucleic();
  }

  // ---------------------------------------------------------------- protein results
  function chartBox(id, title, svg, extra = '') {
    return `<div class="panel chart" id="${id}"><div class="chart-head"><h3>${title}</h3><div class="chart-tools"><button class="btn btn-sm btn-ghost" data-svg="${id}">SVG</button><button class="btn btn-sm btn-ghost" data-png="${id}">PNG</button></div></div>${svg}${extra}</div>`;
  }
  function wireChartExports() {
    document.querySelectorAll('[data-svg]').forEach(b => b.onclick = () => C.exportSvg(document.querySelector('#' + b.dataset.svg + ' svg').outerHTML, 'smash-pull-' + b.dataset.svg));
    document.querySelectorAll('[data-png]').forEach(b => b.onclick = () => C.exportPng(document.querySelector('#' + b.dataset.png + ' svg').outerHTML, 'smash-pull-' + b.dataset.png));
  }
  function renderProtein() {
    const R = st.results, runs = R.runs, s = st.structure, kt = runs[0].temperature;
    const conds = [...new Set(runs.map(r => r._cond))].sort((a, b) => a - b);
    const pal = C.palette();
    const color = c => pal[conds.indexOf(c) % pal.length];
    const clamp = R.inst === 'mt';
    const condLabel = c => clamp ? `F = ${c} ε/Å` : `v = ${c} Å/τ`;
    const rows = conds.map(c => {
      const rr = runs.filter(r => r._cond === c);
      const peaks = rr.map(r => r.peak_tension);
      const nev = rr.map(r => r.events.length);
      const dlc = rr.flatMap(r => A.contourIncrements(r, s.coords).map(e => e.dLc));
      const half = r => { const d0 = r.extension0_a, L = r.contour_a; const thr = d0 + 0.5 * (L - d0); const i = r.extension_a.findIndex(x => x > thr); return i < 0 ? NaN : r.time[i]; };
      const tun = clamp ? rr.map(half) : [];
      return { c, rr, peaks, nev, dlc, tun, lr: clamp ? NaN : rr[0].spring_k * c };
    });
    // summary
    const allDlc = rows.flatMap(r => r.dlc);
    let bell = null;
    if (!clamp) bell = A.bellFit(rows.flatMap(r => r.peaks.map(p => ({ lnr: Math.log(r.lr), f: p }))), kt);
    let clampFit = null;
    if (clamp) {
      const pts = rows.flatMap(r => r.tun.filter(Number.isFinite).map(t => ({ lnr: r.c, f: Math.log(t) })));
      const b = A.bellFit(pts, kt);
      if (b) clampFit = { xb: -kt * b.slope, se: kt * b.slopeSe };
    }
    const tbl = `<div class="table-wrap"><table class="pull-table"><thead><tr><th>Condition</th><th>Runs</th>${clamp ? '<th>Time to unfold (τ)</th><th>Unfolded</th>' : '<th>Loading rate (ε/Å/τ)</th><th>Peak tension (ε/Å)</th>'}<th>Events / run</th><th>ΔLc (nm)</th></tr></thead><tbody>${rows.map(r => `<tr><td><span class="chart-legend" style="margin:0"><span><i style="background:${color(r.c)}"></i>${condLabel(r.c)}</span></span></td><td class="n">${r.rr.length}</td>${clamp ? `<td class="n">${f(A.median(r.tun.filter(Number.isFinite)), 0)} <small class="muted">median</small></td><td class="n">${r.tun.filter(Number.isFinite).length} / ${r.rr.length}</td>` : `<td class="n">${f(r.lr, 3)}</td><td class="n">${f(A.mean(r.peaks))} ± ${f(A.sd(r.peaks))}</td>`}<td class="n">${f(A.mean(r.nev), 1)}</td><td class="n">${r.dlc.length ? f(A.mean(r.dlc) / 10, 1) + ' ± ' + f(A.sd(r.dlc) / 10, 1) : '—'}</td></tr>`).join('')}</tbody></table></div>`;
    const spanNote = `<div class="warnbox" style="margin-bottom:12px"><strong>Experimental.</strong> Tension includes solvent drag, which grows with the length of chain being pulled. Compare pulling geometries only when their spans are similar; rely most on the unfolding order and ΔLc. <a href="about.html#protein">Why</a> · <a href="benchmarks.html#gates">validation</a></div>`;
    $('res-summary').innerHTML = spanNote + `<dl class="kv" style="margin-bottom:12px">
      <div><dt>Trajectories</dt><dd>${runs.length} <small>in ${f(R.seconds, 1)} s</small></dd></div>
      ${clamp ? `<div><dt>Distance to transition xβ</dt><dd>${clampFit && Number.isFinite(clampFit.xb) ? f(clampFit.xb, 1) + ' ± ' + f(clampFit.se, 1) + ' <small>Å, from ln t vs F</small>' : '<small>needs ≥ 2 forces that unfold</small>'}</dd></div>`
        : `<div><dt>Distance to transition xβ</dt><dd>${bell && Number.isFinite(bell.xb) ? f(bell.xb, 1) + ' ± ' + f(bell.xbSe, 1) + ' <small>Å (Bell–Evans)</small>' : '<small>needs ≥ 2 speeds</small>'}</dd></div>`}
      <div><dt>Contour released ΔLc</dt><dd>${allDlc.length ? f(A.mean(allDlc) / 10, 1) + ' <small>nm per event</small>' : '—'}</dd></div>
      <div><dt>Force units</dt><dd>ε/Å <small>model units, not pN</small></dd></div>
    </dl>${tbl}`;
    // charts
    let html = '';
    if (clamp) {
      const series = runs.map(r => ({ x: r.time, y: r.extension_a, color: color(r._cond), opacity: 0.5, width: 1.2 }));
      html += chartBox('c-time', 'Extension against time under constant force', C.line({ id: 'time', series, xLabel: 'time (τ, model units)', yLabel: 'extension (Å)' }), C.legend(conds.map(c => [color(c), condLabel(c)])));
    } else {
      const series = runs.map(r => ({ x: r.extension_a, y: r.tension, color: color(r._cond), opacity: runs.length > 12 ? 0.35 : 0.6, width: 1.1 }));
      const markers = runs.flatMap(r => r.events.map(e => ({ x: e.extension_a, y: e.force, color: color(r._cond), title: `event: ${f(e.force)} ε/Å at ${f(e.extension_a, 0)} Å` })));
      html += chartBox('c-fec', 'Force–extension', C.line({ id: 'fec', series, markers, xLabel: 'extension between attachment points (Å)', yLabel: 'tension (ε/Å, model units)' }), C.legend(conds.map(c => [color(c), condLabel(c)])) + '<p class="hint">Triangles mark unfolding events: a drop of at least 15 % of the peak height or 3× the noise (PROTOCOL.md).</p>');
    }
    html += '<div class="grid2">';
    if (!clamp) {
      const pts = rows.map(r => ({ x: r.peaks.map(() => Math.log(r.lr)), y: r.peaks, color: color(r.c), points: true }));
      const xs = rows.map(r => Math.log(r.lr));
      const fit = bell ? [{ x: [Math.min(...xs) - 0.2, Math.max(...xs) + 0.2], y: [Math.min(...xs) - 0.2, Math.max(...xs) + 0.2].map(x => bell.intercept + bell.slope * x), color: C.css('--text-2'), dash: '5 4', width: 1.3 }] : [];
      html += chartBox('c-bell', 'Peak tension against loading rate', C.line({ id: 'bell', series: [...pts, ...fit], xLabel: 'ln loading rate (ε/Å/τ)', yLabel: 'peak tension (ε/Å)', height: 300 }), bell ? `<p class="hint">Bell–Evans fit: slope kT/xβ = ${f(bell.slope, 3)} → xβ = ${f(bell.xb, 1)} ± ${f(bell.xbSe, 1)} Å.</p>` : '<p class="hint">Run two or more speeds to fit xβ.</p>');
    } else {
      const pts = rows.map(r => ({ x: r.tun.filter(Number.isFinite).map(() => r.c), y: r.tun.filter(Number.isFinite).map(Math.log), color: color(r.c), points: true }));
      html += chartBox('c-bell', 'Unfolding time against force', C.line({ id: 'bell', series: pts, xLabel: 'force (ε/Å)', yLabel: 'ln time to unfold (τ)', height: 300 }), '<p class="hint">Time to reach half of the contour. Exponential force dependence → xβ = −kT · slope.</p>');
    }
    html += chartBox('c-dlc', 'Contour length released per event', C.hist({ values: allDlc.map(v => v / 10), xLabel: 'ΔLc (nm)', height: 300, emptyText: 'No events with a measurable ΔLc' }), `<p class="hint">Growth of the chain length in the force path (bonds plus still-intact native contacts) from each event to the next. Lengths come from the structure, so ΔLc compares directly with experiment; the sum over events is the contour released by full unfolding.</p>`);
    html += '</div>';
    // unfolding order
    const slow = runs.filter(r => r._cond === conds[0]);
    const order = A.breakOrder(slow);
    if (order && order.length) {
      const res = s.residues;
      html += chartBox('c-map', 'Unfolding order of native contacts', C.heat({ n: s.n, cells: order, min: 0, max: 1, loLabel: 'early', hiLabel: 'late / kept', tickLabel: i => res[Math.round(i)], axisLabel: 'residue', label: (i, j, v) => `${res[i]}–${res[j]}: ${f(100 * v, 0)} % of the run` , width: 460 }), `<p class="hint">Each square is a native contact (upper and lower triangle mirror), coloured by when it broke for good, averaged over the ${slow.length} runs at ${condLabel(conds[0])}. The 3D view can be coloured the same way.</p>`);
      st.residueOrder = A.residueOrder(order, s.n);
      const o = $('color-by').querySelector('option[value=break]'); o.disabled = false;
      $('color-by').value = 'break'; viewer.colorBy('values', st.residueOrder);
    }
    html += `<div class="panel" id="movie-panel"><div class="chart-head"><h3>Unfolding pathways and movie</h3>
      <div class="chart-tools"><select id="mv-cond" class="btn btn-sm btn-secondary" aria-label="Condition">${conds.map(c => `<option value="${c}">${condLabel(c)}</option>`).join('')}</select></div></div>
      <div id="mv-paths"></div>
      <div class="run-row" style="margin-top:10px"><button class="btn btn-primary btn-sm" id="mv-make">Make movie of representative runs</button><span class="small muted" id="mv-status"></span></div>
      <div id="mv-stage" hidden style="margin-top:12px"><canvas id="mv-canvas" style="width:100%;height:auto;border-radius:10px;border:1px solid var(--border)"></canvas>
        <div class="frame-row"><button class="btn btn-sm btn-secondary" id="mv-play">Play</button><input type="range" id="mv-seek" min="0" max="1000" value="0" aria-label="Movie position"><button class="btn btn-sm btn-secondary" id="mv-dl">Download video</button></div></div></div>`;
    $('res-charts').innerHTML = html;
    wireChartExports();
    setupMovie(runs, conds, condLabel, clamp);
    // trajectory frames
    const fr = runs.find(r => r.frames && r.frames.length > 1);
    if (fr) {
      st.frames = fr.frames;
      $('frame-row').hidden = false; $('frame').max = fr.frames.length - 1; $('frame').value = 0;
      $('frame-lbl').textContent = `${condLabel(fr._cond)}, run 1`;
    }
    $('res-tell').innerHTML = `<h3>What this can tell you</h3><ul>
      <li><strong>Where the structure resists force and in what order it comes apart.</strong> The unfolding-order map and the 3D colouring are the most robust output of a structure-based model.</li>
      <li><strong>Rankings under one protocol</strong>: pulling direction A against B, or domain X against Y. Ratios of peak tensions are meaningful; absolute values are not (<a href="benchmarks.html">benchmarks</a>).</li>
      <li><strong>Contour-length increments in nm</strong>, which can be matched to the ΔLc of an experimental trace to assign its peaks.</li>
      <li><strong>Not</strong> forces in pN (the model is uncalibrated), the effect of point mutations, solvent, ligands, metals or disulfides, or non-native intermediates. The model only knows the native contacts.</li></ul>`;
    renderComparison();
    $('results').hidden = false; $('results-empty').hidden = true;
  }
  // ---------------------------------------------------------------- pathways & movie
  let movie = null;
  function setupMovie(runs, conds, condLabel, clamp) {
    const s = st.structure, pal = C.palette();
    const show = () => {
      const c = +$('mv-cond').value;
      const rr = runs.filter(r => r._cond === c);
      const P = A.pathways(rr, s.n);
      const real = P.filter(p => p.members.length > 1);
      const chosen = (real.length ? real : P).slice(0, 3);
      const rng = ([a, b]) => `${s.residues[a]}–${s.residues[b]}`;
      const blk = x => x.same ? `within ${rng(x.a)}` : `${rng(x.a)} ↔ ${rng(x.b)}`;
      const desc = p => p.steps.length ? `contacts ${blk(p.steps[0])} break first${p.steps[1] ? `, then ${blk(p.steps[1])}` : ''}` : 'no contact block large enough to follow';
      st.moviePlan = { cond: c, clamp, reps: chosen.map((p, k) => ({ letter: 'ABC'[k], highlight: p.steps.length ? (p.steps[0].same ? [p.steps[0].a] : [p.steps[0].a, p.steps[0].b]) : null, run: rr[p.medoid], n: p.members.length, total: rr.length, desc: desc(p), cohesion: p.cohesion, color: pal[k] })) };
      const others = rr.length - real.reduce((t, p) => t + p.members.length, 0);
      $('mv-paths').innerHTML = `<p class="small" style="margin:0 0 8px">${rr.length} runs at ${condLabel(c)} fall into <strong>${real.length || 1} pathway${(real.length || 1) > 1 ? 's' : ''}</strong>${others && real.length ? ` (${others} run${others > 1 ? 's' : ''} unlike any other)` : ''}. A pathway is defined by its initiating rupture: native contacts are grouped into blocks between ~${Math.max(4, Math.round(s.n / 12))}-residue segments, and runs share a pathway when the same block breaks first. The movie shows the most typical run of each (ρ = how similar the full break order is within the pathway).</p>
        <div class="table-wrap"><table class="pull-table"><thead><tr><th>Pathway</th><th>Runs</th><th>What happens first</th><th>Typical run</th></tr></thead><tbody>${st.moviePlan.reps.map(r => `<tr><td><span class="chart-legend" style="margin:0"><span><i style="background:${r.color}"></i><strong>${r.letter}</strong></span></span></td><td class="n">${r.n} / ${r.total}${r.n > 1 ? ` <small class="muted">ρ ${f(r.cohesion, 2)}</small>` : ''}</td><td>${esc(r.desc)}</td><td class="n">seed ${r.run.seed}</td></tr>`).join('')}</tbody></table></div>`;
    };
    $('mv-cond').onchange = () => { show(); $('mv-stage').hidden = true; if (movie) movie.pause(); };
    show();
    $('mv-make').onclick = makeMovie;
  }
  async function makeMovie() {
    const plan = st.moviePlan, s = st.structure;
    if (!plan) return;
    const cfgs = st.results.config;
    const reqs = plan.reps.map(r => {
      const cfg = cfgs.find(j => j._cond === plan.cond && j.seed === r.run.seed);
      const { _cond, ...rest } = cfg;
      return { ...rest, pdb: st.pdbText, frames: 240 };
    });
    $('mv-make').disabled = true;
    status('mv-status', `Re-running ${reqs.length} representative run${reqs.length > 1 ? 's' : ''} with 240 frames each…`);
    const out = await startJob(reqs);
    $('mv-make').disabled = false;
    if (!out) { status('mv-status', 'Cancelled.'); return; }
    const bad = out.res.find(r => !r || r.error);
    if (bad) { status('mv-status', esc(bad?.error?.message || 'failed'), 'err'); return; }
    // determinism check: the re-run must reproduce the original trajectory exactly
    const same = out.res.every((r, k) => r.tension.length === plan.reps[k].run.tension.length && r.tension.every((v, i) => v === plan.reps[k].run.tension[i]));
    status('mv-status', same ? 'Re-runs reproduce the original trajectories exactly.' : 'Warning: a re-run differs from the original trajectory.', same ? 'ok' : 'err');
    const reps = out.res.map((run, k) => {
      const p = plan.reps[k];
      return { run, color: p.color, highlight: p.highlight, title: `Pathway ${p.letter} · ${p.n} of ${p.total} runs · seed ${run.seed}`, subtitle: p.desc };
    });
    const label = plan.clamp ? `F = ${plan.cond} ε/Å` : `v = ${plan.cond} Å/τ`;
    $('mv-stage').hidden = false;
    if (movie) movie.pause();
    movie = PullMovie($('mv-canvas'), {
      structure: s, reps, clamp: plan.clamp,
      header: `${s.label}: pulled ${st.anchor} → ${st.pull}, ${label}`,
      onTime: t => { $('mv-seek').value = Math.round(t * 1000); },
      onEnd: () => { $('mv-play').textContent = 'Play'; }
    });
    $('mv-play').onclick = () => { if (movie.playing) { movie.pause(); $('mv-play').textContent = 'Play'; } else { movie.play(); $('mv-play').textContent = 'Pause'; } };
    $('mv-seek').oninput = () => { movie.pause(); $('mv-play').textContent = 'Play'; movie.seek(+$('mv-seek').value / 1000); };
    $('mv-dl').onclick = async () => {
      $('mv-dl').disabled = true; $('mv-play').disabled = true;
      status('mv-status', 'Recording the movie in real time (about 15 s)…');
      try {
        const { blob, mime } = await movie.record();
        const ext = mime.includes('mp4') ? 'mp4' : 'webm';
        C.download(`smash-pull-${(s.label.split(':')[0] || 'protein').toLowerCase()}-${st.anchor}-${st.pull}.${ext}`, blob);
        status('mv-status', `Saved ${ext.toUpperCase()} (${(blob.size / 1e6).toFixed(1)} MB).`, 'ok');
      } catch (e) { status('mv-status', esc(e.message), 'err'); }
      $('mv-dl').disabled = false; $('mv-play').disabled = false; $('mv-play').textContent = 'Play';
    };
    window.__pullMovie = movie; // used by the test harness to export example movies
    movie.play(); $('mv-play').textContent = 'Pause';
    $('mv-stage').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  async function renderComparison() {
    const s = st.structure; if (!s) return;
    const id = (s.label.split(':')[0] || '').toUpperCase();
    let bench = null;
    try { const r = await fetch('data/benchmarks.json'); if (r.ok) bench = await r.json(); } catch (e) { /* offline is fine */ }
    const b = bench && bench.protein && bench.protein.find(x => x.pdb === id);
    const old = $('res-compare'); if (old) old.remove();
    const box = document.createElement('div');
    box.className = 'panel'; box.style.marginTop = '14px'; box.id = 'res-compare';
    box.innerHTML = `<h3>Compare</h3><p class="small">${b ? `Precomputed benchmark for ${esc(b.name)}: ${b.directions.map(d => `${esc(d.label)} peak ${f(d.peak_mean)} ± ${f(d.peak_sd)} ε/Å${d.experiment ? ` (experiment: ${esc(d.experiment)})` : ''}`).join('; ')}. <a href="benchmarks.html#protein">All benchmarks</a>.` : 'No precomputed benchmark for this structure yet.'} Experimental studies in the hub: <a href="../explore.html?q=${encodeURIComponent(id && id !== 'UPLOAD' ? id : s.sequence.slice(0, 12))}">search SMASH-BIO</a>.</p>`;
    $('res-tell').insertAdjacentElement('afterend', box);
  }

  // ---------------------------------------------------------------- nucleic results
  function renderNucleic() {
    const R = st.results, L = R.landscape, sm = L.summary;
    const old = $('res-compare'); if (old) old.remove();
    const pal = C.palette();
    let html = '';
    const kv = [`<div><dt>ΔG fold</dt><dd>${f(sm.dG_fold_kcal, 1)} <small>kcal/mol (${f(sm.dG_unfold_kT, 1)} kT)</small></dd></div>`,
      `<div><dt>F½</dt><dd>${sm.F_half_pN == null ? 'n/a' : f(sm.F_half_pN, 1) + ' <small>pN, experimental</small>'}</dd></div>`,
      `<div><dt>Δx at F½</dt><dd>${sm.delta_x_at_F_half_nm == null ? 'n/a' : f(sm.delta_x_at_F_half_nm, 1) + ' <small>nm</small>'}</dd></div>`,
      `<div><dt>Contour released</dt><dd>${f(sm.delta_Lc_nm, 1)} <small>nm</small></dd></div>`];
    if (sm.intermediates.length) kv.push(`<div><dt>Intermediates at F½</dt><dd>${sm.intermediates.map(i => `${i.n_open} bp open`).join(', ')}</dd></div>`);
    const runs = R.runs;
    if (runs.length && !R.clamp) {
      const un = runs.flatMap(r => r.transitions.filter(t => t.unfold).slice(0, 1).map(t => t.force_pn));
      const re = runs.flatMap(r => r.transitions.filter(t => !t.unfold).slice(-1).map(t => t.force_pn));
      kv.push(`<div><dt>Unfolding force</dt><dd>${f(A.mean(un), 1)} ± ${f(A.sd(un), 1)} <small>pN</small></dd></div>`, `<div><dt>Refolding force</dt><dd>${f(A.mean(re), 1)} ± ${f(A.sd(re), 1)} <small>pN</small></dd></div>`);
    }
    let dw = null;
    if (runs.length && R.clamp) {
      const all = runs.map(r => A.dwells(r.transitions));
      const fo = all.flatMap(d => d.fold), op = all.flatMap(d => d.open);
      dw = { fo, op };
      kv.push(`<div><dt>Mean folded lifetime</dt><dd>${fo.length ? f(A.mean(fo) * 1e3, 2) + ' <small>ms</small>' : '—'}</dd></div>`, `<div><dt>Mean open lifetime</dt><dd>${op.length ? f(A.mean(op) * 1e3, 2) + ' <small>ms</small>' : '—'}</dd></div>`, `<div><dt>Transitions</dt><dd>${runs.reduce((s, r) => s + r.transitions.length, 0)}</dd></div>`);
    }
    $('res-summary').innerHTML = `<dl class="kv">${kv.join('')}</dl><p class="hint">Physical units (pN, nm, s). Attempt rate k₀ = ${esc($('na-k0').value)} s⁻¹ is an input, not a fit; kinetics scale with it.</p>`;
    // equilibrium curve
    const eq = L.equilibrium;
    const series = [{ x: eq.extension_nm, y: eq.force_pn, color: C.css('--text-2'), width: 2, dash: '5 4' }];
    if (runs.length && !R.clamp) {
      runs.slice(0, 12).forEach(r => {
        const k = r.refold_start;
        const ext = r.trap_nm.map((x, i) => x - r.force_pn[i] / (+$('na-k').value || 0.3));
        series.push({ x: ext.slice(0, k), y: r.force_pn.slice(0, k), color: pal[1], opacity: 0.45, width: 1.1 });
        series.push({ x: ext.slice(k), y: r.force_pn.slice(k), color: pal[0], opacity: 0.45, width: 1.1 });
      });
    }
    if (!R.clamp) html += chartBox('c-nfec', 'Force–extension', C.line({ id: 'nfec', series, xLabel: 'extension change of handles + molecule (nm)', yLabel: 'force (pN)' }), C.legend([[C.css('--text-2'), 'equilibrium'], ...(runs.length ? [[pal[1], 'pulling'], [pal[0], 'relaxing']] : [])]));
    if (R.clamp && runs.length) {
      const r = runs[0];
      html += chartBox('c-hop', `Hopping at ${f(r.force_pn[0], 1)} pN`, C.line({ id: 'hop', series: [{ x: r.time_s.map(t => t * 1e3), y: r.trap_nm, color: pal[0], width: 1 }], xLabel: 'time (ms)', yLabel: 'molecular extension (nm)' }));
    }
    html += '<div class="grid2">';
    const land = sm.landscape_at_F_half_kT;
    html += chartBox('c-land', sm.F_half_pN != null ? `Free energy at F½ = ${f(sm.F_half_pN, 1)} pN` : 'Free energy at zero force', C.line({ id: 'land', series: [{ x: land.map((_, i) => i), y: land, color: pal[2], width: 2 }], xLabel: 'base pairs open', yLabel: 'ΔG (kT)', height: 300 }));
    if (runs.length && !R.clamp) {
      const un = runs.flatMap(r => r.transitions.filter(t => t.unfold).map(t => t.force_pn));
      html += chartBox('c-rup', 'Unfolding forces', C.hist({ values: un, xLabel: 'force at unfolding (pN)', height: 300, color: pal[1] }));
    } else if (dw) {
      html += chartBox('c-dwell', 'Folded dwell times', C.hist({ values: dw.fo.map(t => t * 1e3), xLabel: 'dwell (ms)', height: 300 }));
    }
    html += '</div>';
    $('res-charts').innerHTML = html;
    wireChartExports();
    $('res-tell').innerHTML = `<h3>What this can tell you</h3><ul>
      <li><strong>How sequence, salt and temperature change stability</strong>: trends in F½ and ΔG with GC content, stem length or loop size are reliable (<a href="benchmarks.html#gate4">benchmarks</a>).</li>
      <li><strong>Extension changes and contour lengths</strong> in nm, to identify which part of a construct opened in an experimental trace.</li>
      <li><strong>Hysteresis and hopping</strong> for a given attempt rate; the absolute time scale is only as good as k₀.</li>
      <li><strong>Not yet</strong> absolute forces to better than about 5 pN, mismatches, bulges, pseudoknots or tertiary structure, or Mg²⁺ beyond an approximate equivalence.</li></ul>`;
    $('results').hidden = false; $('results-empty').hidden = true;
  }

  // ---------------------------------------------------------------- export & share
  function exportCsv() {
    const R = st.results; if (!R) return;
    let lines = [];
    if (R.kind === 'protein') {
      lines.push('# SMASH-Pull protein runs; tension in model units (epsilon/Angstrom), not pN; time in tau');
      lines.push('condition,seed,sample,time_tau,extension_A,tension_eps_per_A');
      R.runs.forEach(r => r.time.forEach((t, i) => lines.push(`${r._cond},${r.seed},${i},${t},${r.extension_a[i]},${r.tension[i]}`)));
    } else {
      lines.push('# SMASH-Pull nucleic runs; force pN, trap/extension nm, time s');
      lines.push('seed,sample,time_s,trap_nm,force_pN,bp_open');
      R.runs.forEach(r => r.time_s.forEach((t, i) => lines.push(`${r.seed},${i},${t},${r.trap_nm[i]},${r.force_pn[i]},${r.n_open[i]}`)));
      if (!R.runs.length) { lines.push('# equilibrium'); lines.push('extension_nm,force_pN,mean_bp_open'); const e = R.landscape.equilibrium; e.force_pn.forEach((F, i) => lines.push(`${e.extension_nm[i]},${F},${e.mean_open[i]}`)); }
    }
    C.download('smash-pull.csv', lines.join('\n'), 'text/csv');
  }
  function exportJson() {
    const R = st.results; if (!R) return;
    const out = { generator: 'SMASH-Pull (pull-engine wasm)', created: new Date().toISOString(), share_url: location.href, source: st.src ? { kind: st.src.kind, id: st.src.id, source: st.src.source } : null, results: R };
    C.download('smash-pull.json', JSON.stringify(out), 'application/json');
  }
  function saveHash() {
    const h = new URLSearchParams();
    h.set('m', st.mode);
    if (st.mode === 'protein' && st.src && st.src.kind && st.src.kind !== 'file') {
      h.set('src', st.src.kind + ':' + st.src.id.replace(/^AF-(.*)-F1$/, '$1'));
      if (st.chain) h.set('chain', st.chain);
      if (st.range) h.set('range', st.range.join('-'));
      if (st.anchor != null) h.set('a', st.anchor);
      if (st.pull != null) h.set('p', st.pull);
      h.set('inst', st.pInst); h.set('proto', st.pProto);
    }
    if (st.mode === 'nucleic') {
      h.set('seq', $('na-seq').value.trim()); h.set('c', $('na-construct').value); h.set('t', $('na-t').value); h.set('na', $('na-na').value); h.set('mg', $('na-mg').value); h.set('inst', st.nInst);
    }
    history.replaceState(null, '', '#' + h.toString());
  }
  async function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    if (h.get('m') === 'nucleic') {
      setMode('nucleic');
      if (h.get('seq')) $('na-seq').value = h.get('seq');
      if (h.get('c')) $('na-construct').value = h.get('c');
      ['t', 'na', 'mg'].forEach(k => { if (h.get(k)) $('na-' + k).value = h.get(k); });
      if (h.get('inst')) { st.nInst = h.get('inst'); setSeg('n-inst', st.nInst); naInst(); }
      naPreview(); return;
    }
    const src = h.get('src');
    if (!src) return;
    const [kind, id] = src.split(':');
    if (h.get('inst')) { st.pInst = h.get('inst'); setSeg('p-inst', st.pInst); pInst(); }
    if (h.get('proto') && !PHONE) { st.pProto = h.get('proto'); setSeg('p-proto', st.pProto); pProto(); }
    st.chain = h.get('chain'); st.range = h.get('range') ? h.get('range').split('-').map(Number) : null;
    const a = h.get('a'), p = h.get('p');
    status('load-status', 'Fetching…');
    try {
      const r = kind === 'af' ? await S.alphafold(id) : await S.pdb(id);
      const chain = st.chain, range = st.range;
      st.src = { ...r, kind, id: r.id || id };
      st.pdbText = r.text; st.chains = scanChains(r.text); st.chain = chain || null; st.range = range;
      if (!st.chain) st.chain = [...st.chains].sort((x, y) => y.n - x.n)[0].chain;
      st.anchor = a != null ? +a : null; st.pull = p != null ? +p : null;
      $('chain-sel').innerHTML = st.chains.map(c => `<option value="${esc(c.chain)}"${c.chain === st.chain ? ' selected' : ''}>${esc(c.chain)} (${c.n} res)</option>`).join('');
      $('chain-pick').hidden = !(st.chains.length > 1 || st.range);
      if (st.range) { $('rng-a').value = st.range[0]; $('rng-b').value = st.range[1]; }
      if (kind === 'pdb') $('pdb-id').value = id; else $('af-id').value = id;
      await parse();
    } catch (e) { status('load-status', esc(e.message), 'err'); }
  }

  // ---------------------------------------------------------------- presets
  function pInst() {
    $('p-inst-hint').textContent = PRESET.protein[st.pInst].label;
    if (st.pInst !== 'mt') $('p-k').value = PRESET.protein[st.pInst].k;
    $('f-speeds').hidden = st.pInst === 'mt'; $('f-force').hidden = st.pInst !== 'mt';
    pProto();
  }
  function pProto() {
    const pr = PRESET.proto[st.pProto];
    $('p-custom').hidden = st.pProto !== 'custom';
    const what = st.pInst === 'mt' ? (pr.forces ? `forces ${pr.forces.join(', ')} ε/Å` : '') : (pr.speeds ? `speeds ${pr.speeds.join(', ')} Å/τ` : '');
    $('p-proto-hint').textContent = pr.label + (what ? ` (${what})` : '');
  }
  function naInst() {
    const p = PRESET.nucleic[st.nInst];
    $('na-k').value = p.k; $('na-handle').value = p.handle;
    $('n-ramp-row').hidden = st.nInst === 'mt'; $('n-clamp-row').hidden = st.nInst !== 'mt';
  }

  // ---------------------------------------------------------------- wiring
  document.addEventListener('DOMContentLoaded', () => {
    viewer = PullViewer($('viewer'), {
      onPick: i => {
        const s = st.structure; if (!s) return;
        const res = s.residues[i];
        if (st.pickNext === 'anchor') { st.anchor = res; st.pickNext = 'pull'; } else { st.pull = res; st.pickNext = 'anchor'; }
        if (st.anchor === st.pull) { status('load-status', 'Fixed and pulled residues must differ.', 'err'); return; }
        $('anchor-res').value = st.anchor; $('pull-res').value = st.pull;
        markPoints(); renderStructureInfo(); clearResults(); saveHash();
      }
    });
    $('mode-protein').onclick = () => { setMode('protein'); saveHash(); };
    $('mode-nucleic').onclick = () => { setMode('nucleic'); saveHash(); };
    document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => {
      b.parentElement.querySelectorAll('button').forEach(x => { x.setAttribute('aria-selected', x === b); $(x.dataset.tab).hidden = x !== b; });
    });
    $('pdb-load').onclick = () => { const v = $('pdb-id').value.trim(); if (!S.isPdbId(v)) { status('load-status', 'A PDB ID is four characters, starting with a digit (e.g. 1TIT).', 'err'); return; } loadFrom('pdb', v); };
    $('pdb-id').onkeydown = e => { if (e.key === 'Enter') $('pdb-load').click(); };
    $('af-load').onclick = () => { const v = $('af-id').value.trim(); if (!S.isUniprot(v)) { status('load-status', 'That does not look like a UniProt accession (e.g. P0CG48).', 'err'); return; } loadFrom('af', v); };
    $('af-id').onkeydown = e => { if (e.key === 'Enter') $('af-load').click(); };
    $('seq-load').onclick = loadSequence;
    $('file-in').onchange = async e => {
      const file = e.target.files[0]; if (!file) return;
      if (file.size > 30e6) { status('load-status', 'File larger than 30 MB.', 'err'); return; }
      st.range = null; st.chain = null;
      await loadText(await file.text(), { source: 'uploaded file', kind: 'file', id: file.name });
    };
    document.querySelectorAll('[data-ex]').forEach(b => b.onclick = () => { $('pdb-id').value = b.dataset.ex; loadFrom('pdb', b.dataset.ex); });
    $('reslice').onclick = () => {
      st.chain = $('chain-sel').value;
      const a = +$('rng-a').value, b = +$('rng-b').value;
      const c = st.chains.find(x => x.chain === st.chain);
      st.range = Number.isFinite(a) && Number.isFinite(b) && (a > c.lo || b < c.hi) ? [Math.min(a, b), Math.max(a, b)] : null;
      st.anchor = st.pull = null;
      parse();
    };
    $('chain-sel').onchange = () => { const c = st.chains.find(x => x.chain === $('chain-sel').value); $('rng-a').value = c.lo; $('rng-b').value = Math.min(c.hi, c.lo + 399); };
    const setPoint = () => {
      const s = st.structure; if (!s) return;
      const a = +$('anchor-res').value, p = +$('pull-res').value;
      if (!s.residues.includes(a) || !s.residues.includes(p) || a === p) { status('load-status', `Residues must be two different numbers in ${s.residues[0]}–${s.residues[s.n - 1]}.`, 'err'); return; }
      st.anchor = a; st.pull = p; markPoints(); renderStructureInfo(); clearResults(); saveHash();
    };
    $('anchor-res').onchange = setPoint; $('pull-res').onchange = setPoint;
    $('color-by').onchange = () => {
      const v = $('color-by').value, s = st.structure; if (!s) return;
      if (v === 'index') viewer.colorBy('index'); else if (v === 'plddt') viewer.colorBy('plddt', s.prep.bfactor); else if (st.residueOrder) viewer.colorBy('values', st.residueOrder);
    };
    $('toggle-contacts').onclick = () => { const on = viewer.toggleContacts(); $('toggle-contacts').setAttribute('aria-pressed', on); };
    $('frame').oninput = () => { if (st.frames) viewer.setFrame(st.frames[+$('frame').value], true); };
    $('play').onclick = () => {
      if (st.frameTimer) { clearInterval(st.frameTimer); st.frameTimer = null; $('play').textContent = 'Play'; return; }
      $('play').textContent = 'Pause';
      st.frameTimer = setInterval(() => {
        let i = +$('frame').value + 1;
        if (i > +$('frame').max) i = 0;
        $('frame').value = i; viewer.setFrame(st.frames[i], true);
      }, 90);
    };
    seg('p-inst', 'pInst', pInst); seg('p-proto', 'pProto', pProto); seg('n-inst', 'nInst', () => { naInst(); });
    if (PHONE) {
      $('phone-warn').hidden = false;
      $('p-proto').querySelectorAll('button').forEach(b => { if (b.dataset.v !== 'quick') { b.disabled = true; b.title = 'Not available on this device'; } });
    }
    pInst(); naInst();
    ['na-seq', 'na-stem', 'na-loop', 'na-t', 'na-na', 'na-mg', 'na-k', 'na-handle', 'na-thermo', 'na-polymer'].forEach(id => $(id).addEventListener('input', () => { naPreview(); saveHash(); }));
    $('na-construct').onchange = () => { $('na-stem-row').hidden = $('na-construct').value !== 'stem'; naPreview(); saveHash(); };
    document.querySelectorAll('[data-na]').forEach(b => b.onclick = () => {
      const e = NA_EX[b.dataset.na];
      $('na-seq').value = e.seq || randomDuplex(600, 20261014);
      $('na-construct').value = e.construct; $('na-stem-row').hidden = true;
      $('na-t').value = e.t; $('na-na').value = e.na;
      naPreview(); saveHash();
    });
    $('run-btn').onclick = run;
    $('cancel-btn').onclick = () => { if (st.job) st.job.cancel(); };
    $('exp-csv').onclick = exportCsv; $('exp-json').onclick = exportJson;
    $('exp-link').onclick = async () => {
      saveHash();
      const note = st.src && st.src.kind === 'file' ? ' (uploaded files are not part of the link)' : '';
      try { await navigator.clipboard.writeText(location.href); status('run-status', 'Link copied' + note + '.', 'ok'); } catch (e) { status('run-status', 'Copy this address: ' + esc(location.href), ''); }
    };
    document.addEventListener('smash:theme', () => { if (!st.results) return; st.results.kind === 'protein' ? renderProtein() : renderNucleic(); });
    readHash();
  });
})();
