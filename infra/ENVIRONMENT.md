# Environment & Path Normalization

This repo uses multiple subprojects (UI, API, local_mixing, sat_revsynth) that each reference data in different locations. These environment variables keep everything consistent.

## Recommended defaults

### API (FastAPI)
Set these before running `identity-factory-api`:

- `IDENTITY_FACTORY_DB_PATH=~/.identity_factory/circuits.db`
- `ECA57_LMDB_PATH=<path to eca57_identities_lmdb>`
- `LOCAL_MIXING_DB_PATH=<path to skeleton lmdb>`
- `LOCAL_MIXING_PERM_DB_PATH=<path to local_mixing/db (LMDB perm tables)>`
- `CLUSTER_DB_PATH=<path to cluster_circuits.db>`
- `WIRE_SHUFFLER_DB_PATH=<path to wire_shuffler.db>`
- `GO_DB_DIR=<path to go-proj/db>`
- `SAT_DB_PATH=<path to sat_circuits.db>`
- `SAT_REVSYNTH_PATH=<path to sat_revsynth>`

### UI (Next.js)
Set these in `identity-factory-ui/.env.local`:

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`
- `NEXT_PUBLIC_API_HOST=http://localhost:8000`

## Why this matters

- The API default DB for circuits lives in `~/.identity_factory`, but unified search used to fall back to `identity-factory-api/cluster_circuits.db`. The `/api/v1/db-status` endpoint shows which DBs are actually present.
- ECA57 Explorer and Skeleton Explorer require LMDB paths that are not shipped by default. If they appear empty in the UI, set `ECA57_LMDB_PATH` and `LOCAL_MIXING_DB_PATH`.

## Quick checks

- `GET /api/v1/db-status` shows a complete DB inventory and sizes.
- For swap-flip gadgets, unified search uses the cluster DB because it carries `source` metadata.
