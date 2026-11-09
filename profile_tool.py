"""Time one unchanged native FlashProve program without consuming its output."""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

command=sys.argv[1:]
assert command and Path(command[0]).name in ('cp_commit','cp_prove','cp_verify')
begin=time.perf_counter()
result=subprocess.run(command)
record=dict(program=Path(command[0]).name,exit_code=result.returncode,wall_ms=(time.perf_counter()-begin)*1000,
    peak_host_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
with open(os.environ['REQUANT_PHASE_RECORD'],'a',encoding='utf-8') as output:
    output.write(json.dumps(record)+'\n')
sys.exit(result.returncode)
