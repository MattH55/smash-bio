// SMASH-Pull page chrome: site navigation, section bar, footer and theme.
// Mirrors ../js/app.js (same classes, same 'smash:theme' storage) but with '../'
// links, because app.js only rewrites links for the /sim/ folder. Once the
// one-line change in docs/pull/INTEGRATION.md is applied, these pages can load
// ../js/app.js instead and this file can go.
(function () {
  'use strict';
  const store = {
    get(k, d) { try { const v = localStorage.getItem('smash:' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('smash:' + k, JSON.stringify(v)); } catch (e) { /* private mode */ } }
  };
  const applyTheme = t => { if (t) document.documentElement.setAttribute('data-theme', t); else document.documentElement.removeAttribute('data-theme'); };
  applyTheme(store.get('theme', null));
  const toggleTheme = () => {
    const cur = document.documentElement.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    const next = cur === 'dark' ? 'light' : 'dark';
    applyTheme(next); store.set('theme', next);
    document.dispatchEvent(new CustomEvent('smash:theme'));
  };
  const NAV = [
    ['index.html', 'Home'], ['explore.html', 'Explore'], ['systems.html', 'Systems'],
    ['datasets.html', 'Datasets'], ['viewer.html', 'Data viewer'], ['stats.html', 'Insights'], ['sim/index.html', 'Simulations <span class="nav-beta">beta</span>'],
    ['pull/index.html', 'Pull <span class="nav-beta">beta</span>'],
    ['schema.html', 'Schema'], ['submit.html', 'Submit'], ['about.html', 'About']
  ];
  const SUB = [['index.html', 'Simulator'], ['benchmarks.html', 'Benchmarks &amp; validation'], ['about.html', 'Model &amp; limits']];
  const LOGO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="5" cy="12" r="3" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="3" fill="currentColor" stroke="none"/><path d="M8 12c1.2-3 2.3-3 3.5 0s2.3 3 3.5 0"/></svg>';
  const ICON = {
    search: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    theme: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18z" fill="currentColor"/></svg>',
    menu: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    close: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>'
  };
  window.PullIcons = ICON;
  function render() {
    const file = (location.pathname.split('/').pop() || 'index.html').toLowerCase() || 'index.html';
    const nav = document.getElementById('site-nav');
    if (nav) {
      nav.className = 'navbar';
      nav.innerHTML = `<div class="nav-container">
        <a href="../index.html" class="logo" aria-label="SMASH-BIO home"><span class="logo-mark">${LOGO}</span><span>SMASH<span class="logo-accent">-BIO</span></span></a>
        <ul class="nav-links" id="nav-links">${NAV.map(([h, l]) => `<li><a href="../${h}"${h === 'pull/index.html' ? ' class="active" aria-current="page"' : ''}>${l}</a></li>`).join('')}</ul>
        <div class="nav-actions">
          <a href="../explore.html" class="icon-btn" aria-label="Search the hub" title="Search">${ICON.search}</a>
          <button class="icon-btn" id="theme-btn" aria-label="Toggle dark mode" title="Toggle theme">${ICON.theme}</button>
          <a href="../submit.html" class="btn btn-primary btn-sm">Submit data</a>
          <button class="icon-btn mobile-menu-btn" id="menu-btn" aria-label="Open menu" aria-expanded="false">${ICON.menu}</button>
        </div></div>`;
      document.getElementById('theme-btn').onclick = toggleTheme;
      const mb = document.getElementById('menu-btn'), links = document.getElementById('nav-links');
      mb.onclick = () => { const o = links.classList.toggle('active'); mb.setAttribute('aria-expanded', o); mb.innerHTML = o ? ICON.close : ICON.menu; };
      const bar = document.createElement('div');
      bar.className = 'section-bar';
      bar.innerHTML = `<div class="container section-bar-inner">
        <span class="sim-tag">SMASH-Pull</span><span class="sim-tag sim-tag-beta">Beta</span>
        <nav aria-label="Pulling simulator">${SUB.map(([h, l]) => `<a href="${h}"${file === h ? ' class="active" aria-current="page"' : ''}>${l}</a>`).join('')}</nav>
        <a class="section-bar-exp" href="../explore.html">Experimental studies</a></div>`;
      nav.insertAdjacentElement('afterend', bar);
    }
    const foot = document.getElementById('site-footer');
    if (foot) {
      foot.className = 'footer';
      foot.innerHTML = `<div class="container"><div class="footer-grid">
        <div><a href="../index.html" class="logo"><span class="logo-mark">${LOGO}</span><span>SMASH<span class="logo-accent">-BIO</span></span></a>
          <p>SMASH-BIO, the Single Molecule Analysis and Spectroscopy Hub. SMASH-Pull runs entirely in your browser. Structures are fetched from public servers; nothing you enter or upload is sent anywhere else.</p></div>
        <div><h4>Pull</h4><ul><li><a href="index.html">Simulator</a></li><li><a href="benchmarks.html">Benchmarks</a></li><li><a href="about.html">Model &amp; limits</a></li></ul></div>
        <div><h4>Hub</h4><ul><li><a href="../explore.html">Explore studies</a></li><li><a href="../systems.html">Biological systems</a></li><li><a href="../datasets.html">Datasets</a></li></ul></div>
        <div><h4>Simulations <span class="nav-beta">beta</span></h4><ul><li><a href="../sim/index.html">Overview</a></li><li><a href="../sim/explore.html">Explore simulations</a></li></ul></div>
        <div><h4>Project</h4><ul><li><a href="../about.html">About &amp; methods</a></li><li><a href="mailto:mhalma@opensourcemed.info">Contact</a></li></ul></div>
      </div><div class="footer-bottom"><span>&copy; 2024–2026 SMASH-BIO</span><span id="build-stamp"></span></div></div>`;
    }
  }
  document.addEventListener('DOMContentLoaded', render);
})();
