# Deployment Guide (UI + API)

This doc describes how to run the Identity Factory API + UI locally and how to publish a stable research instance.

## 1) Local Development (recommended for research)

### API
```bash
cd identity-factory-api
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Example env (adjust paths to your datasets)
export IDENTITY_FACTORY_DB_PATH="/path/to/cluster_circuits.db"
export CLUSTER_DB_PATH="/path/to/cluster_circuits.db"
export WIRE_SHUFFLER_DB_PATH="/path/to/wire_shuffler.db"
export LOCAL_MIXING_DB_PATH="/path/to/skeleton_ids_n4_n7.lmdb"
export LOCAL_MIXING_PERM_DB_PATH="/path/to/local_mixing/db"
export ECA57_LMDB_PATH="/path/to/eca57_identities_lmdb"
export GO_DB_DIR="/path/to/go-proj/db"
export SAT_DB_PATH="/path/to/sat_circuits.db"

python start_api.py --port 8000
```

### UI
```bash
cd identity-factory-ui
./setup.sh
npm run dev
```

Open:
- UI: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- DB status: `http://localhost:3000/db-status`

### Doctor (status check)
```bash
python scripts/doctor.py
```

## 2) Docker Compose (single-machine)

### Build + run
```bash
docker compose up --build
```

This starts:
- API on `http://localhost:8000`
- UI on `http://localhost:3000`

### Data mounting (large datasets)
By default, `docker-compose.yml` mounts `./share` to `/data` in the API container.
To use your large datasets without copying, set `DATA_DIR`:
```bash
DATA_DIR=/path/to/your/data docker compose up --build
```

The API expects these paths inside the container:
- `/data/skeleton_ids_n4_n7.lmdb`
- `/data/local_mixing_db`
- `/data/eca57_identities_lmdb`
- `/data/go_db`
- `/data/sat_circuits.db`

Update the `DATA_DIR` structure accordingly or edit `docker-compose.yml` to match your layout.

**Note:** `NEXT_PUBLIC_API_*` env vars are baked into the UI at build time. If you change the API URL, rebuild the UI container.

## 3) Publishing (research instance)

### Internal-only (recommended)
- Run on a lab server.
- Mount data volumes read-only.
- Put the UI and API behind a VPN or basic auth.
- Use the `/db-status` page to validate readiness.

### Public demo (requires curation)
- Decide which datasets are safe to expose.
- Build a reduced demo DB (or scrub outputs).
- Disable generators and any write endpoints if you want read-only exposure.
- Add rate limits and authentication (reverse proxy).

## 4) Readiness Checklist

The system is "ready" when:
- API starts without errors.
- `/api/v1/db-status` shows the expected datasets as **present**.
- UI pages render without console errors.
- Optional pages (ECA57, Skeleton, SAT) show "missing" state rather than failing.

If you need help wiring a remote dataset mount or setting up a read-only public demo, we can add a small deployment script next.
