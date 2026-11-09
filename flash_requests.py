"""Prove independent synthetic next-token requests under a previously accepted commitment."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import time


def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout',type=Path);parser.add_argument('work',type=Path)
    parser.add_argument('accepted_cycle',type=Path);parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--performance-claim',action='store_true')
    args=parser.parse_args();checkout=args.checkout.resolve();work=args.work.resolve()
    previous=json.loads(args.accepted_cycle.read_text());assert previous['accepted']
    commitment=previous['commitment_id'];assert len(commitment)==64
    build=checkout/'prover/build/hc';os.umask(0o077)
    folder=work/f'request-{args.seed}';folder.mkdir(mode=0o700)
    for name in ('in','home','tmp'):(folder/name).mkdir(mode=0o700)
    parameters=dict(line.split() for line in (work/'config/policy.txt').read_text().splitlines() if len(line.split())==2)
    T=1<<int(parameters['lt']);vocabulary=int(parameters['V']);rng=random.Random(args.seed)
    tokens=[rng.randrange(vocabulary) for _ in range(T)]
    # The native format is T token words followed by r and e, in little-endian order.
    request=folder/'in/example.req'
    with request.open('xb') as output:output.write(struct.pack('<'+'I'*(T+2),*tokens,T-1,T))
    environment=os.environ.copy();environment.update(HOME=str(folder/'home'),TMPDIR=str(folder/'tmp'))
    command=[str(build/'cp_prove'),'-isk',str(work/'isk'),'-in',str(folder/'in'),'-out',str(folder/'out')]
    begin=time.perf_counter()
    with (folder/'cp_prove.log').open('x') as output:
        prove=subprocess.run(command,env=environment,stdout=output,stderr=subprocess.STDOUT,timeout=1200)
    prove_ms=(time.perf_counter()-begin)*1000
    proof=folder/'out/example.proof';verify=None;verify_ms=None;verifier_text=''
    if prove.returncode==0 and proof.is_file():
        command=[str(build/'cp_verify'),str(work/'config'),str(work/'ivk'),str(request),str(folder/'out/example.y'),str(proof),'-id',commitment]
        begin=time.perf_counter();verify=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=240)
        verify_ms=(time.perf_counter()-begin)*1000;verifier_text=verify.stdout
        (folder/'cp_verify.log').write_text(verifier_text)
    accepted=verify is not None and verify.returncode==0 and verifier_text.splitlines()[-1]=='YES'
    record=dict(utc=datetime.now(timezone.utc).isoformat(),seed=args.seed,configuration=previous['configuration'],
        commitment_id=commitment,request_kind='independent synthetic prompt, next token only',r=T-1,e=T,T=T,
        accepted=accepted,prove_exit_code=prove.returncode,verify_exit_code=None if verify is None else verify.returncode,
        last_line=verifier_text.splitlines()[-1] if verifier_text.splitlines() else '',prove_wall_ms=prove_ms,verify_wall_ms=verify_ms,
        performance_claim=args.performance_claim,request_sha256=hashlib.sha256(request.read_bytes()).hexdigest(),
        source_sha256={'flash_requests.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        binary_sha256={p:hashlib.sha256((build/p).read_bytes()).hexdigest() for p in ('cp_prove','cp_verify')})
    if accepted:
        required=('covered:','commitment:','proof of work:','result-v1')
        record['verifier_metadata']={prefix:[line for line in verifier_text.splitlines() if line.startswith(prefix)] for prefix in required}
        assert all(record['verifier_metadata'].values())
        public=Path('artifacts')/(work.name+f'-request-{args.seed}');public.mkdir(parents=True)
        for name in ('config','ivk'):shutil.copytree(work/name,public/name)
        for name in ('in','out'):(public/name).mkdir()
        for name in ('in/example.req','out/example.y','out/example.proof'):shutil.copy2(folder/name,public/name)
        for name in ('cp_prove.log','cp_verify.log'):
            data=(folder/name).read_text().replace(str(work),'WORK').replace(str(checkout),'FLASH_PROVE').replace(str(Path.home()),'HOME')
            (public/name.replace('.log','.txt')).write_text(data,encoding='utf-8',newline='\n')
        record['artifacts_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in public.rglob('*') if p.is_file()}
        record['proof_bytes']=proof.stat().st_size
    else:
        record['limitation']='No rejected response, proof or proving log is exported; private diagnostics remain with the provider.'
    result=Path('results')/(work.name+f'-request-{args.seed}.json')
    result.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Request',args.seed,'accepted',accepted,'prove_ms',prove_ms,'verify_ms',verify_ms,flush=True)
    if not accepted:raise SystemExit(prove.returncode or (verify.returncode if verify else 1))


if __name__=='__main__':main()
