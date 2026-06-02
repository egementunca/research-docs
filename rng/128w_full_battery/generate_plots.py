#!/usr/bin/env python3
"""Generate plots for 128-wire full-battery results document."""

import json
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PLOT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_MIXING = "/usr3/graduate/etunca/research-group/local_mixing"


def load_json_results(pattern):
    """Load all JSON result files matching a glob pattern."""
    results = []
    for f in sorted(glob.glob(pattern)):
        with open(f) as fp:
            d = json.load(fp)
        # extract gate count from filename: w128_g600_r0.json
        base = os.path.basename(f)
        parts = base.replace(".json", "").split("_")
        gates = int(parts[1][1:])
        rep = int(parts[2][1:])
        tests = d.get("tests", d.get("results", []))
        passed = sum(1 for t in tests if t["assessment"] == "PASSED")
        failed = sum(1 for t in tests if t["assessment"] == "FAILED")
        weak = sum(1 for t in tests if t["assessment"] == "WEAK")
        total = passed + failed + weak
        results.append({
            "gates": gates,
            "rep": rep,
            "passed": passed,
            "failed": failed,
            "weak": weak,
            "total": total,
            "pass_frac": passed / total if total > 0 else 0,
            "tests": tests,
        })
    return results


def load_aes_baseline(pattern):
    """Parse AES dieharder text output files."""
    results = []
    for f in sorted(glob.glob(pattern)):
        with open(f) as fp:
            lines = fp.readlines()
        passed = sum(1 for l in lines if "PASSED" in l)
        failed = sum(1 for l in lines if "FAILED" in l)
        weak = sum(1 for l in lines if "WEAK" in l)
        total = passed + failed + weak
        results.append({
            "passed": passed,
            "failed": failed,
            "weak": weak,
            "total": total,
            "pass_frac": passed / total if total > 0 else 0,
        })
    return results


def load_ctr_variance(pattern):
    """Load CTR variance JSON files."""
    results = []
    for f in sorted(glob.glob(pattern)):
        with open(f) as fp:
            d = json.load(fp)
        base = os.path.basename(f)
        # ctr_var_b0.json -> burn_in = 0
        burn_in = int(base.replace("ctr_var_b", "").replace(".json", ""))
        tests = d.get("tests", d.get("results", []))
        passed = sum(1 for t in tests if t["assessment"] == "PASSED")
        total = len(tests)
        results.append({
            "burn_in": burn_in,
            "passed": passed,
            "total": total,
            "pass_frac": passed / total if total > 0 else 0,
        })
    return results


# ── Style ──────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#fafafa",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
})

BLUE = "#2563eb"
RED = "#dc2626"
GREEN = "#16a34a"
ORANGE = "#ea580c"
GRAY = "#6b7280"


# ══════════════════════════════════════════════════════════════════════════
# Figure 1: Full sweep — Uniform vs Balanced at all gate counts
# ══════════════════════════════════════════════════════════════════════════

all_uniform = load_json_results(
    os.path.join(LOCAL_MIXING, "results_128w_uniform_full/results/w128_g*.json")
)
all_balanced = load_json_results(
    os.path.join(LOCAL_MIXING, "results_128w_balanced_full/results/w128_g*.json")
)

def gate_summary(results):
    """Group results by gate count, return (gates, mean_pass%, individual_fracs)."""
    from collections import defaultdict
    by_gate = defaultdict(list)
    for r in results:
        by_gate[r["gates"]].append(r["pass_frac"] * 100)
    out = []
    for g in sorted(by_gate):
        fracs = by_gate[g]
        out.append((g, np.mean(fracs), fracs))
    return out

u_summary = gate_summary(all_uniform)
b_summary = gate_summary(all_balanced)

fig, ax = plt.subplots(figsize=(10, 6))

# Plot uniform
u_gates = [s[0] for s in u_summary]
u_means = [s[1] for s in u_summary]
ax.plot(u_gates, u_means, "o-", color=RED, linewidth=2.5, markersize=8, label="Uniform", zorder=4)
for g, mean, fracs in u_summary:
    jitter = np.random.default_rng(int(g)).uniform(-15, 15, len(fracs))
    ax.scatter([g + j for j in jitter], fracs, color=RED, s=20, alpha=0.35, zorder=3)

# Plot balanced
b_gates = [s[0] for s in b_summary]
b_means = [s[1] for s in b_summary]
ax.plot(b_gates, b_means, "s-", color=BLUE, linewidth=2.5, markersize=8, label="Balanced", zorder=4)
for g, mean, fracs in b_summary:
    jitter = np.random.default_rng(int(g)+1).uniform(-15, 15, len(fracs))
    ax.scatter([g + j for j in jitter], fracs, color=BLUE, s=20, alpha=0.35, zorder=3)

