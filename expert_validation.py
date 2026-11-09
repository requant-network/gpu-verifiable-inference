"""Validate compact routed experts against independent integer Q4/Q5 decoding."""
import argparse,ctypes,hashlib,itertools,json,pathlib
from datetime import datetime,timezone
import cupy as cp
import numpy as np

def decode(blocks,k,q5,gain_eighths):
    rows=blocks.shape[0];result=np.empty((rows,k),np.int64)
    for part in range(k//256):
        b=blocks[:,part];scales=b[:,4:16].astype(np.int64)
        for sub in range(8):
            if sub<4:scale=scales[:,sub]&63;minimum=scales[:,sub+4]&63
            else:scale=(scales[:,sub+4]&15)|((scales[:,sub-4]>>6)<<4);minimum=(scales[:,sub+4]>>4)|((scales[:,sub]>>6)<<4)
            offset=part*256+sub*32
            for byte in range(32):
                packed=b[:,(48 if q5 else 16)+32*(sub//2)+byte]
                code=(packed>>(4*(sub%2)))&15
                if q5:code=code|(((b[:,16+byte]>>sub)&1)<<4)
                numerator=gain_eighths[offset+byte]*(2*scale*code.astype(np.int64)-minimum)
                quotient,remainder=np.divmod(numerator,4)
                result[:,offset+byte]=quotient+((remainder>2)|((remainder==2)&((quotient&1)!=0)))
    return result

def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--seed',type=int,default=20261109)
    parser.add_argument('--output',default='results/expert-validation.json');args=parser.parse_args()
    library=ctypes.CDLL(str(pathlib.Path('build/libexpert.so').resolve()));ptr=ctypes.c_void_p
    library.rq_expert_run.argtypes=[ctypes.c_int]*7+[ptr]*8;library.rq_expert_run.restype=ctypes.c_int
    library.rq_expert_shared.argtypes=[ctypes.c_int]*2;library.rq_expert_shared.restype=ctypes.c_int
    library.rq_expert_error.restype=ctypes.c_char_p
    rng=np.random.default_rng(args.seed);cases=[];limit=cp.cuda.runtime.deviceGetAttribute(97,0)
    for index,(nl,q5,gains,T,pattern) in enumerate(itertools.product(range(1,5),(0,1),(None,'power2','fractional'),(1,17,33,65),('zero','maximum','minimum','random'))):
        rows=256 if index%7==0 else 128;k=1024 if index%3==0 else 256;ne=2;slots=T+64*ne
        raw=rng.integers(0,256,(ne,rows,k//256,176 if q5 else 144),np.uint8)
        raw[:,:,:,0]=0;raw[:,:,:,1]=0x2c;raw[:,:,:,2]=0;raw[:,:,:,3]=0x28
        if pattern=='random':planes=rng.integers(-128,128,(nl,slots,k),np.int8)
        else:planes=np.full((nl,slots,k),{'zero':0,'maximum':127,'minimum':-128}[pattern],np.int8)
        gain_eighths=np.resize(np.array([4,8,16] if gains=='power2' else [1,3,5,9],np.int64),k) if gains else np.full(k,8,np.int64)
        counts=np.array([T//3,T-T//3],np.int32);sbase=np.array([0,(int(counts[0])+63)//64*64],np.int32);rbase=np.array([0,counts[0]],np.int32)
        expected=np.zeros((rows,T),np.int64);values=np.zeros((slots,k),np.int64)
        for l in range(nl-1,-1,-1):values=values*256+planes[l].astype(np.int64)
        for e in range(ne):
            c=int(counts[e]);start=int(sbase[e]);r=int(rbase[e]);weights=decode(raw[e],k,q5,gain_eighths)
            assert np.abs(weights).max()<32768
            expected[:,r:r+c]=weights@values[start:start+c].T
        d_raw,d_planes,d_counts,d_slots,d_ranks=map(cp.asarray,(raw,planes,counts,sbase,rbase));out=cp.zeros((rows,T),cp.int64)
        dg=cp.asarray((gain_eighths/8).astype(np.float32)) if gains else None
        print('case',index,nl,q5,gains,T,rows,k,pattern,flush=True)
        status=library.rq_expert_run(nl,rows,k,T,ne,slots,q5,d_raw.data.ptr,0 if dg is None else dg.data.ptr,d_planes.data.ptr,d_counts.data.ptr,d_slots.data.ptr,d_ranks.data.ptr,out.data.ptr,cp.cuda.get_current_stream().ptr)
        assert status==0,library.rq_expert_error()
        cp.cuda.get_current_stream().synchronize();actual=cp.asnumpy(out);assert np.array_equal(actual,expected),(nl,q5,gains,T,pattern)
        shared=library.rq_expert_shared(nl,16);assert shared<=limit
        cases.append(dict(limbs=nl,q5=bool(q5),gains=gains,tokens=T,rows=rows,k=k,pattern=pattern,tile_slots=16,shared_bytes=shared,
            outputs=actual.size,every_integer_exact=True,input_sha256=hashlib.sha256(raw.tobytes()+planes.tobytes()+gain_eighths.tobytes()).hexdigest(),
            output_sha256=hashlib.sha256(actual.tobytes()).hexdigest()))
    source=['expert_validation.py','native/expert_bridge.cu','patches/sm120-compact.patch']
    record=dict(utc=datetime.now(timezone.utc).isoformat(),seed=args.seed,cases=cases,shared_memory_limit=limit,
        source_sha256={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in source},
        binary_sha256=hashlib.sha256(pathlib.Path('build/libexpert.so').read_bytes()).hexdigest(),
        scope='Compact fused GPU kernel, same BM128/BK256 and original WMMA; one shared tile per operand, sixteen token slots. Independent CPU integer Q4/Q5 decoding and rational ties-to-even rounding for bounded half scales and gains in eighths, every output compared. Correctness campaign only; no latency claim.')
    pathlib.Path(args.output).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(len(cases),'compact fused cases;',sum(c['outputs'] for c in cases),'exact outputs; largest shared allocation',max(c['shared_bytes'] for c in cases),'of',limit)

if __name__=='__main__':main()
