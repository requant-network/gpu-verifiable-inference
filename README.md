# Verifiable GPU Inference Research

A research project by [Requant Network](https://requant.network).

**Status: active research. Compact SM120 kernels pass independent GPU checks; the complete patched inference/proof cycle is still being validated.**

This study ports a pinned inference prover to the RTX 5060 Ti 16 GB and investigates whether exact fused arithmetic can fit consumer Blackwell's shared-memory budget. The question is concrete: can the original commitment, model execution, proof and CPU verification run while retaining all arithmetic and acceptance checks?

## Results actually obtained

| Experiment | Coverage and result |
|---|---|
| Unmodified native CPU verifier | Stored synthetic proof accepted, exit 0, last line `YES` |
| Negative CPU controls | Incorrect ID, altered request/output/proof, and truncated proof are rejected |
| Compact fused routed experts | 384 cases per input seed, two seeds, 3,258,112 exact integer outputs in total |
| Expert shared memory | Maximum 82,944 bytes (81 KiB), within the measured device limit of 101,376 bytes (99 KiB) |
| Compact histogram kernels | 114 cases per seed, two seeds, 12,500,052 exact output counters in total |
| Histogram shared memory | At most 65,536 bytes (64 KiB), including the full 16-bit key range through public bin windows |
| First architecture/cuBLAS fallback | Full run fails at an unconditional 128 KiB histogram opt-in; retained as an unsuccessful baseline |
| Complete corrected GPU proof | Pending; passing isolated kernels is not treated as an accepted inference proof |

These correctness probes ran while other CPU compilation could be active. Their incidental times do not establish a speedup. The pinned source, patch, executed script and native binary hashes are retained in [results](results).

## How the fused kernel fits

The Hopper expert kernel has two A buffers and three B buffers. Its larger configurations exceed the SM120 per-block budget. The compact path keeps the original 128-row by 256-input arithmetic tile and WMMA operations, uses a single shared tile per operand, and synchronizes before reuse. It caps token tiles at sixteen slots.

The memory calculation also includes the WMMA output overlay. An early input-only estimate missed that overlay and produced an illegal-address failure for a larger token tile. The corrected allocation is the maximum of input and output footprints. This failed draft is documented because apparently rejected designs can fail through implementation mistakes, rather than an invalid mathematical idea.

Two independent input cohorts cover Q4/Q5 decoding, one through four signed-byte activation limbs, ragged routing, 1/17/33/65 tokens, 128/256 output rows, 256/1024 input coordinates, zero/max/min/random activations, absent and power-of-two gains, and fractional gains in eighths. The independent CPU decoder uses integer arithmetic and rational ties-to-even rounding. Every output is checked exactly, with no floating tolerance. Coverage is bounded to those scales and shapes; it is not a proof for arbitrary model weights.

## Other shared-memory adaptations

Range and lookup histograms use public windows over the output bins. A 16-bit key histogram scans four 16,384-bin windows rather than two 32,768-bin halves, reducing its allocation from 128 to 64 KiB. Counters are merged to the same global positions. Large range-table histograms are tiled without rejecting the originally supported 15-bit tables.

The generic tiled matrix engine uses two pipeline stages, reducing its footprint from 108 to 72 KiB while leaving its arithmetic tile and output overlay intact. Byte-fold combination selects a 96 KiB public resource cap and retains the existing exact fallback for larger shapes. Packed immutable lookup tables can remain in GPU memory rather than a 128 KiB shared copy. Occupancy selection uses the runtime's actual kernel resources for SM120.

Some separate lookup-forest fusion kernels still assume Hopper-sized buffers. The port selects their existing exact generic paths. The compact expert kernel remains fused. Further forest fusion is an optimization question, and its speed is not inferred from the expert experiment.

## Reproduction

FlashProve is pinned at `9e2bdd8ff5bf9c62f18263d7dac189b0400b260c`. Patches retain Anthropic's Apache-2.0 attribution. Run as an ordinary Linux user, with newly created private work directories under ancestors that other accounts cannot modify. Preserve the upstream compiler probe, secure-path checks and verifier rules.

```sh
python prepare_full.py build/FlashProve
cd build/FlashProve
verifier/build.sh
FLASH_GPU_ARCH=sm_120a prover/build.sh
cd ../..
python cpu_study.py build/FlashProve
```

The measured compiler is CUDA 13.3.73. Upstream's supported version is CUDA 13.2.86. The build retains the warning and compiler arithmetic sample; this deviation must accompany all results. A correct build is required before the full cycle below. The work directory must be new, and its parent must already be private:

```sh
python flash_cycle.py build/FlashProve /absolute/private/new-run
```

[flash_cycle.py](flash_cycle.py) runs the original target-example script. Small research wrappers time the unchanged native commit/prove/verify programs separately. Only an accepted response permits exporting public configuration, verification key, request, answer and proof. Private proving keys and rejected responses are not published. Exact exit codes, verdict lines, commitment ID, coverage, commitment assumptions, proof-of-work line and `result-v1` are retained.

The isolated expert bridge can be built with:

```sh
nvcc -O3 -std=c++17 -arch=sm_120a -DFLASH_EXPERT_COMPACT=1 -shared -Xcompiler=-fPIC \
  -Ibuild/FlashProve/prover native/expert_bridge.cu -o build/libexpert.so
python expert_validation.py
python expert_validation.py --seed 20261209 --output results/expert-replication.json
python memory_validation.py build/FlashProve
python memory_validation.py build/FlashProve --seed 20261209 --output results/memory-replication.json
python verify_records.py
```

GPU checks use NumPy 2.2.6 and CuPy 13.6.0. [patches/README.md](patches/README.md) distinguishes the fallback, compact expert, general memory and packed-table layers.

## Claims and remaining work

The accepted stored proof uses commitment ID `79a5a2bc7a469b40df73dedf40abeb740671e8ae8077738bd3743897aeb22183`, with `r=60`, `e=64`, tokens 61..63 and `y=yes`; it does not establish a new GPU inference result. Its complete coverage and accounting statements are retained in the CPU record. Reported accounting bits are not interpreted as an independently established security level.

The C++/CUDA implementation is not formally verified by the Lean development. Native acceptance does not establish weight hiding or remove the verifier's stated external assumptions. All weights in these experiments are synthetic. There is no throughput, energy, production-model or mining-income claim yet.

Remaining protocol work includes complete new GPU commitments/proofs, multiple requests, accepted public artifacts, rejecting controls on those artifacts, bounded configuration comparisons and final reports. CPU CI builds the pinned verifier and checks honest/tampered stored fixtures; it cannot rerun SM120 experiments. Original research scripts are [MIT licensed](LICENSE); patch modifications retain Apache-2.0 terms. See the [full research protocol](RESEARCH.md).
