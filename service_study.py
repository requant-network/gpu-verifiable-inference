"""Qualified request batching and exact memory policies under an existing commitment."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import signal
import struct
import subprocess
import threading
import time


def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout',type=Path);parser.add_argument('work',type=Path);parser.add_argument('accepted_cycle',type=Path)
    parser.add_argument('--seed',type=int,default=20261112);parser.add_argument('--output',default='results/service-study.json')
    parser.add_argument('--quick',action='store_true');args=parser.parse_args()
    checkout,work=args.checkout.resolve(),args.work.resolve();previous=json.loads(args.accepted_cycle.read_text())
    assert previous['accepted'] and previous['configuration']=='target_small_f2_roomy'
    identifier=previous['commitment_id'];build=checkout/'prover/build/hc'
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()=='9e2bdd8ff5bf9c62f18263d7dac189b0400b260c'
    parameters=dict(line.split() for line in (work/'config/policy.txt').read_text().splitlines() if len(line.split())==2)
    T=1<<int(parameters['lt']);vocabulary=int(parameters['V']);os.umask(0o077)
    root=work/f'service-{args.seed}';root.mkdir(mode=0o700)
    profiles=[dict(name='single',batch=1,step=1,memory=None),dict(name='batch2',batch=2,step=2,memory=None),
              dict(name='batch4',batch=4,step=4,memory=None),
              dict(name='recompute5',batch=1,step=1,memory='layer-rebuilt=5,attention-rebuilt=5,head-rebuilt=5,tail-rebuilt=5')]
    warmups,repetitions=(0,1) if args.quick else (5,30)
    cases={p['name']:dict(**p,observations=[],samples_ms=[],public_example=None,disabled=False) for p in profiles}
    for iteration in range(warmups+repetitions):
        names=list(cases)
        if iteration%2:names.reverse()
        rng=random.Random(args.seed+1009*iteration)
        prompts=[[rng.randrange(vocabulary) for _ in range(T)] for _ in range(4)]
        for name in names:
            case=cases[name]
            if case['disabled']:continue
            folder=root/f'{name}-{iteration:03d}';folder.mkdir(mode=0o700)
            for sub in ('in','home','tmp'):(folder/sub).mkdir(mode=0o700)
            for index,tokens in enumerate(prompts[:case['batch']]):
                (folder/'in'/f'item-{index}.req').write_bytes(struct.pack('<'+'I'*(T+2),*tokens,T-1,T))
            env=os.environ.copy();env.update(HOME=str(folder/'home'),TMPDIR=str(folder/'tmp'),CUDA_DEVICE_ORDER='PCI_BUS_ID',CUDA_VISIBLE_DEVICES='0')
            command=[str(build/'cp_prove'),'-isk',str(work/'isk'),'-in',str(folder/'in'),'-out',str(folder/'out'),'-in-step',str(case['step'])]
            if case['memory']:command+=['-memory',case['memory']]
            # The first observation is a resource probe; timed observations have no telemetry process.
            samples=[];stop=threading.Event()
            def monitor():
                while not stop.is_set():
                    run=subprocess.run(['nvidia-smi','-i','0','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],capture_output=True,text=True)
                    total=0;seen=False
                    for line in run.stdout.splitlines():
                        fields=line.split(',')
                        if len(fields)==2 and fields[1].strip().isdigit():total+=int(fields[1]);seen=True
                    if seen:samples.append(dict(seconds=time.monotonic(),process_memory_mib=total))
                    stop.wait(.1)
            telemetry=threading.Thread(target=monitor,daemon=True) if iteration==0 else None
            if telemetry:telemetry.start()
            start=time.perf_counter()
            try:
                with (folder/'cp_prove.log').open('x') as output:
                    process=subprocess.Popen(command,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                    try:code=process.wait(timeout=600)
                    except subprocess.TimeoutExpired:
                        assert os.getpgid(process.pid)==process.pid
                        os.killpg(process.pid,signal.SIGKILL);process.wait();code=124
                elapsed=(time.perf_counter()-start)*1000
            except subprocess.TimeoutExpired:
                elapsed=(time.perf_counter()-start)*1000;code=124
            finally:
                stop.set()
                if telemetry:telemetry.join()
            log_lines=(folder/'cp_prove.log').read_text(errors='replace').splitlines()
            prove_last_line=log_lines[-1] if log_lines else ''
            prove_last_line=prove_last_line.replace(str(work),'WORK').replace(str(checkout),'FLASH_PROVE').replace(str(Path.home()),'HOME')
            verdicts=[];accepted=code==0
            for index in range(case['batch']):
                request=folder/'in'/f'item-{index}.req';out=folder/'out'/f'item-{index}'
                proof=out.with_suffix('.proof');token=out.with_suffix('.y')
                if code!=0 or not proof.is_file() or not token.is_file():accepted=False;continue
                call=[str(build/'cp_verify'),str(work/'config'),str(work/'ivk'),str(request),str(token),str(proof),'-id',identifier]
                begin=time.perf_counter();verify=subprocess.run(call,capture_output=True,text=True,timeout=240)
                verify_ms=(time.perf_counter()-begin)*1000;lines=verify.stdout.splitlines()
                ok=verify.returncode==0 and bool(lines) and lines[-1]=='YES';accepted &= ok
                metadata={prefix:[line for line in lines if line.startswith(prefix)] for prefix in ('covered:','commitment:','proof of work:','result-v1')}
                if ok:assert all(metadata.values())
                verdicts.append(dict(index=index,accepted=ok,exit_code=verify.returncode,last_line=lines[-1] if lines else '',
                                     verify_wall_ms=verify_ms,verifier_metadata=metadata if ok else {},
                                     request_sha256=hashlib.sha256(request.read_bytes()).hexdigest(),
                                     output_sha256=hashlib.sha256(token.read_bytes()).hexdigest() if ok else None,
                                     proof_sha256=hashlib.sha256(proof.read_bytes()).hexdigest() if ok else None,
                                     proof_bytes=proof.stat().st_size if ok else None))
            observation=dict(iteration=iteration,prove_exit_code=code,prove_last_line=prove_last_line,accepted=accepted,prove_wall_ms=elapsed,
                             verdicts=verdicts,telemetry_samples=len(samples),
                             observed_gpu_process_peak_mib=max((v['process_memory_mib'] for v in samples),default=None))
            case['observations'].append(observation)
            if not accepted:case['disabled']=True
            elif iteration>=warmups:case['samples_ms'].append(elapsed)
            if accepted and iteration==warmups:
                public=Path('artifacts')/f'service-{args.seed}-{name}';public.mkdir(parents=True)
                for sub in ('config','ivk'):shutil.copytree(work/sub,public/sub)
                for sub in ('in','out'):(public/sub).mkdir()
                for source,destination in ((folder/'in/item-0.req',public/'in/example.req'),(folder/'out/item-0.y',public/'out/example.y'),(folder/'out/item-0.proof',public/'out/example.proof')):shutil.copy2(source,destination)
                evidence=dict(accepted=True,configuration=previous['configuration'],commitment_id=identifier,
                              verifier_metadata=verdicts[0]['verifier_metadata'],performance_claim=False,
                              artifacts_sha256={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in public.rglob('*') if p.is_file()},
                              scope='First timed observation, first request of the declared batch. All requests of all observations checked by native CPU verifier; only this representative artifact is public.')
                example=Path('results')/f'service-example-{args.seed}-{name}.json';example.write_text(json.dumps(evidence,indent=2)+'\n');case['public_example']=example.as_posix()
            record=dict(utc=datetime.now(timezone.utc).isoformat(),seed=args.seed,warmups=warmups,samples=repetitions,
                        configuration=previous['configuration'],commitment_id=identifier,cases=list(cases.values()),
                        source_sha256={'service_study.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                        binary_sha256={name:hashlib.sha256((build/name).read_bytes()).hexdigest() for name in ('cp_prove','cp_verify')},
                        reference_record_sha256=hashlib.sha256(args.accepted_cycle.read_bytes()).hexdigest(),
                        scope='Same pre-existing synthetic commitment, native one-batch interface and supported in-step/memory options. Fresh seeded prompts, next token only. Batch wall includes process/model setup and proof generation; verification costs separately retained. Fixed5warm/30 observations for successful configurations; first resource failure stops that configuration and remains retained. First observation samples GPU0 compute-process allocations at nominal100ms; observed NVML peak is not an exact instantaneous whole-device peak. Telemetry excluded from timed observations. No failed response/proof or full private log is published, no guard or verifier was weakened.')
            Path(args.output).write_text(json.dumps(record,indent=2)+'\n')
            print(args.seed,iteration,name,'accepted',accepted,'prove_ms',round(elapsed,2),flush=True)


if __name__=='__main__':main()
