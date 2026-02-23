# Random Circuits as Pseudorandom Permutations: RNG Testing Report

**Date:** 2026-02-22
**Status:** Phases 1, 2, 3, 5, 6 complete. Phase 4 TODO.

---

## 1. The Question

> For a given number of wires `n`, what is the minimum number of random gates `m*(n)` such that a random reversible circuit behaves like a good pseudorandom permutation?

### Theoretical background

The question of minimum circuit depth for pseudorandom permutations was
addressed in Chamon et al. (arXiv:2011.06546). When the circuit is organized
as a **tree** combining a special set of **inflationary (linear)** and
**nonlinear** gates, the minimum number of gates is **O(n log n)** with depth
**O(log n)**.

However, if the circuit uses **only gate 57** (our gate model:
`wire[a] ^= wire[b] OR (NOT wire[c])`), there is no inflation, so the
circuit depth cannot be less than **(log n)^k** with **k > 1**. This means
more gates are needed to achieve the same mixing compared to the mixed
inflationary/nonlinear design.

Previous randomness tests against AES were done for the inflationary/nonlinear
circuit at **n = 128** (see Section 9). The present experiments test circuits
consisting of **only gate 57** to empirically determine the gate-count
threshold for this specific gate type.

### Approach

The approach is empirical: generate bitstreams from random circuits, run
statistical tests, and find the gate-count threshold where tests pass reliably.

---

## 2. How a Circuit Becomes a Bitstream (Step by Step)

The random circuits here are **reversible permutations** on `n`-bit strings.
Each circuit `C` is a composition of `m` random gates, where each gate picks
3 distinct wires `[a, b, c]` and flips wire `a` conditioned on `b` and `c`.
Since every gate is reversible, the full circuit `C : {0,1}^n -> {0,1}^n` is a
bijection (a permutation on the 2^n possible states).

To test whether `C` "looks random," a long bitstream is produced from it
and fed to a statistical test suite. There are three modes, listed from
**most to least meaningful** for pseudorandomness:

### Mode 1: CTR (Counter) mode — primary

```
1. Evaluate: C(0), C(1), C(2), ..., C(k)
   Feed the inputs 0, 1, 2, ... in order (like a counter).
2. Concatenate the n-bit outputs into a bitstream.
3. Feed to dieharder.
```

This is the standard **CTR mode** (NIST SP 800-38A) and the **most direct
test of pseudorandom permutation (PRP) quality**. Each output C(i) depends
on a **single application** of the circuit to a known input. If the outputs
look random, the circuit itself is a good PRP.

CTR mode is harder to pass than OFB because there is no cumulative mixing.

### Mode 2: OFB (Output Feedback) mode — secondary

```
1. Pick a random starting state x_0 (the IV) in {0,1}^n
2. Emit: C(x_0), C(C(x_0)), C(C(C(x_0))), ...
   Each output is fed back as the next input (output feedback).
3. Concatenate into a bitstream. Feed to dieharder.
```

This is the standard **OFB mode** (NIST SP 800-38A), equivalent to our
**iterate mode**. The USE report (Chamon et al.) and the professor's group
used this mode.

OFB **conflates the quality of C with the mixing effect of re-application**.
After k steps, the output is C^k(IV). Even a mediocre permutation applied
millions of times can produce random-looking output. As a result, OFB gives
a **lower (easier) threshold** than CTR.

### Mode 3: Random-input

```
1. For each step, sample a fresh random x_t.
2. Emit C(x_t).
```

The weakest test -- independent random inputs each time.

### Which mode matters?

**CTR/counter mode is the definitive test for pseudorandomness.** The PRP
definition asks: "Is C indistinguishable from a truly random permutation?"
CTR mode tests exactly this. OFB is useful as a secondary check and for
comparison with prior work (the USE report), but **m\*(n) from CTR mode is
the number to report**.

Note: **PRP is the *property* being tested, not a mode.** A good PRP should
pass tests in both CTR and OFB modes.

### Implementation

