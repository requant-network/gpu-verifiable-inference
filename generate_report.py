"""Generate final bounded SM120 port findings from accepted public native proofs."""
import csv,hashlib,json,pathlib,re

root=pathlib.Path('.')
records=[]
for path in sorted((root/'results').glob('consumer-*.json')):
    value=json.loads(path.read_text())
    if value.get('accepted') and value.get('artifacts_sha256'):records.append((path,value))
assert len(records)==5 and len({v['commitment_id'] for p,v in records})==3
records.sort(key=lambda item: ('phases' not in item[1],item[0].as_posix()))
controls=json.loads((root/'results/public-proof-controls.json').read_text())
assert controls['proof_count']==5 and len(controls['cases'])==40
assert sum(c['accepted'] for c in controls['cases'])==5
assert all(c['accepted']==(c['control']=='honest') for c in controls['cases'])
rows=[]
for path,value in records:
    metadata=value['verifier_metadata'];assert all(metadata[k] for k in ('covered:','commitment:','proof of work:','result-v1'))
    words=dict(word.split('=',1) for word in metadata['result-v1'][0].split() if '=' in word)
    assert words['status']=='0' and words['id']==value['commitment_id']
    phases={v['program']:v for v in value.get('phases',[])}
    public=pathlib.Path(*pathlib.Path(next(iter(value['artifacts_sha256']))).parts[:2])
    native_peak=[]
    if (public/'cp_commit.txt').exists():
        native_peak=[int(v) for v in re.findall(r"engine's memory pool held (\d+)",(public/'cp_commit.txt').read_text())]
    rows.append(dict(record=path.as_posix(),configuration=value['configuration'],commitment_id=value['commitment_id'],
        request_seed=value.get('seed',''),r=int(words['r']),e=int(words['e']),T=int(words['T']),claim=words['claim'],
        commitment_wall_ms=phases.get('cp_commit',{}).get('wall_ms',''),
        proving_wall_ms=phases.get('cp_prove',{}).get('wall_ms',value.get('prove_wall_ms')),
        verification_wall_ms=phases.get('cp_verify',{}).get('wall_ms',value.get('verify_wall_ms')),
        proof_bytes=value['proof_bytes'],peak_host_rss_kib=max((v['peak_host_rss_kib'] for v in phases.values()),default=''),
        key_engine_pool_peak_bytes=max(native_peak,default='')))
with (root/'results/proofs-summary.csv').open('w',encoding='utf-8',newline='') as out:
    writer=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
table=['| Configuration / request | Commit, s | Prove, s | Verify, s | Proof bytes | Coverage r..e |','|---|---:|---:|---:|---:|---|']
for row in rows:
    name=row['configuration'].replace('target_small_f2_','')
    if row['request_seed']!='':name+=' / prompt '+str(row['request_seed'])
    commit=f"{row['commitment_wall_ms']/1000:.3f}" if row['commitment_wall_ms']!='' else 'reused'
    table.append(f"| {name} | {commit} | {row['proving_wall_ms']/1000:.3f} | {row['verification_wall_ms']/1000:.3f} | {row['proof_bytes']:,} | {row['r']}..{row['e']} |")
