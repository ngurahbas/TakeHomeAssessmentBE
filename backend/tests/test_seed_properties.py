from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _truncate_property(db_pool_seeded):
    """Wipe the `property` table before each seed test so we have a clean count."""
    with db_pool_seeded.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE property RESTART IDENTITY")
    yield


@pytest.fixture
def tmp_seed_path(tmp_path: Path) -> Path:
    rows = [
        {
            "title": "Seeded Property One",
            "description": "From the seed file.",
            "property_type": "HOUSE",
            "listing_type": "SALE",
            "price_amount": 250000.0,
            "price_currency": "USD",
            "bedrooms": 3,
            "bathrooms": 2,
            "area_sqm": 120.0,
            "address_line": "1 Seed Street",
            "city": "Seedville",
            "district": "Seed State",
            "postal_code": "11111",
            "country_code": "US",
            "latitude": 10.0,
            "longitude": 20.0,
            "status": "AVAILABLE",
            "amenities": ["parking"],
            "images": [
                {
                    "url": "https://example.com/seeded.jpg",
                    "sort_order": 0,
                    "alt": "exterior",
                }
            ],
        }
    ]
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def test_ensure_seed_properties_inserts_rows(db_pool_seeded, tmp_seed_path):
    from app.seed import ensure_seed_properties
    from app.settings import Settings

    pool = db_pool_seeded
    settings = Settings(
        database_url="",
        seed_properties_enabled=True,
        seed_properties_path=str(tmp_seed_path),
    )
    ensure_seed_properties(settings, pool)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM property")
            (count,) = cur.fetchone()
    assert count == 1


def test_ensure_seed_properties_is_idempotent(db_pool_seeded, tmp_seed_path):
    from app.seed import ensure_seed_properties
    from app.settings import Settings

    pool = db_pool_seeded
    settings = Settings(
        database_url="",
        seed_properties_enabled=True,
        seed_properties_path=str(tmp_seed_path),
    )
    ensure_seed_properties(settings, pool)
    ensure_seed_properties(settings, pool)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM property")
            (count,) = cur.fetchone()
    assert count == 1


def test_ensure_seed_properties_disabled_is_noop(
    db_pool_seeded, tmp_seed_path
):
    from app.seed import ensure_seed_properties
    from app.settings import Settings

    pool = db_pool_seeded
    settings = Settings(
        database_url="",
        seed_properties_enabled=False,
        seed_properties_path=str(tmp_seed_path),
    )
    ensure_seed_properties(settings, pool)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM property")
            (count,) = cur.fetchone()
    assert count == 0


def test_ensure_seed_properties_missing_file_warns(
    db_pool_seeded, tmp_path, caplog
):
    from app.seed import ensure_seed_properties
    from app.settings import Settings

    settings = Settings(
        database_url="",
        seed_properties_enabled=True,
        seed_properties_path=str(tmp_path / "does-not-exist.json"),
    )
    ensure_seed_properties(settings, db_pool_seeded)
    assert "property seed file not found" in caplog.text
