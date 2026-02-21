# Random Circuits as Pseudorandom Permutations: RNG Testing Report

**Date:** 2026-02-19 (updated 2026-02-19)
**Status:** Local sweep complete for n=32; cluster sweep planned for n=32-128

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

### Mode 1: Counter mode (the correct PRP test)

```
1. Evaluate: C(0), C(1), C(2), ..., C(k)
   Feed the inputs 0, 1, 2, ... in order (like a counter).
2. Concatenate the n-bit outputs into a bitstream.
3. Feed to dieharder.
```

This is the **most direct test of pseudorandom permutation (PRP) quality**.
Each output C(i) depends on a **single application** of the circuit to a
known input. If the outputs look random, it means the circuit itself is a
good PRP -- it scrambles structured inputs into random-looking outputs in
one shot. This is analogous to block cipher CTR mode.

Counter mode is harder to pass than iterate mode because there is no
cumulative mixing -- the circuit must be good enough on its own.

### Mode 2: Iterate (state machine / OFB)

```
1. Pick a random starting state x_0 in {0,1}^n
2. Discard the first B steps (burn-in) to escape short transients:
       x_1 = C(x_0),  x_2 = C(x_1),  ...,  x_B = C(x_{B-1})
3. Emit: x_{B+1}, x_{B+2}, ..., x_{B+k}
   Each x_t is an n-bit block. Concatenate all blocks into one long bitstream.
4. Feed the bitstream to dieharder.
```

This tests whether iterating the permutation produces output
indistinguishable from random bits. However, **iterate mode conflates the
quality of C with the mixing effect of re-application**. After k steps,
the output is C^k(x_0) -- a composition of k copies of C. Even a mediocre
permutation applied millions of times can produce random-looking output,
because each re-application further mixes the state.

As a result, iterate mode gives a **lower (easier) threshold** than counter
mode. A circuit that passes iterate mode may not be a good PRP -- it may
just have good orbit structure under repeated composition.

### Mode 3: Random-input

```
1. For each step, sample a fresh random x_t.
2. Emit C(x_t).
```

The weakest test -- independent random inputs each time.

### Which mode matters?

**Counter mode is the definitive test for pseudorandomness.** The PRP
definition asks: "Is C indistinguishable from a truly random permutation?"
The natural way to test this is to evaluate C on known inputs and check
whether the outputs look random. Counter mode does exactly this.

Iterate mode is useful as a secondary check (testing orbit/cycle
structure), but **m\*(n) from counter mode is the number to report**.

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

## 6. Results (n=32, counter mode)

### Setup

- **Width**: n = 32 wires
- **Gate counts**: m = 50, 100, 150, 200, 300, 500, 750
- **Replicates**: R = 5 per configuration
- **Tests**: 7 core dieharder tests (8 p-values), pipe mode
- **Stream mode**: counter (C(0), C(1), ..., C(k))

### Counter mode results

| m (gates) | Pass rate | Notes |
|-----------|-----------|-------|
| 50        | 0% (0/5)  | All tests p=0 |
| 100       | 0% (0/5)  | All tests p=0 |
| 150       | 0% (0/5)  | All fail |
| 200       | 0% (0/5)  | Birthdays passes, rest fail |
| 300       | 0% (0/5)  | 5-6 of 8 tests pass but rank_6x8 + monobit still fail |
| 500       | **100%** (5/5) | All circuits pass all tests |
| 750       | **100%** (5/5) | Stable |

**m\*(32) = 500 gates** (~15.6 gates/wire) in counter mode.

### Iterate mode comparison (same tests, R=5)

| m (gates) | Counter | Iterate |
|-----------|---------|---------|
| 200       | 0%      | 0%      |
| 300       | 0%      | 40%     |
| 500       | 100%    | 100%    |

Both modes give m\*(32) = 500, but the transition is sharper in counter mode:
at m=300, iterate passes 40% (cumulative mixing helps) while counter passes 0%.

### Bottleneck tests

At m=300 in counter mode, most individual tests pass (birthdays, rank_32x32,
runs, count_1s, sts_runs) but `diehard_rank_6x8` and `sts_monobit` consistently
fail — these are the last tests to be satisfied as gate count increases.

---

## 7. Caveats and Limitations

1. **Only R=5 replicates.** Pass-rate resolution is limited to 20% increments.
   The cluster sweep with R=100 will give ~1% resolution and smooth curves.

2. **Only n=32 tested so far.** No data yet for n=48, 64, 96, 128.
   The cluster sweep covers all five widths.

3. **No scaling law yet.** With only one data point (m*(32) = 500), the
   function m*(n) cannot be fit. Need 3-4 widths minimum.

4. **File mode data reuse (historical).** Early sweeps used file mode which
   caused dieharder to silently rewind small files. All current sweeps use
   pipe mode, which avoids this entirely.

---

## 8. Next: Cluster Sweep

R=100 replicates across n = {32, 48, 64, 96, 128} on BU SCC (SGE).
4,000 total jobs, counter mode, 7 core tests, pipe mode.

See [RNG_TEST_PLAN.md](RNG_TEST_PLAN.md) for the test matrix and
[CLUSTER_RNG.md](CLUSTER_RNG.md) for the deployment guide.

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
| Width | n = 128 | n = 32 (initial sweep) |
| Mode | OFB (output feedback) | Iterate (equivalent to OFB) |
| Test suites | NIST STS (188 tests) + Dieharder (~114 tests) | Dieharder (7-30 tests) |
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

- **OFB mode = iterate mode**: The USE report validates the bitstream
  generation and testing methodology.
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
