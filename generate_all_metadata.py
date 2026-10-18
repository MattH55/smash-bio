"""
Generate YAML Metadata Files for ALL Optical Tweezers Publications from CSV

This script reads the OT_experiments-dois.csv file and generates individual 
YAML metadata files for all optical tweezers publications with DOIs.

Run: python generate_all_metadata.py
"""

import os
import csv
import yaml
import re
from datetime import datetime

# Configuration
INPUT_CSV = "OT_experiments-dois.csv"
OUTPUT_DIR = "doi_metadata"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_doi_id(doi_url):
    """Extract a clean identifier from a DOI URL."""
    # Remove the https://doi.org/ prefix
    doi = doi_url.replace("https://doi.org/", "").replace("http://doi.org/", "")
    # Create a safe filename from DOI
    safe_id = re.sub(r'[^\w\-.]', '_', doi)
    return safe_id, doi

def determine_system_type(row):
    """Determine the biological system type based on CSV flags."""
    biophysics = int(row.get('Biophysics', 0))
    molecular_physics = int(row.get('Molecular physics', 0))
    dna = int(row.get('DNA', 0))
    force_spectroscopy = int(row.get('Force spectroscopy', 0))
    
    # Categorize based on flags
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

def determine_research_category(row):
    """Determine research categories based on journal and flags."""
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

def generate_metadata(row, index):
    """Generate a metadata dictionary for a publication."""
    
    doi_url = row['DOI'].strip()
    safe_id, doi = extract_doi_id(doi_url)
    
    pub_id = row['PublicationId'].strip()
    journal = row['JournalName'].strip()
    citations = int(row.get('Citations', 0))
    fair_score = float(row.get('FAIR', 0))
    
    system_type = determine_system_type(row)
    categories = determine_research_category(row)
    
    metadata = {
        "experiment_id": f"OT-{pub_id}",
        "metadata_version": "1.0.0",
        "created_date": datetime.now().isoformat(),
        "last_modified": datetime.now().isoformat(),
        "source": {
            "file": INPUT_CSV,
            "index": index + 1
        },
        
        "citation": {
            "title": None,  # To be filled from DOI lookup
            "authors": [],  # To be filled from DOI lookup
            "journal": journal,
            "year": None,  # To be extracted from DOI or lookup
            "volume": None,
            "pages": None,
            "doi": doi,
            "doi_url": doi_url,
            "pubmed_id": None,
            "publication_id": pub_id,
            "citations": citations,
            "fair_score": fair_score
        },
        
        "classification": {
            "system_type": system_type,
            "research_categories": categories,
            "is_biophysics": int(row.get('Biophysics', 0)) == 1,
            "is_molecular_physics": int(row.get('Molecular physics', 0)) == 1,
            "involves_dna": int(row.get('DNA', 0)) == 1,
            "involves_force_spectroscopy": int(row.get('Force spectroscopy', 0)) == 1,
            "has_supplementary_data": True  # All entries in this table have data
        },
        
        "hardware": {
            "instrument": {
                "manufacturer": None,  # To be extracted from paper
                "model": None,
                "system_type": None  # commercial/custom
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
            },
            "bead_properties": {
                "material": None,
                "surface_chemistry": None,
                "manufacturer": None,
                "catalog_number": None
            },
            "fluorescence": {
                "capability": None,
                "excitation_wavelengths_nm": [],
                "detector_type": None
            },
            "microfluidics": {
                "enabled": None,
                "number_of_channels": None,
                "flow_control": None
            }
        },
        
        "sample": {
            "biological_system_type": system_type,
            "source": {
                "organism": None,
                "preparation_method": None
            },
            "nucleic_acid": {
                "type": None,
                "name": None,
                "length_kb": None,
                "topology": None
            } if int(row.get('DNA', 0)) == 1 else None,
            "protein": {
                "name": None,
                "abbreviation": None,
                "expression_system": None,
                "concentration_nM": None
            } if int(row.get('Biophysics', 0)) == 1 else None
        },
        
        "experimental_conditions": {
            "buffer": {
                "name": None,
                "pH": None
            },
            "temperature_C": None,
            "ionic_strength_mM": None,
            "additives": []
        },
        
        "measurements": {
            "operation_mode": None,  # force-clamp, force-extension, etc.
            "force_range": {
                "minimum_pN": None,
                "maximum_pN": None
            },
            "tension_pN": None,
            "data_acquisition_rate_Hz": None,
            "fluorescence_imaging": {
                "enabled": None,
                "acquisition_mode": None
            }
        },
        
        "data_availability": {
            "has_supplementary_files": True,
            "has_raw_data": None,
            "repository": None,
            "repository_url": None,
            "file_formats": [],
            "data_processing_software": None
        },
        
        "results": {
            "primary_measurements": [],
            "key_findings": []
        },
        
        "notes": f"FAIR score: {fair_score}. Citation count: {citations}. Auto-generated from {INPUT_CSV}."
    }
    
    return metadata, safe_id

