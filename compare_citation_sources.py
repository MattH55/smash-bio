#!/usr/bin/env python3
"""
Compare citation counts from different databases for SMASH-BIO publications.
Sources: Semantic Scholar, CrossRef, OpenCitations
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

# UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_yaml_file(filepath):
    """Load a YAML file safely"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        return None

def save_yaml_file(filepath, data):
    """Save data to YAML file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

def clean_doi(doi):
    """Clean and extract DOI"""
    if not doi:
        return None
    doi = doi.strip()
    if doi.startswith('http'):
        match = re.search(r'(10\.\d+/[^\s]+)', doi)
        if match:
            return match.group(1)
        return None
    if doi.startswith('10.'):
        return doi
    return None

def get_semantic_scholar_citations(doi, title=None):
    """Get citation count from Semantic Scholar API"""
    if doi:
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
            params = {'fields': 'citationCount,title'}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('citationCount')
        except:
            pass
    
    # Try by title
    if title:
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {'query': title[:100], 'fields': 'citationCount,title', 'limit': 1}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                if papers:
                    return papers[0].get('citationCount')
        except:
            pass
    
    return None

def get_crossref_citations(doi):
    """Get citation count from CrossRef API"""
    doi = clean_doi(doi)
    if not doi:
        return None
    
    try:
        url = f"https://api.crossref.org/works/{doi}"
        headers = {'User-Agent': 'SMASH-BIO/1.0 (mailto:contact@smash-bio.com)'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('message', {}).get('is-referenced-by-count')
    except:
        pass
    
    return None

def get_opencitations_citations(doi):
    """Get citation count from OpenCitations API"""
    doi = clean_doi(doi)
    if not doi:
        return None
    
    try:
        url = f"https://opencitations.net/index/coci/api/v1/citation-count/{doi}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0].get('count')
    except:
        pass
    
    return None

def main():
    base_path = Path('.')
    
    # Load all DOIs from data.js
    data_file = base_path / 'website' / 'js' / 'data.js'
    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract JSON
    content = content.split('const SMASH_DATA = ')[1]
    end_idx = content.rfind('};')
    if end_idx > 0:
        content = content[:end_idx+1]
    
    data = json.loads(content)
    
    # Get all publications with DOIs
    all_pubs = data['publications'] + data['curated_studies']
    pubs_with_doi = [p for p in all_pubs if p.get('doi') and clean_doi(p.get('doi'))]
    
    print(f"Total publications: {len(all_pubs)}")
    print(f"Publications with DOI: {len(pubs_with_doi)}")
    print(f"\nComparing citation sources for sample of 50 publications...\n")
    
    # Sample for comparison (first 50 with DOI)
    sample = pubs_with_doi[:50]
    
    results = []
    
    semantic_scholar_count = 0
    crossref_count = 0
    opencitations_count = 0
    
    for i, pub in enumerate(sample):
        doi = clean_doi(pub.get('doi', ''))
        title = pub.get('title', '')[:50]
        
        print(f"[{i+1}/50] {title}...")
        
        # Get from each source
        ss = get_semantic_scholar_citations(doi, pub.get('title'))
        cr = get_crossref_citations(doi)
        oc = get_opencitations_citations(doi)
        
        if ss is not None:
            semantic_scholar_count += 1
        if cr is not None:
            crossref_count += 1
        if oc is not None:
            opencitations_count += 1
        
        results.append({
            'id': pub.get('id'),
            'doi': doi,
            'title': title,
            'semantic_scholar': ss,
            'crossref': cr,
            'opencitations': oc
        })
        
        # Rate limit
        time.sleep(0.5)
    
    # Print summary table
    print("\n" + "="*80)
    print("CITATION SOURCE COMPARISON (Sample of 50 publications)")
    print("="*80)
    print(f"\n{'Source':<25} {'Coverage':<15} {'Percentage':<15}")
    print("-"*55)
    print(f"{'Semantic Scholar':<25} {semantic_scholar_count}/50{'':<10} {semantic_scholar_count*2}%")
    print(f"{'CrossRef':<25} {crossref_count}/50{'':<10} {crossref_count*2}%")
    print(f"{'OpenCitations':<25} {opencitations_count}/50{'':<10} {opencitations_count*2}%")
    
    # Detailed comparison
    print("\n" + "="*80)
    print("DETAILED COMPARISON (First 20)")
    print("="*80)
    print(f"\n{'DOI':<25} {'SS':<8} {'CR':<8} {'OC':<8}")
    print("-"*55)
    
    for r in results[:20]:
        doi_short = (r['doi'][:22] + '...') if r['doi'] and len(r['doi']) > 22 else (r['doi'] or 'N/A')
        ss = str(r['semantic_scholar']) if r['semantic_scholar'] is not None else '-'
        cr = str(r['crossref']) if r['crossref'] is not None else '-'
        oc = str(r['opencitations']) if r['opencitations'] is not None else '-'
        print(f"{doi_short:<25} {ss:<8} {cr:<8} {oc:<8}")
    
    # Save results
    output_file = base_path / 'citation_comparison.yaml'
    save_yaml_file(output_file, {
        'comparison_date': datetime.now().isoformat(),
        'sample_size': 50,
        'coverage': {
            'semantic_scholar': semantic_scholar_count,
            'crossref': crossref_count,
            'opencitations': opencitations_count
        },
        'details': results
    })
    
    print(f"\nFull results saved to: {output_file}")
    
    # Recommendation
    best_source = max([
        ('Semantic Scholar', semantic_scholar_count),
        ('CrossRef', crossref_count),
        ('OpenCitations', opencitations_count)
    ], key=lambda x: x[1])
    
    print(f"\n{'='*80}")
    print(f"RECOMMENDATION: Use {best_source[0]} (highest coverage: {best_source[1]}/50)")
    print(f"{'='*80}")

