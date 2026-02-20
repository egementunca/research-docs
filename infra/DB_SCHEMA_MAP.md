# Database Schema Map (Workspace Snapshot)

This is a concrete, **column-level** map of the databases present in this repo and how the API/UI uses them. It is derived from live schemas (SQLite) plus code-defined schemas (LMDB/Go). Use this as the canonical reference when deciding what is active vs. legacy.

## How the API chooses the main Identity DB

`identity-factory-api/identity_factory/api/db_paths.py`:
- If `IDENTITY_FACTORY_DB_PATH` is set, the API uses that.
- Else, if `identity-factory-api/cluster_circuits.db` exists, it is used.
- Else, it falls back to `~/.identity_factory/circuits.db`.

This affects `/api/v1/*` endpoints served by `endpoints.py`.

## 1) Identity Factory SQLite (core circuits DB)

**Paths**
- Active: `identity-factory-api/cluster_circuits.db`
- Legacy/placeholder: `identity-factory-api/identity_circuits.db`
- Optional: `~/.identity_factory/circuits.db` (not present in this workspace)

**Env overrides**
- `IDENTITY_FACTORY_DB_PATH` (core API `/api/v1/*`)
- `CLUSTER_DB_PATH` (cluster endpoints `/api/v1/cluster-database/*`)

**Tables (common)**

`circuits`
- `id INTEGER PRIMARY KEY`
- `width INTEGER NOT NULL`
- `gate_count INTEGER NOT NULL`
- `gates TEXT NOT NULL`
- `permutation TEXT NOT NULL`
- `complexity_walk TEXT`
- `circuit_hash TEXT UNIQUE`
- `dim_group_id INTEGER`
- `representative_id INTEGER`
- `gate_set TEXT DEFAULT 'eca57'` *(cluster DB only)*
- `source TEXT DEFAULT 'cluster'` *(cluster DB only)*

`dim_groups`
- `id INTEGER PRIMARY KEY`
- `width INTEGER NOT NULL`
- `gate_count INTEGER NOT NULL`
- `circuit_count INTEGER DEFAULT 0`
- `is_processed BOOLEAN DEFAULT FALSE`
- `UNIQUE(width, gate_count)`

`jobs`
- `id INTEGER PRIMARY KEY`
- `job_type TEXT NOT NULL`
- `status TEXT NOT NULL`
- `priority INTEGER DEFAULT 0`
- `parameters TEXT NOT NULL`
- `result TEXT`
- `error_message TEXT`
- `started_at TIMESTAMP`
- `completed_at TIMESTAMP`

**Used by**
- `/api/v1/*` (identity-factory endpoints in `endpoints.py`)
- `/api/v1/cluster-database/*` uses **only** `identity-factory-api/cluster_circuits.db` and expects `gate_set`/`source`

**Notes**
- `identity_circuits.db` is missing `gate_set` and `source` columns.
- The simplified `CircuitDatabase` ignores `gate_set`/`source`, so `cluster_circuits.db` is compatible, but if you use `identity_circuits.db` directly, the cluster endpoints will not work.

## 2) Wire Shuffler / Waksman SQLite

**Path**
- `identity-factory-api/wire_shuffler.db` (active)

**Env override**
- `WIRE_SHUFFLER_DB_PATH`

**Tables**

`wire_permutations`
- `id INTEGER PRIMARY KEY`
- `width INTEGER NOT NULL`
- `wire_perm TEXT NOT NULL`
- `wire_perm_hash TEXT NOT NULL`
- `fixed_points INTEGER`
- `hamming INTEGER`
- `cycles INTEGER`
- `swap_distance INTEGER`
- `cycle_type TEXT`
- `parity TEXT`
- `is_identity BOOLEAN DEFAULT 0`
- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

`wire_shuffler_circuits`
- `id INTEGER PRIMARY KEY`
- `run_id INTEGER NOT NULL`
- `perm_id INTEGER NOT NULL`
- `found BOOLEAN NOT NULL`
- `gate_count INTEGER`
- `gates TEXT`
- `circuit_hash TEXT`
- `full_perm TEXT`
- `verify_ok BOOLEAN`
- `synth_time_ms INTEGER`
- `is_best BOOLEAN DEFAULT 0`
- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

`wire_shuffler_metrics`
- `circuit_id INTEGER PRIMARY KEY`
- `width INTEGER NOT NULL`
- `gate_count INTEGER NOT NULL`
- `wires_used INTEGER NOT NULL`
- `wire_coverage REAL NOT NULL`
- `max_wire_degree INTEGER NOT NULL`
- `avg_wire_degree REAL NOT NULL`
- `adjacent_collisions INTEGER NOT NULL`
- `adjacent_commutes INTEGER NOT NULL`
- `total_collisions INTEGER NOT NULL`
- `collision_density REAL NOT NULL`

`wire_shuffler_runs`
- `id INTEGER PRIMARY KEY`
- `width INTEGER NOT NULL`
- `min_gates INTEGER NOT NULL`
- `max_gates INTEGER NOT NULL`
- `solver TEXT NOT NULL`
- `require_all_wires BOOLEAN DEFAULT 0`
- `"order" TEXT`
- `seed INTEGER`
- `status TEXT`
- `notes TEXT`
- `git_sha TEXT`
- `started_at TIMESTAMP`
- `completed_at TIMESTAMP`

