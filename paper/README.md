# Numbers and figures of the SMASH-BIO article

Scripts that compute every number in Halma (2026), *Open Research Europe*, and draw its figures from the
SMASH-BIO release described there (schema v3.1.0, built 10 October 2026).

## Contents

| Path | What it is |
|---|---|
| `data/` | The release files the article was computed from, copied unmodified from the site build; `data/MANIFEST.txt` lists their SHA-256 checksums. The CSV files keep the Windows line endings they were checksummed with (`.gitattributes`); otherwise they are identical to `website/downloads/`. `data/hub_logs/` holds the harvest and classification logs used only for the pre-scope funnel counts. |
| `out/corpus_stats.json` | The numbers used in the article, as produced by `scripts/corpus_stats.py`. |
| `scripts/corpus_stats.py` | Computes `out/corpus_stats.json` from `data/`. `--check` compares the overlapping totals with the site's own statistics (`data/site_stats.js`). |
| `scripts/make_supplementary.py` | Builds Tables S1–S2 of Supplementary File 1 from the schema files in `website/`. |
| `scripts/figstyle.py` | Shared figure style. |
| `scripts/fig2_pipeline.py` | Figure 2, the pipeline. |
| `scripts/ore_fig3_schema.py` | Figure 3, the structure of one record (redraw of the submitted figure). |
| `scripts/fig4_screens.py` | Figure 4, screenshots of the site build (needs Playwright). |
| `scripts/ore_fig5_corpus.py` | Figure 5, the corpus at release (redraw of the submitted figure). |
| `scripts/fig3_field.py` | Figure 6, what the hub shows about the field. |
| `scripts/ore_fig1_patch.py` | Copyedit corrections to Figure 1, which is artwork without a script. It edits the submitted image, which is not in this repository. |

## Reproduce

```
pip install matplotlib pillow
python -I paper/scripts/corpus_stats.py --check > paper/out/corpus_stats.json   # identical to the committed file
python paper/scripts/fig2_pipeline.py          # -> paper/figures/
python paper/scripts/fig3_field.py             # -> paper/figures/
python paper/scripts/ore_fig3_schema.py        # -> paper/figures_ore_revised/
python paper/scripts/ore_fig5_corpus.py        # -> paper/figures_ore_revised/
python paper/scripts/make_supplementary.py     # -> paper/out/supplementary.md
```

The figure numbers above follow the published article. Some script names still carry the numbering of an earlier draft.
