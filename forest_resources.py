"""Evaluate pinned fused-forest storage formulas against the observed SM120 limit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('upstream',type=Path);args=parser.parse_args()
    revision=subprocess.check_output(['git','-C',str(args.upstream),'rev-parse','HEAD'],text=True).strip()
    assert revision=='9e2bdd8ff5bf9c62f18263d7dac189b0400b260c'
    files={name:(args.upstream/'prover/hiding'/name).read_bytes() for name in ('forest_fused.cuh','forest_fused_first.cuh','forest_fused_second.cuh')}
    required={
        'forest_fused.cuh':('constexpr int COLS = 128;','constexpr int LD = COLS + 16;',
                            'RAW = 16 * COLS * 24, WEIGHTS = COLS * 40, DIGITS = 384 * LD;',
                            'STORED_BYTES = 2 * (size_t)(RAW + WEIGHTS + DIGITS);'),
        'forest_fused_first.cuh':('FIRST_WARPS = 16, FIRST_SUMS = 81;', 'FIRST_BYTES = FIRST_WARPS * (4096 + FIRST_SUMS * 24);'),
        'forest_fused_second.cuh':('ROWS_A = 8 * 3 * BYTES_LEFT, TILES_A = (ROWS_A + 15) / 16;',
                                   'PAIR = (16 * TILES_A + 32 * NW) * LD;',
                                   'PLANES = 54, NEAR = PLANES * 16 * 4;',
                                   'BYTES = 2 * (size_t)PAIR + 2 * 8 * (size_t)NEAR;')}
    for name,needles in required.items():
        text=files[name].decode('utf-8-sig')
        for needle in needles:assert needle in text,(name,needle)
    environment=Path('results/environment.json');limit=json.loads(environment.read_text())['shared_mem_optin_bytes']
    cases=[]
    for columns in (128,64,32):
        ld=columns+16
        stored=2*(16*columns*24+columns*40+384*ld)
        second=2*(16*14+32*5)*ld+2*8*(54*16*4)
        cases.append(dict(columns=columns,stored_bytes=stored,second_bytes=second,
                          stored_fits=stored<=limit,second_fits=second<=limit,
                          pinned_configuration=columns==128,interpretation='Pinned source storage formula' if columns==128 else 'Hypothetical storage only; not an implemented or correctness-qualified kernel'))
    assert cases[0]['stored_bytes']==219136 and cases[0]['second_bytes']==165888
    assert not cases[1]['second_fits'] and cases[2]['stored_fits'] and cases[2]['second_fits']
    record=dict(revision=revision,shared_memory_limit=limit,first_range_bytes=16*(4096+81*24),cases=cases,
                source_sha256={'forest_resources.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                result_sha256={environment.name:hashlib.sha256(environment.read_bytes()).hexdigest()},
                upstream_source_sha256={name:hashlib.sha256(data).hexdigest() for name,data in files.items()},
                scope='Source-derived resource qualification, no new GPU execution or performance claim. 128-column formulas are the pinned implementation;64/32-column formulas are hypothetical storage sensitivity only. A smaller width alone does not qualify algorithm indexing, arithmetic, pipeline synchronization or full proofs. Preserve the already-verified generic fallback.')
    Path('results/forest-resources.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Pinned stored/second kernels exceed SM120;32-column storage could fit, but requires new indexing/pipeline qualification')

if __name__=='__main__':main()
