"""Prepare a separate pinned FlashProve checkout with compact SM120 kernels."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PIN = '9e2bdd8ff5bf9c62f18263d7dac189b0400b260c'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--reference', type=Path)
    args = parser.parse_args()
    assert not args.destination.exists(), 'Use a new destination; preserve previous experiments'
    command = ['git', 'clone']
    if args.reference:
        command += ['--reference-if-able', str(args.reference.resolve())]
    command += ['https://github.com/anthropics/FlashProve.git', str(args.destination)]
    subprocess.run(command, check=True)
    subprocess.run(['git', 'checkout', PIN], cwd=args.destination, check=True)
    patches = ['patches/sm120-compact.patch', 'patches/sm120-memory.patch']
    for patch in patches:
        patch = str(Path(patch).resolve())
        subprocess.run(['git', 'apply', '--check', patch], cwd=args.destination, check=True)
        subprocess.run(['git', 'apply', patch], cwd=args.destination, check=True)
    changed = subprocess.check_output(['git', 'diff', '--name-only'], cwd=args.destination, text=True).splitlines()
    record = dict(upstream_revision=PIN,
        source_sha256={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['prepare_sm120.py'] + patches},
        patched_sha256={p: hashlib.sha256((args.destination / p).read_bytes()).hexdigest() for p in changed},
        scope='Compact fused experts; public bin-window histograms; two-stage engine; existing exact forest fallback. Protocol, verifier and checks unchanged.')
    Path('results').mkdir(exist_ok=True)
    Path('results/sm120-preparation.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')

if __name__ == '__main__':
    main()
