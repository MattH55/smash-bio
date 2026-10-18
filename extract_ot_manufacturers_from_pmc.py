#!/usr/bin/env python3
"""
Extract optical tweezers manufacturer information from PubMed Central full-text articles.
This script:
1. Parses NBIB file to extract PMIDs
2. Queries PubMed Central API to get full-text XML for open-access articles
3. Searches for manufacturer information in Methods sections
4. Outputs results to a CSV file
"""

import re
import time
import csv
import requests
from xml.etree import ElementTree as ET
from pathlib import Path

# Common optical tweezers manufacturers to search for
MANUFACTURERS = [
    'LUMICKS',
    'Bruker',
    'Thermofisher',
    'ThermoFisher',
    'Thermo Fisher',
    'JPK',
    'Thorlabs',
    'Elliot Scientific',
    'IMPETUX',
    'Hamamatsu',
    'Zeiss',
    'Nikon',
    'Olympus',
]

# Patterns for custom-built systems
CUSTOM_PATTERNS = [
    r'custom[- ]built',
    r'home[- ]built',
    r'in[- ]house',
    r'lab[- ]built',
    r'custom[- ]made',
    r'locally built',
    r'self[- ]built',
]

def parse_nbib_file(nbib_path):
    """Extract PMIDs from NBIB file."""
    pmids = []
    
    with open(nbib_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by record separator
    records = content.split('\n\n')
    
    for record in records:
        # Find PMID line
        pmid_match = re.search(r'^PMID-\s*(\d+)', record, re.MULTILINE)
        if pmid_match:
            pmids.append(pmid_match.group(1))
    
    return pmids

def check_pmc_availability(pmid):
    """Check if article is available in PubMed Central."""
    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={pmid}&format=json"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'records' in data and len(data['records']) > 0:
                record = data['records'][0]
                if 'pmcid' in record:
                    return record['pmcid']
    except Exception as e:
        print(f"Error checking PMC availability for PMID {pmid}: {e}")
    
    return None

def fetch_pmc_fulltext(pmcid):
    """Fetch full-text XML from PubMed Central."""
    # Remove PMC prefix if present
    pmc_number = pmcid.replace('PMC', '')
    url = f"https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi?verb=GetRecord&identifier=oai:pubmedcentral.nih.gov:{pmc_number}&metadataPrefix=pmc"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"Error fetching full-text for {pmcid}: {e}")
    
    return None

def extract_methods_section(xml_content):
    """Extract Methods/Materials and Methods section from PMC XML."""
    try:
        root = ET.fromstring(xml_content)
        
        # Find all section elements
        methods_text = []
        
        # Common section titles for methods
        method_titles = [
            'methods', 'materials and methods', 'experimental procedures',
            'materials & methods', 'methodology', 'experimental methods',
            'experimental section', 'materials', 'procedures'
        ]
        
        # Search for sections with these titles
        for sec in root.iter('sec'):
            title_elem = sec.find('.//title')
            if title_elem is not None and title_elem.text:
                title_lower = title_elem.text.lower()
                if any(method_title in title_lower for method_title in method_titles):
                    # Extract all text from this section
                    for elem in sec.iter():
                        if elem.text:
                            methods_text.append(elem.text)
                        if elem.tail:
                            methods_text.append(elem.tail)
        
        return ' '.join(methods_text)
    
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return ""

def search_for_manufacturers(text):
    """Search for manufacturer mentions in text."""
    found_manufacturers = []
    
    # Search for known manufacturers
    for manufacturer in MANUFACTURERS:
        pattern = re.compile(r'\b' + re.escape(manufacturer) + r'\b', re.IGNORECASE)
        if pattern.search(text):
            found_manufacturers.append(manufacturer)
    
    # Search for custom-built patterns
    for pattern_str in CUSTOM_PATTERNS:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        if pattern.search(text):
            found_manufacturers.append('Custom-built')
            break
    
    # Search for specific product names
    product_patterns = [
        (r'C-Trap', 'LUMICKS C-Trap'),
        (r'm-Trap', 'LUMICKS m-Trap'),
        (r'z-Movi', 'LUMICKS z-Movi'),
        (r'NanoWizard', 'JPK NanoWizard'),
        (r'NanoTracker', 'JPK NanoTracker'),
    ]
    
    for pattern_str, product_name in product_patterns:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        if pattern.search(text):
            found_manufacturers.append(product_name)
    
    return list(set(found_manufacturers))  # Remove duplicates

