# Swap-with-Flip Gadgets: Formal Specification

## 1. Overview

Swap-with-flip gadgets are 3-wire ECA57 circuits that implement a **2-wire swap** combined with **optional bit-flips**. They serve as building blocks for constructing wire shuffle + bit-flip transformations (`B_{w,s}`) used in obfuscation pipelines.

## 2. Mathematical Definition

### 2.1 The β_{w,s} Function

Let `w` be a permutation on wires `{1, ..., n}` and `s ∈ {0,1}^n` be a bit-flip mask.

The wire shuffle + bit-flip function is defined as:

```
β_{w,s}(x_1, ..., x_n) = (x_{w(1)} ⊕ s_1, ..., x_{w(n)} ⊕ s_n)
```

Where:
- `w(i)` is the source wire for output wire `i`
- `s_i` indicates whether output wire `i` is flipped (XOR with 1)
- `⊕` denotes XOR (addition mod 2)

### 2.2 Swap-with-Flip Gadget

A swap-with-flip gadget implements a restricted form of `β_{w,s}` for 3 wires where:
- Wires 0 and 1 are swapped
- Wire 2 (auxiliary) is preserved
- Flip mask `(s_0, s_1)` is applied to swapped outputs

**Input-Output Relationship:**
```
output[0] = input[1] ⊕ s_0
output[1] = input[0] ⊕ s_1
output[2] = input[2]  (preserved)
```

### 2.3 The Four Flip Masks

| Name | Mask (s_0, s_1) | Behavior |
|------|-----------------|----------|
| `no_flip` | (0, 0) | Pure swap: `out = (in[1], in[0], in[2])` |
| `flip_wire0` | (1, 0) | Swap + flip output 0: `out = (in[1]⊕1, in[0], in[2])` |
| `flip_wire1` | (0, 1) | Swap + flip output 1: `out = (in[1], in[0]⊕1, in[2])` |
| `flip_both` | (1, 1) | Swap + flip both: `out = (in[1]⊕1, in[0]⊕1, in[2])` |

## 3. Truth Tables

### 3.1 no_flip (s = 00)
```
Input  | Output
000    | 000
001    | 001
010    | 100
011    | 101
100    | 010
101    | 011
110    | 110
111    | 111
```

### 3.2 flip_wire0 (s = 10)
```
Input  | Output
000    | 001
001    | 000
010    | 101
011    | 100
100    | 011
101    | 010
110    | 111
111    | 110
```

### 3.3 flip_wire1 (s = 01)
```
Input  | Output
000    | 010
001    | 011
010    | 110
011    | 111
100    | 000
101    | 001
110    | 100
111    | 101
```

### 3.4 flip_both (s = 11)
```
Input  | Output
000    | 011
001    | 010
010    | 111
011    | 110
100    | 001
101    | 000
110    | 101
111    | 100
```

## 4. Circuit Implementation

### 4.1 Gate Set

All gadgets use **ECA57 gates** (Elementary Cellular Automaton Rule 57):

```
target ^= (ctrl1 OR NOT ctrl2)
```

Equivalent to: `target ^= (~ctrl2 | ctrl1)`

### 4.2 Gate Representation

Each gate is a triple `[target, ctrl1, ctrl2]` where:
- `target` ∈ {0, 1, 2}: wire to modify
- `ctrl1` ∈ {0, 1, 2}: first control wire
- `ctrl2` ∈ {0, 1, 2}: second control wire

### 4.3 Example Circuit (no_flip, 6 gates)

```
Gates: [[0,1,2], [1,0,2], [0,1,2], [1,0,2], [0,1,2], [1,0,2]]

Wire 0: ─●─────●─────●─────
Wire 1: ───●─────●─────●───
Wire 2: ─○───○───○───○───○─

● = ctrl1 (positive control)
○ = ctrl2 (negative control, inverted)
```

## 5. Gadget Library Statistics

Current library (6-12 gates):

