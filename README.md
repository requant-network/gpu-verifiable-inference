# Verifiable GPU Inference Research

SM120 support for a pinned inference prover, complete small-model proofs and independent verification.

A research project by [Requant Network](https://requant.network).

**Status: research in progress. No performance result is claimed yet.**

## Research question and scope

Build the pinned FlashProve CPU verifier, check the stored synthetic proof and run toy honest/tampered controls. Retain exact exit codes, verdict lines, IDs and coverage statements.

Implement reproducible SM120 support as an attributed patch over an immutable upstream pin, preserving compiler probes, arithmetic/protocol checks and verifier rules. Validate relevant device arithmetic and memory-resource adaptations.

Run the complete small synthetic model commitment -> inference/proof -> unmodified native CPU verification on RTX5060Ti16GB. Record and solve compatibility failures; do not substitute toy CPU proofs for a GPU inference result.

Execute independent synthetic commitments and multiple requests; measure setup, commit, proof, verification, proof size and memory separately. Add incorrect input, ID, output and proof controls and independently verify retained public artifacts.

Compare bounded configurations and supported optimization paths without weakening claims. Publish English full reproduction and limitations, replicated raw evidence, source/patch/build hashes, CPU CI and clear distinctions between tested C++ behavior and formal Lean claims.

## Experimental approach

Start from independent exact CPU controls and pinned upstream references. Build hardware-specific paths with validation enabled, then compare complete workloads rather than isolated instruction rates. Retain both independent input cohorts and unsuccessful/negative outcomes.

Fixed-input studies use five warm-ups and thirty measured observations where practical. Stochastic solves and proof commitments use independent inputs and separately identify repeated latency observations. Correctness checks, allocation, compilation, transfer and setup boundaries will be documented per timer.

## Reproduction and evidence

Executable studies and commands are added as experiments become runnable. The committed [research protocol](RESEARCH.md) defines the required experiments and completion gates; reports will distinguish completed measurements from pending work. No GPU benchmark is implied by this initial protocol checkpoint.

## Intended deliverables

- Independent CPU reference and negative correctness controls.
- Executable GPU/native implementations with exact upstream revisions.
- Raw seeded results, derived tables and source/result/build provenance.
- Complete English methods, findings, reproduction commands and limitations.
- CPU/reference/artifact CI on the final published commit.

## License and contributions

Original research code is [MIT licensed](LICENSE). Third-party implementations retain their own licenses. Contributions should include the source revision, environment, exact command, correctness evidence, complete timing boundaries and retained negative results.
