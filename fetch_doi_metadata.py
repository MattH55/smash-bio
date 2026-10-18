"""
Fetch Metadata from DOIs using CrossRef API

This script reads the OT_experiments-dois.csv file and fetches actual 
metadata (titles, authors, year, etc.) from the CrossRef API for each DOI.

Run: python fetch_doi_metadata.py
"""

import os
import csv
import yaml
import re
import time
import json
import urllib.request
import urllib.error
from datetime import datetime

# Configuration
INPUT_CSV = "OT_experiments-dois.csv"
OUTPUT_DIR = "extracted_metadata"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# CrossRef API settings
CROSSREF_API = "https://api.crossref.org/works/"
USER_AGENT = "SMASH-BIO/1.0 (mailto:research@example.com)"

def fetch_crossref_metadata(doi):
    """Fetch metadata from CrossRef API for a given DOI."""
    
    # Clean DOI - remove URL prefix if present
    clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    
    url = f"{CROSSREF_API}{clean_doi}"
    
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT}
        )
        
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("message", {})
    
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code} for DOI: {clean_doi}")
        return None
    except urllib.error.URLError as e:
        print(f"  URL Error for DOI: {clean_doi}: {e.reason}")
        return None
    except Exception as e:
        print(f"  Error fetching {clean_doi}: {str(e)}")
        return None

def extract_authors(crossref_data):
    """Extract author names from CrossRef data."""
    authors = []
    for author in crossref_data.get("author", []):
        given = author.get("given", "")
        family = author.get("family", "")
        if family:
            if given:
                authors.append(f"{family}, {given}")
            else:
                authors.append(family)
    return authors

def extract_year(crossref_data):
    """Extract publication year from CrossRef data."""
    # Try different date fields
    for date_field in ["published-print", "published-online", "created", "issued"]:
        date_parts = crossref_data.get(date_field, {}).get("date-parts", [[]])
        if date_parts and date_parts[0] and len(date_parts[0]) > 0:
            return date_parts[0][0]  # First element is year
    return None

def extract_abstract(crossref_data):
    """Extract and clean abstract from CrossRef data."""
    abstract = crossref_data.get("abstract", "")
    if abstract:
        # Remove JATS XML tags
        abstract = re.sub(r'<[^>]+>', '', abstract)
        # Clean up whitespace
        abstract = ' '.join(abstract.split())
    return abstract if abstract else None

def determine_system_type(row):
    """Determine the biological system type based on CSV flags."""
    biophysics = int(row.get('Biophysics', 0))
    molecular_physics = int(row.get('Molecular physics', 0))
    dna = int(row.get('DNA', 0))
    force_spectroscopy = int(row.get('Force spectroscopy', 0))
    
    if dna == 1 and biophysics == 1:
        return "DNA-protein"
    elif dna == 1:
        return "DNA"
    elif biophysics == 1 and force_spectroscopy == 1:
        return "biomolecule-force"
    elif biophysics == 1:
        return "biophysics"
    elif molecular_physics == 1:
        return "molecular-physics"
    elif force_spectroscopy == 1:
        return "force-spectroscopy"
    else:
        return "optical-trapping"

def determine_research_categories(row):
    """Determine research categories based on CSV flags."""
    categories = []
    
    if int(row.get('Biophysics', 0)) == 1:
        categories.append("biophysics")
    if int(row.get('Molecular physics', 0)) == 1:
        categories.append("molecular-physics")
    if int(row.get('DNA', 0)) == 1:
        categories.append("DNA")
    if int(row.get('Force spectroscopy', 0)) == 1:
        categories.append("force-spectroscopy")
    
    if not categories:
        categories.append("optical-tweezers")
    
    return categories

def extract_doi_id(doi_url):
    """Extract a clean identifier from a DOI URL."""
    doi = doi_url.replace("https://doi.org/", "").replace("http://doi.org/", "")
    safe_id = re.sub(r'[^\w\-.]', '_', doi)
    return safe_id, doi

