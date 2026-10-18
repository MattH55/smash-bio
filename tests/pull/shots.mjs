// Layout screenshots of the pull pages at desktop and phone widths; reports horizontal overflow.
// Usage: node shots.mjs <outdir> [base]
import { launch } from './cdp.mjs';
const out = process.argv[2] || '.';
const base = process.argv[3] || 'http://127.0.0.1:8791/pull/';
const b = await launch({ port: 9337 });
try {
  for (const [w, h, mobile, tag] of [[1360, 900, false, 'desk'], [375, 812, true, 'phone']]) {
    await b.viewport(w, h, mobile);
    for (const page of ['index.html#m=protein&src=pdb:1UBQ', 'index.html#m=nucleic&seq=GAGTCCTGGATCCTGTCCGCTTTTGCGGACAGGATCCAGGACTC&t=23&na=200', 'about.html', 'benchmarks.html']) {
      await b.goto(base + page, 1500);
      if (page.startsWith('index')) await b.waitFor(`document.querySelector('#struct-info .kv')`, 60000).catch(() => {});
      const ov = await b.eval(`(() => { const W = document.documentElement.clientWidth; const bad = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.right > W + 1 && r.width > 0 && getComputedStyle(e).position !== 'fixed'; }).slice(0, 5).map(e => e.tagName + '.' + (e.className || '') + '#' + (e.id || '') + ' ' + Math.round(e.getBoundingClientRect().right)); return { W, scrollW: document.documentElement.scrollWidth, bad }; })()`);
      const name = `${tag}_${page.split(/[.#]/)[0]}${page.includes('nucleic') ? '_na' : ''}.png`;
      await b.screenshot(`${out}/${name}`);
      console.log(tag, page.slice(0, 40), 'overflow:', ov.scrollW > ov.W ? `${ov.scrollW} > ${ov.W} ${JSON.stringify(ov.bad)}` : 'none');
    }
  }
  console.log('errors:', b.errors.filter(e => !/favicon/.test(e)));
} finally { await b.close(); }
