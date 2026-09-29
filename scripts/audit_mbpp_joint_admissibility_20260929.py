#!/usr/bin/env python3
"""Intersect existing MBPP family, exposure, contract, and admission dispositions.

Source/provenance synthesis only: no task execution, model calls, or new review.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'results/policy_candidate_adjudication_20260926.json'
FRAME = 'results/policy_full_frame_reconciliation_20260926.json'

def read_json(relative):
    return json.loads((ROOT / relative).read_text())

def digest(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True, help='fresh output file; never overwrite')
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    adjudication = read_json(SOURCE)
    frame = read_json(FRAME)
    rows = adjudication['records']
    assert len(rows) == 43 and adjudication['approved_evaluation_roster'] is False
    family_counts = Counter(r['family_axis'] for r in rows)
    contract_counts = Counter(r['contract_axis'] for r in rows)
    assert sum(family_counts.values()) == sum(contract_counts.values()) == 43
    potential = {r['task_id'] for r in rows if r['family_axis'] in (
        'no_direct_prior_relation_found', 'within_candidate_family')}
    assert len(potential) == 12
    eligible_contracts = {r['task_id'] for r in rows if r['contract_axis'] == 'adopted'}
    assert not eligible_contracts
    # Keep only recorded MBPP-to-MBPP links among the 12 after the conservative
    # definite/prior and plausible/prior family screen. Components are retrieval
    # constraints only, not accepted families or independence certificates.
    graph = {task: set() for task in potential}
    for row in rows:
        task = row['task_id']
        if task not in potential:
            continue
        for uid in row.get('manual_related_uids', []):
            source, _, raw_id = uid.partition('/')
            if source.lower() != 'mbpp':
                continue
            try:
                related = int(raw_id)
            except ValueError:
                continue
            if related in potential:
                graph[task].add(related)
                graph[related].add(task)
    seen, components = set(), []
    for task in sorted(potential):
        if task in seen:
            continue
        stack, component = [task], []
        seen.add(task)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in graph[current] - seen:
                seen.add(neighbor)
                stack.append(neighbor)
        components.append(sorted(component))
    measurement_exposed = sorted(r['task_id'] for r in rows
                                 if r['exposure_tags'].get('measurement_development'))
    no_prior_record = sum(r['exposure_tags'].get('prior_receiver_development') is False for r in rows)
    no_e11_record = sum(r['exposure_tags'].get('e11_dev_root') is False for r in rows)
    assert measurement_exposed == [345, 877] and no_prior_record == no_e11_record == 43
    assert frame['approved_evaluation_roster'] is False
    assert all(r.get('approved_evaluation_roster') is False for r in rows)
    # Existing dispositions are deliberately not auto-converted to eligibility.
    status_intersection = Counter((r['family_axis'], r['contract_axis']) for r in rows)
    result = {
        'classification': 'lead source-ledger intersection; no independent admission decision, task execution, or collection',
        'question': 'Does the original MBPP candidate ledger contain any currently contract-clear, plausibly untouched evaluation root?',
        'candidate_roots': 43,
        'family_axis_counts': dict(family_counts),
        'contract_axis_counts': dict(contract_counts),
        'family_contract_intersection': [
            {'family_axis': f, 'contract_axis': c, 'count': n}
            for (f, c), n in sorted(status_intersection.items())
        ],
        'strict_prior_family_prescreen': {
            'screen_rule': 'retain only no_direct_prior_relation_found and within_candidate_family; exclude definite_prior_family and hold plausible_shared_family',
            'remaining_roots': sorted(potential),
            'remaining_root_count': len(potential),
            'recorded_candidate_link_components': components,
            'component_count': len(components),
            'interpretation': 'components preserve only explicit recorded MBPP-to-MBPP co-split links among the retained candidates; they are not final family adjudications, exposure certificates, or independent clusters; unknown links may merge them'
        },
        'exposure_crosswalk': {
            'recorded_prior_receiver_development_false': no_prior_record,
            'recorded_e11_development_false': no_e11_record,
            'measurement_development_roots': measurement_exposed,
            'critical_limit': 'false means no exposure was recorded in these inputs, not proof of no receiver/pretraining exposure; the two measurement-development roots remain exposed for evaluation'
        },
        'joint_admission': {
            'approved_evaluation_roster': False,
            'currently_contract_clear_roots': len(eligible_contracts),
            'currently_jointly_admissible_roots': 0,
            'reason': 'all43 candidates have an unresolved contract axis (36 clarification,3 reference,1 domain-change,3 specification holds); family, exposure, observer, sampling and execution-independence gates are also incomplete'
        },
        'scientific_decision': 'No original-MBPP evaluation roster can be frozen from these dispositions. Even after conservatively setting aside31 definite/plausible prior-family candidates, the12-root remainder has zero adopted contracts and only eight provisional connected components under recorded candidate links. This is a feasibility/admission finding, not proof the original research question is futile or that eight final independent families exist. Do not collect or fit on this ledger as though it were admitted.',
        'next_gate': 'Resolve the original task-contract and semantic-measurement disposition over the full candidate ledger without selecting by expected outcomes; finalize global family/co-split and exposure crosswalk, then test whether any untouched roster and supported sampling law remain. If the resulting roster cannot meet the already accepted precision/usefulness requirements under finite resources, report infeasibility; do not substitute BigCodeBench or relax the target.',
        'readiness_percent': 60, 'readiness_delta_percentage_points': 0,
        'input_sha256': {p: digest(p) for p in (SOURCE, FRAME, 'docs/policy_candidate_adjudication_20260926.md', 'docs/policy_precision_decision_20260927.md', 'scripts/audit_mbpp_joint_admissibility_20260929.py')},
        'receiver_calls': 0, 'benchmark_executions': 0, 'policy_fit': False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'candidates':43,'family_screen_roots':12,'provisional_link_components':len(components),'contract_clear':0,'jointly_admissible':0}))

if __name__ == '__main__':
    main()
