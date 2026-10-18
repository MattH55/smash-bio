# Integrating SMASH-Pull into smash-bio.org

SMASH-Pull lives entirely in `website/pull/` and touches nothing else. The steps below wire it into
the rest of the site.

**Status 2026-10-14:** at the owner's request §1(b) (nav entry), §2 (system-page link, AlphaFold-backed systems only) and §3 (sitemap) were applied and deployed. §1(a) (shared chrome) and §4 (analytics) were not.

## 1. Navigation entry and shared chrome (`website/js/app.js`)

`app.js` only rewrites links for pages inside `/sim/`. Two edits make it serve `/pull/` as well:

```js
// (a) S.renderChrome: compute the prefix for any one-level sub-folder, not only /sim/
-    const prefix = inSim ? '../' : '';
+    const inPull = /\/pull\//i.test(path);
+    const prefix = (inSim || inPull) ? '../' : '';

// (b) NAV: add the simulator after "Simulations"
     ['datasets.html', 'Datasets'], ['stats.html', 'Insights'], ['sim/index.html', 'Simulations <span class="nav-beta">beta</span>'],
+    ['pull/index.html', 'Pull <span class="nav-beta">beta</span>'],
     ['schema.html', 'Schema'], ['submit.html', 'Submit'], ['about.html', 'About']
```

Mark it active on pull pages with `const active = inSim ? href === 'sim/index.html' : inPull ? href ===
'pull/index.html' : file === href;`. The nav already holds nine items; the existing mobile breakpoint
(1280 px) collapses it to the menu button, so no CSS change is needed.

Optionally add a footer column entry in the same file: `<li><a href="${prefix}pull/index.html">Pulling simulator</a></li>`
under "Simulations".

**After (1)**, the pull pages can use the shared chrome. In `index.html`, `about.html` and
`benchmarks.html`, replace `<script src="js/chrome.js"></script>` with
`<script src="../js/app.js"></script>`, then delete `js/chrome.js`. The pull section bar
(Simulator · Benchmarks · Model & limits) is drawn by chrome.js; keep chrome.js if you want it.

## 2. "Simulate this" links on system pages (`website/js/system.js`)

System records carry `s.uniprot.acc`, `s.uniprot.alphafold` and `s.uniprot.n_pdb`. Add one fact row.
Line numbers are those of 2026-10-14; insert after the "Predicted structure" row, around line 36:

```js
  if (u.acc && (u.alphafold || u.n_pdb)) facts.push(['Simulate', `<a class="btn btn-secondary btn-sm" href="pull/index.html#m=protein&src=af:${encodeURIComponent(u.acc)}">Pull this protein in the browser</a> <span class="muted small">(AlphaFold model; beta)</span>`]);
```

For nucleic-acid systems with a known hairpin sequence, link `pull/index.html#m=nucleic&seq=<sequence>`.
The simulator detects the stem and loop itself, and refuses sequences that are not perfect stems.

The URL hash scheme the simulator reads:

| Key | Meaning | Example |
|---|---|---|
| `m` | `protein` or `nucleic` | `m=protein` |
| `src` | `pdb:<ID>` or `af:<UniProt>` | `src=pdb:1TIT`, `src=af:P0CG48` |
| `chain`, `range` | chain and residue window | `chain=A&range=1-120` |
| `a`, `p` | fixed and pulled residue numbers | `a=48&p=76` |
| `inst`, `proto` | `afm`/`ot`/`mt`, `quick`/`standard`/`custom` | `inst=afm&proto=standard` |
| `seq`, `c`, `t`, `na`, `mg` | nucleic sequence, construct (`auto`/`stem`/`unzip`), °C, mM, mM | `seq=GAG…&t=25` |

Experimental records could link the same way from `record.html` when a PDB ID is known:
`pull/index.html#m=protein&src=pdb:<ID>`.

## 3. Sitemap (`hub/s07_build_site.py`)

Add the three pages to `MAIN_PAGES` (line 99):

```python
              ("pull/index.html", "0.6", "monthly"), ("pull/benchmarks.html", "0.4", "monthly"),
              ("pull/about.html", "0.4", "monthly"),
```

and, if `sitemap.html` lists sections, a "Pulling simulator" group with the same three links.

## 4. Analytics

The pull pages carry **no Google tag**. The brief allows only smash-bio.org assets and structure
servers as network requests. If the site owner wants analytics here anyway, paste the same `gtag.js`
snippet the other pages use into the three pages' `<head>`, and update the privacy paragraph in
`about.html#privacy`. That is the owner's decision.

## 5. Hosting

- Upload `website/pull/` as-is (≈ 0.4 MB including `wasm/pull_engine.wasm` and `data/`).
- The worker instantiates WebAssembly from an `ArrayBuffer`, so the server does **not** need to send
  `application/wasm` (it still may).
- No CORS, COOP/COEP or special headers are needed: SharedArrayBuffer is not used.
- The existing FTP deploy (`hub/deploy_ftp.py`) uploads everything under `website/`, so it would include
  `pull/`. **Not deployed**, per the brief: the site owner decides when.

## 6. Rebuilding after an engine change

```
cd pull-engine && cargo test --release
cargo build --release --lib --target wasm32-unknown-unknown
copy target\wasm32-unknown-unknown\release\pull_engine.wasm ..\website\pull\wasm\
cd ..\tests\pull && node gate5.mjs          # native = Chrome bytes
node benchmarks.mjs && node build_validation.mjs   # refresh data/*.json
```
