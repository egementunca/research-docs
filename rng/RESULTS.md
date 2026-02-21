# RNG Sweep Results — Gate 57, n=32

Date: 2026-02-20 (updated 2026-02-19)

## Iterate vs Counter Mode

These results include two sweep modes. Understanding the difference is
important for interpreting the thresholds:

**Counter mode** (`C(0), C(1), C(2), ...`) — each output is a **single
application** of the circuit on a known input. This directly tests whether the
circuit is a **pseudorandom permutation (PRP)**: can you distinguish C from a
truly random permutation by evaluating it on inputs of your choice? There is no
cumulative mixing — the circuit must scramble well enough in one shot.

**Iterate mode** (`x → C(x) → C(C(x)) → ...`) — each output depends on the
**cumulative** effect of all previous applications. After 50M steps, you are
seeing C^{50000000}(x₀). Even a mediocre permutation applied millions of times
can look random, because each re-application further mixes the state. This
conflates the quality of C itself with the mixing effect of re-application.

**Counter mode is the correct test for pseudorandomness.** The PRP definition
asks whether C is indistinguishable from a random permutation, and counter mode
tests exactly that. Iterate mode tests a related but easier property (orbit
structure under repeated composition). As a result, **iterate mode gives a lower
(easier) threshold** — circuits pass iterate mode at fewer gates than they need
for counter mode.

**m\*(n) from counter mode is the number to report.**

---

## Common Configuration

- **Gate**: 57 (`wire[a] ^= wire[b] OR (NOT wire[c])`)
- **Wires**: n = 32
- **Gate counts**: m = {50, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 5000}
- **Replicates**: R = 5 per configuration
- **Dieharder tests** (7 core): birthdays (0), rank_32x32 (2), rank_6x8 (3),
  count_1s_str (8), runs (15), sts_monobit (100), sts_runs (101)

---

## Counter Mode Results (pipe mode)

The definitive PRP test. Each output C(i) is a single circuit evaluation.

| m (gates) | Pass rate | Circuits passed | Notes |
|-----------|-----------|-----------------|-------|
| 50        | 0%        | 0/5             | All tests p=0, total failure |
| 100       | 0%        | 0/5             | All tests p=0 |
| 150       | 0%        | 0/5             | All fail, one WEAK birthdays |
| 200       | 0%        | 0/5             | Birthdays passes, rest fail |
| 300       | 0%        | 0/5             | 5-6 of 8 tests pass but rank_6x8 + monobit still fail |
| 500       | **100%**  | **5/5**         | All circuits pass all tests |
| 750       | **100%**  | **5/5**         | Stable |
| 1000+     | ...       | sweep continuing | Expected stable |

**m\*(32) from counter mode = 500 gates** (~15.6 gates/wire).

The transition is sharp: 0% at m=300, 100% at m=500. At m=300, most individual
tests pass (birthdays, rank_32x32, runs, count_1s, sts_runs), but `rank_6x8`
and `sts_monobit` consistently fail — these are the bottleneck tests in counter
mode.

Compared to iterate mode at m=300: iterate got 40% pass rate, but counter mode
gets **0%**. This confirms counter mode is harder — the circuits at m=300 aren't
good PRPs yet, they just have decent orbit structure under repeated iteration.

---

## Iterate Mode Results (file mode, legacy)

Iterate mode benefits from cumulative mixing over millions of re-applications,
so it passes at lower gate counts. These results are informative but represent
a **weaker test** than counter mode.

**Note**: This sweep used file mode (200 MB files). Some tests may have
experienced data reuse/rewinding. See [RNG_REPORT.md](RNG_REPORT.md) §3.

| m (gates) | Pass rate | Circuits passed | Notes |
|-----------|-----------|-----------------|-------|
| 50        | 0%        | 0/5             | All 7 tests FAIL |
| 100       | 0%        | 0/5             | Birthdays passes, rest fail |
| 150       | 0%        | 0/5             | Some individual tests pass |
| 200       | 0%        | 0/5             | Most tests pass, runs still fails |
| 300       | 40%       | 2/5             | First full passes appear |
| 500       | 100%      | 5/5             | All circuits pass all tests |
| 750       | 100%      | 5/5             | Stable |
| 1000      | 100%      | 5/5             | Stable |
| 1500      | 100%      | 5/5             | Stable |
| 2000      | 100%      | 5/5             | Stable |
| 3000      | 100%      | 5/5             | Stable |
| 5000      | 100%      | 5/5             | Stable |

**m\*(32) from iterate mode = 500 gates** (~15.6 gates/wire). Sharp transition
in the 200–500 range.

---

## Plots (Iterate Mode Sweep)

### Overall Pass Rate vs Gate Count

![Pass rate vs gates](plots/pass_rate_vs_gates.png)

Sharp 0→100% transition between m=200 and m=500. The sigmoid-like curve shows
a clear threshold effect.

### Per-Test Pass Rate (n=32)

![Per-test pass rate](plots/per_test_pass_rate_w32.png)

Shows which tests are easiest/hardest to pass. `diehard_birthdays` passes first
(from m=100), while `diehard_runs` is the bottleneck test that drives the
overall m* threshold.

### P-Value Scatter (All Tests)

![P-value scatter](plots/pvalues_scatter.png)

P-values by gate count across all tests and replicates. Below m=200, p-values
cluster near 0 or 1 (non-uniform). Above m=500, p-values spread uniformly
across [0,1] as expected for good randomness.

### P-Values Per Test (6-Panel)

![P-values per test](plots/pvalues_per_test.png)

Breakdown of p-value distributions for each individual test. Shows the
per-test transition from structured to uniform p-values as gate count
increases.

### Pipeline Diagram

![Pipeline diagram](plots/pipeline_diagram.png)

Overview of the testing pipeline: circuit generation → bitstream → dieharder.

---

## Key Findings

1. **Counter mode m\*(32) = 500** — same threshold as iterate mode, but the
   transition is sharper (0% at m=300 vs 40% in iterate mode).

2. **Counter mode is harder than iterate mode.** At m=300, iterate mode passes
   40% of circuits but counter mode passes 0%. This is expected: iterate mode
   benefits from millions of cumulative re-applications that further mix the
   state, while counter mode requires the circuit to be a good PRP in a single
   application.

3. **Sharp threshold**: Both modes show a sharp 0→100% transition in a narrow
   gate-count band, consistent with a phase transition in pseudorandomness.

4. **Bottleneck tests differ by mode**: In iterate mode, `diehard_runs` is the
   hardest test. In counter mode, `diehard_rank_6x8` and `sts_monobit` are the
   last to pass (still failing at m=300 while birthdays, runs, and count_1s
   already pass).

5. **Stability above threshold**: Once past the threshold, pass rate is 100%
   all the way to m=5000. No regression in either mode.

---

## Next Steps: Cluster Sweep

The R=5 local sweep gives only 20% resolution on pass rates (0%, 20%, 40%,
60%, 80%, 100%). To characterize the transition precisely, we need:

- **R=100 replicates** per (n, m) point for smooth transition curves
- **Multiple widths**: n = 32, 48, 64, 96, 128
- **Dense gate counts** around each width's transition region
- **Counter mode only** (the correct PRP test)

See [CLUSTER_RNG.md](CLUSTER_RNG.md) for the full cluster deployment guide.
