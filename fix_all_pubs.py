"""
Final cleanup for all 266 publications in data.js:
1. Remove all citation counts
2. Add experimental_params to every entry based on what we have
3. For biology papers with abstracts: extract what we can
4. For physics/instrumentation papers: set null (not applicable)
5. For bio papers without abstract: note full-text needed
"""

import json, re
from collections import Counter

with open('website/js/data.js', 'r', encoding='utf-8') as f:
    content = f.read()
m = re.search(r'const SMASH_DATA = ({.*});?\s*$', content, re.DOTALL)
data = json.loads(m.group(1))

# Debug: system_type distribution
pubs = data.get('publications', []) + data.get('top_cited', [])
st_dist = Counter((p.get('system_type','?'), bool(p.get('abstract'))) for p in pubs)
print("system_type distribution (type, has_abstract): count")
for k,v in sorted(st_dist.items(), key=lambda x:-x[1]):
    print(f"  {v:3d}  {k}")

print(f"\nTotal pubs+top_cited: {len(pubs)}")
print(f"With abstracts: {sum(1 for p in pubs if p.get('abstract'))}")
print()

# Patterns
RE_FORCE  = re.compile(r'(\d+\.?\d*)\s*(?:–|-|to)\s*(\d+\.?\d*)\s*pN|'
                        r'(\d+\.?\d*)\s*pN\s+(?:force|tension)|'
                        r'(?:force|tension|stall)\s+of\s+(\d+\.?\d*)\s*pN', re.I)
RE_STIFF  = re.compile(r'(\d+\.?\d*)\s*pN/nm', re.I)
RE_DNA_L  = re.compile(r'lambda\s*(?:phage\s+)?DNA|λ[\s-]?DNA|48[,\.]?5\s*kbp|48502\s*bp', re.I)
RE_DNA_S  = re.compile(r'(\d+\.?\d*)\s*kbp?\s+(?:linear\s+)?(?:dsDNA|ssDNA|DNA)', re.I)
RE_PH     = re.compile(r'\bpH\s*(\d+\.?\d*)', re.I)
RE_TEMP   = re.compile(r'(\d{2})\s*°?\s*C\b(?!\w)')
RE_INSTR  = re.compile(r'C-Trap|LUMICKS|Q-Trap|custom[\s-]+(?:optical\s+)?tweezers|'
                        r'home[\s-]+built|in[\s-]+house', re.I)
RE_FLUOR  = re.compile(r'\b(Cy[357]|ATTO\s*\d{3}|Alexa\s+Fluor\s+\d{3}|'
                        r'GFP|mCherry|YOYO|SYTOX|eGFP|JF\d{3}|TMR|SNAP|HALO)\b', re.I)
RE_BEAD   = re.compile(r'(\d+\.?\d*)\s*[µu]m\s+(?:diameter\s+)?(?:polystyrene|silica|bead)|'
                        r'(\d+\.?\d*)\s*[µu]m\s+(?:streptavidin|anti[\s-]?dig)', re.I)
RE_TRAPS  = re.compile(r'(dual|double|single|quadruple|two)\s+(?:optical\s+)?trap', re.I)
RE_WAVE   = re.compile(r'(\d{3,4})\s*nm\s+(?:laser|trapping)|'
                        r'(?:laser|trapping)\s+(?:wavelength\s+)?(\d{3,4})\s*nm', re.I)
RE_BIOTYP = re.compile(r'\b(DNA|RNA|protein|nucleosome|chromatin|cell|membrane|'
                        r'microtubule|actin|virus|bacterium|kinesin|myosin)\b', re.I)
RE_CONC   = re.compile(r'(\d+\.?\d*)\s*nM\s+[A-Z][a-zA-Z]{2,15}')  # case-sensitive nM

# Bio system types (accepting lowercase after .lower())
BIO_TYPES = {'dna', 'protein', 'cell', 'chromatin', 'rna', 'virus',
             'dna_protein', 'membrane', 'cytoskeleton', 'biophysics',
             'dna-protein', 'nucleic acid', 'nucleosome'}


