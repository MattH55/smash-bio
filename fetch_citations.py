#!/usr/bin/env python3
"""
Fetch citation counts using Semantic Scholar API (more reliable than Google Scholar)
"""

import yaml
import json
import time
import requests
from pathlib import Path

def load_yaml_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except:
        return None

def get_semantic_scholar_citations(title, year=None):
    """Look up citation count from Semantic Scholar API"""
    try:
        # Search by title
        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': title[:200],
            'fields': 'citationCount,title,year',
            'limit': 5
        }
        
        response = requests.get(search_url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            papers = data.get('data', [])
            
            # Find best match
            for paper in papers:
                paper_title = paper.get('title', '').lower()
                # Check if titles are similar
                if any(word in paper_title for word in title.lower().split()[:4]):
                    return paper.get('citationCount', 0)
        
        return 0
    except Exception as e:
        print(f"  Error: {e}")
        return 0

def main():
    base_path = Path('.')
    cache_file = base_path / 'citation_cache.yaml'
    
    # Load data.js
    data_file = base_path / 'website' / 'js' / 'data.js'
    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse JSON
    content = content.split('const SMASH_DATA = ')[1].rstrip().rstrip(';')
    data = json.loads(content)
    
    all_pubs = data['publications'] + data['curated_studies']
    citation_cache = load_yaml_file(cache_file) or {}
    
    print(f"Fetching citations for {len(all_pubs)} publications...")
    print("Using Semantic Scholar API")
    
    updated = 0
    for i, pub in enumerate(all_pubs):
        title = pub.get('title', '')
        pub_id = pub.get('id', '')
        
        if not title or title == 'Untitled':
            continue
        
        # Skip if already cached
        if pub_id in citation_cache and citation_cache[pub_id] > 0:
            print(f"[{i+1}/{len(all_pubs)}] {title[:40]}... (cached: {citation_cache[pub_id]})")
            continue
        
        print(f"[{i+1}/{len(all_pubs)}] {title[:50]}...")
        
        citations = get_semantic_scholar_citations(title, pub.get('year'))
        citation_cache[pub_id] = citations
        
        if citations > 0:
            print(f"    Found: {citations} citations")
            updated += 1
        
        # Save periodically
        if (i + 1) % 10 == 0:
            with open(cache_file, 'w') as f:
                yaml.dump(citation_cache, f)
        
        time.sleep(0.5)  # Rate limit
    
    # Final save
    with open(cache_file, 'w') as f:
        yaml.dump(citation_cache, f)
    
    print(f"\nUpdated {updated} citation counts")
    print(f"Cache saved to {cache_file}")
    
    # Count how many have citations
    with_citations = sum(1 for v in citation_cache.values() if v > 0)
    print(f"Publications with citations: {with_citations}")
    
    # Show top cited
    top = sorted(citation_cache.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\nTop 10 cited:")
    for pub_id, count in top:
        print(f"  {count}: {pub_id}")

if __name__ == '__main__':
    main()
