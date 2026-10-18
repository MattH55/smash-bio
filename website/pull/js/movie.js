// Unfolding movies: one horizontal strip per representative trajectory, the
// chain oriented so the pull axis runs left → right, residues coloured by the
// fraction of their native contacts still intact, intact contacts drawn as
// faint lines, and the run's force curve with a moving cursor. Records to a
// video file with MediaRecorder (MP4 where the browser supports it, else WebM).
'use strict';
window.PullMovie = function (canvas, opts) {
  const { structure, reps, clamp, header } = opts;
  const ctx = canvas.getContext('2d');
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const W = 1280, K = reps.length;
  const ROW = K === 1 ? 440 : K === 2 ? 300 : 236, TOP = 54, BOT = 44;
  const H = (TOP + K * ROW + BOT) + ((TOP + K * ROW + BOT) % 2);
  canvas.width = W; canvas.height = H;
  const n = structure.n, nat = structure.coords;
  const contacts = structure.contacts.map(([i, j]) => [i, j, dist(nat, i, j)]);
  const nContacts = new Array(n).fill(0);
  contacts.forEach(([i, j]) => { nContacts[i]++; nContacts[j]++; });
  function dist(c, i, j) { return Math.hypot(c[3 * i] - c[3 * j], c[3 * i + 1] - c[3 * j + 1], c[3 * i + 2] - c[3 * j + 2]); }

  // Frame of reference: x along anchor → pull (native), y the in-plane
  // principal axis of the native structure, z depth.
  const ia = reps[0].run.anchor_index, ip = reps[0].run.pull_index;
  const A = [nat[3 * ia], nat[3 * ia + 1], nat[3 * ia + 2]];
  const sub = (p, q) => [p[0] - q[0], p[1] - q[1], p[2] - q[2]];
  const dot = (p, q) => p[0] * q[0] + p[1] * q[1] + p[2] * q[2];
  const nrm = p => { const l = Math.hypot(...p) || 1; return p.map(v => v / l); };
  const cross = (p, q) => [p[1] * q[2] - p[2] * q[1], p[2] * q[0] - p[0] * q[2], p[0] * q[1] - p[1] * q[0]];
  const ex = nrm(sub([nat[3 * ip], nat[3 * ip + 1], nat[3 * ip + 2]], A));
  let u = nrm(cross(ex, Math.abs(ex[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0])), v = cross(ex, u);
  { // principal direction in the (u, v) plane
    let suu = 0, svv = 0, suv = 0;
    for (let i = 0; i < n; i++) { const d = sub([nat[3 * i], nat[3 * i + 1], nat[3 * i + 2]], A); const a = dot(d, u), b = dot(d, v); suu += a * a; svv += b * b; suv += a * b; }
    const th = 0.5 * Math.atan2(2 * suv, suu - svv);
    const u2 = u.map((x, k) => Math.cos(th) * x + Math.sin(th) * v[k]);
    v = nrm(cross(ex, u2)); u = nrm(u2);
  }
  const ey = u, ez = v;
  const proj = (c, i) => { const d = [c[3 * i] - A[0], c[3 * i + 1] - A[1], c[3 * i + 2] - A[2]]; return [dot(d, ex), dot(d, ey), dot(d, ez)]; };
  // common scale over every frame of every representative
  let x0 = Infinity, x1 = -Infinity, ymax = 1;
  for (const r of reps) for (const f of r.run.frames) for (let i = 0; i < n; i++) { const p = proj(f, i); x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); ymax = Math.max(ymax, Math.abs(p[1])); }
  const AREA_L = 24, AREA_R = 860, CH_L = 900, CH_R = W - 24;
  const scale = Math.min((AREA_R - AREA_L - 40) / (x1 - x0 + 10), (ROW - 70) / (2 * ymax + 10));

  // force-curve ranges
  const series = reps.map(r => ({ x: clamp ? r.run.time : r.run.extension_a, y: r.run.tension }));
  const cx0 = Math.min(...series.map(s => Math.min(...s.x))), cx1 = Math.max(...series.map(s => Math.max(...s.x)));
  const cyv = series.flatMap(s => s.y);
  const cy0 = Math.min(0, Math.min(...cyv)), cy1 = Math.max(...cyv) * 1.08;

  function lerpFrame(r, fpos) {
    const F = r.run.frames, k = Math.min(F.length - 2, Math.floor(fpos)), w = fpos - k;
    if (F.length === 1) return { coords: F[0], step: r.run.frame_steps[0] || 0 };
    const a = F[k], b = F[k + 1], out = new Float64Array(a.length);
    for (let q = 0; q < a.length; q++) out[q] = a[q] + (b[q] - a[q]) * w;
    return { coords: out, step: r.run.frame_steps[k] + (r.run.frame_steps[k + 1] - r.run.frame_steps[k]) * w };
  }
  const C_INTACT = [42, 120, 214], C_BROKEN = [235, 104, 52], C_NONE = [150, 150, 150];
  const mix = (a, b, t) => `rgb(${a.map((x, k) => Math.round(x + (b[k] - x) * t))})`;

  function drawRow(r, row, fpos) {
    const y0 = TOP + row * ROW, mid = y0 + ROW / 2 + 12;
    const { coords: c, step } = lerpFrame(r, fpos);
    // contact state
    const intactRes = new Array(n).fill(0);
    const intact = contacts.map(([i, j, r0]) => { const ok = dist(c, i, j) < 1.2 * r0; if (ok) { intactRes[i]++; intactRes[j]++; } return ok; });
    const P = Array.from({ length: n }, (_, i) => proj(c, i));
    const X = p => AREA_L + 20 + (p[0] - x0) * scale, Y = p => mid - p[1] * scale;
    // row background + labels
    ctx.fillStyle = row % 2 ? css('--surface-2') : css('--surface');
    ctx.fillRect(0, y0, W, ROW);
    ctx.fillStyle = css('--text'); ctx.font = '600 17px system-ui, sans-serif';
    ctx.fillText(r.title, AREA_L, y0 + 24);
    ctx.fillStyle = css('--text-2'); ctx.font = '14px system-ui, sans-serif';
    ctx.fillText(r.subtitle, AREA_L, y0 + 44);
    // intact contacts
    ctx.lineWidth = 1; ctx.strokeStyle = css('--text-3'); ctx.globalAlpha = 0.28; ctx.beginPath();
    contacts.forEach(([i, j], k) => { if (intact[k]) { ctx.moveTo(X(P[i]), Y(P[i])); ctx.lineTo(X(P[j]), Y(P[j])); } });
    ctx.stroke(); ctx.globalAlpha = 1;
    // backbone, back to front
    const zmin = Math.min(...P.map(p => p[2])), zmax = Math.max(...P.map(p => p[2])) + 1e-9;
    const order = [...Array(n - 1).keys()].sort((a, b) => (P[a][2] + P[a + 1][2]) - (P[b][2] + P[b + 1][2]));
    const lw = Math.max(2.5, Math.min(7, scale * 1.5));
    ctx.lineCap = 'round';
    const resCol = i => nContacts[i] ? mix(C_BROKEN, C_INTACT, intactRes[i] / nContacts[i]) : `rgb(${C_NONE})`;
    if (r.highlight) { // initiating-rupture residues: yellow halo under the backbone
      ctx.strokeStyle = 'rgba(245, 190, 30, 0.55)'; ctx.lineWidth = lw + 9;
      for (const [h0, h1] of r.highlight) {
        ctx.beginPath();
        for (let i = h0; i <= h1; i++) i === h0 ? ctx.moveTo(X(P[i]), Y(P[i])) : ctx.lineTo(X(P[i]), Y(P[i]));
        ctx.stroke();
      }
    }
    for (const i of order) {
      const zf = ((P[i][2] + P[i + 1][2]) / 2 - zmin) / (zmax - zmin);
      ctx.globalAlpha = 0.45 + 0.55 * zf;
      const g = ctx.createLinearGradient(X(P[i]), Y(P[i]), X(P[i + 1]), Y(P[i + 1]));
      g.addColorStop(0, resCol(i)); g.addColorStop(1, resCol(i + 1));
      ctx.strokeStyle = g; ctx.lineWidth = lw;
      ctx.beginPath(); ctx.moveTo(X(P[i]), Y(P[i])); ctx.lineTo(X(P[i + 1]), Y(P[i + 1])); ctx.stroke();
    }
    ctx.globalAlpha = 1;
    // anchor, pulled bead and the trap/spring
    const pa = P[r.run.anchor_index], pp = P[r.run.pull_index];
    ctx.fillStyle = '#1baf7a'; ctx.fillRect(X(pa) - 9, Y(pa) - 9, 18, 18);
    if (!clamp) {
      const trapX = r.run.extension0_a + r.run.speed * r.run.dt * step;
      const tx = AREA_L + 20 + (trapX - x0) * scale, ty = mid;
      ctx.strokeStyle = css('--text-3'); ctx.lineWidth = 1.5; ctx.setLineDash([5, 4]);
      ctx.beginPath(); ctx.moveTo(X(pp), Y(pp)); ctx.lineTo(tx, ty); ctx.stroke(); ctx.setLineDash([]);
      ctx.strokeStyle = css('--text-2'); ctx.lineWidth = 2; ctx.strokeRect(tx - 6, ty - 6, 12, 12);
    } else {
      ctx.strokeStyle = css('--text-2'); ctx.lineWidth = 2.5; ctx.beginPath();
      ctx.moveTo(X(pp) + 10, Y(pp)); ctx.lineTo(X(pp) + 40, Y(pp)); ctx.lineTo(X(pp) + 32, Y(pp) - 6); ctx.moveTo(X(pp) + 40, Y(pp)); ctx.lineTo(X(pp) + 32, Y(pp) + 6); ctx.stroke();
    }
    ctx.fillStyle = '#eb6834'; ctx.beginPath(); ctx.arc(X(pp), Y(pp), 8, 0, 7); ctx.fill();
    // force curve
    const s = series[row], cyT = y0 + 20, cyB = y0 + ROW - 34;
    const CX = x => CH_L + (x - cx0) / ((cx1 - cx0) || 1) * (CH_R - CH_L), CY = y => cyB - (y - cy0) / ((cy1 - cy0) || 1) * (cyB - cyT);
    ctx.strokeStyle = css('--border-strong'); ctx.lineWidth = 1; ctx.strokeRect(CH_L, cyT, CH_R - CH_L, cyB - cyT);
    const si = Math.min(s.x.length - 1, Math.round(step / r.run.sample_every));
    ctx.lineWidth = 1.2; ctx.strokeStyle = css('--series-muted'); ctx.beginPath();
    s.x.forEach((x, i) => i ? ctx.lineTo(CX(x), CY(s.y[i])) : ctx.moveTo(CX(x), CY(s.y[i]))); ctx.stroke();
    ctx.strokeStyle = r.color; ctx.lineWidth = 1.8; ctx.beginPath();
    for (let i = 0; i <= si; i++) i ? ctx.lineTo(CX(s.x[i]), CY(s.y[i])) : ctx.moveTo(CX(s.x[i]), CY(s.y[i]));
    ctx.stroke();
    ctx.fillStyle = r.color; ctx.beginPath(); ctx.arc(CX(s.x[si]), CY(s.y[si]), 5, 0, 7); ctx.fill();
    ctx.fillStyle = css('--text-3'); ctx.font = '12px system-ui, sans-serif';
    ctx.fillText(clamp ? 'extension (Å) vs time (τ)' : 'tension (ε/Å) vs extension (Å)', CH_L, cyB + 18);
    ctx.textAlign = 'right';
    ctx.fillText(clamp ? `${s.y[si].toFixed(0)} Å` : `${s.y[si].toFixed(2)} ε/Å · ${s.x[si].toFixed(0)} Å`, CH_R, cyB + 18);
    ctx.textAlign = 'left';
    const lost = intact.filter(x => !x).length;
    ctx.fillStyle = css('--text-2'); ctx.font = '13px system-ui, sans-serif';
    ctx.fillText(`${contacts.length - lost} / ${contacts.length} native contacts intact`, AREA_L, y0 + ROW - 12);
  }

  function draw(t) {
    ctx.fillStyle = css('--surface'); ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = css('--text'); ctx.font = '700 19px system-ui, sans-serif';
    ctx.fillText(header, 24, 34);
    reps.forEach((r, row) => drawRow(r, row, t * (r.run.frames.length - 1)));
    const yb = TOP + K * ROW;
    ctx.fillStyle = css('--surface-2'); ctx.fillRect(0, yb, W, H - yb);
    ctx.fillStyle = css('--accent'); ctx.fillRect(24, yb + 10, (W - 48) * t, 4);
    ctx.font = '13px system-ui, sans-serif'; ctx.fillStyle = css('--text-2');
    const sw = (c, x, l) => { ctx.fillStyle = mix(c, c, 0); ctx.fillRect(x, yb + 24, 14, 10); ctx.fillStyle = css('--text-2'); ctx.fillText(l, x + 20, yb + 34); };
    sw(C_INTACT, 24, 'contacts intact'); sw(C_BROKEN, 160, 'contacts lost');
    ctx.fillStyle = '#1baf7a'; ctx.fillRect(290, yb + 24, 10, 10); ctx.fillStyle = css('--text-2'); ctx.fillText('fixed', 306, yb + 34);
    ctx.fillStyle = '#eb6834'; ctx.beginPath(); ctx.arc(364, yb + 29, 5, 0, 7); ctx.fill(); ctx.fillStyle = css('--text-2'); ctx.fillText('pulled', 376, yb + 34);
    if (reps.some(r => r.highlight)) { ctx.fillStyle = 'rgba(245, 190, 30, 0.8)'; ctx.fillRect(440, yb + 24, 18, 10); ctx.fillStyle = css('--text-2'); ctx.fillText('first contacts to break', 464, yb + 34); }
    ctx.textAlign = 'right'; ctx.fillText('SMASH-Pull · smash-bio.org/pull · Cα Gō model, model units', W - 24, yb + 34); ctx.textAlign = 'left';
  }

  let t = 0, playing = false, last = 0, raf = 0;
  const DURATION = opts.duration || 14; // seconds for t: 0 → 1
  function tick(now) {
    if (!playing) return;
    if (last) t = Math.min(1, t + (now - last) / 1000 / DURATION);
    last = now; draw(t);
    if (opts.onTime) opts.onTime(t);
    if (t >= 1) { playing = false; if (opts.onEnd) opts.onEnd(); return; }
    raf = requestAnimationFrame(tick);
  }
  draw(0);
  const api = {
    play() { if (t >= 1) t = 0; playing = true; last = 0; raf = requestAnimationFrame(tick); },
    pause() { playing = false; cancelAnimationFrame(raf); },
    seek(x) { t = Math.max(0, Math.min(1, x)); draw(t); },
    get playing() { return playing; },
    redraw() { draw(t); },
    // Record one full pass; resolves with {blob, mime}.
    record() {
      const types = ['video/mp4;codecs=avc1.42E01E', 'video/mp4', 'video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'];
      const mime = types.find(m => window.MediaRecorder && MediaRecorder.isTypeSupported(m));
      if (!mime) return Promise.reject(new Error('This browser cannot record video from a canvas.'));
      const stream = canvas.captureStream(30);
      const rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 6e6 });
      const chunks = [];
      rec.ondataavailable = e => e.data.size && chunks.push(e.data);
      return new Promise(resolve => {
        rec.onstop = () => resolve({ blob: new Blob(chunks, { type: mime.split(';')[0] }), mime });
        const prevEnd = opts.onEnd;
        opts.onEnd = () => { opts.onEnd = prevEnd; setTimeout(() => rec.stop(), 400); if (prevEnd) prevEnd(); };
        rec.start(250);
        t = 0; draw(0);
        setTimeout(() => api.play(), 500); // hold the first frame briefly
      });
    }
  };
  return api;
};
