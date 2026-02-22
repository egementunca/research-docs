# RNG Test Plan (Random Circuits)

## Objective

Quantify when random circuits behave like pseudorandom permutations.
For a given width `n`, estimate the minimum gate count `m*(n)` where
the output stream passes statistical RNG tests at a high rate, then fit
a scaling law `m*(n) ~ f(n)`.

This is about **pseudorandomness of circuit outputs**, not security.
Passing dieharder/NIST tests is a necessary signal, not sufficient proof.

## Gate Model

Each gate picks 3 distinct wires `[a, b, c]` and computes:
```
wire[a] ^= wire[b] OR (NOT wire[c])
```
This is gate 57 — a single nonlinear reversible gate. A circuit of `m` such
gates forms a reversible permutation on `{0,1}^n`. Consecutive gates must differ.

## Stream Modes (Block Cipher Modes of Operation)

We test the same circuit C in two standard block cipher modes (NIST SP 800-38A).
**PRP (Pseudorandom Permutation)** is the *property* being tested, not a mode.

### CTR (Counter) Mode — primary

`C(0), C(1), C(2), ...` — each output is a single application of the circuit
to a distinct counter value. No chaining, no cumulative mixing. This directly
tests whether C is a PRP: can you distinguish C from a random permutation by
evaluating it on chosen inputs?

CTR mode is the harder, more meaningful test. There is no burn-in.

### OFB (Output Feedback) Mode — secondary, for comparison

`IV → C(IV) → C(C(IV)) → ...` — each output is fed back as the next input.
The k-th output is C^k(IV). This is our **iterate mode** and is equivalent
to what the USE report (Chamon et al.) and the professor's group used.

OFB is an easier test because millions of cumulative re-applications provide
extra mixing even if C alone is a weak PRP. We run OFB for comparison with
prior work, not as the primary metric.

### Related-Key Mode — supplementary

`C[0..1](x), C[0..2](x), ..., C[0..M](x)` — fix input x, evaluate every prefix
of the circuit (1 gate, 2 gates, ..., M gates). This tracks how pseudorandomness
emerges gate by gate, directly observing the mixing process. Suggested by Ran Canetti;
analogous to what Andrei describes as "layer by layer evolution" of string entropy.

Related-key mode tests whether the "key schedule" (adding gates incrementally) leaks
structure. The output for each input is M blocks (one per prefix length), then moves
to the next input. CLI: `--mode related-key`.

Empirical confirmation (n=32, R=5): OFB/iterate passes at m=300 (40%),
CTR/counter fails completely at m=300 (0%).

## Test Suites

### Dieharder (v3.31.1, built from source)

**Quick mode** (7 core tests, used in Phase 1):

| ID | Test Name | What it checks |
|----|-----------|----------------|
| 0  | diehard_birthdays | Spacing/clustering |
| 2  | diehard_rank_32x32 | Linear dependence (matrix rank) |
| 3  | diehard_rank_6x8 | Finer linear structure |
| 8  | diehard_count_1s_str | Bit frequency bias |
| 15 | diehard_runs | Sequential structure (2 p-values) |
| 100 | sts_monobit | Basic frequency (NIST) |
| 101 | sts_runs | Run-length structure (NIST) |

**Full mode** (27 test families, ~114 individual tests):
All dieharder tests with "Good" reliability. Excludes IDs 5, 6, 7 (Suspect)
and 14 (Do Not Use). Matches the full battery used in the USE report.

### NIST STS (SP 800-22, v2.1.2)

15 test categories producing 188 p-values per sequence. Key tests NOT covered
by dieharder:

| # | Test | p-values |
|---|------|----------|
| 2 | Frequency Within a Block | 1 |
| 4 | Longest Run of Ones | 1 |
| 6 | Discrete Fourier Transform (Spectral) | 1 |
| 7 | Non-overlapping Template Matching | 148 |
| 8 | Overlapping Template Matching | 1 |
| 9 | Maurer's Universal Statistical | 1 |
| 10 | Linear Complexity | 1 |
| 12 | Approximate Entropy | 1 |
| 13 | Cumulative Sums | 2 |
| 14 | Random Excursions | 8 |
| 15 | Random Excursions Variant | 18 |

### Assessment Thresholds

Dieharder:
- **PASSED**: p-value in [0.005, 0.995]
- **WEAK**: p-value in [10^-6, 0.005) or (0.995, 1-10^-6]
- **FAILED**: p-value < 10^-6 or > 1-10^-6

NIST STS:
- Per-sequence: PASS if p-value > 0.01
- Per-test: PASS if proportion ≥ 96.92% (weighted threshold for 300 sequences)

## Acceptance Criteria

