"""Independent arithmetic from committed finite-panel rows; no code execution."""
import hashlib,json
from fractions import Fraction
from pathlib import Path


def main():
    paths=['results/checkpoint_challenge_grading_20260928.json','results/literal_panel_baseline_20260928.json','results/checkpoint_challenge_generation_reconciliation_20260928.json']
    grade,baseline,cost=[json.loads(Path(p).read_bytes()) for p in paths]
    rows=grade['rows'];base=baseline['rows'];roots={r['root'] for r in base}
    assert len(roots)==9 and len(base)==54 and len(rows)==162
    expected={(r['root'],r['artifact'],a) for r in base for a in ['PATCH','RETHINK','FRESH']}
    assert len(expected)==162 and {(r['root'],r['artifact'],r['arm']) for r in rows}==expected
    counts={};means={}
    for arm in ['STOP','PATCH','RETHINK','FRESH']:
        selected=base if arm=='STOP' else [r for r in rows if r['arm']==arm]
        status=[r['batteries']['supplement_v1'] for r in selected]
        assert set(status)<={'PASS','FAIL','INCOMPLETE'}
        counts[arm]={s:status.count(s) for s in ['PASS','FAIL','INCOMPLETE']}
        bounds=[]
        for root in roots:
            st=[r['batteries']['supplement_v1'] for r in selected if r['root']==root];assert len(st)==6
            bounds.append((Fraction(st.count('PASS'),6),Fraction(st.count('PASS')+st.count('INCOMPLETE'),6)))
        means[arm]=[sum(b[j] for b in bounds)/9 for j in [0,1]]
        assert all(abs(float(means[arm][j])-grade['descriptive']['mean_bounds'][arm][j])<1e-12 for j in [0,1])
    contrast={a+'-'+b:[str(means[a][0]-means[b][1]),str(means[a][1]-means[b][0])] for a,b in [('PATCH','RETHINK'),('PATCH','FRESH'),('RETHINK','FRESH')]}
    print(json.dumps({'scope':'saved-row arithmetic reproduction, no payload execution or independent scientific review','inputs_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},'counts':counts,'equal_root_mean_bounds_exact':{a:list(map(str,v)) for a,v in means.items()},'contrast_bounds_exact':contrast,'allocated_gpu_seconds':cost['allocated_seconds'],'discovery_only':True},indent=2))

if __name__=='__main__':main()
