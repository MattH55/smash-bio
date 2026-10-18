"""
Optical Tweezers Metadata Data Classes

FAIR-compliant metadata schema for optical tweezers measurements of biological systems.
Based on Heller et al. 2025 Biophysical Journal (S0006-3495(25)00141-9)

Usage:
    from optical_tweezers_metadata import OpticalTweezersExperiment
    
    experiment = OpticalTweezersExperiment(
        experiment_id="EXP-001",
        hardware=Hardware(...),
        sample=Sample(...),
        ...
    )
    
    # Export to JSON
    experiment.to_json("experiment_metadata.json")
    
    # Export to YAML
    experiment.to_yaml("experiment_metadata.yaml")
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Union
from datetime import datetime
from enum import Enum
import json
import yaml


# ============================================================================
# ENUMS
# ============================================================================

class SystemType(str, Enum):
    COMMERCIAL = "commercial"
    CUSTOM = "custom"

class TrapConfiguration(str, Enum):
    SINGLE_TRAP_SURFACE = "single-trap-surface"
    SINGLE_TRAP_MICROPIPETTE = "single-trap-micropipette"
    DUAL_TRAP = "dual-trap"
    QUADRUPLE_TRAP = "quadruple-trap"

class BeadMaterial(str, Enum):
    POLYSTYRENE = "polystyrene"
    SILICA = "silica"
    MELAMINE = "melamine"
    OTHER = "other"

class SurfaceChemistry(str, Enum):
    STREPTAVIDIN = "streptavidin"
    ANTI_DIGOXIGENIN = "anti-digoxigenin"
    PROTEIN_G = "protein-G"
    CARBOXYL = "carboxyl"
    AMINE = "amine"
    PEG = "PEG"
    OTHER = "other"

class Immersion(str, Enum):
    WATER = "water"
    OIL = "oil"
    AIR = "air"

class DetectorType(str, Enum):
    QPD = "QPD"
    PSD = "PSD"
    CAMERA = "camera"
    OTHER = "other"

class FluorescenceCapability(str, Enum):
    NONE = "none"
    WIDE_FIELD = "wide-field"
    TIRF = "TIRF"
    CONFOCAL = "confocal"
    STED = "STED"
    SPINNING_DISK = "spinning-disk"

class CameraDetectorType(str, Enum):
    EMCCD = "EMCCD"
    SCMOS = "sCMOS"
    APD = "APD"
    PMT = "PMT"
    OTHER = "other"

class FlowControl(str, Enum):
    PRESSURE = "pressure"
    SYRINGE = "syringe"
    GRAVITY = "gravity"
    NONE = "none"

class BiologicalSystemType(str, Enum):
    DNA = "DNA"
    RNA = "RNA"
    PROTEIN = "protein"
    DNA_PROTEIN = "DNA-protein"
    CHROMATIN = "chromatin"
    CELL = "cell"
    MEMBRANE = "membrane"
    CYTOSKELETON = "cytoskeleton"
    MOTOR_PROTEIN = "motor-protein"
    PATHOGEN = "pathogen"
    OTHER = "other"

class NucleicAcidType(str, Enum):
    DSDNA = "dsDNA"
    SSDNA = "ssDNA"
    DSRNA = "dsRNA"
    SSRNA = "ssRNA"
    DNA_RNA_HYBRID = "DNA-RNA-hybrid"
    OTHER = "other"

class Topology(str, Enum):
    LINEAR = "linear"
    CIRCULAR = "circular"
    SUPERCOILED = "supercoiled"
    RELAXED = "relaxed"

class HandleType(str, Enum):
    DSDNA = "dsDNA"
    SSDNA = "ssDNA"
    PEG = "PEG"
    NONE = "none"
    OTHER = "other"

class AttachmentChemistry(str, Enum):
    BIOTIN = "biotin"
    DIGOXIGENIN = "digoxigenin"
    THIOL = "thiol"
    AMINE = "amine"
    CLICK_CHEMISTRY = "click-chemistry"
    OTHER = "other"

class ExpressionSystem(str, Enum):
    E_COLI = "E. coli"
    INSECT = "insect"
    MAMMALIAN = "mammalian"
    YEAST = "yeast"
    CELL_FREE = "cell-free"
    NATIVE = "native"
    OTHER = "other"

class ReconstitutionMethod(str, Enum):
    SALT_GRADIENT = "salt-gradient"
    CHAPERONE_ASSISTED = "chaperone-assisted"
    NATIVE = "native"
    OTHER = "other"

class OxygenScavengingSystem(str, Enum):
    GLUCOSE_OXIDASE_CATALASE = "glucose-oxidase-catalase"
    PCA_PCD = "PCA-PCD"
    ROXS = "ROXS"
    NONE = "none"
    OTHER = "other"

class OperationMode(str, Enum):
    PASSIVE = "passive"
    FORCE_CLAMP = "force-clamp"
    FORCE_RAMP = "force-ramp"
    FORCE_JUMP = "force-jump"
    POSITION_CLAMP = "position-clamp"
    ROTATION = "rotation"
    TORQUE_WRENCH = "torque-wrench"

class LoadingRateUnit(str, Enum):
    PN_PER_S = "pN/s"
    NM_PER_S = "nm/s"
    UM_PER_S = "μm/s"

class AcquisitionMode(str, Enum):
    CONTINUOUS = "continuous"
    TIME_LAPSE = "time-lapse"
    KYMOGRAPH = "kymograph"
    Z_STACK = "z-stack"

class CalibrationMethod(str, Enum):
    POWER_SPECTRUM = "power-spectrum"
    STEP_RESPONSE = "step-response"
    DRAG_FORCE = "drag-force"
    DNA_UNZIPPING = "DNA-unzipping"
    THERMAL_NOISE = "thermal-noise"
    OTHER = "other"

class FilteringMethod(str, Enum):
    NONE = "none"
    LOW_PASS = "low-pass"
    MEDIAN = "median"
    SAVITZKY_GOLAY = "Savitzky-Golay"
    OTHER = "other"

class FittingModel(str, Enum):
    WLC = "WLC"
    FJC = "FJC"
    EWLC = "eWLC"
    MARKO_SIGGIA = "Marko-Siggia"
    CUSTOM = "custom"
    OTHER = "other"


# ============================================================================
# HARDWARE DATA CLASSES
# ============================================================================

@dataclass
class Instrument:
    """Instrument information"""
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    system_type: Optional[SystemType] = None


@dataclass
class OpticalTraps:
    """Optical trap configuration"""
    number_of_traps: int = 2
    trap_configuration: Optional[TrapConfiguration] = None
    laser_wavelength_nm: float = 1064.0
    laser_power_mW: Optional[float] = None


@dataclass
class TrapStiffness:
    """Trap stiffness measurement"""
    value: float
    unit: str = "pN/nm"
    per_trap_values: Optional[List[float]] = None


@dataclass
class BeadDiameter:
    """Bead diameter specification"""
    value: float
    unit: str = "μm"


@dataclass
class BeadProperties:
    """Bead physical and chemical properties"""
    material: Optional[BeadMaterial] = None
    surface_chemistry: Optional[SurfaceChemistry] = None
    manufacturer: Optional[str] = None
    catalog_number: Optional[str] = None


@dataclass
class Objective:
    """Objective lens specifications"""
    numerical_aperture: float = 1.2
    magnification: Optional[float] = None
    immersion: Optional[Immersion] = None


@dataclass
class Detection:
    """Position and force detection system"""
    position_detector_type: Optional[DetectorType] = None
    position_resolution_nm: Optional[float] = None
    force_resolution_pN: Optional[float] = None
    data_acquisition_rate_Hz: Optional[float] = None


@dataclass
class Fluorescence:
    """Fluorescence microscopy configuration"""
    capability: FluorescenceCapability = FluorescenceCapability.NONE
    excitation_wavelengths_nm: Optional[List[float]] = None
    emission_filters: Optional[List[str]] = None
    detector_type: Optional[CameraDetectorType] = None


@dataclass
class Microfluidics:
    """Microfluidics system configuration"""
    enabled: bool = False
    number_of_channels: Optional[int] = None
    channel_configuration: Optional[str] = None
    flow_control: Optional[FlowControl] = None


@dataclass
class Hardware:
    """Complete hardware configuration"""
    trap_stiffness: TrapStiffness
    bead_diameter: BeadDiameter
    instrument: Optional[Instrument] = None
    optical_traps: Optional[OpticalTraps] = None
    bead_properties: Optional[BeadProperties] = None
    objective: Optional[Objective] = None
    detection: Optional[Detection] = None
    fluorescence: Optional[Fluorescence] = None
    microfluidics: Optional[Microfluidics] = None


# ============================================================================
# SAMPLE DATA CLASSES
# ============================================================================

@dataclass
class SampleSource:
    """Sample source information"""
    organism: Optional[str] = None
    cell_line: Optional[str] = None
    tissue: Optional[str] = None
    commercial_source: Optional[str] = None
    preparation_method: Optional[str] = None


@dataclass
class NucleicAcid:
    """DNA or RNA substrate information"""
    type: Optional[NucleicAcidType] = None
    name: Optional[str] = None
    sequence: Optional[str] = None
    sequence_reference: Optional[str] = None
    length_bp: Optional[int] = None
    length_kb: Optional[float] = None
    topology: Optional[Topology] = None
    modifications: Optional[List[str]] = None


@dataclass
class Handles:
    """Molecular handles for attachment"""
    type: Optional[HandleType] = None
    length_bp: Optional[int] = None
    length_nm: Optional[float] = None
    attachment_5prime: Optional[AttachmentChemistry] = None
    attachment_3prime: Optional[AttachmentChemistry] = None


@dataclass
class FluorescentLabel:
    """Fluorescent labeling information"""
    fluorophore: Optional[str] = None
    labeling_site: Optional[str] = None
    labeling_efficiency: Optional[float] = None


@dataclass
class Protein:
    """Protein sample information"""
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    uniprot_id: Optional[str] = None
    molecular_weight_kDa: Optional[float] = None
    oligomeric_state: Optional[str] = None
    expression_system: Optional[ExpressionSystem] = None
    purification_method: Optional[str] = None
    concentration_nM: Optional[float] = None
    concentration_uM: Optional[float] = None
    storage_conditions: Optional[str] = None
    mutations: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    fluorescent_label: Optional[FluorescentLabel] = None


@dataclass
class Chromatin:
    """Chromatin/nucleosome information"""
    nucleosome_source: Optional[str] = None
    histone_octamer_source: Optional[str] = None
    reconstitution_method: Optional[ReconstitutionMethod] = None
    nucleosome_density: Optional[str] = None
    histone_modifications: Optional[List[str]] = None
    labeled_histones: Optional[List[str]] = None


@dataclass
class Cell:
    """Cell sample information"""
    cell_type: Optional[str] = None
    cell_line: Optional[str] = None
    passage_number: Optional[int] = None
    culture_conditions: Optional[str] = None
    treatments: Optional[List[str]] = None


@dataclass
class Sample:
    """Complete sample information"""
    biological_system_type: BiologicalSystemType
    source: Optional[SampleSource] = None
    nucleic_acid: Optional[NucleicAcid] = None
    handles: Optional[Handles] = None
    protein: Optional[Protein] = None
    chromatin: Optional[Chromatin] = None
    cell: Optional[Cell] = None


# ============================================================================
# EXPERIMENTAL CONDITIONS DATA CLASSES
# ============================================================================

@dataclass
class Buffer:
    """Buffer composition"""
    name: Optional[str] = None
    composition: Optional[str] = None
    pH: Optional[float] = None
    ionic_strength_mM: Optional[float] = None


@dataclass
class Salt:
    """Salt concentration"""
    name: str
    concentration_mM: float


@dataclass
class Nucleotides:
    """Nucleotide concentrations"""
    ATP_mM: Optional[float] = None
    ATPgammaS_mM: Optional[float] = None
    ADP_mM: Optional[float] = None
    GTP_mM: Optional[float] = None
    dNTPs_mM: Optional[float] = None
    NTPs_mM: Optional[float] = None
    other: Optional[str] = None


@dataclass
class OxygenScavenging:
    """Oxygen scavenging system"""
    system: Optional[OxygenScavengingSystem] = None
    components: Optional[str] = None


@dataclass
class CrowdingAgent:
    """Crowding agent"""
    name: str
    concentration: str


@dataclass
class Additive:
    """Other buffer additive"""
    name: str
    concentration: str
    purpose: Optional[str] = None


@dataclass
class ExperimentalConditions:
    """Complete experimental conditions"""
    buffer: Optional[Buffer] = None
    salts: Optional[List[Salt]] = None
    temperature_C: Optional[float] = None
    nucleotides: Optional[Nucleotides] = None
    oxygen_scavenging: Optional[OxygenScavenging] = None
    surface_passivation: Optional[str] = None
    crowding_agents: Optional[List[CrowdingAgent]] = None
    other_additives: Optional[List[Additive]] = None


# ============================================================================
# MEASUREMENT DATA CLASSES
# ============================================================================

@dataclass
class ForceRange:
    """Force range specification"""
    minimum_pN: Optional[float] = None
    maximum_pN: Optional[float] = None


@dataclass
class LoadingRate:
    """Loading rate for force-ramp experiments"""
    value: float
    unit: LoadingRateUnit = LoadingRateUnit.PN_PER_S


@dataclass
class ExtensionRange:
    """Extension range specification"""
    minimum_nm: Optional[float] = None
    maximum_nm: Optional[float] = None


@dataclass
class FluorescenceImaging:
    """Fluorescence imaging parameters"""
    enabled: bool = False
    acquisition_mode: Optional[AcquisitionMode] = None
    frame_rate_Hz: Optional[float] = None
    exposure_time_ms: Optional[float] = None
    laser_power_uW: Optional[float] = None


@dataclass
class Measurements:
    """Measurement parameters"""
    operation_mode: OperationMode
    force_range: Optional[ForceRange] = None
    loading_rate: Optional[LoadingRate] = None
    clamp_force_pN: Optional[float] = None
    tension_pN: Optional[float] = None
    extension_range: Optional[ExtensionRange] = None
    measurement_duration_s: Optional[float] = None
    number_of_molecules: Optional[int] = None
    number_of_measurements_per_molecule: Optional[int] = None
    fluorescence_imaging: Optional[FluorescenceImaging] = None


# ============================================================================
# CALIBRATION DATA CLASSES
# ============================================================================

@dataclass
class Calibration:
    """Calibration information"""
    method: Optional[CalibrationMethod] = None
    calibration_bead_diameter_um: Optional[float] = None
    drag_coefficient_pN_s_nm: Optional[float] = None
    corner_frequency_Hz: Optional[float] = None
    calibration_temperature_C: Optional[float] = None
    calibration_buffer: Optional[str] = None
    position_sensitivity_nm_per_V: Optional[float] = None
    calibration_date: Optional[str] = None
    calibration_file: Optional[str] = None


# ============================================================================
# DATA PROCESSING DATA CLASSES
# ============================================================================

@dataclass
class AnalysisSoftware:
    """Analysis software information"""
    name: Optional[str] = None
    version: Optional[str] = None
    url: Optional[str] = None


@dataclass
class Filtering:
    """Data filtering parameters"""
    method: FilteringMethod = FilteringMethod.NONE
    cutoff_frequency_Hz: Optional[float] = None
    window_size: Optional[int] = None


@dataclass
class FittingModelParams:
    """Force-extension fitting model parameters"""
    model_name: Optional[FittingModel] = None
    persistence_length_nm: Optional[float] = None
    contour_length_nm: Optional[float] = None
    stretch_modulus_pN: Optional[float] = None


@dataclass
class StatisticalAnalysis:
    """Statistical analysis information"""
    methods: Optional[List[str]] = None
    confidence_level: Optional[float] = None
    sample_size: Optional[int] = None


@dataclass
class AnalysisScripts:
    """Analysis script references"""
    repository_url: Optional[str] = None
    script_files: Optional[List[str]] = None


@dataclass
class DataProcessing:
    """Data processing information"""
    analysis_software: Optional[AnalysisSoftware] = None
    filtering: Optional[Filtering] = None
    fitting_model: Optional[FittingModelParams] = None
    statistical_analysis: Optional[StatisticalAnalysis] = None
    analysis_scripts: Optional[AnalysisScripts] = None


# ============================================================================
# RESULTS DATA CLASSES
# ============================================================================

@dataclass
class Measurement:
    """Single measurement result"""
    parameter: str
    value: float
    error: Optional[float] = None
    unit: Optional[str] = None
    n: Optional[int] = None


@dataclass
class Results:
    """Experimental results"""
    primary_measurements: Optional[List[Measurement]] = None
    key_findings: Optional[List[str]] = None


# ============================================================================
# DATA FILES DATA CLASSES
# ============================================================================

@dataclass
class RawDataFile:
    """Raw data file information"""
    filename: str
    format: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ProcessedDataFile:
    """Processed data file information"""
    filename: str
    format: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Repository:
    """Data repository information"""
    name: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    accession_number: Optional[str] = None


@dataclass
class DataFiles:
    """Data file references"""
    raw_data: Optional[List[RawDataFile]] = None
    processed_data: Optional[List[ProcessedDataFile]] = None
    repository: Optional[Repository] = None


# ============================================================================
# CITATION DATA CLASS
# ============================================================================

@dataclass
class Citation:
    """Publication citation information"""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    pubmed_id: Optional[str] = None


# ============================================================================
# MAIN EXPERIMENT DATA CLASS
# ============================================================================

@dataclass
class OpticalTweezersExperiment:
    """
    Complete optical tweezers experiment metadata.
    
    This is the main class for storing FAIR-compliant metadata
    for optical tweezers measurements of biological systems.
    """
    experiment_id: str
    hardware: Hardware
    sample: Sample
    experimental_conditions: ExperimentalConditions
    measurements: Measurements
    
    # Optional fields
    metadata_version: str = "1.0.0"
    created_date: Optional[str] = None
    last_modified: Optional[str] = None
    citation: Optional[Citation] = None
    calibration: Optional[Calibration] = None
    data_processing: Optional[DataProcessing] = None
    results: Optional[Results] = None
    data_files: Optional[DataFiles] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Set default timestamps if not provided"""
        if self.created_date is None:
            self.created_date = datetime.now().isoformat()
        if self.last_modified is None:
            self.last_modified = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        def convert_value(v):
            if isinstance(v, Enum):
                return v.value
            elif hasattr(v, '__dataclass_fields__'):
                return {k: convert_value(val) for k, val in asdict(v).items() if val is not None}
            elif isinstance(v, list):
                return [convert_value(item) for item in v]
            return v
        
        return {k: convert_value(v) for k, v in asdict(self).items() if v is not None}
    
    def to_json(self, filepath: str = None, indent: int = 2) -> str:
        """Export to JSON format"""
        json_str = json.dumps(self.to_dict(), indent=indent, default=str)
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
        return json_str
    
    def to_yaml(self, filepath: str = None) -> str:
        """Export to YAML format"""
        yaml_str = yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)
        if filepath:
            with open(filepath, 'w') as f:
                f.write(yaml_str)
        return yaml_str
    
    @classmethod
    def from_json(cls, filepath: str) -> 'OpticalTweezersExperiment':
        """Load from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls._from_dict(data)
    
    @classmethod
    def from_yaml(cls, filepath: str) -> 'OpticalTweezersExperiment':
        """Load from YAML file"""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: dict) -> 'OpticalTweezersExperiment':
        """Create instance from dictionary (simplified - for full implementation add nested parsing)"""
        # This is a simplified version - full implementation would recursively
        # parse nested dataclasses
        return cls(**data)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_template() -> OpticalTweezersExperiment:
    """Create a template experiment with example values"""
    return OpticalTweezersExperiment(
        experiment_id="TEMPLATE-001",
        hardware=Hardware(
            trap_stiffness=TrapStiffness(value=0.3, unit="pN/nm"),
            bead_diameter=BeadDiameter(value=2.14, unit="μm"),
            instrument=Instrument(
                manufacturer="LUMICKS",
                model="C-Trap",
                system_type=SystemType.COMMERCIAL
            ),
            optical_traps=OpticalTraps(
                number_of_traps=2,
                trap_configuration=TrapConfiguration.DUAL_TRAP,
                laser_wavelength_nm=1064.0
            ),
            bead_properties=BeadProperties(
                material=BeadMaterial.POLYSTYRENE,
                surface_chemistry=SurfaceChemistry.STREPTAVIDIN
            ),
            fluorescence=Fluorescence(
                capability=FluorescenceCapability.CONFOCAL
            ),
            microfluidics=Microfluidics(
                enabled=True,
                number_of_channels=6
            )
        ),
        sample=Sample(
            biological_system_type=BiologicalSystemType.DNA_PROTEIN,
            nucleic_acid=NucleicAcid(
                type=NucleicAcidType.DSDNA,
                name="lambda DNA",
                length_kb=48.5,
                topology=Topology.LINEAR
            ),
            handles=Handles(
                type=HandleType.DSDNA,
                attachment_5prime=AttachmentChemistry.BIOTIN,
                attachment_3prime=AttachmentChemistry.DIGOXIGENIN
            )
        ),
        experimental_conditions=ExperimentalConditions(
            buffer=Buffer(
                name="Imaging buffer",
                pH=7.5
            ),
            temperature_C=25.0,
            salts=[
                Salt(name="KCl", concentration_mM=100.0)
            ]
        ),
        measurements=Measurements(
            operation_mode=OperationMode.FORCE_CLAMP,
            tension_pN=5.0,
            fluorescence_imaging=FluorescenceImaging(
                enabled=True,
                acquisition_mode=AcquisitionMode.KYMOGRAPH
            )
        )
    )


if __name__ == "__main__":
    # Create template and export examples
    template = create_template()
    
    # Export to JSON
    print("JSON output:")
    print(template.to_json())
    
    print("\n" + "="*60 + "\n")
    
    # Export to YAML
    print("YAML output:")
    print(template.to_yaml())