| Flip Mask | Count | Min Gates | Max Gates |
|-----------|-------|-----------|-----------|
| no_flip | 60 | 6 | 12 |
| flip_wire0 | 47 | 6 | 12 |
| flip_wire1 | 47 | 6 | 12 |
| flip_both | 49 | 6 | 12 |
| **Total** | **203** | 6 | 12 |

Distribution by gate count:
- 6 gates: ~17 circuits
- 8 gates: ~30 circuits
- 10 gates: ~30 circuits
- 12 gates: ~23 circuits

## 6. Integration Styles

### 6.1 Style A: Separate Flip Layer

1. Construct wire shuffle circuit `B_w` (permutation only)
2. Add explicit X gates for each wire where `s_i = 1`

```
B_{w,s} = X_layer(s) ∘ B_w
```

**Pros:** Simple, works for any width
**Cons:** X gates are visible structure

### 6.2 Style B: Embedded Gadgets

1. Decompose permutation into 2-wire swaps (Knuth or Waksman)
2. For each swap, select gadget with appropriate flip mask
3. Compose gadgets with wire remapping

```
B_{w,s} = G_k ∘ ... ∘ G_2 ∘ G_1
```

Where each `G_i` is a swap-with-flip gadget.

**Pros:** Bit-flips hidden inside gadget structure
**Cons:** Requires gadget library, limited to 2-wire operations

## 7. Composition Rules

### 7.1 Inverse

The inverse of `β_{w,s}` is:

```
β_{w,s}^{-1} = β_{w^{-1}, w^{-1}(s)}
```

### 7.2 Composition

For sequential application:

```
β_{w,s} ∘ β_{w',s'} = β_{w∘w', w'(s) ⊕ s'}
```

## 8. Verification

A circuit `C` correctly implements swap-with-flip for mask `(s_0, s_1)` iff for all inputs `x ∈ {0,1}^3`:

```python
def verify_swap_flip(circuit, s0, s1):
    for x in range(8):
        bits = [(x >> i) & 1 for i in range(3)]
        out = circuit.apply(bits)

        expected_0 = bits[1] ^ s0  # swap + flip
        expected_1 = bits[0] ^ s1  # swap + flip
        expected_2 = bits[2]       # preserved

        if out != [expected_0, expected_1, expected_2]:
            return False
    return True
```

## 9. Usage

### 9.1 Python (SAT RevSynth)

```python
from synthesizers.shuffle_bitflip import ShuffleBitflipGenerator

generator = ShuffleBitflipGenerator(width=6)
circuit = generator.generate(
    permutation=[3, 1, 5, 0, 2, 4],
    flip_mask=[1, 0, 1, 0, 0, 1]
)
```

### 9.2 Rust (Local Mixing)

```rust
use local_mixing::algorithms::shuffle_bitflip::ShuffleBitflipGenerator;
use local_mixing::config::{ShuffleBitflipConfig, FlipMode};

let config = ShuffleBitflipConfig {
    enabled: true,
    flip_mode: FlipMode::Embedded,
    gadget_library_path: Some("gadgets.json".into()),
    ..Default::default()
};

let generator = ShuffleBitflipGenerator::new(6, config);
let circuit = generator.generate(&[3, 1, 5, 0, 2, 4], &[1, 0, 1, 0, 0, 1], &mut rng);
```

## 10. Database Locations

| Data | Location | Format |
|------|----------|--------|
| Swap-flip gadgets | `identity-factory-api/cluster_circuits.db` | SQLite |
| Gadget JSON library | `sat_revsynth/data/swap_flip_gadgets.json` | JSON |
| Wire shuffle circuits | `identity-factory-api/wire_shuffler.db` | SQLite |

## 11. References

- PLAN_wire_shuffle_bitflip.md - Integration plan
- sat_revsynth/scripts/enumerate_swap_flip_gadgets.py - SAT enumeration
- local_mixing/src/algorithms/shuffle_bitflip.rs - Rust implementation
- local_mixing/src/config.rs - Configuration types

---

*Last updated: 2026-02-10*
