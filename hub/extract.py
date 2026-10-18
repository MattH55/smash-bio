"""Regex extractors for Table 3 fields, results and data-availability statements.

Every extractor returns values together with a short snippet so the record keeps
auditable provenance. Extracted values are flagged as automatic (unverified).
"""
import re

NUM = r"(\d+(?:[.,]\d+)?)"
RANGE = NUM + r"(?:\s*(?:-|–|—|to|and)\s*" + NUM + r")?"
PM = r"(?:\s*(?:±|\+/-|\+-)\s*" + NUM + r")?"
SP = r"[\s   ]*"
MU = r"(?:µ|μ|u|micro)"


def _num(s):
    return float(s.replace(",", ".")) if s is not None else None


def snip(text, m, w=90):
    a, b = max(0, m.start() - w), min(len(text), m.end() + w)
    return ("…" if a else "") + text[a:b].replace("\n", " ").strip() + ("…" if b < len(text) else "")


def window_find(text, anchor_rx, value_rx, w=140, conv=None, valid=None, maxhits=6):
    """Find value_rx within +/- w chars of anchor_rx. Returns list of (value, unit, snippet, extra)."""
    out = []
    for am in anchor_rx.finditer(text):
        a, b = max(0, am.start() - w), min(len(text), am.end() + w)
        seg = text[a:b]
        for vm in value_rx.finditer(seg):
            v = conv(vm) if conv else vm
            if v is None or (valid and not valid(v)):
                continue
            out.append((v, snip(text, re.compile(re.escape(vm.group(0))).search(text, a) or am)))
            break
        if len(out) >= maxhits:
            break
    return out


def most_common(vals):
    if not vals:
        return None
    from collections import Counter
    c = Counter(round(v, 4) if isinstance(v, float) else v for v, _ in vals)
    best = c.most_common(1)[0][0]
    for v, s in vals:
        if (round(v, 4) if isinstance(v, float) else v) == best:
            return v, s


# ---------------------------------------------------------------- hardware
R_LASER = re.compile(r"laser|trapping beam|trap(ping)? light|Nd:?YAG|Nd:?YVO4|fib(er|re) laser|diode", re.I)
R_WAVELENGTH = re.compile(r"\b(1064|1070|1047|1053|1083|1085|1030|1550|975|980|976|946|915|852|850|845|830|808|785|780|532)" + SP + r"nm\b")
R_POWER = re.compile(NUM + SP + r"(m?W)\b")
R_STIFF_ANCHOR = re.compile(r"stiffness|spring constant|trap strength|\bκ\b|kappa", re.I)
R_STIFF = re.compile(NUM + PM + SP + r"(pN" + SP + r"(?:/|·|\s|per\s)" + SP + r"nm(?:\s*(?:-1|−1|⁻¹))?|pN\s*nm\s*(?:-1|−1|⁻¹)|pN/μm|pN/um|pN" + SP + "/" + SP + MU + "m|fN/nm|N/m|mN/m)", re.I)
R_BEAD_ANCHOR = re.compile(r"\bbeads?\b|microspheres?|particles?|Dynabeads|spheres?", re.I)
R_BEAD = re.compile(NUM + PM + SP + r"(" + MU + r"m|nm)" + r"(?:[\s-]*(?:diameter|diam\.|-?sized|in diameter|radius))?", re.I)
R_ACQ_ANCHOR = re.compile(r"sampl\w*|acqui\w*|recorded|digiti[sz]ed|data rate|frame rate|frames per second|bandwidth|read out", re.I)
R_FREQ = re.compile(NUM + SP + r"(MHz|kHz|Hz|fps|frames/s)\b")
R_FILTER_ANCHOR = re.compile(r"(low[- ]pass|anti-?alias\w*|filter\w*|downsampl\w*|averag\w* (to|down to))", re.I)
R_TEMP = re.compile(NUM + PM + SP + r"(°C|° C|ºC|oC|K)\b(?!\w)")
R_TEMP_ANCHOR = re.compile(r"temperature|room temperature|at\s*$|°C", re.I)
R_NA = re.compile(r"(?:numerical aperture|\bNA)\s*(?:of|=|:)?\s*(0\.\d+|1\.\d+)", re.I)
R_MAG = re.compile(r"\b(40|60|63|100|150)\s*[x×X]\b")
R_IMMERSION = re.compile(r"\b(water|oil|glycerol|silicone)[- ]immersion\b", re.I)
R_OBJ_MAKE = re.compile(r"\b(Nikon|Olympus|Zeiss|Leica|Evident)\b[^.;]{0,60}\bobjective", re.I)

