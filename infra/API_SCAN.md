# API Scan (2026-02-17)

This is a snapshot of the API surface and its backing data dependencies based on the current workspace state.

## Summary (Status)

- **Primary circuits DB**: uses `identity-factory-api/cluster_circuits.db` by default (exists, ~46k circuits).
- **Home DB**: `~/.identity_factory/circuits.db` exists but is small (48 circuits).
- **Wire shuffler DB**: present (`identity-factory-api/wire_shuffler.db`).
- **SAT DB**: `sat_circuits.db` **missing**.
- **ECA57 LMDB**: `sat_revsynth/data/eca57_identities_lmdb` **missing**.
- **Skeleton LMDB**: default path `local_mixing/db` **does not contain** skeleton DBs; exports exist in `share/`.
- **Go enumerator DBs**: present in `obfuscated-circuits/go-proj/db`, but API expects `identity-factory-api/go-proj/db`.
- **local_mixing binary**: present at `local_mixing/target/release/local_mixing_bin`.

## Core Identity Factory

| Router | Endpoints | Dependency | Status |
| --- | --- | --- | --- |
| `endpoints.py` | `/api/v1/stats`, `/api/v1/circuits`, `/api/v1/dim-groups`, `/api/v1/health` | Primary SQLite DB | **OK** (cluster DB present) |
| `generator_endpoints.py` | `/api/v1/generators/*` | Primary SQLite DB + generator deps | **OK** (may require SAT solver for some generators) |
| `automation_endpoints.py` | `/api/v1/automation/*` | Primary SQLite DB | **OK** |
| `irreducible_endpoints.py` | `/api/v1/irreducible/*` | `~/.identity_factory/irreducible.db` | **OK** (DB present) |
| `imported_identity_endpoints.py` | `/api/v1/imported-identities/*` | `~/.identity_factory/imported_identities.db` | **OK** (DB present) |

## Databases / Search

| Router | Endpoints | Dependency | Status |
| --- | --- | --- | --- |
| `cluster_endpoints.py` | `/api/v1/cluster-database/*` | `identity-factory-api/cluster_circuits.db` | **OK** |
| `wire_shuffler_endpoints.py` | `/api/v1/wire-shuffler/*` | `identity-factory-api/wire_shuffler.db` | **OK** |
| `perm_db_endpoints.py` | `/api/v1/perm-database/*` | `local_mixing/db` (LMDB) | **OK** |
| `sat_database_endpoints.py` | `/api/v1/sat-database/*` | `identity-factory-api/sat_circuits.db` | **MISSING** |
| `eca57_lmdb_endpoints.py` | `/api/v1/eca57-lmdb/*` | `ECA57_LMDB_PATH` | **MISSING** |
| `skeleton_db_endpoints.py` | `/api/v1/skeleton/*` | `LOCAL_MIXING_DB_PATH` | **MISSING** (exports exist in `share/`) |
| `unified_search_endpoints.py` | `/api/v1/search/*` | Primary SQLite DB + (optional) ECA57 LMDB + skeleton LMDB | **PARTIAL** (SQLite OK; LMDB sources missing) |
| `db_status_endpoints.py` | `/api/v1/db-status` | Filesystem scan | **OK** |

## Experiments / Local Mixing

| Router | Endpoints | Dependency | Status |
| --- | --- | --- | --- |
| `experiment_endpoints.py` | `/api/v1/experiments/*` | local_mixing binary + `local_mixing/experiments` | **OK** |
| `local_mixing_endpoints.py` | `/api/v1/local-mixing/*` | local_mixing utils | **OK** |
| `identity_browser_endpoints.py` | `/api/v1/local-mixing/identities/*` | `local_mixing/experiments` | **OK** |

## Waksman

| Router | Endpoints | Dependency | Status |
| --- | --- | --- | --- |
| `waksman_endpoints.py` | `/api/v1/waksman/*` | `identity-factory-api/wire_shuffler.db` + sat_revsynth | **OK** (sat_revsynth path required) |

## Go Database

| Router | Endpoints | Dependency | Status |
| --- | --- | --- | --- |
| `go_database_endpoints.py` | `/api/v1/go-database/*` | `identity-factory-api/go-proj/db/*.gob` | **MISMATCH** (data exists in `obfuscated-circuits/go-proj/db`) |

## Recommended fixes (short list)

1. Set `ECA57_LMDB_PATH` to a valid LMDB if you want the ECA57 Explorer active.  
2. Set `LOCAL_MIXING_DB_PATH` to `share/skeleton_ids_n4_n7.lmdb` (or export to `local_mixing/db`).  
3. Wire Go DB endpoints to the actual location or add a symlink.  
4. Add or restore `sat_circuits.db` if SAT DB endpoints are needed.

