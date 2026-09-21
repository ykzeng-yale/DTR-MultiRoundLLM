"""Read-only arithmetic and provenance audit; never executes stored programs."""
from pathlib import Path
import collections
import hashlib
import json
import statistics
import subprocess
import time


def main():
    start = time.perf_counter()
    base = Path('results')
    evidence, runs, signatures = {}, [], []

    def load(path, jsonl=False):
        data = path.read_bytes()
        evidence[str(path)] = hashlib.sha256(data).hexdigest()
        return [json.loads(x) for x in data.splitlines()] if jsonl else json.loads(data)

    for name in ['landmark_dev_release_v1_20260921T130048Z',
                 'landmark_dev_release_v1b_20260921T130349Z',
                 'landmark_dev_release_v1c_20260921T130757Z']:
        p = base / name
        completion, manifest = load(p/'completion.json'), load(p/'manifest.json')
        calls, roots = load(p/'calls.jsonl', True), load(p/'roots.jsonl', True)
        for file, digest in completion['checksums'].items():
            assert hashlib.sha256((p/file).read_bytes()).hexdigest() == digest
        for file, digest in manifest['freeze']['tracked_file_hashes'].items():
            blob = subprocess.check_output(['git', 'show', manifest['freeze']['resolved_commit']+':'+file])
            assert hashlib.sha256(blob).hexdigest() == digest
        for row in calls:
            assert hashlib.sha256(json.dumps(row['output'], sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest() == row['output_sha256']
        assert sum(x['prompt_tokens'] for x in calls) == completion['measured_prompt_tokens']
        assert sum(x['completion_tokens'] for x in calls) == completion['measured_completion_tokens']
        signatures.append({(x['root_id'], x['arm'], x['replicate']):x['output_sha256'] for x in calls})
        runs.append({'run': name, 'freeze': manifest['freeze']['resolved_commit'], 'calls':len(calls),
                     'prompt_tokens':completion['measured_prompt_tokens'],
                     'completion_tokens':completion['measured_completion_tokens'],
                     'seconds':completion['wall_seconds'], 'paid_usd':completion['paid_api_spend_usd']})
    assert signatures[0] == signatures[1] == signatures[2]
    grades = load(base/'landmark_dev_release_v1c_20260921T130757Z_grades/grades.jsonl', True)
    assert all(x['outcome'] in [0, 1] for x in grades)
    lookup = {(x['root_id'], x['arm'], x['replicate']):x for x in calls}
    for row in grades:
        key = (row['root_id'], 'initial' if row['arm']=='stop' else row['arm'], row['replicate'])
        assert row['output_sha256'] == lookup[key]['output_sha256']
    ids = sorted({x['root_id'] for x in grades})
    arms = ['stop', 'generic_repair', 'history_specific_repair', 'independent_restart']
    by = {i:{a:[x['outcome'] for x in grades if x['root_id']==i and x['arm']==a] for a in arms} for i in ids}
    differences = [statistics.mean(by[i]['history_specific_repair'])-statistics.mean(by[i]['generic_repair']) for i in ids]
    report = {
        'evidence_type':'Independent read-only audit of worker fresh exploratory development records; no model or candidate execution',
        'reviewed_worker_commit':'335a6deb0a7dd60e75b25313487dae242ca6a000',
        'checks':dict.fromkeys(['completion_checksums','freeze_commit_blob_hashes','output_hashes',
                              'grade_output_bindings','usage_sums','three_output_maps_equal'],True),
        'runs':runs, 'totals':{k:sum(x[k] for x in runs) for k in ['calls','prompt_tokens','completion_tokens','seconds','paid_usd']},
        'features':dict(collections.Counter(x['feedback_feature'] for x in roots)),
        'families':sorted({x['family_id'] for x in roots}), 'root_outcomes':by,
        'arm_means':{a:statistics.mean(statistics.mean(by[i][a]) for i in ids) for a in arms},
        'root_mean_history_minus_generic':dict(zip(ids,differences)),
        'descriptive_root_sample_variance':statistics.variance(differences),
        'input_sha256':evidence, 'audit_seconds':time.perf_counter()-start,
        'audit_new_model_calls':0,'audit_new_candidate_executions':0,'audit_paid_usd':0,
        'limits':'Does not independently rerun grading or establish root independence, population precision, or feedback efficacy.'}
    target = base/'development_delivery_lead_audit_20260921.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['totals','features','arm_means','root_mean_history_minus_generic','descriptive_root_sample_variance','audit_seconds']},indent=2))


if __name__ == '__main__':
    main()
