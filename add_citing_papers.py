#!/usr/bin/env python3
"""
Add relevant citing papers to the SMASH-BIO database.
Filters for high-quality optical tweezers biophysics papers.
"""

import yaml
import hashlib
import sys
import io
from pathlib import Path
from datetime import datetime

# UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_yaml_file(filepath):
    """Load a YAML file safely"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def save_yaml_file(filepath, data):
    """Save data to YAML file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

def is_highly_relevant(paper):
    """Check if paper is highly relevant to optical tweezers biophysics"""
    title = paper.get('title', '').lower()
    
    # High relevance keywords - must have at least one
    high_relevance = [
        'optical tweezer', 'optical trap', 'force spectroscopy',
        'magnetic tweezer', 'single-molecule', 'single molecule',
        'force-extension', 'force clamp', 'dna origami',
        'protein folding', 'molecular motor', 'dna stretching',
        'nanomechanic', 'piconewton', 'mechanosensing'
    ]
    
    # Biology keywords - must have at least one
    bio_keywords = [
        'dna', 'rna', 'protein', 'cell', 'chromatin', 'actin',
        'microtubule', 'enzyme', 'receptor', 'binding', 'helicase',
        'polymerase', 'nucleic', 'red blood', 'bacteria', 'virus'
    ]
    
    has_technique = any(kw in title for kw in high_relevance)
    has_bio = any(kw in title for kw in bio_keywords)
    
    # Papers that are clearly relevant based on title
    clearly_relevant = [
        'optical tweezer', 'magnetic tweezer', 'force spectroscopy',
        'single-molecule', 'single molecule', 'dna origami', 'afm'
    ]
    
    if any(kw in title for kw in clearly_relevant):
        return True
    
    return has_technique and has_bio

def generate_id(doi, paper_id):
    """Generate a unique ID for the paper"""
    if doi:
        hash_input = doi
    else:
        hash_input = paper_id
    
    hash_val = hashlib.md5(hash_input.encode()).hexdigest()[:10]
    return f"CITE-{hash_val}"

def classify_system_type(title):
    """Classify the biological system type"""
    title_lower = title.lower()
    
    if any(x in title_lower for x in ['chromatin', 'nucleosome', 'histone', 'dna-protein', 'protein-dna']):
        return 'DNA-protein'
    elif any(x in title_lower for x in ['dna', 'rna', 'nucleic acid', 'hairpin', 'g-quadruplex', 'origami']):
        return 'DNA'
    elif any(x in title_lower for x in ['protein', 'enzyme', 'receptor', 'folding', 'unfolding', 'titin', 'dystrophin']):
        return 'protein'
    elif any(x in title_lower for x in ['cell', 'membrane', 'lipid', 'red blood', 'cytoskeleton', 'actin', 'microtubule']):
        return 'cell-biology'
    elif any(x in title_lower for x in ['force', 'tweezer', 'spectroscopy', 'stretching', 'nanomechanic']):
        return 'force-spectroscopy'
    else:
        return 'biophysics'

def main():
    base_path = Path('.')
    
    # Load citing papers
    citing_file = base_path / 'citing_papers_found.yaml'
    citing_data = load_yaml_file(citing_file)
    
    if not citing_data:
        print("No citing papers found!")
        return
    
    papers = citing_data.get('papers', [])
    print(f"Loaded {len(papers)} citing papers")
    
    # Filter for high-quality relevant papers
    # Minimum 5 citations to ensure quality
    relevant_papers = [
        p for p in papers 
        if p.get('citations', 0) >= 5 and 
           is_highly_relevant(p) and
           p.get('doi')  # Must have DOI for verification
    ]
    
    print(f"Filtered to {len(relevant_papers)} highly relevant papers with DOI and 5+ citations")
    
    # Load existing extracted metadata index
    index_file = base_path / 'extracted_metadata' / '_index.yaml'
    index_data = load_yaml_file(index_file) or {'all_publications': [], 'metadata': {}}
    
    existing_dois = set()
    for pub in index_data.get('all_publications', []):
        if pub.get('doi'):
            existing_dois.add(pub['doi'].lower())
    
    # Add new papers
    added_count = 0
    for paper in relevant_papers:
        doi = paper.get('doi', '')
        
        # Skip if already exists
        if doi.lower() in existing_dois:
            continue
        
        paper_id = generate_id(doi, paper.get('paper_id', ''))
        system_type = classify_system_type(paper.get('title', ''))
        
        # Create entry
        entry = {
            'id': paper_id,
            'title': paper.get('title', 'Untitled'),
            'year': paper.get('year'),
            'journal': paper.get('journal', ''),
            'doi': doi,
            'first_author': paper.get('first_author', 'Unknown'),
            'citations': paper.get('citations', 0),
            'system_type': system_type,
            'source': 'citation_discovery',
            'discovered_from': paper.get('source_paper', '')
        }
        
        index_data['all_publications'].append(entry)
        existing_dois.add(doi.lower())
        added_count += 1
        
        print(f"  + [{paper.get('citations', 0)}] {paper.get('title', '')[:60]}...")
    
    # Update index metadata
    index_data['metadata'] = index_data.get('metadata', {})
    index_data['metadata']['last_citation_discovery'] = datetime.now().isoformat()
    index_data['metadata']['total_publications'] = len(index_data['all_publications'])
    
    # Save updated index
    save_yaml_file(index_file, index_data)
    
    print(f"\n{'='*60}")
    print(f"Added {added_count} new papers to the database")
    print(f"Total publications now: {len(index_data['all_publications'])}")
    print(f"\nRun 'python generate_website_data.py' to update the website")

if __name__ == '__main__':
    main()
