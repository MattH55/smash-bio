// Renders data/benchmarks.json and data/validation.json.
'use strict';
(function () {
  const C = window.PullChart;
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const f = (v, d = 2) => v == null || !Number.isFinite(+v) ? '—' : (+v).toFixed(d);
  const pill = s => `<span class="gate ${s === 'pass' ? 'pass' : s === 'fail' ? 'fail' : s === 'not_run' ? 'notrun' : 'pending'}">${s.replace('_', ' ')}</span>`;
  let B = null, V = null;
  async function load() {
    const get = async u => { try { const r = await fetch(u); return r.ok ? r.json() : null; } catch (e) { return null; } };
    [B, V] = await Promise.all([get('data/benchmarks.json'), get('data/validation.json')]);
    render();
  }
  function render() {
    const pal = C.palette();
    if (V) {
      $('gate-table').querySelector('tbody').innerHTML = V.gates.map(g => `<tr><td class="n"><strong>${esc(g.id)}</strong></td><td>${esc(g.name)}</td><td>${pill(g.status)}</td><td class="small">${esc(g.detail)}</td></tr>`).join('');
      if (V.gate2_cases) {
        const keys = Object.keys(V.gate2_cases).filter(k => k.startsWith('gfp'));
        const cs = keys.map(k => V.gate2_cases[k]);
        $('gfp-table').querySelector('tbody').innerHTML = cs.map(c => `<tr><td>${c.anchor}–${c.pull}</td><td class="n">${Math.abs(c.pull - c.anchor)} res</td><td class="n">${f(c.mean)} ± ${f(c.sd)}</td><td class="n">${c.experiment_pN}</td></tr>`).join('');
        $('gfp-chart').innerHTML = C.line({ id: 'gfp', series: cs.map((c, i) => ({ x: [c.experiment_pN], y: [c.mean], color: pal[i], points: true, r: 6 })), xLabel: 'experimental unfolding force (pN)', yLabel: 'model peak tension (ε/Å)', height: 300, xRange: [50, 600], yRange: [0, Math.ceil(Math.max(...cs.map(c => c.mean)) / 5) * 5 + 5] }) + C.legend(cs.map((c, i) => [pal[i], `${c.anchor}–${c.pull} (${Math.abs(c.pull - c.anchor)} res)`]));
      }
      if (V.gate4) {
        const g = V.gate4;
        $('g4-hist').innerHTML = '<h3>Predicted F½, 30 stems</h3>' + C.hist({ values: g.F_half_pN, xLabel: 'F½ (pN)', height: 260, min: 8, max: 26, bins: 18, color: pal[1] }) + '<p class="hint">Experiment for this class: 13.2 pN (gate window 10.2–16.2).</p>';
        $('g4-gc').innerHTML = '<h3>Median F½ against GC content</h3>' + C.line({ id: 'gc', series: [{ x: g.gc_series.map(q => q.gc_percent), y: g.gc_series.map(q => q.median_F_half_pN), color: pal[0], width: 2 }, { x: g.gc_series.map(q => q.gc_percent), y: g.gc_series.map(q => q.median_F_half_pN), color: pal[0], points: true }], xLabel: 'GC (%)', yLabel: 'median F½ (pN)', height: 260 });
        $('g4-note').innerHTML = `Median predicted F½ is <strong>${f(g.median_F_half_pN, 1)} pN</strong>, against 13.2 pN measured, so the absolute-force part of the gate <strong>fails</strong>. Median Δx (${f(g.median_delta_x_nm, 1)} nm) passes, and F½ rises monotonically with GC content. With the reference pipeline's thermodynamics (37 °C stacks, no loop term) the median would be ${f(g.reference_thermo.median_F_half_pN, 1)} pN. The predicted Δx is also about 10 % short of experiment. That points at the single-strand elasticity carried over from the reference (0.59 nm/nt, Lp 0.75 nm): a strand that extends too little under force gains too little work on opening, which raises F½. It was not re-fitted, because fitting it to this gate would defeat the gate.`;
      }
    }
    if (B) {
      const p = B.protocol;
      $('prot-proto').textContent = `Browser standard protocol: speeds ${p.speeds.join(', ')} Å/τ, ${p.replicas} replicas each, spring ${p.spring_k} ε/Å², kT ${p.temperature} ε, γ ${p.friction}, dt ${p.dt} τ. Tension in model units (ε/Å), never pN. Engine ${B.engine}, generated ${B.generated}.`;
      const rows = [];
      B.protein.forEach(pr => pr.directions.forEach(d => rows.push(`<tr><td><strong>${esc(pr.name)}</strong><div class="small muted">${esc(pr.pdb)} chain ${esc(pr.chain)}</div></td><td>${esc(d.label)} <span class="small muted">(${d.anchor}–${d.pull})</span></td><td class="n">${f(d.peak_mean)} ± ${f(d.peak_sd)}</td><td class="n">${d.xb_A == null ? '—' : f(d.xb_A, 1) + ' ± ' + f(d.xb_se_A, 1)}</td><td class="n">${f(d.per_speed[0].dlc_total_nm, 1)} <span class="small muted">of ${f(d.contour_nm, 1)}</span></td><td class="small">${esc(d.experiment)}<div class="muted">${esc(d.ref)}</div></td></tr>`)));
      $('prot-table').querySelector('tbody').innerHTML = rows.join('');
      if (!$('prot-note')) $('prot-table').closest('.table-wrap').insertAdjacentHTML('afterend', '<p class="hint" id="prot-note">ΔLc total is at the slowest speed. At faster speeds the run ends before the last contacts break. It matches experiment for I27, ubiquitin, GB1 and protein L. The fitted xβ (0.1–0.6 Å, against 2–3 Å in experiments) and talin\'s high peak, for a domain that unfolds near 5 pN, both show how much of the tension is solvent drag at these speeds (<a href="about.html#protein">why</a>).</p>');
      $('prot-charts').innerHTML = B.protein.flatMap(pr => pr.directions.map(d => ({ pr, d }))).map(({ pr, d }, i) => {
        const series = d.per_speed.filter(q => q.trace).map((q, k) => ({ x: q.trace.x, y: q.trace.y, color: pal[k], width: 1.2 }));
        return `<div class="chart"><h3 style="font-size:.95rem">${esc(pr.name)} ${esc(d.label)}</h3>${C.line({ id: 'p' + i, series, xLabel: 'extension (Å)', yLabel: 'tension (ε/Å)', height: 240 })}${C.legend(d.per_speed.map((q, k) => [pal[k], q.speed + ' Å/τ']))}</div>`;
      }).join('');
      $('na-table').querySelector('tbody').innerHTML = B.nucleic.map(n => `<tr><td><strong>${esc(n.name)}</strong><div class="small muted mono" style="overflow-wrap:anywhere">${esc(n.sequence)}</div></td><td class="small">${f(n.T_K - 273.15, 0)} °C, ${n.na_mM} mM</td><td class="n">${f(n.dG_fold_kcal, 1)}</td><td class="n">${f(n.F_half_pN, 1)}</td><td class="n">${f(n.dx_nm, 1)}</td><td class="n">${f(n.unfold_pN, 1)} ± ${f(n.unfold_sd, 1)} / ${f(n.refold_pN, 1)} ± ${f(n.refold_sd, 1)}</td></tr>`).join('');
      const u = B.unzip;
      $('unzip-chart').innerHTML = `<h3 style="font-size:.95rem">${esc(u.name)}</h3>` + C.line({ id: 'unzip', series: [{ x: u.curve.x, y: u.curve.y, color: pal[0], width: 1.4 }], xLabel: 'extension change (nm)', yLabel: 'force (pN)', height: 260 });
      $('unzip-note').innerHTML = `<p>The equilibrium unzipping force of a 600-bp random sequence averages <strong>${f(u.mean_force_pN, 1)} pN</strong> (range ${f(u.min_pN, 1)}–${f(u.max_pN, 1)} pN). For comparison, ${esc(u.experiment)} (${esc(u.ref)}).</p><p class="muted">Hairpins with mismatches or bulges (HIV TAR, P5ab) are not in the table: the model accepts perfect stems only.</p>`;
    }
  }
  document.addEventListener('DOMContentLoaded', load);
  document.addEventListener('smash:theme', () => { if (B || V) render(); });
})();
