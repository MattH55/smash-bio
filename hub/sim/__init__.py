"""SMASH-SIM: the Simulations category of SMASH-BIO.

Simulations get the same treatment as the experimental force-spectroscopy
records (harvest -> classify -> extract -> build records -> validate ->
publish), but they are a **separate category**: their own record type
(``SIM-######``), their own pages under ``/sim/``, their own downloads, and a
visible label everywhere. They exist to be compared with experiments, never to
stand in for them.

The package is additive: it calls the shared harvester, gazetteer, resolvers and
extractors in ``hub/common.py`` and ``hub/modules/`` and never edits them, the
SMFS pipeline, or the published schemas.

Run it from the ``hub/`` directory::

    python -m sim.run --step all
"""

from sim.spec import SIM, SimSpec

__all__ = ["SIM", "SimSpec"]