VENDORS = [
    ("LUMICKS", r"\bLUMICKS\b|\bC-?Trap\b|\bm-Trap\b|\bq-Trap\b|\bAFS G\d\b|\bBluelake\b|\bz-Movi\b"),
    ("JPK / Bruker", r"\bJPK\b|\bNanoTracker\b|\bForceRobot\b|\bNanoWizard\b|\bCellHesion\b"),
    ("Bruker", r"\bBruker\b|\bMultiMode\b|\bDimension (Icon|FastScan)\b|\bBioScope\b|\bPicoForce\b|\bVeeco\b|\bDigital Instruments\b"),
    ("Asylum Research / Oxford Instruments", r"\bAsylum\b|\bMFP-?3D\b|\bCypher\b|\bOxford Instruments\b"),
    ("Picotwist", r"\bPicoTwist\b|\bPicotwist\b"),
    ("Depixus", r"\bDepixus\b|\bMagna One\b|\bSIMDEQ\b"),
    ("Impetux", r"\bImpetux\b|\bSENSOCELL\b|\bLightAce\b"),
    ("Elliot Scientific", r"\bElliot Scientific\b|\bE3500\b|\bE4100\b"),
    ("Thorlabs", r"\bThorlabs\b.{0,40}(tweez|OTKB|trap)|\bOTKB\b"),
    ("Aresis", r"\bAresis\b|\bTweez 2\d\d\b"),
    ("Arryx / Haemonetics", r"\bArryx\b|\bBioRyx\b"),
    ("Molecular Devices / Zeiss PALM", r"\bPALM MicroTweezers\b|\bPALM MicroBeam\b"),
    ("Nanosurf", r"\bNanosurf\b|\bFluidFM\b|\bCytosurge\b"),
    ("Park Systems", r"\bPark Systems\b|\bNX10\b|\bNX-Bio\b"),
    ("NT-MDT", r"\bNT-MDT\b|\bNTEGRA\b"),
    ("Agilent / Keysight", r"\bAgilent (5500|5400)\b|\bKeysight\b.{0,20}AFM|\bPicoPlus\b|\bMolecular Imaging\b"),
    ("Luigs & Neumann", r"\bLuigs\b"),
    ("Mad City Labs", r"\bMad City Labs\b"),
    ("Physik Instrumente", r"\bPhysik Instrumente\b|\bPI P-\d+"),
    ("Nanotracker", r"$^"),
]
VENDOR_RX = [(n, re.compile(p, re.I)) for n, p in VENDORS]
MODEL_RX = re.compile(r"\b(C-?Trap(?: G2)?|m-Trap|q-Trap|Q-Trap|AFS G[12]|NanoTracker ?2?|ForceRobot ?\d*|NanoWizard ?\w*|MFP-?3D(?:-BIO)?|Cypher(?: ES| VRS)?|MultiMode ?\d*|Dimension \w+|PicoTwist|Magna One|SENSOCELL|E3500|OTKB|Tweez 2\d\d|BioRyx ?\d*|FluidFM|CellHesion ?\d*)\b", re.I)
CUSTOM_RX = re.compile(r"\b(custom[- ](built|made|designed)|home[- ]?(built|made)|in-house (built|constructed|developed)|self-built|built in[- ]house|described previously|as previously described)\b", re.I)

DETECTION = [("QPD", r"quadrant (photo)?diode|\bQPD\b|quadrant detector"), ("PSD", r"position[- ]sensitive (photo)?detector|\bPSD\b(?! of)"),
             ("BFP_interferometry", r"back[- ]focal[- ]plane"), ("camera_EMCCD", r"\bEM-?CCD\b"), ("camera_sCMOS", r"\bsCMOS\b"),
             ("camera_CMOS", r"\bCMOS\b(?! sensor)|high[- ]speed camera"), ("camera_CCD", r"\bCCD\b"),
             ("cantilever_deflection", r"cantilever deflection|optical lever"), ("ionic_current", r"ionic current")]
