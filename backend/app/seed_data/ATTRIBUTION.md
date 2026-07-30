# Seed data attribution

## `properties.json`

A 250-row sample of property records adapted from the public dataset:

> **Sekirkallc/ai-data-factory-real-estate** — Hugging Face
> https://huggingface.co/datasets/Sekirkallc/ai-data-factory-real-estate
> © Sekirka LLC. Licensed under the **MIT License**.
>
> Each hourly snapshot in the source dataset is a 25-row batch of synthetic
> Florida real-estate records. The vendored JSON was assembled from
> 20 historical snapshots (500 raw rows) by random sampling without
> replacement down to 250 rows.

The vendored JSON adds fields that the source dataset does not include
(round-robin `property_type`, `listing_type`, status mix across
`AVAILABLE` / `RESERVED` / `SOLD` / `RENTED`, deterministic
`address_line` / `amenities`, Picsum placeholder image URLs, and
curated US multi-city `city` / `district` / `country_code` /
`latitude` / `longitude`) so the rows fit the application's `property`
table schema and provide geographic variety for demos.

## City / state / lat / lon synthesis

The HF source is a Florida-only synthetic set — its only location
field is the string `"Miami, FL"`, which is not enough to demo the
`city` and `country_code` filters. To provide a multi-city seed, the
vendor script deterministically assigns each row to one of a curated
list of 15 US metros (Miami, New York, Los Angeles, Chicago, Seattle,
Austin, Denver, Boston, Atlanta, San Francisco, Portland, Phoenix,
Dallas, Philadelphia, San Diego) using an MD5 hash of the row's
identifier. The same source row always lands in the same city, so
re-vendoring produces identical output. Latitude and longitude are
jittered by ±0.04° around the chosen city's center so the points do
not stack on top of each other on a map.

`country_code` is always `"US"`. `address_line`, `status`, and
`amenities` are also synthesized deterministically from the same hash
so the same source row always produces the same vendored row.

## Image placeholders

All `images[].url` entries in the vendored JSON are Picsum URLs of the
form `https://picsum.photos/seed/<seed>/800/600`. Picsum serves random
images from a CC0 / public-domain Unsplash pool and is free for
commercial use. The URLs are reproducible — the same seed always
returns the same image — so the seed data is stable across re-seeds.

## Vendoring

The seed data is regenerated (rarely) by running:

```
.venv/bin/python scripts/vendor_property_seed.py
```

from the `backend/` directory. The script downloads the latest
historical parquet snapshots into `.cache/seed-vendor/`, falls back to
the local cache when the Hugging Face API is unreachable, and writes
`app/seed_data/properties.json`. It is **not** invoked at app startup
or at test time.
