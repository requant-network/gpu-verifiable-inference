"""Check the actual patched histogram kernels against independent CPU counts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import cupy as cp
import numpy as np


def section(text, start, end):
    assert text.count(start) == 1 and text.count(end) == 1
    return text.split(start, 1)[1].split(end, 1)[0]


def main():
    assert __debug__, 'Assertions must stay enabled'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    parser.add_argument('--seed', type=int, default=20261109)
    parser.add_argument('--output', default='results/memory-validation.json')
    args = parser.parse_args()
    files = ['prover/hiding/count_keys16.cuh', 'prover/hiding/product_test.cuh',
             'prover/hash_commitment/hf_range_windows.cuh']
    texts = [(args.checkout / p).read_text() for p in files]
    count16 = '#if FLASH_SM120_MEMORY' + section(texts[0], '#if FLASH_SM120_MEMORY', '// Launches k_count_keys16();')
    hidk = 'template <int REP>' + section(texts[1], 'template <int REP>', '// The 8-to-1 fold after the three rounds')
    ranges = '__device__ __forceinline__ u32 key_of' + section(texts[2], '__device__ __forceinline__ u32 key_of', '// Subtracts the padding keys')
    source = '''#include <cuda_runtime.h>
#define FLASH_SM120_MEMORY 1
typedef unsigned int u32;
typedef unsigned short u16;
#define GSL(q,n) for (size_t q = (size_t)blockIdx.x * blockDim.x + threadIdx.x; q < (n); q += (size_t)gridDim.x * blockDim.x)
''' + count16 + hidk + ranges
    module = cp.RawModule(code=source, options=('--std=c++17',),
        name_expressions=('k_count_keys16', 'h_idk<1>', 'h_idk<8>', 'k_count'))
    kernels = {name: module.get_function(name) for name in ('k_count_keys16', 'h_idk<1>', 'h_idk<8>', 'k_count')}
    for kernel in kernels.values():
        kernel.max_dynamic_shared_size_bytes = 65536
    rng = np.random.default_rng(args.seed)
    cases = []

    def check(name, expected, actual, **parameters):
        actual = cp.asnumpy(actual)
        assert np.array_equal(expected, actual), (name, parameters, np.flatnonzero(expected != actual)[:8])
        cases.append(dict(kernel=name, **parameters, counters=actual.size, every_count_exact=True,
            output_sha256=hashlib.sha256(actual.tobytes()).hexdigest()))

    for nvb in (1, 257, 8193):
        for identities in (1, 3):
            for pattern in ('zero', 'boundaries', 'random'):
                shape = (identities, nvb * 8)
                if pattern == 'zero':
                    keys = np.zeros(shape, np.uint16)
                elif pattern == 'boundaries':
                    keys = np.resize(np.array([0, 16383, 16384, 32767, 32768, 49151, 49152, 65535], np.uint16), shape)
                else:
                    keys = rng.integers(0, 65536, shape, np.uint16)
                gpu_keys = cp.asarray(keys)
                for k, rep in ((16, 1), (15, 1), (14, 1), (10, 8), (8, 8)):
                    expected = np.stack([np.bincount(row.astype(np.int64) & ((1 << k) - 1), minlength=1 << k) for row in keys]).astype(np.uint32) + 7
                    actual = cp.full(expected.shape, 7, cp.uint32)
                    name = 'k_count_keys16' if k == 16 else f'h_idk<{rep}>'
                    bpi = 3
                    arguments = (gpu_keys, np.uint64(nvb), np.int32(bpi))
                    if k != 16:
                        arguments += (np.int32(k),)
                    kernels[name]((identities * bpi,), (512,), arguments + (actual,),
                        shared_mem=min(4 * (1 << min(k, 15)) * rep, 65536))
                    check(name, expected, actual, nvb=nvb, identities=identities, pattern=pattern, k=k, rep=rep)

    for iota in (0, 2, 4):
        for k in (0, 8, 14, 15):
            for pattern in ('boundaries', 'random'):
                size = 32776
                keys = (rng.integers(0, 65536, size, np.uint16) if pattern == 'random' else
                    np.resize(np.array([0, 1, 16383, 16384, 32767, 32768, 49152, 65535], np.uint16), size))
                identities = np.arange(size) & ((1 << iota) - 1)
                valid = keys.astype(np.uint32) < (1 << k)
                expected = np.bincount((identities[valid] << k) + keys[valid], minlength=1 << (iota + k)).astype(np.uint32) + 7
                actual = cp.full(expected.shape, 7, cp.uint32)
                lib = min(iota, max(0, 14 - k))
                bits = min(lib + k, 14)
                kernels['k_count']((3, 1 << (iota - lib), 1 << (lib + k - bits)), (512,),
                    (cp.asarray(keys), np.uint64(size // 8), np.int32(iota), np.int32(k), np.int32(lib), actual), shared_mem=4 << bits)
                check('k_count', expected, actual, iota=iota, k=k, lib=lib, pattern=pattern, key_count=size)

    cp.cuda.get_current_stream().synchronize()
    record = dict(utc=datetime.now(timezone.utc).isoformat(), seed=args.seed, cases=cases,
        outputs_checked=sum(c['counters'] for c in cases), generated_cuda_sha256=hashlib.sha256(source.encode()).hexdigest(),
        source_sha256={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['memory_validation.py', 'patches/sm120-memory.patch']},
        patched_sha256={p: hashlib.sha256((args.checkout / p).read_bytes()).hexdigest() for p in files},
        method='Compile verbatim kernel sections from the patched checkout. Independent NumPy integer bincount; nonzero initial counters; no tolerance.',
        shared_bytes_max=65536, performance_claim=False)
    Path(args.output).write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('PASS', len(cases), 'cases;', record['outputs_checked'], 'exact counters')


if __name__ == '__main__':
    main()
