# Circuit Storage Formats: Current State and Unification Plan

## The Problem

The codebase has **12 different circuit representations** scattered across 5 repositories.
This creates confusion, conversion bugs, and makes it hard to:
- Search for circuits across databases
- Share circuits between tools
- Understand what format a file uses

## Current Formats Summary

| Format | Where | Example | Gate Type |
|--------|-------|---------|-----------|
| `.gate` semicolon | local_mixing files | `012;47d;c74;` | ECA57 |
| Binary blob | LMDB values | `\x00\x01\x02\x01\x02\x00` | ECA57 |
| SQLite JSON (MCT) | identity_circuits.db | `[["CCX",0,1,2]]` | MCT |
| SQLite JSON (tuples) | sat_revsynth | `[[[0,1],2]]` | MCT |
| Go JSON | go-proj .json | `[[0,1,2],[1,2,0]]` | ECA57 |
| Go Gob | go-proj .gob | rune-indexed | ECA57 |
| big_identities.txt | cluster imports | `table=...,circuit=012;` | ECA57 |
| Bracket notation | Python API | `[0,1,2] [1,2,0]` | ECA57 |
| REST JSON | HTTP API | `{"gates":[[0,1,2]]}` | ECA57 |
| PlaygroundGate | TypeScript UI | `{target:0,controls:[1,2]}` | ECA57/MCT |
| Circuit._gates | sat_revsynth | `([0,1],2)` | MCT |
| Gate class | obfuscated-circuits | `Gate(a,c1,c2,inv)` | CNOT/TOF |

## Key Discrepancies

### 1. Gate Semantics
- **ECA57**: Always 3 wires `(target, ctrl1, ctrl2)`. Flip if `ctrl1=1 AND ctrl2=0`
- **MCT**: Variable controls `(controls[], target)`. Flip if ALL controls = 1
- Some tools conflate these or convert incorrectly

### 2. Wire Ordering
- `.gate` format: `[target][ctrl1][ctrl2]` (target first)
- MCT format: `([controls], target)` (target last)
- REST API: `[target, ctrl1, ctrl2]` (target first)
- This causes off-by-one bugs when copying code

### 3. File Extensions
- `.gate` - local_mixing standard
- `.json` - go-proj exports
- `.txt` - ad-hoc dumps
- No extension - some LMDB exports

### 4. Database Keys
- LMDB: binary keys with basis_id + width + gate_count + hash
- SQLite: integer PKs, text hashes
- Go Gob: permutation string keys

## Proposed Unified Format

### Canonical Text Format: `.eca57`

A new extension `.eca57` with a clear header and standard body:

```
# ECA57 Circuit
# width: 32
# gates: 150
# hash: a1b2c3d4e5f6...
# source: local_mixing/experiments/2026-02-19/run_001
012;47d;c74;d47;...
```

Rules:
- Header lines start with `#`
- `# width:` is required
- `# gates:` is computed, not stored (count semicolons)
- `# hash:` is SHA-256 of the gate string (without header)
- `# source:` tracks provenance
- Body is semicolon-delimited 3-char tokens (existing `.gate` format)

### Canonical Binary Format: Circuit Blob

For LMDB/database storage:
```
[2 bytes: width as u16 LE]
[4 bytes: gate_count as u32 LE]
[32 bytes: SHA-256 hash]
[N*3 bytes: gates, each as [target_u8, ctrl1_u8, ctrl2_u8]]
```

Total: 38 + 3*gate_count bytes

### Canonical JSON Format

For REST API and JavaScript:
```json
{
  "format": "eca57",
  "version": 1,
  "width": 32,
  "gates": [[0,1,2], [4,7,13], ...],
  "hash": "a1b2c3d4...",
  "source": "local_mixing/experiments/..."
}
```

The `gates` array uses `[target, ctrl1, ctrl2]` order (matching `.gate` files).

## Conversion Utilities

### Rust (local_mixing)

