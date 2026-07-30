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
(round-robin `property_type`, `listing_type`, country/region defaults,
jittered `latitude`/`longitude` around the Miami center, and Picsum
placeholder image URLs) so the rows fit the application's `property`
table schema.

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
