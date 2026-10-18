#!/usr/bin/env python3
"""
Generate comprehensive data.js for SMASH-BIO website
Filters for biophysics-related entries and looks up author information
"""

import yaml
import json
import os
import re
import time
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("Warning: requests not available, author lookup disabled")

try:
    from scholarly import scholarly
    HAS_SCHOLARLY = True
except ImportError:
    HAS_SCHOLARLY = False
    print("Warning: scholarly not available, Google Scholar citation lookup disabled")
    print("Install with: pip install scholarly")

def load_yaml_file(filepath):
    """Load a YAML file safely"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def is_biophysics_related(title, abstract=''):
    """Check if a publication is biophysics-related"""
    text = (str(title) + ' ' + str(abstract)).lower()
    
    # Biophysics keywords
    bio_keywords = [
        'dna', 'rna', 'protein', 'cell', 'membrane', 'chromatin', 'nucleosome',
        'histone', 'enzyme', 'receptor', 'binding', 'folding', 'unfolding',
        'helicase', 'polymerase', 'topoisomerase', 'nucleic acid', 'amino acid',
        'peptide', 'lipid', 'bilayer', 'vesicle', 'virus', 'bacteria', 'phage',
        'ribosome', 'transcription', 'replication', 'translation', 'gene',
        'chromosome', 'telomere', 'nucleotide', 'codon', 'hairpin', 'g-quadruplex',
        'motor', 'kinesin', 'myosin', 'dynein', 'actin', 'microtubule', 'filament',
        'cytoskeleton', 'organelle', 'mitochondri', 'nucleus', 'nuclear',
        'single-molecule', 'single molecule', 'force-extension', 'force extension',
        'molecular motor', 'molecular machine', 'biological', 'biomolecul',
        'biophysic', 'biochem', 'molecular biology', 'cell biology',
        'stretching', 'unzipping', 'unwinding', 'condensin', 'cohesin', 'smc',
        'repair', 'recombination', 'crispr', 'cas9', 'cas12', 'nuclease',
        'ligase', 'kinase', 'phosphatase', 'atpase', 'gtpase',
        'antibody', 'antigen', 'immunoglobulin', 'receptor-ligand',
        'cancer', 'tumor', 'disease', 'patient', 'clinical', 'therapeutic',
        'drug', 'inhibitor', 'substrate', 'cofactor', 'allosteric'
    ]
    
    # Exclude non-biological physics
    exclude_keywords = [
        'cold atom', 'quantum gas', 'bose-einstein', 'fermion', 'boson',
        'levitated particle', 'levitated nanosphere', 'optomechanics',
        'cavity opto', 'photonic crystal', 'metamaterial', 'plasmon',
        'quantum dot', 'semiconductor', 'graphene', 'carbon nanotube',
        'nanoparticle trap', 'aerosol', 'colloidal crystal', 'latex bead'
    ]
    
    # Check exclusions first
    for kw in exclude_keywords:
        if kw in text:
            return False
    
    # Check for biophysics keywords
    for kw in bio_keywords:
        if kw in text:
            return True
    
    return False

def classify_system_type(title, abstract=''):
    """Classify publication based on content"""
    text = (str(title) + ' ' + str(abstract)).lower()
    
    if any(x in text for x in ['chromatin', 'nucleosome', 'histone', 'dna-protein', 'protein-dna']):
        return 'DNA-protein'
    elif any(x in text for x in ['dna', 'rna', 'nucleic acid', 'hairpin', 'g-quadruplex', 'telomere']):
        return 'DNA'
    elif any(x in text for x in ['protein', 'enzyme', 'receptor', 'folding', 'unfolding']):
        return 'protein'
    elif any(x in text for x in ['cell', 'membrane', 'lipid', 'vesicle', 'cytoskeleton']):
        return 'cell-biology'
    elif any(x in text for x in ['force', 'tweezer', 'spectroscopy', 'stretching']):
        return 'force-spectroscopy'
    else:
        return 'biophysics'

def classify_experiment_type(title, abstract=''):
    """
    Classify publication into Table 3 experiment types:
    1. unfolding - Nucleic acid or protein unfolding
    2. dna_protein - DNA-protein interactions
    3. force_generation - Force generation by cytoskeletal filaments/motors
    4. rheology - Cell mechanics/rheology
    """
    text = (str(title) + ' ' + str(abstract)).lower()
    
    # Force generation keywords
    force_gen = ['kinesin', 'myosin', 'dynein', 'motor protein', 'molecular motor',
                 'actin filament', 'microtubule', 'cytoskeleton', 'spindle', 'mitotic',
                 'mdia1', 'formin', 'tubulin', 'actin polymerization']
    
    # Rheology keywords  
    rheology = ['rheology', 'microrheology', 'viscoelastic', 'cell mechanics',
                'cell stiffness', 'red blood cell', 'erythrocyte', 'membrane mechanics',
                'cortical stiffness', 'mechanosensing', 'mechanotransduction']
    
    # DNA-protein keywords
    dna_protein = ['dna-protein', 'helicase', 'polymerase', 'topoisomerase', 'nuclease',
                   'chromatin', 'nucleosome', 'histone', 'dna repair', 'replication',
                   'condensin', 'cohesin', 'crispr', 'cas9', 'rna polymerase', 'fancd2']
    
    # Unfolding keywords
    unfolding = ['unfolding', 'folding', 'force-extension', 'stretching', 'pulling',
                 'hairpin', 'g-quadruplex', 'riboswitch', 'mechanical fingerprint',
                 'contour length', 'persistence length', 'unzipping']
    
    scores = {
        'force_generation': sum(1 for kw in force_gen if kw in text),
        'rheology': sum(1 for kw in rheology if kw in text),
        'dna_protein': sum(1 for kw in dna_protein if kw in text),
        'unfolding': sum(1 for kw in unfolding if kw in text)
    }
    
    max_score = max(scores.values())
    if max_score == 0:
        return 'other'
    
    for cat, score in scores.items():
        if score == max_score:
            return cat
    return 'other'

def lookup_authors_from_doi(doi):
    """Look up authors from CrossRef API"""
    if not HAS_REQUESTS or not doi:
        return None
    
    # Clean DOI
    doi = doi.strip()
    if doi.startswith('http'):
        doi = re.search(r'10\.\d+/.+', doi)
        if doi:
            doi = doi.group()
        else:
            return None
    
    try:
        url = f"https://api.crossref.org/works/{doi}"
        headers = {'User-Agent': 'SMASH-BIO/1.0 (mailto:contact@smash-bio.com)'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', {})
            
            authors = message.get('author', [])
            author_list = []
            for author in authors[:10]:  # Limit to 10 authors
                family = author.get('family', '')
                given = author.get('given', '')
                if family:
                    author_list.append(f"{family}, {given}")
            
            return {
                'authors': author_list,
                'first_author': author_list[0] if author_list else None,
                'title': message.get('title', [''])[0] if message.get('title') else None,
                'journal': message.get('container-title', [''])[0] if message.get('container-title') else None,
                'year': message.get('published-print', {}).get('date-parts', [[None]])[0][0] or \
                        message.get('published-online', {}).get('date-parts', [[None]])[0][0]
            }
    except Exception as e:
        print(f"  Error looking up {doi}: {e}")
    
    return None

def extract_first_author(authors):
    """Extract first author from various author formats"""
    if not authors:
        return 'Unknown'
    
    if isinstance(authors, list):
        if len(authors) > 0:
            author = authors[0]
            if isinstance(author, dict):
                family = author.get('family', '')
                given = author.get('given', '')
                if family:
                    return f"{family}, {given[0]}." if given else family
            elif isinstance(author, str):
                return author
    elif isinstance(authors, str):
        if ';' in authors:
            return authors.split(';')[0].strip()
        elif ',' in authors and authors.count(',') >= 1:
            parts = authors.split(',')
            if len(parts) >= 2:
                return f"{parts[0].strip()}, {parts[1].strip()[0]}."
        return authors
    
    return 'Unknown'

def main():
    base_path = Path('.')
    extracted_path = base_path / 'extracted_metadata'
    publications_path = base_path / 'publications_metadata'
    output_path = base_path / 'website' / 'js' / 'data.js'
    citation_cache_file = base_path / 'citation_cache.yaml'
    
    # Load citation cache if available
    citation_cache = load_yaml_file(citation_cache_file) or {}
    if citation_cache:
        print(f"Loaded {len(citation_cache)} cached citations")
    
    # Load author cache if available
    author_cache_file = base_path / 'author_cache.yaml'
    author_cache = load_yaml_file(author_cache_file) or {}
    if author_cache:
        print(f"Loaded {len(author_cache)} cached authors")
    
    # Load index for extracted metadata
    index_file = extracted_path / '_index.yaml'
    index_data = load_yaml_file(index_file)
    
    # Load citing papers found through citation discovery
    citing_file = base_path / 'citing_papers_found.yaml'
    citing_data = load_yaml_file(citing_file)
    
    all_publications = []
    curated_studies = []
    # Note: author_cache is loaded from file above, do not reset!
    
    # Process extracted publications - filter for biophysics
    print("Loading and filtering extracted publications...")
    biophysics_count = 0
    skipped_count = 0
    
    if index_data and 'all_publications' in index_data:
        for i, pub in enumerate(index_data['all_publications']):
            # Load individual YAML for more details
            filename = pub.get('filename')
            full_data = None
            if filename:
                full_data = load_yaml_file(extracted_path / filename)
            
            title = pub.get('title', 'Untitled')
            abstract = full_data.get('abstract', '') if full_data else ''
            
            # Filter for biophysics only
            if not is_biophysics_related(title, abstract):
                skipped_count += 1
                continue
            
            biophysics_count += 1
            
            # Get citation count and author from index
            citations = 0
            first_author = 'Unknown'
            
            if index_data.get('top_50_cited'):
                for tc in index_data['top_50_cited']:
                    if tc.get('id') == pub.get('id'):
                        citations = tc.get('citations', 0)
                        first_author = tc.get('first_author', 'Unknown')
                        break
            
            # Try to get author from full data
            if full_data and (first_author == 'Unknown' or not first_author):
                first_author = extract_first_author(full_data.get('authors', []))
            
            # Look up from CrossRef if still unknown (skip to save time)
            doi = pub.get('doi', '')
            # Commenting out slow DOI lookup for faster generation
            # if first_author == 'Unknown' and doi and HAS_REQUESTS:
            #     if doi in author_cache:
            #         crossref_data = author_cache[doi]
            #     else:
            #         print(f"  Looking up DOI: {doi[:50]}...")
            #         crossref_data = lookup_authors_from_doi(doi)
            #         author_cache[doi] = crossref_data
            #         time.sleep(0.1)  # Rate limit
            #     
            #     if crossref_data:
            #         first_author = crossref_data.get('first_author', 'Unknown')
            
            system_type = classify_system_type(title, abstract)
            experiment_type = classify_experiment_type(title, abstract)
            
            pub_id = pub.get('id', '')
            
            # Use citation count from cache if available (0 is valid)
            if pub_id in citation_cache and citation_cache[pub_id] is not None:
                citations = citation_cache[pub_id]
            else:
                citations = 0  # Default to 0 if no data
            
            # Use author from cache if available and better than current
            if pub_id in author_cache and author_cache[pub_id]:
                first_author = author_cache[pub_id]
            
            all_publications.append({
                'id': pub_id,
                'title': title,
                'year': pub.get('year'),
                'journal': pub.get('journal', ''),
                'doi': doi,
                'system_type': system_type,
                'experiment_type': experiment_type,
                'first_author': first_author if first_author and first_author != 'Unknown' else None,
                'citations': citations,
                'abstract': abstract[:500] if abstract else '',
                'source': 'extracted'
            })
    
    print(f"  Kept {biophysics_count} biophysics publications, skipped {skipped_count} non-biophysics")
    
    # Process citing papers (discovered through citation network)
    if citing_data and citing_data.get('papers'):
        print("Loading papers from citation discovery...")
        citing_added = 0
        existing_dois = set(p.get('doi', '').lower() for p in all_publications if p.get('doi'))
        
        for paper in citing_data['papers']:
            # Only include papers with 5+ citations and DOI
            if paper.get('citations', 0) < 5 or not paper.get('doi'):
                continue
            
            title = paper.get('title', '')
            doi = paper.get('doi', '')
            
            # Skip duplicates
            if doi.lower() in existing_dois:
                continue
            
            # Only include clearly biophysics-related papers
            if not is_biophysics_related(title, ''):
                continue
            
            system_type = classify_system_type(title, '')
            
            # Generate unique ID
            import hashlib
            hash_val = hashlib.md5(doi.encode()).hexdigest()[:10]
            pub_id = f"CITE-{hash_val}"
            
            all_publications.append({
                'id': pub_id,
                'title': title,
                'year': paper.get('year'),
                'journal': paper.get('journal', ''),
                'doi': doi,
                'system_type': system_type,
                'first_author': paper.get('first_author', 'Unknown'),
                'citations': paper.get('citations'),
                'abstract': '',
                'source': 'citation_discovery'
            })
            
            existing_dois.add(doi.lower())
            citing_added += 1
        
        print(f"  Added {citing_added} papers from citation discovery")
    
    # Process curated studies (all are biophysics by definition)
    print("Loading curated studies...")
    for study_file in sorted(publications_path.glob('study_*.yaml')):
        data = load_yaml_file(study_file)
        if not data:
            continue
        
        study_id = data.get('experiment_id', data.get('study_id', study_file.stem))
        
        # Handle both 'citation' and 'publication' structures
        pub_info = data.get('citation', data.get('publication', {}))
        
        title = pub_info.get('title', data.get('title', 'Untitled'))
        year = pub_info.get('year', data.get('year'))
        journal = pub_info.get('journal', data.get('journal', ''))
        doi = pub_info.get('doi', data.get('doi', ''))
        
        # Get authors - handle list of strings
        authors = pub_info.get('authors', data.get('authors', []))
        first_author = extract_first_author(authors)
        
        # Determine system type from sample.biological_system_type or biological_system
        sample_data = data.get('sample', {})
        bio_system_type = sample_data.get('biological_system_type', '')
        if bio_system_type:
            system_type = bio_system_type
        else:
            bio_system = data.get('biological_system', {})
            system_type = bio_system.get('type', 'biophysics')
        
        if system_type not in ['DNA', 'DNA-protein', 'protein', 'cell-biology']:
            system_type = classify_system_type(title, str(sample_data))
        
        abstract = pub_info.get('abstract', data.get('abstract', ''))
        sample_info = sample_data
        
        # Use citation count from cache if available (0 is valid)
        cached_citations = citation_cache.get(study_id)
        citations = cached_citations if cached_citations is not None else 0
        
        # Extract hardware/instrument details
        hardware = data.get('hardware', {})
        instrument = hardware.get('instrument', {})
        optical_traps = hardware.get('optical_traps', {})
        trap_stiffness = hardware.get('trap_stiffness', {})
        bead = hardware.get('bead_diameter', {})
        bead_props = hardware.get('bead_properties', {})
        fluorescence = hardware.get('fluorescence', {})
        microfluidics = hardware.get('microfluidics', {})
        
        # Extract experimental conditions
        exp_cond = data.get('experimental_conditions', {})
        buffer = exp_cond.get('buffer', {})
        
        # Extract measurements
        measurements = data.get('measurements', {})
        force_range = measurements.get('force_range', {})
        
        # Extract sample details
        nucleic_acid = sample_data.get('nucleic_acid', {})
        protein = sample_data.get('protein', {})
        
        curated_studies.append({
            'id': study_id,
            'title': title,
            'year': year,
            'journal': journal,
            'doi': doi,
            'system_type': system_type,
            'first_author': first_author,
            'citations': citations,
            'abstract': abstract[:500] if abstract else '',
            'source': 'curated',
            'has_full_metadata': True,
            
            # Full publication info
            'publication': {
                'title': title,
                'authors': authors if isinstance(authors, list) else [authors] if authors else [],
                'journal': journal,
                'year': year,
                'volume': pub_info.get('volume', ''),
                'pages': pub_info.get('pages', ''),
                'doi': doi,
                'pubmed_id': pub_info.get('pubmed_id', '')
            },
            
            # Sample metadata
            'sample': {
                'biological_system_type': sample_data.get('biological_system_type', system_type),
                'organism': sample_data.get('source', {}).get('organism', ''),
                'preparation_method': sample_data.get('source', {}).get('preparation_method', ''),
                'nucleic_acid': {
                    'type': nucleic_acid.get('type', ''),
                    'name': nucleic_acid.get('name', ''),
                    'length_kb': nucleic_acid.get('length_kb'),
                    'topology': nucleic_acid.get('topology', '')
                },
                'protein': {
                    'name': protein.get('name', ''),
                    'abbreviation': protein.get('abbreviation', ''),
                    'expression_system': protein.get('expression_system', ''),
                    'concentration_nM': protein.get('concentration_nM')
                }
            },
            
            # Hardware/instrument
            'hardware': {
                'instrument': {
                    'manufacturer': instrument.get('manufacturer', ''),
                    'model': instrument.get('model', ''),
                    'system_type': instrument.get('system_type', '')
                },
                'optical_traps': {
                    'number_of_traps': optical_traps.get('number_of_traps'),
                    'trap_configuration': optical_traps.get('trap_configuration', ''),
                    'laser_wavelength_nm': optical_traps.get('laser_wavelength_nm'),
                    'laser_power_mW': optical_traps.get('laser_power_mW')
                },
                'trap_stiffness': {
                    'value': trap_stiffness.get('value'),
                    'unit': trap_stiffness.get('unit', 'pN/nm')
                },
                'bead': {
                    'diameter_um': bead.get('value'),
                    'material': bead_props.get('material', ''),
                    'surface_chemistry': bead_props.get('surface_chemistry', '')
                },
                'fluorescence': {
                    'capability': fluorescence.get('capability', ''),
                    'excitation_wavelengths_nm': fluorescence.get('excitation_wavelengths_nm', []),
                    'detector_type': fluorescence.get('detector_type', '')
                },
                'microfluidics': {
                    'enabled': microfluidics.get('enabled', False),
                    'number_of_channels': microfluidics.get('number_of_channels'),
                    'flow_control': microfluidics.get('flow_control', '')
                }
            },
            
            # Experimental conditions
            'experimental_conditions': {
                'buffer': {
                    'name': buffer.get('name', ''),
                    'pH': buffer.get('pH')
                },
                'temperature_C': exp_cond.get('temperature_C')
            },
            
            # Measurements
            'measurements': {
                'operation_mode': measurements.get('operation_mode', ''),
                'force_range_pN': {
                    'min': force_range.get('minimum_pN'),
                    'max': force_range.get('maximum_pN')
                },
                'tension_pN': measurements.get('tension_pN'),
                'fluorescence_imaging': {
                    'enabled': measurements.get('fluorescence_imaging', {}).get('enabled', False),
                    'acquisition_mode': measurements.get('fluorescence_imaging', {}).get('acquisition_mode', '')
                }
            },
            
            # Additional
            'notes': data.get('notes', '')
        })
    
    print(f"Loaded {len(curated_studies)} curated studies")
    
    # Statistics
    total = len(all_publications) + len(curated_studies)
    
    type_counts = {}
    year_counts = {}
    journal_counts = {}
    
    for pub in all_publications + curated_studies:
        st = pub.get('system_type', 'other')
        type_counts[st] = type_counts.get(st, 0) + 1
        
        year = pub.get('year')
        if year:
            year_counts[year] = year_counts.get(year, 0) + 1
        
        journal = pub.get('journal', '')
        if journal:
            journal_counts[journal] = journal_counts.get(journal, 0) + 1
    
    top_journals = sorted(journal_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    
    top_cited = sorted(
        [p for p in all_publications if p.get('citations') is not None and p.get('citations') > 0],
        key=lambda x: x.get('citations') or 0,
        reverse=True
    )[:20]
    
    # Build final data structure
    data = {
        'statistics': {
            'total_publications': total,
            'extracted_publications': len(all_publications),
            'curated_studies': len(curated_studies),
            'by_type': type_counts,
            'by_year': dict(sorted(year_counts.items())),
            'top_journals': dict(top_journals)
        },
        'top_cited': top_cited,
        'curated_studies': curated_studies,
        'publications': all_publications
    }
    
    # Write JavaScript file
    js_content = '''// SMASH-BIO Complete Data
// Biophysics-focused publications from extracted_metadata and publications_metadata
// Total: ''' + str(total) + ''' entries

const SMASH_DATA = ''' + json.dumps(data, indent=2, ensure_ascii=False) + ''';
'''
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"\nGenerated {output_path}")
    print(f"Total biophysics entries: {total}")
    print(f"  - Extracted: {len(all_publications)}")
    print(f"  - Curated: {len(curated_studies)}")
    print(f"\nBy system type:")
    for st, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {st}: {count}")

if __name__ == '__main__':
    main()
