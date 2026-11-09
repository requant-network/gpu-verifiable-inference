# Methods

A research project by [Requant Network](https://requant.network).

## Claim boundaries and source pin

The reference is Anthropic FlashProve revision `9e2bdd8ff5bf9c62f18263d7dac189b0400b260c`. The study evaluates the C++/CUDA programs on synthetic small-model configurations. It does not transfer Lean claims to those programs, establish weight hiding, independently prove the stated accounting assumptions, or demonstrate production-model throughput.

Every accepted proof is a complete native CPU verifier call under a retained commitment ID. Its exit status, exact last line, `covered:` statement, commitment assumptions, proof-of-work statement and `result-v1` line are retained together. Accounting bits are not presented as an independently established security level. Next-token-only requests and requests covering earlier model choices have different scopes and are labelled separately.

## Resource adaptations

The experimental build explicitly selects `sm_120a`; the default Hopper branch retains its original algorithms. Patches are attributed Apache-2.0 layers over the immutable pin. No protocol, field arithmetic, verifier acceptance rule, compiler arithmetic sample or secure-path check is removed.

Compact routed experts keep the original BM=128/BK=256 WMMA tile, use one shared buffer for each operand and sixteen token slots, and synchronize before reusing storage. Allocation includes the maximum of input and overlaid output footprints. This corrects an early draft that underestimated the output overlay and failed with an illegal address. The measured largest allocation is 82,944 bytes against a 101,376-byte device limit.

Range and lookup histograms partition public output-bin windows, rescan the input for each window, and merge counts into their original positions. The maximum allocation is 64 KiB, including support for the original 15-bit range tables and full 16-bit keys. The generic tiled engine uses two pipeline stages and 72 KiB. Byte-fold combination uses a 96 KiB cap and its existing exact fallback above it. Packed immutable tables can remain in global GPU memory; runtime occupancy replaces Hopper-specific launch estimates. Separate oversized lookup-forest fusion paths use their existing generic exact implementation; routed experts remain fused.

A complete compatibility run passed the earlier shared-memory fault but exposed an independent, unconditional 24 GiB engine reserve. The consumer-card layer reserves 4 GiB for the engine, retaining the separate 2 GiB driver allowance, allocation checks and native pool-peak reporting. This reserve requires empirical qualification on the small model and is not a universal memory-fit formula. Allocation failure remains a failing experiment.

## Independent device checks

Two expert cohorts each cover 384 cases: Q4/Q5 blocks, one through four signed-byte activation limbs, ragged routing, 1/17/33/65 tokens, rows 128/256, K 256/1024, zero/max/min/random activations and absent, power-of-two or fractional gains. The CPU decoder independently unpacks codes/scales and uses integer rational ties-to-even rounding. Every output is compared exactly. Coverage is limited to the tested bounded half-scale construction and gain values.

Histogram checks compile verbatim kernel sections from the patched checkout. Independent NumPy integer counts verify random and boundary keys, multiple identities, nonzero initial counters, masked lookup keys and range filtering. Each cohort checks 114 cases and 6,250,026 counters. Packed-table checks execute the verbatim initializer/accessors for all 65,536 entries at several block sizes. Their minimal shared-constant stub tests visibility and entry access, not field `quad()`; complete native proof verification remains necessary.

## Complete native cycles and requests

The cycle driver runs the original target-example script from the pinned checkout. Newly created research wrappers time the unchanged native `cp_commit`, `cp_prove` and `cp_verify` executables. The script creates a new private work directory under ancestors that other accounts cannot modify, commits to synthetic weights with independently drawn randomness, constructs the request, proves the response, and invokes the native CPU verifier.

The accepted commitment is retained before subsequent requests. Additional independently seeded synthetic prompts use `r=T-1, e=T`, so their proofs concern only the next token. They are not described as proving arbitrary earlier synthetic tokens were model choices. Multiple commitments and the exact-match/clipped-gap small configurations are kept distinct.

Only an accepted response permits export of public configuration, verification key, the request, `example.y` and `example.proof`. Output directories are not copied wholesale; hidden staging data and private proving keys are excluded. Rejected responses and private proving logs stay private. Accepted logs undergo a separate publication audit. Source, patch, generated binaries and accepted artifact hashes bind every result to its implementation.

## Controls and measurement

The unchanged CPU verifier first accepts the upstream stored synthetic proof and rejects an incorrect ID, changed request/output/proof and a truncated proof. Independently retained GPU proofs are subsequently rechecked from their public artifacts with whole native verifier calls. Additional controls alter the public key and leaf entry. These tests check bounded acceptance/rejection behavior, not adaptive soundness or hiding.

Commit, proof and verification host wall times are separate. Native engine-pool high-water marks and host RSS are distinguished from total GPU allocation. Single independent commitments are not treated as thirty repeated latency samples; raw per-commitment/request observations and their scope are reported. No clocks or power limits are changed, and no energy efficiency is inferred. Compatibility-only runs during compilation carry no comparative performance claim.

The measured toolchain is CUDA 13.3.73, a deviation from upstream's supported 13.2.86. The original build warning and by-value compiler sample remain active. CPU CI builds the pinned verifier and reruns public honest/altered controls. Hosted CPU CI cannot rerun SM120 kernels or establish CUDA implementation correctness. Full reproduction requires the recorded GPU, compiler, runtime, source pin, patch sequence and private-work-directory rules.
