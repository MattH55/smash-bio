"""Europe PMC harvest for the Simulations category.

This is a deliberate thin shim: the Simulations category uses the **existing**
harvester (``modules.harvest.harvest``) unchanged, so the caching, the
half-rate pacing (``RATE_FACTOR = 2.0``) and the resumable JSONL behaviour are
the same code paths the technique modules already exercise. Only the query
fragments differ, and those live in ``sim/spec.py`` (``SIM.harvest_queries``).

The brief's rule is that new pipeline code calls the existing harvester rather
than forking it; this module exists so that ``sim.run`` has a single import
point and so the delegation is explicit and testable.
"""
from modules.harvest import RATE_FACTOR, harvest as _harvest, polite_get, slim

__all__ = ["harvest", "polite_get", "slim", "RATE_FACTOR"]


def harvest(spec, **kwargs):
    """Harvest one spec with the shared, cached, half-rate Europe PMC harvester."""
    return _harvest(spec, **kwargs)