"""Conservative, evidence-carrying extraction for the Simulations category.

Every returned value carries the original number **and** the unit the source
wrote, plus a `unit_system` (`physical`, `reduced`, `reduced_with_stated_conversion`).
A number is only accepted when the text gives it together with a unit we can
read; an unreadable or unknown unit means the value is dropped, not guessed.
Reduced units are never converted to physical units unless the source states the
conversion, in which case it is recorded in ``model.unit_conversions``.
"""
import re


# Observables whose pattern carries no unit group (counts only).
CANONICAL_UNITS = {"number_of_steps_or_intermediates": "1"}

SPEED_TO_M_PER_S = {
    "m/s": 1.0, "nm/s": 1e-9, "um/s": 1e-6, "nm/ns": 1.0, "nm/us": 1e-3,
}

# Experimental geometry vocabulary (same enum as the SMFS records), used only
# when the text explicitly emulates or refers to that geometry.
GEOMETRY_PATTERNS = (
    ("dumbbell_dual_trap", r"dual[- ]trap|two (?:optical )?traps?|dumbbell|double[- ]trap|two beads"),
    ("bead_on_surface_magnetic", r"magnetic tweezers?|magnetic trap|paramagnetic bead"),
    ("four_trap_braid", r"four[- ]trap|magnetic braid"),
    ("three_bead_assay", r"three[- ]bead"),
    ("cantilever_tip_surface", r"\bafm\b|atomic force microscop\w*|cantilever|tip[- ]surface|force[- ]distance"),
    ("single_trap_surface_tether", r"single[- ]trap|surface[- ]tethered|one (?:optical )?trap"),
    ("nanopore_translocation", r"nanopore|translocation|\bsprnt\b"),
    ("doubly_tethered_curtain", r"dna curtain|doubly[- ]tethered|double[- ]tether\w* curtain"),
    ("flow_tethered_end", r"flow[- ]stretch\w*|hydrodynamic (?:flow|drag)|shear flow|flow cell"),
    ("micropipette_bead", r"micropipette|micropipet"),
    ("biomembrane_force_probe", r"biomembrane force probe|\bbfp\b"),
)

FORCE_FIELD_PATTERN = (
    r"(?P<ff>CHARMM\d+[A-Za-z]*|AMBER[-\w/]*|OPLS[-\w]*|GROMOS\d*|Martini\s*[23]|"
    r"AMBER99SB[-\w]*|residue[- ]based[-\w ]*|AWSEM|HPS|Kim[- ]Hummer|MJ[- ]?HPS)"
)

SPEED_PATTERN = (r"(?:pul(?:l|led|ling)|retract\w*|unzip\w*|load\w*)[^.]{0,50}?"
                 r"(?P<value>[0-9]*\.?[0-9]+)\s*"
                 r"(?P<unit>nm/ns|nm/µs|nm/us|nm/s|µm/s|um/s|m/s)")
SPRING_PATTERN = (r"(?:spring|force) constant[^.]{0,40}?(?P<value>[0-9]*\.?[0-9]+)\s*"
                  r"(?P<unit>pN/nm|N/m|kcal/mol/Å\^?2|kcal/mol/A\^?2|kcal mol-1 A-2|kj/mol/nm\^?2)")
TEMPERATURE_PATTERN = (r"(?:temperature|thermostat\w*|equilibrat\w*|at)[^.]{0,40}?"
                       r"(?P<value>[0-9]{2,4}(?:\.[0-9]+)?)\s*(?P<unit>K|kelvin)\b")
TRAJECTORY_PATTERN = (r"(?P<value>[0-9]+)\s*(?:independent\s+|separate\s+|distinct\s+)?"
                      r"(?:trajector(?:y|ies)|runs|replicas|steered[- ]md runs|pullings)\b")
SIM_TIME_PATTERN = (r"(?:simulat\w+|sampl\w*|run|trajector\w+)\s*(?:time|for|over|of)[^.]{0,30}?"
                    r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>ns|µs|us|ps|ms|s)\b")