ax.axhline(y=95, color=GRAY, linestyle="--", alpha=0.5, label="95% threshold")
ax.set_xlabel("Number of gates")
ax.set_ylabel("Tests passed (%)")
ax.set_title("128 wires — Full Dieharder battery (30 tests)\nEach dot = one circuit, line = mean across 10 circuits")
ax.set_ylim(0, 105)
ax.legend(loc="lower right", fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(PLOT_DIR, "fig1_uniform_vs_balanced.png"), dpi=150)
print("Saved fig1_uniform_vs_balanced.png")
plt.close()

# Keep references for fig6
balanced_1000 = [r for r in all_balanced if r["gates"] == 1000]


# ══════════════════════════════════════════════════════════════════════════
# Figure 2: Phase 1+2 m*(n) pass rate curves (from RESULTS.md data)
# ══════════════════════════════════════════════════════════════════════════

# Data transcribed from RESULTS.md (CTR mode, 7 core tests, R=100)
phase12_data = {
    32:  [(200, 0), (250, 0), (300, 1), (350, 9), (400, 39), (450, 72),
          (500, 90), (525, 96), (550, 92), (575, 98), (600, 97)],
    48:  [(300, 0), (400, 0), (500, 3), (600, 32), (650, 41), (700, 67),
          (750, 78), (800, 91), (850, 97), (900, 95), (950, 99), (1000, 95)],
    64:  [(400, 0), (600, 0), (800, 17), (900, 52), (1000, 74), (1100, 94),
          (1200, 96), (1500, 98), (2000, 99), (2500, 98)],
    96:  [(600, 0), (1000, 2), (1500, 71), (1750, 93), (2000, 98), (2250, 97),
          (2500, 95), (3000, 99), (4000, 100), (5000, 98)],
    128: [(1000, 0), (1500, 6), (2000, 73), (2250, 89), (2500, 98),
          (2750, 99), (3000, 100), (4000, 100), (5000, 100)],
}

fig, ax = plt.subplots(figsize=(10, 6))
width_colors = {32: "#8b5cf6", 48: ORANGE, 64: GREEN, 96: BLUE, 128: RED}

for n, data in phase12_data.items():
    gates = [d[0] for d in data]
    rates = [d[1] for d in data]
    ax.plot(gates, rates, "o-", color=width_colors[n], label=f"n={n}", markersize=5, linewidth=2)

ax.axhline(y=95, color=GRAY, linestyle="--", alpha=0.5, label="95% threshold")
ax.set_xlabel("Number of gates (m)")
ax.set_ylabel("Pass rate (%)")
ax.set_title("CTR mode — Pass rate vs gate count (7 core Dieharder tests, R=100)")
ax.legend(loc="lower right")
ax.set_ylim(-5, 105)
fig.tight_layout()
fig.savefig(os.path.join(PLOT_DIR, "fig2_mstar_curves.png"), dpi=150)
print("Saved fig2_mstar_curves.png")
plt.close()


# ══════════════════════════════════════════════════════════════════════════
# Figure 3: m*(n) scaling
# ══════════════════════════════════════════════════════════════════════════

mstar_data = [(32, 525), (48, 850), (64, 1200), (96, 2000), (128, 2500)]
ns = [d[0] for d in mstar_data]
ms = [d[1] for d in mstar_data]

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(ns, ms, "s-", color=BLUE, markersize=10, linewidth=2.5, label="m*(n) from data")

# linear fit
fit_ns = np.linspace(20, 140, 100)
ax.plot(fit_ns, 19.6 * fit_ns, "--", color=GRAY, alpha=0.6, label="m*(n) = 19.6·n")

ax.set_xlabel("Number of wires (n)")
ax.set_ylabel("m*(n) — gates needed for 95% pass rate")
ax.set_title("Scaling of m*(n) — CTR mode")
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(PLOT_DIR, "fig3_mstar_scaling.png"), dpi=150)
print("Saved fig3_mstar_scaling.png")
plt.close()


# ══════════════════════════════════════════════════════════════════════════
# Figure 4: CTR variance sanity check
# ══════════════════════════════════════════════════════════════════════════

ctr_data = load_ctr_variance(
    os.path.join(LOCAL_MIXING, "results_ctr_variance/ctr_var_b*.json")
)

