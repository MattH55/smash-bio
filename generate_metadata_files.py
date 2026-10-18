"""
Generate YAML Metadata Files for LUMICKS Publications

This script generates individual YAML metadata files for all documented 
optical tweezers publications from the LUMICKS_Publications_Metadata.md
and the LUMICKS publications website.

Run: python generate_metadata_files.py
"""

import os
import yaml
from datetime import datetime

# Create output directory
OUTPUT_DIR = "publications_metadata"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Publication data extracted from documentation and web searches
PUBLICATIONS = [
    {
        "id": "study_01_TopII_decatenation_Cutts_2025",
        "experiment_id": "TOPII-2025-001",
        "title": "Substrate accessibility regulation of human TopIIα decatenation by cohesin",
        "authors": ["Cutts, E.E.", "Saravanan, S.", "Girvan, P.", "Ambrose, B.", "Fisher, G.L.M.", "Rueda, D.S.", "Aragon, L."],
        "journal": "Nature Communications",
        "year": 2025,
        "doi": "10.1038/s41467-025-62505-3",
        "system_type": "DNA-protein",
        "protein": "Topoisomerase IIα",
        "dna_type": "Lambda DNA braids",
        "traps": 4,
        "force_range": "5-28 pN"
    },
    {
        "id": "study_02_chromatin_remodelers_Carcamo_2024",
        "experiment_id": "REMOD-2024-001",
        "title": "Dynamic 1D Search and Processive Nucleosome Translocations by RSC and ISW2",
        "authors": ["Carcamo, C.", "Ha, T."],
        "journal": "eLife",
        "year": 2024,
        "doi": "10.7554/eLife.91433",
        "system_type": "chromatin",
        "protein": "RSC, ISW2, SWR1",
        "dna_type": "Lambda DNA with nucleosome arrays",
        "traps": 2,
        "force_range": "5 pN tension"
    },
    {
        "id": "study_03_Pol_II_transcription_Wang_2025",
        "experiment_id": "POLII-2025-001",
        "title": "Kinetic control of mammalian transcription elongation",
        "authors": ["Wang, Y."],
        "journal": "Nature Structural & Molecular Biology",
        "year": 2025,
        "doi": "10.1038/s41594-025-01707-1",
        "system_type": "DNA-protein",
        "protein": "RNA Polymerase II, elongation factors",
        "dna_type": "Synthetic nucleic acid scaffold",
        "traps": 2,
        "force_range": "5 pN tension"
    },
    {
        "id": "study_04_LEM2_BAF_vonAppen_2025",
        "experiment_id": "LEM2-2025-001",
        "title": "A self-enforcing protein-DNA surface hydrogel safeguards nuclear integrity",
        "authors": ["von Appen, A."],
        "journal": "Nature",
        "year": 2025,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "LEM2, BAF",
        "dna_type": "dsDNA",
        "traps": 2,
        "force_range": "up to 65 pN (melting)"
    },
    {
        "id": "study_05_membrane_tension_Yan_2024",
        "experiment_id": "MEMB-2024-001",
        "title": "Cell protrusions and contractions generate long-range membrane tension propagation",
        "authors": ["Yan, S."],
        "journal": "Cell",
        "year": 2024,
        "doi": "",
        "system_type": "cell",
        "protein": "Actin cortex",
        "dna_type": "N/A - live cells",
        "traps": 2,
        "force_range": "~15 pN tether force"
    },
    {
        "id": "study_06_smCFFM_Liu",
        "experiment_id": "SMCFFM-001",
        "title": "Single-molecule correlative fluorescence-force microscopy studies",
        "authors": ["Liu, S."],
        "journal": "Various",
        "year": 2024,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "CMG helicase, PRC2",
        "dna_type": "Long DNA/chromatin",
        "traps": 2,
        "force_range": "5-20 pN"
    },
    {
        "id": "study_07_FANCD2_Rueda_2024",
        "experiment_id": "FANCD2-2024-001",
        "title": "FANCD2-FANCI surveys DNA and recognizes double- to single-stranded junctions",
        "authors": ["Passmore, L.A.", "Rueda, D.S."],
        "journal": "Nature",
        "year": 2024,
        "doi": "10.1038/s41586-024-07770-w",
        "system_type": "DNA-protein",
        "protein": "FANCD2-FANCI",
        "dna_type": "Lambda DNA with ss-dsDNA junctions",
        "traps": 2,
        "force_range": "5-10 pN"
    },
    {
        "id": "study_08_ORC_MCM_Dekker_2023",
        "experiment_id": "ORC-2023-001",
        "title": "A chromatinized origin reduces mobility of ORC and MCM through interactions and spatial constraint",
        "authors": ["Dekker, N.", "Diffley, J.F.X."],
        "journal": "Nature Communications",
        "year": 2023,
        "doi": "10.1038/s41467-023-42524-8",
        "system_type": "chromatin",
        "protein": "ORC, MCM",
        "dna_type": "10.4 kbp DNA with ARS1",
        "traps": 2,
        "force_range": "5-10 pN"
    },
    {
        "id": "study_09_SMC_complexes_Aragon_2023",
        "experiment_id": "SMC-2023-001",
        "title": "New Insights in Chromosome Organization: Single Molecule Analysis of Eukaryotic SMC Complexes",
        "authors": ["Aragon, L."],
        "journal": "Various",
        "year": 2023,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "Cohesin, Smc5/6, Condensin",
        "dna_type": "dsDNA, ssDNA, hybrid substrates",
        "traps": 2,
        "force_range": "5-20 pN"
    },
    {
        "id": "study_10_FUS_phase_separation_Banerjee_2022",
        "experiment_id": "FUS-2022-001",
        "title": "Decoding the onset of Amyotrophic Lateral Sclerosis (ALS): LLPS of IDPs",
        "authors": ["Banerjee, P."],
        "journal": "Various",
        "year": 2022,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "FUS",
        "dna_type": "Lambda DNA",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_11_ATL_NER_Tessmer_2020",
        "experiment_id": "ATL-2020-001",
        "title": "Alkyltransferase-like protein clusters scan DNA rapidly over long distances and recruit NER to alkyl-DNA lesions",
        "authors": ["Rill, N.", "Tessmer, I."],
        "journal": "PNAS",
        "year": 2020,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "ATL, UvrA",
        "dna_type": "DNA with alkyl lesions",
        "traps": 2,
        "force_range": "5-10 pN"
    },
    {
        "id": "study_12_ParABS_MorenoHerrero_2022",
        "experiment_id": "PAR-2022-001",
        "title": "Insights into Bacterial DNA Condensation and chromosome organization",
        "authors": ["Moreno-Herrero, F."],
        "journal": "Various",
        "year": 2022,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "ParB, SMC-ScpAB",
        "dna_type": "DNA with parS sites",
        "traps": 2,
        "force_range": "5-10 pN"
    },
    {
        "id": "study_13_Cas12a_Montoya_2021",
        "experiment_id": "CAS12-2021-001",
        "title": "Mechanics of CRISPR-Cas12a and engineered variants on λ-DNA",
        "authors": ["Paul, B.", "Montoya, G."],
        "journal": "Nucleic Acids Research",
        "year": 2021,
        "doi": "10.1093/nar/gkac348",
        "system_type": "DNA-protein",
        "protein": "Cas12a",
        "dna_type": "Lambda DNA",
        "traps": 2,
        "force_range": "10-50 pN"
    },
    {
        "id": "study_14_nuclear_extracts_VanHouten_2023",
        "experiment_id": "SMADNE-2023-001",
        "title": "Single-molecule analysis of cancer DNA-protein interactions from nuclear extracts",
        "authors": ["Van Houten, B."],
        "journal": "Various",
        "year": 2023,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "OGG1, PARP1, TDG, UV-DDB",
        "dna_type": "Lambda DNA (undamaged, nicked, damaged)",
        "traps": 2,
        "force_range": "5-10 pN"
    },
    {
        "id": "study_15_RPA_migration_Pangeni_2024",
        "experiment_id": "RPA-2024-001",
        "title": "Rapid Long-distance Migration of RPA on Single Stranded DNA",
        "authors": ["Pangeni, S.", "Ha, T."],
        "journal": "Journal of Molecular Biology",
        "year": 2024,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "RPA",
        "dna_type": "Lambda ssDNA",
        "traps": 2,
        "force_range": "3 pN"
    },
    {
        "id": "study_16_RecBCD_Fazio_2024",
        "experiment_id": "RECB-2024-001",
        "title": "E. coli RecB Nuclease Domain Regulates RecBCD Helicase Activity",
        "authors": ["Fazio, N.", "Lohman, T.M."],
        "journal": "Journal of Molecular Biology",
        "year": 2024,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "RecBCD",
        "dna_type": "~20 kbp DNA",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_17_NDF_FACT_Li_2025",
        "experiment_id": "NDF-2025-001",
        "title": "Phase-separated NDF-FACT condensates facilitate transcription elongation on chromatin",
        "authors": ["Li, Z."],
        "journal": "Nature Cell Biology",
        "year": 2025,
        "doi": "10.1038/s41556-025-01778-8",
        "system_type": "chromatin",
        "protein": "NDF, FACT, Pol II",
        "dna_type": "Chromatin templates",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_18_Shu_RAD51_2024",
        "experiment_id": "SHU-2024-001",
        "title": "The human Shu complex promotes RAD51 activity by modulating RPA dynamics on ssDNA",
        "authors": ["Various"],
        "journal": "Nature Communications",
        "year": 2024,
        "doi": "10.1038/s41467-024-51595-0",
        "system_type": "DNA-protein",
        "protein": "Shu complex, RAD51, RPA",
        "dna_type": "ssDNA",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_19_DNA_Pol_exchange_2024",
        "experiment_id": "POLX-2024-001",
        "title": "Mapping fast DNA polymerase exchange during replication",
        "authors": ["Various"],
        "journal": "Nature Communications",
        "year": 2024,
        "doi": "10.1038/s41467-024-49612-3",
        "system_type": "DNA-protein",
        "protein": "DNA polymerase",
        "dna_type": "Replication forks",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_20_kinetochore_Barford_2024",
        "experiment_id": "KINET-2024-001",
        "title": "Kinetochores grip microtubules with directionally asymmetric grip behavior",
        "authors": ["Barford, D."],
        "journal": "Science",
        "year": 2024,
        "doi": "",
        "system_type": "cytoskeleton",
        "protein": "Ndc80, DAM1",
        "dna_type": "N/A - microtubules",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_21_HELQ_2023",
        "experiment_id": "HELQ-2023-001",
        "title": "Helicase HELQ: Molecular Characters Fit for DSB Repair Function",
        "authors": ["Various"],
        "journal": "Molecular Cell",
        "year": 2023,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "HELQ, RAD51, RPA",
        "dna_type": "ssDNA, dsDNA",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_22_trigger_factor_2025",
        "experiment_id": "TF-2025-001",
        "title": "Trigger factor accelerates nascent chain compaction and folding",
        "authors": ["Various"],
        "journal": "PNAS",
        "year": 2025,
        "doi": "10.1073/pnas.2422678122",
        "system_type": "protein",
        "protein": "Trigger factor, nascent chains",
        "dna_type": "N/A - protein folding",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_23_cell_mechanics_2025",
        "experiment_id": "CELL-2025-001",
        "title": "Robust quantification of cellular mechanics using optical tweezers",
        "authors": ["Various"],
        "journal": "Biophysical Reports",
        "year": 2025,
        "doi": "",
        "system_type": "cell",
        "protein": "N/A",
        "dna_type": "N/A - live cells",
        "traps": 2,
        "force_range": "piconewton range"
    },
    # New 2025 publications from LUMICKS website
    {
        "id": "study_24_CRISPR_TypeI_Fv_Klein_2025",
        "experiment_id": "CRISPR-2025-001",
        "title": "Type I-Fv and engineered type IV-A1 CRISPR–Cas effectors facilitate genome reduction in Escherichia coli",
        "authors": ["Klein, N."],
        "journal": "Nucleic Acids Research",
        "year": 2025,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "CRISPR-Cas effectors",
        "dna_type": "DNA targets",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_25_PARP1_chromatin_Schaich_2025",
        "experiment_id": "PARP1-2025-001",
        "title": "Nucleosome unwrapping and PARP1 allostery drive affinities for chromatin and DNA breaks",
        "authors": ["Schaich, M.A."],
        "journal": "Nature Communications",
        "year": 2025,
        "doi": "",
        "system_type": "chromatin",
        "protein": "PARP1",
        "dna_type": "Chromatin with nucleosomes",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_26_HSV1_helicase_Yu_2025",
        "experiment_id": "HSV-2025-001",
        "title": "Mechanisms of HSV-1 helicase-primase inhibition and replication fork complex assembly",
        "authors": ["Yu, Z."],
        "journal": "Cell",
        "year": 2025,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "HSV-1 helicase-primase",
        "dna_type": "Replication fork DNA",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_27_DNA_ligase_Nagpal_2025",
        "experiment_id": "LIG3-2025-001",
        "title": "The zinc finger of DNA ligase 3α binds to nucleosomes via an arginine anchor",
        "authors": ["Nagpal, A."],
        "journal": "Nature Communications",
        "year": 2025,
        "doi": "",
        "system_type": "chromatin",
        "protein": "DNA ligase 3α",
        "dna_type": "Nucleosomal DNA",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_28_H4K16_chromatin_Nitsch_2025",
        "experiment_id": "H4K16-2025-001",
        "title": "H4K16 acylations destabilize chromatin architecture and facilitate transcriptional response",
        "authors": ["Nitsch, S."],
        "journal": "Molecular Cell",
        "year": 2025,
        "doi": "",
        "system_type": "chromatin",
        "protein": "Histones H4K16 variants",
        "dna_type": "Chromatin fibers",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_29_NapA_Schumacher_2025",
        "experiment_id": "NAPA-2025-001",
        "title": "Structural Studies on the M. tuberculosis Nucleoid-associated-Protein, NapA, Indicates DNA Bridging Mechanism",
        "authors": ["Schumacher, M.A."],
        "journal": "Journal of Molecular Biology",
        "year": 2025,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "NapA",
        "dna_type": "DNA",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_30_kinesin_autoinhibition_Bensel_2025",
        "experiment_id": "KIN-2025-001",
        "title": "Kinesin-1 autoinhibition tunes cargo transport by motor ensembles",
        "authors": ["Bensel, B.M."],
        "journal": "Biophysical Journal",
        "year": 2025,
        "doi": "",
        "system_type": "motor-protein",
        "protein": "Kinesin-1",
        "dna_type": "N/A - microtubules",
        "traps": 2,
        "force_range": "5-8 pN stall"
    },
    {
        "id": "study_31_condensin_TopII_Tsubota_2025",
        "experiment_id": "COND-2025-001",
        "title": "Functional interplay between condensin I and topoisomerase IIα in single-molecule DNA compaction",
        "authors": ["Tsubota, Y."],
        "journal": "Nature Communications",
        "year": 2025,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "Condensin I, TopIIα",
        "dna_type": "DNA",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_32_GPMV_membrane_Yosibash_2025",
        "experiment_id": "GPMV-2025-001",
        "title": "A Versatile GPMV-Imaging Platform for Quantitative Analysis of Receptor Binding and Membrane Fusion",
        "authors": ["Yosibash, I."],
        "journal": "Biophysical Journal",
        "year": 2025,
        "doi": "",
        "system_type": "membrane",
        "protein": "Membrane receptors",
        "dna_type": "N/A - membranes",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_33_Elongator_tubulin_Planelles_2025",
        "experiment_id": "ELONG-2025-001",
        "title": "Elongator is a microtubule polymerase selective for polyglutamylated tubulin",
        "authors": ["Planelles-Herrero, V.J."],
        "journal": "Cell",
        "year": 2025,
        "doi": "",
        "system_type": "cytoskeleton",
        "protein": "Elongator",
        "dna_type": "N/A - microtubules",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_34_protein_labeling_Silbermann_2025",
        "experiment_id": "LABEL-2025-001",
        "title": "One-pot dual protein labeling for simultaneous mechanical and fluorescent readouts in optical tweezers",
        "authors": ["Silbermann, L.M."],
        "journal": "Protein Science",
        "year": 2025,
        "doi": "",
        "system_type": "protein",
        "protein": "Various (methodology)",
        "dna_type": "N/A - methodology",
        "traps": 2,
        "force_range": "variable"
    },
    {
        "id": "study_35_G_quadruplex_Bao_2025",
        "experiment_id": "GQUAD-2025-001",
        "title": "Coexistence of G-Quadruplex and i-Motif Within a DNA Duplex is Tolerated by a PCBP2-Assisted Replisome",
        "authors": ["Bao, Y."],
        "journal": "Angewandte Chemie",
        "year": 2025,
        "doi": "",
        "system_type": "DNA-protein",
        "protein": "PCBP2, replisome",
        "dna_type": "G-quadruplex DNA",
        "traps": 2,
        "force_range": "variable"
    },
]


