# Simulations category — integration steps (owner)

All of these are **ready-to-apply steps for after the technique-module branches
merge**. Nothing here has been applied, and nothing in the shared site files has
been edited.

## 1. Navigation and footers

`website/sim/*.html` render their own chrome (`website/sim/js/sim.js`) because the
shared `website/js/app.js` builds navigation with links relative to the site
root, which would break under `/sim/`. To fold Simulations into the shared chrome
instead:

1. In `website/js/app.js`, extend `NAV` with `['sim/index.html', 'Simulations']`
   and make `renderChrome` prefix links with `../` when the page is one level
   deep (or switch to root-absolute links).
2. Delete the `chrome()` function from `website/sim/js/sim.js` and its call in
   each page (keep `banner()`, `bars()`, `compactCard()`).
3. Keep the visible **Simulation** tag on every simulation card: the brief
   requires the label everywhere simulations appear.

## 2. The "Simulation vs experiment" panel on system pages

`website/sim/system.html?system=<name>` already renders the two-sided view
(simulation results on the left, matched experimental values on the right). To
put the same panel on the **experimental** system pages:

1. Copy `renderSystemPanel()` logic from `website/sim/js/system.js` into
   `website/js/system.js` as an additive block that runs only when
   `SMASH.simSystems` contains the current system.
2. Load the simulation data files only on system pages:
   ```html
   <script src="sim/data/index.js"></script>
   <script src="sim/data/matches.js"></script>
   <script src="sim/data/systems.js"></script>
   ```
3. Rules the panel must keep: reduced-unit values never share a physical axis; a
   `homolog` link is labelled as name-based only; experiments are never merged
   into the simulation row set.

## 3. Schema references

`website/schema/sim/smash-sim-record.schema.json` references the published SMFS
3.1.0 `$defs` (`../smash-smfs-record.schema.json`, `../smash-smfs-results.schema.json`).
Once `smash-common.schema.json` is the agreed shared home, repoint these refs:

| current ref | new ref |
|---|---|
| `../smash-smfs-record.schema.json#/$defs/Quantity` | `../smash-common.schema.json#/$defs/Quantity` |
| `../smash-smfs-record.schema.json#/$defs/Identifier` | `../smash-common.schema.json#/$defs/Identifier` |
| `../smash-smfs-record.schema.json#/$defs/Evidence` | `../smash-common.schema.json#/$defs/Evidence` |
| `../smash-smfs-record.schema.json#/$defs/DatasetLink` | `../smash-common.schema.json#/$defs/DatasetLink` |
| `../smash-smfs-record.schema.json#/$defs/DataAvailability/properties/status` | `../smash-common.schema.json#/$defs/DataAvailability/properties/status` |
| `../smash-smfs-record.schema.json#/$defs/Technique/properties/force_application_geometry` | keep: the geometry enum is the experimental vocabulary and must stay shared |

`sim/schema.py` loads the schemas it needs; add `smash-common.schema.json` to
its `schema_files()` list if you repoint (it is already registered when present).

## 4. Downloads, sitemap and submission form

1. Add the three downloads to the schema page's download section:
   `website/downloads/sim/smash-sim-records.jsonl.gz`,
   `smash-sim-summary.csv`, `smash-sim-matches.csv`.
2. Add `/sim/` URLs to `website/sitemap-pages.xml` (the sim pages are static).
3. Wire `website/sim/submit.html` into `website/submit.html` so a simulation
   record can be posted through the existing form; validate server-side with
   `python -c "from sim import schema; schema.validator().validate(record)"`.

## 5. Publishing the corpus

```bash
cd hub
python -m sim.run --step all             # harvest -> classify -> fulltext -> datasets -> records -> match -> outputs -> audit
python -m sim.identifiers               # optional: warm the category identifier table
python -m sim.verify                    # Phase 6 checks -> docs/sim/verification.md
python -m pytest -q                     # expect 107 passed
```

`python -m sim.run --step all --out-dir out/sim-smoke` keeps a scratch run out of
`website/`.

## 6. Follow-ups that need the owner

- **BSDB** is 404 at both published hosts; the Internet Archive copy from
  2025-03-14 is recorded in `hub/data/sim/datasets/bsdb.json`. Ask the Cieplak
  group whether they will host a copy, and whether the reduced-unit peak forces
  may be redistributed.
- **ForceGen / Buehler lab**: the repository is MIT-licensed, so code may be
  redistributed; confirm that the per-protein force–extension records may be too
  before ingesting them.
- **Mykuliak et al. 2020** (Fairdata, CC BY 4.0) is redistributable; only the
  metadata is indexed so far.