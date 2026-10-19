"""Motor-family classification for the SMASH-BIO Motors module (BRIEF_MOTORS.md, task 1c).

classify(title, abstract, entities) -> MotorCall

Order: canonical entity names from hub/gazetteer.py first, then title regexes. A family is attached unless the only
motor-like entities are myosin II / muscle (out of scope) or the myosin call rests on a title in a muscle context.
Gliding / ensemble assays are attached and labelled assay_type = gliding_or_ensemble. The SMASH-BIO experiment class is
not required (author decision at Gate 1, A). The gazetteer is hub/data/motor_gazetteer.yaml.
Nothing here invents values: the evidence snippet is the entity's own gazetteer snippet or a span of the title.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

GAZ_PATH = Path(__file__).resolve().parents[1] / "data" / "motor_gazetteer.yaml"
# certainty of the evidence route, before ambiguity between families is taken into account
BASE = {"entity_specific": 1.0, "entity_generic": 0.7, "title": 0.45}


@dataclass
class MotorCall:
    family: str | None                 # family attached to the record, or None
    candidate: str | None              # best family found even when not attached (for review)
    certainty: float                   # 0..1, used to rank records for author review
    confidence: str                    # high / medium / low, written to the evidence object
    route: str                         # entity_specific / entity_generic / title / none
    reason: str                        # why attached or not
    scores: dict = field(default_factory=dict)
    evidence: dict | None = None
    assay_type: str | None = None    # single_molecule / gliding_or_ensemble, set when attached


@lru_cache(maxsize=1)
def gazetteer(path: str = str(GAZ_PATH)) -> dict:
    g = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    ent2fam: dict[str, tuple[str, bool]] = {}
    titles: dict[str, list[re.Pattern]] = {}
    for fam, spec in g["families"].items():
        for e in spec.get("entities") or []:
            ent2fam[e["name"]] = (fam, e.get("specific", True))
        titles[fam] = [re.compile(p, re.I) for p in spec.get("titles") or []]
    ex = g["exclusions"]
    return {"ent2fam": ent2fam, "titles": titles, "excluded": set(ex["entities"]), "never": set(ex["never_resolve"]),
            "gliding": re.compile(ex["gliding"], re.I), "single_molecule": re.compile(ex["single_molecule"], re.I),
            "muscle": re.compile(ex["muscle"], re.I), "families": list(g["families"])}


def _confidence(c: float) -> str:
    return "high" if c >= 0.8 else "medium" if c >= 0.5 else "low"


def classify(title: str, abstract: str, entities: list[dict]) -> MotorCall:
    G = gazetteer()
    title = title or ""
    text = f"{title} {abstract or ''}"
    names = [e.get("name") for e in entities or [] if e.get("name")]
    scores: Counter = Counter()
    route_of: dict[str, str] = {}
    snippet_of: dict[str, str] = {}
    for e in entities or []:
        hit = G["ent2fam"].get(e.get("name"))
        if not hit:
            continue
        fam, specific = hit
        route = "entity_specific" if specific else "entity_generic"
        scores[fam] += 2 if specific else 1
        if route_of.get(fam) != "entity_specific":
            route_of[fam] = route
            snippet_of[fam] = (e.get("evidence") or {}).get("snippet") or e["name"]
    if not scores:  # titles only when no entity resolved a family
        for fam, pats in G["titles"].items():
            for p in pats:
                m = p.search(title)
                if m:
                    scores[fam] += 1
                    route_of[fam] = "title"
                    snippet_of.setdefault(fam, title[max(0, m.start() - 60):m.end() + 60])
                    break
    if not scores:
        if any(n in G["excluded"] for n in names):
            return MotorCall(None, None, 0.0, "low", "none", "excluded entity (myosin II / muscle) and no motor-family entity", {})
        return MotorCall(None, None, 0.0, "low", "none", "no motor family found", {})

    ranked = scores.most_common()
    best, top = ranked[0]
    share = top / sum(scores.values())
    certainty = round(BASE[route_of[best]] * share, 3)
    ev = {"field": "motor.family", "method": "gazetteer", "section": "entities" if route_of[best] != "title" else "title",
          "snippet": snippet_of[best][:300], "confidence": _confidence(certainty)}
    call = MotorCall(None, best, certainty, _confidence(certainty), route_of[best], "", dict(scores), ev)

    has_family_entity = any(n in G["ent2fam"] for n in names)
    if any(n in G["excluded"] for n in names) and not has_family_entity:
        call.reason = "excluded entity (myosin II / muscle) and no motor-family entity"
        return call
    if best == "myosin_processive" and route_of[best] == "title" and G["muscle"].search(text):
        call.reason = "myosin by title only, muscle context"
        return call
    # Gliding / ensemble assays are included (author decision, Gate 1 E) and labelled, not excluded.
    call.assay_type = "gliding_or_ensemble" if G["gliding"].search(text) and not G["single_molecule"].search(text) else "single_molecule"
    call.family = best
    call.reason = "attached"
    return call
