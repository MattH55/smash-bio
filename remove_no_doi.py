"""
1. Populate missing DOIs from publications_metadata YAML files
2. Remove entries where journal='Various' (presentations/webinars without peer review)
3. Remove entries that still have no DOI after YAML lookup
"""
import json, re, glob, yaml, os, sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

with open('website/js/data.js', 'r', encoding='utf-8') as f:
    content = f.read()
m = re.search(r'const SMASH_DATA = ({.*});?\s*$', content, re.DOTALL)
data = json.loads(m.group(1))

# ── Build DOI lookup from YAML files ─────────────────────────────────────────
# key = experiment_id (e.g. FANCD2-2024-001), value = doi string
yaml_doi_map = {}
for yf in glob.glob('publications_metadata/*.yaml'):
    try:
        y = yaml.safe_load(open(yf, encoding='utf-8'))
        if not isinstance(y, dict):
            continue
        # Try various DOI locations
        doi = (y.get('doi') or
               (y.get('citation') or {}).get('doi') or
               (y.get('publication') or {}).get('doi') or '')
        doi = str(doi).strip() if doi else ''
        if not doi:
            continue
        # Map by experiment_id (primary) or study_id / id
        eid = (y.get('experiment_id') or
               y.get('study_id') or
               y.get('id') or '')
        if eid:
            yaml_doi_map[str(eid).strip()] = doi
    except Exception:
        pass

print(f"Loaded {len(yaml_doi_map)} DOIs from YAML files")
for k, v in sorted(yaml_doi_map.items()):
    print(f"  {k}: {v}")

print()
removed_list = []
doi_populated = 0

for coll in ('publications', 'top_cited', 'curated_studies'):
    before = data.get(coll, [])
    kept = []
    for p in before:
        journal = (p.get('journal') or '').strip()
        doi     = (p.get('doi') or '').strip()
        pid     = (p.get('id') or '').strip()

        # Try to populate missing DOI from YAML lookup
        if not doi and pid in yaml_doi_map:
            doi = yaml_doi_map[pid]
            p['doi'] = doi
            doi_populated += 1
            print(f"  [POPULATED] {pid}: {doi}")

        journal_lower = journal.lower()

        # Remove if journal is 'Various' (webinar/presentation)
        if journal_lower == 'various':
            removed_list.append(f"  VARIOUS  [{coll}] {pid} | {journal}")
            continue

        # Remove if still no DOI after lookup
        if not doi or doi.lower() in ('n/a', 'none', 'tbd', ''):
            removed_list.append(f"  NO DOI   [{coll}] {pid} | {journal}")
            continue

        kept.append(p)

    data[coll] = kept
    print(f"{coll}: {len(before)} -> {len(kept)} (removed {len(before)-len(kept)})")

print()
print("Removed entries:")
for r in removed_list:
    print(r)

# Update statistics
all_pubs  = len(data.get('publications',[])) + len(data.get('top_cited',[]))
cur_count = len(data.get('curated_studies',[]))
data['statistics']['total_publications'] = all_pubs + cur_count
print(f"\nNew total: {data['statistics']['total_publications']} ({all_pubs} regular + {cur_count} curated)")
print(f"DOIs populated from YAML: {doi_populated}")
print(f"Entries removed: {len(removed_list)}")

# Write back
json_output = json.dumps(data, indent=2, ensure_ascii=False)
total = data['statistics']['total_publications']
new_content = (
    "// SMASH-BIO Complete Data\n"
    "// Biophysics-focused publications from extracted_metadata and publications_metadata\n"
    "// Total: " + str(total) + " entries (all have valid DOIs)\n"
    "// Entries without DOI or journal='Various' removed.\n\n"
    "const SMASH_DATA = " + json_output + ";\n"
)

with open('website/js/data.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("\ndata.js updated successfully.")
