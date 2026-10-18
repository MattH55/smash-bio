"""Methods text for the Simulations category.

Re-exported from ``modules.fulltext`` (the SMFS step-5 fetcher/parser and its
parsed-text cache) so the category uses one shared, cached full-text layer
instead of a second one. Nothing here is copied or modified.
"""
from modules.fulltext import (  # noqa: F401  (re-exported)
    build_index,
    data_availability,
    index_path,
    load_index,
    methods_for,
    parsed_for,
)

__all__ = ["build_index", "data_availability", "index_path", "load_index",
           "methods_for", "parsed_for"]