FORCE_RANGE_PATTERN = (r"forces?[^.]{0,24}?(?:up to|between|from|of)[^.]{0,30}?"
                       r"(?P<value>[0-9]*\.?[0-9]+)\s*(?P<unit>pN|nN)")

REPO_URL_PATTERN = (r"https?://(?:www\.)?(zenodo\.org|figshare\.com|osf\.io|datadryad\.org|"
                    r"ebi\.ac\.uk|fairdata\.fi|github\.com|materialscloud\.org|"
                    r"doi\.org/10\.5281|data\.dryad)[^\s,;)\"']*")
ON_REQUEST_PATTERN = (r"(?:available|obtained|provided|requested)\s*(?:from|on)\s*(?:the\s*)?"
                      r"(?:corresponding author|request|authors)")
NOT_AVAILABLE_PATTERN = (r"no new data|all (?:the )?data (?:are|is|were) (?:presented|included|shown) "
                         r"in the (?:article|paper|manuscript)|data (?:are|is) not (?:publicly )?available")
RESIDUE_RANGE_PATTERN = re.compile(r"(?:residues?|atoms?|nucleotides?|nt)\s*([0-9]+)\s*[-–to]+\s*([0-9]+)", re.I)
CONSTRUCT_PATTERN = re.compile(
    r"(?:construct|fragment|domain|residues?|nucleotides?|nt)\s*"
    r"(?P<start>[0-9]{1,4})\s*(?:[-–]|to)\s*(?P<end>[0-9]{1,4})", re.I)
SCI_PATTERN = re.compile(r"(?P<lead>\s?)(?P<sign>[-−]?)(?P<mant>[0-9]*\.?[0-9]+)"
                         r"\s*[x×]\s*10\s*\^?\s*(?P<exp>[-−]?[0-9]+)")
HTML_TAG = re.compile(r"</?[A-Za-z][^>]{0,80}>")
ENTITIES = {"&lt;": "<", "&gt;": ">", "&amp;": "&", "&nbsp;": " ", "&minus;": "-",
            "\u2009": " ", "\u2008": " ", "\u00a0": " "}


def clean_text(text):
    """Drop inline HTML markup and entities so they cannot distort a match.

    Full texts arrive as JATS-flavoured HTML ("Delta x <sup>+</sup> = 2.7 nm"), and
    a stray angle bracket would otherwise be read as a bound.
    """
    text = HTML_TAG.sub(" ", text or "")
    for entity, character in ENTITIES.items():
        text = text.replace(entity, character)
    return text


def normalise_scientific(text):
    """Rewrite ``5 × 10^-5`` as ``0.00005`` so the number and its unit stay adjacent."""
    def sub(match):
        lead = match.group("lead") or ""  # keep the whitespace so the value stays a separate token
        sign = "-" if match.group("sign") in ("-", "−") else ""
        exponent = match.group("exp").replace("−", "-")
        try:
            value = float(f"{sign}{match.group('mant')}e{exponent}")
        except ValueError:  # pragma: no cover - defensive
            return match.group(0)
        rendered = f"{value:.12f}".rstrip("0").rstrip(".")
        if rendered in ("", "-", "0"):
            rendered = f"{value:g}"
        return lead + rendered

    return SCI_PATTERN.sub(sub, text or "")


def snippet(text, match, before=60, after=30):
    return text[max(0, match.start() - before):match.end() + after][:400]


def evidence(field, method, text, match, confidence, section=None):
    item = {"field": field, "method": method, "snippet": snippet(text, match), "confidence": confidence}
    if section:
        item["section"] = section
    return item


def normalise_unit(unit_text, spec):
    if not unit_text:
        return None
    key = unit_text.strip().lower()
    return spec.unit_aliases.get(key) or spec.unit_aliases.get(key.replace(" ", ""))


