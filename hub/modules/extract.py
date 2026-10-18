"""Conservative, evidence-carrying extraction shared by every module.

A number is extracted only when the text gives the number and its canonical
unit adjacent to a named observable. Every value carries an evidence object so
it can be audited; nothing is inferred.
"""
import re


# Canonical unit per observable. Values must match the module schema.
UNITS = {
    # FRET
    "fret_efficiency_apparent": "1", "fret_efficiency_accurate": "1",
    "fret_efficiency": "1", "stoichiometry": "1",
    "interdye_distance_mean_nm": "nm", "interdye_distance_R_E_nm": "nm",
    "donor_lifetime_ns": "ns", "acceptor_lifetime_ns": "ns", "anisotropy": "1",
    "population_fraction": "1", "n_states": "1", "transition_rate_s-1": "1/s",
    "dwell_time_ms": "ms", "radius_of_gyration_nm": "nm",
    "end_to_end_distance_nm": "nm", "scaling_exponent_nu": "1",
    "dissociation_constant_M": "M", "forster_radius_nm": "nm",
    "binding_rate_kon": "1/(M*s)", "unbinding_rate_koff": "1/s",
    "folding_rate": "1/s", "unfolding_rate": "1/s", "photobleaching_lifetime": "s",
    # SPT
    "diffusion_coefficient_um2_s-1": "um2/s", "anomalous_exponent_alpha": "1",
    "bound_fraction": "1", "residence_time_s": "s", "confinement_radius_nm": "nm",
    "velocity_nm_s-1": "nm/s", "run_length_nm": "nm", "step_size_nm": "nm",
    "localization_precision_nm": "nm", "mean_track_length_frames": "frame",
    "n_diffusive_states": "1",
    # Mass photometry
    "molecular_mass_kDa": "kDa", "relative_abundance": "1",
    "oligomeric_state": "1", "binding_stoichiometry": "1",
    "mass_resolution_kDa": "kDa", "event_count": "1", "aav_full_fraction": "1",
    # Single-channel
    "unitary_conductance_pS": "pS", "unitary_current_pA": "pA",
    "open_probability": "1", "mean_open_time_ms": "ms", "mean_closed_time_ms": "ms",
    "burst_duration_ms": "ms", "n_open_states": "1", "n_closed_states": "1",
    "subconductance_level_pS": "pS", "ec50_M": "M", "reversal_potential_mV": "mV",
}


# Named analysis tools. A tool is only ever reported when the text names it.
KNOWN_SOFTWARE = {
    "FRETBursts": r"\bfretbursts\b", "PAM": r"\bpam\b(?![a-z])",
    "tMAVEN": r"\btmaven\b", "Deep-LASI": r"deep[- ]lasi", "SPARTAN": r"\bspartan\b",
    "iSMS": r"\bisms\b", "MASH-FRET": r"mash[- ]fret", "FRETboard": r"\bfretboard\b",
    "ebFRET": r"\befret\b", "HaMMy": r"\bhammy\b", "vbFRET": r"\bvbfret\b",
    "SMART": r"\bsmart\b(?=[^a-z]|$)", "TrackMate": r"\btrackmate\b",
    "u-track": r"u[- ]track", "SMAP": r"\bsmap\b", "Spot-On": r"spot[- ]on",
    "ThunderSTORM": r"\bthunderstorm\b", "DiscoverMP": r"\bdiscovermp\b",
    "PhotoMol": r"\bphotomol\b", "eSPC": r"\bespc\b", "QuB": r"\bqub\b",
    "HJCFIT": r"\bhjcf?it\b", "DCprogs": r"\bdcprogs\b", "SCAN": r"\bscan\b",
    "Clampfit": r"\bclampfit\b",
}


def extract_results(text, spec, method="regex_title_abstract", confidence="low", max_results=12):
    """Extract grounded results. Returns a list of Result dicts with provenance."""
    text = text or ""
    results = []
    for observable in spec.observables:
        pattern = spec.observable_patterns.get(observable)
        if not pattern:
            continue
        match = re.search(pattern, text, re.I)
        if not match or match.lastindex is None:
            continue
        try:
            value = float(match.group(1))
        except (TypeError, ValueError):
            continue
        results.append({
            "quantity": observable,
            "value": value,
            "unit": UNITS.get(observable, "1"),
            "provenance": [{
                "field": f"results[{len(results)}]",
                "method": method,
                "snippet": text[max(0, match.start() - 40):match.end() + 20][:400],
                "confidence": confidence,
            }],
        })
        if len(results) >= max_results:
            break
    return results


def extract_software(text):
    """Names of analysis tools only when the text names them."""
    text = text or ""
    return [name for name, pattern in KNOWN_SOFTWARE.items() if re.search(pattern, text, re.I)]