def extract_context(text, manufacturer, context_chars=200):
    """Extract context around manufacturer mention."""
    pattern = re.compile(r'\b' + re.escape(manufacturer) + r'\b', re.IGNORECASE)
    match = pattern.search(text)
    
    if match:
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        context = text[start:end]
        return context.strip()
    
    return ""

def main():
    # Input file path
    nbib_file = r"C:\Users\matth\Downloads\pubmed-opticaltwe-set_experimental_bio (1).nbib"
    
    # Output file
    output_file = r"C:\Users\matth\OneDrive\Documents\PhD\SMASH-BIO\ot_manufacturers_results.csv"
    
    print("=" * 80)
    print("Optical Tweezers Manufacturer Extraction Tool")
    print("=" * 80)
    
    # Parse NBIB file
    print(f"\n1. Parsing NBIB file: {nbib_file}")
    pmids = parse_nbib_file(nbib_file)
    print(f"   Found {len(pmids)} PMIDs")
    
    # Process each PMID
    results = []
    
    for i, pmid in enumerate(pmids, 1):
        print(f"\n2. Processing PMID {pmid} ({i}/{len(pmids)})")
        
        # Check PMC availability
        print(f"   Checking PMC availability...")
        pmcid = check_pmc_availability(pmid)
        
        if not pmcid:
            print(f"   ❌ Not available in PMC (not open access)")
            results.append({
                'PMID': pmid,
                'PMCID': 'N/A',
                'Status': 'Not in PMC',
                'Manufacturers': '',
                'Context': ''
            })
            continue
        
        print(f"   ✓ Found PMCID: {pmcid}")
        
        # Fetch full-text
        print(f"   Fetching full-text XML...")
        xml_content = fetch_pmc_fulltext(pmcid)
        
        if not xml_content:
            print(f"   ❌ Could not fetch full-text")
            results.append({
                'PMID': pmid,
                'PMCID': pmcid,
                'Status': 'Fetch failed',
                'Manufacturers': '',
                'Context': ''
            })
            continue
        
        # Extract methods section
        print(f"   Extracting Methods section...")
        methods_text = extract_methods_section(xml_content)
        
        if not methods_text:
            print(f"   ⚠ No Methods section found")
            results.append({
                'PMID': pmid,
                'PMCID': pmcid,
                'Status': 'No Methods section',
                'Manufacturers': '',
                'Context': ''
            })
            continue
        
        # Search for manufacturers
        print(f"   Searching for manufacturers...")
        manufacturers = search_for_manufacturers(methods_text)
        
        if manufacturers:
            print(f"   ✓ Found: {', '.join(manufacturers)}")
            # Get context for first manufacturer
            context = extract_context(methods_text, manufacturers[0])
            
            results.append({
                'PMID': pmid,
                'PMCID': pmcid,
                'Status': 'Success',
                'Manufacturers': '; '.join(manufacturers),
                'Context': context
            })
        else:
            print(f"   ⚠ No manufacturers found in Methods section")
            results.append({
                'PMID': pmid,
                'PMCID': pmcid,
                'Status': 'No manufacturer found',
                'Manufacturers': '',
                'Context': ''
            })
        
        # Be nice to NCBI servers
        time.sleep(0.5)
    
    # Write results to CSV
    print(f"\n3. Writing results to: {output_file}")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['PMID', 'PMCID', 'Status', 'Manufacturers', 'Context'])
        writer.writeheader()
        writer.writerows(results)
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total = len(results)
    in_pmc = sum(1 for r in results if r['PMCID'] != 'N/A')
    found_manufacturers = sum(1 for r in results if r['Manufacturers'])
    
    print(f"Total articles: {total}")
    print(f"Available in PMC: {in_pmc} ({in_pmc/total*100:.1f}%)")
    print(f"Manufacturers found: {found_manufacturers} ({found_manufacturers/total*100:.1f}%)")
    
    # Count manufacturer types
    manufacturer_counts = {}
    for result in results:
        if result['Manufacturers']:
            for mfr in result['Manufacturers'].split('; '):
                manufacturer_counts[mfr] = manufacturer_counts.get(mfr, 0) + 1
    
    if manufacturer_counts:
        print("\nManufacturer breakdown:")
        for mfr, count in sorted(manufacturer_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {mfr}: {count}")
    
    print(f"\nResults saved to: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
