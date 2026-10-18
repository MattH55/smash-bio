#!/usr/bin/env python3
"""
Find papers citing articles in the SMASH-BIO database.
Uses Semantic Scholar API to discover new optical tweezers biophysics papers.
"""

import yaml
import json
import time
import sys
import io
import re
import requests
from pathlib import Path
from datetime import datetime

# Set UTF-8 encoding
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

def is_biophysics_related(title, abstract=''):
    """Check if a paper is related to biophysics/optical tweezers"""
    text = (str(title) + ' ' + str(abstract)).lower()
    
    # Must have optical tweezers or related technique
    technique_keywords = [
        'optical tweezer', 'optical trap', 'force spectroscopy', 
        'magnetic tweezer', 'single-molecule', 'single molecule',
        'force-extension', 'force clamp', 'afm', 'atomic force'
    ]
    
    # Must have biological content
    bio_keywords = [
        'dna', 'rna', 'protein', 'cell', 'membrane', 'chromatin',
        'enzyme', 'receptor', 'binding', 'folding', 'helicase',
        'polymerase', 'nucleic acid', 'peptide', 'lipid', 'bacteria',
        'molecular motor', 'kinesin', 'myosin', 'actin', 'microtubule',
        'biological', 'biomolecul', 'biophysic'
    ]
    
    has_technique = any(kw in text for kw in technique_keywords)
    has_bio = any(kw in text for kw in bio_keywords)
    
    return has_technique and has_bio

def get_paper_id_from_doi(doi):
    """Get Semantic Scholar paper ID from DOI"""
    if not doi:
        return None
    
    # Clean DOI
    doi = doi.strip()
    if doi.startswith('http'):
        match = re.search(r'10\.\d+/[^\s]+', doi)
        if match:
            doi = match.group()
        else:
            return None
    
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
        params = {'fields': 'paperId,title'}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('paperId')
    except Exception as e:
        pass
    
    return None

def get_citations(paper_id, limit=100):
    """Get papers that cite the given paper"""
    if not paper_id:
        return []
    
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations"
        params = {
            'fields': 'paperId,title,year,authors,journal,citationCount,externalIds,abstract',
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
    except Exception as e:
        print(f"    Error fetching citations: {e}")
    
    return []

def main():
    base_path = Path('.')
    
    # Load existing publications from data.js
    data_file = base_path / 'website' / 'js' / 'data.js'
    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract JSON (handle multiline)
    content = content.split('const SMASH_DATA = ')[1]
    # Find the end - look for closing };
    end_idx = content.rfind('};')
    if end_idx > 0:
        content = content[:end_idx+1]
    
    data = json.loads(content)
    
    # Get DOIs from top-cited publications
    all_pubs = data['publications'] + data['curated_studies']
    top_cited = sorted([p for p in all_pubs if p.get('citations')], 
                       key=lambda x: x.get('citations', 0), reverse=True)[:30]
    
    existing_ids = set(p.get('id') for p in all_pubs)
    existing_dois = set(p.get('doi', '').lower() for p in all_pubs if p.get('doi'))
    
    print(f"Searching citations from top {len(top_cited)} cited papers...")
    print(f"Existing publications in database: {len(all_pubs)}")
    print("-" * 60)
    
    new_papers = []
    seen_paper_ids = set()
    
    for i, pub in enumerate(top_cited):
        doi = pub.get('doi', '')
        title = pub.get('title', 'Unknown')[:50]
        
        if not doi:
            continue
        
        print(f"\n[{i+1}/{len(top_cited)}] {title}...")
        
        # Get Semantic Scholar paper ID
        paper_id = get_paper_id_from_doi(doi)
        if not paper_id:
            print("    Could not find paper ID")
            time.sleep(0.5)
            continue
        
        # Get citing papers
        citations = get_citations(paper_id, limit=100)
        print(f"    Found {len(citations)} citing papers")
        
        for cite in citations:
            citing = cite.get('citingPaper', {})
            citing_id = citing.get('paperId')
            
            if not citing_id or citing_id in seen_paper_ids:
                continue
            seen_paper_ids.add(citing_id)
            
            citing_title = citing.get('title', '')
            citing_abstract = citing.get('abstract', '') or ''
            citing_doi = citing.get('externalIds', {}).get('DOI', '')
            
            # Skip if already in database
            if citing_doi and citing_doi.lower() in existing_dois:
                continue
            
            # Check if biophysics related
            if is_biophysics_related(citing_title, citing_abstract):
                authors = citing.get('authors', [])
                first_author = authors[0].get('name', 'Unknown') if authors else 'Unknown'
                
                journal_info = citing.get('journal') or {}
                journal = journal_info.get('name', '') if isinstance(journal_info, dict) else str(journal_info)
                
                new_papers.append({
                    'title': citing_title,
                    'year': citing.get('year'),
                    'first_author': first_author,
                    'doi': citing_doi,
                    'journal': journal,
                    'citations': citing.get('citationCount', 0),
                    'paper_id': citing_id,
                    'source_paper': pub.get('id')
                })
        
        # Rate limit
        time.sleep(1)
    
    # Remove duplicates and sort by citation count
    unique_papers = {}
    for p in new_papers:
        key = p.get('doi') or p.get('paper_id')
        if key and (key not in unique_papers or p.get('citations', 0) > unique_papers[key].get('citations', 0)):
            unique_papers[key] = p
    
    new_papers = sorted(unique_papers.values(), key=lambda x: x.get('citations', 0), reverse=True)
    
    print("\n" + "=" * 60)
    print(f"Found {len(new_papers)} new biophysics papers from citation search")
    print("=" * 60)
    
    # Save results
    output = {
        'search_date': datetime.now().isoformat(),
        'total_found': len(new_papers),
        'papers': new_papers
    }
    
    output_file = base_path / 'citing_papers_found.yaml'
    save_yaml_file(output_file, output)
    print(f"\nResults saved to {output_file}")
    
    # Show top 20
    print("\nTop 20 new papers found:")
    print("-" * 60)
    for i, p in enumerate(new_papers[:20]):
        title = p.get('title', 'Unknown')[:65]
        citations = p.get('citations', 0)
        year = p.get('year', '?')
        print(f"{i+1}. [{citations}] ({year}) {title}")
        if p.get('doi'):
            print(f"   DOI: {p['doi']}")

if __name__ == '__main__':
    main()