def generate_metadata(row, crossref_data, index):
    """Generate a complete metadata dictionary."""
    
    doi_url = row['DOI'].strip()
    safe_id, doi = extract_doi_id(doi_url)
    
    pub_id = row['PublicationId'].strip()
    journal_from_csv = row['JournalName'].strip()
    citations = int(row.get('Citations', 0))
    fair_score = float(row.get('FAIR', 0))
    
    system_type = determine_system_type(row)
    categories = determine_research_categories(row)
    
    # Extract data from CrossRef
    if crossref_data:
        title = crossref_data.get("title", [None])[0] if crossref_data.get("title") else None
        authors = extract_authors(crossref_data)
        year = extract_year(crossref_data)
        journal = crossref_data.get("container-title", [journal_from_csv])[0] if crossref_data.get("container-title") else journal_from_csv
        volume = crossref_data.get("volume")
        issue = crossref_data.get("issue")
        page = crossref_data.get("page")
        publisher = crossref_data.get("publisher")
        abstract = extract_abstract(crossref_data)
        article_type = crossref_data.get("type")
        subjects = crossref_data.get("subject", [])
        references_count = crossref_data.get("references-count", 0)
        is_referenced_by_count = crossref_data.get("is-referenced-by-count", 0)
        license_info = crossref_data.get("license", [])
        url = crossref_data.get("URL")
    else:
        title = None
        authors = []
        year = None
        journal = journal_from_csv
        volume = None
        issue = None
        page = None
        publisher = None
        abstract = None
        article_type = None
        subjects = []
        references_count = 0
        is_referenced_by_count = 0
        license_info = []
        url = doi_url
    
    metadata = {
        "experiment_id": f"OT-{pub_id}",
        "metadata_version": "1.0.0",
        "created_date": datetime.now().isoformat(),
        "data_source": "CrossRef API" if crossref_data else "CSV only",
        
        "citation": {
            "title": title,
            "authors": authors,
            "journal": journal,
            "year": year,
            "volume": volume,
            "issue": issue,
            "pages": page,
            "doi": doi,
            "doi_url": doi_url,
            "url": url,
            "publisher": publisher,
            "article_type": article_type,
            "publication_id": pub_id,
            "citations_csv": citations,
            "citations_crossref": is_referenced_by_count,
            "references_count": references_count,
            "fair_score": fair_score
        },
        
        "abstract": abstract,
        
        "classification": {
            "system_type": system_type,
            "research_categories": categories,
            "subjects": subjects,
            "is_biophysics": int(row.get('Biophysics', 0)) == 1,
            "is_molecular_physics": int(row.get('Molecular physics', 0)) == 1,
            "involves_dna": int(row.get('DNA', 0)) == 1,
            "involves_force_spectroscopy": int(row.get('Force spectroscopy', 0)) == 1,
            "has_supplementary_data": True
        },
        
        "license": [
            {
                "url": lic.get("URL"),
                "content_version": lic.get("content-version"),
                "start_date": lic.get("start", {}).get("date-time")
            }
            for lic in license_info
        ] if license_info else None,
        
        "hardware": {
            "instrument": {
                "manufacturer": None,
                "model": None,
                "system_type": None
            },
            "optical_traps": {
                "number_of_traps": None,
                "trap_configuration": None,
                "laser_wavelength_nm": None,
                "laser_power_mW": None
            },
            "trap_stiffness": {
                "value": None,
                "unit": "pN/nm"
            },
            "bead_diameter": {
                "value": None,
                "unit": "μm"
            }
        },
        
        "sample": {
            "biological_system_type": system_type,
            "source_organism": None,
            "preparation_method": None
        },
        
        "experimental_conditions": {
            "buffer": None,
            "temperature_C": None,
            "ionic_strength_mM": None
        },
        
        "measurements": {
            "operation_mode": None,
            "force_range_pN": None
        }
    }
    
    return metadata, safe_id

