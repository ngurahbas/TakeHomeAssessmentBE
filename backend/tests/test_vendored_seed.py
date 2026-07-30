"""Pure-JSON checks against the vendored seed data on disk.

The DB-backed seed tests live in `tests/test_seed_properties.py`. These
checks only read `app/seed_data/properties.json` directly so they do not
need Postgres / Valkey and can run on any host.
"""

from __future__ import annotations

import json
from pathlib import Path

VENDORED_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "seed_data" / "properties.json"
)


def test_vendored_seed_has_us_multi_city_variety() -> None:
    rows = json.loads(VENDORED_PATH.read_text(encoding="utf-8"))

    assert len(rows) == 250

    cities = {r["city"] for r in rows}
    states = {r["district"] for r in rows}
    countries = {r["country_code"] for r in rows}
    statuses = {r["status"] for r in rows}

    assert countries == {"US"}
    assert len(cities) >= 10
    assert len(states) >= 6
    assert statuses == {"AVAILABLE", "RESERVED", "SOLD", "RENTED"}

    for r in rows:
        assert -90 <= r["latitude"] <= 90
        assert -180 <= r["longitude"] <= 180
        assert r["amenities"]
        assert r["images"]
        assert r["address_line"]