`waksman_circuits`
- `id INTEGER PRIMARY KEY`
- `perm_id INTEGER NOT NULL`
- `gate_count INTEGER NOT NULL`
- `gates TEXT NOT NULL`
- `swap_count INTEGER NOT NULL`
- `synth_time_ms INTEGER`
- `verify_ok BOOLEAN`
- `circuit_hash TEXT`
- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

**Used by**
- `/api/v1/wire-shuffler/*`
- `/api/v1/waksman/*`

## 3) Irreducible SQLite

**Path**
- `/Users/egementunca/.identity_factory/irreducible.db` (active)

**Tables**

`forward_circuits`
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `width INTEGER NOT NULL`
- `gate_count INTEGER NOT NULL`
- `gates TEXT NOT NULL`
- `permutation TEXT NOT NULL`
- `permutation_hash TEXT NOT NULL`
- `touches_all_wires BOOLEAN DEFAULT TRUE`
- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

`inverse_circuits`
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `forward_id INTEGER NOT NULL`
- `gate_count INTEGER NOT NULL`
- `gates TEXT NOT NULL`
- `synthesis_method TEXT`
- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

`identity_circuits`
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `forward_id INTEGER NOT NULL`
- `inverse_id INTEGER NOT NULL`
- `width INTEGER NOT NULL`
- `total_gates INTEGER NOT NULL`
- `quality_score REAL`
- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

**Used by**
- `/api/v1/irreducible/*`

## 4) Imported Identities SQLite

**Path**
- `/Users/egementunca/.identity_factory/imported_identities.db` (active)

**Tables**

`imported_identities`
- `id INTEGER PRIMARY KEY`
- `source_table TEXT NOT NULL`
- `wires INTEGER NOT NULL`
- `gate_count INTEGER NOT NULL`
- `gates TEXT NOT NULL`
- `circuit_str TEXT NOT NULL`
- `circuit_hash TEXT UNIQUE`
- `is_verified BOOLEAN DEFAULT FALSE`
- `imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

`imported_identity_stats` (VIEW)
- `source_table, wires, circuit_count, min_gates, max_gates, avg_gates`

**Used by**
- `/api/v1/imported-identities/*`

## 5) Local Mixing SQLite (rainbow tables)

**Path**
- `local_mixing/db/circuits.db` (very large)

**Tables**
- Dynamic per-dimension tables: `n{N}m{M}`

**Schema (`n6m1` example)**
- `circuit BLOB`
- `perm BLOB`
- `shuf BLOB`

**Used by**
- `local_mixing` CLI (compression + replacement pipelines)
- Not used directly by FastAPI endpoints

**Notes**
- This DB is large and often accessed read-only. Some CLI paths set SQLite to `locking_mode = EXCLUSIVE`, which makes it single-process at a time.

## 6) Local Mixing LMDB (perm tables)

**Path**
- `local_mixing/db` (LMDB data.mdb + lock)

**DB names**
- `perm_tables_n{N}`
- `n{N}m{M}`
- `n{N}m{M}perms`

**Used by**
- `/api/v1/perm-database/*`
- `local_mixing` CLI (compress, replace, canonical lookup)

**Notes**
- LMDB allows many readers, one writer. Read-only access is safe for concurrent use.

## 7) Skeleton LMDB (pair-taxonomy identities)

**Expected Path**
- `LOCAL_MIXING_DB_PATH` env var (defaults to `local_mixing/db`)

**DB names**
- `ids_n3`, `ids_n4`, `ids_n5`, `ids_n6`, `ids_n7`

**Encoding**
- Key: GatePair taxonomy bincode (3×u32 LE or legacy 3 bytes)
- Value: bincode `Vec<Vec<u8>>`, where each gate is 3 bytes (t, c1, c2)

**Used by**
- `/api/v1/skeleton/*`

**Notes**
- `share/skeleton_ids_n4_n7.lmdb` is an export you can point to via `LOCAL_MIXING_DB_PATH`.

## 8) ECA57 LMDB (sat_revsynth TemplateDB)

**Expected Path**
- `ECA57_LMDB_PATH` env var (defaults to `sat_revsynth/data/eca57_identities_lmdb`)

**DB names** (from `sat_revsynth/src/database/lmdb_env.py`)
- `meta`
- `templates_by_hash`
- `template_families`
- `templates_by_dims`
- `witnesses_by_hash`
- `witness_prefilter`

**Used by**
- `/api/v1/eca57-lmdb/*`

## 9) Go Enumerator DBs (gob)

**Expected Path**
- `identity-factory-api/go-proj/db/*.gob`

**Env override**
- `GO_DB_DIR`

**Actual Path**
- `obfuscated-circuits/go-proj/db/*.gob`

**Used by**
- `/api/v1/go-database/*` (currently mismatched unless you symlink/copy)

## 10) SAT DB (missing)

**Expected Path**
- `identity-factory-api/sat_circuits.db`

**Used by**
- `/api/v1/sat-database/*`

**Status**
- Missing in this workspace.

## 11) Exports / Legacy / Not Used by API

- `share/wire_shuffler.db`, `share/wire_shuffler.lmdb`: exports only.
- `share/skeleton_ids_n4_n7.lmdb`: export; usable if pointed via `LOCAL_MIXING_DB_PATH`.
- `_archive/*`: legacy; not used.
- `identity-factory-api/identity_circuits.db`: legacy placeholder.
