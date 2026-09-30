"""Source-only contract for a future two-decision randomized development study.

No population is selected and no collection is released. The caller must supply
an independently adjudicated root/family crosswalk and pinned scientific sources.
This module binds outcome-blind splits, assignments, all-assigned receipts and a
policy lock; it does not establish family independence, measurement validity,
semantic secrecy, sufficient support, or that a supplied policy was really fit.
The existing text Q learner remains quality-only fitted Q, not DR training.
"""
import copy
import hashlib
import json
import math
import random
from fractions import Fraction

from experiments.sequential.public_history import (
    bind_selection, digest, public_view,
)
from experiments.sequential.text_history_q import ACTIONS, validate

SPLITS = ('train', 'tune', 'evaluation')
PINS = ('crosswalk', 'population', 'measurement', 'receiver', 'generator',
        'public_observer', 'private_observer', 'learner', 'analysis')
COMPONENTS = ('receiver', 'generator', 'critic', 'public_check', 'private_check')
COST_FIELDS = {'stage', 'component', 'calls', 'input_tokens',
               'completion_tokens', 'elapsed_seconds', 'usd', 'energy_joules'}


def sha256(value):
    """Canonical metadata binding, never a secrecy or provenance proof."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                   ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def answer_sha256(text):
    """Raw UTF-8 artifact hash for this identity response-to-program contract.

    Transcript-prefix/config hashing remains canonical JSON. A collector that
    strips fences or transforms an answer needs a new explicitly pinned
    extractor/receipt contract; it cannot substitute a different scored artifact.
    """
    if type(text) is not str:
        raise ValueError('raw UTF-8 answer artifact')
    return hashlib.sha256(text.encode('utf-8', errors='strict')).hexdigest()


def _text(value, name):
    if type(value) is not str or not value:
        raise ValueError(name)


def _number(value, name, *, integer=False, upper=None):
    types = (int,) if integer else (int, float)
    if type(value) not in types or not math.isfinite(value) or value < 0:
        raise ValueError(name)
    if upper is not None and value > upper:
        raise ValueError(name)


def make_design(root_families, split_counts, *, repeats, seed, pins, root_prefix_sha256):
    """Freeze a proposed crosswalk/assignment ledger without using outcomes.

    Family counts are explicit; all roots and repeated trajectories of one
    supplied family stay together. Seeded shuffle and draws are materialized,
    not reconstructed during collection. Unused draws survive absorbing STOP.
    The fixed logger is uniform over the realized STOP/PATCH/RETHINK slate;
    these are selector probabilities, not probabilities of arbitrary language.
    """
    if type(root_families) is not dict or not root_families:
        raise ValueError('nonempty root/family crosswalk')
    for root, family in root_families.items():
        _text(root, 'root'); _text(family, 'family')
    if type(root_prefix_sha256) is not dict or set(root_prefix_sha256) != set(root_families):
        raise ValueError('every root needs its frozen initial public prompt prefix')
    for value in root_prefix_sha256.values():
        digest(value)
    if type(split_counts) is not dict or set(split_counts) != set(SPLITS):
        raise ValueError('three family split counts required')
    for count in split_counts.values():
        _number(count, 'split count', integer=True)
        if count == 0:
            raise ValueError('each split needs families')
    if type(repeats) is not int or repeats < 1 or type(seed) is not int:
        raise ValueError('repeats/seed')
    if type(pins) is not dict or set(pins) != set(PINS):
        raise ValueError('complete source pins required')
    for value in pins.values():
        digest(value)
    families = sorted(set(root_families.values()))
    if sum(split_counts.values()) != len(families):
        raise ValueError('all families must be assigned exactly once')
    rng = random.Random(seed)
    rng.shuffle(families)
    partitions = {}
    offset = 0
    for split in SPLITS:
        for family in families[offset:offset + split_counts[split]]:
            partitions[family] = split
        offset += split_counts[split]
    ledger = []
    for root in sorted(root_families):
        family = root_families[root]
        for replicate in range(repeats):
            ledger.append({'episode': f'e{len(ledger):08d}', 'root': root,
                           'family': family, 'split': partitions[family],
                           'replicate': replicate,
                           'assigned_actions': [ACTIONS[rng.randrange(3)] for _ in range(2)]})
    design = {'schema': 'two-decision-development-design-v1',
              'status': 'proposal-only', 'collection_released': False,
              'incomplete_training_rule': 'abort-fit-on-any-incomplete-assignment',
              'artifact_representation': 'raw-utf8-assistant-response-as-program',
              'seed': seed, 'repeats': repeats, 'pins': copy.deepcopy(pins),
              'root_families': dict(sorted(root_families.items())),
              'root_prefix_sha256': dict(sorted(root_prefix_sha256.items())),
              'family_splits': dict(sorted(partitions.items())),
              'probabilities': [1 / 3] * 3, 'horizon': 2,
              'ledger': ledger, 'max_receiver_calls': 3 * len(ledger)}
    design['config_sha256'] = sha256(design)
    return design


def _design(design):
    if type(design) is not dict or 'config_sha256' not in design:
        raise ValueError('design schema')
    body = {k: v for k, v in design.items() if k != 'config_sha256'}
    if sha256(body) != design['config_sha256']:
        raise ValueError('design hash drift')
    if design['status'] != 'proposal-only' or design['collection_released'] is not False:
        raise ValueError('this contract cannot release collection')
    counts = {s: sum(v == s for v in design['family_splits'].values()) for s in SPLITS}
    expected = make_design(design['root_families'], counts, repeats=design['repeats'],
                           seed=design['seed'], pins=design['pins'],
                           root_prefix_sha256=design['root_prefix_sha256'])
    if design != expected:
        raise ValueError('design does not reproduce frozen assignment')


def _view(design, view, turn):
    v = public_view(view)
    if len(v['public_observations']) != turn + 1 or v['remaining_calls'] != 2 - turn:
        raise ValueError('decision stage mismatch')
    if v['public_observations'][-1]['message_index'] != len(v['messages']) - 1:
        raise ValueError('latest public check must refer to latest receiver answer')
    if [a['id'] for a in v['slate']] != list(ACTIONS):
        raise ValueError('supported action slate drift')
    if v['slate'][0]['kind'] != 'STOP' or any(
        a['kind'] != 'PROMPT' or a['calls_required'] != 1 for a in v['slate'][1:]
    ):
        raise ValueError('one receiver call per continuation')
    if (v['receiver_sha256'] != design['pins']['receiver'] or
            v['generator_sha256'] != design['pins']['generator'] or
            any(o['observer_sha256'] != design['pins']['public_observer']
                for o in v['public_observations'])):
        raise ValueError('view version drift')
    return v


def bind_assignment(design, episode, view, turn):
    """Bind the realized pre-action history/slate to its hidden ledger draw."""
    _design(design)
    if type(turn) is not int or turn not in (0, 1):
        raise ValueError('turn')
    rows = [r for r in design['ledger'] if r['episode'] == episode]
    if len(rows) != 1:
        raise ValueError('unassigned episode')
    v = _view(design, view, turn)
    if turn == 0 and sha256(v['messages'][:-1]) != design['root_prefix_sha256'][rows[0]['root']]:
        raise ValueError('frozen root prompt prefix drift')
    return bind_selection(v, design['probabilities'],
                          rows[0]['assigned_actions'][turn])


def _costs(costs, *, steps, termination):
    if type(costs) is not list:
        raise ValueError('cost ledger')
    totals = {k: 0 for k in ('calls', 'input_tokens', 'completion_tokens',
                            'elapsed_seconds', 'usd')}
    energy = 0.0
    energy_missing = False
    receiver_stages = []
    events = set()
    for c in costs:
        if type(c) is not dict or set(c) != COST_FIELDS:
            raise ValueError('separate cost units required')
        if c['component'] not in COMPONENTS or c['stage'] not in ('initial', '0', '1', 'final'):
            raise ValueError('cost source/stage')
        for k in totals:
            _number(c[k], k, integer=k in ('calls', 'input_tokens', 'completion_tokens'))
            totals[k] += c[k]
        if c['energy_joules'] is None:
            energy_missing = True
        else:
            _number(c['energy_joules'], 'energy_joules')
            energy += c['energy_joules']
        stage = c['stage']
        component = c['component']
        if (stage, component) in events:
            raise ValueError('duplicate cost component/stage')
        events.add((stage, component))
        if component == 'receiver':
            if stage == 'final' or c['calls'] != 1 or stage in receiver_stages:
                raise ValueError('receiver call identity/count')
            receiver_stages.append(stage)
        elif c['calls'] and component not in ('generator', 'critic'):
            raise ValueError('checks are not model calls')
        if stage == 'final' and component != 'private_check':
            raise ValueError('only private measurement after termination')
        if stage in ('0', '1'):
            t = int(stage)
            if t >= len(steps):
                raise ValueError('cost after unobserved decision')
            if steps[t]['selection']['chosen_id'] == 'STOP' and component == 'receiver':
                raise ValueError('receiver call after STOP')
    # Attempt costs include failed service calls; UNATTEMPTED consumes no call.
    if termination == 'UNATTEMPTED':
        if receiver_stages:
            raise ValueError('unattempted receiver call')
    elif 'initial' not in receiver_stages:
        raise ValueError('initial deployment call cost absent')
    for t, step in enumerate(steps):
        if any((str(t), c) not in events for c in ('generator', 'critic', 'public_check')):
            raise ValueError('explicit predecision generation/selection/check costs required')
        attempted = step['response_status'] in ('RETURNED', 'SERVICE_MISSING')
        if (str(t) in receiver_stages) != attempted:
            raise ValueError('continuation call cost mismatch')
    totals['energy_joules'] = None if energy_missing else energy
    totals['known_energy_joules'] = energy
    totals['energy_complete'] = not energy_missing
    return totals


def reconcile(design, receipts, *, splits=SPLITS):
    """Retain every assignment, including unavailable outcomes and failed calls.

    Receipts contain sanitized grade values/digests, never private case content.
    Prefix integrity is checked on executed public histories. Missingness bounds
    below are completion envelopes on the supplied frame, not confidence bounds.
    """
    _design(design)
    if not splits or set(splits) - set(SPLITS):
        raise ValueError('requested splits')
    expected = {r['episode']: r for r in design['ledger'] if r['split'] in splits}
    if type(receipts) is not list or len(receipts) != len(expected):
        raise ValueError('all assigned receipts required')
    seen = set()
    rows = []
    for e in receipts:
        fields = {'episode', 'root', 'family', 'split', 'config_sha256', 'initial_sha256',
                  'steps', 'termination', 'final_sha256', 'outcome', 'costs'}
        if type(e) is not dict or set(e) != fields:
            raise ValueError('receipt exact schema')
        identity = e['episode']
        if identity not in expected or identity in seen:
            raise ValueError('duplicate/unassigned receipt')
        seen.add(identity)
        assignment = expected[identity]
        if any(e[k] != assignment[k] for k in ('root', 'family', 'split')):
            raise ValueError('root/family/split drift')
        if e['config_sha256'] != design['config_sha256']:
            raise ValueError('receipt config drift')
        steps = e['steps']
        if type(steps) is not list or len(steps) > 2:
            raise ValueError('two-decision history')
        initial = e['initial_sha256']
        last_answer = initial
        if initial is not None:
            digest(initial)
        for t, step in enumerate(steps):
            if type(step) is not dict or set(step) != {'view', 'selection',
                                                     'response_status', 'response_sha256'}:
                raise ValueError('step exact schema')
            v = _view(design, step['view'], t)
            if t == 0 and sha256(v['messages'][:-1]) != design['root_prefix_sha256'][e['root']]:
                raise ValueError('frozen root prompt prefix drift')
            if answer_sha256(v['messages'][-1]['content']) != last_answer:
                raise ValueError('answer hash/prefix mismatch')
            if step['selection'] != bind_selection(v, design['probabilities'], assignment['assigned_actions'][t]):
                raise ValueError('logged selection differs from frozen draw')
            if t:
                prev = steps[t - 1]
                old = prev['view']['messages']
                new = v['messages']
                selected = prev['selection']['chosen_id']
                prompt = next(a['text'] for a in prev['view']['slate'] if a['id'] == selected)
                if (prev['response_status'] != 'RETURNED' or selected == 'STOP' or
                        new[:len(old)] != old or len(new) != len(old) + 2 or
                        new[-2] != {'role': 'user', 'content': prompt} or
                        v['public_observations'][:-1] != prev['view']['public_observations']):
                    raise ValueError('continuation/prefix or post-STOP drift')
            status = step['response_status']
            chosen = step['selection']['chosen_id']
            if chosen == 'STOP':
                if status != 'STOP' or step['response_sha256'] is not None or t != len(steps) - 1:
                    raise ValueError('absorbing STOP')
            else:
                if status not in ('RETURNED', 'SERVICE_MISSING', 'UNATTEMPTED'):
                    raise ValueError('continuation response status')
                if status == 'RETURNED':
                    digest(step['response_sha256'])
                    last_answer = step['response_sha256']
                elif step['response_sha256'] is not None or t != len(steps) - 1:
                    raise ValueError('service missing prefix')
        termination = e['termination']
        if termination == 'STOP':
            ok = bool(steps) and steps[-1]['response_status'] == 'STOP'
        elif termination == 'HORIZON':
            ok = len(steps) == 2 and steps[-1]['response_status'] == 'RETURNED'
        elif termination == 'SERVICE_MISSING':
            ok = (not steps and initial is None) or (bool(steps) and steps[-1]['response_status'] == 'SERVICE_MISSING')
        elif termination == 'BUDGET_MISSING':
            ok = bool(steps) and steps[-1]['response_status'] == 'UNATTEMPTED'
        elif termination == 'UNATTEMPTED':
            ok = not steps and initial is None
        else:
            ok = False
        if not ok or e['final_sha256'] != last_answer:
            raise ValueError('terminal state/final answer')
        outcome = e['outcome']
        if type(outcome) is not dict or set(outcome) != {'status', 'value', 'reason', 'instrument_sha256',
                                                                'artifact_sha256', 'grade_receipt_sha256'}:
            raise ValueError('source-separated outcome schema')
        if outcome['instrument_sha256'] != design['pins']['private_observer']:
            raise ValueError('private observer drift')
        if outcome['artifact_sha256'] != e['final_sha256']:
            raise ValueError('grade does not bind the exact final artifact')
        if outcome['grade_receipt_sha256'] is not None:
            digest(outcome['grade_receipt_sha256'])
        if outcome['status'] == 'OBSERVED':
            if e['final_sha256'] is None or outcome['grade_receipt_sha256'] is None:
                raise ValueError('observed quality requires an artifact-bound grade receipt')
            _number(outcome['value'], 'observed quality', upper=1)
            if outcome['reason'] is not None:
                raise ValueError('observed outcome has no missingness reason')
            bounds = (outcome['value'], outcome['value'])
        elif outcome['status'] == 'UNAVAILABLE' and outcome['value'] is None:
            _text(outcome['reason'], 'explicit unavailable outcome reason')
            bounds = (0., 1.)
        else:
            raise ValueError('missing quality is not STOP or zero')
        totals = _costs(e['costs'], steps=steps, termination=termination)
        if outcome['status'] == 'OBSERVED' and not any(
            c['stage'] == 'final' and c['component'] == 'private_check' for c in e['costs']
        ):
            raise ValueError('private measurement cost receipt absent')
        rows.append({'episode': identity, 'root': e['root'], 'family': e['family'],
                     'split': e['split'], 'quality_bounds': list(bounds), 'costs': totals})
    roots_per_family = {}
    for r in expected.values():
        roots_per_family.setdefault((r['split'], r['family']), set()).add(r['root'])
    families_per_split = {s: {r['family'] for r in expected.values() if r['split'] == s} for s in splits}
    for row in rows:
        row['weight'] = 1 / (len(families_per_split[row['split']]) *
                             len(roots_per_family[(row['split'], row['family'])]) * design['repeats'])
    support = {}
    for s in splits:
        support[s] = []
        for t in range(2):
            cells = {}
            for a in ACTIONS:
                active = [e for e in receipts if e['split'] == s and t < len(e['steps'])
                          and e['steps'][t]['selection']['chosen_id'] == a]
                cells[a] = {'trajectories': len(active),
                            'roots': len({e['root'] for e in active}),
                            'families': len({e['family'] for e in active})}
            support[s].append(cells)
    return {'config_sha256': design['config_sha256'], 'receipt_sha256': sha256(receipts),
            'rows': rows, 'split_completion_envelopes': {
                s: [sum(r['weight'] * r['quality_bounds'][j] for r in rows if r['split'] == s)
                    for j in (0, 1)] for s in splits},
            'assigned': len(expected), 'unavailable': sum(e['outcome']['status'] == 'UNAVAILABLE' for e in receipts),
            'stage_action_support': support, 'minimum_logged_probability': 1 / 3,
            'maximum_two_decision_inverse_probability': 9.}


def learner_rows(design, receipts, *, split):
    """Export complete rows only after refusing any assigned missing trajectory.

    This is deliberately not an implicit complete-case fit. A missing-data
    learner/estimand needs its own prospective protocol. Exported rows omit costs;
    current text Q optimizes quality, so this does not create a cost-aware policy.
    """
    if split not in ('train', 'tune'):
        raise ValueError('evaluation labels require a locked policy')
    result = reconcile(design, receipts, splits=(split,))
    if result['unavailable'] or any(e['termination'] not in ('STOP', 'HORIZON') for e in receipts):
        raise ValueError('incomplete assigned trajectories: no implicit complete-case learning')
    rows = [{'episode': e['episode'], 'family': e['family'],
             'steps': [{'view': step['view'], 'selection': step['selection']} for step in e['steps']],
             'outcome': e['outcome']['value']} for e in receipts]
    validate(rows)
    return copy.deepcopy(rows)


def weighted_learner_bundle(design, receipts, *, split):
    """Explicit equal-family/root weights for the versioned weighted Q fit.

    This is still a quality-only fit. Returning cost accounting or positive
    weights does not prove sufficient overlap, a correct crosswalk, or a policy
    benefit. All-assigned/complete-trajectory refusals are inherited unchanged.
    """
    episodes = learner_rows(design, receipts, split=split)
    reconciled = reconcile(design, receipts, splits=(split,))
    return {'episodes': episodes,
            'sample_weights': {row['episode']: Fraction(1,
                len({f for f, s in design['family_splits'].items() if s == split}) *
                sum(f == row['family'] for f in design['root_families'].values()) *
                design['repeats']) for row in reconciled['rows']},
            'config_sha256': design['config_sha256'],
            'receipt_sha256': reconciled['receipt_sha256']}


def policy_lock(design, development_receipts, *, policy_sha256, freeze_commit):
    """Bind a declared policy artifact before held-out outcomes are consumed.

    This validates only the lock record. Caller must verify the real artifact,
    commit chronology, fit provenance and training adequacy before execution.
    """
    digest(policy_sha256)
    if type(freeze_commit) is not str or len(freeze_commit) != 40 or any(c not in '0123456789abcdef' for c in freeze_commit):
        raise ValueError('committed policy freeze required')
    result = reconcile(design, development_receipts, splits=('train', 'tune'))
    return {'schema': 'policy-lock-v1', 'config_sha256': design['config_sha256'],
            'policy_sha256': policy_sha256, 'freeze_commit': freeze_commit,
            'development_receipt_sha256': result['receipt_sha256'],
            'development_families': sorted(f for f, s in design['family_splits'].items() if s != 'evaluation'),
            'evaluation_assignment_sha256': sha256([r for r in design['ledger'] if r['split'] == 'evaluation'])}


def evaluation_rows(design, receipts, lock):
    """Validate one predeclared lock and retain all held-out assigned outcomes."""
    _design(design)
    if type(lock) is not dict or set(lock) != {'schema', 'config_sha256', 'policy_sha256',
            'freeze_commit', 'development_receipt_sha256', 'development_families',
            'evaluation_assignment_sha256'}:
        raise ValueError('exact policy lock required')
    for k in ('policy_sha256', 'development_receipt_sha256', 'evaluation_assignment_sha256'):
        digest(lock[k])
    families = sorted(f for f, s in design['family_splits'].items() if s != 'evaluation')
    if (lock['schema'] != 'policy-lock-v1' or lock['config_sha256'] != design['config_sha256'] or
            lock['development_families'] != families or
            lock['evaluation_assignment_sha256'] != sha256([r for r in design['ledger'] if r['split'] == 'evaluation'])):
        raise ValueError('policy family/assignment lock drift')
    if type(lock['freeze_commit']) is not str or len(lock['freeze_commit']) != 40 or any(c not in '0123456789abcdef' for c in lock['freeze_commit']):
        raise ValueError('policy freeze commit')
    return reconcile(design, receipts, splits=('evaluation',))
