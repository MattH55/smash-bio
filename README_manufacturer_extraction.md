# Optical Tweezers Manufacturer Extraction

## Overview
This tool extracts optical tweezers manufacturer information from experimental publications by accessing full-text articles from PubMed Central (PMC).

## Files Created
- `extract_ot_manufacturers_from_pmc.py` - Main extraction script
- `ot_manufacturers_results.csv` - Output file with results

## How to Run

### Prerequisites
1. **Install Python** (if not already installed):
   - Download from https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"

2. **Install required packages**:
   ```bash
   pip install requests
   ```

### Running the Script
```bash
python extract_ot_manufacturers_from_pmc.py
```

## What the Script Does

1. **Parses NBIB file**: Extracts all PMIDs from the input file
2. **Checks PMC availability**: Determines which articles are open-access in PubMed Central
3. **Downloads full-text**: Retrieves XML full-text for available articles
4. **Extracts Methods sections**: Parses the Methods/Materials and Methods sections
5. **Searches for manufacturers**: Looks for:
   - Known manufacturers: LUMICKS, Bruker, Thermofisher, JPK, Thorlabs, etc.
   - Specific products: C-Trap, m-Trap, z-Movi, NanoWizard, etc.
   - Custom-built systems: "custom-built", "home-built", "in-house", etc.
6. **Outputs results**: Creates CSV with manufacturer info and context

## Output Format

The script generates `ot_manufacturers_results.csv` with columns:
- **PMID**: PubMed ID
- **PMCID**: PubMed Central ID (if available)
- **Status**: Processing status (Success, Not in PMC, No manufacturer found, etc.)
- **Manufacturers**: List of manufacturers found (semicolon-separated)
- **Context**: Text excerpt showing manufacturer mention

## Expected Results

- **Open-access rate**: Typically 30-50% of articles are available in PMC
- **Manufacturer detection**: Depends on how explicitly authors report equipment
- **Processing time**: ~0.5 seconds per article (to respect NCBI rate limits)

## Limitations

1. **Only open-access articles**: Can only analyze articles freely available in PMC
2. **Text-based search**: May miss manufacturers mentioned in figures or tables
3. **Naming variations**: Some manufacturers may be mentioned with different spellings
4. **Incomplete reporting**: Many papers don't explicitly state manufacturer names

## Customization

To add more manufacturers, edit the `MANUFACTURERS` list in the script:
```python
MANUFACTURERS = [
    'LUMICKS',
    'Bruker',
    'YourManufacturer',
    # Add more here
]
```

## Notes

- The script respects NCBI rate limits (0.5 second delay between requests)
- No API key required for basic usage (3 requests/second limit)
- For faster processing, you can register for an NCBI API key
