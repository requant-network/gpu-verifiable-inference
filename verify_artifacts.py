"""Independently verify retained public GPU proofs and rejecting native controls on a CPU."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('checkout',type=Path)
    parser.add_argument('--output',default='results/public-proof-controls.json');args=parser.parse_args()
    verifier=args.checkout.resolve()/'bin/cp_verify';cases=[]
    records=[]
    for path in Path('results').glob('*.json'):
        value=json.loads(path.read_text())
        if value.get('accepted') and value.get('artifacts_sha256'):records.append((path,value))
    assert records,'No accepted public GPU proof has been retained'
    for path,value in records:
        source=Path(*Path(next(iter(value['artifacts_sha256']))).parts[:2])
        identifier=value['commitment_id']
        for name in ('honest','incorrect-id','altered-request','altered-output','altered-proof','truncated-proof','altered-key','altered-leaf'):
            with tempfile.TemporaryDirectory(prefix='requant-public-proof-') as temp:
                work=Path(temp)/'fixture';shutil.copytree(source,work)
                altered={'altered-request':'in/example.req','altered-output':'out/example.y','altered-proof':'out/example.proof',
                    'truncated-proof':'out/example.proof','altered-key':'ivk/key.bin','altered-leaf':'ivk/leaf/0.bin'}.get(name)
                if altered:
                    target=work/altered;data=bytearray(target.read_bytes());assert data
                    if name=='truncated-proof':data=data[:len(data)//2]
                    else:data[len(data)//2]^=1
                    target.write_bytes(data)
                supplied=('0' if identifier[0]!='0' else '1')+identifier[1:] if name=='incorrect-id' else identifier
                command=[str(verifier),str(work/'config'),str(work/'ivk'),str(work/'in/example.req'),str(work/'out/example.y'),str(work/'out/example.proof'),'-id',supplied]
                begin=time.perf_counter();run=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=240)
                elapsed=(time.perf_counter()-begin)*1000;lines=run.stdout.splitlines()
                accepted=run.returncode==0 and bool(lines) and lines[-1]=='YES'
                assert accepted==(name=='honest'),(path,name,run.returncode,run.stdout[-5000:])
                cases.append(dict(record=str(path),control=name,exit_code=run.returncode,last_line=lines[-1] if lines else '',accepted=accepted,
                    wall_ms=elapsed,output=run.stdout.replace(str(work),'PUBLIC_FIXTURE').replace(str(Path.home()),'HOME'),
                    command=['bin/cp_verify','PUBLIC_FIXTURE/config','PUBLIC_FIXTURE/ivk','PUBLIC_FIXTURE/in/example.req','PUBLIC_FIXTURE/out/example.y','PUBLIC_FIXTURE/out/example.proof','-id',supplied]))
        print('PASS accepted GPU proof and seven rejecting native controls:',source,flush=True)
    record=dict(utc=datetime.now(timezone.utc).isoformat(),cases=cases,proof_count=len(records),
        source_sha256={'verify_artifacts.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        verifier_sha256=hashlib.sha256(verifier.read_bytes()).hexdigest(),performance_claim=False,
        scope='Independent whole native CPU verifier calls on retained public GPU artifacts; accepting controls retain exact commitment, coverage, work and result-v1 lines. Altered public data only; no hiding or formal-verification conclusion.')
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
