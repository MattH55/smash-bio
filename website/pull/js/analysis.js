// Post-processing of engine results in the page. Every rule here is stated in
// docs/pull/PROTOCOL.md; numbers that depend on a modelling choice carry it.
'use strict';
window.PullAnalysis = (function () {
  const mean = a => a.length ? a.reduce((s, v) => s + v, 0) / a.length : NaN;
  const sd = a => { if (a.length < 2) return NaN; const m = mean(a); return Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / (a.length - 1)); };
  const median = a => { if (!a.length) return NaN; const b = [...a].sort((x, y) => x - y); const n = b.length; return n % 2 ? b[(n - 1) / 2] : (b[n / 2 - 1] + b[n / 2]) / 2; };

  // Marko-Siggia: F Lp / kT = 1/(4(1-x)^2) - 1/4 + x  ->  x(F) by Newton (same as wlc.rs).
  function wlcFraction(f, lp, kt) {
    const y = lp * Math.max(0, f) / kt;
    let x = Math.min(0.98, Math.max(0, 1 - 0.5 / Math.sqrt(Math.max(y, 1e-12))));
    for (let i = 0; i < 30; i++) {
      const d = Math.max(1 - x, 1e-8);
      const r = 0.25 / (d * d) - 0.25 + x - y;
      x = Math.min(0.999, Math.max(0, x - r / (0.5 / (d * d * d) + 1)));
    }
    return x;
  }

  // Protein contour length. A WLC fit to the simulated trace is biased: at the
  // speeds a browser can afford, solvent drag (~γ v N/2) adds to the measured
  // tension and makes the chain look stiffer. The model offers an exact,
  // drag-free alternative: the *effective contour*, the shortest path from the
  // fixed to the pulled residue along bonds (3.8 Å) and through native contacts
  // that are still intact (their native Cα–Cα distance). This is what an
  // experimental ΔLc measures: the length of chain newly placed in the force
  // path. ΔLc of event k = effective contour at the next event's peak (or the
  // end of the run) minus that at event k's peak. Lengths in Å: physical.
  const LP_PROTEIN_A = 4.0;
  function effectiveContour(n, coords, contacts, intact, a, p) {
    const adj = Array.from({ length: n }, () => []);
    for (let i = 0; i + 1 < n; i++) { const d = dist(coords, i, i + 1); adj[i].push([i + 1, d]); adj[i + 1].push([i, d]); }
    contacts.forEach(([i, j], k) => { if (intact[k]) { const d = dist(coords, i, j); adj[i].push([j, d]); adj[j].push([i, d]); } });
    const D = new Float64Array(n).fill(Infinity), done = new Uint8Array(n);
    D[a] = 0;
    for (let it = 0; it < n; it++) {
      let u = -1, best = Infinity;
      for (let v = 0; v < n; v++) if (!done[v] && D[v] < best) { best = D[v]; u = v; }
      if (u < 0 || u === p) break;
      done[u] = 1;
      for (const [v, w] of adj[u]) if (D[u] + w < D[v]) D[v] = D[u] + w;
    }
    return D[p];
  }
  function dist(c, i, j) { return Math.hypot(c[3 * i] - c[3 * j], c[3 * i + 1] - c[3 * j + 1], c[3 * i + 2] - c[3 * j + 2]); }
  // run: engine protein_run result; coords: native Cα coordinates of the same trace.
  function contourIncrements(run, coords) {
    const ev = run.events || [];
    if (!ev.length || !coords) return [];
    const n = coords.length / 3, cb = run.contact_breaks, pairs = cb.map(c => [c[0], c[1]]);
    const lcAt = step => effectiveContour(n, coords, pairs, cb.map(c => c[2] == null || c[2] > step), run.anchor_index, run.pull_index);
    const steps = ev.map(e => e.index * run.sample_every);
    const out = [];
    for (let k = 0; k < ev.length; k++) {
      const before = lcAt(steps[k]);
      const after = lcAt(k + 1 < ev.length ? steps[k + 1] : run.n_steps);
      const d = after - before;
      if (Number.isFinite(d) && d > 0) out.push({ event: k, force: ev[k].force, extension: ev[k].extension_a, dLc: d, lcBefore: before, lcAfter: after });
    }
    return out;
  }
  function finalContour(run, coords) {
    const cb = run.contact_breaks;
    return effectiveContour(coords.length / 3, coords, cb.map(c => [c[0], c[1]]), cb.map(c => c[2] == null), run.anchor_index, run.pull_index);
  }

  // Bell–Evans: F* = (kT/xβ) ln(r) + c over (ln loading rate, peak) pairs.
  function bellFit(points, kt) {
    const p = points.filter(q => Number.isFinite(q.lnr) && Number.isFinite(q.f));
    const xs = [...new Set(p.map(q => q.lnr.toFixed(6)))];
    if (xs.length < 2) return null;
    const mx = mean(p.map(q => q.lnr)), my = mean(p.map(q => q.f));
    let sxy = 0, sxx = 0;
    for (const q of p) { sxy += (q.lnr - mx) * (q.f - my); sxx += (q.lnr - mx) ** 2; }
    const slope = sxy / sxx, icpt = my - slope * mx;
    // slope standard error
    let ss = 0; for (const q of p) ss += (q.f - (icpt + slope * q.lnr)) ** 2;
    const se = Math.sqrt(ss / Math.max(1, p.length - 2) / sxx);
    return { slope, intercept: icpt, slopeSe: se, xb: slope > 0 ? kt / slope : NaN, xbSe: slope > 0 ? kt * se / slope / slope : NaN, n: p.length };
  }

  // Mean break step of each native contact, as a fraction of the run, over runs.
  function breakOrder(runs) {
    if (!runs.length) return null;
    const nc = runs[0].contact_breaks.length;
    const sum = new Array(nc).fill(0), cnt = new Array(nc).fill(0);
    for (const r of runs) {
      r.contact_breaks.forEach((c, k) => {
        const f = c[2] == null ? 1 : c[2] / r.n_steps;
        sum[k] += f; cnt[k]++;
      });
    }
    return runs[0].contact_breaks.map((c, k) => [c[0], c[1], sum[k] / cnt[k]]);
  }
  // Per-residue unfolding time: mean over the residue's contacts.
  function residueOrder(order, n) {
    const s = new Array(n).fill(0), c = new Array(n).fill(0);
    for (const [i, j, f] of order) { s[i] += f; c[i]++; s[j] += f; c[j]++; }
    return s.map((v, i) => c[i] ? v / c[i] : NaN);
  }

  // Nucleic clamp: dwell times between transitions.
  function dwells(transitions, tEnd) {
    const fold = [], open = [];
    for (let k = 1; k < transitions.length; k++) {
      const dt = transitions[k].t_s - transitions[k - 1].t_s;
      (transitions[k - 1].unfold ? open : fold).push(dt);
    }
    return { fold, open, meanFold: mean(fold), meanOpen: mean(open) };
  }

  // ---- unfolding pathways
  // Native contacts are grouped into blocks: contacts between sequence segments
  // of B ≈ n/12 residues (blocks with >= 3 contacts). A block breaks when the
  // median of its contacts has broken for good. A run's pathway is its
  // initiating rupture: the block that breaks first. (Rank correlation over all
  // contacts was tried first and rejected: the shared peel-from-the-pulled-end
  // order makes every pair of runs correlate at ρ > 0.85, hiding real
  // differences in which element lets go first.) Pathways with one run are
  // reported as "other". Representative = medoid: the run whose full contact
  // break order correlates best with the rest of its pathway.
  const PATHWAY_RHO = null;
  function rankVec(a) {
    const idx = a.map((v, i) => [v, i]).sort((x, y) => x[0] - y[0]);
    const r = new Array(a.length);
    for (let i = 0; i < idx.length;) {
      let j = i; while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j++;
      for (let k = i; k <= j; k++) r[idx[k][1]] = (i + j) / 2;
      i = j + 1;
    }
    return r;
  }
  function pearson(x, y) {
    const n = x.length, mx = mean(x), my = mean(y);
    let sxy = 0, sxx = 0, syy = 0;
    for (let i = 0; i < n; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; }
    return sxx && syy ? sxy / Math.sqrt(sxx * syy) : 1;
  }
  function fingerprint(run) { return run.contact_breaks.map(c => c[2] == null ? 1 : c[2] / run.n_steps); }
  function contactBlocks(contacts, n) {
    const B = Math.max(4, Math.round(n / 12));
    const g = new Map();
    contacts.forEach(([i, j], k) => {
      const key = Math.floor(i / B) + ':' + Math.floor(j / B);
      if (!g.has(key)) g.set(key, { key, a: Math.floor(i / B), b: Math.floor(j / B), idx: [] });
      g.get(key).idx.push(k);
    });
    return { B, blocks: [...g.values()].filter(x => x.idx.length >= 3) };
  }
  function pathways(runs, n) {
    const m = runs.length;
    if (!m) return [];
    const { B, blocks } = contactBlocks(runs[0].contact_breaks, n);
    if (!blocks.length) return [{ members: runs.map((_, i) => i), medoid: 0, cohesion: 1, steps: [] }];
    const fp = runs.map(fingerprint), rk = fp.map(rankVec);
    const blockTimes = fp.map(f => blocks.map(b => median(b.idx.map(k => f[k]))));
    const rho = (a, b) => pearson(rk[a], rk[b]);
    const byFirst = new Map();
    blockTimes.forEach((t, r) => {
      let k = 0; for (let q = 1; q < t.length; q++) if (t[q] < t[k]) k = q;
      if (!byFirst.has(k)) byFirst.set(k, []);
      byFirst.get(k).push(r);
    });
    const span = (blk, end) => [blk * B, Math.min(n - 1, blk * B + B - 1)];
    const out = [...byFirst.entries()].map(([first, members]) => {
      const medoid = members.length === 1 ? members[0] : members.reduce((best, i) => {
        const s = mean(members.filter(j => j !== i).map(j => rho(i, j)));
        return s > best.s ? { i, s } : best;
      }, { i: members[0], s: -Infinity }).i;
      const meanT = blocks.map((_, q) => mean(members.map(r => blockTimes[r][q])));
      const order = meanT.map((t, q) => [t, q]).sort((x, y) => x[0] - y[0]).map(x => x[1]).filter(q => q !== first);
      const steps = [first, ...order.slice(0, 1)].map(q => ({ a: span(blocks[q].a), b: span(blocks[q].b), time: meanT[q], same: blocks[q].a === blocks[q].b }));
      const within = members.length > 1 ? mean(members.flatMap((a, k) => members.slice(k + 1).map(b => rho(a, b)))) : 1;
      return { members, medoid, cohesion: within, steps, firstBlock: blocks[first].key };
    });
    out.sort((x, y) => y.members.length - x.members.length);
    return out;
  }
  // Earliest-unfolding stretches: windows of >= 5 residues with the lowest mean time.
  function earliestSegments(t, k = 2) {
    const n = t.length, w = Math.min(n, Math.max(5, Math.round(n / 10)));
    const val = i => { let s = 0, c = 0; for (let q = i; q < i + w; q++) if (Number.isFinite(t[q])) { s += t[q]; c++; } return c ? s / c : Infinity; };
    const cands = [];
    for (let i = 0; i + w <= n; i++) cands.push([i, val(i)]);
    cands.sort((a, b) => a[1] - b[1]);
    const out = [];
    for (const [i, v] of cands) {
      if (!Number.isFinite(v) || v >= 1) break;
      if (out.some(o => Math.abs(o.start - i) < w)) continue;
      out.push({ start: i, end: i + w - 1, time: v });
      if (out.length === k) break;
    }
    return out;
  }

  return { mean, sd, median, wlcFraction, pathways, fingerprint, PATHWAY_RHO, contourIncrements, effectiveContour, finalContour, bellFit, breakOrder, residueOrder, dwells, LP_PROTEIN_A };
})();
