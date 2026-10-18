"""Validate the generated SMASH-BIO XML sitemap set.

Run from ``hub/`` with ``python validate_sitemap.py``.  Step 7 also calls the
validator automatically, so invalid sitemap output cannot silently ship.
"""
from __future__ import annotations

import datetime
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
NS = {"sm": SITEMAP_NS}
SITE_HOST = "smash-bio.org"
MAX_ENTRIES = 50_000
MAX_BYTES = 50 * 1024 * 1024


def _valid_lastmod(value: str) -> bool:
    try:
        datetime.date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def _assert_public_url(value: str, context: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc != SITE_HOST:
        raise ValueError(f"{context}: URL is not on the canonical HTTPS host: {value}")
    if parsed.fragment:
        raise ValueError(f"{context}: sitemap URLs must not contain fragments: {value}")


def validate_sitemaps(web: Path, expected_records: int | None = None,
                      expected_systems: int | None = None) -> dict[str, int]:
    """Validate the index and every referenced child; return URL counts."""
    index_path = web / "sitemap.xml"
    index = ET.parse(index_path).getroot()
    if index.tag != f"{{{SITEMAP_NS}}}sitemapindex":
        raise ValueError("sitemap.xml is not a sitemap index in the sitemap namespace")

    children: list[Path] = []
    for item in index.findall("sm:sitemap", NS):
        loc = item.findtext("sm:loc", namespaces=NS)
        lastmod = item.findtext("sm:lastmod", namespaces=NS)
        _assert_public_url(loc or "", "sitemap.xml")
        if not _valid_lastmod(lastmod or ""):
            raise ValueError(f"sitemap.xml: invalid lastmod {lastmod!r}")
        name = Path(urlparse(loc).path).name
        child = web / name
        if not child.is_file():
            raise ValueError(f"sitemap.xml references missing child {name}")
        children.append(child)

    generated_children = set(web.glob("sitemap-*.xml"))
    if set(children) != generated_children:
        missing = sorted(p.name for p in generated_children - set(children))
        raise ValueError(f"sitemap.xml does not reference generated children: {missing}")

    seen: set[str] = set()
    counts = {"sitemaps": len(children), "urls": 0, "records": 0, "systems": 0}
    for child in children:
        if child.stat().st_size > MAX_BYTES:
            raise ValueError(f"{child.name} exceeds the 50 MB sitemap limit")
        root = ET.parse(child).getroot()
        if root.tag != f"{{{SITEMAP_NS}}}urlset":
            raise ValueError(f"{child.name} is not a URL set in the sitemap namespace")
        entries = root.findall("sm:url", NS)
        if len(entries) > MAX_ENTRIES:
            raise ValueError(f"{child.name} exceeds the 50,000 URL sitemap limit")
        for item in entries:
            loc = item.findtext("sm:loc", namespaces=NS)
            lastmod = item.findtext("sm:lastmod", namespaces=NS)
            _assert_public_url(loc or "", child.name)
            if loc in seen:
                raise ValueError(f"duplicate sitemap URL: {loc}")
            seen.add(loc)
            if not _valid_lastmod(lastmod or ""):
                raise ValueError(f"{child.name}: invalid lastmod {lastmod!r} for {loc}")
            parsed = urlparse(loc)
            query = parse_qs(parsed.query)
            counts["records"] += parsed.path == "/record.html" and "id" in query
            counts["systems"] += parsed.path == "/system.html" and "s" in query
        counts["urls"] += len(entries)

    if expected_records is not None and counts["records"] != expected_records:
        raise ValueError(f"expected {expected_records} record URLs, found {counts['records']}")
    if expected_systems is not None and counts["systems"] != expected_systems:
        raise ValueError(f"expected {expected_systems} system URLs, found {counts['systems']}")
    return counts


if __name__ == "__main__":
    website = Path(__file__).resolve().parent.parent / "website"
    try:
        result = validate_sitemaps(website)
    except (ET.ParseError, OSError, ValueError) as exc:
        raise SystemExit(f"sitemap validation failed: {exc}") from exc
    print("sitemap valid:", ", ".join(f"{key}={value}" for key, value in result.items()))