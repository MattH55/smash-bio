# Integration steps (owner-applied)

Both branches are deliberately additive and leave shared files untouched, so
these are the only changes needed after merge. Assume `feature/smfret-module`
merges first, then `feature/sc-spt-mp-modules`.

## 1. Consolidate the shared schema definitions — DONE

This was the one item that could be finished before merge, so it is done:

- All 50 `_shared-pending.schema.json#/$defs/...` references in the six
  `website/schema/modules/smash-*.schema.json` files now read
  `../smash-common.schema.json#/$defs/...` (the module schemas live one directory
  below `smash-common.schema.json`).
- `website/schema/modules/_shared-pending.schema.json` is deleted. Its `$defs`
  set was identical to `smash-common`'s; the only difference was that the shared
  `Result` carries the extra `trace_set` property, a superset, so no record
  changed meaning.
- `modules/build_outputs.build_registry` always loads `smash-common` now, and
  `test_modules_schema.py` asserts the repoint (`test_staging_schema_is_gone`,
  `test_module_schemas_reference_the_shared_defs`). `python -m pytest hub -q` is
  green (66 passed).

Nothing else in this file touches the schemas, so the remaining steps below are
unchanged.

## 2. Technique-family switch in the header

`website/js/app.js` renders `#site-nav` for every page. Add a switch; the
default stays force spectroscopy so existing URLs and behaviour are unchanged.

```js
// in app.js, inside the nav renderer, after the existing links:
const FAMILIES = [
  { id: 'force',  label: 'Force spectroscopy', href: 'index.html' },
  { id: 'fret',   label: 'smFRET',             href: 'fret/index.html' },
  { id: 'spt',    label: 'Tracking',           href: 'spt/index.html' },
  { id: 'mp',     label: 'Mass photometry',    href: 'mp/index.html' },
  { id: 'channel',label: 'Single channel',     href: 'channel/index.html' }
];
// render as a <select> or a small link list before the theme toggle
```

Then create the module page directories (copies of the existing pages, with
relative asset paths fixed):

```
website/fret/index.html  explore.html  stats.html  schema.html  submit.html
website/spt/...    website/mp/...    website/channel/...
```

Copy `explore.html`, `stats.html`, `schema.html`, `submit.html`; add
`<base href="../">` or rewrite `css/`, `js/`, `data/` to `../css/` etc. Do not
edit the originals.

## 3. Explore page filters

Add module facets to the copied explore pages, reading
`data/modules/<slug>/index.js` (`SMASH.modules.<slug>`):

- FRET: excitation scheme, immobilization, accurate vs. apparent E, dye pair.
- SPT: probe type, sample context, analysis model.
- MP: instrument, calibration type, assay method.
- Channel: configuration, expression system, idealization method.

## 4. Unified system pages

`website/js/system.js` should render three sections from
`data/modules/crossrefs.jsonl`:

- **Force studies** (existing).
- **FRET studies** where `modules` contains `fret`.
- **Measured by both** when a system appears in both indexes (the payoff of the
  module). Match on the resolved entity (UniProt / Rfam / name), not on DOI.

## 5. Downloads

Module downloads already land in `website/downloads/modules/`:

```
smash-fret-records.jsonl.gz   smash-fret-summary.csv   smash-fret-datasets.csv
smash-spt-records.jsonl.gz    ...                       ...
smash-mp-records.jsonl.gz     ...                       ...
smash-channel-records.jsonl.gz ...                      ...
```

Add one card per module to the copied schema pages, and a small block on the home
page with live counts from `SMASH.modules.<slug>.n`. Leave the hero untouched
(branding is an owner decision).

## 6. Attribution (FRET schema page)

Cite, after verifying each DOI resolves:

- Lerner et al., eLife 2021, `10.7554/eLife.60416`
- Hellenkamp et al., Nat Methods 2018, `10.1038/s41592-018-0085-0`
- Ingargiola et al., Photon-HDF5, Biophys J 2016, `10.1016/j.bpj.2015.11.013`

Note that the ELIXIR FRET-IDP Community Resource (2026-2027) is developing a
dedicated registry and the MIADE-FRET reporting standard for disordered-protein
FRET; state that SMASH-BIO links to it rather than duplicating it.

## 7. Verify

```
python -m pytest hub -q                       # all schema + pipeline tests
python -m modules.run spt --step outputs      # per module, validates before writing
```

Then serve `website/` and check each new page for console errors, broken links
(run a link checker) and the 375 px layout. Re-validate every SMFS record against
v3.1.0: the test `test_force_downloads_are_byte_unchanged` is the guard.