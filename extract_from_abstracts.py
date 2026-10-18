"""
Extract experimental parameters from abstracts already in data.js.
Adds an 'experimental_params' field to every publication entry.
For curated_studies, parameters are already populated separately.
This script covers the 230 regular publications + 20 top_cited.

For full-text extraction (more complete), run:
    python extract_experimental_params.py
(requires network access to Unpaywall + Europe PMC)
"""

import json
import re

# ── Load data.js ─────────────────────────────────────────────────────────────
with open('website/js/data.js', 'r', encoding='utf-8') as f:
    content = f.read()
m = re.search(r'const SMASH_DATA = ({.*});?\s*$', content, re.DOTALL)
data = json.loads(m.group(1))

# ── Regex patterns for abstract-level extraction ─────────────────────────────
RE_FORCE    = re.compile(r'(\d+\.?\d*)\s*(?:–|-|to)\s*(\d+\.?\d*)\s*pN|'
                          r'(\d+\.?\d*)\s*pN\s+(?:force|tension)|'
                          r'(?:force|tension|stall)\s+of\s+(\d+\.?\d*)\s*pN', re.I)
RE_STIFF    = re.compile(r'(\d+\.?\d*)\s*pN/nm', re.I)
RE_BEAD     = re.compile(r'(\d+\.?\d*)\s*[µu]m\s+(?:diameter\s+)?(?:polystyrene|silica|bead)|'
                          r'(\d+\.?\d*)\s*[µu]m\s+(?:streptavidin|anti)', re.I)
RE_DNA_LAM  = re.compile(r'lambda[\s-]?(?:phage\s+)?DNA|λ[\s-]?DNA|48[,\.]?5\s*kbp|48502\s*bp', re.I)
RE_DNA_SIZE = re.compile(r'(\d+\.?\d*)\s*kbp?\s+(?:linear\s+)?(?:dsDNA|ssDNA|DNA)', re.I)
RE_TEMP     = re.compile(r'(\d{2})\s*°?\s*C\b', re.I)
RE_PH       = re.compile(r'pH\s*(\d+\.?\d*)', re.I)
RE_INSTRUM  = re.compile(r'C-Trap|LUMICKS|Q-Trap|custom[\s-]+(?:optical\s+)?tweezers|'
                          r'home[\s-]+built|in[\s-]+house', re.I)
RE_FLUOR    = re.compile(r'(Cy[357]|ATTO\s*\d{3}|Alexa\s+Fluor\s+\d{3}|'
                          r'GFP|mCherry|YOYO|SYTOX|eGFP|JF\d{3}|TMR|SNAP|HALO|QD\d{3})', re.I)
RE_BUFFER   = re.compile(r'(\d+)\s*mM\s+(Tris|HEPES|PBS|PIPES|MOPS)[^\.\n]{0,80}pH\s*(\d+\.?\d*)', re.I)
RE_PROTEIN  = re.compile(r'(\d+\.?\d*)\s*nM\s+[A-Z][a-zA-Z]{1,15}')  # case-SENSITIVE nM
RE_TRAPS    = re.compile(r'(dual|double|single|quadruple|two)\s+(?:optical\s+)?trap', re.I)
RE_WAVE     = re.compile(r'(\d{3,4})\s*nm\s+(?:laser|trapping)|'
                          r'(?:laser|trapping)\s+(?:wavelength\s+)?(\d{3,4})\s*nm', re.I)
RE_BIOTYPE  = re.compile(r'\b(DNA|RNA|protein|nucleosome|chromatin|cell|membrane|'
                          r'microtubule|actin|virus|bacterium|kinesin|myosin)\b', re.I)


