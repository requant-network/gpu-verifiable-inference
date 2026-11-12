# Final report

A research project by [Requant Network](https://requant.network).

## Conclusion

The requested lower-shared-memory variant works on the RTX 5060 Ti 16 GB. Its routed expert kernel remains fused and uses at most 81 KiB of dynamic shared memory, within the measured 99 KiB opt-in limit. The complete patched commitment, inference/proof and original CPU-verification path accepts five newly generated synthetic proofs across two policies and three randomized commitments.

This is functional compatibility evidence under the original verifier, with unchanged field/protocol checks and explicit assumptions. It is not a performance comparison with an H100 or a claim about production-model security. The most concrete deliverable is the reproducible patch sequence and independently checkable public proof artifacts.

## What had to change

Architecture selection alone did not provide compatibility. Hopper-oriented buffers and opt-ins appeared in several independent components. The expert's two-A/three-B pipeline exceeded the device budget; replacing it with one shared tile per operand and sixteen token slots retained its WMMA arithmetic. Correct allocation also needed the output overlay. The failed input-only estimate demonstrated an implementation error, not a mathematical impossibility of the smaller-memory design.

Public histogram windows reduce their storage to 64 KiB and preserve the original output positions. A two-stage tiled engine reduces its budget to 72 KiB. Immutable packed lookup tables can remain in GPU memory. The port uses actual runtime occupancy and existing generic exact forest paths where separate fusion kernels remain too large.

The first memory-corrected full run then exposed an independent 24 GiB VRAM reserve, even for the small model. The consumer layer reserves 4 GiB and retains the separate driver allowance, allocation checks and reported pool peaks. Complete accepted runs qualify that choice for these configurations. A general worst-case engine-memory formula is not established.

## Why the evidence is layered

Independent integer expert tests diagnose decoding, signed-limb reconstruction, routing, fractional gain rounding and buffer reuse. Verbatim histogram and packed-table probes diagnose the memory transformations. These tests cover bounded inputs and cannot alone establish correctness of the whole prover.

The complete native cycles add the missing end-to-end check. Their proofs are then verified again from retained public files, with seven rejecting alterations per proof. The native metadata preserves the exact coverage and assumptions. Separate CPU CI rebuilds the original verifier and checks the committed artifacts on hosted CPU infrastructure. Neither those tests nor native acceptance transfer formal Lean claims to the C++/CUDA implementation.

## Performance and scope

Commitment, proving and verification are timed separately for each independent cycle or request. They are a small set of observations with different randomness and policy/coverage, not a fixed-input service-throughput benchmark. GPU pool high-water marks, host RSS and slab sizes have separate meanings and remain labelled. No whole-GPU peak or energy efficiency is inferred from the pool data.

The two original exact-match requests, the clipped-gap configuration and the two additional next-token-only prompts have different scopes. Their acceptance demonstrates interoperability within those scopes. It does not show that arbitrary earlier prompt tokens were the model's choices or that every accepted response has an unqualified strongest-possible argmax guarantee. The full `covered:`, accounting and commitment statements accompany every artifact.

## Completed protocol gates

| Required experiment | Retained evidence |
|---|---|
| Native CPU verification and rejecting controls | Stored honest proof plus five altered calls; exact exit/verdict/ID metadata |
| Attributed SM120 implementation and resource/arithmetic checks | Four pinned patch layers, compiler sample, two expert/histogram/table cohorts |
| Complete small GPU cycle through the original CPU verifier | Three commitment/proof cycles and two additional accepted requests |
| Independent commitments, requests, memory/phase data and altered public inputs | Three IDs, two prompt seeds, raw logs, five public artifact sets and forty whole native CPU calls |
| Bounded configurations, reproduction, limits and CPU CI | Exact-match/clipped-gap coverage, full source/artifact hashes, reports and hosted native rechecks |

## Follow-up priorities

First, enlarge the synthetic workload while measuring the true device-memory peak and preserving all native checks. The fixed 4 GiB engine reserve is an empirical qualified choice, so scaling should proceed with allocation evidence rather than a universal-fit claim.

Second, study the separate forest fusion kernels with compact tiles. The existing exact generic fallback provides a useful correctness baseline; a new fused implementation needs its own independent arithmetic and complete-proof checks. Third, benchmark service batching and request reuse with a declared repeated-latency design before reporting throughput or amortized setup gains.

Production weights, security evaluation, hiding experiments and formal implementation verification are outside this completed engineering study. [Results](RESULTS.md), [Methods](METHODS.md), [related work](RELATED_WORK.md), the [patch guide](patches/README.md) and the [protocol](RESEARCH.md) retain the concrete reproduction and claim boundaries.

## Follow-up closure, 12 November 2026

The [follow-up report](FOLLOWUP_REPORT.md) resolves the concrete priorities above with additional experiments, resource gates and updated conclusions. Its findings supersede the open-work wording in this historical campaign.
