"""Static examples audit: literal parsing and independent arithmetic, no code execution."""
import ast
import hashlib
import json
import math
from pathlib import Path
import time


def main():
    start = time.perf_counter()
    public_path = Path('docs/public_diagnostic_examples_v1.json')
    private_path = Path('experiments/landmark/dev_release_v1c/private_specs.jsonl')
    public = json.loads(public_path.read_text())
    private = {x['root_id']:x for x in map(json.loads, private_path.read_text().splitlines())}
    checks = []
    for task in public['cases']:
        root = task['root_id']
        inputs = []
        for assertion in private[root]['private_assertions']:
            tree = ast.parse(assertion)
            calls = [n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id==task['entry_point']]
            assert len(calls)==1 and not calls[0].keywords
            inputs.append([ast.literal_eval(n) for n in calls[0].args])
        for case in task['cases']:
            args = ast.literal_eval(case['args_literal'])
            expected = ast.literal_eval(case['expected_literal'])
            if root=='mbpp/52': actual = sum(args[0] for _ in range(args[1]))
            elif root=='mbpp/357': actual = sorted(y for tup in args[0] for y in tup)[-1]
            elif root=='mbpp/373': actual = args[0]*args[1]*args[2]
            elif root=='mbpp/378': actual = [args[0][(i-1)%len(args[0])] for i in range(len(args[0]))]
            elif root=='mbpp/402':
                n,r,p=args
                actual=(math.factorial(n)//(math.factorial(r)*math.factorial(n-r)))%p
            elif root=='mbpp/489': actual=sum(x==sorted(args[1])[-1] for x in args[1])
            elif root=='mbpp/509': actual=(args[0]+1)//2
            else: raise ValueError(root)
            assert actual==expected
            checks.append({'root_id':root,'case_id':case['case_id'],'oracle_agrees':True,'literal_private_input_overlap':args in inputs})
    assert len(checks)==21
    result={'evidence_type':'static literal/input and arithmetic audit; no stored code execution',
            'cases':checks,'case_count':len(checks),
            'overlap_gate':'HOLD' if any(x['literal_private_input_overlap'] for x in checks) else 'PASS',
            'input_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [public_path,private_path]},
            'seconds':time.perf_counter()-start,'model_calls':0,'candidate_reference_executions':0,'paid_usd':0,
            'limits':'No semantic holdout, grader validity, informative diagnostic or empirical efficacy certification.'}
    Path('results/public_diagnostic_examples_review_20260921.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['cases','input_sha256']},indent=2))


if __name__=='__main__':main()
