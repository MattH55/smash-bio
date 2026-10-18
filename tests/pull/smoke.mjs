// Browser smoke test of website/pull/index.html against a local static server.
// Usage: node smoke.mjs [base_url] [outdir]
import { launch } from './cdp.mjs';
const base = process.argv[2] || 'http://127.0.0.1:8791/pull/';
const out = process.argv[3] || '.';
const b = await launch({ port: 9334 });
const log = (...a) => console.log(...a);
try {
  await b.goto(base + 'index.html');
  log('chrome', b.version);
  await b.eval(`document.querySelector('[data-ex="1UBQ"]').click()`);
  await b.waitFor(`document.getElementById('load-status').classList.contains('ok') || document.getElementById('load-status').classList.contains('err')`, 60000);
  log('load:', await b.eval(`document.getElementById('load-status').textContent`));
  await b.eval(`document.getElementById('run-btn').click()`);
  const t0 = Date.now();
  await b.waitFor(`!document.getElementById('results').hidden || document.getElementById('run-status').classList.contains('err')`, 300000);
  log('protein run:', ((Date.now() - t0) / 1000).toFixed(1), 's |', await b.eval(`document.getElementById('run-status').textContent`));
  log('summary:', await b.eval(`document.getElementById('res-summary').innerText.replace(/\\s+/g,' ').slice(0,400)`));
  await b.screenshot(out + '/smoke_protein.png');
  // nucleic
  await b.eval(`document.getElementById('mode-nucleic').click()`);
  await b.eval(`document.querySelector('[data-na="hp20"]').click()`);
  await b.waitFor(`document.querySelector('#struct-info .kv')`, 30000);
  log('na info:', await b.eval(`document.getElementById('struct-info').innerText.replace(/\\s+/g,' ').slice(0,300)`));
  await b.eval(`document.getElementById('run-btn').click()`);
  await b.waitFor(`!document.getElementById('results').hidden || document.getElementById('run-status').classList.contains('err')`, 300000);
  log('nucleic run:', await b.eval(`document.getElementById('run-status').textContent`));
  log('summary:', await b.eval(`document.getElementById('res-summary').innerText.replace(/\\s+/g,' ').slice(0,400)`));
  await b.screenshot(out + '/smoke_nucleic.png');
  log('hash:', await b.eval('location.hash'));
  const hosts = [...new Set(b.requests.map(u => { try { return new URL(u).host; } catch { return u.slice(0, 20); } }))];
  log('hosts contacted:', hosts.join(', '));
  log('errors:', b.errors.length ? b.errors : 'none');
} catch (e) {
  log('FAILED', e.message, b.errors);
  await b.screenshot(out + '/smoke_fail.png').catch(() => {});
} finally { await b.close(); }
