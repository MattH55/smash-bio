// Produce example unfolding movies through the real page (headless Chrome).
// Usage: node movies.mjs <outdir> [base]   (base defaults to the local server)
import { writeFileSync } from 'node:fs';
import { launch } from './cdp.mjs';
const out = process.argv[2] || '.';
const base = process.argv[3] || 'http://127.0.0.1:8791/pull/';
const CASES = [
  { name: 'i27', hash: 'm=protein&src=pdb:1TIT&inst=afm&proto=standard' },
  { name: 'ubiquitin-NC', hash: 'm=protein&src=pdb:1UBQ&inst=afm&proto=standard' },
];
const b = await launch({ width: 1400, height: 1000 });
try {
  for (const c of CASES.filter(c => !process.env.ONLY || c.name === process.env.ONLY)) {
    await b.goto(`${base}index.html#${c.hash}`);
    await b.waitFor(`document.getElementById('load-status').classList.contains('ok')`, 60000);
    await b.eval(`document.getElementById('run-btn').click()`);
    const t0 = Date.now();
    await b.waitFor(`!document.getElementById('results').hidden`, 1800000, 500);
    console.log(c.name, 'runs done in', ((Date.now() - t0) / 1000).toFixed(0), 's');
    // pathways at every condition
    const conds = await b.eval(`[...document.querySelectorAll('#mv-cond option')].map(o => o.value)`);
    for (const v of conds) {
      await b.eval(`(() => { const s = document.getElementById('mv-cond'); s.value = ${JSON.stringify(v)}; s.onchange(); })()`);
      console.log(`  v=${v}:`, await b.eval(`document.getElementById('mv-paths').innerText.replace(/\\s+/g, ' ')`));
    }
    // movie at the slowest condition (first option)
    await b.eval(`(() => { const s = document.getElementById('mv-cond'); s.value = ${JSON.stringify(conds[0])}; s.onchange(); })()`);
    await b.eval(`document.getElementById('mv-make').click()`);
    await b.waitFor(`!document.getElementById('mv-stage').hidden && window.__pullMovie`, 900000, 500);
    console.log('  ', await b.eval(`document.getElementById('mv-status').textContent`));
    for (const t of [0, 0.35, 0.7, 1]) {
      await b.eval(`window.__pullMovie.pause(); window.__pullMovie.seek(${t})`);
      const png = await b.eval(`document.getElementById('mv-canvas').toDataURL('image/png')`);
      writeFileSync(`${out}/${c.name}-t${Math.round(t * 100)}.png`, Buffer.from(png.split(',')[1], 'base64'));
    }
    const vid = await b.eval(`(async () => {
      const { blob, mime } = await window.__pullMovie.record();
      const buf = new Uint8Array(await blob.arrayBuffer());
      let s = ''; for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode(...buf.subarray(i, i + 0x8000));
      return { mime, b64: btoa(s) };
    })()`, 120000);
    const ext = vid.mime.includes('mp4') ? 'mp4' : 'webm';
    writeFileSync(`${out}/${c.name}.${ext}`, Buffer.from(vid.b64, 'base64'));
    console.log(`  saved ${c.name}.${ext} (${vid.mime})`);
  }
  console.log('errors:', b.errors.filter(e => !/favicon/.test(e)));
} finally { await b.close(); }