A dieharder replicate **passes** if it has 0 FAILs and at most 1 WEAK across
all p-values.

```
pass_rate(n, m) = (# circuits passing) / R
m*(n) = min{ m : pass_rate(n, m) >= 0.95 }
```

## Sampling Plan

### Widths and Gate Counts

| Width (n) | Phase 1 gate counts (done) | Phase 2 additions (transition refinement) |
|-----------|---------------------------|------------------------------------------|
| 32 | 200, 250, 300, 350, 400, 450, 500, 600 | 525, 550, 575 |
| 48 | 300, 400, 500, 600, 700, 800, 1000, 1200 | 650, 750, 850, 900, 950 |
| 64 | 400, 600, 800, 1000, 1200, 1500, 2000, 2500 | 900, 1100 |
| 96 | 600, 1000, 1500, 2000, 2500, 3000, 4000, 5000 | 1750, 2250 |
| 128 | 1000, 1500, 2000, 3000, 4000, 5000, 6000, 8000 | 2250, 2500, 2750 |

### Replicates

- **Phase 1-2**: R=100 per (n, m). Gives ~1% resolution on pass rates.
- **Phase 3-5**: R=20 per (n, m). Sufficient for verifying test coverage.

### Execution: BU SCC Cluster (SGE)

Each replicate is independent — embarrassingly parallel. One SGE array
task per replicate:

- 1 core, 4GB RAM per task
- Wall time: 1 hour (7 tests), 2-3 hours (full battery)
- Submitted as separate array jobs per width and phase

See [CLUSTER_RNG.md](../../local_mixing/CLUSTER_RNG.md) for the full deployment guide.

## Phases

| Phase | Description | Tests | Mode | Jobs | Status |
|-------|------------|-------|------|------|--------|
| 1 | Coarse scan, all widths | 7 core dieharder | counter | 4,000 | **COMPLETE** |
| 2 | Transition refinement | 7 core dieharder | counter | 1,400 | TODO |
| 3 | Full dieharder battery | 27 families (~114 tests) | counter | 300 | TODO |
| 4 | NIST STS | 15 categories (188 tests) | counter | 200 | TODO |
| 5 | Iterate/OFB comparison | 7 core dieharder | iterate | 800 | TODO |
| 6 | Related-key (prefix) test | 7 core dieharder | related-key | 300 | TODO |

**Total: ~7,000 jobs**

## Completed Results (Phase 1)

### m\*(n) Estimates (95% threshold, counter mode, R=100)

| Width (n) | m\*(n) | Gates/wire | Transition region |
|-----------|--------|------------|-------------------|
| 32 | ~600 | 18.8 | 350–600 |
| 48 | ~1000 | 20.8 | 600–1000 |
| 64 | ~1200 | 18.8 | 800–1200 |
| 96 | ~2000 | 20.8 | 1500–2000 |
| 128 | ~3000 | 23.4 | 2000–3000 |

See [RESULTS.md](RESULTS.md) for full tables and analysis.

## Tooling

### Binary

```bash
# Supports 1-128 wires, counter and iterate modes
local_mixing_bin rng-stream --wires 32 --gates 500 --samples 50000000 \
    --mode counter --seed 42 | dieharder -g 200 -d 100
```

### Sweep Script (subcommands)

```bash
# Local sequential sweep
python scripts/rng_sweep.py --mode quick --pipe --stream-mode counter

# Worker: single replicate (for SGE tasks)
python scripts/rng_sweep.py worker --wires 32 --gates 500 --seed 42 \
    --replicate-index 0 --mode quick --stream-mode counter \
    --binary-path /path/to/bin --dieharder-path /path/to/dh \
    --output-dir results/

# Submit: generate SGE array job (quick = 7 tests, full = all tests)
python scripts/rng_sweep.py submit --mode full --stream-mode counter \
    --wires 32 --gates 400 550 800 --replicates 20 \
    --binary-path /path/to/bin --dieharder-path /path/to/dh \
    --results-dir /scratch/sweep_w32

# Collect and merge
python scripts/rng_sweep.py collect --results-dir /scratch/sweep_w32
python scripts/merge_rng_results.py w32.json w48.json -o all.json
python scripts/plot_rng_sweep.py --results all.json
```

## What Remains

1. **Phase 2-6** on cluster (see CLUSTER_RNG.md for commands)
2. **Scaling law**: fit m\*(n) ~ n^alpha or n*log(n) from the 5+ data points
3. **Transition characterization**: smooth S-curves from Phase 2 data
4. **NIST-style plots**: "% accepted sequences" per test (Phase 4)
5. **Iterate vs counter comparison**: show iterate gives easier threshold (Phase 5)
6. **Related-key analysis**: gate-by-gate entropy emergence (Phase 6)
