// Minimal SVG charts for SMASH-Pull: line/scatter, histogram, heat map.
// Colours are read from the site's CSS variables at draw time and written into
// the SVG as literal values, so an exported SVG/PNG looks like the screen.
'use strict';
window.PullChart = (function () {
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const palette = () => [1, 2, 3, 4, 5, 7, 8, 6].map(i => css('--series-' + i));
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function niceTicks(lo, hi, n) {
    if (!(hi > lo)) { hi = lo + 1; }
    const span = hi - lo, step0 = span / Math.max(1, n);
    const mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const err = step0 / mag;
    const step = (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1) * mag;
    const t = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) t.push(Math.abs(v) < step * 1e-9 ? 0 : v);
    return t;
  }
  const fmt = v => {
    const a = Math.abs(v);
    if (a === 0) return '0';
    if (a >= 1e4 || a < 1e-2) return v.toExponential(0).replace('e+', 'e');
    return String(+v.toPrecision(3));
  };

  function frame(o, xs, ys) {
    const W = o.width || 640, H = o.height || 340;
    const m = { l: 58, r: 14, t: 12, b: 44 };
    let [x0, x1] = o.xRange || [Math.min(...xs), Math.max(...xs)];
    let [y0, y1] = o.yRange || [Math.min(...ys), Math.max(...ys)];
    if (!(x1 > x0)) { x0 -= 1; x1 += 1; }
    if (!(y1 > y0)) { y0 -= 1; y1 += 1; }
    if (!o.yRange) { const p = (y1 - y0) * 0.05; y0 -= o.yZero && y0 >= 0 ? 0 : p; y1 += p; if (o.yZero && y0 > 0) y0 = 0; }
    const X = v => m.l + (v - x0) / (x1 - x0) * (W - m.l - m.r);
    const Y = v => H - m.b - (v - y0) / (y1 - y0) * (H - m.t - m.b);
    const grid = css('--grid'), text3 = css('--text-3'), border = css('--border-strong');
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="11">`;
    s += `<rect x="0" y="0" width="${W}" height="${H}" fill="${o.background || 'none'}"/>`;
    for (const t of niceTicks(y0, y1, 5)) {
      s += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(t)}" y2="${Y(t)}" stroke="${grid}"/>`;
      s += `<text x="${m.l - 6}" y="${Y(t) + 3.5}" text-anchor="end" fill="${text3}">${fmt(t)}</text>`;
    }
    const xt = o.xTicks || niceTicks(x0, x1, Math.max(3, Math.round((W - m.l - m.r) / 90)));
    for (const t of xt) {
      if (t < x0 - 1e-12 || t > x1 + 1e-12) continue;
      s += `<line x1="${X(t)}" x2="${X(t)}" y1="${H - m.b}" y2="${H - m.b + 4}" stroke="${border}"/>`;
      s += `<text x="${X(t)}" y="${H - m.b + 16}" text-anchor="middle" fill="${text3}">${o.xFmt ? o.xFmt(t) : fmt(t)}</text>`;
    }
    s += `<line x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}" stroke="${border}"/>`;
    s += `<text x="${(m.l + W - m.r) / 2}" y="${H - 8}" text-anchor="middle" fill="${css('--text-2')}" font-size="12">${esc(o.xLabel || '')}</text>`;
    s += `<text transform="translate(14 ${(m.t + H - m.b) / 2}) rotate(-90)" text-anchor="middle" fill="${css('--text-2')}" font-size="12">${esc(o.yLabel || '')}</text>`;
    return { s, X, Y, W, H, m, x0, x1, y0, y1 };
  }

  // series: [{x:[], y:[], color, width, opacity, dash, points:true, label}]
  function line(o) {
    const xs = [], ys = [];
    for (const se of o.series) for (let i = 0; i < se.x.length; i++) if (Number.isFinite(se.x[i]) && Number.isFinite(se.y[i])) { xs.push(se.x[i]); ys.push(se.y[i]); }
    for (const mk of o.markers || []) { xs.push(mk.x); ys.push(mk.y); }
    if (!xs.length) return empty(o);
    const f = frame(o, xs, ys);
    let s = f.s;
    s += `<clipPath id="c${o.id || 'p'}"><rect x="${f.m.l}" y="${f.m.t}" width="${f.W - f.m.l - f.m.r}" height="${f.H - f.m.t - f.m.b}"/></clipPath><g clip-path="url(#c${o.id || 'p'})">`;
    for (const se of o.series) {
      if (se.points) {
        for (let i = 0; i < se.x.length; i++) if (Number.isFinite(se.y[i])) s += `<circle cx="${f.X(se.x[i]).toFixed(1)}" cy="${f.Y(se.y[i]).toFixed(1)}" r="${se.r || 3.2}" fill="${se.color}" fill-opacity="${se.opacity ?? 0.85}"/>`;
        continue;
      }
      let d = '', pen = false;
      for (let i = 0; i < se.x.length; i++) {
        if (!Number.isFinite(se.y[i]) || !Number.isFinite(se.x[i])) { pen = false; continue; }
        d += (pen ? 'L' : 'M') + f.X(se.x[i]).toFixed(1) + ' ' + f.Y(se.y[i]).toFixed(1);
        pen = true;
      }
      s += `<path d="${d}" fill="none" stroke="${se.color}" stroke-width="${se.width || 1.4}" stroke-opacity="${se.opacity ?? 1}" stroke-linejoin="round"${se.dash ? ` stroke-dasharray="${se.dash}"` : ''}/>`;
    }
    for (const mk of o.markers || []) s += `<path d="M${f.X(mk.x)} ${f.Y(mk.y) - 7}l-4.5 -7h9z" fill="${mk.color || css('--text')}"><title>${esc(mk.title || '')}</title></path>`;
    s += '</g></svg>';
    return s;
  }

  function hist(o) {
    const v = o.values.filter(Number.isFinite);
    if (!v.length) return empty(o);
    let lo = o.min ?? Math.min(...v), hi = o.max ?? Math.max(...v);
    if (!(hi > lo)) { lo -= 0.5; hi += 0.5; }
    const nb = o.bins || Math.max(5, Math.min(30, Math.ceil(Math.sqrt(v.length) * 1.5)));
    const w = (hi - lo) / nb;
    const counts = new Array(nb).fill(0);
    for (const x of v) counts[Math.min(nb - 1, Math.max(0, Math.floor((x - lo) / w)))]++;
    const f = frame({ ...o, yZero: true, yLabel: o.yLabel || 'count' }, [lo, hi], [0, Math.max(...counts)]);
    let s = f.s;
    const col = o.color || palette()[0];
    counts.forEach((c, i) => {
      if (!c) return;
      const x = f.X(lo + i * w), x2 = f.X(lo + (i + 1) * w);
      s += `<rect x="${x + 0.5}" y="${f.Y(c)}" width="${Math.max(1, x2 - x - 1)}" height="${f.Y(0) - f.Y(c)}" fill="${col}" fill-opacity=".85"><title>${fmt(lo + i * w)}–${fmt(lo + (i + 1) * w)}: ${c}</title></rect>`;
    });
    return s + '</svg>';
  }

  // Square heat map of an n x n matrix (null = empty), colour from low to high.
  function heat(o) {
    const n = o.n, W = o.width || 420, m = { l: 40, t: 10, b: 36, r: 64 };
    const cell = (W - m.l - m.r) / n, H = m.t + m.b + cell * n;
    const vals = o.cells.map(c => c[2]).filter(Number.isFinite);
    const lo = o.min ?? Math.min(...vals), hi = o.max ?? Math.max(...vals);
    const text3 = css('--text-3');
    const ramp = t => { // viridis-like, 5 stops
      const st = [[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]];
      const u = Math.min(0.9999, Math.max(0, t)) * 4, i = Math.floor(u), w = u - i;
      const c = st[i].map((a, k) => Math.round(a + (st[i + 1][k] - a) * w));
      return `rgb(${c})`;
    };
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" font-family="system-ui, sans-serif" font-size="10">`;
    s += `<rect x="${m.l}" y="${m.t}" width="${cell * n}" height="${cell * n}" fill="none" stroke="${css('--border-strong')}"/>`;
    for (const [i, j, v] of o.cells) {
      const fill = Number.isFinite(v) ? ramp((v - lo) / ((hi - lo) || 1)) : css('--series-muted');
      const r = `width="${Math.max(cell, 1.2)}" height="${Math.max(cell, 1.2)}" fill="${fill}"`;
      s += `<rect x="${m.l + j * cell}" y="${m.t + i * cell}" ${r}><title>${o.label ? esc(o.label(i, j, v)) : ''}</title></rect>`;
      s += `<rect x="${m.l + i * cell}" y="${m.t + j * cell}" ${r}/>`;
    }
    for (const t of niceTicks(0, n - 1, 5)) {
      s += `<text x="${m.l + (t + 0.5) * cell}" y="${m.t + n * cell + 14}" text-anchor="middle" fill="${text3}">${o.tickLabel ? o.tickLabel(t) : t + 1}</text>`;
      s += `<text x="${m.l - 5}" y="${m.t + (t + 0.5) * cell + 3}" text-anchor="end" fill="${text3}">${o.tickLabel ? o.tickLabel(t) : t + 1}</text>`;
    }
    s += `<text x="${m.l + n * cell / 2}" y="${H - 6}" text-anchor="middle" fill="${css('--text-2')}" font-size="11">${esc(o.axisLabel || 'residue')}</text>`;
    const bx = m.l + n * cell + 14, bh = n * cell;
    for (let k = 0; k < 40; k++) s += `<rect x="${bx}" y="${m.t + bh * (1 - (k + 1) / 40)}" width="12" height="${bh / 40 + 0.5}" fill="${ramp(k / 39)}"/>`;
    s += `<text x="${bx + 16}" y="${m.t + 8}" fill="${text3}">${esc(o.hiLabel || fmt(hi))}</text><text x="${bx + 16}" y="${m.t + bh}" fill="${text3}">${esc(o.loLabel || fmt(lo))}</text>`;
    return s + '</svg>';
  }

  function empty(o) {
    const W = o.width || 640, H = o.height || 200;
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}"><text x="${W / 2}" y="${H / 2}" text-anchor="middle" fill="${css('--text-3')}" font-family="system-ui" font-size="13">${esc(o.emptyText || 'No data')}</text></svg>`;
  }

  function legend(items) {
    return `<div class="chart-legend">${items.map(([c, l]) => `<span><i style="background:${c}"></i>${esc(l)}</span>`).join('')}</div>`;
  }

  function download(name, data, type) {
    const blob = data instanceof Blob ? data : new Blob([data], { type });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  function svgWithBackground(svg) {
    return svg.replace('fill="none"/>', `fill="${css('--surface')}"/>`);
  }
  function exportSvg(svg, name) { download(name + '.svg', svgWithBackground(svg), 'image/svg+xml'); }
  function exportPng(svg, name) {
    const s = svgWithBackground(svg);
    const vb = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(s);
    const w = +vb[1] * 2, h = +vb[2] * 2;
    const img = new Image();
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = w; c.height = h;
      const g = c.getContext('2d');
      g.fillStyle = css('--surface'); g.fillRect(0, 0, w, h);
      g.drawImage(img, 0, 0, w, h);
      c.toBlob(b => download(name + '.png', b), 'image/png');
    };
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(s);
  }
  return { line, hist, heat, legend, palette, css, download, exportSvg, exportPng, fmt };
})();
