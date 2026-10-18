#!/usr/bin/env python3
"""
Fetch citation counts for all SMASH-BIO publications.
Uses CrossRef (100% coverage), with Semantic Scholar and OpenCitations as fallbacks.
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
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        return None

def save_yaml_file(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

def clean_doi(doi):
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

def get_crossref_citations(doi):
    """CrossRef: Best coverage (100%)"""
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

def get_semantic_scholar_citations(doi, title=None):
    """Semantic Scholar: Second best (86%)"""
    doi = clean_doi(doi)
    if doi:
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
            params = {'fields': 'citationCount'}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get('citationCount')
        except:
            pass
    
    # Try by title
    if title:
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {'query': title[:100], 'fields': 'citationCount', 'limit': 1}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                if papers:
                    return papers[0].get('citationCount')
        except:
            pass
    return None

def get_opencitations_citations(doi):
    """OpenCitations: Third option (96%)"""
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
    cache_file = base_path / 'citation_cache.yaml'
    
    # Load existing cache
    citation_cache = load_yaml_file(cache_file) or {}
    print(f"Loaded {len(citation_cache)} existing cached citations")
    
    # Load data.js to get all publications
    data_file = base_path / 'website' / 'js' / 'data.js'
    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.split('const SMASH_DATA = ')[1]
    end_idx = content.rfind('};')
    if end_idx > 0:
        content = content[:end_idx+1]
    
    data = json.loads(content)
    all_pubs = data['publications'] + data['curated_studies']
    
    print(f"Total publications: {len(all_pubs)}")
    print("Using CrossRef (primary), Semantic Scholar and OpenCitations (fallbacks)")
    print("-" * 60)
    
    updated = 0
    cr_found = 0
    ss_found = 0
    oc_found = 0
    
    for i, pub in enumerate(all_pubs):
        pub_id = pub.get('id', '')
        doi = pub.get('doi', '')
        title = pub.get('title', '')
        
        # Skip if already in cache with value > 0
        if pub_id in citation_cache and citation_cache[pub_id] and citation_cache[pub_id] > 0:
            continue
        
        safe_title = title[:40].encode('ascii', 'replace').decode() if title else 'Unknown'
        print(f"[{i+1}/{len(all_pubs)}] {safe_title}...")
        
        citations = None
        source = None
        
        # Try CrossRef first (100% coverage)
        citations = get_crossref_citations(doi)
        if citations is not None:
            source = 'CR'
            cr_found += 1
        else:
            # Try Semantic Scholar (86% coverage)
            citations = get_semantic_scholar_citations(doi, title)
            if citations is not None:
                source = 'SS'
                ss_found += 1
            else:
                # Try OpenCitations (96% coverage)
                citations = get_opencitations_citations(doi)
                if citations is not None:
                    source = 'OC'
                    oc_found += 1
        
        if citations is not None:
            citation_cache[pub_id] = citations
            updated += 1
            if citations > 0:
                print(f"    [{source}] {citations} citations")
        else:
            citation_cache[pub_id] = 0
        
        # Save every 20 updates
        if updated % 20 == 0 and updated > 0:
            save_yaml_file(cache_file, citation_cache)
            print("    [Cache saved]")
        
        # Rate limit
        time.sleep(0.3)
    
    # Final save
    save_yaml_file(cache_file, citation_cache)
    
    print("\n" + "=" * 60)
    print("CITATION FETCH COMPLETE")
    print("=" * 60)
    print(f"Updated: {updated}")
    print(f"  CrossRef: {cr_found}")
    print(f"  Semantic Scholar: {ss_found}")
    print(f"  OpenCitations: {oc_found}")
    print(f"Total with citations > 0: {sum(1 for v in citation_cache.values() if v and v > 0)}")
    print(f"\nCache saved to: {cache_file}")
    print("\nRun 'python generate_website_data.py' to update the website")

if __name__ == '__main__':
    main()
