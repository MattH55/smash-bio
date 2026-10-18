// Browser check of the pages changed on 2026-10-15 (viewer, about, sim overview, schema).
// Usage: node site_check.mjs <outdir> [base]
import { launch } from './cdp.mjs';
const out = process.argv[2] || '.';
const base = process.argv[3] || 'http://127.0.0.1:8791/';
const b = await launch({ width: 1400, height: 1000 });
const log = (...a) => console.log(...a);
try {
  await b.goto(base + 'viewer.html', 2500);
  await b.waitFor(`document.querySelector('#ds-list [data-key]')`, 30000);
  log('viewer datasets:', await b.eval(`document.querySelectorAll('#ds-list [data-key]').length`));
  await b.waitFor(`document.querySelector('#plot svg')`, 30000);
  log('viewer first:', await b.eval(`document.getElementById('ds-head').querySelector('h2').textContent.slice(0,80) + ' | ' + document.getElementById('plot-title').textContent + ' | ' + document.getElementById('cond-toggles').innerText.replace(/\\s+/g,' ')`));
  await b.screenshot(`${out}/viewer_desk.png`);
  await b.goto(base + 'viewer.html#ds=prion_pentosan_polysulfate', 2500);
  await b.waitFor(`document.querySelector('#plot svg')`, 30000);
  log('viewer prion:', await b.eval(`document.getElementById('plot-title').textContent`));
  await b.viewport(375, 812, true);
  await b.goto(base + 'viewer.html', 2500);
  await b.waitFor(`document.querySelector('#plot svg')`, 30000);
  log('viewer phone overflow:', await b.eval(`document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth`));
  await b.screenshot(`${out}/viewer_phone.png`);
  await b.viewport(1400, 1000, false);
  await b.goto(base + 'about.html', 1500);
  log('about:', await b.eval(`[...document.querySelectorAll('h2')].map(h=>h.textContent).join(' | ')`));
  log('about doi ok:', await b.eval(`document.body.innerHTML.includes('10.1016/j.bpj.2025.03.005') && !document.body.innerHTML.includes('2025.02.001') && !document.body.innerHTML.includes('<code>hub/</code>')`));
  await b.goto(base + 'sim/index.html', 2500);
  log('sim tile:', await b.eval(`document.getElementById('k-matched').textContent + ' | ' + document.getElementById('k-matched-sub').textContent`));
  await b.goto(base + 'schema.html', 1500);
  log('schema badge:', await b.eval(`document.querySelector('h1 .badge').textContent`));
  await b.goto(base + 'explore.html', 3000);
  log('explore escaped titles:', await b.eval(`(document.body.innerText.match(/&lt;|&apos;|&amp;/g)||[]).length`));
  log('errors:', b.errors.filter(e => !/favicon|googletagmanager|google-analytics/.test(e)));
} catch (e) { log('FAILED', e.message, b.errors); await b.screenshot(`${out}/site_fail.png`).catch(() => {}); }
finally { await b.close(); }
