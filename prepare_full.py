"""Layer packed-table support over a separate pinned compact SM120 checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    parser.add_argument('--reference',type=Path)
    args=parser.parse_args()
    command=[sys.executable,'prepare_sm120.py',str(args.destination)]
    if args.reference:command+=['--reference',str(args.reference)]
    subprocess.run(command,check=True)
    patch='patches/sm120-tables.patch'
    subprocess.run(['git','apply','--check',str(Path(patch).resolve())],cwd=args.destination,check=True)
    subprocess.run(['git','apply',str(Path(patch).resolve())],cwd=args.destination,check=True)
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=args.destination,text=True).splitlines()
    sources=['prepare_full.py','prepare_sm120.py','patches/sm120-compact.patch','patches/sm120-memory.patch',patch]
    record=dict(upstream_revision='9e2bdd8ff5bf9c62f18263d7dac189b0400b260c',
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
        patched_sha256={p:hashlib.sha256((args.destination/p).read_bytes()).hexdigest() for p in changed},
        scope='Native SM120, 81 KiB fused experts, 64 KiB histograms, 72 KiB tiled engine, immutable packed lookup table in GPU memory, runtime occupancy. Existing exact forest fallback; protocol/verifier/checks unchanged.')
    Path('results/full-preparation.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