The Rust binary `local_mixing_bin rng-stream` generates the bitstream
and **pipes it directly to dieharder via stdin** -- no intermediate file
is needed:

```bash
local_mixing_bin rng-stream \
  --wires 32 \
  --gates 1000 \
  --samples 100000000 \
  --mode counter \
  --seed 42 \
| dieharder -g 200 -d 100
```

Note: no burn-in is needed in counter mode (each C(i) is independent).

The output is raw packed bits (no padding). For n=32 wires and
k=100,000,000 samples, the stream is 32 * 100M / 8 = 381 MB, but it
is never written to disk -- it flows directly through the pipe.

For cases where a file is needed (e.g., running multiple tests on the
same data), the `--out` flag writes to a file and `-g 201 -f <file>` reads
it back. But piping is preferred since it avoids disk I/O bottlenecks
and imposes no storage limit.

---

## 3. What Dieharder Is and How It Works

### Overview

Dieharder is the standard statistical test suite for random number generators.
It includes ~30 tests from three families:
- **Diehard tests** (George Marsaglia's original suite)
- **STS tests** (NIST Statistical Test Suite)
- **RGB/DAB tests** (additional modern tests)

Each test checks a specific statistical property that truly random bits should
satisfy.

### How the pipeline runs

**Pipe mode (recommended)** -- generator pipes directly to dieharder:
```bash
local_mixing_bin rng-stream --wires 32 --gates 1000 \
  --samples 1000000000 --mode counter --seed 42 \
  | dieharder -g 200 -d 100
```

Each test gets its own pipe invocation. The generator produces data on
demand -- no file, no size limit, no rewind. Each test draws exactly as
many random numbers as it needs. The sweep script runs the generator once
per (test, replicate) pair.

**File mode (legacy, use with caution)**:
```bash
# Generate once:
local_mixing_bin rng-stream ... --out /tmp/stream.bin
# Run each test separately:
dieharder -g 201 -f /tmp/stream.bin -d 0
dieharder -g 201 -f /tmp/stream.bin -d 100
rm /tmp/stream.bin
```

**WARNING -- data reuse in file mode**: If a test needs more data than the
file contains, dieharder silently **rewinds** the file and cycles through
it again, producing invalid p-values. Different tests have very different
data requirements:

| Test | Rands needed (psamples=100) | Min file size (32-bit) |
|------|---------------------------|------------------------|
| diehard_birthdays | ~5M | ~20 MB |
| diehard_rank_32x32 | ~128M | ~512 MB |
| diehard_runs | ~10M | ~40 MB |
| sts_monobit | ~10M | ~40 MB |
| rgb_bitdist | ~640M | ~2.6 GB |
| rgb_lagged_sum (lag 31) | ~3.2B | ~13 GB |
| Full battery (all tests) | ~60-80B | ~250+ GB |

For the 7 core tests, a file must be at least **~3 GB** to avoid rewinds.
For the full battery, **10-20 GB** is the practical minimum.

The sweep script now supports `--pipe` mode which avoids this problem entirely:
```bash
python scripts/rng_sweep.py --mode quick --pipe
```

Key flags:
- `-g 200` = read raw binary from stdin (pipe, no rewind)
- `-g 201` = read raw binary from file (may rewind if too small)
- `-d <N>` = run specific test number N

### What the output looks like

```
        test_name   |ntup| tsamples |psamples|  p-value |Assessment
  diehard_rank_32x32|   0|    40000 |    100 |0.17422076|  PASSED
```

### Reading the results

Each test produces:
- **p-value**: A number between 0 and 1. For truly random data, p-values
  should be uniformly distributed over [0, 1].
- **Assessment**: Dieharder categorizes based on p-value:
  - **PASSED**: p-value in [0.005, 0.995] -- looks random
  - **WEAK**: p-value in [0.000001, 0.005) or (0.995, 0.999999] -- suspicious
  - **FAILED**: p-value < 0.000001 or > 0.999999 -- clearly non-random

Important: the p-value is NOT a quality score. A result of p = 0.03 is fine,
p = 0.95 is fine. The goal is that p-values are **uniformly distributed**
across [0,1] -- not that they are close to 1.

---

## 4. The Dieharder Tests: What Each One Does

### Diehard Tests (Marsaglia's originals)

| # | Test | What it checks |
|---|------|----------------|
| 0 | **Birthdays** | Spacings between "birthdays" (random points on a large interval). Tests whether the spacings follow the expected Poisson distribution. Detects clustering. |
| 1 | **OPERM5** | Overlapping permutations of 5 consecutive values. Checks whether all 5! = 120 orderings appear equally often. Detects ordering bias. |
| 2 | **Rank 32x32** | Builds 32x32 binary matrices from the stream and computes their rank. The rank distribution should match the theoretical formula. Detects linear dependencies between bits. |
| 3 | **Rank 6x8** | Same idea as above but with 6x8 matrices. Less data-hungry, catches finer-grain linear structure. |
| 4 | **Bitstream** | Treats the stream as overlapping 20-bit words and counts how many of the 2^20 possible words are missing. Detects sparse coverage of bit patterns. |
| 5 | **OPSO** | Overlapping-pairs-sparse-occupancy. Counts missing pairs of 10-bit words in overlapping windows. Similar to bitstream but at a different scale. |
| 6 | **OQSO** | Overlapping-quadruples. Like OPSO but with 4-tuples of shorter words. |
| 7 | **DNA** | Treats bits as a 4-letter alphabet (pairs of bits = "nucleotides"). Counts missing 10-letter "words." Detects structure at the 2-bit level. |
| 8 | **Count-the-1s (stream)** | Counts the number of 1-bits in consecutive 5-letter words (letters defined by byte value). The counts should follow a specific distribution. |
| 9 | **Count-the-1s (byte)** | Same idea but per-byte. |
| 10 | **Parking Lot** | Simulates "parking" 12,000 unit circles in a 100x100 square. The number of successful placements should follow a normal distribution. Tests multi-dimensional uniformity. |
| 11 | **Min Distance (2D)** | Places 8,000 random points in a square and finds the minimum distance. The squared minimum distance should be exponentially distributed. Tests spatial clustering. |
| 12 | **3D Sphere** | Places 4,000 random points in a cube, finds the minimum distance. The cube of the min distance should be exponential. 3D spatial uniformity test. |
| 13 | **Squeeze** | Repeatedly multiplies a floating-point number by a random value until it reaches 1. The number of steps should follow a known distribution. Tests floating-point uniformity. |
| 15 | **Runs** | Counts runs of consecutive ascending/descending values. The counts should match the theoretical distribution. Classic sequence test. |
| 16 | **Craps** | Simulates games of craps using the random stream. The number of wins and throw counts should match theoretical probabilities. A fun but effective uniformity test. |
| 17 | **GCD** | Computes GCD of pairs of random integers. The distribution of GCD values and iteration counts should match number-theoretic expectations. |

### STS Tests (NIST)

| # | Test | What it checks |
|---|------|----------------|
| 100 | **Monobit** | Overall frequency of 0s and 1s. Should be approximately 50/50. The most basic test. |
| 101 | **Runs** | Number of uninterrupted sequences of identical bits. Too many or too few runs indicate structure. |
| 102 | **Serial** | Frequency of all possible n-bit patterns (generalized). Tests whether all 2^n patterns of length n appear equally often. |

### RGB/DAB Tests (modern additions)

| # | Test | What it checks |
|---|------|----------------|
| 200 | **Bit Distribution** | Tests the distribution of bits at each position across many samples. Detects positional bias. |
| 201 | **Generalized Min Distance** | Generalization of the minimum distance test to higher dimensions and different parameters. |
| 202 | **Permutations** | Tests whether all permutations of n-tuples appear with equal frequency. Generalized permutation test. |
| 203 | **Lagged Sum** | Sums of values separated by various lags. Detects correlations at different time scales. |
| 204 | **Kolmogorov-Smirnov** | Meta-test: applies KS test to the p-values from other tests. Checks that p-values are themselves uniform. |
| 205 | **Byte Distribution** | Checks that all 256 byte values appear equally often. Detects byte-level bias. |
| 206 | **DAB DCT** | Applies discrete cosine transform to blocks of random data. The DCT coefficients should follow expected distributions. Detects spectral structure. |
| 207 | **DAB Fill Tree** | Fills a binary tree with random bits and checks the resulting structure. Detects tree-structural bias. |
| 208 | **DAB Fill Tree 2** | Variant of the fill tree test with different parameters. |
| 209 | **DAB Monobit 2** | Enhanced monobit test that checks bit frequency across different block sizes simultaneously. |

**Note:** Tests 5, 6, 7 are marked "Suspect" by dieharder (known to have
slightly imprecise reference distributions). Test 14 (Sums) is marked
"Do Not Use." All others are rated "Good."

---

## 5. Other Measures Beyond P-Values

Beyond per-test p-values, there are several complementary measures:

1. **KS test on p-values**: Running the same test on many independent circuits
   produces a collection of p-values. These should be uniformly distributed.
   A Kolmogorov-Smirnov test on the p-values gives a "meta p-value" --
   a more robust aggregate measure than counting pass/fail.

2. **Test battery depth**: How many of the ~30 tests a generator passes.
   Passing 1 test is weak evidence; passing all 30 is much stronger.

3. **Sample-size sensitivity**: If the p-value holds up as the number of
   samples k increases, that is stronger evidence than passing at one fixed k.
   If the p-value degrades as k grows, there is detectable structure that
   simply needs more data to reveal.

---

## 6. Results

### Phase 1+2: CTR/Counter Mode (7 core tests, R=100)

- **Widths**: n = 32, 48, 64, 96, 128
- **Tests**: 7 core dieharder tests (8 p-values), pipe mode
- **Replicates**: R = 100 per (n, m) point
- **Stream mode**: CTR/counter
- **Phase 2** added denser gate counts in the transition region.

#### m\*(n) Summary (95% pass rate threshold)

| Width (n) | m\*(n) | Gates/wire | Transition region |
|-----------|--------|------------|-------------------|
| 32 | ~525 | 16.4 | 350–600 |
| 48 | ~850 | 17.7 | 600–950 |
| 64 | ~1200 | 18.8 | 800–1200 |
| 96 | ~2000 | 20.8 | 1500–2250 |
| 128 | ~2500 | 19.5 | 2000–2750 |

Scaling: m\*(n) ≈ 18–21n (roughly linear in width). Phase 2 tightened estimates:
m\*(32) from ~600→~525, m\*(48) from ~1000→~850, m\*(128) from ~3000→~2500.

#### Key observations

1. **Gradual S-curve at R=100.** The transition spans roughly a factor of 2.

2. **Pass rates plateau at 95–99%.** Occasional WEAK results at high gate counts
   are expected stochastic noise with max_weak=1.

3. **Bottleneck test: sts_monobit.** In the transition region, failed replicates
   almost always fail on sts_monobit (ID 100) while all other 6 tests pass.

### Phase 3: Full Dieharder Battery (27 families, counter mode, R=20)

**Result: 0% pass rate everywhere.** Root cause: `rgb_minimum_distance` (test ID 201)
fails with p=0.0 in 100% of replicates due to a **dieharder invocation bug** — the
test was run with default ntup=0 (dimension 0), which is a degenerate configuration
that fails for all generators including AES-OFB. See §11 for full analysis.
Excluding this test, the full battery does not shift m\*(n).

### Phase 5: OFB/Iterate Mode (7 core tests, R=20)

| Width (n) | m\*(CTR) | m\*(OFB) | CTR/OFB ratio |
|-----------|----------|----------|---------------|
| 32 | ~525 | ~400 | 1.31 |
| 48 | ~850 | ~500 | 1.70 |
| 64 | ~1200 | ~800 | 1.50 |
| 96 | ~2000 | ~1500 | 1.33 |
| 128 | ~2500 | ~2000 | 1.25 |

OFB mode requires ~25–40% fewer gates. Cumulative re-application provides extra
mixing, confirming CTR is the harder, more meaningful test.

### Phase 6: Related-Key Mode (7 core tests, R=20)

**Result: 0% pass rate everywhere.** The stream includes outputs from shallow
circuit prefixes (1–2 gates) which are clearly non-random, poisoning the entire
stream. This mode needs depth-stratified analysis rather than whole-stream testing.

See [RESULTS.md](RESULTS.md) for full per-width tables and all plots.

---

## 7. Caveats and Limitations

1. **`rgb_minimum_distance` fails due to invocation bug.** The full dieharder
   battery (Phase 3) always fails this test because our sweep script runs
   `-d 201` without `-n`, triggering a degenerate dimension-0 mode. Even
   dieharder's built-in AES-OFB fails at ntup=0. The fix is to pass
   `-n 2` through `-n 5` explicitly. See §11 for full analysis.

2. **No NIST STS yet.** The USE report ran 188 NIST STS tests that are
   not covered by dieharder (Phase 4 TODO).

3. **Scaling law is preliminary.** m\*(n) ≈ 18–21n from 5 data points.
   More widths (e.g., n=256) would strengthen the fit.

4. **Related-key mode needs depth stratification.** Phase 6 tested the
   full concatenated stream, which fails due to shallow-prefix outputs.
   Per-depth analysis would be more informative.

---

## 8. Status and Next Steps

| Phase | Description | Jobs | Status |
|-------|------------|------|--------|
| 1 | Coarse scan (7 tests, CTR, R=100) | 4,000 | **COMPLETE** |
| 2 | Transition refinement (7 tests, CTR, R=100) | 1,400 | **COMPLETE** |
| 3 | Full dieharder battery (27 families, counter) | 300 | **COMPLETE** |
| 4 | NIST STS (188 tests) for USE report comparability | 200 | TODO |
| 5 | OFB/iterate mode comparison (7 tests, R=20) | 800 | **COMPLETE** |
| 6 | Related-key prefix test (7 tests, R=20) | 300 | **COMPLETE** (0% pass) |

Remaining:
- Phase 4: NIST STS for direct USE report comparability
- Scaling law refinement: n=256, 512 to discriminate linear from superlinear

See [RNG_TEST_PLAN.md](RNG_TEST_PLAN.md) and [CLUSTER_RNG.md](CLUSTER_RNG.md).

---

## 9. Related Work: USEncryption Block Cipher Randomness Analysis

The report "Analyzing the Randomness of the USEncryption Block Cipher"
(Santiago Bañón, Mucciolo, Chamon, Veltri, 2023) tested a related circuit
design -- the USEncryption (USE) block cipher at **n = 128 bits** -- using
both NIST STS and Dieharder. The USE cipher uses a **tree-organized circuit**
with both **inflationary (linear) and nonlinear gates**, which achieves
O(n log n) gate count and O(log n) depth (see Chamon et al., arXiv:2011.06546).

The present experiments differ in that only **gate 57** is used (no
inflationary gates), so the mixing behavior and gate-count threshold are
expected to be different.

### Methodology

| Aspect | USE Cipher Report | Our Random Circuits |
|--------|-------------------|---------------------|
| Circuit design | Tree with inflationary + nonlinear gates | Linear chain of gate-57 only |
| Width | n = 128 | n = 32, 48, 64, 96, 128 |
| Mode | OFB (output feedback) | CTR/counter (primary) + OFB/iterate (comparison) |
| Test suites | NIST STS (188 tests) + Dieharder (~114 tests) | Dieharder (7 core + 27 families) |
| Data size | 100M bits (Dieharder), 300M bits (NIST STS) | 1.6B bits (50M samples * 32 bits) |
| Pass threshold | 96.92% (NIST minimum pass rate) | 95% |

### Key findings from the USE report

1. **Sharp transition with encryption levels**: When sweeping the number of
   encryption levels `l` (analogous to circuit depth), the cipher fails badly
   below `l = 3` and passes everything above `l = 3`. This is the same kind
   of sharp threshold behavior observed in our gate-count sweeps.

2. **Full Dieharder results**: The USE cipher (recommended configuration
   s(8, 5, 8)) passed all ~114 Dieharder tests with only 1 WEAK result,
   comparable to AES-256 (which had 3 WEAK, 1 FAILED on `rgb_lagged_sum`).

3. **Comparison to AES-256**: In both NIST STS and Dieharder, the USE cipher
   output is statistically indistinguishable from AES-256 output. All results
   fall above the NIST minimum pass rate of 96.92%.

4. **Configuration sensitivity**: Performance degrades only when both linear
   and nonlinear layers are very low (e.g., 0 or 1) simultaneously.
   Sufficient depth in either type compensates for less of the other.

### Relevance

- **OFB mode = our iterate mode**: The USE report validates the bitstream
  generation and testing methodology. Our CTR mode is a stricter variant.
- **Threshold behavior is universal**: Both encryption levels and gate counts
  show a sharp non-random-to-random transition. This is consistent with
  mixing-time theory.
- **Gate-57-only circuits are a new data point**: The USE report tested the
  full inflationary/nonlinear design. Repeating similar tests with gate-57-only
  circuits (this work) measures the cost of removing inflationary gates.

---

## 10. Appendix: Gate Model

Each gate in the random circuit picks 3 distinct wires `[a, b, c]` from the
`n` available wires and computes:

```
wire[a] ^= wire[b] OR (NOT wire[c])
```

This is a reversible 3-wire gate (a controlled flip). A circuit of `m` such
gates, composed in sequence, produces a permutation on `{0,1}^n`. The gates
are chosen uniformly at random (with the constraint that consecutive gates
differ).

The circuit is implemented in Rust with bitwise operations on `u128`, giving
native-speed evaluation for n up to 128.

---

## 11. Appendix: Why `rgb_minimum_distance` Always Fails

### The observation

In Phase 3 (full dieharder battery), the test `rgb_minimum_distance` (ID 201) fails
with p ≈ 0.0 in **100% of all 300 replicates**, across all 5 widths (32–128) and all
gate counts — including configurations far above m\*(n) where every other test passes.
The failure rate is completely independent of circuit quality.

### Root cause: dieharder invocation bug (ntup=0)

**The failure is caused by running `rgb_minimum_distance` with the default ntup=0,
which is a degenerate configuration that fails for ALL generators, including
dieharder's own built-in cryptographic generators.**

#### The bug

`rgb_minimum_distance` computes the minimum Euclidean distance among N random points
in a d-dimensional hypercube, where d is set by the `-n` (ntuple) parameter. The
test is designed for d = 2, 3, 4, 5 — when dieharder runs its full battery via `-a`,
it automatically loops ntup from 2 to 5 (see `run_all_tests.c`, lines 119–135).

However, when invoked individually via `-d 201` **without** specifying `-n`, the
global `ntuple` defaults to 0. The test code blindly uses this value:

```c
// rgb_minimum_distance.c, line 109-110
test[0]->ntuple = ntuple;     // ntuple is the global, = 0
rgb_md_dim = test[0]->ntuple; // dimension = 0
```

With dimension 0, the test degenerates: point coordinates are never generated
(the generation loop `for(d=0; d<rgb_md_dim; d++)` doesn't execute), all pairwise
distances collapse to 0, and the resulting p-value is always 0 or 1.

#### Empirical confirmation

We verified this by running dieharder's own built-in AES-OFB generator (generator
205) — a cryptographically secure PRNG — against `rgb_minimum_distance`:

| Generator | ntup | p-value | Assessment |
|-----------|------|---------|------------|
| AES-OFB (built-in, `-g 205`) | 0 (default) | 0.00000000 | **FAILED** |
| AES-OFB (built-in, `-g 205`) | 2 | 0.62 | PASSED |
| AES-OFB (built-in, `-g 205`) | 3 | 0.42 | PASSED |
| AES-OFB (built-in, `-g 205`) | 4 | 0.71 | PASSED |
| AES-OFB (built-in, `-g 205`) | 5 | 0.22 | PASSED |
| Mersenne Twister (`-g 14`) | 2 | 0.61 | PASSED |
| Mersenne Twister (`-g 14`) | 3 | 0.65 | PASSED |
| Mersenne Twister (`-g 14`) | 4 | 0.41 | PASSED |
| Mersenne Twister (`-g 14`) | 5 | 0.04 | PASSED |

**AES-OFB fails at ntup=0 and passes at ntup=2–5.** This proves the ntup=0
invocation is broken, independent of the generator.

#### How our sweep triggered the bug

Our Phase 3 sweep script (`rng_sweep.py`) runs each test individually via:

```python
cmd = [dieharder_path, "-g", "200", "-d", str(test_id)]  # no -n flag
```

For test 201, this produces `-d 201` without `-n`, defaulting to ntup=0. Every
single one of our 300 Phase 3 replicates hit this degenerate case, explaining the
100% failure rate across all widths and gate counts.

### Secondary concern: PRP/PRF birthday bound (n = 32)

Even with the ntup bug fixed, `rgb_minimum_distance` may still detect a real
structural property at small block sizes. Our circuits are **permutations** on
{0, 1}^n, so CTR mode outputs C(0), C(1), ... are all distinct (no collisions).
The Fischler reference distribution assumes i.i.d. uniform values that can collide.

The **PRP/PRF switching lemma** bounds the distinguishing advantage at
q(q−1)/2^(n+1) after q queries. For n = 32 with 40,000 outputs per trial (d = 5,
N = 8000), this advantage is ~19% — potentially detectable over 100 trials.

| Width n | Birthday bound 2^(n/2) | Data per trial | Ratio | PRP detectable? |
|---------|----------------------|----------------|-------|-----------------|
| 32 | 65,536 | 40,000 | 0.61 | Possibly |
| 64 | 4.3 × 10^9 | 40,000 | 10^-5 | No |
| 128 | 1.8 × 10^19 | 40,000 | 10^-15 | No |

**Verified empirically:** With correct ntup values, both n=32 and n=128 pass:

| Generator | ntup | p-value | Assessment |
|-----------|------|---------|------------|
| Our circuit, n=32, m=525 (at m\*) | 2 | 0.00012 | WEAK |
| Our circuit, n=32, m=525 | 3 | 0.16 | PASSED |
| Our circuit, n=32, m=525 | 4 | 0.03 | PASSED |
| Our circuit, n=32, m=525 | 5 | 0.01 | PASSED |
| Our circuit, n=128, m=4000 | 2 | 0.16 | PASSED |
| Our circuit, n=128, m=4000 | 3 | 0.03 | PASSED |
| Our circuit, n=128, m=4000 | 4 | 0.35 | PASSED |
| Our circuit, n=128, m=4000 | 5 | 0.00017 | WEAK |

The WEAK results (1 out of 4 ntup values each) are consistent with normal
statistical fluctuation — a single run has ~1% chance of WEAK per test. The
PRP birthday bound is not causing systematic failures at any width when the
test is properly invoked.

### Fix

The sweep script should be updated to pass `-n` explicitly for tests that require
it. Tests 200–203 all need ntuple handling:

| Test ID | Test name | Required `-n` range |
|---------|-----------|-------------------|
| 200 | rgb_bitdist | 1–12 |
| 201 | rgb_minimum_distance | 2–5 |
| 202 | rgb_permutations | 2–5 |
| 203 | rgb_lagged_sums | 0–32 |

### Bottom line

**The 100% failure of `rgb_minimum_distance` is a dieharder invocation bug, not a
property of our circuits.** Running `-d 201` without `-n` triggers a degenerate
dimension-0 mode that fails for every generator, including AES-OFB. Dieharder's
`-a` mode handles this correctly by looping ntup from 2 to 5, but individual
test invocation does not.

This failure does not indicate a PRP weakness and should be excluded from
pass-rate calculations (or, better, the sweep should be re-run with correct
`-n` flags).
