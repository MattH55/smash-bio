"""Scope classification for the Simulations category.

Tier labels are the brief's own:

    core          simulates mechanical pulling or force-driven unfolding/unbinding
                  of a biomolecule
    methods       new pulling-simulation methods, models or benchmarks
    out_of_scope  equilibrium MD without force; materials; non-biological polymers

Precedence is deliberate and documented: an explicit exclusion, or the absence
of both force and simulation evidence, is `out_of_scope`; otherwise a paper that
reads as method/model/benchmark development is `methods`; otherwise, when a
biomolecule is identified as the simulated system, it is `core`. Only `core` and
`methods` rows become records.
"""
import re
from collections import Counter


METHODS_PATTERN = (
    r"(\bbenchmark\w*|we (?:present|introduce|develop|propose|report) (?:a|an|the)? ?"
    r"(?:new|novel|general|unified)|method development|new (?:method|model|algorithm|approach|"
    r"framework|protocol)|force[- ]field (?:development|parameteri[sz]ation)|"
    r"(?:open[- ]source|freely available) (?:software|tool|package)|validation (?:study|benchmark)|"
    r"comparison of (?:models|methods|simulation))"
)


def article_text(article):
    return " ".join(filter(None, [
        article.get("title"),
        article.get("abstract"),
        " ".join(filter(None, article.get("keywords") or [])),
        " ".join(filter(None, article.get("mesh") or [])),
    ]))


def detect_molecule_type(text, spec):
    """First matching molecule type in spec order, else None."""
    for molecule_type, pattern in spec.molecule_patterns.items():
        if re.search(pattern, text, re.I):
            return molecule_type
    return None


def detect_model_families(text, spec):
    """All matching model families, most specific first."""
    families = [family for family, pattern in spec.model_family_patterns.items()
                if re.search(pattern, text, re.I)]
    if "Go_heavy_atom" in families and "Go_CA" in families:
        families.remove("Go_CA")  # a heavy-atom Go model also matches the generic Go pattern
    return families


def classify(article, spec):
    """Return (row, tier). `row` is None for out_of_scope rows."""
    text = article_text(article)
    forcing = re.search(spec.forcing_pattern, text, re.I)
    simulation = bool(re.search(spec.simulation_pattern, text, re.I))
    excluded = bool(re.search(spec.out_of_scope_pattern, text, re.I))
    molecule_type = detect_molecule_type(text, spec)
    families = detect_model_families(text, spec)
    is_review = any("review" in str(p).lower() for p in article.get("pub_types") or [])
    is_methods_paper = bool(re.search(METHODS_PATTERN, text, re.I))

    reasons = []
    if excluded:
        reasons.append("explicit-exclusion")
    if not forcing:
        reasons.append("no-force-evidence")
    if not simulation:
        reasons.append("no-simulation-evidence")
    if reasons:
        return None, "out_of_scope"
    if molecule_type is None:
        return None, "out_of_scope"
    if is_methods_paper:
        return ({"tier": "methods", "scope_reasons": ["methods-or-benchmark"],
                 "molecule_type": molecule_type, "model_families": families,
                 "is_review": is_review, "is_methods_paper": True,
                 "forcing_snippet": forcing.group(0)}, "methods")
    return ({"tier": "core", "scope_reasons": ["force-driven-simulation-of-a-biomolecule"],
             "molecule_type": molecule_type, "model_families": families,
             "is_review": is_review, "is_methods_paper": False,
             "forcing_snippet": forcing.group(0)}, "core")


def classify_all(articles, spec):
    """Classify a list of articles. Returns (kept_rows, tier_counts)."""
    kept, tiers = [], Counter()
    for article in articles:
        row, tier = classify(article, spec)
        tiers[tier] += 1
        if row is None:
            continue
        merged = dict(article)
        merged.update(row)
        kept.append(merged)
    return kept, tiers