# FlashProve SM120 port

A research project by [Requant Network](https://requant.network).

The patch applies to Anthropic FlashProve revision `9e2bdd8ff5bf9c62f18263d7dac189b0400b260c` (Apache-2.0). Patch modifications are provided under Apache-2.0; upstream notices remain applicable. Original standalone research scripts are MIT licensed.

| Patch | Apply to | Purpose and observed status |
|---|---|---|
| `sm120.patch` | Original pin, alone | Initial native SM120 build with existing exact cuBLAS expert fallback. Builds, but the complete run fails on a separate 128 KiB histogram opt-in. Historical baseline. |
| `sm120-compact.patch` | Original pin, alone | Alternative to the first patch: native SM120 with an 81 KiB fused expert path. Two independent cohorts pass 3,258,112 exact integer outputs. |
| `sm120-memory.patch` | After compact patch | 64 KiB histogram windows, two-stage 72 KiB tiled engine, 96 KiB fold cap and existing exact forest fallback. Two cohorts pass 12,500,052 histogram counters; the complete four-layer port accepts five new proofs. |
| `sm120-tables.patch` | After compact and memory patches | Keep the immutable packed lookup table in GPU memory and use runtime occupancy. Two table-access cohorts pass, and the complete four-layer port accepts five new proofs. |
| `sm120-reserve.patch` | After the previous three layers | Reserve 4 GiB for the engine rather than the unconditional 24 GiB. Keep the 2 GiB driver allowance, allocation checks and pool-peak reporting. Qualified by three accepted small-model commitment/proof cycles. |

`prepare_consumer.py` applies the final four layers in order to a new checkout. `prepare_full.py` preserves the earlier three-layer experiment. Never apply the initial cuBLAS-only patch before the compact patch: they are alternative architecture-selection layers. The default `sm_90a` branch retains the original algorithms. `FLASH_GPU_ARCH=sm_120a` explicitly selects the experimental consumer Blackwell path.

The expert kernel retains its 128-row/256-input tile and WMMA arithmetic. A single A/B tile and sixteen token slots replace Hopper's larger pipeline. Allocation includes the output overlay, which the first failed draft underestimated. Tests cover Q4/Q5, one through four activation limbs, ragged routing and fractional gain rounding against independent integer arithmetic. These bounded tests do not establish correctness for every model or a performance advantage.

The largest expert footprint follows directly from the tile constants, in bytes:

```text
A = 16 * (2 * 128 * 16 + 32) = 66,048
B(NL, NS) = 16 * (NL * NS * 16 + 32)
Original, NL=4/NS=32: 2*A + 3*B = 231,936 = 226.5 KiB
Compact, NL=4/NS=16: max(A+B, 256*NL*NS*4) = 82,944 = 81 KiB
```

The output-overlay term is necessary. Retaining NS=32 would require 128 KiB for the four-limb output even if its input buffers fit in 97 KiB. The sixteen-slot tile removes that resource conflict. [The figure](../figures/shared-memory.png) compares configured footprints with the device limit; it does not compare execution speed.

Histogram windows partition public bin ranges; all counts merge into their original positions. Large 15-bit range tables remain supported. Some separate lookup-forest fused kernels exceed the device budget and use the existing generic exact implementation. The compact expert remains fused.

No field, proof, commitment, verifier, secure-path or compiler-sample check is removed. CUDA 13.3.73 is a measured compiler deviation from upstream's supported 13.2.86; the build warning and arithmetic sample remain active. The accepted complete cycles and their public artifacts are retained in the [results](../RESULTS.md). `history/sm120-compact-v1.patch` is a rejected prototype retained for its output-overlay diagnostic; it is not part of the supported patch sequence.
