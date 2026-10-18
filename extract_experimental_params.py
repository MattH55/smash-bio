"""
Automated extraction of experimental parameters from optical tweezers publications.
- Uses Unpaywall API to find open-access full text URLs
- Falls back to PMC, Europe PMC, biorxiv
- Extracts key parameters using regex patterns
- Updates doi_metadata YAML files
- Re-generates website data by appending experimental_params to publications

Usage:
    python extract_experimental_params.py              # process all
    python extract_experimental_params.py --limit 20   # test on first 20
    python extract_experimental_params.py --doi 10.1038/xxx  # single paper
"""

import os
import re
import sys
import time
import glob
import json
import argparse
import requests
import yaml
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────
UNPAYWALL_EMAIL = "smash-bio@example.com"   # Unpaywall requires email
SLEEP_BETWEEN = 1.5                          # seconds between requests
MAX_TEXT_CHARS = 50000                       # truncate full text for parsing
CACHE_FILE     = "param_extraction_cache.yaml"
OUTPUT_FILE    = "extracted_params.json"    # summary of what was extracted

# ─── Regex Patterns ──────────────────────────────────────────────────────────
RE_BEAD_SIZE   = re.compile(
    r'(\d+\.?\d*)\s*[–-]?\s*(?:\d+\.?\d*)?\s*[µu]m[,\s].*?bead|'
    r'bead[s]?\s+[^\.\n]{0,60}?(\d+\.?\d*)\s*[µu]m|'
    r'(\d+\.?\d*)\s*[µu]m\s+(?:diameter\s+)?(?:polystyrene|silica|streptavidin)',
    re.IGNORECASE
)
RE_BEAD_SURF   = re.compile(
    r'(streptavidin|anti[\s-]?digoxigenin|carboxyl|amine|protein\s*A|NHS|biotin|NeutrAvidin)[\s\-]+coated',
    re.IGNORECASE
)
RE_INSTRUMENT  = re.compile(
    r'(C-Trap|C\s+Trap|LUMICKS|Q-Trap|custom[\s-]+built|home[\s-]+built|in[\s-]+house)',
    re.IGNORECASE
)
RE_STIFFNESS   = re.compile(
    r'(?:trap\s+stiffness|spring\s+constant|stiffness)[^\.\n]{0,60}?(\d+\.?\d*)\s*pN/nm',
    re.IGNORECASE
)
RE_TEMP        = re.compile(
    r'(?:at|temperature)[^\.\n]{0,30}?(\d{2,3})\s*°?\s*[CK](?!\w)|'
    r'(\d{2,3})\s*°?\s*C\s+(?:throughout|during|in\s+all)',
    re.IGNORECASE
)
RE_FORCE       = re.compile(
    r'(\d+\.?\d*)\s*(?:to|–|-)\s*(\d+\.?\d*)\s*pN|'
    r'(?:force|tension)\s+of\s+(\d+\.?\d*)\s*pN|'
    r'(\d+\.?\d*)\s*pN\s+(?:force|tension)',
    re.IGNORECASE
)
RE_BUFFER      = re.compile(
    r'(\d+)\s*mM\s+(Tris|HEPES|PBS|PIPES|MOPS|phosphate|acetate|imidazole)[^\.]{0,100}?pH\s*(\d+\.?\d*)|'
    r'(?:buffer|solution)\s+containing[^\.]{0,150}?pH\s*(\d+\.?\d*)|'
    r'pH\s*(\d+\.?\d*)',
    re.IGNORECASE
)
RE_DNA         = re.compile(
    r'lambda[\s-]?(?:phage\s+)?DNA|λ[\s-]?DNA|(\d+\.?\d*)\s*kb(?:p)?\s+(?:linear\s+)?(?:dsDNA|DNA)|'
    r'(\d+)\s*(?:base\s+pair|bp)\s+DNA|bacteriophage\s+lambda|48[,.]?(?:502|500|5)\s*bp',
    re.IGNORECASE
)
RE_PROTEIN_CONC = re.compile(
    r'(\d+\.?\d*)\s*nM\s+[A-Z][a-z]{1,15}|'
    r'[A-Z][a-z]{1,15}\s+at\s+(\d+\.?\d*)\s*nM',
)
RE_TRAPS       = re.compile(
    r'(dual|double|single|quadruple|two|three|four)[\s-]+(?:optical\s+)?trap',
    re.IGNORECASE
)
RE_WAVELENGTH  = re.compile(
    r'(\d{3,4})\s*nm\s+(?:laser|trapping|wavelength)|'
    r'(?:laser|trapping)\s+(?:wavelength\s+of\s+)?(\d{3,4})\s*nm',
    re.IGNORECASE
)
RE_FLUOR_DYE   = re.compile(
    r'(Cy3|Cy5|Cy7|ATTO\s*\d{3}|Alexa\s+Fluor\s+\d{3}|GFP|mCherry|YOYO|SYTOX|eGFP|mEGFP|'
    r'JF\d{3}|TMR|SNAP|HALO|CLIP|QD\d{3}|quantum\s+dot)',
    re.IGNORECASE
)


