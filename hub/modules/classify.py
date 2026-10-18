"""Scope classification shared by every technique module.

tier:
  core        module technique + a biological system + single-molecule evidence
  methods     instrument / analysis / benchmark development for the technique
  peripheral  technique on a biological sample but without single-molecule evidence
  out         explicitly excluded, non-biological, or no technique detected
"""
import re
from collections import Counter


def article_text(article):
    return " ".join(filter(None, [
        article.get("title"),
        article.get("abstract"),
        " ".join(filter(None, article.get("keywords") or [])),
        " ".join(filter(None, article.get("mesh") or [])),
    ]))


def classify(article, spec):
    """Return (tier, techniques, reasons, is_review) for one article."""
    text = article_text(article)
    tech = [tag for tag, pattern in spec.technique_patterns.items()
            if re.search(pattern, text, re.I)]
    bio = bool(re.search(spec.bio_pattern, text, re.I))
    single = bool(re.search(spec.single_molecule_pattern, text, re.I))
    methods = bool(re.search(spec.methods_pattern, text, re.I))
    excluded = bool(re.search(spec.out_of_scope_pattern, text, re.I))
    is_review = any("review" in str(p).lower() for p in article.get("pub_types") or [])

    if not tech:
        return "out", [], ["no-technique"], is_review
    if excluded and not (bio and single):
        return "out", tech, ["explicit-exclusion"], is_review
    if bio and single:
        return "core", tech, ["technique+biology+single-molecule"], is_review
    if methods:
        return "methods", tech, ["instrument-or-analysis"], is_review
    return "peripheral", tech, ["weak-single-molecule-evidence"], is_review


def classify_all(articles, spec):
    """Classify a list of articles; drop `out`, return (kept, tier_counts)."""
    kept, tiers = [], Counter()
    for article in articles:
        tier, tech, reasons, is_review = classify(article, spec)
        tiers[tier] += 1
        if tier == "out":
            continue
        row = dict(article)
        row.update({
            "tier": tier,
            "techniques_detected": tech,
            "scope_reasons": reasons,
            "is_review": is_review,
        })
        kept.append(row)
    return kept, tiers