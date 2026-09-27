#!/usr/bin/env python3
"""Three bounded --version probes, no model loading or generation."""
import json
from pathlib import Path
import resource
import subprocess
import time
from scripts.calibrate_receiver_resources_20260927 import sha_file

if __name__=='__main__':
    out=Path('results/receiver_fsize_diagnostic_20260927.json')
    if out.exists():raise ValueError('refuse overwrite')
    m=json.loads(Path('experiments/env/llama_server_manifest.json').read_bytes())
    for n,r in m['files'].items():
        if sha_file(Path('work/bin')/n)!=r['sha256']:raise ValueError('binary pin')
    rows=[]
    for cap in [None,8388608,67108864]:
        def limit():
            if cap is not None:resource.setrlimit(resource.RLIMIT_FSIZE,(cap,cap))
        t=time.monotonic()
        try:
            p=subprocess.run(['work/bin/llama-server','--version'],capture_output=True,timeout=5,preexec_fn=limit)
            rows.append({'file_cap':cap,'returncode':p.returncode,'stdout':p.stdout[:4096].decode(errors='replace'),'stderr':p.stderr[:4096].decode(errors='replace'),'seconds':time.monotonic()-t})
        except subprocess.TimeoutExpired:rows.append({'file_cap':cap,'timeout':True,'seconds':time.monotonic()-t})
    out.write_text(json.dumps({'classification':'bounded version-command infrastructure diagnosis; no models loaded','rows':rows,'model_calls':0},indent=2)+'\n')
    print(out.read_text())