def _value_boundary_ok(text, match):
    """Reject a number that is part of a token ("Leu15", "TDP-43", "10-4") rather than a value."""
    start, end = match.start("value"), match.end("value")
    before = text[start - 1] if start > 0 else " "
    if before.isalnum() or before in "-–—'’⁄":
        return False
    return True


def _unit_boundary_ok(text, match):
    """Reject a unit that is only the prefix of a longer one ("nm/s" inside "nm/step")."""
    unit = match.groupdict().get("unit")
    if not unit:
        return True
    end = match.end("unit")
    return not (end < len(text) and text[end].isalpha())


#: words in the window before a number that mean it quantifies something else
QUANTIFIER_WORDS = ("difference", "less than", "greater than", "increases by", "decreases by",
                    "changed by", "uncertainty", "error bar", "standard error",
                    "increases from", "decreases from", "increased from", "decreased from")

#: observables where a word in the immediate window means the number is a change, not the value
OBSERVABLE_REJECT = {
    "contour_length": ("increas", "increment", "change", "differ", "δ", "Δ"),
    "persistence_length": ("change",),
}

#: words that turn a number into an upper or lower bound rather than a measurement
BOUND_MAX = (">", "≥", "above", "up to", "maximum", "max.", "not exceed")
BOUND_MIN = ("<", "≤", "below", "at least", "minimum", "min.", "greater than")


def _quantifier_ok(text, match, window=90):
    """Reject values that the sentence is using as a difference or a bound.

    "the difference between the unfolding forces is less than 0.1 pN" is not a
    measurement of the unfolding force, so it must not be extracted as one.
    """
    anchor = match.start("value")
    before = text[max(0, anchor - window):anchor].lower()
    return not any(word in before for word in QUANTIFIER_WORDS)


def _observable_ok(text, match, observable, window=30):
    words = OBSERVABLE_REJECT.get(observable)
    if not words:
        return True
    anchor = match.start("value")
    before = text[max(0, anchor - window):anchor].lower()
    return not any(word in before for word in words)


def _bound(text, match, window=18):
    """Return 'max', 'min' or None when the number is bounded rather than measured."""
    anchor = match.start("value")
    before = text[max(0, anchor - window):anchor].lower()
    if any(word in before for word in BOUND_MAX):
        return "max"
    if any(word in before for word in BOUND_MIN):
        return "min"
    return None


def extract_results(text, spec, method="regex_title_abstract", confidence="low", max_results=12):
    """Grounded results. Every value keeps the unit the source wrote."""
    text = normalise_scientific(clean_text(text))
    results = []
    for observable in spec.observables:
        pattern = spec.observable_patterns.get(observable)
        if not pattern:
            continue
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        if (not _value_boundary_ok(text, match) or not _unit_boundary_ok(text, match)
                or not _quantifier_ok(text, match)
                or not _observable_ok(text, match, observable)):
            continue
        try:
            value = float(match.group("value"))
        except (TypeError, ValueError):
            continue
        unit_text = match.groupdict().get("unit")
        if unit_text is None:
            canonical = CANONICAL_UNITS.get(observable)
            if canonical is None:
                continue
            unit, unit_system = canonical, "physical"
        else:
            resolved = normalise_unit(unit_text, spec)
            if resolved is None:
                continue  # unknown unit: drop rather than guess
            unit, unit_system = resolved
        result = {
            "quantity": observable,
            "unit": unit,
            "unit_system": unit_system,
            "provenance": [evidence(f"results[{len(results)}]", method, text, match, confidence)],
        }
        bound = _bound(text, match)
        if bound:
            # "forces >60 pN" is a bound, not a measurement: keep it as min/max
            result[bound] = value
            result["statistic"] = "range"
        else:
            result["value"] = value
        around = snippet(text, match, 80, 40)
        if re.search(r"\bmean\b|\baverage\b", around, re.I):
            result["statistic"] = "mean"
        results.append(result)
        if len(results) >= max_results:
            break
    return results


