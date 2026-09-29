#!/usr/bin/env python3
"""Audit whether saved project runs supply admissible text-Q training/evaluation data.

This is a provenance/positivity audit only. It never fits a policy, reads
per-episode terminal outcome values, executes a task, or changes any frame.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_json(path):
    return json.loads((ROOT / path).read_text())

def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='fresh output path; existing files are never overwritten')
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    # The ignored join contains sanitized labels; discard the outcome field
    # immediately and inspect only structure and public logged action metadata.
    rows = []
    for line in (ROOT / 'work/pilot_terminal_label_join_20260929/episodes.jsonl').read_text().splitlines():
        row = json.loads(line)
        rows.append({k: v for k, v in row.items() if k != 'outcome'})
    by_stage = [Counter(), Counter()]
    families = set()
    versions = set()
    for row in rows:
        families.add(row['family'])
        for t, step in enumerate(row['steps']):
            s = step['selection']
            assert s['slate_ids'] == ['STOP', 'PATCH', 'RETHINK']
            assert s['probabilities'] == [1/3, 1/3, 1/3]
            assert s['selected_probability'] == 1/3
            by_stage[t][s['chosen_id']] += 1
            versions.add((step['view']['receiver_sha256'], step['view']['generator_sha256']))
    assert len(rows) == 18 and sum(sum(c.values()) for c in by_stage) == 31 and len(families) == 9
    labels = load_json('results/pilot_terminal_label_join_20260929.json')
    assert labels['assigned'] == labels['complete_labels'] == 18 and labels['missing'] == []
    assert labels['policy_fitted'] is False and labels['independent_families_claimed'] is False
    full = load_json('results/full_history_pilot_reconciliation_20260928.json')
    strat = load_json('results/strategy_terminal_reconciliation_20260928.json')
    strat_rows = load_json('work/strategy_terminal_grading_20260928/summary.json')
    strat_keys = [{k: r[k] for k in ('root', 'trajectory', 'policy', 'disposition')} for r in strat_rows['rows']]
    strat_roots = {r['root'] for r in strat_keys}
    strat_starts = {(r['root'], r['trajectory']) for r in strat_keys}
    assert strat_rows['assigned'] == 162 and len(strat_roots) == 9 and len(strat_starts) == 18
    frame = load_json('results/policy_full_frame_reconciliation_20260926.json')
    adjudication = load_json('results/policy_candidate_adjudication_20260926.json')
    assert full['assigned_trajectories'] == 18 and full['returned_calls'] == 42
    assert strat['assigned'] == 162 and strat['all_rows_and_batteries_reconciled']
    assert frame['remaining_candidate_roots_after_known_receiver_exposure_and_display_hold'] == 43
    assert adjudication['approved_evaluation_roster'] is False
    inputs = [
        'work/pilot_terminal_label_join_20260929/episodes.jsonl',
        'results/pilot_terminal_label_join_20260929.json',
        'results/full_history_pilot_reconciliation_20260928.json',
        'results/strategy_terminal_reconciliation_20260928.json',
        'work/strategy_terminal_grading_20260928/summary.json',
        'results/policy_full_frame_reconciliation_20260926.json',
        'results/policy_candidate_adjudication_20260926.json',
        'docs/e12_results_20260922.md', 'docs/e13a_lead_judgment_20260923.md',
        'experiments/sequential/text_history_q.py',
        'scripts/audit_existing_full_history_fitability_20260929.py',
    ]
    result = {
        'classification': 'lead structural fitability audit; no policy fit, task execution, or new data collection',
        'question': 'Do existing logged outcomes support an admissible full-history STOP/PATCH/RETHINK policy fit and independent family evaluation?',
        'full_history_behavior_log': {
            'assigned_trajectories': len(rows), 'complete_sanitized_labels_reported': labels['complete_labels'],
            'decision_points': sum(sum(c.values()) for c in by_stage), 'stage0_actions': dict(by_stage[0]),
            'stage1_actions': dict(by_stage[1]), 'unique_root_families': len(families),
            'two_trajectories_per_root': all(sum(r['family'] == f for r in rows) == 2 for f in families),
            'logged_slate_probabilities_verified': True, 'one_receiver_generator_pair': len(versions) == 1,
            'data_disposition': 'support/schema pilot only: the same nine roots were reused by other development comparisons; excluded from policy fit and independent evaluation'
        },
        'other_saved_data': [
            {'stream': 'matched complete-strategy comparison', 'evidence': '162 branches, 18 starts, 9 reused roots; each row is a complete assigned strategy trajectory, not randomized action selection at each public history', 'use': 'descriptive strategy comparison only'},
            {'stream': 'E12', 'evidence': '14 fixed development roots and five fixed prompt arms; single-intervention arm contrast, not two-decision per-history slate randomization', 'use': 'development mechanism evidence, not full-history Q logger'},
            {'stream': 'E13a', 'evidence': '60 assigned draws on five E12 outcome-inspected checkpoints; R1/FRESH complete-package comparison', 'use': 'conditional development comparison, not an independent policy sample'},
            {'stream': 'original 198-root frame', 'evidence': '43 remaining candidates after known receiver-development exposure and display hold; 15 definite prior-family links, 16 plausible links, 10 with no direct link found; no evaluation roster approved', 'use': 'source candidate roster, not logged trajectories or certified untouched families'}
        ],
        'learner_scale': {'fixed_features': 256, 'actions': 3, 'decision_stages': 2, 'action_stage_coefficient_vectors': 6, 'nominal_coefficients': 1536, 'observed_decisions': 31, 'smallest_stage_action_cell': 2},
        'judgment': 'No existing dataset is admissible for the target policy fit plus independent-family evaluation. The only full-history randomized slate log has 9 reused roots and 31 decisions, with action-stage cells 5/6/7 and 2/4/7; ridge makes computation possible but cannot create family-level information or an untouched test set. Other runs lack sequential per-history action randomization or independence. Do not fit or launch another controller comparison from these records.',
        'next_gate': 'Before further model calls, specify and admit a population-specific semantic observer and family/exposure frame. Then collect a separately frozen development cohort under known positive action probabilities at each realized supported history; reserve untouched families for evaluation and log cost/missingness. No population substitution, endpoint repair, or five-point threshold change is authorized by this audit.',
        'readiness_percent': 60, 'readiness_delta_percentage_points': 0,
        'input_sha256': {p: sha(p) for p in inputs},
        'receiver_calls': 0, 'benchmark_executions': 0, 'policy_fit': False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'families': len(families), 'decisions': sum(sum(c.values()) for c in by_stage), 'action_counts': [dict(x) for x in by_stage], 'nominal_coefficients': 1536, 'eligible_fit': False}))

if __name__ == '__main__':
    main()