fig, ax = plt.subplots(figsize=(8, 4))
burn_ins = [r["burn_in"] / 1e6 for r in ctr_data]
pass_fracs = [r["pass_frac"] * 100 for r in ctr_data]

ax.bar(range(len(burn_ins)), pass_fracs, color=BLUE, alpha=0.7, edgecolor=BLUE)
ax.set_xticks(range(len(burn_ins)))
ax.set_xticklabels([f"{b:.0f}M" for b in burn_ins], fontsize=10)
ax.set_xlabel("Counter starting offset (millions)")
ax.set_ylabel("Tests passed (%)")
ax.set_title("CTR mode variance check — same circuit, different counter offsets\n(128w, 1500g, balanced, 7 core tests)")
ax.set_ylim(0, 105)
ax.axhline(y=87.5, color=GREEN, linestyle="--", alpha=0.5, label="7/8 = 87.5%")
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(PLOT_DIR, "fig4_ctr_variance.png"), dpi=150)
print("Saved fig4_ctr_variance.png")
plt.close()


# ══════════════════════════════════════════════════════════════════════════
# Figure 5: Balanced vs Uniform comparison from LOAD_BALANCED_RESULTS.md
# ══════════════════════════════════════════════════════════════════════════

# Data from LOAD_BALANCED_RESULTS.md (CTR mode, 7 core tests, R=100)
lb_comparison = {
    32: {
        "gates": [400, 500],
        "standard": [39, 90],
        "balanced": [42, 95],
    },
    64: {
        "gates": [800, 1000, 1200],
        "standard": [17, 74, 96],
        "balanced": [43, 86, 99],
    },
    128: {
        "gates": [2000, 2500, 3000],
        "standard": [73, 98, 100],
        "balanced": [83, 97, 98],
    },
}

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=True)

for ax, n in zip(axes, [32, 64, 128]):
    d = lb_comparison[n]
    x = np.arange(len(d["gates"]))
    w = 0.35
    ax.bar(x - w / 2, d["standard"], w, label="Uniform", color=RED, alpha=0.65)
    ax.bar(x + w / 2, d["balanced"], w, label="Balanced", color=BLUE, alpha=0.65)
    ax.set_xticks(x)
    ax.set_xticklabels([str(g) for g in d["gates"]])
    ax.set_xlabel("Gates")
    ax.set_title(f"n = {n} wires")
    ax.axhline(y=95, color=GRAY, linestyle="--", alpha=0.4)
    if n == 32:
        ax.set_ylabel("Pass rate (%)")
    ax.set_ylim(0, 105)
    ax.legend(fontsize=9)

fig.suptitle("Balanced vs Uniform — CTR mode (7 core tests, R=100)", fontsize=14)
fig.tight_layout()
fig.savefig(os.path.join(PLOT_DIR, "fig5_balanced_vs_uniform.png"), dpi=150)
print("Saved fig5_balanced_vs_uniform.png")
plt.close()


# ══════════════════════════════════════════════════════════════════════════
# Figure 6: Per-test pass rates for balanced 1000g (full battery)
# ══════════════════════════════════════════════════════════════════════════

# Aggregate per-test results across the 4 balanced 1000g replicates
test_stats = {}
for r in balanced_1000:
    for t in r["tests"]:
        name = t["test_name"]
        ntup = t.get("ntup", 0)
        key = f"{name} (n={ntup})" if ntup else name
        if key not in test_stats:
            test_stats[key] = {"passed": 0, "total": 0}
        test_stats[key]["total"] += 1
        if t["assessment"] == "PASSED":
            test_stats[key]["passed"] += 1

# Sort by pass rate
sorted_tests = sorted(test_stats.items(), key=lambda x: x[1]["passed"] / max(x[1]["total"], 1))

fig, ax = plt.subplots(figsize=(10, max(6, len(sorted_tests) * 0.25)))
names = [t[0] for t in sorted_tests]
rates = [t[1]["passed"] / t[1]["total"] * 100 for t in sorted_tests]
colors_bar = [GREEN if r >= 75 else ORANGE if r >= 50 else RED for r in rates]

ax.barh(range(len(names)), rates, color=colors_bar, alpha=0.7)
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names, fontsize=8)
ax.set_xlabel("Pass rate across 4 replicates (%)")
ax.set_title("Per-test results — Balanced, 128w, 1000 gates (full battery)")
ax.set_xlim(0, 105)
ax.axvline(x=75, color=GRAY, linestyle="--", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(PLOT_DIR, "fig6_per_test_balanced_1000.png"), dpi=150)
print("Saved fig6_per_test_balanced_1000.png")
plt.close()

print("\nAll plots generated!")
