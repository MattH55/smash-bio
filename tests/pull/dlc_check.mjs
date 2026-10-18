// Diagnostic: events and contour-length increments (effective contour) at the standard speeds.
import { runJobs, readPdb, loadAnalysis } from './run_jobs.mjs';
const A = loadAnalysis();
const pdb = readPdb(process.argv[2] || '1TIT');
const jobs = [0.05, 0.1, 0.2].map(v => ({ op: 'protein_run', pdb, chain: 'A', speed: v, dt: 0.01, seed: 1, max_samples: 1500 }));
const res = await runJobs(jobs, { threads: 3 });
const S = (await runJobs([{ op: 'structure', pdb, chain: 'A' }], { threads: 1 }))[0];
for (const r of res) {
  if (r.error) { console.log(r.error); continue; }
  const inc = A.contourIncrements(r, S.coords);
  console.log(`v=${r.speed} d0=${r.extension0_a.toFixed(0)} contour=${r.contour_a.toFixed(0)} final ext=${r.extension_a.at(-1).toFixed(0)} peak=${r.peak_tension.toFixed(2)} ms=${r._ms.toFixed(0)}`);
  r.events.forEach((e, k) => console.log(`   event ${k}: ext ${e.extension_a.toFixed(0)} F ${e.force.toFixed(2)} drop ${e.drop.toFixed(2)}`));
  console.log('   dLc (A):', inc.map(e => e.dLc.toFixed(0) + ' (' + e.lcBefore.toFixed(0) + '->' + e.lcAfter.toFixed(0) + ')').join(', '), ' final Lc', A.finalContour(r, S.coords).toFixed(0));
}

