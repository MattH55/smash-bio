import re
from collections import defaultdict

def parse_nbib_file(filepath):
    """Parse NBIB file and extract publication entries."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by PMID entries
    entries = re.split(r'\n(?=PMID-)', content)
    
    publications = []
    for entry in entries:
        if not entry.strip():
            continue
            
        pub = {}
        
        # Extract PMID
        pmid_match = re.search(r'PMID-\s*(\d+)', entry)
        if pmid_match:
            pub['pmid'] = pmid_match.group(1)
        
        # Extract Title
        title_match = re.search(r'TI\s*-\s*(.+?)(?=\n[A-Z]{2,4}\s*-|\n\n)', entry, re.DOTALL)
        if title_match:
            pub['title'] = ' '.join(title_match.group(1).split())
        
        # Extract Abstract
        abstract_match = re.search(r'AB\s*-\s*(.+?)(?=\n[A-Z]{2,4}\s*-|\n\n)', entry, re.DOTALL)
        if abstract_match:
            pub['abstract'] = ' '.join(abstract_match.group(1).split())
        
        # Extract Publication Type
        pub_types = re.findall(r'PT\s*-\s*(.+)', entry)
        pub['pub_types'] = pub_types
        
        # Extract full entry for reference
        pub['full_entry'] = entry
        
        publications.append(pub)
    
    return publications

def is_experimental_study(pub):
    """Determine if publication is an experimental study."""
    pub_types = pub.get('pub_types', [])
    
    # Exclude reviews, preprints, and non-experimental types
    exclude_types = ['Review', 'Preprint', 'Journal Article, Review']
    
    for pt in pub_types:
        if any(excl.lower() in pt.lower() for excl in exclude_types):
            # Check if it's ONLY a review
            if len(pub_types) == 1 or (len(pub_types) == 2 and 'Journal Article' in pub_types):
                return False
    
    # Look for experimental indicators in abstract
    abstract = pub.get('abstract', '').lower()
    title = pub.get('title', '').lower()
    
    experimental_keywords = [
        'we measured', 'we demonstrate', 'we show', 'we observe',
        'experimental', 'single-molecule', 'optical tweezers',
        'we used optical tweezers', 'using optical tweezers',
        'we employed', 'we performed', 'we conducted'
    ]
    
    has_experimental = any(keyword in abstract or keyword in title for keyword in experimental_keywords)
    
    return has_experimental

def extract_manufacturer(pub):
    """Extract optical tweezers manufacturer from publication."""
    abstract = pub.get('abstract', '')
    title = pub.get('title', '')
    full_text = abstract + ' ' + title
    
    manufacturers = []
    
    # Known optical tweezers manufacturers
    manufacturer_patterns = {
        'LUMICKS': r'\b(LUMICKS|Lumicks)\b',
        'JPK Instruments': r'\b(JPK\s+Instruments?|JPK)\b',
        'Thorlabs': r'\b(Thorlabs)\b',
        'Elliot Scientific': r'\b(Elliot\s+Scientific)\b',
        'IMPETUX': r'\b(IMPETUX)\b',
        'Aresis': r'\b(Aresis)\b',
        'BioNanoTools': r'\b(BioNanoTools)\b',
        'Tweezers': r'\b(C-Trap|AFS-1|miniTweezers)\b',  # Specific product names
    }
    
    # Search for manufacturers
    for manufacturer, pattern in manufacturer_patterns.items():
        if re.search(pattern, full_text, re.IGNORECASE):
            manufacturers.append(manufacturer)
    
    # Look for custom-built systems
    custom_patterns = [
        r'custom[- ]built',
        r'home[- ]built',
        r'in[- ]house',
        r'lab[- ]built',
        r'self[- ]built',
        r'locally built',
        r'custom optical tweezers',
        r'custom setup'
    ]
    
    for pattern in custom_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            if 'Custom-built' not in manufacturers:
                manufacturers.append('Custom-built')
            break
    
    # Look for commercial system mentions
    commercial_patterns = [
        r'commercial optical tweezers',
        r'commercial system',
        r'commercially available'
    ]
    
    for pattern in commercial_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            if not manufacturers:
                manufacturers.append('Commercial (unspecified)')
            break
    
    return manufacturers

def main():
    filepath = r'C:\Users\matth\OneDrive\Documents\PhD\SMASH-BIO\pubmed-opticaltwe-set.nbib'
    
    print("Parsing NBIB file...")
    publications = parse_nbib_file(filepath)
    print(f"Total publications found: {len(publications)}\n")
    
    # Filter experimental studies
    experimental_pubs = [pub for pub in publications if is_experimental_study(pub)]
    print(f"Experimental studies identified: {len(experimental_pubs)}\n")
    
    # Extract manufacturers
    results = []
    manufacturer_counts = defaultdict(int)
    
    for pub in experimental_pubs:
        manufacturers = extract_manufacturer(pub)
        
        if manufacturers:
            for mfr in manufacturers:
                manufacturer_counts[mfr] += 1
            
            results.append({
                'pmid': pub.get('pmid', 'Unknown'),
                'title': pub.get('title', 'No title'),
                'manufacturers': manufacturers
            })
    
    # Print results
    print("="*80)
    print("EXPERIMENTAL STUDIES WITH IDENTIFIED MANUFACTURERS")
    print("="*80)
    print()
    
    for i, result in enumerate(results, 1):
        print(f"{i}. PMID: {result['pmid']}")
        print(f"   Title: {result['title'][:100]}...")
        print(f"   Manufacturer(s): {', '.join(result['manufacturers'])}")
        print()
    
    print("="*80)
    print("MANUFACTURER SUMMARY")
    print("="*80)
    print()
    print(f"Total experimental studies with manufacturer info: {len(results)}")
    print(f"Total experimental studies analyzed: {len(experimental_pubs)}")
    print(f"Percentage with manufacturer info: {len(results)/len(experimental_pubs)*100:.1f}%")
    print()
    print("Manufacturer counts:")
    for mfr, count in sorted(manufacturer_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {mfr}: {count}")
    
    # Save detailed results to file
    output_file = r'C:\Users\matth\OneDrive\Documents\PhD\SMASH-BIO\ot_manufacturers_results.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("OPTICAL TWEEZERS MANUFACTURER EXTRACTION RESULTS\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Total publications in file: {len(publications)}\n")
        f.write(f"Experimental studies identified: {len(experimental_pubs)}\n")
        f.write(f"Studies with manufacturer information: {len(results)}\n\n")
        
        f.write("="*80 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("="*80 + "\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"{i}. PMID: {result['pmid']}\n")
            f.write(f"   Title: {result['title']}\n")
            f.write(f"   Manufacturer(s): {', '.join(result['manufacturers'])}\n")
            f.write("\n")
        
        f.write("="*80 + "\n")
        f.write("MANUFACTURER SUMMARY\n")
        f.write("="*80 + "\n\n")
        
        for mfr, count in sorted(manufacturer_counts.items(), key=lambda x: x[1], reverse=True):
            f.write(f"{mfr}: {count}\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("EXPERIMENTAL STUDIES WITHOUT MANUFACTURER INFO\n")
        f.write("="*80 + "\n\n")
        
        pubs_without_mfr = [pub for pub in experimental_pubs 
                           if pub.get('pmid') not in [r['pmid'] for r in results]]
        
        for pub in pubs_without_mfr[:20]:  # Show first 20
            f.write(f"PMID: {pub.get('pmid', 'Unknown')}\n")
            f.write(f"Title: {pub.get('title', 'No title')}\n\n")
    
    print(f"\nDetailed results saved to: {output_file}")

if __name__ == "__main__":
    main()
