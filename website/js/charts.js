// Minimal SVG charts (stacked columns, line, horizontal bars, grouped hbars) with hover tooltips.
// Colors come from CSS custom properties (--series-N) so light/dark are both validated steps.
(function () {
  const S = window.SMASH, E = S.esc;
  const NS = 'http://www.w3.org/2000/svg';
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const niceMax = v => { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); const n = v / p; return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p; };
  // round tick step (1/2/5 x 10^n) and an axis max that is a whole number of steps
  const niceScale = (v, n = 4) => { if (v <= 0) return { max: 1, step: 0.25 }; const raw = v / n, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p; const step = (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p; return { max: Math.ceil(v / step - 1e-9) * step, step }; };
  const fmtTick = v => v >= 1000 ? (v / 1000) + 'K' : (Math.round(v * 100) / 100).toString();

  function tooltip(host) {
    let t = host.querySelector('.tooltip');
    if (!t) { t = document.createElement('div'); t.className = 'tooltip'; host.appendChild(t); }
    return {
      show(html, x, y) {
        t.innerHTML = html; t.style.opacity = 1;
        const w = t.offsetWidth, hw = host.clientWidth;
        t.style.left = Math.min(Math.max(0, x + 14), hw - w) + 'px';
        t.style.top = Math.max(0, y - t.offsetHeight - 10) + 'px';
      },
      hide() { t.style.opacity = 0; }
    };
  }
  function legend(series) {
    return `<div class="legend">${series.map(s => `<span><i style="background:var(${s.color})"></i>${E(s.label)}</span>`).join('')}</div>`;
  }
  function tableHtml(head, rows) {
    return `<div class="data-table-wrap" style="margin-top:10px;max-height:320px;overflow:auto"><table class="data-table"><thead><tr>${head.map(h => `<th>${E(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map((c, i) => `<td class="${i ? 'num' : ''}">${E(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  function withTableToggle(el, head, rows) {
    const b = document.createElement('button');
    b.className = 'btn btn-ghost btn-sm table-toggle'; b.innerHTML = '<i class="fas fa-table"></i> Show table';
    const box = document.createElement('div');
    b.onclick = () => { const on = !box.innerHTML; box.innerHTML = on ? tableHtml(head, rows) : ''; b.innerHTML = on ? '<i class="fas fa-chart-column"></i> Hide table' : '<i class="fas fa-table"></i> Show table'; };
    el.appendChild(b); el.appendChild(box);
  }
  const svgEl = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  // bar path: square at baseline, 4px rounded data-end
  const colPath = (x, y, w, h, r) => { r = Math.min(r, w / 2, h); return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`; };

  // ---------------------------------------------------------- stacked columns
  S.stackedColumns = function (el, { cats, series, height = 280, yLabel = '', percent = false }) {
    el.innerHTML = legend(series) + '<div class="chart"></div>';
    const host = el.querySelector('.chart');
    const draw = () => {
      host.innerHTML = '';
      const W = Math.max(320, host.clientWidth), H = height, m = { l: 40, r: 8, t: 8, b: 26 };
      const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': yLabel }, host);
      const totals = cats.map((_, i) => series.reduce((a, s) => a + (s.values[i] || 0), 0));
      const sc = percent ? { max: 1, step: 0.25 } : niceScale(Math.max(...totals)), max = sc.max;
      const iw = W - m.l - m.r, ih = H - m.t - m.b, band = iw / cats.length, bw = Math.min(24, band * 0.72);
      for (let v = 0; v <= max + 1e-9; v += sc.step) {
        const y = m.t + ih - ih * v / max;
        svgEl('line', { x1: m.l, x2: W - m.r, y1: y, y2: y, class: 'gridline' }, svg);
        const t = svgEl('text', { x: m.l - 6, y: y + 4, 'text-anchor': 'end', class: 'axis-text' }, svg); t.textContent = percent ? Math.round(v * 100) + '%' : fmtTick(v);
      }
      const step = Math.ceil(cats.length / Math.floor(iw / 38));
      cats.forEach((c, i) => {
        const x = m.l + band * i + (band - bw) / 2;
        let y = m.t + ih;
        const tot = totals[i] || 1;
        const vis = series.map((s, j) => ({ j, v: percent ? (s.values[i] || 0) / tot : (s.values[i] || 0) })).filter(o => o.v > 0);
        vis.forEach((o, n) => {
          const h = ih * o.v / max;
          const gap = n < vis.length - 1 ? 0 : 0;
          const top = n === vis.length - 1;
          const hh = Math.max(0, h - (n > 0 ? 2 : 0));
          y -= h;
          const d = top ? colPath(x, y, bw, hh, 4) : `M${x},${y}h${bw}v${hh}h${-bw}Z`;
          svgEl('path', { d, fill: `var(${series[o.j].color})` }, svg);
        });
        if (i % step === 0) { const t = svgEl('text', { x: x + bw / 2, y: H - 8, 'text-anchor': 'middle', class: 'axis-text' }, svg); t.textContent = c; }
        const hit = svgEl('rect', { x: m.l + band * i, y: m.t, width: band, height: ih, fill: 'transparent' }, svg);
        hit.addEventListener('mousemove', ev => {
          const rb = host.getBoundingClientRect();
          tip.show(`<div class="tt-title">${E(c)} · ${S.fmt(totals[i])}</div>` + series.map(s => s.values[i] ? `<div class="tt-row"><span><i style="background:var(${s.color})"></i> ${E(s.label)}</span><b>${S.fmt(s.values[i])}${percent ? ` (${Math.round(100 * s.values[i] / tot)}%)` : ''}</b></div>` : '').join(''), ev.clientX - rb.left, ev.clientY - rb.top);
        });
        hit.addEventListener('mouseleave', () => tip.hide());
      });
      const tip = tooltip(host);
    };
    draw();
    new ResizeObserver(() => draw()).observe(host);
    withTableToggle(el, ['', ...series.map(s => s.label), 'Total'], cats.map((c, i) => [c, ...series.map(s => S.fmt(s.values[i] || 0)), S.fmt(series.reduce((a, s) => a + (s.values[i] || 0), 0))]));
  };

  // ---------------------------------------------------------- line (single series, percent)
  S.lineChart = function (el, { cats, values, extra, height = 240, percent = true, label = '' }) {
    el.innerHTML = '<div class="chart"></div>';
    const host = el.querySelector('.chart');
    const draw = () => {
      host.innerHTML = '';
      const W = Math.max(320, host.clientWidth), H = height, m = { l: 40, r: 44, t: 12, b: 26 };
      const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': label }, host);
      const sc = niceScale(Math.max(...values) * 1.05), max = sc.max;
      const iw = W - m.l - m.r, ih = H - m.t - m.b;
      const X = i => m.l + (cats.length === 1 ? iw / 2 : iw * i / (cats.length - 1)), Y = v => m.t + ih - ih * v / max;
      for (let v = 0; v <= max + 1e-9; v += sc.step) {
        svgEl('line', { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: 'gridline' }, svg);
        const t = svgEl('text', { x: m.l - 6, y: Y(v) + 4, 'text-anchor': 'end', class: 'axis-text' }, svg); t.textContent = percent ? Math.round(v * 100) + '%' : fmtTick(v);
      }
      const step = Math.ceil(cats.length / Math.floor(iw / 40));
      cats.forEach((c, i) => { if (i % step === 0) { const t = svgEl('text', { x: X(i), y: H - 8, 'text-anchor': 'middle', class: 'axis-text' }, svg); t.textContent = c; } });
      const pts = values.map((v, i) => `${X(i)},${Y(v)}`).join(' ');
      svgEl('polygon', { points: `${X(0)},${Y(0)} ${pts} ${X(values.length - 1)},${Y(0)}`, fill: 'var(--series-1)', opacity: 0.1 }, svg);
      svgEl('polyline', { points: pts, fill: 'none', stroke: 'var(--series-1)', 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, svg);
      const li = values.length - 1;
      svgEl('circle', { cx: X(li), cy: Y(values[li]), r: 4.5, fill: 'var(--series-1)', stroke: 'var(--surface)', 'stroke-width': 2 }, svg);
      const lt = svgEl('text', { x: X(li) + 8, y: Y(values[li]) + 4, class: 'value-text' }, svg); lt.textContent = percent ? (values[li] * 100).toFixed(1) + '%' : S.fmt(values[li]);
      const cross = svgEl('line', { y1: m.t, y2: m.t + ih, stroke: 'var(--border-strong)', 'stroke-width': 1, opacity: 0 }, svg);
      const dot = svgEl('circle', { r: 5, fill: 'var(--series-1)', stroke: 'var(--surface)', 'stroke-width': 2, opacity: 0 }, svg);
      const hit = svgEl('rect', { x: m.l, y: m.t, width: iw, height: ih, fill: 'transparent' }, svg);
      const tip = tooltip(host);
      hit.addEventListener('mousemove', ev => {
        const rb = svg.getBoundingClientRect(), sx = (ev.clientX - rb.left) * W / rb.width;
        const i = Math.max(0, Math.min(cats.length - 1, Math.round((sx - m.l) / iw * (cats.length - 1))));
        cross.setAttribute('x1', X(i)); cross.setAttribute('x2', X(i)); cross.setAttribute('opacity', 1);
        dot.setAttribute('cx', X(i)); dot.setAttribute('cy', Y(values[i])); dot.setAttribute('opacity', 1);
        const hb = host.getBoundingClientRect();
        tip.show(`<div class="tt-title">${E(cats[i])}</div><div class="tt-row"><span>${E(label)}</span><b>${percent ? (values[i] * 100).toFixed(1) + '%' : S.fmt(values[i])}</b></div>${extra ? extra(i) : ''}`, ev.clientX - hb.left, ev.clientY - hb.top);
      });
      hit.addEventListener('mouseleave', () => { tip.hide(); cross.setAttribute('opacity', 0); dot.setAttribute('opacity', 0); });
    };
    draw();
    new ResizeObserver(() => draw()).observe(host);
    withTableToggle(el, ['', label], cats.map((c, i) => [c, percent ? (values[i] * 100).toFixed(1) + '%' : S.fmt(values[i])]));
  };

  // ---------------------------------------------------------- horizontal bars (HTML, single series)
  S.hbars = function (el, items, { color = '--series-1', fmt = S.fmt, link } = {}) {
    const max = Math.max(...items.map(i => i[1]), 1);
    el.innerHTML = items.map(([k, v, lbl]) => `<div class="hbar-row" title="${E(lbl || k)}: ${fmt(v)}">
      <span class="hb-label">${link ? `<a href="${link(k)}">${E(lbl || k)}</a>` : E(lbl || k)}</span>
      <span class="hb-track"><span class="hb-bar" style="width:${Math.max(0.5, 100 * v / max)}%;background:var(${color})"></span><span class="hb-val">${fmt(v)}</span></span></div>`).join('');
  };

  // ---------------------------------------------------------- 100% stacked horizontal bars
  S.stackedHBars = function (el, { rows, series }) {
    el.innerHTML = legend(series) + rows.map(([k, lbl, vals]) => {
      const tot = vals.reduce((a, b) => a + b, 0) || 1;
      return `<div class="hbar-row" style="grid-template-columns:minmax(110px,34%) 1fr"><span class="hb-label">${E(lbl)} <span class="muted">(${S.fmt(tot)})</span></span>
        <span style="display:flex;gap:2px;height:16px">${vals.map((v, j) => v ? `<span title="${E(series[j].label)}: ${S.fmt(v)} (${(100 * v / tot).toFixed(1)}%)" style="flex:${v} 0 0;background:var(${series[j].color});${j === vals.length - 1 || !vals.slice(j + 1).some(Boolean) ? 'border-radius:0 4px 4px 0' : ''}"></span>` : '').join('')}</span></div>`;
    }).join('');
    withTableToggle(el, ['', ...series.map(s => s.label)], rows.map(([k, lbl, vals]) => [lbl, ...vals.map(S.fmt)]));
  };

  // ---------------------------------------------------------- paired horizontal bars (two series)
  S.pairedHBars = function (el, { rows, series }) {
    el.innerHTML = legend(series) + rows.map(([lbl, a, b]) => `<div class="hbar-row"><span class="hb-label">${E(lbl)}</span><span style="display:flex;flex-direction:column;gap:2px">
      <span class="hb-track"><span class="hb-bar" style="width:${Math.max(0.5, a * 100)}%;height:9px;background:var(${series[0].color})"></span><span class="hb-val">${(a * 100).toFixed(0)}%</span></span>
      <span class="hb-track"><span class="hb-bar" style="width:${Math.max(0.5, b * 100)}%;height:9px;background:var(${series[1].color})"></span><span class="hb-val">${(b * 100).toFixed(0)}%</span></span></span></div>`).join('');
    withTableToggle(el, ['Field', series[0].label, series[1].label], rows.map(([l, a, b]) => [l, (a * 100).toFixed(1) + '%', (b * 100).toFixed(1) + '%']));
  };
})();
