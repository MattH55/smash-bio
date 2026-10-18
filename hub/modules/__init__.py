"""SMASH-BIO technique modules.

Each technique family (smFRET, single-particle tracking, mass photometry,
single-channel electrophysiology) is described by a single :class:`ModuleSpec`
and runs on the shared machinery in this package: harvest -> classify -> extract
-> build records -> build outputs -> cross-reference.

The package is intentionally additive: it never edits the SMFS pipeline scripts
or the published SMFS schemas. Run a module with::

    python -m modules.run fret --step classify

from the ``hub/`` directory.
"""
from modules.base import ModuleSpec, MODULES, get_module, ta

__all__ = ["ModuleSpec", "MODULES", "get_module", "ta"]