def main():
    """Process CSV and generate all metadata files."""
    
    print(f"Reading {INPUT_CSV}...")
    
    publications = []
    
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        # Skip the header row with "Table S6..."
        first_line = f.readline()
        if "Table S6" in first_line:
            pass  # Skip this line
        else:
            f.seek(0)  # Go back to start if no header
        
        reader = csv.DictReader(f)
        
        for idx, row in enumerate(reader):
            # Skip empty rows or rows without DOI
            doi = row.get('DOI', '').strip()
            if not doi or not doi.startswith('http'):
                continue
            
            metadata, safe_id = generate_metadata(row, idx)
            
            # Create filename
            filename = f"ot_{idx+1:04d}_{safe_id[:50]}.yaml"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            # Write YAML file
            with open(filepath, 'w', encoding='utf-8') as yf:
                yaml.dump(metadata, yf, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            publications.append({
                "index": idx + 1,
                "id": f"OT-{row['PublicationId'].strip()}",
                "filename": filename,
                "doi": row['DOI'].strip(),
                "journal": row['JournalName'].strip(),
                "citations": int(row.get('Citations', 0)),
                "fair_score": float(row.get('FAIR', 0)),
                "system_type": metadata['classification']['system_type'],
                "categories": metadata['classification']['research_categories']
            })
            
            if (idx + 1) % 25 == 0:
                print(f"  Processed {idx + 1} publications...")
    
    print(f"\nGenerated {len(publications)} metadata files in '{OUTPUT_DIR}/'")
    
    # Create index file
    print("Creating index file...")
    
    # Sort by citations (descending) for the index
    publications_by_citations = sorted(publications, key=lambda x: -x['citations'])
    
    # Create statistics
    stats = {
        "total": len(publications),
        "by_category": {},
        "by_journal": {},
        "by_system_type": {}
    }
    
    for pub in publications:
        # Count by system type
        st = pub['system_type']
        stats['by_system_type'][st] = stats['by_system_type'].get(st, 0) + 1
        
        # Count by journal
        j = pub['journal']
        stats['by_journal'][j] = stats['by_journal'].get(j, 0) + 1
        
        # Count by category
        for cat in pub['categories']:
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
    
    index = {
        "title": "Optical Tweezers Publications Metadata Index",
        "description": "Auto-generated metadata files for optical tweezers experiments from Table S6",
        "source_file": INPUT_CSV,
        "generated": datetime.now().isoformat(),
        "statistics": {
            "total_publications": stats['total'],
            "by_system_type": stats['by_system_type'],
            "by_category": stats['by_category'],
            "top_journals": dict(sorted(stats['by_journal'].items(), key=lambda x: -x[1])[:20])
        },
        "top_cited_publications": [
            {
                "id": p['id'],
                "doi": p['doi'],
                "journal": p['journal'],
                "citations": p['citations'],
                "filename": p['filename']
            }
            for p in publications_by_citations[:50]
        ],
        "all_publications": [
            {
                "index": p['index'],
                "id": p['id'],
                "filename": p['filename'],
                "doi": p['doi'],
                "journal": p['journal'],
                "system_type": p['system_type']
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
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total publications: {stats['total']}")
    print(f"\nBy System Type:")
    for k, v in sorted(stats['by_system_type'].items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"\nBy Research Category:")
    for k, v in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"\nTop 10 Journals:")
    for k, v in list(sorted(stats['by_journal'].items(), key=lambda x: -x[1]))[:10]:
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
