# RNG Test Plan (Random Circuits)

## Objective
We want to quantify when random circuits behave like good pseudorandom
permutations. For a given width `n`, estimate the minimum gate count `m*(n)`
where the output stream passes statistical RNG tests at a high rate.

This is about **pseudorandomness of circuit outputs**, not security.
Passing tests is a necessary signal, not sufficient proof of security.

## What We Are Doing
We will:
1. Define **output models** that convert a random circuit into a bitstream.
2. Run a **statistical test battery** (Dieharder) on that bitstream.
3. Sweep `m` (gate counts) for each `n` (widths), and estimate the threshold
   `m*(n)` where tests pass reliably.
4. Fit a scaling law `m*(n) ~ f(n)`.

See `RNG_REPORT.md` for the full writeup with results and plots.

## Output Models (Bitstream Sources)

We treat a random circuit `C` over `n` wires as a permutation on `{0,1}^n`.

### Mode 1: Iterate (state machine) -- implemented
- Sample a random initial state `x_0`.
- Burn-in: discard first `B` steps (default B=1000).
- Iterate `x_{t+1} = C(x_t)`.
- Emit the `n`-bit state at each step.

This is the stricter model -- the circuit must sustain randomness when
composed with itself.

### Mode 2: Counter mode -- implemented
- Evaluate `C(0), C(1), C(2), ..., C(k)`.
- Concatenate the `n`-bit outputs into a bitstream.

This tests whether the circuit scrambles structured/correlated inputs
(more relevant to cryptographic counter-mode usage).

### Mode 3: Random-input -- implemented
- Sample `x_t` uniformly at random each step.
- Emit `C(x_t)`.

This is the weakest test (independent random inputs).

## Encoding
We emit the `n`-bit state directly into a continuous bitstream
(packed bits, no padding).

Implementation: `local_mixing_bin rng-stream`.

## Gate Model
Each gate picks 3 distinct wires `[a, b, c]` and computes:
```
wire[a] ^= wire[b] OR (NOT wire[c])
```
A circuit of `m` such gates forms a reversible permutation on `{0,1}^n`.
Consecutive gates are required to differ.

## Test Suite
Primary: **Dieharder** (version 3.31.1, built from source).

Dieharder includes ~30 tests from three families:
- Diehard tests (Marsaglia): birthday spacings, rank, overlapping
  permutations, parking lot, etc.
- STS tests (NIST): runs, serial, frequency, etc.
- RGB tests (Brown): bit distribution, timing, etc.

Each test is run as a **separate dieharder invocation**. There are two modes:

**Pipe mode (recommended, `--pipe`):**
```
local_mixing_bin rng-stream ... | dieharder -g 200 -d <test_id>
```
The generator pipes data directly to dieharder. No file, no rewind, no
size limit. Each test draws exactly the random numbers it needs. The
generator runs once per (test, replicate) pair with the same seed.

**File mode (legacy):**
```
dieharder -g 201 -f <bitstream.bin> -d <test_id>
```
WARNING: If the file is smaller than what a test needs, dieharder silently
**rewinds** the file and reuses data, invalidating results. Data requirements
vary hugely per test (20 MB for birthdays, 2.6 GB for rgb_bitdist, 13 GB
for rgb_lagged_sum). For the full battery, 10-20 GB minimum.

Pipe mode avoids this problem entirely and is the default going forward.

### Assessment thresholds (set by dieharder)
- **PASSED**: p-value in [0.005, 0.995]
- **WEAK**: p-value in [10^-6, 0.005) or (0.995, 1-10^-6]
- **FAILED**: p-value < 10^-6 or > 1-10^-6

## Acceptance Criteria
For each `(n, m)` we generate `R` independent circuits, each with its own
bitstream, then evaluate:
- No FAIL p-values
- At most `k` WEAK results (default `k = 1` for quick runs, `k = 0` for final)

Define pass-rate:

`pass_rate(n, m) = (# of circuits passing) / R`

Define threshold:

`m*(n) = min{ m : pass_rate(n,m) >= 0.95 }`

### How many replicates are enough?

Each replicate is an **independent random circuit** -- a completely new
random permutation. The question is how many independent circuits need to
be tested at a given (n, m) to reliably estimate the pass rate.

| R | Pass-rate resolution | Use case |
|---|---------------------|----------|
| 5 | {0%, 20%, 40%, 60%, 80%, 100%} | Quick sweep: find approximate threshold |
| 10 | {0%, 10%, 20%, ..., 100%} | Medium sweep: locate transition region |
| 30 | ~3% resolution | Refinement: estimate pass rate with +/- 3% |
| 100 | ~1% resolution | Publication-quality confidence intervals |

For context, the USE cipher report used 300 sequences for NIST STS (but
those test the same cipher, not independent random ciphers).

**Strategy**: R=5 for Phase 1 (find approximate m*), then R=30 around the
transition region for confidence intervals. R=5 at 12 gate counts takes
~75 min; R=30 at 5 gate counts around the transition takes ~3.5 hours.

## Sampling Plan

### Phase 0: Quick sweep (completed 2026-02-19)
- widths: `n in {16, 32}`
- gate counts: `m in {100, 200, 500, 1000, 2000, 5000}`
- replicates: `R = 3`, tests: 1 (only rank_32x32 produced results)
- samples: 5M (file too small for most tests)
- **Result**: `m*(32) = 500`, `m*(16) = not reached` (state space artifact)
- **Problem**: old script stacked all test IDs in one dieharder call, so later
  tests got no data. Fixed: each test now runs as a separate invocation.