table='\n'.join(table)
results=f'''# Results

A research project by [Requant Network](https://requant.network).

## Complete native execution on consumer Blackwell

Five new GPU proofs are accepted by the original native CPU verifier, with exit status 0 and exact last line `YES`. They cover three independently randomized commitments, two small-model policy configurations and two additional independently seeded prompts. The synthetic weight construction is controlled; these are not three independently trained models.

Every accepted proof retains its ID, full native coverage statement, commitment assumptions, proof-of-work line and `result-v1`. Public configuration, verification key, request, response and proof are retained under [artifacts](artifacts). Proving keys, hidden staging data and rejected responses are excluded.

{table}

These are standalone-process observations, not a thirty-sample fixed-input latency distribution. Commitment randomness and proof-of-work can affect runtime. The table permits a bounded compatibility comparison of both policies; it does not establish a statistically reliable performance ranking between them. Detailed values, IDs, memory fields and source-record links are in [proofs-summary.csv](results/proofs-summary.csv).

The two added prompts use r=63/e=64, so their proofs cover the next response token only. The configuration's original request has r=60/e=64, with its own detailed token coverage. Acceptance is always interpreted under the original policy and accounting statements rather than as an unqualified claim about every token in the prompt.

## Independent native controls

The retained public GPU artifacts are each checked by a separate whole native CPU verifier call. All five honest calls accept. All 35 altered calls reject: incorrect ID, changed request, changed response, changed proof, truncated proof, changed public key and changed leaf entry for each proof. The [raw control record](results/public-proof-controls.json) retains complete commands, exit codes, verdict lines and accepting metadata. A separate stored upstream proof also accepts, with five altered controls rejected.

Hosted CPU CI rebuilds the pinned verifier and rechecks the public GPU artifacts from their committed files. It does not run the CUDA prover or establish implementation-level formal correctness. Native acceptance retains the verifier's external assumptions and does not establish weight hiding.

## Device arithmetic and shared memory

Two expert input cohorts each contain 384 cases. All 3,258,112 output entries match the independent integer decoder with rational ties-to-even rounding. The largest configured dynamic allocation is 82,944 bytes, or 81 KiB, against the measured 101,376-byte opt-in limit. The compact path remains a fused WMMA expert kernel.

Two histogram cohorts each contain 114 cases, checking 12,500,052 exact counters in total, including nonzero initial counts, all 16-bit key windows and the original 15-bit range-table support. Dynamic histogram storage is at most 64 KiB. Packed-table initializer/accessor checks cover 1,179,648 entries across two cohorts; their minimal constant-visibility stub does not substitute for complete field arithmetic. Complete native acceptance provides the separate end-to-end check.

![Source-derived dynamic shared-memory footprints](figures/shared-memory.png)

The figure is a memory-budget comparison, not a speedup plot. The original largest expert source footprint is 226.5 KiB; the compact footprint includes its output overlay. The tiled engine's configured budget falls from 108 to 72 KiB. Separate oversized forest-fusion paths use their existing exact generic implementation.

## Global memory qualification and failed baselines

An architecture flag plus the cuBLAS expert fallback builds but fails at an unconditional 128 KiB histogram opt-in. The memory-corrected version passes that point and then fails because of an unconditional 24 GiB engine reserve. Both failures remain documented. The consumer layer reserves 4 GiB for the engine while keeping the separate 2 GiB driver allowance, allocation checks and native pool-peak reporting.

The accepted runs qualify this reserve for the tested small configurations. The first key-generation engine-pool peak is 603,979,776 bytes, or 576 MiB; its entry-generation engine-pool peak is 301,989,888 bytes. Those are native pool high-water marks, not a measurement of total GPU peak allocation. Host RSS and slab sizes are separately retained in the logs and CSV.

The first compact draft also underestimated its WMMA output overlay. Its historical patch and independent footprint diagnostic remain in [compatibility-baselines.json](results/compatibility-baselines.json). The complete raw failed expert campaign and its earlier driver were not retained publicly; no timing or accuracy result is claimed from that draft. The corrected final tests and complete accepted cycles have full source bindings.

## Provenance and limits

The source pin is `9e2bdd8ff5bf9c62f18263d7dac189b0400b260c`. All four port layers retain Apache-2.0 attribution. Native CUDA is 13.3.73, a deviation from upstream's supported 13.2.86; the warning and 324-value compiler arithmetic sample remain active. Every native program runs as an ordinary user with the original private-path and allocation checks.

This is a bounded small-synthetic-model port. Larger models, arbitrary weight distributions, formal CUDA verification, hiding, adaptive attacks, service throughput and energy are unmeasured. See [Methods](METHODS.md), [related work](RELATED_WORK.md), [final conclusions](FINAL_REPORT.md), the [environment](results/environment.json) and the complete [protocol](RESEARCH.md).
'''
final='''# Final report

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
'''
final += '\n## Follow-up closure, 12 November 2026\n\nThe [follow-up report](FOLLOWUP_REPORT.md) resolves the concrete priorities above with additional experiments, resource gates and updated conclusions. Its findings supersede the open-work wording in this historical campaign.\n'
(root/'RESULTS.md').write_text(results,encoding='utf-8',newline='\n');(root/'FINAL_REPORT.md').write_text(final,encoding='utf-8',newline='\n')
record=dict(source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ['generate_report.py','plot_memory.py']},
    artifacts_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ['RESULTS.md','FINAL_REPORT.md','results/proofs-summary.csv','figures/shared-memory.png','figures/shared-memory.svg']},
    accepted_proofs=5,independent_commitments=3,whole_native_public_verifier_calls=40)
(root/'results/report-provenance.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Generated accepted-proof tables and final SM120 port findings')
