"""The ModuleSpec contract and the module registry."""
from dataclasses import dataclass, field
from pathlib import Path


def ta(*phrases):
    """Europe PMC TITLE_ABS OR-query over the given phrases."""
    return "(" + " OR ".join(f'TITLE_ABS:"{p}"' for p in phrases) + ")"


@dataclass(frozen=True)
class ModuleSpec:
    slug: str                       # "spt" -> cache/out prefixes and page path
    name: str                       # human name
    short: str                      # short label for navigation
    nav_label: str
    record_prefix: str              # "SPT"
    schema_file: str                # relative to website/schema (or modules/)
    results_schema_file: str
    version: str
    schema_subdir: str              # "modules" or "" (schema root, e.g. smFRET)
    harvest_queries: dict           # tag -> Europe PMC query fragment
    technique_patterns: dict        # tag -> regex
    bio_pattern: str                # biological-system regex
    single_molecule_pattern: str    # evidence this is single-molecule at all
    methods_pattern: str            # instrument/analysis-development regex
    out_of_scope_pattern: str       # explicit exclusions
    observables: tuple
    observable_patterns: dict       # observable -> regex with one numeric group
    raw_formats: tuple
    repositories: tuple
    citation_dois: tuple = ()
    extra: dict = field(default_factory=dict)

    @property
    def record_id_pattern(self):
        return rf"^{self.record_prefix}-[0-9]{{6}}$"

    def record_id(self, number):
        return f"{self.record_prefix}-{int(number):06d}"

    def page_path(self):
        return f"/{self.slug}/"

    def out_prefix(self):
        return self.slug


def _registry():
    from modules import channel, fret, mp, spt
    specs = (fret.FRET, spt.SPT, mp.MP, channel.CHANNEL)
    return {spec.slug: spec for spec in specs}


MODULES = _registry()


def get_module(slug):
    try:
        return MODULES[slug]
    except KeyError as exc:  # pragma: no cover - defensive
        raise KeyError(f"unknown module {slug!r}; known: {sorted(MODULES)}") from exc


def hub_dir():
    return Path(__file__).resolve().parent.parent