def main():
    """Process CSV and fetch metadata for all DOIs."""
    
    print(f"Reading {INPUT_CSV}...")
    print("Fetching metadata from CrossRef API (this may take a while)...")
    print()
    
    publications = []
    successful = 0
    failed = 0
    
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        # Skip the header row with "Table S6..."
        first_line = f.readline()
        if "Table S6" not in first_line:
            f.seek(0)
        
        reader = csv.DictReader(f)
        rows = list(reader)
    
    total = len([r for r in rows if r.get('DOI', '').strip().startswith('http')])
    print(f"Found {total} DOIs to process")
    print("="*60)
    
    for idx, row in enumerate(rows):
        doi = row.get('DOI', '').strip()
        if not doi or not doi.startswith('http'):
            continue
        
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        print(f"[{idx+1}/{total}] Fetching: {clean_doi[:50]}...")
        
        # Fetch from CrossRef
        crossref_data = fetch_crossref_metadata(doi)
        
        if crossref_data:
            successful += 1
            title = crossref_data.get("title", ["Unknown"])[0][:60] if crossref_data.get("title") else "Unknown"
            # Normalize title for printing (handle Unicode)
            safe_title = title.encode('ascii', 'replace').decode('ascii')
            print(f"  [OK] Title: {safe_title}...")
        else:
            failed += 1
            print(f"  [FAIL] No data retrieved")
        
        # Generate metadata
        metadata, safe_id = generate_metadata(row, crossref_data, idx)
        
        # Save YAML file
        filename = f"ot_{idx+1:04d}_{safe_id[:50]}.yaml"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as yf:
            yaml.dump(metadata, yf, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        publications.append({
            "index": idx + 1,
            "id": metadata['experiment_id'],
            "filename": filename,
            "doi": doi,
            "title": metadata['citation']['title'],
            "authors": metadata['citation']['authors'][:3] if metadata['citation']['authors'] else [],  # First 3 authors
            "year": metadata['citation']['year'],
            "journal": metadata['citation']['journal'],
            "citations": metadata['citation']['citations_crossref'] or metadata['citation']['citations_csv'],
            "system_type": metadata['classification']['system_type'],
            "has_abstract": metadata['abstract'] is not None
        })
        
        # Rate limiting - be nice to the API
        time.sleep(0.5)
    
    print()
    print("="*60)
    print(f"COMPLETED: {successful} successful, {failed} failed")
    print("="*60)
    
    # Create comprehensive index
    print("\nCreating index file...")
    
    # Statistics
    stats = {
        "total": len(publications),
        "with_title": sum(1 for p in publications if p['title']),
        "with_abstract": sum(1 for p in publications if p['has_abstract']),
        "by_year": {},
        "by_system_type": {},
        "by_journal": {}
    }
    
    for pub in publications:
        # Count by year
        year = pub.get('year')
        if year:
            stats['by_year'][year] = stats['by_year'].get(year, 0) + 1
        
        # Count by system type
        st = pub['system_type']
        stats['by_system_type'][st] = stats['by_system_type'].get(st, 0) + 1
        
        # Count by journal
        j = pub['journal']
        if j:
            stats['by_journal'][j] = stats['by_journal'].get(j, 0) + 1
    
    # Sort publications by citations for top cited list
    pubs_by_citations = sorted(publications, key=lambda x: -(x['citations'] or 0))
    
    index = {
        "title": "Optical Tweezers Publications - Extracted Metadata Index",
        "description": "Complete metadata extracted from CrossRef API for optical tweezers publications",
        "source_file": INPUT_CSV,
        "generated": datetime.now().isoformat(),
        "statistics": {
            "total_publications": stats['total'],
            "with_title": stats['with_title'],
            "with_abstract": stats['with_abstract'],
            "by_year": dict(sorted(stats['by_year'].items(), reverse=True)),
            "by_system_type": dict(sorted(stats['by_system_type'].items(), key=lambda x: -x[1])),
            "top_journals": dict(sorted(stats['by_journal'].items(), key=lambda x: -x[1])[:20])
        },
        "top_50_cited": [
            {
                "id": p['id'],
                "title": p['title'],
                "first_author": p['authors'][0] if p['authors'] else None,
                "year": p['year'],
                "journal": p['journal'],
                "citations": p['citations'],
                "doi": p['doi'],
                "filename": p['filename']
            }
            for p in pubs_by_citations[:50]
        ],
        "all_publications": [
            {
                "index": p['index'],
                "id": p['id'],
                "filename": p['filename'],
                "title": p['title'],
                "year": p['year'],
                "journal": p['journal'],
                "doi": p['doi']
            }
            for p in publications
        ]
    }
    
    index_path = os.path.join(OUTPUT_DIR, "_index.yaml")
    with open(index_path, 'w', encoding='utf-8') as f:
        yaml.dump(index, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print(f"Created index file: {index_path}")
    
    # Print summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total publications: {stats['total']}")
    print(f"With titles: {stats['with_title']}")
    print(f"With abstracts: {stats['with_abstract']}")
    print(f"\nBy Year:")
    for year in sorted(stats['by_year'].keys(), reverse=True)[:10]:
        print(f"  {year}: {stats['by_year'][year]}")
    print(f"\nBy System Type:")
    for k, v in sorted(stats['by_system_type'].items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"\nTop 5 Journals:")
    for k, v in list(sorted(stats['by_journal'].items(), key=lambda x: -x[1]))[:5]:
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
