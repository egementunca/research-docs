# DB Inventory (2026-02-15)

This is a living inventory of databases and large data assets in the repo and in `~/.identity_factory`. Sizes and counts are approximate and based on a local scan on 2026-02-15.

## SQLite Databases

| Path | Size | Key Tables (counts) | Purpose | Used By |
| --- | --- | --- | --- | --- |
| `~/.identity_factory/circuits.db` | 0.1 MB | `circuits` 48, `dim_groups` 22, `jobs` 0 | Main Identity Factory DB | `/api/v1/*` identity-factory endpoints, Dashboard |
| `~/.identity_factory/imported_identities.db` | 1468.8 MB | `imported_identities` 306,288 | Imported big identities | `/api/v1/imported-identities/*` |
| `~/.identity_factory/irreducible.db` | 0.3 MB | `forward_circuits` 751, `inverse_circuits` 1 | Irreducible identities | `/api/v1/irreducible/*` |
| `identity-factory-api/cluster_circuits.db` | 10.8 MB | `circuits` 46,847, `dim_groups` 10, `jobs` 0 | Cluster enumeration DB | `/api/v1/cluster-database/*`, unified search SQLite source |
| `identity-factory-api/wire_shuffler.db` | 1.0 MB | `wire_permutations` 765, `wire_shuffler_circuits` 1693, `wire_shuffler_metrics` 1007, `wire_shuffler_runs` 6 | Wire shuffle + Waksman DB | `/api/v1/wire-shuffler/*`, `/api/v1/waksman/*` |
| `identity-factory-api/identity_circuits.db` | 0 MB | `circuits` 0, `dim_groups` 0, `jobs` 0 | Legacy/placeholder | Not used by API |
| `sat_revsynth/db_exports/wire_shuffler.db` | 0.9 MB | same as above (perms 754) | Export copy | Not used by API |
| `share/wire_shuffler.db` | 0.9 MB | same as above (perms 754) | Export copy | Not used by API |
| `local_mixing/db/circuits.db` | 10131.1 MB | tables `n6m1..`, `n7m1..`, `n10m30` | Rainbow tables | local_mixing CLI |
| `local_mixing/db-old/circuits.db` | 10101.6 MB | older rainbow tables | Legacy | Not used |
| `_archive/reversible-synth/data/templates.db` | tiny | `templates` | Legacy | Not used |

## LMDB / LMDB-like Directories

| Path | Size | Purpose | Used By |
| --- | --- | --- | --- |
| `local_mixing/db/` | 63,389.9 MB | LMDB permutation tables (`data.mdb`) + SQLite | `/api/v1/perm-database/*`, local_mixing |
| `local_mixing/data/collection.lmdb` | 447.5 MB | TemplateDB (sat_revsynth format) | local_mixing `--lmdb-db` |
| `sat_revsynth/data/collection.lmdb` | 23.0 MB | TemplateDB (smaller) | sat_revsynth tools |
| `sat_revsynth/collection.lmdb` | 1.7 MB | older TemplateDB | likely legacy |
| `collection.lmdb` | 0.1 MB | tiny TemplateDB | placeholder/legacy |
| `sat_revsynth/db_exports/skeleton_ids_n4_n7.lmdb` | 1.0 MB | Skeleton identities export | not wired |
| `share/skeleton_ids_n4_n7.lmdb` | 1.0 MB | Skeleton identities export | not wired |
| `identity-factory-api/wire_shuffler.lmdb` | 2.2 MB | LMDB copy of wire shuffler | not used by API |
| `share/wire_shuffler.lmdb` | 2.2 MB | LMDB copy of wire shuffler | not used by API |

## Go Enumerator DBs

| Path | Size | Notes |
| --- | --- | --- |
| `obfuscated-circuits/go-proj/db/n3m6.gob` | tiny | Go enumerator DB |
| `obfuscated-circuits/go-proj/db/n4m6.gob` | 88.6 MB | Go enumerator DB |
| `obfuscated-circuits/go-proj/db/n5m4.gob` | 3.7 MB | Go enumerator DB |

The Go DB API currently expects `identity-factory-api/go-proj/db`, so these are not wired unless moved/symlinked.

## Missing / Expected Assets

- `sat_circuits.db` (SAT DB endpoints expect this; not present).
- `sat_revsynth/data/eca57_identities_lmdb` (ECA57 Explorer expects this; missing).
- Skeleton LMDB in `local_mixing/db` with `ids_n3..ids_n7` (not present; exports exist in `share/`).

## Recommended Metadata / Fields (no schema changes applied yet)

These additions would improve traceability and UI functionality:

- `circuits` (Identity Factory): add `created_at`, `source`, `gate_set`, `notes`, `seed`.
- `dim_groups`: add `created_at`, `source`.
- `imported_identities`: add `verified_at`, `source_details`, `import_batch_id`.
- `wire_shuffler_circuits`: add `created_at` (if not already recorded in runs table).
- Add `metadata` tables for all primary DBs: `schema_version`, `build_time`, `generator_version`, `dataset_name`.

## Environment Variables (canonical)

Recommended defaults to keep the UI and API consistent:

- `IDENTITY_FACTORY_DB_PATH=~/.identity_factory/circuits.db`
- `ECA57_LMDB_PATH=<path to eca57_identities_lmdb>`
- `LOCAL_MIXING_DB_PATH=<path to skeleton lmdb or local_mixing/db>`