DETECTION_RX = [(n, re.compile(p, re.I)) for n, p in DETECTION]
STEER = [("AOD", r"acousto-?optic(al)? deflector|\bAODs?\b"), ("EOD", r"electro-?optic(al)? deflector|\bEODs?\b"),
         ("piezo_mirror", r"piezo(electric)?[- ](tip[- ]tilt )?mirror|steerable mirror|piezo-?actuated mirror"),
         ("galvo_mirror", r"galvanometer|galvo mirror"), ("SLM", r"spatial light modulator|\bSLM\b"),
         ("piezo_stage", r"piezo(electric)?[- ]?(nano)?stage|nanopositioning stage")]
STEER_RX = [(n, re.compile(p, re.I)) for n, p in STEER]
CALIB = [("power_spectrum_passive", r"power spectr(um|al density|a)|\bPSD (fit|analysis|calibration)|Lorentzian|corner frequency"),
         ("power_spectrum_active", r"active calibration|oscillat\w+ (the )?(stage|trap).{0,40}calibrat"),
         ("equipartition", r"equipartition"), ("stokes_drag", r"stokes(')? (drag|law|friction)|viscous drag calibration|drag force calibration"),
         ("thermal_noise_cantilever", r"thermal (noise|fluctuation|tune) (method|spectrum)?|thermal tune"),
         ("sader", r"\bSader\b"), ("allan_variance", r"Allan variance"), ("dna_force_extension_reference", r"overstretching plateau.{0,40}calibrat"),
         ("step_response", r"step response")]
CALIB_RX = [(n, re.compile(p, re.I)) for n, p in CALIB]
MODALITY = [("confocal_fluorescence", r"confocal|C-?Trap|kymograph"), ("TIRF", r"\bTIRF\b|total internal reflection"),
            ("smFRET", r"\bsmFRET\b|single-molecule FRET|\bFRET\b"), ("STED", r"\bSTED\b"), ("IRM", r"interference reflection"),
            ("widefield_fluorescence", r"(wide-?field|epi-?)fluorescence"), ("Raman", r"\bRaman\b"),
            ("electrophysiology", r"patch[- ]clamp|electrophysiolog"), ("high_speed_AFM_imaging", r"high-speed AFM"),
            ("label_free_scattering", r"label-free|iSCAT|interferometric scattering")]
MODALITY_RX = [(n, re.compile(p, re.I)) for n, p in MODALITY]

GEOMETRY = [
    ("four_trap_braid", r"quadruple[- ]trap|four[- ]trap|q-?trap\b|DNA braids?"),
    ("three_bead_assay", r"three[- ]bead|3-bead"),
    ("dumbbell_dual_trap", r"dumbbell|dual[- ]trap|dual-beam|two (optical )?traps|double[- ]trap|C-?Trap|between two (beads|microspheres)"),
    ("single_trap_surface_tether", r"(single[- ]trap|single[- ]beam).{0,60}(surface|coverslip)|surface-?tethered.{0,40}optical"),
    ("freely_orbiting_magnetic", r"freely orbiting"),
    ("bead_on_surface_magnetic", r"magnetic (tweezers|bead).{0,80}(surface|tether|flow cell)|magnetic tweezers"),
    ("cantilever_cell_surface", r"single[- ]cell force spectroscop|cell[- ]?(probe|attached).{0,30}cantilever|FluidFM"),
    ("cantilever_tip_surface", r"cantilever|AFM tip|atomic force"),
    ("bead_on_surface_acoustic", r"acoustic force"),
    ("bead_on_surface_centrifugal", r"centrifug"),
    ("nanopore_translocation", r"nanopore"),
    ("doubly_tethered_curtain", r"double[- ]tethered|DNA curtains?"),
    ("flow_tethered_end", r"flow[- ]stretch|hydrodynamic|tethered.{0,30}flow"),
    ("biomembrane_force_probe", r"biomembrane force probe|\bBFP\b"),
    ("micropipette_bead", r"micropipette"),
    ("dna_origami_clamp", r"origami.{0,30}(force|clamp|spring)"),
    ("cell_surface_tension_sensor", r"tension gauge|tension (sensor|probe)"),
    ("membrane_tether_extrusion", r"membrane (tether|tube|nanotube)s?|tether (pulling|extraction)"),
    ("in_vivo_trapped_organelle", r"in vivo|living cells?.{0,40}(trap|droplet|organelle|vesicle)|lipid droplets?|phagosome"),
]
GEOMETRY_RX = [(n, re.compile(p, re.I)) for n, p in GEOMETRY]
TECH_DEFAULT_GEOM = {"optical_tweezers": "dumbbell_dual_trap", "magnetic_tweezers": "bead_on_surface_magnetic",
                     "afm_smfs": "cantilever_tip_surface", "acoustic_force_spectroscopy": "bead_on_surface_acoustic",
                     "centrifuge_force": "bead_on_surface_centrifugal", "nanopore_force": "nanopore_translocation",
                     "hydrodynamic_stretching": "flow_tethered_end", "biomembrane_force_probe": "biomembrane_force_probe",
                     "micropipette": "micropipette_bead", "tension_sensors": "cell_surface_tension_sensor",
                     "torque_tweezers": "bead_on_surface_magnetic"}
