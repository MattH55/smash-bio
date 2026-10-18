#!/usr/bin/env python3
"""
Classify all SMASH-BIO publications into the 4 experiment types from Table 3:
1. Unfolding experiments (nucleic acid or protein)
2. DNA-protein interactions
3. Force generation by cytoskeletal filaments or motors
4. Rheology (cell mechanics)
"""

import json
import yaml
from pathlib import Path
from collections import defaultdict

def classify_experiment_type(title, abstract=''):
    """
    Classify a publication into one of the 4 Table 3 experiment types.
    Returns: 'unfolding', 'dna_protein', 'force_generation', 'rheology', or 'other'
    """
    text = (str(title) + ' ' + str(abstract)).lower()
    
    # Keywords for each category (priority order matters)
    
    # 1. Force generation by cytoskeletal filaments or motors
    force_gen_keywords = [
        'kinesin', 'myosin', 'dynein', 'motor protein', 'molecular motor',
        'actin filament', 'microtubule', 'cytoskeleton', 'cytoskeletal',
        'spindle', 'mitotic', 'filament sliding', 'motility assay',
        'step size', 'stall force', 'motor ensemble', 'stepping',
        'processive', 'mdia1', 'formin', 'protrusion', 'contraction',
        'actin polymerization', 'tubulin'
    ]
    
    # 2. Rheology / cell mechanics
    rheology_keywords = [
        'rheology', 'microrheology', 'viscoelastic', 'cell mechanics',
        'cell stiffness', 'mechanical properties', 'cell deformation',
        'red blood cell', 'erythrocyte', 'membrane mechanics',
        "young's modulus", 'elastic modulus', 'cortical stiffness',
        'keratinocyte', 'cell trapping', 'cell manipulation',
        'mechanosensing', 'mechanotransduction', 'traction force'
    ]
    
    # 3. DNA-protein interactions
    dna_protein_keywords = [
        'dna-protein', 'protein-dna', 'helicase', 'polymerase', 
        'topoisomerase', 'nuclease', 'ligase', 'recombinase',
        'chromatin', 'nucleosome', 'histone', 'transcription factor',
        'dna repair', 'replication', 'dna binding', 'protein binding',
        'condensin', 'cohesin', 'smc', 'rad51', 'recbcd', 'uvrd',
        'xpd', 'crispr', 'cas9', 'cas12', 'dna gyrase', 'rna polymerase',
        'primosome', 'primase', 'dna scanning', 'sliding clamp',
        'dnaa', 'dna-bound', 'nucleoprotein', 'fancd2'
    ]
    
    # 4. Unfolding experiments (nucleic acid or protein)
    unfolding_keywords = [
        'unfolding', 'folding', 'force-extension', 'force extension',
        'stretching', 'pulling', 'mechanical unfolding', 'protein unfolding',
        'rna unfolding', 'dna hairpin', 'hairpin', 'g-quadruplex',
        'riboswitch', 'aptamer', 'secondary structure', 'tertiary structure',
        'mechanical fingerprint', 'force spectroscopy', 'single-molecule stretching',
        'worm-like chain', 'wlc', 'contour length', 'persistence length',
        'force-induced', 'mechanical stability', 'unzipping'
    ]
    
    # Score each category
    scores = {
        'force_generation': sum(1 for kw in force_gen_keywords if kw in text),
        'rheology': sum(1 for kw in rheology_keywords if kw in text),
        'dna_protein': sum(1 for kw in dna_protein_keywords if kw in text),
        'unfolding': sum(1 for kw in unfolding_keywords if kw in text)
    }
    
    # Get category with highest score
    max_score = max(scores.values())
    if max_score == 0:
        return 'other'
    
    # Return category with highest score
    for cat, score in scores.items():
        if score == max_score:
            return cat
    
    return 'other'

def main():
    base_path = Path('.')
    
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
    
    # Classify all publications
    categories = defaultdict(list)
    
    for pub in all_pubs:
        title = pub.get('title', '')
        abstract = pub.get('abstract', '')
        exp_type = classify_experiment_type(title, abstract)
        
        categories[exp_type].append({
            'id': pub.get('id', ''),
            'title': title,
            'doi': pub.get('doi', ''),
            'year': pub.get('year'),
            'first_author': pub.get('first_author', ''),
            'citations': pub.get('citations', 0)
        })
    
    # Print summary
    print("=" * 70)
    print("EXPERIMENT TYPE CLASSIFICATION (Table 3 Categories)")
    print("=" * 70)
    
    type_names = {
        'unfolding': '1. Unfolding experiments (nucleic acid or protein)',
        'dna_protein': '2. DNA-protein interactions',
        'force_generation': '3. Force generation by cytoskeletal filaments/motors',
        'rheology': '4. Rheology (cell mechanics)',
        'other': '5. Other/Mixed'
    }
    
    for exp_type in ['unfolding', 'dna_protein', 'force_generation', 'rheology', 'other']:
        pubs = categories[exp_type]
        print(f"\n{type_names[exp_type]}: {len(pubs)} publications")
        print("-" * 60)
        
        # Show top 5 by citations
        sorted_pubs = sorted(pubs, key=lambda x: x.get('citations') or 0, reverse=True)
        for i, p in enumerate(sorted_pubs[:5]):
            title_short = p['title'][:50] + '...' if len(p['title']) > 50 else p['title']
            print(f"  [{p.get('citations', 0):3d} cit] {title_short}")
    
    # Save classification
    output = {
        'summary': {cat: len(pubs) for cat, pubs in categories.items()},
        'classifications': {cat: pubs for cat, pubs in categories.items()}
    }
    
    with open('experiment_classifications.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False)
    
    print(f"\n\nSaved classifications to: experiment_classifications.yaml")
    print(f"\nTotal: {len(all_pubs)} publications classified")

if __name__ == '__main__':
    main()