def detect_model(text, spec, method="regex_title_abstract", confidence="low"):
    """Model family, group, software, solvent and force field, each only when named."""
    text = clean_text(text)
    families = [family for family, pattern in spec.model_family_patterns.items()
                if re.search(pattern, text, re.I)]
    if "Go_heavy_atom" in families and "Go_CA" in families:
        families.remove("Go_CA")
    model = {}
    if families:
        model["family"] = families[0]
        model["family_group"] = spec.family_group.get(families[0], "other")
        first = re.search(spec.model_family_patterns[families[0]], text, re.I)
        model["evidence"] = [evidence("model.family", method, text, first, confidence)]
    software = [name for name, pattern in spec.software_patterns.items() if re.search(pattern, text, re.I)]
    if software:
        model["software"] = [{"name": name} for name in software]
    match = re.search(FORCE_FIELD_PATTERN, text, re.I)
    if match:
        model["force_field"] = match.group("ff")
    for solvent, pattern in spec.solvent_patterns.items():
        if re.search(pattern, text, re.I):
            model["solvent"] = solvent
            break
    return model


def detect_construct(text, spec, method="regex_title_abstract", confidence="low"):
    """The simulated construct, only when the text states a residue/nucleotide range."""
    match = CONSTRUCT_PATTERN.search(clean_text(text))
    if not match:
        return None
    start, end = match.group("start"), match.group("end")
    key = "nucleotide_range" if re.search(r"nucleotides?|\bnt\b", match.group(0), re.I) \
        else "residue_range"
    return {key: f"{start}-{end}",
            "evidence": [evidence("system.construct", method, text, match, confidence)]}


def detect_unit_system(text, spec, method="regex_title_abstract", confidence="low"):
    """Return (unit_system, unit_conversions or None) for the model."""
    text = normalise_scientific(clean_text(text))
    low = (text or "").lower()
    conversions = {}
    for key, pattern in spec.conversion_patterns.items():
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        resolved = normalise_unit(match.group("unit"), spec)
        if resolved is None:
            continue
        conversions[key] = {
            "value": float(match.group("value")),
            "unit": resolved[0],
            "note": "stated conversion between model (reduced) and physical units",
            # the published Quantity definition carries a single Evidence object
            "evidence": evidence(f"model.unit_conversions.{key}", method, text, match, confidence),
        }
    reduced = any(marker in low for marker in spec.reduced_markers)
    if reduced:
        return ("reduced_with_stated_conversion" if conversions else "reduced"), (conversions or None)
    return "physical", (conversions or None)


def _anchor(text, verb_pattern, field, method, confidence):
    pattern = (verb_pattern + r"[^.]{0,60}?(?P<what>(?:residues?|atoms?|nucleotides?|nt)\s*"
               r"[0-9]+\s*[-–to]+\s*[0-9]+|(?:residues?|atoms?|nucleotides?|nt)\s*[0-9]+|"
               r"[NC][- ]terminus|5'|3'|the [A-Za-z0-9+\-]+ (?:domain|end|terminus|loop|hairpin))")
    match = re.search(pattern, text, re.I)
    if not match:
        return None, None
    what = match.group("what").strip()
    anchor = {"description": what, "evidence": [evidence(field, method, text, match, confidence)]}
    rng = RESIDUE_RANGE_PATTERN.search(what)
    if rng:
        anchor["residue_range"] = f"{rng.group(1)}-{rng.group(2)}"
    low = what.lower()
    if "terminus" in low:
        anchor["end"] = "N_terminus" if low.startswith("n") else "C_terminus"
    elif what.startswith("5'"):
        anchor["end"] = "5_prime"
    elif what.startswith("3'"):
        anchor["end"] = "3_prime"
    return anchor, match