GEOM_TECH = {"dumbbell_dual_trap": {"optical_tweezers", "torque_tweezers"}, "four_trap_braid": {"optical_tweezers"},
             "three_bead_assay": {"optical_tweezers"}, "single_trap_surface_tether": {"optical_tweezers", "torque_tweezers"},
             "bead_on_surface_magnetic": {"magnetic_tweezers", "torque_tweezers"}, "freely_orbiting_magnetic": {"magnetic_tweezers", "torque_tweezers"},
             "cantilever_tip_surface": {"afm_smfs", "force_spectroscopy_unspecified"}, "cantilever_cell_surface": {"afm_smfs", "force_spectroscopy_unspecified"},
             "bead_on_surface_acoustic": {"acoustic_force_spectroscopy"}, "bead_on_surface_centrifugal": {"centrifuge_force"},
             "nanopore_translocation": {"nanopore_force"}, "doubly_tethered_curtain": {"hydrodynamic_stretching"},
             "flow_tethered_end": {"hydrodynamic_stretching"}, "biomembrane_force_probe": {"biomembrane_force_probe"},
             "micropipette_bead": {"micropipette", "biomembrane_force_probe"}, "dna_origami_clamp": {"tension_sensors"},
             "cell_surface_tension_sensor": {"tension_sensors"},
             "membrane_tether_extrusion": {"optical_tweezers", "afm_smfs", "micropipette", "magnetic_tweezers"},
             "in_vivo_trapped_organelle": {"optical_tweezers", "magnetic_tweezers"}}

# ---------------------------------------------------------------- assay
BEAD_MAT = [("polystyrene", r"polystyrene"), ("silica", r"silica|glass beads?"), ("superparamagnetic", r"superparamagnetic|Dynabeads|magnetic beads?|MyOne|M-2[78]0"), ("gold", r"gold (nano)?(particles?|beads?)")]
BEAD_MAT_RX = [(n, re.compile(p, re.I)) for n, p in BEAD_MAT]
BEAD_PRODUCT_RX = re.compile(r"\b(Dynabeads(?:®)?\s*(?:M-?\d{3}|MyOne\s*(?:Streptavidin\s*)?[CT]\d)|M-?2[78]0 streptavidin|MyOne\s*[CT]1|Spherotech|Bangs Laboratories|Polysciences|Kisker)\b", re.I)
FUNCT = [("streptavidin", r"streptavidin"), ("anti-digoxigenin", r"anti-?dig(oxigenin)?\b"), ("neutravidin", r"neutravidin"),
         ("protein G", r"protein G[- ](coated|beads)"), ("protein A", r"protein A[- ](coated|beads)"), ("carboxyl", r"carboxyl(ated)?[- ](modified|beads|polystyrene)"),
         ("amine", r"amin(e|o)[- ](modified|functionali[sz]ed) beads"), ("Ni-NTA", r"Ni-?NTA"), ("anti-GFP", r"anti-GFP"),
         ("antibody-coated", r"antibody[- ]coated"), ("concanavalin A", r"concanavalin"), ("poly-L-lysine", r"poly-?L-?lysine"),
         ("PEG", r"PEG[- ](ylated|coated|passivat)"), ("lipid-coated", r"lipid[- ]coated beads|membrane[- ]coated beads")]
