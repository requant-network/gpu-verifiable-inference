"""Prepare the SM120 port including a bounded consumer-card engine reserve."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path)
    parser.add_argument('--reference',type=Path);args=parser.parse_args()
    command=[sys.executable,'prepare_full.py',str(args.destination)]
    if args.reference:command+=['--reference',str(args.reference)]
    subprocess.run(command,check=True)
    patch='patches/sm120-reserve.patch'
    subprocess.run(['git','apply','--check',str(Path(patch).resolve())],cwd=args.destination,check=True)
    subprocess.run(['git','apply',str(Path(patch).resolve())],cwd=args.destination,check=True)
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=args.destination,text=True).splitlines()
    files=['prepare_consumer.py','prepare_full.py','prepare_sm120.py','patches/sm120-compact.patch','patches/sm120-memory.patch','patches/sm120-tables.patch',patch]
    record=dict(upstream_revision='9e2bdd8ff5bf9c62f18263d7dac189b0400b260c',
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files},
        patched_sha256={p:hashlib.sha256((args.destination/p).read_bytes()).hexdigest() for p in changed},
        scope='Native compact SM120 kernels and 4 GiB engine reserve, retaining 2 GiB driver allowance and all allocation/protocol/verifier checks. Empirical small-model workspace qualification remains required; no universal VRAM fit claim.')
    Path('results/consumer-preparation.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
