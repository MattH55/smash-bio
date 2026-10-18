"""Step 3 - technique detection and scope tiering of harvested articles.

tier:
  core        biological system + a force-application technique + evidence of
              force applied between two ends (tether / bond / motor / cell probe)
  methods     instrument / analysis / calibration development for SMFS
  peripheral  technique on a biological sample but without force spectroscopy
              (e.g. optical sorting, Raman tweezers, AFM imaging) - kept for completeness
  out         physics / non-biological / unrelated (dropped)
Output: out/articles_classified.jsonl
"""
import re
from collections import Counter

from common import OUT, load_jsonl, save_jsonl

R = lambda p: re.compile(p, re.I)

TECH = {
    "optical_tweezers": R(r"optical(ly)?[- ]tweez|optical[- ]trap|laser[- ]tweez|laser[- ]trap|dual[- ]trap|\bc-trap\b|photonic force microsc|optical pincer|holographic optical tweez|optically trapped (bead|microsphere|particle)"),
    "magnetic_tweezers": R(r"magnetic[- ]tweez|magnetic (bead )?(force spectroscopy|force clamp|pulling)|magnetic trap(?!ped (atom|ion|gas))|magnetically (trapped|pulled|tethered)|magnetic beads?.{0,60}(tether|force|stretch)"),
    "torque_tweezers": R(r"torque tweez|magnetic torque|angular optical trap|optical torque wrench|freely orbiting magnetic|magneto-optical tweez"),
    "afm_smfs": R(r"(atomic force|\bafm\b).{0,120}(force spectroscop|pull|unfold|ruptur|unbind|stretch|single[- ]molecule|force[- ]extension|force[- ]clamp|adhesion force|cantilever)|single[- ]molecule force spectroscop|\bsmfs\b|single[- ]cell force spectroscop|cantilever.{0,80}(pull|unfold|force spectroscop)"),
    "acoustic_force_spectroscopy": R(r"acoustic force spectroscop|acoustic force.{0,60}(tether|single[- ]molecule|dna|bead)"),
    "centrifuge_force": R(r"centrifug\w* force (microscop|spectroscop)|centrifuge force"),
    "nanopore_force": R(r"nanopore[- ]tweez|\bsprnt\b|nanopore.{0,120}(unzip|unfold|force spectroscop|helicase.{0,40}(step|motion)|translocation.{0,40}(force|motor))"),
    "hydrodynamic_stretching": R(r"flow[- ]stretch|dna curtain|hydrodynamic(ally)? (force|stretch|drag|flow).{0,60}(dna|tether|molecule)|flow[- ](induced|driven) stretch|tethered.{0,40}(under|in) (a )?(laminar )?flow|flow[- ]extension"),
    "biomembrane_force_probe": R(r"biomembrane force probe|\bbfp\b.{0,40}(force|bond)|micropipette adhesion frequency|adhesion frequency assay"),
    "micropipette": R(r"micropipette (aspiration|manipulation|force)|dual micropipette"),
    "tension_sensors": R(r"tension gauge tether|\btgt\b.{0,30}(force|tension)|molecular tension (sensor|probe|fluorescence)|dna[- ]based tension|dna (tension|force) (probe|sensor|gauge)|fret[- ]based tension sensor|origami force (clamp|spectrometer)|nanoscopic force clamp|force[- ]sensing dna"),
    "microneedle": R(r"glass micro-?needle|microneedle.{0,40}(single|force|stretch)"),
    "afm_generic": R(r"atomic force microscop|\bafm\b"),
    "force_spectroscopy_unspecified": R(r"force spectroscop"),
}

