#!/usr/bin/env python3
"""
Fetch and update author information for all SMASH-BIO publications.
Uses CrossRef API to get first author name for each DOI.
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

def get_first_author_from_crossref(doi):
    """Get first author from CrossRef API"""
    doi = clean_doi(doi)
    if not doi:
        return None
    
    try:
        url = f"https://api.crossref.org/works/{doi}"
        headers = {'User-Agent': 'SMASH-BIO/1.0 (mailto:contact@smash-bio.com)'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', {})
            authors = message.get('author', [])
            
            if authors and len(authors) > 0:
                first = authors[0]
                family = first.get('family', '')
                given = first.get('given', '')
                
                if family:
                    # Format: "Family, G." or "Family, Given"
                    if given:
                        # Use first initial if given name is long
                        if len(given) > 3:
                            return f"{family}, {given[0]}."
                        else:
                            return f"{family}, {given}"
                    return family
    except Exception as e:
        pass
    
    return None

def get_first_author_from_semantic_scholar(doi, title=None):
    """Get first author from Semantic Scholar API"""
    doi = clean_doi(doi)
    
    if doi:
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
            params = {'fields': 'authors'}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                authors = data.get('authors', [])
                if authors and len(authors) > 0:
                    name = authors[0].get('name', '')
                    if name:
                        # Convert "First Last" to "Last, F."
                        parts = name.split()
                        if len(parts) >= 2:
                            return f"{parts[-1]}, {parts[0][0]}."
                        return name
        except:
            pass
    
    # Try title search
    if title:
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {'query': title[:100], 'fields': 'authors', 'limit': 1}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                if papers:
                    authors = papers[0].get('authors', [])
                    if authors and len(authors) > 0:
                        name = authors[0].get('name', '')
                        if name:
                            parts = name.split()
                            if len(parts) >= 2:
                                return f"{parts[-1]}, {parts[0][0]}."
                            return name
        except:
            pass
    
    return None

def main():
    base_path = Path('.')
    cache_file = base_path / 'author_cache.yaml'
    
    # Load existing cache
    author_cache = load_yaml_file(cache_file) or {}
    print(f"Loaded {len(author_cache)} existing cached authors")
    
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
    
    # Filter for missing authors
    needs_author = [p for p in all_pubs if not p.get('first_author') 
                    or p.get('first_author', '').lower() in ['unknown', 'various', '']]
    
    print(f"Total publications: {len(all_pubs)}")
    print(f"Missing authors: {len(needs_author)}")
    print("-" * 60)
    
    updated = 0
    cr_found = 0
    ss_found = 0
    
    for i, pub in enumerate(all_pubs):
        pub_id = pub.get('id', '')
        doi = pub.get('doi', '')
        title = pub.get('title', '')
        current_author = pub.get('first_author', '')
        
        # Skip if already has valid author in cache
        if pub_id in author_cache and author_cache[pub_id]:
            continue
        
        # Skip if already has valid author
        if current_author and current_author.lower() not in ['unknown', 'various', '']:
            author_cache[pub_id] = current_author
            continue
        
        safe_title = title[:40].encode('ascii', 'replace').decode() if title else 'Unknown'
        print(f"[{i+1}/{len(all_pubs)}] {safe_title}...")
        
        author = None
        source = None
        
        # Try CrossRef first
        author = get_first_author_from_crossref(doi)
        if author:
            source = 'CR'
            cr_found += 1
        else:
            # Try Semantic Scholar
            author = get_first_author_from_semantic_scholar(doi, title)
            if author:
                source = 'SS'
                ss_found += 1
        
        if author:
            author_cache[pub_id] = author
            updated += 1
            print(f"    [{source}] {author}")
        
        # Save every 20 updates
        if updated % 20 == 0 and updated > 0:
            save_yaml_file(cache_file, author_cache)
            print("    [Cache saved]")
        
        # Rate limit
        time.sleep(0.3)
    
    # Final save
    save_yaml_file(cache_file, author_cache)
    
    # Count results
    total_with_author = sum(1 for v in author_cache.values() if v)
    
    print("\n" + "=" * 60)
    print("AUTHOR FETCH COMPLETE")
    print("=" * 60)
    print(f"Updated: {updated}")
    print(f"  CrossRef: {cr_found}")
    print(f"  Semantic Scholar: {ss_found}")
    print(f"Total with authors: {total_with_author}")
    print(f"\nCache saved to: {cache_file}")
    print("\nRun 'python generate_website_data.py' to update the website")

if __name__ == '__main__':
    main()