FUNCT_RX = [(n, re.compile(p, re.I)) for n, p in FUNCT]
ATTACH = [("biotin–streptavidin", r"biotin\w*.{0,60}(strept|neutr)avidin|(strept|neutr)avidin.{0,60}biotin"),
          ("digoxigenin–anti-digoxigenin", r"digoxigenin|anti-?dig\b"), ("ybbR/Sfp (CoA)", r"ybbR|\bSfp\b"),
          ("SpyTag/SpyCatcher", r"SpyTag|SpyCatcher"), ("SnoopTag/SnoopCatcher", r"Snoop(Tag|Catcher)"),
          ("HaloTag", r"HaloTag|Halo-tag"), ("SNAP-tag", r"SNAP-?tag"), ("cysteine–maleimide", r"maleimide"),
          ("thiol–gold", r"thiol.{0,30}gold|gold.{0,30}thiol"), ("His-tag/Ni-NTA", r"His-?tag|Ni-?NTA|polyhistidine"),
          ("cohesin–dockerin", r"cohesin[- ]dockerin|dockerin"), ("click chemistry", r"click chemistry|DBCO|azide-alkyne|\bSPAAC\b"),
          ("sortase", r"sortase"), ("covalent PEG linker", r"PEG (linker|spacer)|heterobifunctional PEG"),
          ("DNA hybridization handle", r"(oligonucleotide|ssDNA|DNA)[- ]handles?|handle DNA"), ("antibody–antigen", r"anti-?(GFP|myc|FLAG|HA|His)\b"),
          ("non-specific adsorption", r"non-?specific(ally)? (adsor|attach|binding to the)")]
ATTACH_RX = [(n, re.compile(p, re.I)) for n, p in ATTACH]
HANDLE_RX = re.compile(NUM + SP + r"(kbp|kb|bp)[- ]*(?:long\s*)?(?:ds|double-stranded\s*)?DNA\s*handles?", re.I)
CONTROL = [("force_ramp", r"force[- ]ramp|force-extension|pulling (and relaxation|cycles?)|stretch(ing)?[- ]relax|constant (pulling|loading) rate|dynamic force spectroscopy"),
           ("force_clamp", r"force[- ]clamp|force feedback|force[- ]feedback"), ("constant_force", r"constant[- ]force|fixed force|constant tension"),
           ("constant_distance", r"constant[- ](trap )?(distance|separation|position|extension)|fixed trap (distance|position)"),
           ("passive_mode", r"passive mode|equilibrium (hopping|fluctuations?)|hopping experiments?"), ("force_jump", r"force[- ]jump|force[- ]quench|force step"),
           ("constant_velocity", r"constant (velocity|speed)|retraction (speed|velocity)|pulling speed"),
           ("oscillatory", r"oscillat\w+ (force|trap|driving)|sinusoidal|microrheolog"), ("rotation", r"rotat\w+ (the )?magnets?|magnet rotations?|twist(ing|ed)? (the )?DNA|turns")]
CONTROL_RX = [(n, re.compile(p, re.I)) for n, p in CONTROL]
R_LOADING = re.compile(NUM + r"(?:\s*(?:-|–|to)\s*" + NUM + r")?" + SP + r"(pN|nN)" + SP + r"(?:/|·|per\s)" + SP + r"s\b", re.I)
R_SPEED = re.compile(NUM + r"(?:\s*(?:-|–|to)\s*" + NUM + r")?" + SP + r"(nm|" + MU + r"m)" + SP + r"(?:/|·|per\s)" + SP + r"s\b(?![a-z])", re.I)
R_SPEED_ANCHOR = re.compile(r"pull\w*|retract\w*|speed|velocit\w*|moved|stretch\w*|trap|piezo|approach", re.I)
R_SPRING_AFM = re.compile(NUM + PM + SP + r"(pN/nm|pN nm-1|N/m|mN/m)", re.I)
R_CANTILEVER = re.compile(r"\b(MLCT(?:-Bio)?(?:-DC)?|BioLever(?: mini)?|OBL-10|BL-AC40TS|AC40(?:TS)?|BL-RC150VB|TR400PB|OMCL-\w+|MSNL|MSCT|NPG|DNP-?S?|PNP-TR|qp-BioAC|Arrow TL\d|CSC\d\d|NSC\d\d|RC800PB|BL-150VB|USC-F[\d.]+)\b", re.I)
R_MAG_BEAD_SIZE = re.compile(r"\b(M-?270|M-?280|M-?450|MyOne)\b", re.I)