BIO = R(r"\b(protein|proteins|dna|rna|nucleic|nucleosome|chromatin|enzyme|motor|kinesin|myosin|dynein|actin|tubulin|microtubule|"
        r"polymerase|helicase|ribosome|antibod|receptor|ligand|peptide|collagen|titin|ubiquitin|cell|cells|cellular|membrane|lipid|vesicle|"
        r"bacteri|virus|viral|phage|yeast|erythrocyte|blood|tissue|biolog|biomolec|biopolymer|chromosome|integrin|cadherin|"
        r"fibronectin|talin|riboswitch|hairpin|g-quadruplex|amino acid|glycan|polysaccharide|neuron|sperm|embryo|organelle|"
        r"mitochond|chloroplast|spider silk|mussel|elastin|fibrin|mucin|platelet|leukocyte|lymphocyte|t-cell|t cell|bond)")

FORCE2 = R(r"single[- ]molecule|single (dna|rna|protein|chromatin|polymer)? ?molecules?|individual (dna|rna|protein)? ?molecules?|tether|force[- ]extension|unfold|unzip|stretch|pulling|\bpull(ed)?\b|ruptur|unbind|stall force|"
           r"\bsteps?\b|stepping|processiv|catch[- ]bond|slip[- ]bond|force[- ]clamp|force[- ]ramp|loading rate|\bpn\b|piconewton|"
           r"mechanical (stability|unfolding|properties of (single|individual))|mechanochem|bond lifetime|adhesion force|"
           r"translocat|motor|torque|supercoil|overstretch|elasticity of (dna|rna|single)|persistence length|contour length|"
           r"force[- ]dependent|force spectroscop|energy landscape|transition state|kinetics under (load|force)|"
           r"load[- ]dependent|mechanosens|mechanotransduc|force generation|tension")

RHEO = R(r"rheolog|viscoelastic|cell mechanic|cellular mechanic|membrane tether|membrane tube|tether pull|deformab|"
         r"stiffness of (cells?|the cell|nuclei|nucleus)|cortical tension|cytoplasm|microrheolog|elastic modulus|"
         r"viscosity|mechanical properties of (cells?|red blood|erythrocyte|nuclei|chromosome)|stretching of (cells?|red blood|erythrocyte)")

OUT_PHYS = R(r"\b(cold|ultracold|neutral|rydberg) atoms?\b|bose[- ]einstein|\bbec\b|atomic (gas|clock|ensemble)|\bqubit|quantum (gas|computing|"
             r"optomechan|ground state|simulation|information)|levitat|vacuum|ion trap|trapped ions?|optical lattice|magneto-optical trap\b|"
             r"\bmot\b|plasmonic (trapping|tweez)|metasurface|photonic crystal|semiconductor|nanowire|graphene|quantum dots? trapping|"
             r"aerosol|airborne|soliton|fib(er|re) laser|spin(or)? (gas|dynamics)|electron beam|cosmic|antimatter|atom interferomet|"
             r"optical binding|colloidal (crystal|glass)|active (matter|brownian)|microrobot|micro-robot|optical vortex beams?|"
             r"orbital angular momentum|non-?diffracting beam|bessel beam|airy beam|plasma|dielectric particles?")

NON_FORCE_BIO = R(r"raman|sorting|cytometr|single[- ]cell (isolation|transfer|sorting)|fertiliz|in vitro fertil|"
                  r"cell (manipulation|positioning|patterning) |ablation|laser (scissors|microdissection|surgery)|"
                  r"photoporation|optoporation|transfection|imaging of|topograph|high[- ]speed afm imaging")

METHOD = R(r"\b(calibrat|instrument|apparatus|setup|set-up|design|implementation|software|algorithm|toolbox|package|"
           r"we (built|developed|present|describe|introduce) (a|an|the)|novel (method|approach|technique|instrument)|"
           r"protocol|noise|drift|resolution|bandwidth|detection scheme|back[- ]focal[- ]plane)\b")

STRONG = R(r"force spectroscop|single[- ]molecule|single (dna|rna|protein)? ?molecules?|tether|force[- ]extension|unfold|unzip|rupture|"
            r"unbinding force|stall force|catch[- ]bond|force[- ]clamp|overstretch|supercoil|stepping|processiv|loading rate|"
            r"piconewton|\bpn\b|torque|membrane (tether|tube|nanotube)|trap stiffness|motor proteins?|molecular motors?|"
            r"kinesin|myosin|dynein|polymerase|helicase|translocase|force generation|mechanical properties|elasticity|"
            r"viscoelastic|(adhesion|binding|interaction|unbinding) forces?|stiffness")

