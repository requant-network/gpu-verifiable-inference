# Service, memory and scale qualification

Requant Network, 12 November 2026. This supplement closes the concrete batching/reuse and resource-qualification questions in the [historical report](FINAL_REPORT.md). It uses synthetic weights and the already accepted commitment; the native CPU verifier, compiler sample, arithmetic checks and resource guards remain intact.

## Repeated native batch interface

The four profiles are one request, a batch of two (`-in-step 2`), a batch of four (`-in-step 4`), and one request with all four documented forest rebuild levels set to five. All use the same commitment and fresh seeded prompts; profiles share their first prompt within an iteration and their order alternates. There are five warm-ups and thirty measured observations per successful profile in each of two seeded cohorts. The model commitment is reused, while each timed call still starts a process and loads its model/key state. This tests native request batching, not a persistent resident server.

The complete generation wall includes process startup, model/key loading and proof generation. CPU verification of **every request** is recorded separately. All service proofs cover `r=63 e=64 T=64`, `tokens=none`, `y=yes`, `next-token=yes`, under the declared exact-match acceptance policy; they do not certify that earlier prompt tokens were the model's choices. Each accepted native verifier returns exit code 0 with entire last line `YES`. Its coverage, commitment assumptions, work and `result-v1` lines are retained per request, rather than reduced to a stronger security label.

The caller-supplied commitment ID is `4f351f1f2123409da095d4df1140fcd39a06719d9061163cb62c6719ad2f1943`, taken from our own original commitment operation. The existing C++/CUDA implementation has not thereby become a formally proved implementation; the upstream commitment assumptions and proof-of-work accounting remain part of each native acceptance statement.

| Seed | Profile | Requests per batch | Generation median, ms | p95, ms | Median per request, ms | First-probe observed GPU MiB |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 20261112 | single | 1 | 3223.02 | 3827.32 | 3223.02 | 4608 |
| 20261112 | batch2 | 2 | 4075.59 | 4679.53 | 2037.79 | 4676 |
| 20261112 | batch4 | 4 | 5607.81 | 6077.28 | 1401.95 | 4850 |
| 20261112 | recompute5 | 1 | 3249.89 | 3825.11 | 3249.89 | 4608 |
| 20261212 | single | 1 | 3279.34 | 3979.83 | 3279.34 | 4608 |
| 20261212 | batch2 | 2 | 4052.92 | 4483.80 | 2026.46 | 4676 |
| 20261212 | batch4 | 4 | 5532.21 | 6085.45 | 1383.05 | 4850 |
| 20261212 | recompute5 | 1 | 3303.72 | 3576.62 | 3303.72 | 4608 |

All 560 per-request proofs across the two cohorts were accepted by the native CPU verifier.

Batching amortizes the process/model setup. The separate rebuild-five profile gives no material memory reduction at this small workload, so the data do not support changing its default memory policy on that basis. This observation does not predict a production model's throughput or general latency distribution.

## Observed memory and full-size gate

The first warm-up of each profile samples GPU0 compute-process allocation through NVML at nominal 100 ms intervals. These probes are excluded from measured observations. This is an **observed sampled process allocation peak**, not a true instantaneous whole-device memory peak. Native pool counters and sampled allocations describe different boundaries. The production frontend scrubs profiling environment on re-execution; its hardening was preserved instead of changing it to force a profiler through.

The actual unchanged target script was also invoked for `target_full_f2` in a fresh work directory. It returned **exit code 2 before any GPU phase**: its full configuration requires at least 280 GB available host memory; about 59 GB was available. Nothing was created. The [raw resource-gate result](results/full-resource-gate.json) retains the entire last line and script output. This is a measured host-memory gate, not evidence that the full model fits or fails solely because the GPU has 16 GB. Running past the guard would endanger unrelated server processes and would not be a valid resource-qualified experiment.

## Forest fusion decision

[Source-derived resource qualification](results/forest-resources.json) checks the pinned storage formulas against the observed 101,376-byte per-block opt-in limit. The original stored and second-pass fused kernels require 219,136 and 165,888 bytes. Hypothetical 64-column tiles still require 115,712/116,736 bytes and do not fit. At 32 columns the storage formulas give 64,000/92,160 bytes, but that is **not an implemented or qualified kernel**: the source also fixes warp K-splitting, four-entry lane work and asynchronous copy subdivisions for its original tile. Changing only the width could produce missing arithmetic or out-of-bounds accesses.

Retain the complete-proof-verified generic fallback. The 32-column budget identifies a possible separate kernel redesign; it does not justify enabling that unimplemented path or claiming its speed. The operational compatibility question is resolved by accepted native proofs with the fallback. Production weights and a newly redesigned fused forest are outside these measured results.

## Evidence and reproduction

[service_study.py](service_study.py) defines all profiles, fresh requests, timing boundaries and fail-stop limits. Invoke it with the pinned patched checkout, private synthetic work directory and `results/consumer-cycle1.json`, then repeat with `--seed 20261212 --output results/service-replication.json`. Use fresh seed-specific work directories. Public [service examples](results/service-example-20261112-single.json) contain only accepted public configuration, verifier key, request, output and proof. No private proving key or failed response/proof is exported.

[The unchanged public-artifact replayer](verify_artifacts.py) checked each of the eight full-cohort examples and seven altered controls per example: all eight honest examples accepted and all 56 altered controls rejected in [64 fresh native calls](results/service-proof-controls.json). [verify_followups.py](verify_followups.py) checks every new source/artifact binding, the original binary/commitment reference, all per-request native verdicts, controls and the [derived median/p95 table](results/followup-summary.csv). Hosted CPU CI independently rebuilds the pinned verifier and repeats public-proof controls. CI does not rerun GPU timings.

The completed service decision is to use the supported batch interface when requests can be grouped, retain the qualified fallback and avoid extrapolating the small model to the gated full configuration. Formal security, hiding, arbitrary production weights and heterogeneous multi-GPU operation are not established by native acceptance here.

## Server timing boundary

GPU campaigns run serially on the same RTX 5060 Ti. Clocks, power limits and unrelated server services are unchanged. Measurements describe this server and retained workload; small percentage differences are not treated as universal improvements. No energy measurement or heterogeneous multi-GPU throughput is inferred.
