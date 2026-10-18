// Minimal Chrome DevTools Protocol driver (no dependencies; Node >= 22 WebSocket).
// Used by the browser checks and gates 5b / 6: launch headless Chrome, open a
// page, evaluate expressions (awaiting promises), collect console errors, and
// take screenshots.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

export const CHROME = process.env.CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));

export async function launch({ width = 1360, height = 900 } = {}) {
  const port = 20000 + Math.floor(Math.random() * 20000); // never collide with a stale instance
  const profile = mkdtempSync(path.join(tmpdir(), 'pullcdp-'));
  const proc = spawn(CHROME, [
    '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    `--window-size=${width},${height}`, '--no-first-run', '--no-default-browser-check',
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding', 'about:blank'
  ], { stdio: 'ignore' });
  let ver;
  for (let i = 0; i < 80; i++) {
    try { ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break; } catch { await sleep(150); }
  }
  if (!ver) throw new Error('chrome did not start');
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = targets.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0;
  const pending = new Map();
  const listeners = [];
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
    else if (m.method) listeners.forEach(l => l(m));
  };
  const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
  const errors = [];
  listeners.push(m => {
    if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errors.push(m.params.args.map(a => a.value ?? a.description).join(' '));
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') errors.push(m.params.entry.text + ' ' + (m.params.entry.url || ''));
  });
  await send('Runtime.enable'); await send('Page.enable'); await send('Log.enable'); await send('Network.enable');
  const requests = [];
  listeners.push(m => { if (m.method === 'Network.requestWillBeSent') requests.push(m.params.request.url); });
  return {
    send, errors, requests, version: ver.Browser,
    async goto(url, waitMs = 800) {
      // A URL that differs only in its #hash is a same-document navigation with no
      // load event; a unique query parameter forces a real load.
      if (url.includes('#')) { const [u, h] = url.split('#'); url = `${u}${u.includes('?') ? '&' : '?'}_nav=${Date.now()}#${h}`; }
      const loaded = new Promise(r => { const l = m => { if (m.method === 'Page.loadEventFired') { listeners.splice(listeners.indexOf(l), 1); r(); } }; listeners.push(l); });
      await send('Page.navigate', { url });
      await loaded; await sleep(waitMs);
    },
    async eval(expr, timeoutMs = 600000) {
      const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true, timeout: timeoutMs });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    },
    async waitFor(expr, timeoutMs = 120000, every = 250) {
      const t0 = Date.now();
      while (Date.now() - t0 < timeoutMs) { if (await this.eval(`!!(${expr})`)) return true; await sleep(every); }
      throw new Error('timeout waiting for ' + expr);
    },
    async viewport(width, height, mobile = false) {
      await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: mobile ? 2 : 1, mobile });
    },
    async screenshot(file, full = true) {
      let clip;
      if (full) {
        const m = await send('Page.getLayoutMetrics');
        const w = Math.ceil(m.cssContentSize.width), h = Math.ceil(Math.min(m.cssContentSize.height, 8000));
        clip = { x: 0, y: 0, width: w, height: h, scale: 1 };
      }
      const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: !!full, ...(clip ? { clip } : {}) });
      writeFileSync(file, Buffer.from(r.data, 'base64'));
    },
    async close() { try { ws.close(); } catch { } proc.kill(); await sleep(400); try { rmSync(profile, { recursive: true, force: true }); } catch { } }
  };
}
