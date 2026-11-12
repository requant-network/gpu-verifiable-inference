# Research protocol

A research project by [Requant Network](https://requant.network).

## Required experiments

1. Build the pinned FlashProve CPU verifier, check the stored synthetic proof and run toy honest/tampered controls. Retain exact exit codes, verdict lines, IDs and coverage statements.
2. Implement reproducible SM120 support as an attributed patch over an immutable upstream pin, preserving compiler probes, arithmetic/protocol checks and verifier rules. Validate relevant device arithmetic and memory-resource adaptations.
3. Run the complete small synthetic model commitment -> inference/proof -> unmodified native CPU verification on RTX5060Ti16GB. Record and solve compatibility failures; do not substitute toy CPU proofs for a GPU inference result.
4. Execute independent synthetic commitments and multiple requests; measure setup, commit, proof, verification, proof size and memory separately. Add incorrect input, ID, output and proof controls and independently verify retained public artifacts.
5. Compare bounded configurations and supported optimization paths without weakening claims. Publish English full reproduction and limitations, replicated raw evidence, source/patch/build hashes, CPU CI and clear distinctions between tested C++ behavior and formal Lean claims.

## Evidence and completion gates

Original code is MIT licensed; upstream code and patches retain attribution and applicable licenses. Execute GPU timing campaigns sequentially on the available RTX 5060 Ti 16 GB. Keep independent generator seeds distinct from repeated timing samples. Preserve unsuccessful trials, negative findings, exact integer/proof checks, raw source/result hashes, compiler flags and hardware/software metadata. No energy claim without sampled measurements.

Completion requires all experiments above, executable CPU/GPU studies, independently recheckable retained evidence, derived tables, a detailed English README, METHODS.md, RESULTS.md and FINAL_REPORT.md. Public repository topics/homepage identify Requant Network. Latest published-head CPU/reference/artifact CI must pass. A documented negative experiment may complete a hypothesis test; a missing required experiment may not.

## Follow-up closure, 12 November 2026

The [follow-up report](FOLLOWUP_REPORT.md) records the disposition of the concrete next steps: new experiments, negative findings and measured resource limits. The earlier completed campaign remains available for historical comparison. Run `python verify_followups.py` for the added evidence checks.