# ---------------------------------------------------------------- solution
R_PH = re.compile(r"\bpH\s*(?:=|of|:)?\s*(\d{1,2}(?:\.\d+)?)", re.I)
SALT_NAMES = r"(NaCl|KCl|MgCl2|MgCl₂|CaCl2|CaCl₂|Tris(?:-HCl)?|HEPES|MOPS|PIPES|MES|EDTA|EGTA|DTT|TCEP|KOAc|K-?acetate|Mg\(OAc\)2|MgOAc|ZnCl2|K-glutamate|potassium glutamate|NaOAc|sodium phosphate|phosphate|glycerol|BSA|Tween[- ]?20|ATP|ADP|AMP-?PNP|ATPγS|ATP-?γ-?S|GTP|GMP-?CPP|GDP|NTPs?|dNTPs?|imidazole|spermidine|PEG\s?\d*|sucrose|glucose|trolox|β-mercaptoethanol|2-mercaptoethanol|NaN3|sodium azide|casein|Pluronic\s?F-?127)"
R_SALT = re.compile(NUM + SP + r"(mM|µM|μM|uM|nM|M|%|mg/ml|mg/mL)" + SP + SALT_NAMES, re.I)
R_OXY = re.compile(r"glucose oxidase|GLOXY|catalase|protocatechu\w+ (dioxygenase|acid)|\bPCA\b.{0,10}\bPCD\b|pyranose oxidase|trolox|oxygen[- ]scaveng\w+", re.I)
R_BUFFER = re.compile(r"\b(Tris(?:-HCl)?|HEPES|MOPS|PIPES|MES|phosphate[- ]buffered saline|PBS|BRB80|PEM|TE|Tris-acetate|sodium cacodylate)\b(?: buffer)?", re.I)

# ---------------------------------------------------------------- annotations
SOFTWARE = [("Pylake", r"\bpylake\b"), ("Bluelake", r"\bBluelake\b"), ("LabVIEW", r"\bLab ?VIEW\b"), ("MATLAB", r"\bMATLAB\b"),
            ("IGOR Pro", r"\bIgor( Pro)?\b"), ("Python", r"\bPython\b"), ("Origin", r"\bOrigin(Pro| \d{4}| software)\b"),
            ("R", r"\bR (software|package|version|\d\.\d)|\bRStudio\b"), ("POTATO", r"\bPOTATO\b"), ("Tweezepy", r"\bTweezepy\b"),
            ("tweezepy/pytweezer", r"\bpytweezer\b"), ("JPK Data Processing", r"JPK (data processing|SPM data)"),
            ("Fodis", r"\bFodis\b"), ("Hooke", r"\bHooke\b(?!'s law)"), ("AtomicJ", r"\bAtomicJ\b"), ("Gwyddion", r"\bGwyddion\b"),
            ("ImageJ/Fiji", r"\bImageJ\b|\bFiji\b"), ("KymoAnalyzer", r"Kymo\w*(Analyzer|graphClear|Butler)"),
            ("vbFRET/ebFRET", r"\b(vb|eb)FRET\b"), ("HaMMy", r"\bHaMMy\b"), ("tweezers calibration (tweezercalib)", r"tweezercalib"),
            ("MT software (Picotwist/Depixus)", r"PicoJai|Magnetic Tweezers? software"), ("NanoScope Analysis", r"NanoScope Analysis"),
            ("Mathematica", r"\bMathematica\b"), ("C++/C#", r"\bC\+\+|\bC#")]
SOFTWARE_RX = [(n, re.compile(p, re.I)) for n, p in SOFTWARE]
MODELS = [("eWLC", r"extensible worm[- ]like[- ]chain|\beWLC\b|Odijk"), ("tWLC", r"twistable worm[- ]like|\btWLC\b"),
          ("WLC", r"worm[- ]like[- ]chain|\bWLC\b|Marko[- ]Siggia|Bouchiat"), ("eFJC", r"extensible freely[- ]jointed|\beFJC\b"),
          ("FJC", r"freely[- ]jointed[- ]chain|\bFJC\b"), ("Bell-Evans", r"Bell[- ]Evans|Evans[- ]Ritchie"), ("Bell", r"\bBell('s)? (model|equation|formula)"),
          ("Dudko-Hummer-Szabo", r"Dudko|Hummer[- ]Szabo|\bDHS\b"), ("Kramers", r"\bKramers\b"), ("Crooks", r"\bCrooks\b"),
          ("Jarzynski", r"\bJarzynski\b"), ("HMM", r"hidden Markov|\bHMM\b"), ("step_finding", r"step[- ]finding|step[- ]detection|Kerssemakers|change[- ]point"),
          ("Michaelis-Menten", r"Michaelis[- ]Menten"), ("Arrhenius", r"Arrhenius"), ("two-state", r"two-state model")]
