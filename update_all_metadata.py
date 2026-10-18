#!/usr/bin/env python3
"""
Update ALL publications with author names and citation counts.
Uses CrossRef as primary source with Semantic Scholar fallback.
Ensures no 'Unknown' or 'Various' authors, and all have citation counts.
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
    except:
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

def get_from_crossref(doi):
    """Get citation count AND first author from CrossRef"""
    doi = clean_doi(doi)
    if not doi:
        return None, None
    
    try:
        url = f"https://api.crossref.org/works/{doi}"
        headers = {'User-Agent': 'SMASH-BIO/1.0 (mailto:contact@smash-bio.com)'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', {})
            
            # Citations
            citations = message.get('is-referenced-by-count', 0)
            
            # First author
            authors = message.get('author', [])
            first_author = None
            if authors and len(authors) > 0:
                first = authors[0]
                family = first.get('family', '')
                given = first.get('given', '')
                if family:
                    if given:
                        first_author = f"{family}, {given[0]}."
                    else:
                        first_author = family
            
            return citations, first_author
    except Exception as e:
        pass
    
    return None, None

def get_from_semantic_scholar(doi, title=None):
    """Get citation count AND first author from Semantic Scholar"""
    doi = clean_doi(doi)
    
    if doi:
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
            params = {'fields': 'citationCount,authors'}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                citations = data.get('citationCount')
                
                authors = data.get('authors', [])
                first_author = None
                if authors and len(authors) > 0:
                    name = authors[0].get('name', '')
                    if name:
                        parts = name.split()
                        if len(parts) >= 2:
                            first_author = f"{parts[-1]}, {parts[0][0]}."
                        else:
                            first_author = name
                
                return citations, first_author
        except:
            pass
    
    # Try title search
    if title:
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {'query': title[:100], 'fields': 'citationCount,authors', 'limit': 1}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                if papers:
                    citations = papers[0].get('citationCount')
                    authors = papers[0].get('authors', [])
                    first_author = None
                    if authors and len(authors) > 0:
                        name = authors[0].get('name', '')
                        if name:
                            parts = name.split()
                            if len(parts) >= 2:
                                first_author = f"{parts[-1]}, {parts[0][0]}."
                            else:
                                first_author = name
                    return citations, first_author
        except:
            pass
    
    return None, None

def main():
    base_path = Path('.')
    
    # Load caches
    citation_cache_file = base_path / 'citation_cache.yaml'
    author_cache_file = base_path / 'author_cache.yaml'
    
    citation_cache = load_yaml_file(citation_cache_file) or {}
    author_cache = load_yaml_file(author_cache_file) or {}
    
    print(f"Starting caches: {len(citation_cache)} citations, {len(author_cache)} authors")
    
    # Load data.js
    data_file = base_path / 'website' / 'js' / 'data.js'
    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.split('const SMASH_DATA = ')[1]
    end_idx = content.rfind('};')
    if end_idx > 0:
        content = content[:end_idx+1]
    
    data = json.loads(content)
    all_pubs = data['publications'] + data['curated_studies']
    
    # Find entries needing updates
    needs_citation = []
    needs_author = []
    
    for pub in all_pubs:
        pub_id = pub.get('id', '')
        
        # Check citation
        if pub_id not in citation_cache or citation_cache.get(pub_id) is None:
            needs_citation.append(pub)
        
        # Check author
        current_author = author_cache.get(pub_id) or pub.get('first_author', '')
        if not current_author or current_author.lower() in ['unknown', 'various', '']:
            needs_author.append(pub)
    
    print(f"\nTotal publications: {len(all_pubs)}")
    print(f"Need citation update: {len(needs_citation)}")
    print(f"Need author update: {len(needs_author)}")
    print("-" * 60)
    
    # Combine into one list - entries needing any update
    needs_update = {}
    for pub in needs_citation + needs_author:
        needs_update[pub.get('id')] = pub
    
    updated = 0
    cr_count = 0
    ss_count = 0
    
    for i, (pub_id, pub) in enumerate(needs_update.items()):
        doi = pub.get('doi', '')
        title = pub.get('title', '')
        
        safe_title = title[:40].encode('ascii', 'replace').decode() if title else 'Unknown'
        print(f"[{i+1}/{len(needs_update)}] {safe_title}...")
        
        # Try CrossRef first
        citations, author = get_from_crossref(doi)
        source = 'CR' if citations is not None or author else None
        
        # Fallback to Semantic Scholar
        if citations is None:
            ss_cit, ss_auth = get_from_semantic_scholar(doi, title)
            if ss_cit is not None:
                citations = ss_cit
                source = 'SS'
            if ss_auth and not author:
                author = ss_auth
                source = source or 'SS'
        
        if author and not get_from_crossref(doi)[1]:
            # Also try SS for author if CR didn't have it
            _, ss_auth = get_from_semantic_scholar(doi, title)
            if ss_auth:
                author = ss_auth
        
        # Update caches
        if citations is not None:
            citation_cache[pub_id] = citations
            if source:
                cr_count += 1 if 'CR' in source else 0
                ss_count += 1 if source == 'SS' else 0
        
        if author:
            author_cache[pub_id] = author
        
        if citations is not None or author:
            updated += 1
            status = []
            if citations is not None:
                status.append(f"{citations} cit")
            if author:
                status.append(author)
            print(f"    [{source}] {', '.join(status)}")
        
        # Save periodically
        if updated % 25 == 0 and updated > 0:
            save_yaml_file(citation_cache_file, citation_cache)
            save_yaml_file(author_cache_file, author_cache)
            print("    [Caches saved]")
        
        time.sleep(0.3)
    
    # Final save
    save_yaml_file(citation_cache_file, citation_cache)
    save_yaml_file(author_cache_file, author_cache)
    
    # Summary
    total_with_citations = sum(1 for v in citation_cache.values() if v is not None and v >= 0)
    total_with_authors = sum(1 for v in author_cache.values() if v)
    
    print("\n" + "=" * 60)
    print("UPDATE COMPLETE")
    print("=" * 60)
    print(f"Updated: {updated}")
    print(f"Total with citations: {total_with_citations}/{len(all_pubs)}")
    print(f"Total with authors: {total_with_authors}/{len(all_pubs)}")
    print(f"\nRun 'python generate_website_data.py' to update website")

if __name__ == '__main__':
    main()
