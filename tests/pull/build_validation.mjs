// Collect gate results into website/pull/data/validation.json for benchmarks.html.
// Status vocabulary: pass | fail | not_run | pending. Missing result files are pending.
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { REPO } from './run_jobs.mjs';
const R = n => { const p = path.join(REPO, 'tests', 'pull', 'results', n + '.json'); return existsSync(p) ? JSON.parse(readFileSync(p, 'utf8').replace(/^﻿/, '')) : null; };
const f = (v, d = 2) => (v == null || !Number.isFinite(v)) ? 'n/a' : (+v).toFixed(d);
const g1ab = R('gate1ab'), g1c = R('gate1c'), g2 = R('gate2'), g4 = R('gate4'), g5 = R('gate5'), g6 = R('gate6');
const gates = [];
gates.push({ id: '1a', name: 'Parity with the reference pipeline (parsing, contact map, energies, deterministic and injected-noise trajectories, nucleic thermodynamics)', status: g1ab ? (g1ab.parity_pass ? 'pass' : 'fail') : 'pending', detail: g1ab ? g1ab.parity_detail : '' });
gates.push({ id: '1b', name: 'Production force field equals reference force field (1TIT, 1UBQ, 2GB1; 21 conformations each)', status: g1ab ? (g1ab.fast_pass ? 'pass' : 'fail') : 'pending', detail: g1ab ? g1ab.fast_detail : '' });
gates.push({ id: '1c', name: 'Statistical equivalence of trajectories with the reference (protocol G1, 30 replicas per engine)', status: g1c ? (g1c.pass ? 'pass' : 'fail') : 'pending',
  detail: g1c ? Object.entries(g1c.proteins).map(([k, v]) => `${k}: KS p = ${f(v.ks_p, 3)}, ρ = ${f(v.spearman_rho_break_order, 3)}`).join('; ') : 'Reference runs in progress (the Python reference needs ≈ 1 s per step).' });
gates.push({ id: '2a', name: 'Ubiquitin: N–C stronger than K48–C', status: g2 ? (g2.gate2a.pass ? 'pass' : 'fail') : 'pending', detail: g2 ? `N–C ${f(g2.gate2a.mean_NC)} vs K48–C ${f(g2.gate2a.mean_K48C)} ε/Å, one-sided Mann–Whitney p = ${g2.gate2a.p_one_sided.toExponential(1)}. Caveat: N–C also spans more chain (drag).` : '' });
gates.push({ id: '2b', name: 'GFP: strong pulling directions above weak ones, Spearman ρ ≥ 0.7 with experiment', status: g2 ? (g2.gate2b.pass ? 'pass' : 'fail') : 'pending', detail: g2 ? `ρ = ${f(g2.gate2b.spearman_rho)}; strong above weak: ${g2.gate2b.strong_above_weak}. Peak tension follows the pulled span (drag), not the measured strength.` : '' });
gates.push({ id: '3', name: 'Nucleic structures against ViennaRNA (100 random sequences)', status: 'not_run', detail: 'Pre-declared: needs a secondary-structure folding algorithm, which the engine does not have; the simulator accepts only perfect stems.' });
gates.push({ id: '4', name: 'DNA hairpins against experiment (20-bp, 55 % GC class; Woodside et al. 2006)', status: g4 ? (g4.pass ? 'pass' : 'fail') : 'pending', detail: g4 ? `Median F½ ${f(g4.median_F_half_pN, 1)} pN (target 13.2 ± 3.0): ${g4.pass_F_half ? 'pass' : 'fail'}; median Δx ${f(g4.median_delta_x_nm, 1)} nm (target 18 ± 20 %): ${g4.pass_delta_x ? 'pass' : 'fail'}; F½ rises with GC: ${g4.gc_monotonic ? 'pass' : 'fail'}.` : '' });
gates.push({ id: '5a', name: 'Native and WebAssembly (Chrome) give byte-identical results', status: g5 ? (g5.a ? 'pass' : 'fail') : 'pending', detail: g5 ? g5.detail_a : '' });
gates.push({ id: '5b', name: 'Two runs in Chrome are byte-identical', status: g5 ? (g5.b ? 'pass' : 'fail') : 'pending', detail: g5 ? g5.detail_b : '' });
gates.push({ id: '5c', name: 'Firefox and Safari', status: 'not_run', detail: 'Neither browser is available on the test machine. Expected identical: all floating-point maths, including transcendental functions, is inside the WebAssembly module.' });
gates.push({ id: '6a', name: 'Titin I27 standard run (3 speeds × 10 replicas) under 60 s in Chrome', status: g6 ? (g6.pass ? 'pass' : 'fail') : 'pending', detail: g6 ? g6.detail : '' });
gates.push({ id: '6b', name: 'Phone performance', status: 'not_run', detail: 'No phone available; phones are limited to the Quick protocol.' });
const out = { generated: new Date().toISOString().slice(0, 10), gates, gate2_cases: g2 ? g2.cases : null, gate4: g4 ? { median_F_half_pN: g4.median_F_half_pN, median_delta_x_nm: g4.median_delta_x_nm, reference_thermo: g4.reference_thermo, gc_series: g4.gc_series, F_half_pN: g4.F_half_pN } : null };
writeFileSync(path.join(REPO, 'website', 'pull', 'data', 'validation.json'), JSON.stringify(out));
console.log(gates.map(g => `${g.id} ${g.status}`).join(' | '));
