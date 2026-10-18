#!/usr/bin/env python3
"""
Update Google Scholar citation counts for SMASH-BIO publications
Uses scholarly library for Google Scholar access
"""

import yaml
import json
import time
import sys
import io
from pathlib import Path

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from scholarly import scholarly
    HAS_SCHOLARLY = True
except ImportError:
    HAS_SCHOLARLY = False
    print("Error: scholarly library required. Install with: pip install scholarly")
    exit(1)

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

def lookup_citations_google_scholar(title, first_author=None, year=None):
    """Look up citation count from Google Scholar using scholarly"""
    try:
        # Clean and prepare query
        clean_title = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in title)
        query = clean_title[:100]
        
        if first_author and first_author != 'Unknown':
            author_name = first_author.split(',')[0].strip()
            query = f'"{query}" {author_name}'
        
        # Search Google Scholar
        search_query = scholarly.search_pubs(query)
        
        # Get first result
        result = next(search_query, None)
        if result:
            # Check title similarity
            result_title = result.get('bib', {}).get('title', '').lower()
            search_words = clean_title.lower().split()[:4]
            
            matches = sum(1 for word in search_words if word in result_title)
            if matches >= 2:  # At least 2 words match
                citations = result.get('num_citations', 0)
                return citations
        
        return 0
        
    except StopIteration:
        return 0
    except Exception as e:
        error_str = str(e)
        if 'CAPTCHA' in error_str or '429' in error_str:
            print("    Rate limited - waiting 60 seconds...")
            time.sleep(60)
            return None
        print(f"    Error: {error_str[:50]}")
        return 0

def main():
    base_path = Path('.')
    cache_file = base_path / 'citation_cache_gs.yaml'
    
    # Load existing cache
    citation_cache = load_yaml_file(cache_file) or {}
    print(f"Loaded {len(citation_cache)} existing cached citations")
    
    # Load data.js to get list of publications
    data_file = base_path / 'website' / 'js' / 'data.js'
    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract JSON
    content = content.split('const SMASH_DATA = ')[1].rstrip().rstrip(';')
    data = json.loads(content)
    
    all_pubs = data['publications'] + data['curated_studies']
    print(f"Total publications to check: {len(all_pubs)}")
    print("Using Google Scholar via scholarly library\n")
    
    # Update citations
    updated = 0
    skipped = 0
    
    for i, pub in enumerate(all_pubs):
        title = pub.get('title', '')
        pub_id = pub.get('id', '')
        
        if not title or title == 'Untitled':
            continue
        
        # Skip if already cached with non-zero value
        if pub_id in citation_cache and citation_cache[pub_id] > 0:
            skipped += 1
            continue
        
        # Display progress
        safe_title = title[:45].encode('ascii', 'replace').decode()
        print(f"[{i+1}/{len(all_pubs)}] {safe_title}...")
        
        citations = lookup_citations_google_scholar(
            title, 
            pub.get('first_author'),
            pub.get('year')
        )
        
        if citations is not None:
            citation_cache[pub_id] = citations
            if citations > 0:
                print(f"    Found: {citations} citations")
            updated += 1
        
        # Save cache every 10 updates
        if updated % 10 == 0 and updated > 0:
            save_yaml_file(cache_file, citation_cache)
            print("    [Cache saved]")
        
        # Rate limit for Google Scholar
        time.sleep(3)
    
    # Final save
    save_yaml_file(cache_file, citation_cache)
    
    print(f"\n{'='*50}")
    print(f"Updated: {updated} publications")
    print(f"Skipped (cached): {skipped}")
    print(f"With citations: {sum(1 for v in citation_cache.values() if v > 0)}")
    print(f"Cache saved to {cache_file}")
    
    # Copy to main cache
    main_cache = base_path / 'citation_cache.yaml'
    save_yaml_file(main_cache, citation_cache)
    print(f"Also saved to {main_cache}")
    
    # Show top cited
    top = sorted(citation_cache.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\nTop 10 cited:")
    for pub_id, count in top:
        print(f"  {count}: {pub_id}")

if __name__ == '__main__':
    main()