def detect_geometry(text, spec, method="regex_title_abstract", confidence="low"):
    """Pulling geometry in the experimental representation, plus anchors."""
    text = clean_text(text)
    geometry = {}
    for name, pattern in GEOMETRY_PATTERNS:
        match = re.search(pattern, text, re.I)
        if match:
            geometry["force_application_geometry"] = name
            geometry["evidence"] = [evidence("protocol.geometry.force_application_geometry",
                                              method, text, match, confidence)]
            break
    fixed, fixed_match = _anchor(text, r"(?:fix(?:ed|ing)?|held fixed|restrain\w*|frozen|pinned|"
                                       r"anchor\w*|tether\w*)",
                                 "protocol.geometry.anchor_a", method, confidence)
    pulled, pull_match = _anchor(text, r"(?:pull(?:ed|ing)?|unfold\w*|unzip\w*|stretch\w*)",
                                 "protocol.geometry.anchor_b", method, confidence)
    if fixed:
        geometry["anchor_a"] = fixed
    if pulled:
        geometry["anchor_b"] = pulled
    direction = re.search(r"(?:along|in) the (?P<axis>[xyz]|end[- ]to[- ]end|reaction[- ]coordinate|"
                          r"unfolding|pulling|separation) (?:axis|direction|coordinate)", text, re.I)
    if direction:
        geometry["pull_direction"] = direction.group("axis")
        geometry.setdefault("evidence", []).append(
            evidence("protocol.geometry.pull_direction", method, text, direction, confidence))
    if geometry and "force_application_geometry" not in geometry:
        # a forced simulation with no stated instrument geometry is 'other', not guessed
        geometry["force_application_geometry"] = "other"
    if fixed or pulled:
        anchor_text = fixed_match if fixed_match else pull_match
        geometry.setdefault("description", snippet(text, anchor_text, 40, 40))
    return geometry


def detect_protocol(text, spec, method="regex_title_abstract", confidence="low"):
    """Protocol mode, pulling speed, spring, temperature, trajectories, geometry."""
    text = normalise_scientific(clean_text(text))
    protocol = {}
    for mode, pattern in spec.mode_patterns.items():
        match = re.search(pattern, text, re.I)
        if match:
            protocol["mode"] = mode
            protocol["evidence"] = [evidence("protocol.mode", method, text, match, confidence)]
            break
    speed = re.search(SPEED_PATTERN, text, re.I)
    if speed and _value_boundary_ok(text, speed) and _unit_boundary_ok(text, speed):
        resolved = normalise_unit(speed.group("unit"), spec)
        if resolved:
            unit = resolved[0]
            protocol["pulling_speed"] = {"value": float(speed.group("value")), "unit": unit}
            factor = SPEED_TO_M_PER_S.get(unit)
            if factor is not None:
                protocol["pulling_speed_m_per_s"] = float(speed.group("value")) * factor
            protocol.setdefault("evidence", []).append(
                evidence("protocol.pulling_speed", method, text, speed, confidence))
    spring = re.search(SPRING_PATTERN, text, re.I)
    if spring and _value_boundary_ok(text, spring) and _unit_boundary_ok(text, spring):
        protocol["spring_constant"] = {"value": float(spring.group("value")),
                                       "unit": spring.group("unit")}
        protocol.setdefault("evidence", []).append(
            evidence("protocol.spring_constant", method, text, spring, confidence))
    temperature = re.search(TEMPERATURE_PATTERN, text, re.I)
    if temperature and _value_boundary_ok(text, temperature):
        protocol["temperature"] = {"value": float(temperature.group("value")),
                                   "unit": "K" if temperature.group("unit").lower().startswith("k") else "K"}
        protocol.setdefault("evidence", []).append(
            evidence("protocol.temperature", method, text, temperature, confidence))
    trajectories = re.search(TRAJECTORY_PATTERN, text, re.I)
    if trajectories and _value_boundary_ok(text, trajectories):
        protocol["n_trajectories"] = int(trajectories.group("value"))
        protocol.setdefault("evidence", []).append(
            evidence("protocol.n_trajectories", method, text, trajectories, confidence))
    sim_time = re.search(SIM_TIME_PATTERN, text, re.I)
    if sim_time and _value_boundary_ok(text, sim_time) and _unit_boundary_ok(text, sim_time):
        unit = normalise_unit(sim_time.group("unit"), spec)
        if unit:
            protocol["simulated_time_per_trajectory"] = {"value": float(sim_time.group("value")),
                                                         "unit": unit[0]}
            protocol.setdefault("evidence", []).append(
                evidence("protocol.simulated_time_per_trajectory", method, text, sim_time, confidence))
    force_range = re.search(FORCE_RANGE_PATTERN, text, re.I)
    if force_range and _value_boundary_ok(text, force_range) and _unit_boundary_ok(text, force_range):
        unit = normalise_unit(force_range.group("unit"), spec)
        if unit:
            protocol["force_range"] = {"value": float(force_range.group("value")), "unit": unit[0]}
    geometry = detect_geometry(text, spec, method, confidence)
    if geometry:
        protocol["geometry"] = geometry
    return protocol


