"""Exercise the pinned native CPU verifier with honest and altered public fixtures."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    parser.add_argument('--output', default='results/cpu-verifier.json')
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    fixture = checkout / 'examples/accepted-proof'
    verifier = checkout / 'bin/cp_verify'
    commitment = (fixture / 'ID.txt').read_text().strip()
    cases = []
    with tempfile.TemporaryDirectory(prefix='requant-public-controls-') as temp:
        work = Path(temp)
        for name in ('honest', 'incorrect-id', 'altered-request', 'altered-output', 'altered-proof', 'truncated-proof'):
            current = work / name
            shutil.copytree(fixture, current)
            changed = {'altered-request': 'example.req', 'altered-output': 'example.y',
                       'altered-proof': 'example.proof', 'truncated-proof': 'example.proof'}.get(name)
            if changed:
                target = current / changed
                data = bytearray(target.read_bytes())
                assert data
                if name == 'truncated-proof':
                    data = data[:len(data)//2]
                else:
                    data[len(data)//2] ^= 1
                target.write_bytes(data)
            supplied_id = ('0' if commitment[0] != '0' else '1') + commitment[1:] if name == 'incorrect-id' else commitment
            command = [str(verifier), str(current/'config'), str(current/'ivk'), str(current/'example.req'),
                       str(current/'example.y'), str(current/'example.proof'), '-id', supplied_id]
            begin = time.perf_counter()
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
            elapsed = (time.perf_counter()-begin)*1000
            lines = result.stdout.splitlines()
            accepted = result.returncode == 0 and bool(lines) and lines[-1] == 'YES'
            assert accepted == (name == 'honest'), (name, result.returncode, result.stdout)
            public_command = ['bin/cp_verify', f'CONTROL/{name}/config', f'CONTROL/{name}/ivk',
                f'CONTROL/{name}/example.req', f'CONTROL/{name}/example.y', f'CONTROL/{name}/example.proof', '-id', supplied_id]
            # Only replace the temporary path; preserve the verifier's exact verdict and metadata.
            output = result.stdout.replace(str(work), 'CONTROL')
            cases.append(dict(name=name, command=public_command, exit_code=result.returncode,
                last_line=lines[-1] if lines else '', accepted=accepted, wall_ms=elapsed, output=output))
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()
    assert revision == '9e2bdd8ff5bf9c62f18263d7dac189b0400b260c'
    record = dict(utc=datetime.now(timezone.utc).isoformat(), upstream_revision=revision, commitment_id=commitment,
        cases=cases, source_sha256={'cpu_study.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        verifier_sha256=hashlib.sha256(verifier.read_bytes()).hexdigest(),
        fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.iterdir() if p.is_file()},
        performance_claim=False, scope='Native CPU verifier of stored synthetic proof; no claim of newly generated GPU inference.')
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('PASS native stored-proof verification and five rejecting controls')


if __name__ == '__main__':
    main()
