# RNG Test Plan (Random Circuits)

## Objective

Quantify when random circuits behave like pseudorandom permutations.
For a given width `n`, estimate the minimum gate count `m*(n)` where
the output stream passes statistical RNG tests at a high rate, then fit
a scaling law `m*(n) ~ f(n)`.

This is about **pseudorandomness of circuit outputs**, not security.
Passing dieharder tests is a necessary signal, not sufficient proof.

## Gate Model

Each gate picks 3 distinct wires `[a, b, c]` and computes:
```
wire[a] ^= wire[b] OR (NOT wire[c])
```
This is gate 57 — a single nonlinear reversible gate. A circuit of `m` such
gates forms a reversible permutation on `{0,1}^n`. Consecutive gates must differ.

## Stream Mode: Counter (always)

**Counter mode** (`C(0), C(1), C(2), ...`): each output is a single
application of the circuit to a known input. This directly tests whether the
circuit is a **pseudorandom permutation (PRP)** — can you distinguish `C` from
a random permutation by evaluating it on chosen inputs?

This is the correct and only mode we use. There is no burn-in (each
evaluation is independent).

**Why not iterate mode?** Iterate mode (`x → C(x) → C(C(x)) → ...`) benefits
from cumulative mixing over millions of re-applications, giving artificially
low thresholds. Counter mode is harder and more meaningful.

Empirical confirmation (n=32): iterate passes at m=300 (40%), counter fails
completely at m=300 (0%). Both converge to m*(32)=500 for 100% pass rate.

## Test Suite

**Dieharder** (version 3.31.1, built from source).

7 core tests (quick mode), run as **separate dieharder invocations** in
**pipe mode** (generator pipes data directly, no file, no rewind):

| ID | Test Name | What it checks |
|----|-----------|----------------|
| 0  | diehard_birthdays | Spacing/clustering |
| 2  | diehard_rank_32x32 | Linear dependence (matrix rank) |
| 3  | diehard_rank_6x8 | Finer linear structure |
| 8  | diehard_count_1s_str | Bit frequency bias |
| 15 | diehard_runs | Sequential structure (2 p-values) |
| 100 | sts_monobit | Basic frequency (NIST) |
| 101 | sts_runs | Run-length structure (NIST) |

### Assessment thresholds (set by dieharder)
- **PASSED**: p-value in [0.005, 0.995]
- **WEAK**: p-value in [10^-6, 0.005) or (0.995, 1-10^-6]
- **FAILED**: p-value < 10^-6 or > 1-10^-6

## Acceptance Criteria

A replicate **passes** if it has 0 FAILs and at most 1 WEAK across all 8 p-values.

```
pass_rate(n, m) = (# circuits passing) / R
m*(n) = min{ m : pass_rate(n, m) >= 0.95 }
```

## Sampling Plan

### Widths and Gate Counts

| Width (n) | Gate counts to sweep | Rationale |
|-----------|---------------------|-----------|
| 32 | 200, 250, 300, 350, 400, 450, 500, 600 | Known transition at 300-500, dense scan |
| 48 | 300, 400, 500, 600, 700, 800, 1000, 1200 | Expected transition ~500-1000 |
| 64 | 400, 600, 800, 1000, 1200, 1500, 2000, 2500 | Expected transition ~800-1500 |
| 96 | 600, 1000, 1500, 2000, 2500, 3000, 4000, 5000 | Expected transition ~1500-3000 |
| 128 | 1000, 1500, 2000, 3000, 4000, 5000, 6000, 8000 | Expected transition ~2000-5000 |

### Replicates

R = 100 per (n, m) point. Each replicate uses a different random seed,
producing a different random circuit. This gives ~1% resolution on pass
rates and smooth transition curves.

**Total: 5 widths x 8 gate counts x 100 replicates = 4,000 jobs**

### Execution: BU SCC Cluster (SGE)

Each replicate is independent — embarrassingly parallel. One SGE array
task per replicate:

- 1 core, 4GB RAM per task
- Wall time: 1 hour (n=32-64), 2 hours (n=96-128)
- Submitted as 5 separate array jobs (one per width)

See [CLUSTER_RNG.md](CLUSTER_RNG.md) for the full deployment guide.

## Tooling

### Binary

```bash
# Supports 1-128 wires
local_mixing_bin rng-stream --wires 32 --gates 500 --samples 50000000 \
    --mode counter --seed 42 | dieharder -g 200 -d 100
```

### Sweep Script (subcommands)

```bash
# Local sequential sweep (backward compatible)
python scripts/rng_sweep.py --mode quick --pipe --stream-mode counter

# Worker: single replicate (for SGE tasks)
python scripts/rng_sweep.py worker --wires 32 --gates 500 --seed 42 \
    --replicate-index 0 --binary-path /path/to/bin --dieharder-path /path/to/dh \
    --output-dir results/

# Submit: generate SGE array job
python scripts/rng_sweep.py submit --mode quick --stream-mode counter \
    --wires 32 --gates 200 300 500 --replicates 100 \
    --binary-path /path/to/bin --dieharder-path /path/to/dh \
    --results-dir /scratch/sweep_w32

# Collect: aggregate results
python scripts/rng_sweep.py collect --results-dir /scratch/sweep_w32
```

### Merge and Plot

```bash
# Merge per-width results into combined JSON
python scripts/merge_rng_results.py w32.json w48.json w64.json -o all.json

# Plot (auto-labels with stream mode, supports n=32-128)
python scripts/plot_rng_sweep.py --results all.json
```

## Completed Results

### n=32, counter mode (R=5, local)
| m | Pass rate |
|---|-----------|
| 50-300 | 0% |
| 500 | 100% |
| 750 | 100% |

**m\*(32) = 500** (~15.6 gates/wire). Sharp transition between m=300 and m=500.

See [RESULTS.md](RESULTS.md) for full results including iterate mode comparison.

## What Remains

1. **Cluster sweep**: R=100 across n={32,48,64,96,128} — the main deliverable
2. **Scaling law**: fit m\*(n) ~ n^alpha or n*log(n) from the 5 data points
3. **Transition characterization**: with R=100, plot smooth S-curves and
   identify the steepness of the phase transition at each width