def detect_artifacts(text, spec, method="regex_fulltext_methods", confidence="medium"):
    """Whether trajectories, force-extension curves, input files and scripts are shared."""
    text = clean_text(text)
    artifacts = {}
    for name, pattern in spec.artifact_patterns.items():
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        item = {"available": True, "statement": snippet(text, match, 40, 60),
                "evidence": [evidence(f"data_availability.{name}.available", method, text, match,
                                      confidence)]}
        formats = [fmt for fmt in spec.raw_formats if re.search(rf"\.?{re.escape(fmt)}\b", text, re.I)]
        if formats:
            item["formats"] = sorted(set(formats))
        artifacts[name] = item
    return artifacts


def detect_data(text, spec, method="regex_title_abstract", confidence="low"):
    """Data availability, repository links and shared simulation artifacts."""
    text = clean_text(text)
    availability = {"status": "not_stated"}
    urls = {}
    for match in re.finditer(REPO_URL_PATTERN, text, re.I):
        host = match.group(1).lower()
        repository = ("GitHub" if "github" in host else "Zenodo" if "zenodo" in host or "5281" in host
                      else "Figshare" if "figshare" in host else "Dryad" if "dryad" in host
                      else "OSF" if "osf" in host else "Fairdata" if "fairdata" in host
                      else "BioStudies" if "ebi.ac.uk" in host else "Materials Cloud")
        urls.setdefault(repository, []).append(match.group(0).rstrip("."))
    on_request = re.search(ON_REQUEST_PATTERN, text, re.I)
    not_available = re.search(NOT_AVAILABLE_PATTERN, text, re.I)
    datasets = [{"id": url, "url": url, "repository": repo}
                for repo, repo_urls in urls.items() for url in repo_urls if repo != "GitHub"]
    code = [{"id": url, "url": url, "repository": "GitHub"} for url in urls.get("GitHub", [])]
    if urls:
        if datasets:
            availability.update({"status": "public_repository", "has_linked_dataset": True,
                                 "has_any_data": True, "datasets": datasets})
            match = re.search(REPO_URL_PATTERN, text, re.I)
            availability["statement"] = snippet(text, match, 60, 40)
        elif code:
            availability.update({"status": "code_only", "has_linked_dataset": False,
                                 "has_any_data": True})
        if code:
            availability["code"] = code
    elif on_request:
        availability.update({"status": "on_request", "has_linked_dataset": False,
                             "statement": snippet(text, on_request, 60, 40)})
    elif not_available:
        availability.update({"status": "not_available", "has_linked_dataset": False,
                             "statement": snippet(text, not_available, 60, 40)})
    artifacts = detect_artifacts(text, spec, method=("regex_fulltext_methods" if method !=
                                                     "regex_title_abstract" else method),
                                 confidence=confidence)
    if artifacts:
        availability.update(artifacts)
        availability.setdefault("has_any_data", True)
    return availability