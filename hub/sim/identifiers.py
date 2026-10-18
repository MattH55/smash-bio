"""Identifier grounding for the Simulations category.

The shared resolver table (``modules/identifiers.py``) covers UniProt, Rfam,
ChEBI, GO, Cell Ontology and GenBank; this module reads it and additionally
checks PDB entries against RCSB. Codes confirmed for *this* category are kept in
``sim/verified_identifiers.json`` rather than in the shared table, so the
Simulations branch never writes to a file the other branches own. Nothing is
ever written to a record unless :func:`verify` returned true.
"""
import json
from pathlib import Path

from common import get
from modules import identifiers as shared

SCHEMES = ("pdb",) + tuple(shared.SCHEMES)
TABLE_PATH = Path(__file__).resolve().parent / "verified_identifiers.json"


def _table():
    if TABLE_PATH.exists():
        try:
            return json.loads(TABLE_PATH.read_text(encoding="utf-8"))
        except ValueError:  # pragma: no cover - corrupt table
            return {}
    return {}


def verify_pdb(pdb_id, persist=True):
    """True only when the RCSB entry API returns this exact entry id.

    The result is written to the category table, so each PDB entry is checked
    against RCSB at most once (negative results included).
    """
    pdb_id = (pdb_id or "").strip().upper()
    if len(pdb_id) != 4:
        return False
    table = _table()
    key = f"pdb:{pdb_id}"
    if key in table:
        return bool(table[key].get("verified"))
    data = get(f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}", retries=1, timeout=20)
    containers = (data or {}).get("rcsb_entry_container_identifiers") or {}
    ok = str(containers.get("entry_id", "")).upper() == pdb_id
    if persist:
        table[key] = {"scheme": "pdb", "id": pdb_id, "verified": ok}
        TABLE_PATH.write_text(json.dumps(table, ensure_ascii=False, indent=1, sort_keys=True),
                              encoding="utf-8")
    return ok


def verify(scheme, value):
    row = _table().get(f"{scheme}:{value}")
    if row is not None:
        return bool(row.get("verified"))
    if scheme == "pdb":
        return verify_pdb(value)
    return shared.verify(scheme, value)


def identifier(scheme, value, **extra):
    row = {"scheme": scheme, "id": value, "verified": verify(scheme, value)}
    row.update(extra)
    return row


def verified_only(rows):
    """Keep only the identifiers a resolver confirmed (no unverified code is published)."""
    return [dict(row) for row in rows or [] if row.get("verified")]


def warm(pairs, verbose=True, limit=None):
    """Confirm codes online and record them in the category's own table.

    The resolver functions are the shared ones (``modules.identifiers._CHECKERS``),
    but the results are written here, not into the shared table.
    """
    table = dict(_table())
    checkers = dict(getattr(shared, "_CHECKERS", {}))
    done = 0
    for scheme, value in pairs:
        key = f"{scheme}:{value}"
        if not value or key in table or (limit is not None and done >= limit):
            continue
        checker = verify_pdb if scheme == "pdb" else checkers.get(scheme)
        if checker is None:
            continue
        try:
            ok = bool(checker(value))
        except Exception as exc:  # pragma: no cover - network flake
            ok = False
            if verbose:
                print(f"  ! {key} failed ({exc!r})", flush=True)
        table[key] = {"scheme": scheme, "id": value, "verified": ok}
        TABLE_PATH.write_text(json.dumps(table, ensure_ascii=False, indent=1, sort_keys=True),
                              encoding="utf-8")
        done += 1
        if verbose:
            print(f"  {'ok ' if ok else 'NO '} {key}", flush=True)
    return done, table