```rust
impl CircuitSeq {
    // Existing
    fn repr(&self) -> String;           // -> "012;47d;..."
    fn from_string(s: &str) -> Self;    // <- "012;47d;..."
    fn repr_blob(&self) -> Vec<u8>;     // -> binary
    fn from_blob(b: &[u8]) -> Self;     // <- binary

    // New unified
    fn to_eca57(&self, width: usize) -> String;  // with header
    fn from_eca57(s: &str) -> (Self, usize);     // parse header
    fn to_json(&self, width: usize) -> serde_json::Value;
}
```

### Python (identity-factory-api)

```python
# circuits/formats.py

def gate_string_to_list(s: str) -> list[tuple[int,int,int]]:
    """Parse '012;47d;' -> [(0,1,2), (4,7,13), ...]"""

def list_to_gate_string(gates: list[tuple]) -> str:
    """Convert [(0,1,2), ...] -> '012;47d;...'"""

def parse_eca57_file(path: str) -> dict:
    """Parse .eca57 file -> {width, gates, hash, source}"""

def write_eca57_file(path: str, width: int, gates: list, source: str):
    """Write canonical .eca57 file"""

def blob_to_gates(data: bytes) -> tuple[int, list]:
    """Parse binary blob -> (width, gates)"""

def gates_to_blob(width: int, gates: list) -> bytes:
    """Convert to binary blob"""
```

### TypeScript (identity-factory-ui)

```typescript
// lib/circuitFormats.ts

interface ECA57Circuit {
  format: 'eca57';
  version: 1;
  width: number;
  gates: [number, number, number][];
  hash: string;
  source?: string;
}

function parseGateString(s: string): [number, number, number][];
function toGateString(gates: [number, number, number][]): string;
function parseECA57Json(obj: unknown): ECA57Circuit;
```

## Migration Plan

### Phase 1: Add Canonical Utilities
- Add `circuits/formats.py` to identity-factory-api
- Add `to_eca57()`/`from_eca57()` to CircuitSeq in Rust
- Add `circuitFormats.ts` to UI

### Phase 2: Unified Search Index
Create a new SQLite table that indexes ALL circuits from all sources:

```sql
CREATE TABLE circuit_index (
    id INTEGER PRIMARY KEY,
    hash TEXT UNIQUE,          -- SHA-256 of gate string
    width INTEGER NOT NULL,
    gate_count INTEGER NOT NULL,
    gate_string TEXT NOT NULL, -- canonical semicolon format
    source TEXT NOT NULL,      -- 'lmdb:ids_n8', 'sqlite:identity_circuits', etc.
    source_id TEXT,            -- original ID in source DB
    is_identity BOOLEAN,
    permutation TEXT,          -- JSON array if known
    created_at TIMESTAMP
);
CREATE INDEX idx_circuit_dims ON circuit_index(width, gate_count);
CREATE INDEX idx_circuit_source ON circuit_index(source);
```

### Phase 3: Deprecate Old Formats
- `.gate` files continue working but new code writes `.eca57`
- Go JSON exports include header comments
- REST API always returns canonical JSON format

## File Discovery

To find all circuit files in the codebase:

```bash
# .gate files
find . -name "*.gate" -type f

# JSON circuit files (Go exports)
find . -path "*/go-proj/db/*.json" -type f

# big_identities imports
find . -name "*identities*.txt" -type f

# Experiment outputs
find . -path "*/experiments/*" -name "*.gate" -type f
```

## RNG Test Integration

For dieharder tests, we store results linked to circuits by hash:

```sql
CREATE TABLE rng_test_results (
    id INTEGER PRIMARY KEY,
    circuit_hash TEXT NOT NULL,    -- FK to circuit_index.hash
    test_mode TEXT NOT NULL,       -- 'iterate' or 'random-input'
    samples INTEGER NOT NULL,
    seed INTEGER NOT NULL,
    dieharder_version TEXT,
    overall_pass BOOLEAN,
    num_passed INTEGER,
    num_weak INTEGER,
    num_failed INTEGER,
    test_details TEXT,             -- JSON of individual test results
    created_at TIMESTAMP,
    FOREIGN KEY (circuit_hash) REFERENCES circuit_index(hash)
);
```

This lets us query: "Show me all 32-wire circuits with >500 gates that pass RNG tests."
