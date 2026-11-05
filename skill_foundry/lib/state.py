#!/usr/bin/env python3
"""State schema versions + idempotent migration (run.json / catalog.json).

Older on-disk state is upgraded on load so readers never have to know about
historical formats. Bump a version and extend the corresponding migrate_* when
the shape changes.
"""

from __future__ import annotations

from typing import Any

RUN_SCHEMA_VERSION = 1
CATALOG_VERSION = 1


def migrate_run(record: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a run.json record to the current schema (idempotent, in place)."""
    v = record.get("schema_version")
    if v is None:
        # v0 → v1: no structural change — just stamp the version so future
        # migrations have a known starting point.
        record["schema_version"] = RUN_SCHEMA_VERSION
        return record
    if not isinstance(v, int) or v > RUN_SCHEMA_VERSION:
        raise ValueError(
            f"run.json schema {v!r} is newer than supported {RUN_SCHEMA_VERSION}"
        )
    return record


def migrate_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a hub/catalog.json record to the current version (idempotent)."""
    v = catalog.get("version")
    if v is None:
        catalog["version"] = CATALOG_VERSION
        return catalog
    if not isinstance(v, int) or v > CATALOG_VERSION:
        raise ValueError(
            f"catalog version {v!r} is newer than supported {CATALOG_VERSION}"
        )
    return catalog
