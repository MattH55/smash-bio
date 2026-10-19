// SMASH-BIO shared front-end helpers (no build step; works from file:// and any static host)
window.SMASH = window.SMASH || {};

(function () {
  const S = window.SMASH;

  // ------------------------------------------------------------ labels
  S.TECH = {
    optical_tweezers: { label: 'Optical tweezers', short: 'OT', icon: 'fa-bullseye', blurb: 'Focused laser traps hold dielectric beads; force from bead displacement.' },
    magnetic_tweezers: { label: 'Magnetic tweezers', short: 'MT', icon: 'fa-magnet', blurb: 'Magnet-generated field gradients pull superparamagnetic beads; parallel tethers.' },
    torque_tweezers: { label: 'Torque / rotational tweezers', short: 'Torque', icon: 'fa-rotate', blurb: 'Magnetic torque, freely-orbiting and angular optical traps measuring twist.' },
    afm_smfs: { label: 'AFM force spectroscopy', short: 'AFM', icon: 'fa-arrows-up-down', blurb: 'Cantilever-based pulling of molecules, bonds and cells.' },
    acoustic_force_spectroscopy: { label: 'Acoustic force spectroscopy', short: 'AFS', icon: 'fa-wave-square', blurb: 'Standing acoustic waves push many tethered beads at once.' },
    centrifuge_force: { label: 'Centrifuge force microscopy', short: 'CFM', icon: 'fa-circle-notch', blurb: 'Centrifugal force on tethered beads, imaged in a spinning microscope.' },
    nanopore_force: { label: 'Nanopore tweezers', short: 'Nanopore', icon: 'fa-circle-dot', blurb: 'Voltage-driven translocation through a pore applies force (e.g. SPRNT).' },
    hydrodynamic_stretching: { label: 'Hydrodynamic / flow stretching', short: 'Flow', icon: 'fa-water', blurb: 'Laminar flow drag stretches tethered molecules; DNA curtains.' },
    biomembrane_force_probe: { label: 'Biomembrane force probe', short: 'BFP', icon: 'fa-circle-half-stroke', blurb: 'A red blood cell spring measures single-bond kinetics.' },
    micropipette: { label: 'Micropipette manipulation', short: 'Pipette', icon: 'fa-syringe', blurb: 'Micropipette aspiration and adhesion-frequency assays.' },
    tension_sensors: { label: 'Molecular tension sensors', short: 'Tension', icon: 'fa-gauge', blurb: 'DNA tension gauge tethers, hairpin probes and origami force clamps.' },
    microneedle: { label: 'Glass microneedles', short: 'Needle', icon: 'fa-pen-nib', blurb: 'Flexible glass needles as force transducers.' },
    force_spectroscopy_unspecified: { label: 'Force spectroscopy (unspecified)', short: 'SMFS', icon: 'fa-chart-line', blurb: 'Force spectroscopy where the instrument could not be resolved from the abstract.' }
  };
  S.CLASS = {
    unfolding_protein: 'Protein unfolding', unfolding_nucleic_acid: 'Nucleic-acid unfolding', nucleic_acid_protein_interaction: 'Nucleic acid–protein interactions',
    nucleic_acid_mechanics: 'Nucleic-acid mechanics', chromatin_mechanics: 'Chromatin', translation_transcription_replication: 'Transcription / replication / translation',
    force_generation_motor: 'Motors & force generation', force_generation_polymerization: 'Polymerization forces', receptor_ligand_adhesion: 'Receptor–ligand / adhesion bonds',
    membrane_mechanics: 'Membrane mechanics', rheology_cell: 'Cell rheology', rheology_material: 'Material rheology', methods_calibration: 'Methods & calibration'
  };
  S.STATUS = {
    public_repository: { label: 'Public repository', icon: 'fa-database', rank: 0 },
    source_data_supplement: { label: 'Source data file', icon: 'fa-file-csv', rank: 1 },
    journal_supplement: { label: 'Journal supplement', icon: 'fa-paperclip', rank: 2 },
    code_only: { label: 'Code only', icon: 'fa-code', rank: 3 },
    on_request: { label: 'On request', icon: 'fa-envelope', rank: 4 },
    not_available: { label: 'No new data', icon: 'fa-ban', rank: 5 },
    not_stated: { label: 'No statement', icon: 'fa-circle-question', rank: 6 },
    unknown_no_fulltext: { label: 'Not checked (no full text)', icon: 'fa-lock', rank: 7 }
  };
  S.KIND = { primary_research: 'Primary research', review: 'Review', methods: 'Methods', preprint: 'Preprint', correction: 'Correction', other: 'Other' };
  S.CURATION = { author_verified: 'Author verified', curated: 'Curated', ai_assisted: 'AI-assisted', auto_fulltext: 'Auto (full text)', auto_abstract: 'Auto (abstract)' };
  S.OBS = {
    unfolding_force: 'Unfolding force', refolding_force: 'Refolding force', rupture_force: 'Rupture force', unbinding_force: 'Unbinding force',
    unzipping_force: 'Unzipping force', overstretching_force: 'Overstretching force', equilibrium_force: 'Equilibrium force', stall_force: 'Stall force',
    adhesion_force: 'Adhesion force', tether_force: 'Tether force', step_size: 'Step size', persistence_length: 'Persistence length',
    contour_length_increment: 'Contour length increment', contour_length: 'Contour length', stretch_modulus: 'Stretch modulus', velocity: 'Velocity',
    folding_free_energy: 'Free energy', distance_to_transition_state: 'Distance to transition state', bond_lifetime: 'Bond lifetime', torque: 'Torque',
    dwell_time: 'Dwell time', molecular_stiffness: 'Stiffness', elastic_modulus: 'Elastic modulus', rate_constant_zero_force: 'Zero-force rate',
    processivity_run_length: 'Run length', loading_rate: 'Loading rate'
  };
  S.tl = k => (S.TECH[k] || { label: k }).label;
  S.cl = k => S.CLASS[k] || k;
  S.sl = k => (S.STATUS[k] || { label: k }).label;

  // Publication text sometimes arrives with HTML tags and entities (<i>, <sub>, &lt;i&gt;).
  // Decode and strip those before escaping, so the page shows the words rather than the markup.
  const _subMap = { '0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉','+':'₊','-':'₋','=':'₌','(':'₍',')':'₎','a':'ₐ','e':'ₑ','o':'ₒ','x':'ₓ','h':'ₕ','k':'ₖ','l':'ₗ','m':'ₘ','n':'ₙ','p':'ₚ','s':'ₛ','t':'ₜ','v':'ᵥ' };
  const _supMap = { '0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹','+':'⁺','-':'⁻','=':'⁼','(':'⁽',')':'⁾','n':'ⁿ','i':'ⁱ' };
  const _decoder = typeof document !== 'undefined' ? document.createElement('textarea') : null;
  const _decodeOnce = s => s.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);/g, (m) => {
    if (!_decoder) return m;
    _decoder.innerHTML = m;
    return _decoder.value;
  });
  const _toScript = (tag, inner) => {
    const map = String(tag).toLowerCase() === 'sub' ? _subMap : _supMap;
    return [...inner].map(ch => map[ch] || ch).join('');
  };
  S.text = value => {
    let s = String(value == null ? '' : value);
    if (!/[&<]/.test(s)) return s;
    for (let i = 0; i < 3 && s.includes('&'); i++) {
      const next = _decodeOnce(s);
      if (next === s) break;
      s = next;
    }
    s = s.replace(/<\s*br\s*\/?\s*>/gi, ' ');
    s = s.replace(/<\s*(sub|sup)\s*>([\s\S]*?)<\s*\/\s*\1\s*>/gi, (_, tag, inner) => _toScript(tag, inner.replace(/<[^>]*>/g, '')));
    s = s.replace(/<\/?[A-Za-z][^>]*>/g, '');
    return s.replace(/[ \t]{2,}/g, ' ');
  };
  S.esc = s => S.text(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  S.fmt = n => (n == null ? '–' : Number(n).toLocaleString('en-US'));
  S.compact = n => n >= 10000 ? (n / 1000).toFixed(n >= 100000 ? 0 : 1) + 'K' : S.fmt(n);
  S.bytes = b => { if (!b) return ''; const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0; while (b >= 1024 && i < 4) { b /= 1024; i++; } return b.toFixed(b >= 10 || i === 0 ? 0 : 1) + ' ' + u[i]; };
  S.qs = () => new URLSearchParams(location.search);
  S.statusPill = st => `<span class="data-pill ${st}"><i class="fas ${(S.STATUS[st] || {}).icon || 'fa-circle'}"></i>${S.esc(S.sl(st))}</span>`;
  S.doiUrl = d => d ? 'https://doi.org/' + d : null;

  // ------------------------------------------------------------ biological systems: slugs + link-outs
  // must match hub/s09_systems.py slug()
  S.slug = name => String(name || '').toLowerCase().replace(/λ/g, 'lambda').replace(/[φΦ]/g, 'phi').replace(/α/g, 'alpha').replace(/β/g, 'beta')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60);
  // {identifiers:[{scheme,id}], gene, taxon, name, wikipedia:{url}} -> [{label, url, group}]
  S.linkouts = o => {
    const L = [], enc = encodeURIComponent, ids = o.identifiers || [];
    const add = (group, label, url) => { if (url && !L.some(x => x.url === url)) L.push({ group, label, url }); };
    ids.forEach(i => {
      const id = i.id;
      if (i.scheme === 'uniprot') {
        add('Protein', 'UniProt ' + id, `https://www.uniprot.org/uniprotkb/${id}/entry`);
        add('Structure', 'AlphaFold DB', `https://alphafold.ebi.ac.uk/entry/${id}`);
        add('Structure', 'PDBe-KB structures', `https://www.ebi.ac.uk/pdbe/pdbe-kb/proteins/${id}`);
        add('Protein', 'InterPro domains', `https://www.ebi.ac.uk/interpro/protein/UniProt/${id}/`);
        add('Interactions', 'STRING network', `https://string-db.org/cgi/network?identifiers=${id}`);
        add('Pathways', 'Reactome', `https://reactome.org/content/query?q=${id}`);
      }
      if (i.scheme === 'pdb') add('Structure', 'PDB ' + id, `https://www.rcsb.org/structure/${id}`);
      if (i.scheme === 'rfam') { add('RNA', 'Rfam ' + id, `https://rfam.org/family/${id}`); add('RNA', 'RNAcentral', `https://rnacentral.org/search?q=${id}`); }
      if (i.scheme === 'genbank') add('Sequence', 'GenBank ' + id, `https://www.ncbi.nlm.nih.gov/nuccore/${id}`);
      if (i.scheme === 'chebi') add('Chemistry', 'ChEBI ' + id, `https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:${id}`);
      if (i.scheme === 'cl') add('Cell', 'Cell Ontology ' + id, `https://www.ebi.ac.uk/ols4/ontologies/cl/classes?obo_id=${id}`);
      if (i.scheme === 'go') add('Function', 'Gene Ontology ' + id, `https://www.ebi.ac.uk/QuickGO/term/${id}`);
    });
    if (o.gene && o.taxon) add('Gene', `NCBI Gene ${o.gene}`, `https://www.ncbi.nlm.nih.gov/gene/?term=${enc(o.gene)}%5Bsym%5D+AND+${o.taxon}%5Btaxid%5D`);
    if (ids.some(i => i.scheme === 'chebi') && o.name) add('Chemistry', 'PubChem', `https://pubchem.ncbi.nlm.nih.gov/#query=${enc(o.name)}`);
    if (o.wikipedia && o.wikipedia.url) add('Reference', 'Wikipedia', o.wikipedia.url);
    if (o.name) {
      const term = o.name.replace(/\s*\(.*?\)/g, '').split(/\s*\/\s*/)[0];
      add('Literature', 'Europe PMC: force spectroscopy', `https://europepmc.org/search?query=${enc(`"${term}" AND ("force spectroscopy" OR "optical tweezers" OR "magnetic tweezers" OR "single-molecule")`)}`);
    }
    return L;
  };
  S.linkoutHtml = (o, opts = {}) => {
    const L = S.linkouts(o);
    if (!L.length) return opts.empty || '';
    return `<div class="chip-row">${L.map(l => `<a class="idlink ext" href="${S.esc(l.url)}" target="_blank" rel="noopener" title="${S.esc(l.group)}">${S.esc(l.label)}</a>`).join('')}</div>`;
  };

  // ------------------------------------------------------------ storage (per-viewer conveniences only)
  S.store = {
    get(k, d) { try { const v = localStorage.getItem('smash:' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('smash:' + k, JSON.stringify(v)); } catch (e) { /* ignore */ } }
  };

  // ------------------------------------------------------------ theme
  const applyTheme = t => { if (t) document.documentElement.setAttribute('data-theme', t); else document.documentElement.removeAttribute('data-theme'); };
  applyTheme(S.store.get('theme', null));
  S.toggleTheme = () => {
    const cur = document.documentElement.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    const next = cur === 'dark' ? 'light' : 'dark';
    applyTheme(next); S.store.set('theme', next);
    document.dispatchEvent(new CustomEvent('smash:theme'));
  };

  // ------------------------------------------------------------ script loader (file:// safe)
  const loaded = {};
  S.loadScript = src => loaded[src] || (loaded[src] = new Promise((res, rej) => {
    const s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = () => rej(new Error('failed ' + src)); document.head.appendChild(s);
  }));
  // decode the columnar index written by hub/s07_build_site.py (pack_index)
  S.unpackIndex = P => {
    const rows = new Array(P.n), C = P.cols, D = P.dicts;
    for (let i = 0; i < P.n; i++) {
      const r = { id: 'SMFS-' + String(P.ids[i]).padStart(6, '0') };
      for (const k of P.cat) { const c = C[k][i]; r[k] = c < 0 ? null : D[k][c]; }
      for (const k of P.catl) r[k] = C[k][i].map(c => D[k][c]);
      for (const k of P.bool) r[k] = C[k][i] === '1';
      for (const k of P.plain) r[k] = C[k][i];
      rows[i] = r;
    }
    return rows;
  };
  S.shards = {};
  S.registerShard = (n, recs) => { S.shards[n] = recs; };
  S.getRecord = async id => {
    await S.loadScript('data/index.js');
    const row = S.index.find(r => r.id === id);
    if (!row) return null;
    const n = String(row.sh).padStart(3, '0');
    if (!S.shards[row.sh]) await S.loadScript(`data/records/r-${n}.js`);
    return (S.shards[row.sh] || []).find(r => r.record_id === id) || null;
  };

  // ------------------------------------------------------------ chrome
  // Paths are root-relative. Pages under /sim/ get a "../" prefix so the same
  // header and footer work one directory down. Simulations stay a beta section:
  // the main nav item points at /sim/, and the experimental links keep their names.
  const NAV = [
    ['index.html', 'Home'], ['explore.html', 'Explore'], ['modules.html', 'Modules'], ['systems.html', 'Systems'],
    ['datasets.html', 'Datasets'], ['viewer.html', 'Data viewer'], ['stats.html', 'Insights'], ['sim/index.html', 'Simulations <span class="nav-beta">beta</span>'],
    ['pull/index.html', 'Pull <span class="nav-beta">beta</span>'],
    ['schema.html', 'Schema'], ['submit.html', 'Submit'], ['about.html', 'About']
  ];
  const SIM_NAV = [
    ['index.html', 'Overview'], ['explore.html', 'Explore'], ['stats.html', 'Coverage'],
    ['schema.html', 'Schema'], ['submit.html', 'Submit']
  ];
  const LOGO_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="5" cy="12" r="3" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="3" fill="currentColor" stroke="none"/><path d="M8 12c1.2-3 2.3-3 3.5 0s2.3 3 3.5 0"/></svg>';
  S.inSimSection = () => /\/sim\//i.test(String(location.pathname || '').replace(/\\/g, '/'));
  S.inModulesSection = () => /\/modules\//i.test(String(location.pathname || '').replace(/\\/g, '/'));
  S.renderChrome = () => {
    const path = String(location.pathname || '').replace(/\\/g, '/');
    const inSim = /\/sim\//i.test(path);
    const inModules = /\/modules\//i.test(path);
    const file = (path.split('/').pop() || 'index.html').toLowerCase() || 'index.html';
    const prefix = (inSim || inModules) ? '../' : '';
    const nav = document.getElementById('site-nav');
    if (nav) {
      nav.className = 'navbar';
      const items = NAV.map(([href, label]) => {
        const active = inSim ? href === 'sim/index.html' : inModules ? href === 'modules.html' : file === href;
        return `<li><a href="${prefix}${href}"${active ? ' class="active" aria-current="page"' : ''}>${label}</a></li>`;
      }).join('');
      const searchHref = inSim ? 'explore.html' : `${prefix}explore.html`;
      const submitHref = inSim ? 'submit.html' : `${prefix}submit.html`;
      nav.innerHTML = `<div class="nav-container">
        <a href="${prefix}index.html" class="logo" aria-label="SMASH-BIO home"><span class="logo-mark">${LOGO_SVG}</span><span>SMASH<span class="logo-accent">-BIO</span></span></a>
        <ul class="nav-links" id="nav-links">${items}</ul>
        <div class="nav-actions">
          <a href="${searchHref}" class="icon-btn" aria-label="${inSim ? 'Search simulations' : 'Search the hub'}" title="${inSim ? 'Search simulations' : 'Search'}"><i class="fas fa-magnifying-glass"></i></a>
          <button class="icon-btn" id="theme-btn" aria-label="Toggle dark mode" title="Toggle theme"><i class="fas fa-circle-half-stroke"></i></button>
          <a href="${submitHref}" class="btn btn-primary btn-sm">${inSim ? 'Submit simulation' : 'Submit data'}</a>
          <button class="icon-btn mobile-menu-btn" id="menu-btn" aria-label="Open menu" aria-expanded="false"><i class="fas fa-bars"></i></button>
        </div></div>`;
      document.getElementById('theme-btn').onclick = S.toggleTheme;
      const mb = document.getElementById('menu-btn'), links = document.getElementById('nav-links');
      mb.onclick = () => { const o = links.classList.toggle('active'); mb.setAttribute('aria-expanded', o); mb.innerHTML = `<i class="fas ${o ? 'fa-xmark' : 'fa-bars'}"></i>`; };
      let bar = document.getElementById('section-bar');
      if (inSim) {
        if (!bar) {
          bar = document.createElement('div');
          bar.id = 'section-bar';
          nav.insertAdjacentElement('afterend', bar);
        }
        bar.className = 'section-bar';
        bar.innerHTML = `<div class="container section-bar-inner">
          <span class="sim-tag">Simulation</span><span class="sim-tag sim-tag-beta">Beta</span>
          <nav aria-label="Simulations section, beta">${SIM_NAV.map(([href, label]) =>
            `<a href="${href}"${file === href ? ' class="active" aria-current="page"' : ''}>${label}</a>`).join('')}</nav>
          <a class="section-bar-exp" href="${prefix}explore.html">Experimental studies</a>
        </div>`;
      } else if (bar) {
        bar.remove();
      }
    }
    const foot = document.getElementById('site-footer');
    if (foot) {
      foot.className = 'footer';
      foot.innerHTML = `<div class="container"><div class="footer-grid">
        <div><a href="${prefix}index.html" class="logo"><span class="logo-mark">${LOGO_SVG}</span><span>SMASH<span class="logo-accent">-BIO</span></span></a>
          <p>Single Molecule Analysis and Spectroscopy Hub — an open index of force-spectroscopy studies, their biological systems, instruments and data. Pulling simulations are a separate beta section, indexed and counted separately from the experimental records.</p></div>
        <div><h4>Hub</h4><ul><li><a href="${prefix}explore.html">Explore studies</a></li><li><a href="${prefix}modules.html">Experiment modules</a></li><li><a href="${prefix}systems.html">Biological systems</a></li><li><a href="${prefix}datasets.html">Datasets</a></li><li><a href="${prefix}stats.html">Insights</a></li></ul></div>
        <div><h4>Simulations <span class="nav-beta">beta</span></h4><ul><li><a href="${prefix}sim/index.html">Overview</a></li><li><a href="${prefix}sim/explore.html">Explore simulations</a></li><li><a href="${prefix}sim/stats.html">Coverage</a></li><li><a href="${prefix}sim/schema.html">Simulation schema</a></li></ul></div>
        <div><h4>Standard</h4><ul><li><a href="${prefix}schema.html">Force-spectroscopy schema</a></li><li><a href="${prefix}schema.html#downloads">Experimental downloads</a></li><li><a href="${prefix}sim/schema.html#downloads">Simulation downloads</a></li><li><a href="${prefix}sitemap.html">Sitemap</a></li></ul></div>
        <div><h4>Project</h4><ul><li><a href="${prefix}about.html">About &amp; methods</a></li><li><a href="${prefix}about.html#cite">How to cite</a></li><li><a href="${inSim ? 'submit.html' : prefix + 'submit.html'}">Submit a record</a></li><li><a href="mailto:mhalma@opensourcemed.info">Contact</a></li></ul></div>
      </div><div class="footer-bottom"><span>&copy; 2024–2026 SMASH-BIO</span><span id="build-stamp"></span></div></div>`;
      const stamp = document.getElementById('build-stamp');
      if (stamp && inSim && S.sim && S.sim.meta) stamp.textContent = `Simulation index built ${S.sim.meta.built}`;
      else if (stamp && S.meta) stamp.textContent = `Index built ${S.meta.built}`;
    }
  };
  document.addEventListener('DOMContentLoaded', S.renderChrome);
})();
