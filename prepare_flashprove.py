"""Apply the attributed SM120 patch to a separate pinned FlashProve checkout."""
import argparse,hashlib,json,pathlib,subprocess

PIN='9e2bdd8ff5bf9c62f18263d7dac189b0400b260c'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=pathlib.Path);args=parser.parse_args()
assert not args.destination.exists(),'Use a new destination; existing experiments are preserved'
patch=pathlib.Path('patches/sm120.patch').resolve()
subprocess.run(['git','clone','https://github.com/anthropics/FlashProve.git',str(args.destination)],check=True)
subprocess.run(['git','checkout',PIN],cwd=args.destination,check=True)
subprocess.run(['git','apply','--check',str(patch)],cwd=args.destination,check=True)
subprocess.run(['git','apply',str(patch)],cwd=args.destination,check=True)
sources=['prepare_flashprove.py','patches/sm120.patch']
record=dict(upstream_revision=PIN,source_sha256={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in sources},
    patched_sha256={p:hashlib.sha256((args.destination/p).read_bytes()).hexdigest() for p in ('prover/build.sh','prover/weights_blocks/experts.cuh')},
    scope='Separate attributed working copy; immutable upstream pin, native SM120 architecture and existing exact cuBLAS expert path. No protocol/verifier/validation changes.')
pathlib.Path('results').mkdir(exist_ok=True)
pathlib.Path('results/port-preparation.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
