"""Vendor a 250-row sample of property seed data.

Downloads historical parquet snapshots from
``Sekirkallc/ai-data-factory-real-estate`` (Hugging Face, MIT) and writes
``app/seed_data/properties.json`` in our schema, with Picsum placeholder image
URLs. Run once; the JSON is then committed and the runtime stays dep-free.

Re-run only if the source dataset changes. Requires ``pyarrow`` (dev dep).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "app" / "seed_data" / "properties.json"

DATASET_BASE = (
    "https://huggingface.co/datasets/Sekirkallc/ai-data-factory-real-estate"
)
TREE_URL = f"{DATASET_BASE}/tree/main"

PROPERTY_TYPES = ["APARTMENT", "HOUSE", "VILLA", "STUDIO", "OFFICE"]
LISTING_TYPES = ["SALE", "RENT"]


def fetch_tree_files() -> list[str]:
    req = urllib.request.Request(TREE_URL, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req) as r:
        print("TREE status:", r.status, "content-length:", r.headers.get("content-length"))
        body = r.read()
    print("TREE body len:", len(body), "first 50:", body[:50])
    data = json.loads(body)
    return [f["path"] for f in data if f.get("path", "").endswith(".parquet")]


def download(url: str, dest: Path) -> None:
    if dest.exists():
        return
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req) as r:
        body = r.read()
    with dest.open("wb") as f:
        f.write(body)


def load_snapshot(path: Path) -> list[dict]:
    table = pq.read_table(path)
    return table.to_pylist()


def normalize(row: dict, idx: int) -> dict:
    bedrooms = row.get("bedrooms", row.get("beds"))
    bathrooms = row.get("bathrooms", row.get("baths"))
    sqft = row.get("sqft")
    description = row.get("description") or ""

    if sqft is not None:
        area_sqm = round(float(sqft) * 0.092903, 2)
    else:
        area_sqm = None

    lat_base, lon_base = 25.7617, -80.1918
    rng = random.Random(row.get("id", str(idx)))
    lat = round(lat_base + rng.uniform(-0.1, 0.1), 6)
    lon = round(lon_base + rng.uniform(-0.1, 0.1), 6)

    seed_key = f"{row.get('id', idx)}-{idx}"
    digest = int(hashlib.md5(seed_key.encode()).hexdigest(), 16)
    prop_type = PROPERTY_TYPES[digest % len(PROPERTY_TYPES)]
    listing_type = LISTING_TYPES[(digest >> 1) % len(LISTING_TYPES)]

    seed_id = row.get("id", f"prop_{idx:06d}")
    images = [
        {
            "url": f"https://picsum.photos/seed/{seed_id}-{idx}-{i}/800/600",
            "sort_order": i,
            "alt": f"Property {seed_id} photo {i + 1}",
        }
        for i in range(2)
    ]

    return {
        "title": str(row.get("title", "")).strip() or "Untitled",
        "description": description,
        "property_type": prop_type,
        "listing_type": listing_type,
        "price_amount": float(row["price"]),
        "price_currency": "USD",
        "bedrooms": int(bedrooms) if bedrooms is not None else None,
        "bathrooms": int(bathrooms) if bathrooms is not None else None,
        "area_sqm": area_sqm,
        "address_line": str(row.get("location", "")).strip() or "Unknown",
        "city": "Miami",
        "district": "FL",
        "postal_code": None,
        "country_code": "US",
        "latitude": lat,
        "longitude": lon,
        "status": "AVAILABLE",
        "amenities": [],
        "images": images,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=REPO_ROOT / ".cache" / "seed-vendor",
        help="Where downloaded parquet snapshots are cached.",
    )
    args = parser.parse_args()

    cache_dir = args.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)

    print("listing timestamped parquets on main...")
    timestamped: list[str] = []
    try:
        tree_paths = fetch_tree_files()
        timestamped = [
            p for p in tree_paths if p.startswith("data_") and p.endswith(".parquet")
        ]
        print(f"  found {len(timestamped)} timestamped parquets on main")
    except Exception as e:
        print(f"  tree API failed ({e}); falling back to cache")

    rows: list[dict] = []
    if timestamped:
        for p in timestamped:
            dest = cache_dir / Path(p).name
            print(f"  downloading {p} -> {dest.name}")
            download(f"{DATASET_BASE}/resolve/main/{p}", dest)
            rows.extend(load_snapshot(dest))
    else:
        cached = sorted(
            p for p in cache_dir.glob("data_*.parquet") if p.is_file()
        )
        print(f"  using {len(cached)} cached parquets")
        for dest in cached:
            rows.extend(load_snapshot(dest))

    print(f"total raw rows: {len(rows)}")

    rng = random.Random(args.seed)
    rng.shuffle(rows)
    sampled = rows[: args.count]
    print(f"sampled: {len(sampled)}")

    normalized = [normalize(r, i) for i, r in enumerate(sampled)]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