# ─── Fetch helpers ────────────────────────────────────────────────────────────
def clean_doi(doi_raw):
    """Normalize DOI - strip https://doi.org/ prefix if present."""
    if doi_raw:
        doi_raw = doi_raw.strip()
        if doi_raw.startswith('http'):
            doi_raw = re.sub(r'^https?://doi\.org/', '', doi_raw)
    return doi_raw


def get_oa_url(doi):
    """Try Unpaywall API to get open-access full-text URL."""
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email={UNPAYWALL_EMAIL}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('is_oa'):
                # Prefer PDF, then HTML best-OA location
                best = data.get('best_oa_location', {})
                if best:
                    return best.get('url_for_pdf') or best.get('url_for_landing_page')
    except Exception:
        pass
    return None


def fetch_from_pmc(doi):
    """Try Europe PMC or PubMed Central for full text."""
    try:
        # Try Europe PMC search
        r = requests.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={"query": f"DOI:{doi}", "format": "json", "resultType": "core"},
            timeout=10
        )
        if r.status_code == 200:
            hits = r.json().get("resultList", {}).get("result", [])
            if hits:
                pmcid = hits[0].get("pmcid")
                if pmcid:
                    # Fetch full text XML from Europe PMC
                    ft = requests.get(
                        f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML",
                        timeout=15
                    )
                    if ft.status_code == 200:
                        return ft.text
    except Exception:
        pass
    return None


def fetch_biorxiv(doi):
    """Try biorxiv API."""
    try:
        r = requests.get(
            f"https://api.biorxiv.org/details/biorxiv/{doi}/na/json",
            timeout=10
        )
        if r.status_code == 200:
            results = r.json().get("collection", [])
            if results:
                preprint_doi = results[-1].get("doi", doi)
                # Fetch preprint HTML from biorxiv
                html = requests.get(
                    f"https://www.biorxiv.org/content/{preprint_doi}v1",
                    timeout=15
                )
                if html.status_code == 200:
                    return html.text
    except Exception:
        pass
    return None