def extract(text):
    if not text:
        return {}
    params = {}

    # Force
    for mo in RE_FORCE.finditer(text):
        g1,g2,g3,g4 = mo.group(1),mo.group(2),mo.group(3),mo.group(4)
        if g1 and g2:
            params['force_range_pN'] = {'min': float(g1), 'max': float(g2)}
        elif g3 or g4:
            params['force_pN'] = float(g3 or g4)
        break

    # Stiffness
    mo = RE_STIFF.search(text)
    if mo:
        params['trap_stiffness_pN_per_nm'] = float(mo.group(1))

    # Bead
    for mo in RE_BEAD.finditer(text):
        v = float(mo.group(1) or mo.group(2) or '0')
        if 0.3 <= v <= 10.0:
            params['bead_diameter_um'] = v
            break

    # DNA substrate
    if RE_DNA_L.search(text):
        params['dna_substrate'] = 'Lambda DNA (48.5 kbp)'
    else:
        mo = RE_DNS = RE_DNA_S.search(text)
        if mo:
            params['dna_substrate'] = f'{mo.group(1)} kbp DNA'

    # Temperature
    temps = [float(mo.group(1)) for mo in RE_TEMP.finditer(text)
             if 4 <= float(mo.group(1)) <= 50]
    if temps:
        params['temperature_C'] = temps[0]

    # pH
    phs = [float(mo.group(1)) for mo in RE_PH.finditer(text)
           if 4.0 <= float(mo.group(1)) <= 10.0]
    if phs:
        params['buffer_pH'] = phs[0]

    # Instrument
    mo = RE_INSTR.search(text)
    if mo:
        raw = mo.group(0).upper()
        if 'C-TRAP' in raw or 'C TRAP' in raw:
            params['instrument'] = 'LUMICKS C-Trap'
        elif 'Q-TRAP' in raw:
            params['instrument'] = 'LUMICKS Q-Trap'
        elif 'LUMICKS' in raw:
            params['instrument'] = 'LUMICKS'
        else:
            params['instrument'] = 'Custom-built'

    # Trap config
    mo = RE_TRAPS.search(text)
    if mo:
        c = mo.group(1).lower()
        params['trap_config'] = {'dual':'dual-trap','double':'dual-trap','two':'dual-trap',
                                  'single':'single-trap','quadruple':'quadruple-trap'}.get(c,c+'-trap')

    # Wavelength
    mo = RE_WAVE.search(text)
    if mo:
        params['laser_wavelength_nm'] = int(mo.group(1) or mo.group(2))

    # Fluorescent dyes
    labels = list({mo.group(1) for mo in RE_FLUOR.finditer(text)})
    if labels:
        params['fluorescent_labels'] = labels[:5]

    # Bio type keywords (from title/abstract)
    bio_types = list({mo.group(1).lower() for mo in RE_BIOTYP.finditer(text[:500])})
    if bio_types:
        params['biological_system_keywords'] = bio_types[:5]

    # Protein concentrations (case-sensitive nM)
    concs = [mo.group(0) for mo in RE_CONC.finditer(text)]
    if concs:
        params['protein_concentrations_mentioned'] = concs[:4]

    return params


# Process
bio_count   = 0
phys_count  = 0
extracted   = 0

for collection in ('publications', 'top_cited'):
    for entry in data.get(collection, []):
        entry.pop('citations', None)

        abstract = entry.get('abstract', '') or ''
        title    = entry.get('title', '') or ''
        sys_type = (entry.get('system_type') or '').strip().lower()
        exp_type = (entry.get('experiment_type') or '').strip().lower()

        # Determine if this is a biological experiment
        # Accept papers where system_type or exp_type suggests biology
        is_bio = (sys_type in BIO_TYPES or
                  any(k in sys_type for k in ('dna','protein','cell','bio','chrom','nucl','mem','cyto')) or
                  any(k in exp_type for k in ('dna','protein','cell','bio','fold','unfold','chrom','nucl')))

        if not is_bio:
            # Pure physics/instrumentation paper - not applicable
            phys_count += 1
            entry['experimental_params'] = None  # no biological params expected
            continue

        bio_count += 1
        text = (title + ' ' + abstract).strip()

        if not abstract:
            # Bio paper but no abstract
            entry['experimental_params'] = {
                'note': 'No abstract available. Full-text extraction required (run extract_experimental_params.py).'
            }
            continue

        # Extract from title + abstract
        params = extract(text)

        # Check if we got anything useful beyond just keywords
        useful_keys = {k for k in params if k not in ('biological_system_keywords',)}
        if useful_keys:
            entry['experimental_params'] = params
            extracted += 1
        else:
            entry['experimental_params'] = {
                'biological_system_keywords': params.get('biological_system_keywords', []),
                'note': 'Abstract available but parameters not reported in abstract. Full-text extraction required.'
            }

print(f"Biology papers:   {bio_count}")
print(f"Physics papers:   {phys_count} (experimental_params=null)")
print(f"With extracted:   {extracted}")

# Show a few extracted examples
print("\n--- Sample extracted params ---")
n=0
for collection in ('publications', 'top_cited'):
    for entry in data.get(collection, []):
        ep = entry.get('experimental_params')
        if ep and 'note' not in ep and ep is not None:
            if len(ep) > 1:
                print(entry.get('title','')[:60])
                for k,v in ep.items():
                    print(f"  {k}: {v}")
                print()
                n+=1
                if n>=5: break
    if n>=5: break

# Write back
json_output = json.dumps(data, indent=2, ensure_ascii=False)
total = data['statistics']['total_publications']
new_content = (
    "// SMASH-BIO Complete Data\n"
    "// Biophysics-focused publications from extracted_metadata and publications_metadata\n"
    "// Total: " + str(total) + " entries\n"
    "// Citation counts removed. Experimental parameters: curated (36), abstract-extracted (varies).\n"
    "// For full-text extraction of remaining papers: python extract_experimental_params.py\n\n"
    "const SMASH_DATA = " + json_output + ";\n"
)

with open('website/js/data.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("\ndata.js written successfully.")