def extract_from_text(text):
    """Extract what we can from abstract or any text snippet."""
    if not text:
        return {}
    params = {}

    # Force range
    for mo in RE_FORCE.finditer(text):
        g1,g2,g3,g4 = mo.group(1),mo.group(2),mo.group(3),mo.group(4)
        if g1 and g2:
            params['force_range_pN'] = {'min': float(g1), 'max': float(g2)}
        elif g3 or g4:
            params['force_pN'] = float(g3 or g4)
        break

    # Trap stiffness
    mo = RE_STIFF.search(text)
    if mo:
        params['trap_stiffness_pN_per_nm'] = float(mo.group(1))

    # Bead
    for mo in RE_BEAD.finditer(text):
        v = float(mo.group(1) or mo.group(2))
        if 0.3 <= v <= 10.0:
            params['bead_diameter_um'] = v
            break

    # DNA substrate
    if RE_DNA_LAM.search(text):
        params['dna_substrate'] = 'Lambda DNA (48.5 kbp)'
    else:
        mo = RE_DNA_SIZE.search(text)
        if mo:
            params['dna_substrate'] = f'{mo.group(1)} kbp DNA'

    # Temperature
    temps = [float(mo.group(1)) for mo in RE_TEMP.finditer(text)
             if 4 <= float(mo.group(1)) <= 50]
    if temps:
        params['temperature_C'] = temps[0]

    # pH
    pHs = [float(mo.group(1)) for mo in RE_PH.finditer(text)
           if 4.0 <= float(mo.group(1)) <= 10.0]
    if pHs:
        params['buffer_pH'] = pHs[0]

    # Buffer composition
    mo = RE_BUFFER.search(text)
    if mo:
        params['buffer'] = f'{mo.group(1)} mM {mo.group(2)}'
        params['buffer_pH'] = float(mo.group(3))

    # Instrument
    mo = RE_INSTRUM.search(text)
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
                                  'single':'single-trap','quadruple':'quadruple-trap'}.get(c, c+'-trap')

    # Wavelength
    mo = RE_WAVE.search(text)
    if mo:
        params['laser_wavelength_nm'] = int(mo.group(1) or mo.group(2))

    # Fluorescent labels
    labels = list({mo.group(1) for mo in RE_FLUOR.finditer(text)})
    if labels:
        params['fluorescent_labels'] = labels[:5]

    # Biological system type (inferred from abstract)
    bio_types = list({mo.group(1).lower() for mo in RE_BIOTYPE.finditer(text[:500])})
    if bio_types:
        params['biological_system_keywords'] = bio_types[:5]

    # Protein concentrations
    concs = [mo.group(0) for mo in RE_PROTEIN.finditer(text)]
    if concs:
        params['protein_concentrations_mentioned'] = concs[:4]

    return params


# ── Process all publications and top_cited ────────────────────────────────────
total_extracted = 0
total_with_abstract = 0

# Biology-relevant system types (skip pure physics papers)
BIO_SYSTEM_TYPES = {'DNA', 'protein', 'cell', 'chromatin', 'rna', 'virus',
                    'dna_protein', 'membrane', 'cytoskeleton', 'biophysics'}

for collection_name in ('publications', 'top_cited'):
    for entry in data.get(collection_name, []):
        # Remove citations field
        entry.pop('citations', None)

        abstract = entry.get('abstract', '') or ''
        title    = entry.get('title', '') or ''
        sys_type = (entry.get('system_type') or '').lower()
        exp_type = (entry.get('experiment_type') or '').lower()

        if abstract:
            total_with_abstract += 1

        # Skip pure physics/instrumentation papers (no biological experiment)
        is_bio = (sys_type in BIO_SYSTEM_TYPES or
                  any(k in sys_type for k in ('dna','protein','cell','bio')) or
                  any(k in exp_type for k in ('dna','protein','cell','bio','fold','unfold')))

        if not is_bio:
            # Leave params blank for physics papers
            entry['experimental_params'] = None
            continue

        # No abstract available
        if not abstract:
            entry['experimental_params'] = {'note': 'No abstract available; full-text extraction required.'}
            continue

        # Combine title + abstract for extraction
        combined_text = title + ' ' + abstract
        params = extract_from_text(combined_text)

        # Only add if we got something meaningful (not just keywords)
        meaningful = {k: v for k, v in params.items()
                      if k != 'biological_system_keywords' and v}
        if meaningful:
            entry['experimental_params'] = params
            total_extracted += 1
        else:
            # Has abstract but nothing extractable
            entry['experimental_params'] = {
                'biological_system_keywords': params.get('biological_system_keywords', []),
                'note': 'Abstract available; detailed parameters require full-text extraction.'
            }

print(f"Publications processed: {len(data.get('publications', []))}")
print(f"Top-cited processed:    {len(data.get('top_cited', []))}")
print(f"With abstracts:         {total_with_abstract}")
print(f"Had extractable params: {total_extracted}")

# ── Write back ────────────────────────────────────────────────────────────────
json_output = json.dumps(data, indent=2, ensure_ascii=False)
total = data['statistics']['total_publications']
new_content = (
    "// SMASH-BIO Complete Data\n"
    "// Biophysics-focused publications from extracted_metadata and publications_metadata\n"
    "// Total: " + str(total) + " entries\n"
    "// Citation counts removed. Experimental parameters extracted from abstracts.\n"
    "// For full-text parameter extraction, run: python extract_experimental_params.py\n\n"
    "const SMASH_DATA = " + json_output + ";\n"
)

with open('website/js/data.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("\ndata.js updated successfully.")
print("Run python extract_experimental_params.py (with network) for full-text extraction.")