def fetch_text(doi, oa_url=None):
    """Attempt to fetch paper text from multiple sources."""
    text = None

    # 1. Try Europe PMC full text XML
    text = fetch_from_pmc(doi)
    if text and len(text) > 500:
        return text[:MAX_TEXT_CHARS]

    # 2. Try open access URL from Unpaywall
    if oa_url:
        try:
            r = requests.get(oa_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and len(r.text) > 500:
                return r.text[:MAX_TEXT_CHARS]
        except Exception:
            pass

    # 3. Try biorxiv
    text = fetch_biorxiv(doi)
    if text and len(text) > 500:
        return text[:MAX_TEXT_CHARS]

    return None


# ─── Parameter Extraction ─────────────────────────────────────────────────────
def extract_params(text):
    """Extract experimental parameters from full paper text using regex."""
    params = {
        "instrument": None,
        "trap_config": None,
        "laser_wavelength_nm": None,
        "bead_diameter_um": None,
        "bead_surface_chemistry": None,
        "trap_stiffness_pN_per_nm": None,
        "temperature_C": None,
        "force_range_pN": None,
        "buffer_pH": None,
        "buffer_composition": None,
        "dna_substrate": None,
        "fluorescent_labels": [],
        "extraction_confidence": "low"
    }

    if not text:
        return params

    # Clean XML tags if present
    text_clean = re.sub(r'<[^>]+>', ' ', text)
    text_clean = re.sub(r'\s+', ' ', text_clean)

    # Instrument
    m = RE_INSTRUMENT.search(text_clean)
    if m:
        raw = m.group(1).upper()
        if 'C-TRAP' in raw or 'C TRAP' in raw:
            params["instrument"] = "LUMICKS C-Trap"
        elif 'Q-TRAP' in raw:
            params["instrument"] = "LUMICKS Q-Trap"
        elif 'LUMICKS' in raw:
            params["instrument"] = "LUMICKS (model unknown)"
        elif 'CUSTOM' in raw or 'HOME' in raw or 'IN-HOUSE' in raw or 'IN HOUSE' in raw:
            params["instrument"] = "Custom-built"
        params["extraction_confidence"] = "medium"

    # Trap configuration
    m = RE_TRAPS.search(text_clean)
    if m:
        raw = m.group(1).lower()
        config_map = {"dual": "dual-trap", "double": "dual-trap", "two": "dual-trap",
                      "single": "single-trap", "quadruple": "quadruple-trap",
                      "three": "triple-trap", "four": "quadruple-trap"}
        params["trap_config"] = config_map.get(raw, raw + "-trap")

    # Laser wavelength
    m = RE_WAVELENGTH.search(text_clean)
    if m:
        wl = m.group(1) or m.group(2)
        if wl:
            params["laser_wavelength_nm"] = int(wl)

    # Bead size - find the most specific match
    best_bead = None
    for m in RE_BEAD_SIZE.finditer(text_clean):
        val = m.group(1) or m.group(2) or m.group(3)
        if val:
            v = float(val)
            # Beads are typically 0.5 - 10 µm
            if 0.3 <= v <= 10.0:
                best_bead = v
                break
    params["bead_diameter_um"] = best_bead

    # Bead surface chemistry
    m = RE_BEAD_SURF.search(text_clean)
    if m:
        params["bead_surface_chemistry"] = m.group(1).lower().replace('–', '-').replace('–', '-')

    # Trap stiffness
    m = RE_STIFFNESS.search(text_clean)
    if m:
        params["trap_stiffness_pN_per_nm"] = float(m.group(1))

    # Temperature
    temps = []
    for m in RE_TEMP.finditer(text_clean):
        v = m.group(1) or m.group(2)
        if v:
            t = float(v)
            if 4 <= t <= 50:  # reasonable biological temp range
                temps.append(t)
    if temps:
        # Take most common or first
        params["temperature_C"] = temps[0]

    # Force range
    force_vals = []
    for m in RE_FORCE.finditer(text_clean[:10000]):  # Methods section usually early
        g1, g2, g3, g4 = m.group(1), m.group(2), m.group(3), m.group(4)
        if g1 and g2:
            force_vals.append({"min": float(g1), "max": float(g2)})
        elif g3:
            force_vals.append({"tension": float(g3)})
        elif g4:
            force_vals.append({"tension": float(g4)})
    if force_vals:
        params["force_range_pN"] = force_vals[0]

    # Buffer / pH
    best_ph = None
    best_buf = None
    for m in RE_BUFFER.finditer(text_clean):
        conc, buf_name, ph1, ph2, ph3 = (m.group(1), m.group(2), m.group(3),
                                          m.group(4), m.group(5))
        ph = ph1 or ph2 or ph3
        if ph:
            pv = float(ph)
            if 4.0 <= pv <= 10.0:
                best_ph = pv
                if conc and buf_name:
                    best_buf = f"{conc} mM {buf_name}"
                break
    params["buffer_pH"] = best_ph
    if best_buf:
        params["buffer_composition"] = best_buf

    # DNA substrate
    m = RE_DNA.search(text_clean)
    if m:
        if re.search(r'lambda|λ|48[,.]?5', m.group(0), re.IGNORECASE):
            params["dna_substrate"] = "Lambda DNA (48.5 kbp)"
        else:
            kb = m.group(1) or m.group(2)
            params["dna_substrate"] = f"{kb} kbp DNA" if kb else m.group(0).strip()

    # Fluorescent labels
    labels = list(set(m.group(1) for m in RE_FLUOR_DYE.finditer(text_clean)))
    params["fluorescent_labels"] = labels[:6]  # keep top 6

    # Upgrade confidence if we got multiple fields
    filled = sum(1 for v in params.values() if v and v != [] and v != "low")
    if filled >= 4:
        params["extraction_confidence"] = "high"
    elif filled >= 2:
        params["extraction_confidence"] = "medium"

    return params


# ─── Update doi_metadata YAML ─────────────────────────────────────────────────
def update_yaml_with_params(yaml_path, extracted):
    """Write extracted params into the doi_metadata YAML file."""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    hw = data.get('hardware', {})
    ec = data.get('experimental_conditions', {})
    ms = data.get('measurements', {})

    # Instrument
    if extracted.get('instrument'):
        inst = hw.get('instrument', {})
        if 'LUMICKS C-Trap' in extracted['instrument']:
            inst.update({"manufacturer": "LUMICKS", "model": "C-Trap", "system_type": "commercial"})
        elif 'LUMICKS Q-Trap' in extracted['instrument']:
            inst.update({"manufacturer": "LUMICKS", "model": "Q-Trap", "system_type": "commercial"})
        elif 'LUMICKS' in extracted['instrument']:
            inst.update({"manufacturer": "LUMICKS", "system_type": "commercial"})
        elif 'Custom' in extracted['instrument']:
            inst.update({"manufacturer": "Custom-built", "system_type": "custom"})
        hw['instrument'] = inst

    # Trap config
    if extracted.get('trap_config'):
        ot = hw.get('optical_traps', {})
        ot['trap_configuration'] = extracted['trap_config']
        if 'dual' in extracted['trap_config']:
            ot['number_of_traps'] = 2
        elif 'single' in extracted['trap_config']:
            ot['number_of_traps'] = 1
        elif 'quadruple' in extracted['trap_config']:
            ot['number_of_traps'] = 4
        hw['optical_traps'] = ot

    # Laser wavelength
    if extracted.get('laser_wavelength_nm'):
        ot = hw.get('optical_traps', {})
        ot['laser_wavelength_nm'] = extracted['laser_wavelength_nm']
        hw['optical_traps'] = ot

    # Bead
    if extracted.get('bead_diameter_um'):
        hw['bead_diameter'] = {"value": extracted['bead_diameter_um'], "unit": "µm"}
        bp = hw.get('bead_properties', {})
        if extracted.get('bead_surface_chemistry'):
            bp['surface_chemistry'] = extracted['bead_surface_chemistry']
        hw['bead_properties'] = bp

    # Trap stiffness
    if extracted.get('trap_stiffness_pN_per_nm'):
        hw['trap_stiffness'] = {"value": extracted['trap_stiffness_pN_per_nm'], "unit": "pN/nm"}

    # Fluorescence
    if extracted.get('fluorescent_labels'):
        fl = hw.get('fluorescence', {})
        fl['dyes_detected'] = extracted['fluorescent_labels']
        hw['fluorescence'] = fl

    data['hardware'] = hw

    # Temperature
    if extracted.get('temperature_C'):
        ec['temperature_C'] = extracted['temperature_C']

    # Buffer
    buf = ec.get('buffer', {})
    if extracted.get('buffer_pH'):
        buf['pH'] = extracted['buffer_pH']
    if extracted.get('buffer_composition'):
        buf['composition_snippet'] = extracted['buffer_composition']
    ec['buffer'] = buf
    data['experimental_conditions'] = ec

    # Force / measurements
    if extracted.get('force_range_pN'):
        fr = extracted['force_range_pN']
        meas = ms.get('force_range', {})
        if 'min' in fr:
            meas['minimum_pN'] = fr['min']
            meas['maximum_pN'] = fr['max']
        elif 'tension' in fr:
            ms['tension_pN'] = fr['tension']
        ms['force_range'] = meas
        data['measurements'] = ms

    # DNA substrate
    if extracted.get('dna_substrate'):
        sample = data.get('sample', {})
        na = sample.get('nucleic_acid') or {}
        if isinstance(na, dict):
            if not na.get('name'):
                na['name'] = extracted['dna_substrate']
        else:
            na = {"name": extracted['dna_substrate']}
        sample['nucleic_acid'] = na
        data['sample'] = sample

    # Add extraction note
    conf = extracted.get('extraction_confidence', 'low')
    data['notes'] = (data.get('notes', '') or '') + \
                    f" [Auto-extracted params, confidence={conf}]"

    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return conf


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Extract experimental params from OT papers")
    parser.add_argument("--limit", type=int, default=None, help="Max papers to process")
    parser.add_argument("--doi", type=str, default=None, help="Process single DOI")
    parser.add_argument("--force", action="store_true", help="Re-process even if already done")
    args = parser.parse_args()

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cache = yaml.safe_load(f) or {}

    # Find all doi_metadata YAML files
    yaml_files = sorted(glob.glob("doi_metadata/*.yaml"))
    print(f"Found {len(yaml_files)} doi_metadata files")

    results = {}
    processed = 0
    skipped_cached = 0
    no_fulltext = 0
    errors = 0

    for yaml_path in yaml_files:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            doc = yaml.safe_load(f)

        raw_doi = (doc.get('citation') or {}).get('doi', '')
        doi = clean_doi(raw_doi)

        if not doi:
            continue

        # Filter to single DOI if specified
        if args.doi and args.doi not in doi:
            continue

        # Skip if already done (unless --force)
        if not args.force and doi in cache:
            skipped_cached += 1
            continue

        # Limit
        if args.limit and processed >= args.limit:
            break

        print(f"[{processed+1}] {doi}", end=" ... ", flush=True)

        try:
            # Get open-access URL
            oa_url = get_oa_url(doi)
            time.sleep(SLEEP_BETWEEN)

            # Fetch full text
            text = fetch_text(doi, oa_url)
            time.sleep(SLEEP_BETWEEN)

            if not text:
                print("NO FULLTEXT")
                no_fulltext += 1
                cache[doi] = {"status": "no_fulltext"}
                processed += 1
                continue

            # Extract parameters
            params = extract_params(text)
            conf = params.get("extraction_confidence", "low")
            print(f"OK (conf={conf}, bead={params.get('bead_diameter_um')}, pH={params.get('buffer_pH')})")

            # Update YAML
            update_yaml_with_params(yaml_path, params)
            cache[doi] = {"status": "extracted", "confidence": conf}
            results[doi] = params
            processed += 1

        except Exception as e:
            print(f"ERROR: {e}")
            cache[doi] = {"status": "error", "error": str(e)}
            errors += 1
            processed += 1

        # Save cache every 10 papers
        if processed % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                yaml.dump(cache, f)

    # Final cache save
    with open(CACHE_FILE, 'w') as f:
        yaml.dump(cache, f)

    # Summary
    print(f"\n{'='*60}")
    print(f"Processed:       {processed}")
    print(f"Extracted:       {len(results)}")
    print(f"No full text:    {no_fulltext}")
    print(f"Errors:          {errors}")
    print(f"Skipped (cache): {skipped_cached}")

    # Write extraction summary
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nExtraction summary saved to {OUTPUT_FILE}")
    print("Run python generate_website_data.py to update the website with new parameters.")


if __name__ == "__main__":
    main()
