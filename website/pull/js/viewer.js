// Lightweight Cα trace viewer on a 2D canvas (no WebGL, no Mol*): drag to rotate,
// wheel/pinch to zoom, click a residue to pick it. Chosen over Mol* to keep the
// page dependency-free and the network limited to structure servers (see
// docs/pull/ARCHITECTURE.md, decision D4).
'use strict';
window.PullViewer = function (canvas, opts = {}) {
  const ctx = canvas.getContext('2d');
  let xyz = null, n = 0, colors = [], native = null;
  let R = [1, 0, 0, 0, 1, 0, 0, 0, 1];
  let zoom = 1, center = [0, 0, 0], radius = 20;
  let marks = {}; // index -> {color, label}
  let contacts = null; // [[i,j]] drawn faint when shown
  let showContacts = false;
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  function fit(c) {
    let s = [0, 0, 0];
    for (let i = 0; i < c.length; i += 3) { s[0] += c[i]; s[1] += c[i + 1]; s[2] += c[i + 2]; }
    const m = c.length / 3;
    center = s.map(v => v / m);
    let r = 1;
    for (let i = 0; i < c.length; i += 3) r = Math.max(r, Math.hypot(c[i] - center[0], c[i + 1] - center[1], c[i + 2] - center[2]));
    radius = r;
  }
  function rot(ax, ay) {
    const cy = Math.cos(ay), sy = Math.sin(ay), cx = Math.cos(ax), sx = Math.sin(ax);
    const Ry = [cy, 0, sy, 0, 1, 0, -sy, 0, cy], Rx = [1, 0, 0, 0, cx, -sx, 0, sx, cx];
    const mul = (A, B) => { const C = new Array(9).fill(0); for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) for (let k = 0; k < 3; k++) C[i * 3 + j] += A[i * 3 + k] * B[k * 3 + j]; return C; };
    R = mul(mul(Rx, Ry), R);
  }
  function project() {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
    const scale = zoom * 0.46 * Math.min(w, h) / radius;
    const P = new Array(n);
    for (let i = 0; i < n; i++) {
      const x = xyz[3 * i] - center[0], y = xyz[3 * i + 1] - center[1], z = xyz[3 * i + 2] - center[2];
      const X = R[0] * x + R[1] * y + R[2] * z, Y = R[3] * x + R[4] * y + R[5] * z, Z = R[6] * x + R[7] * y + R[8] * z;
      P[i] = [w / 2 + X * scale, h / 2 - Y * scale, Z];
    }
    return { P, dpr, w, h, scale };
  }
  function draw() {
    if (!xyz) return;
    const { P, dpr, w, h, scale } = project();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const zr = radius || 1;
    const fade = z => 0.35 + 0.65 * Math.min(1, Math.max(0, (z / zr + 1) / 2));
    if (showContacts && contacts) {
      ctx.lineWidth = 1;
      ctx.strokeStyle = css('--text-3');
      ctx.globalAlpha = 0.25;
      ctx.beginPath();
      for (const [i, j] of contacts) { ctx.moveTo(P[i][0], P[i][1]); ctx.lineTo(P[j][0], P[j][1]); }
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    // bonds, back to front
    const order = [...Array(Math.max(0, n - 1)).keys()].sort((a, b) => (P[a][2] + P[a + 1][2]) - (P[b][2] + P[b + 1][2]));
    const lw = Math.max(2, Math.min(7, scale * 1.4));
    ctx.lineCap = 'round';
    for (const i of order) {
      ctx.globalAlpha = fade((P[i][2] + P[i + 1][2]) / 2);
      ctx.strokeStyle = colors[i] || css('--accent');
      ctx.lineWidth = lw;
      ctx.beginPath(); ctx.moveTo(P[i][0], P[i][1]); ctx.lineTo(P[i + 1][0], P[i + 1][1]); ctx.stroke();
    }
    ctx.globalAlpha = 1;
    for (const k of Object.keys(marks)) {
      const i = +k, m = marks[k];
      if (!P[i]) continue;
      ctx.fillStyle = m.color; ctx.strokeStyle = css('--surface'); ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(P[i][0], P[i][1], lw * 1.3 + 3, 0, 7); ctx.fill(); ctx.stroke();
      ctx.fillStyle = css('--text'); ctx.font = '600 12px system-ui, sans-serif';
      ctx.fillText(m.label, P[i][0] + lw + 6, P[i][1] - lw - 4);
    }
  }
  // interaction
  let drag = null, moved = false;
  const pts = new Map();
  canvas.addEventListener('pointerdown', e => { canvas.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); drag = [e.clientX, e.clientY]; moved = false; });
  canvas.addEventListener('pointermove', e => {
    if (!pts.has(e.pointerId)) return;
    const prev = pts.get(e.pointerId);
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 2) {
      const [a, b] = [...pts.values()];
      const d1 = Math.hypot(a[0] - b[0], a[1] - b[1]);
      const other = [...pts.entries()].find(([id]) => id !== e.pointerId)[1];
      const d0 = Math.hypot(prev[0] - other[0], prev[1] - other[1]);
      if (d0 > 0) zoom = Math.min(8, Math.max(0.3, zoom * d1 / d0));
      moved = true; draw(); return;
    }
    const dx = e.clientX - prev[0], dy = e.clientY - prev[1];
    if (Math.abs(e.clientX - drag[0]) + Math.abs(e.clientY - drag[1]) > 4) moved = true;
    rot(dy * 0.01, dx * 0.01);
    draw();
  });
  const up = e => {
    pts.delete(e.pointerId);
    if (!moved && opts.onPick && xyz) {
      const r = canvas.getBoundingClientRect();
      const { P } = project();
      const x = e.clientX - r.left, y = e.clientY - r.top;
      let best = -1, bd = 18;
      for (let i = 0; i < n; i++) { const d = Math.hypot(P[i][0] - x, P[i][1] - y); if (d < bd) { bd = d; best = i; } }
      if (best >= 0) opts.onPick(best);
    }
  };
  canvas.addEventListener('pointerup', up);
  canvas.addEventListener('pointercancel', e => pts.delete(e.pointerId));
  canvas.addEventListener('wheel', e => { e.preventDefault(); zoom = Math.min(8, Math.max(0.3, zoom * Math.exp(-e.deltaY * 0.0015))); draw(); }, { passive: false });
  window.addEventListener('resize', () => draw());
  document.addEventListener('smash:theme', () => draw());

  return {
    setStructure(coords, contactList) {
      xyz = Float64Array.from(coords); native = xyz; n = xyz.length / 3; contacts = contactList || null;
      fit(xyz); R = [1, 0, 0, 0, 1, 0, 0, 0, 1]; zoom = 1; marks = {};
      this.colorBy('index');
    },
    setFrame(coords, refit) { xyz = Float64Array.from(coords); if (refit) fit(xyz); draw(); },
    resetFrame() { xyz = native; fit(xyz); draw(); },
    colorBy(mode, values) {
      const hue = t => `hsl(${Math.round(240 - 240 * t)} 70% 52%)`;
      if (mode === 'index') colors = [...Array(n).keys()].map(i => hue(i / Math.max(1, n - 1)));
      else if (mode === 'plddt') colors = values.map(b => !Number.isFinite(b) ? '#999' : b >= 90 ? '#0053d6' : b >= 70 ? '#65cbf3' : b >= 50 ? '#ffdb13' : '#ff7d45');
      else if (mode === 'values') { const f = values.filter(Number.isFinite); const lo = Math.min(...f), hi = Math.max(...f); colors = values.map(v => Number.isFinite(v) ? hue((v - lo) / ((hi - lo) || 1)) : css('--series-muted')); }
      draw();
    },
    setMarks(m) { marks = m || {}; draw(); },
    toggleContacts() { showContacts = !showContacts; draw(); return showContacts; },
    reset() { R = [1, 0, 0, 0, 1, 0, 0, 0, 1]; zoom = 1; if (xyz) fit(xyz); draw(); },
    draw
  };
};
