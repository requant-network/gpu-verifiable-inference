"""Run the original target-example script, profile native programs, retain accepted public evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout',type=Path)
    parser.add_argument('work',type=Path)
    parser.add_argument('--configuration',default='target_small_f2_roomy')
    parser.add_argument('--output',default='results/flash-cycle.json')
    parser.add_argument('--performance-claim',action='store_true')
    args=parser.parse_args();checkout=args.checkout.resolve();work=args.work.resolve()
    assert not work.exists(), 'The upstream script must create a new private work directory'
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()=='9e2bdd8ff5bf9c62f18263d7dac189b0400b260c'
    native=checkout/'prover/build/hc'
    assert all((native/p).is_file() for p in ('cp_commit','cp_prove','cp_verify'))
    os.umask(0o077)
    tools=checkout/('requant-profile-'+work.name);tools.mkdir(mode=0o700)
    phases=Path('build')/('phases-'+work.name+'.jsonl');phases.parent.mkdir(exist_ok=True)
    assert not phases.exists()
    profiler=Path('profile_tool.py').resolve()
    for name in ('cp_commit','cp_prove','cp_verify'):
        wrapper=tools/name
        script='#!/usr/bin/python3\nimport runpy,sys\nsys.argv.insert(1,'+repr(str(native/name))+')\nrunpy.run_path('+repr(str(profiler))+',run_name="__main__")\n'
        with wrapper.open('x',encoding='utf-8',newline='\n') as output:output.write(script)
        wrapper.chmod(0o700)  # New research wrapper only; never alters upstream directory permissions.
    environment=os.environ.copy();environment.update(BUILD=str(tools),REQUANT_PHASE_RECORD=str(phases.resolve()))
    command=['prover/examples/run_target_example.sh',args.configuration,str(work)]
    result=subprocess.run(command,cwd=checkout,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=1800)
    text=result.stdout.replace(str(checkout),'FLASH_PROVE').replace(str(work),'WORK').replace(str(Path.home()),'HOME')
    phase_records=[json.loads(line) for line in phases.read_text().splitlines()] if phases.exists() else []
    accepted=result.returncode==0 and (work/'cp_verify.log').is_file() and (work/'cp_verify.log').read_text().splitlines()[-1]=='YES'
    record=dict(utc=datetime.now(timezone.utc).isoformat(),configuration=args.configuration,
        command=['prover/examples/run_target_example.sh',args.configuration,'WORK'],exit_code=result.returncode,
        last_line=result.stdout.splitlines()[-1] if result.stdout.splitlines() else '',accepted=accepted,
        script_output=text,phases=phase_records,performance_claim=args.performance_claim,
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['flash_cycle.py','profile_tool.py']},
        binary_sha256={p:hashlib.sha256((native/p).read_bytes()).hexdigest() for p in ('cp_commit','cp_prove','cp_verify')},
        upstream_script_sha256=hashlib.sha256((checkout/'prover/examples/run_target_example.sh').read_bytes()).hexdigest(),
        applied_diff_sha256=hashlib.sha256(subprocess.check_output(['git','diff','--binary'],cwd=checkout)).hexdigest())
    if accepted:
        verifier_output=(work/'cp_verify.log').read_text()
        required=('covered:','commitment:','proof of work:','result-v1')
        record['verifier_metadata']={prefix:[line for line in verifier_output.splitlines() if line.startswith(prefix)] for prefix in required}
        assert all(record['verifier_metadata'].values()), 'Retain all native acceptance metadata'
        commitment_lines=[line for line in (work/'cp_commit.log').read_text().splitlines() if line.startswith('commitment ID: ')]
        assert len(commitment_lines)==1
        record['commitment_id']=commitment_lines[0].split(':',1)[1].strip()
        public=Path('artifacts')/work.name;assert not public.exists();public.mkdir(parents=True)
        # Upstream duty: export output and its log only after native verification accepted.
        for folder in ('config','ivk'):shutil.copytree(work/folder,public/folder)
        for folder in ('in','out'):(public/folder).mkdir()
        for name in ('in/example.req','out/example.y','out/example.proof'):shutil.copy2(work/name,public/name)
        for name in ('cp_commit.log','cp_prove.log','cp_verify.log'):
            data=(work/name).read_text().replace(str(work),'WORK').replace(str(checkout),'FLASH_PROVE').replace(str(Path.home()),'HOME')
            (public/name.replace('.log','.txt')).write_text(data,encoding='utf-8',newline='\n')
        record['artifacts_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in public.rglob('*') if p.is_file()}
        record['proof_bytes']=(work/'out/example.proof').stat().st_size
    else:
        record['limitation']='No rejected response, proof or private proving-key material is exported. This is an unsuccessful compatibility experiment.'
    Path(args.output).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Cycle exit',result.returncode,'accepted',accepted,'phases',phase_records,flush=True)
    print(text[-1800:],flush=True)
    # A failed hypothesis is retained, and remains a failing executable experiment.
    if not accepted:raise SystemExit(result.returncode or 1)


if __name__=='__main__':main()