MODELS_RX = [(n, re.compile(p, re.I)) for n, p in MODELS]
DYES = re.compile(r"\b(Cy[2357](?:\.5)?|Alexa(?: Fluor)?\s?\d{3}|ATTO\s?\d{3}\w?|Atto\s?\d{3}\w?|SYTOX\s?(?:Orange|Green|Blue)|YOYO-1|TOTO-1|POPO-3|DAPI|Hoechst|e?GFP|mCherry|mNeonGreen|JF\s?\d{3}|Janelia Fluor\s?\d{3}|TMR|TAMRA|Cy3B|LD\d{3}|Dylight\s?\d{3}|Qdots?|quantum dots?)\b", re.I)

# ---------------------------------------------------------------- results (abstract-level)
RES_PATTERNS = [
    ("unfolding_force", r"unfold(ing|s|ed)?(?: at)?(?: a)?(?: mean| average| median| most probable)?\s+forces?"),
    ("refolding_force", r"refold(ing)?\s+forces?"),
    ("rupture_force", r"rupture forces?|(dissociation|detachment|breaking) forces?"),
    ("unbinding_force", r"unbinding forces?|binding strength"),
    ("unzipping_force", r"unzipping forces?"),
    ("overstretching_force", r"overstretching(?: transition)?(?: plateau)?(?: force)?"),
    ("stall_force", r"stall(ing)? forces?"),
    ("equilibrium_force", r"(equilibrium|coexistence|transition|midpoint) forces?|F1/2"),
    ("adhesion_force", r"adhesion forces?"),
    ("tether_force", r"tether forces?"),
    ("step_size", r"step(s| size)?(?: sizes?)?(?: of)?"),
    ("persistence_length", r"persistence lengths?"),
    ("contour_length_increment", r"contour[- ]length (increments?|increases?|changes?|gains?)|ΔLc|ΔL_c"),
    ("contour_length", r"contour lengths?"),
    ("stretch_modulus", r"stretch(ing|e)? moduli|stretch(ing)? modulus"),
    ("velocity", r"velocit(y|ies)|speeds?|rates? of translocation|translocation rates?"),
    ("folding_free_energy", r"(folding|unfolding|stability|free)[- ]energ(y|ies)|ΔG"),
    ("distance_to_transition_state", r"distance to the transition state|transition[- ]state distance|Δx‡|Δx\b|x‡"),
    ("bond_lifetime", r"(bond )?lifetimes?"),
    ("torque", r"torques?"),
    ("dwell_time", r"dwell times?"),
    ("molecular_stiffness", r"stiffness(es)?"),
    ("elastic_modulus", r"(Young'?s|elastic) modul(us|i)"),
    ("rate_constant_zero_force", r"(intrinsic|zero[- ]force|spontaneous) (unfolding |dissociation |off[- ])?rates?|k0\b|k_0\b"),
    ("processivity_run_length", r"run lengths?|processivit(y|ies)"),
    ("loading_rate", r"loading rates?"),
]
RES_UNITS = {
    "pN": {"unfolding_force", "refolding_force", "rupture_force", "unbinding_force", "unzipping_force", "overstretching_force",
           "stall_force", "equilibrium_force", "adhesion_force", "tether_force", "stretch_modulus"},
    "nN": {"rupture_force", "adhesion_force", "unbinding_force"},
    "nm": {"step_size", "persistence_length", "contour_length_increment", "contour_length", "distance_to_transition_state", "processivity_run_length"},
    "Å": {"distance_to_transition_state", "step_size", "contour_length_increment"},
    "bp": {"step_size", "processivity_run_length"}, "nt": {"step_size"},
    "µm": {"processivity_run_length", "contour_length", "persistence_length"},
    "nm/s": {"velocity"}, "bp/s": {"velocity"}, "nt/s": {"velocity"}, "aa/s": {"velocity"}, "µm/s": {"velocity"}, "codons/s": {"velocity"},
    "kBT": {"folding_free_energy", "activation_free_energy"}, "kcal/mol": {"folding_free_energy"}, "kJ/mol": {"folding_free_energy"},
    "ms": {"bond_lifetime", "dwell_time"}, "s": {"bond_lifetime", "dwell_time"}, "µs": {"bond_lifetime", "dwell_time"},
    "pN·nm": {"torque"}, "pN/nm": {"molecular_stiffness"}, "kPa": {"elastic_modulus"}, "Pa": {"elastic_modulus"}, "MPa": {"elastic_modulus"},
    "s⁻¹": {"rate_constant_zero_force"}, "pN/s": {"loading_rate"},
}
UNIT_RX = (r"(pN\s*(?:·|\s)?\s*nm|pN/nm|pN/s|pN|nN|nm/s|bp/s|nt/s|aa/s|codons?/s|" + MU + r"m/s|nm|Å|" + MU + r"m|bp|nt|kBT|kB\s?T|k_BT|kT|kcal/mol|kcal mol-1|kJ/mol|ms|" + MU + r"s|s-1|s−1|s⁻¹|kPa|MPa|Pa|s)\b")
VAL_RX = re.compile(r"(?:~|≈|∼|≃|approximately |about |around |of |at |was |were |is |are |by |up to |as high as |>|<|≥|≤|=|\()?\s*" +
                    NUM + r"(?:\s*(?:±|\+/-)\s*" + NUM + r")?(?:\s*(?:-|–|to)\s*" + NUM + r")?" + SP + UNIT_RX)