### Phase 1: Quick sweep v2 (verified 2026-02-20)
- 1 replicate at n=32, m=1000, 50M samples, 7 core tests
- All 7 tests PASSED with healthy p-values (0.43 to 0.97)
- **Runtime: 89 seconds** (64s generation + 25s for 7 tests)

### Phase 2: Medium sweep (next -- the main deliverable)

```
python scripts/rng_sweep.py --mode quick --pipe
```

| Parameter | Value |
|-----------|-------|
| Widths | n = {32, 48} |
| Gate counts | m = {100, 200, 500, 1000, 2000} |
| Replicates | R = 5 |
| Data mode | Pipe (no file, no rewind) |
| Tests | 7 core tests |

**Time estimate:**
- Per replicate: ~90 seconds (gen + 25s per test in pipe mode)
- 2 widths * 5 gates * 5 replicates = 50 replicates
- Total: **~75 minutes**

### Phase 3: Extended sweep

```
python scripts/rng_sweep.py --mode medium --pipe
```

| Parameter | Value |
|-----------|-------|
| Widths | n = {32, 48, 64} |
| Gate counts | m = {100, 200, 500, 1000, 2000, 5000} |
| Replicates | R = 10 |
| Data mode | Pipe (no file, no rewind) |
| Tests | 16 extended tests |

**Time estimate:**
- Per replicate: ~2-3 minutes (gen + 16 tests)
- 3 widths * 6 gates * 10 replicates = 180 replicates
- Total: **~6-9 hours**

### Phase 4: Full battery + counter mode comparison

```
python scripts/rng_sweep.py --mode full --pipe
python scripts/rng_sweep.py --mode full --pipe --stream-mode counter
```

| Parameter | Value |
|-----------|-------|
| Widths | n = {32, 48, 64} |
| Gate counts | m = {100, 200, 500, 1000, 2000, 5000} |
| Replicates | R = 10 |
| Data mode | Pipe (no file, no rewind) |
| Tests | all 30 tests |

**Time estimate:**
- Per replicate: ~5-8 minutes (gen + 30 tests in pipe mode)
- 3 widths * 6 gates * 10 replicates * 2 modes = 360 replicates
- Total: **~30-48 hours** (can run overnight)

**Note**: The full battery includes rgb_lagged_sum (32 sub-tests) and
rgb_bitdist (12 sub-tests) which are extremely data-hungry. In file mode
they would need 10-20 GB per file. Pipe mode handles this transparently.

### Phase 5: Refinement
- Narrow the gate-count range around each m*(n) transition
- Replicates: R >= 30
- Fit scaling law m*(n) ~ f(n)

## Current Tooling

### Bitstream generator
```bash
# Pipe directly to dieharder (no file):
local_mixing_bin rng-stream --wires 32 --gates 1000 --samples 50000000 \
  --mode iterate --burn-in 1000 --seed 42 \
  | dieharder -g 200 -d 100

# Or write temp file (for running multiple tests on same stream):
local_mixing_bin rng-stream --wires 32 --gates 1000 --samples 50000000 \
  --mode iterate --burn-in 1000 --seed 42 --out /tmp/stream.bin
dieharder -g 201 -f /tmp/stream.bin -d 2    # run one test
dieharder -g 201 -f /tmp/stream.bin -d 100  # run another on same data
rm /tmp/stream.bin
```

### Sweep runner
```bash
# Always use --pipe to avoid data reuse issues:
python scripts/rng_sweep.py --mode quick --pipe    # 7 tests, R=5, ~75 min
python scripts/rng_sweep.py --mode medium --pipe   # 16 tests, R=10, ~6-9h
python scripts/rng_sweep.py --mode full --pipe     # 30 tests, R=10, ~30h

# Override specific parameters:
python scripts/rng_sweep.py --mode quick --pipe --wires 64 --gates 500 1000 --replicates 3
python scripts/rng_sweep.py --mode quick --pipe --stream-mode counter
```

### Plot generator
```bash
python scripts/plot_rng_sweep.py            # Auto-finds latest results
```

### Dieharder binary
Local build: `dieharder-3.31.1/dieharder/dieharder`.

## Results and Plots
- Results JSON: `experiments/<date>/rng_sweep/rng_sweep_results.json`
- Pass rate plot: `experiments/<date>/rng_sweep/pass_rate_vs_gates.png`
- P-value scatter: `experiments/<date>/rng_sweep/pvalues_scatter.png`
- Pipeline diagram: `experiments/<date>/rng_sweep/pipeline_diagram.png`
- Full report: `docs/RNG_REPORT.md`

## Preliminary Findings (2026-02-19)

| n (wires) | m*(n) | Notes |
|-----------|-------|-------|
| 16        | ---   | State space too small for rank test (2^16 states) |
| 32        | 500   | ~15-16 gates per wire |

Caveat: based on 1 test (`diehard_rank_32x32`), 3 replicates only.
See `RNG_REPORT.md` for full discussion of caveats.

## Open Questions
1. Does m*(n) scale linearly with n? (need more data points)
2. Does counter mode give different m*(n) than iterate mode?
3. Does m*(n) depend on the number of samples k? (need k-sweep)
4. Can we test n=128? (requires u128 state representation)
5. What minimum dataset size do we accept for full battery?