def generate_yaml_template(pub):
    """Generate YAML metadata for a publication."""
    
    template = {
        "experiment_id": pub["experiment_id"],
        "metadata_version": "1.0.0",
        "created_date": f"{pub['year']}-01-01T00:00:00",
        "last_modified": datetime.now().isoformat(),
        
        "citation": {
            "title": pub["title"],
            "authors": pub["authors"],
            "journal": pub["journal"],
            "year": pub["year"],
            "volume": "",
            "pages": "",
            "doi": pub.get("doi", ""),
            "pubmed_id": ""
        },
        
        "hardware": {
            "instrument": {
                "manufacturer": "LUMICKS",
                "model": "C-Trap",
                "system_type": "commercial"
            },
            "optical_traps": {
                "number_of_traps": pub.get("traps", 2),
                "trap_configuration": "quadruple-trap" if pub.get("traps", 2) == 4 else "dual-trap",
                "laser_wavelength_nm": 1064.0,
                "laser_power_mW": None
            },
            "trap_stiffness": {
                "value": 0.3,
                "unit": "pN/nm"
            },
            "bead_diameter": {
                "value": 2.14,
                "unit": "μm"
            },
            "bead_properties": {
                "material": "polystyrene",
                "surface_chemistry": "streptavidin",
                "manufacturer": "",
                "catalog_number": ""
            },
            "fluorescence": {
                "capability": "confocal",
                "excitation_wavelengths_nm": [],
                "detector_type": "APD"
            },
            "microfluidics": {
                "enabled": True,
                "number_of_channels": 6,
                "flow_control": "pressure"
            }
        },
        
        "sample": {
            "biological_system_type": pub["system_type"],
            "source": {
                "organism": "",
                "preparation_method": ""
            },
            "nucleic_acid": {
                "type": "dsDNA" if "DNA" in pub.get("dna_type", "") else "",
                "name": pub.get("dna_type", ""),
                "length_kb": 48.5 if "Lambda" in pub.get("dna_type", "") else None,
                "topology": "linear"
            },
            "protein": {
                "name": pub.get("protein", ""),
                "abbreviation": "",
                "expression_system": "",
                "concentration_nM": None
            }
        },
        
        "experimental_conditions": {
            "buffer": {
                "name": "Assay buffer",
                "pH": 7.5
            },
            "temperature_C": 25.0
        },
        
        "measurements": {
            "operation_mode": "force-clamp",
            "force_range": {
                "minimum_pN": None,
                "maximum_pN": None
            },
            "tension_pN": None,
            "fluorescence_imaging": {
                "enabled": True,
                "acquisition_mode": "kymograph"
            }
        },
        
        "results": {
            "primary_measurements": [],
            "key_findings": []
        },
        
        "notes": f"Force range: {pub.get('force_range', 'Not specified')}"
    }
    
    return template


def main():
    """Generate all YAML metadata files."""
    
    print(f"Generating {len(PUBLICATIONS)} YAML metadata files...")
    
    for pub in PUBLICATIONS:
        filename = f"{pub['id']}.yaml"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        metadata = generate_yaml_template(pub)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        print(f"  Created: {filename}")
    
    print(f"\nDone! Generated {len(PUBLICATIONS)} files in '{OUTPUT_DIR}/' directory.")
    
    # Also create an index file
    index_path = os.path.join(OUTPUT_DIR, "_index.yaml")
    index = {
        "title": "LUMICKS Optical Tweezers Publications Metadata Index",
        "generated": datetime.now().isoformat(),
        "total_publications": len(PUBLICATIONS),
        "publications": [
            {
                "id": p["id"],
                "title": p["title"],
                "year": p["year"],
                "journal": p["journal"],
                "system_type": p["system_type"]
            }
            for p in sorted(PUBLICATIONS, key=lambda x: (-x["year"], x["title"]))
        ]
    }
    
    with open(index_path, 'w', encoding='utf-8') as f:
        yaml.dump(index, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print(f"Created index file: _index.yaml")


if __name__ == "__main__":
    main()
