# Related work and contribution boundaries

A research project by [Requant Network](https://requant.network).

Anthropic introduces FlashProve as a research prototype in [Progress on provable inference for large language models](https://www.anthropic.com/research/provable-inference). The [pinned implementation](https://github.com/anthropics/FlashProve/tree/9e2bdd8ff5bf9c62f18263d7dac189b0400b260c) supplies the commitment system, quantized model execution, proof generation, CPU verifier, accounting statements and its formal-development boundaries.

This research supplies a bounded consumer-Blackwell port and executable evidence. It does not replace the original proof system or extend the formal claims. The protocol and verifier are unchanged; resource adaptations change buffering, public bin partitioning, immutable-table placement, supported exact implementation paths and a device-memory reserve.

## Engineering contribution

The compact routed expert keeps its WMMA arithmetic while reducing dynamic shared storage to 81 KiB. Its output overlay is included explicitly. Independent integer decoding tests and a complete accepted native proof cover different layers: the former diagnose device arithmetic and rounding on bounded inputs, while the latter checks the resulting complete small-model proof under the original verifier.

Consumer-card compatibility required more than an architecture flag. Separate histogram opt-ins assumed 128 KiB, packed tables assumed another 128 KiB shared copy, the tiled engine used a 108 KiB pipeline, and the commitment path reserved 24 GiB of VRAM regardless of model size. These are retained as concrete compatibility findings. Replacing them does not establish a speed advantage over the original Hopper implementation, which is not timed on an H100 in this study.

## Interpretation and next work

Accepted synthetic proofs demonstrate bounded interoperability of the modified CUDA prover with the original C++ CPU verifier. Acceptance retains the native coverage, proof-of-work accounting and external commitment assumptions. It does not establish weight hiding, production-model safety, adaptive soundness or equivalence with the separate Lean verifier.

The public deliverable contains the original pin, attributed patches, independent device tests, accepted public proof artifacts, native rejecting controls and reproducible build/run instructions. Further forest fusion, larger synthetic models, service batching and application deployment are separate workloads. They require their own correctness, memory and performance evidence.