REVIEW_TYPES = {"review", "review-article", "systematic review", "Review", "Systematic Review"}


def classify(a):
    text = " ".join(filter(None, [a.get("title"), a.get("abstract"), " ".join(filter(None, a.get("keywords") or [])),
                                  " ".join(filter(None, a.get("mesh") or []))]))
    t = text.lower()
    tech = [k for k, rx in TECH.items() if rx.search(t)]
    # an AFM paper only counts as SMFS when the force-spectroscopy pattern matched
    if "afm_smfs" in tech:
        tech = [k for k in tech if k not in ("afm_generic", "force_spectroscopy_unspecified")]
    primary_tech = [k for k in tech if k not in ("afm_generic", "force_spectroscopy_unspecified")]
    if not primary_tech and "force_spectroscopy_unspecified" in tech:
        primary_tech = ["force_spectroscopy_unspecified"]
    bio = len(set(m.group(0).lower() for m in BIO.finditer(t)))
    force = len(set(m.group(0).lower() for m in FORCE2.finditer(t)))
    rheo = bool(RHEO.search(t))
    phys = len(set(m.group(0).lower() for m in OUT_PHYS.finditer(t)))
    nonforce = bool(NON_FORCE_BIO.search(t))
    method = bool(METHOD.search(t))
    is_review = any(p in REVIEW_TYPES or "review" in p.lower() for p in a.get("pub_types") or [])
    reasons = []
    if not primary_tech:
        # papers found by generic SMFS phrases with no named technique: keep if clearly SMFS
        if force >= 3 and bio >= 2 and re.search(r"single[- ]molecule|catch[- ]bond|force[- ]extension|unzip|rupture force|stall force|force[- ]clamp", t):
            primary_tech = ["force_spectroscopy_unspecified"]
            reasons.append("generic-smfs-language")
        else:
            return "out", tech, ["no-force-technique"], is_review
    if phys >= 2 and bio <= 2:
        return "out", primary_tech, ["physics-dominant"], is_review
    strong = len(set(m.group(0).lower() for m in STRONG.finditer(t)))
    if bio == 0:
        if strong >= 2 and phys == 0:
            return "methods", primary_tech, ["instrument-or-analysis"], is_review
        return "out", primary_tech, ["no-biological-system"], is_review
    if force >= 2 or (force >= 1 and bio >= 2) or rheo:
        if nonforce and strong < 2 and not rheo:
            return "peripheral", primary_tech, ["manipulation-without-force-spectroscopy"], is_review
        if phys >= 2 and strong < 2:
            return ("methods" if strong else "out"), primary_tech, ["physics-with-bio-application"], is_review
        if strong == 0 and not rheo:
            return "peripheral", primary_tech, ["weak-force-evidence"], is_review
        return "core", primary_tech, reasons or ["technique+bio+force"], is_review
    if strong >= 2:
        return "methods", primary_tech, ["instrument-or-analysis"], is_review
    return "peripheral", primary_tech, ["bio-without-force-evidence"], is_review


def main():
    arts = load_jsonl(OUT / "articles_raw.jsonl")
    tiers = Counter()
    out = []
    for a in arts:
        tier, tech, reasons, is_review = classify(a)
        tiers[tier] += 1
        if tier == "out":
            continue
        a["tier"], a["techniques_detected"], a["scope_reasons"], a["is_review"] = tier, tech, reasons, is_review
        out.append(a)
    save_jsonl(OUT / "articles_classified.jsonl", out)
    print(tiers)
    tc = Counter(t for a in out if a["tier"] == "core" for t in a["techniques_detected"])
    print("core technique counts:", tc.most_common())
    print("core reviews:", sum(a["is_review"] for a in out if a["tier"] == "core"))


if __name__ == "__main__":
    main()