def norm_unit(u):
    u = u.replace("μ", "µ").replace("u", "µ") if u.startswith(("u", "μ")) and u not in ("um",) else u
    u = {"um": "µm", "um/s": "µm/s", "kT": "kBT", "kB T": "kBT", "k_BT": "kBT", "kcal mol-1": "kcal/mol", "s-1": "s⁻¹", "s−1": "s⁻¹",
         "codon/s": "codons/s"}.get(u, u)
    u = re.sub(r"pN\s*(?:·|\s)\s*nm", "pN·nm", u)
    return u.replace("µs", "µs")


def extract_results(text):
    """Pull (observable, value, unit) triples from abstract/results text."""
    if not text:
        return []
    out, seen = [], set()
    for sent in re.split(r"(?<=[.;])\s+(?=[A-Z(])", text):
        for q, prx in RES_PATTERNS:
            for qm in re.finditer(prx, sent, re.I):
                tail = sent[qm.end(): qm.end() + 70]
                vm = VAL_RX.search(tail)
                if not vm or vm.start() > 45:
                    continue
                unit = norm_unit(vm.group(4).strip())
                ok = any(q in qs for u, qs in RES_UNITS.items() if u == unit)
                if not ok:
                    continue
                v = _num(vm.group(1))
                key = (q, v, unit)
                if key in seen:
                    continue
                seen.add(key)
                r = {"quantity": q, "value": v, "unit": unit, "statistic": "single_value",
                     "source": {"location": "abstract", "snippet": sent[max(0, qm.start() - 60): qm.end() + 90].strip()[:300],
                                "extraction": "auto_regex", "confidence": "medium"}}
                if vm.group(2):
                    r["uncertainty"], r["uncertainty_type"] = _num(vm.group(2)), "unspecified"
                if vm.group(3):
                    r["min"], r["max"] = v, _num(vm.group(3))
                    r["value"], r["statistic"] = None, "range"
                out.append(r)
    return out[:25]


# ---------------------------------------------------------------- data availability statement
DA_CLASSES = [
    ("not_available", r"no (new )?data (were|was) (generated|created|analy[sz]ed)|not applicable|data sharing (is )?not applicable|no datasets? (were|was) (generated|analy[sz]ed)"),
    ("public_repository", r"zenodo|figshare|dryad|osf\.io|open science framework|mendeley data|dataverse|4tu|biostudies|empiar|github|gitlab|deposited (in|at|to)|"
                          r"publicly available (at|in|from|on)|available (at|in|on|from) (the )?(https?://|doi|repository)|accession (number|code)|data\.4tu|researchdata|repository"),
    ("source_data_supplement", r"source data (are|is) provided|source data (file|files)|provided with this paper|source data"),
    ("journal_supplement", r"(within|in) (the )?(article|paper|manuscript|main text)( and| or)? (its )?(supplementary|supporting|supplemental)|supplementary (information|material|data) (files? )?(of|accompanying|with)|included in (this|the) (published )?(article|paper)|all (relevant )?data are (included|within|in the paper|available in the)|(supplementary|supporting) (information|materials?|files?)"),
    ("on_request", r"(upon|on) (reasonable )?request|from the (corresponding )?authors?|contact the (corresponding )?author|available (by|via) request|request to the|by request"),
]
DA_RX = [(n, re.compile(p, re.I)) for n, p in DA_CLASSES]


def classify_statement(text):
    if not text:
        return []
    return [n for n, rx in DA_RX if rx.search(text)]
