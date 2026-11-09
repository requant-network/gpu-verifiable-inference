"""Check the verbatim patched packed-table initializer and entry accessors on GPU."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import cupy as cp
import numpy as np


def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('checkout',type=Path)
    parser.add_argument('--seed',type=int,default=20261109);parser.add_argument('--output',default='results/packed-validation.json')
    args=parser.parse_args();relative='prover/hiding/forest_keys.cuh'
    text=(args.checkout/relative).read_text();start='template <> struct Form<PackedSrc>'
    assert text.count(start)==1
    form=start+text.split(start,1)[1].split('// Any other table (GENERAL)',1)[0]
    source='''#include <cuda_runtime.h>
#define FLASH_SM120_MEMORY 1
typedef unsigned char u8;typedef unsigned int u32;typedef unsigned long long u64;typedef unsigned short uint16_t;
typedef u64 T;constexpr int POWERS_BYTES=256;
struct PackedSrc{const unsigned short* ctab;};template<class S>struct Form;
template<class Derived>struct ByValues{
  __device__ void set_powers(const T& a,void* sh){if(threadIdx.x==0)((u64*)sh)[0]=a;}
};
''' + form + '''
extern "C" __global__ void probe(const unsigned short* table,u64* values,u32* bytes,u64* ready){
 extern __shared__ unsigned char room[];
 Form<PackedSrc> f;f.init(PackedSrc{table},0x123456789abcdef0ULL,room);
 for(int k=blockIdx.x*blockDim.x+threadIdx.x;k<65536;k+=gridDim.x*blockDim.x){
   values[k]=f.value(k);bytes[k]=f.bytes0(k);ready[k]=((u64*)room)[0];
 }
}
'''
    kernel=cp.RawKernel(source,'probe',options=('--std=c++17',));rng=np.random.default_rng(args.seed);cases=[]
    for pattern in ('zero','maximum','random'):
        table=(np.zeros(65536,np.uint16) if pattern=='zero' else np.full(65536,65535,np.uint16) if pattern=='maximum' else rng.integers(0,65536,65536,np.uint16))
        expected=np.arange(65536,dtype=np.uint64)+(table.astype(np.uint64)<<28)
        expected_bytes=np.arange(65536,dtype=np.uint32)|(table.astype(np.uint32)<<16)
        for threads in (32,256,512):
            values=cp.empty(65536,cp.uint64);bytes_=cp.empty(65536,cp.uint32);ready=cp.empty(65536,cp.uint64)
            kernel((7,),(threads,),(cp.asarray(table),values,bytes_,ready),shared_mem=256)
            assert np.array_equal(cp.asnumpy(values),expected)
            assert np.array_equal(cp.asnumpy(bytes_),expected_bytes)
            assert np.all(cp.asnumpy(ready)==0x123456789abcdef0)
            cases.append(dict(pattern=pattern,threads=threads,exact_entries=65536,shared_bytes=256,
                output_sha256=hashlib.sha256(cp.asnumpy(values).tobytes()+cp.asnumpy(bytes_).tobytes()).hexdigest()))
    record=dict(utc=datetime.now(timezone.utc).isoformat(),seed=args.seed,cases=cases,
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['packed_validation.py','patches/sm120-tables.patch']},
        patched_sha256={relative:hashlib.sha256((args.checkout/relative).read_bytes()).hexdigest()},
        generated_cuda_sha256=hashlib.sha256(source.encode()).hexdigest(),performance_claim=False,
        scope='Verbatim Form<PackedSrc> initialization and value/bytes accessors, all 65536 public table entries. Minimal ByValues stub only checks visibility of shared constants; it does not test field quad() or the complete forest. Native full-proof verification remains required.')
    Path(args.output).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('PASS',len(cases),'packed-table cases;',sum(c['exact_entries'] for c in cases),'exact entries')


if __name__=='__main__':main()
