"""Freeze ten new seed replicates of every discovery request; no task selection."""
import copy,hashlib,json,random
from pathlib import Path
from experiments.landmark.collect import digest


def main():
    source=Path('work/checkpoint_challenge_requests_20260928.json');original=json.loads(source.read_bytes())
    requests_path=Path('work/checkpoint_replication_requests_20260928.json');manifest_path=Path('results/checkpoint_replication_assignments_20260928.json')
    if requests_path.exists() or manifest_path.exists():raise ValueError('refuse overwrite')
    rng=random.Random(2026092811);used={r['payload']['seed'] for r in original};requests=[]
    for replicate in range(10):
        for old in original:
            req=copy.deepcopy(old);seed=rng.randrange(1,2**32-1)
            while seed in used:seed=rng.randrange(1,2**32-1)
            used.add(seed);req['payload']['seed']=seed;req['replicate']=replicate;requests.append(req)
    rng.shuffle(requests)
    for i,r in enumerate(requests):r['slot']=i
    requests_path.write_text(json.dumps(requests,indent=2)+'\n')
    fields=['slot','root','artifact','arm','replicate','initial_artifact_sha256','public_status']
    manifest_path.write_text(json.dumps([{**{k:r[k] for k in fields},'seed':r['payload']['seed'],'payload_sha256':digest(r['payload'])} for r in requests],indent=2)+'\n')
    print(len(requests),hashlib.sha256(requests_path.read_bytes()).hexdigest())

if __name__=='__main__':main()
