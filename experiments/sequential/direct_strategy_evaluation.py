"""Pure prospective ledger/analysis for direct complete-strategy deployment.

This is distinct from behavior-logger OPE. It binds declared sources, policy
artifacts and assignment accounting, not actual tuning pedigree, target
admission, semantic measurement validity or independent fresh execution.
No collector, selector, model, candidate, reference or network is invoked.
"""
import copy
from fractions import Fraction
import math

from experiments.prompt_choice.paired_inference import CONTRASTS, policy_contrast_bounds, serialize
from experiments.prompt_choice import census_inference_v1 as census
from experiments.sequential.development_design import sha256
from experiments.sequential.public_history import digest

COMPONENTS = ('receiver', 'generator', 'critic', 'publiccheck', 'selection', 'privatecheck')
METRICS = ('calls', 'input_tokens', 'completion_tokens', 'elapsed_seconds', 'usd', 'energy_joules')
CAP_METRICS = METRICS[:-1]
KINDS = ('learned', 'fixed', 'heuristic', 'resampling', 'adaptation')
VERSIONS = ('receiver_sha256', 'observer_sha256', 'endpoint_sha256', 'execution_law_sha256')


def _text(value, label):
    if type(value) is not str or not value:
        raise ValueError(label)


def _commit(value):
    if type(value) is not str or len(value) != 40 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('committed development-only strategy/choice lock required')


def _number(value, label, integer=False):
    if type(value) not in ((int,) if integer else (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(label)
    return Fraction(str(value))


def _exact(value):
    if type(value) in (int, Fraction):
        return Fraction(value)
    if (type(value) is dict and set(value) == {'num', 'den'} and
            type(value['num']) is int and type(value['den']) is int and value['den'] > 0):
        return Fraction(value['num'], value['den'])
    raise ValueError('exact rational grade interval required; floats/booleans refused')


def _caps(caps):
    if type(caps) is not dict or set(caps) != set(CAP_METRICS):
        raise ValueError('finite calls/tokens/latency/USD caps required')
    for k, v in caps.items():
        _number(v, 'budget cap', integer=k in ('calls', 'input_tokens', 'completion_tokens'))
    if caps['calls'] < 1 or caps['usd'] != 0:
        raise ValueError('initial call and zero paid-spend envelope required')


def make_design(family_roots, root_source_sha256, *, replicates, strategies, learned_id,
                baseline_ids, versions, choice_lock, common_caps, physical_caps,
                inference, shared_initial=True):
    """Materialize a direct prospective assignment; choose no strategy here.

    Caller supplies the whole roster and explicitly selected B1/B2 from frozen
    development decisions. Same common information-access contract is required;
    declared strategies can use different subsets/context within that contract.
    Equal budget ceilings include initial/generator/critic/selection costs.
    """
    if type(family_roots) is not dict or not family_roots:
        raise ValueError('fixed family/root census')
    roots = []
    for f, rs in family_roots.items():
        _text(f, 'family')
        if type(rs) is not list or not rs or rs != sorted(set(rs)):
            raise ValueError('nonempty sorted unique roots within family')
        for r in rs:
            _text(r, 'root')
        roots += rs
    if len(roots) != len(set(roots)):
        raise ValueError('root crosses declared families')
    if type(root_source_sha256) is not dict or set(root_source_sha256) != set(roots):
        raise ValueError('every root needs its source contract hash')
    for value in root_source_sha256.values():
        digest(value)
    if type(replicates) is not int or replicates < 1 or type(shared_initial) is not bool:
        raise ValueError('balanced fresh repetitions and start-sharing law')
    if type(versions) is not dict or set(versions) != set(VERSIONS):
        raise ValueError('fixed receiver/outcome/execution-law pins')
    for value in versions.values():
        digest(value)
    _caps(common_caps); _caps(physical_caps)
    if type(inference) is not dict or set(inference) != {'method', 'alpha', 'useful_gain'}:
        raise ValueError('prospectively pinned inference specification required')
    if (inference['method'] != census.VERSION or not 0 < _exact(inference['alpha']) < 1 or
            _exact(inference['useful_gain']) != Fraction(1, 20)):
        raise ValueError('fixed census inference/five-point usefulness rule')
    inference = {'method': census.VERSION, 'alpha': serialize(_exact(inference['alpha'])),
                 'useful_gain': serialize(_exact(inference['useful_gain']))}
    if type(choice_lock) is not dict or set(choice_lock) != {'freeze_commit', 'development_manifest_sha256', 'selected_on'}:
        raise ValueError('prospective comparator choice lock')
    _commit(choice_lock['freeze_commit']); digest(choice_lock['development_manifest_sha256'])
    if choice_lock['selected_on'] != 'development-only':
        raise ValueError('evaluation-selected comparator choice refused')
    if type(strategies) is not list or len(strategies) < 3:
        raise ValueError('entire frozen strategy roster')
    ids = []
    access = set()
    for s in strategies:
        if type(s) is not dict or set(s) != {'id', 'kind', 'source_sha256', 'artifact_sha256',
                'information_access_sha256', 'freeze_commit', 'development_manifest_sha256', 'fallback', 'caps'}:
            raise ValueError('strategy exact schema')
        _text(s['id'], 'strategy ID')
        if s['kind'] not in KINDS or s['fallback'] not in ('none', 'last-valid-initial'):
            raise ValueError('strategy kind/frozen deployment fallback')
        for key in ('source_sha256', 'artifact_sha256', 'information_access_sha256', 'development_manifest_sha256'):
            digest(s[key])
        _commit(s['freeze_commit']); _caps(s['caps'])
        if s['development_manifest_sha256'] != choice_lock['development_manifest_sha256']:
            raise ValueError('strategy development information differs from comparator choice lock')
        if s['caps'] != common_caps:
            raise ValueError('common complete-deployment budget ceiling required')
        access.add(s['information_access_sha256'])
        ids.append(s['id'])
    if len(set(ids)) != len(ids) or len(access) != 1:
        raise ValueError('strategy identity/information-access parity')
    if (type(baseline_ids) is not list or len(baseline_ids) != 2 or
            len(set(baseline_ids)) != 2 or learned_id in baseline_ids or
            any(s not in ids for s in [learned_id] + baseline_ids) or
            next(s['kind'] for s in strategies if s['id'] == learned_id) != 'learned'):
        raise ValueError('explicit learned policy and distinct B1/B2 required')
    ledger, initials = [], []
    for f in sorted(family_roots):
        for r in family_roots[f]:
            for repeat in range(replicates):
                groups = ['shared'] if shared_initial else ids
                start_ids = {}
                for group in groups:
                    iid = 'initial-' + sha256([f, r, repeat, group])
                    initials.append({'initial_execution_id': iid, 'family_id': f,
                                     'root': r, 'replicate': repeat})
                    for sid in ids if shared_initial else [group]:
                        start_ids[sid] = iid
                for sid in ids:
                    ledger.append({'assignment_id': 'strategy-' + sha256([f, r, repeat, sid]),
                                   'family_id': f, 'root': r, 'replicate': repeat,
                                   'strategy_id': sid, 'initial_execution_id': start_ids[sid]})
    design = {'schema': 'direct-strategy-evaluation-v1', 'status': 'proposal-only',
              'collection_released': False, 'family_roots': dict(sorted(family_roots.items())),
              'root_source_sha256': dict(sorted(root_source_sha256.items())),
              'replicates': replicates, 'strategies': copy.deepcopy(strategies),
              'learned_id': learned_id, 'baseline_ids': list(baseline_ids),
              'versions': dict(versions), 'choice_lock': dict(choice_lock),
              'common_caps': dict(common_caps), 'physical_caps': dict(physical_caps),
              'inference': inference,
              'shared_initial': shared_initial, 'horizon': 2,
              'initial_ledger': initials, 'ledger': ledger}
    design['config_sha256'] = sha256(design)
    return design


def _design(d):
    if type(d) is not dict or 'config_sha256' not in d:
        raise ValueError('direct design')
    if sha256({k: v for k, v in d.items() if k != 'config_sha256'}) != d['config_sha256']:
        raise ValueError('direct design hash drift')
    rebuilt = make_design(d['family_roots'], d['root_source_sha256'],
        replicates=d['replicates'], strategies=d['strategies'], learned_id=d['learned_id'],
        baseline_ids=d['baseline_ids'], versions=d['versions'], choice_lock=d['choice_lock'],
        common_caps=d['common_caps'], physical_caps=d['physical_caps'], inference=d['inference'],
        shared_initial=d['shared_initial'])
    if rebuilt != d:
        raise ValueError('direct assignment/law drift')


def _costs(events, stages, physical_ids):
    """Explicit zero/no-op records allowed; absent records are never zero."""
    if type(events) is not list:
        raise ValueError('complete separate cost ledger')
    expected = {(stage, c) for stage in stages for c in COMPONENTS}
    seen = set()
    totals = {k: Fraction(0) for k in METRICS}
    lower = {k: Fraction(0) for k in METRICS}
    for e in events:
        if type(e) is not dict or set(e) != {'physical_id', 'stage', 'component'} | set(METRICS):
            raise ValueError('cost event schema/units')
        key = (e['stage'], e['component'])
        if key not in expected or key in seen:
            raise ValueError('duplicate/unassigned cost component/stage')
        seen.add(key)
        _text(e['physical_id'], 'physical cost event ID')
        if e['physical_id'] in physical_ids:
            raise ValueError('physical operation reused across independent cost receipts')
        physical_ids.add(e['physical_id'])
        for k in METRICS:
            value = e[k]
            if value is None:
                if k == 'calls':
                    raise ValueError('actual call count required')
                totals[k] = None
            else:
                v = _number(value, k, integer=k in ('calls', 'input_tokens', 'completion_tokens'))
                lower[k] += v
                if totals[k] is not None:
                    totals[k] += v
        if e['component'] not in ('receiver', 'generator', 'critic') and e['calls'] != 0:
            raise ValueError('checks/selection are not model calls')
        if e['component'] == 'privatecheck' and e['stage'] != 'final' and any(e[k] != 0 for k in METRICS):
            raise ValueError('private grading is forbidden before deployment termination')
        if e['stage'] == 'final' and e['calls']:
            raise ValueError('model call after deployment termination')
    if seen != expected:
        raise ValueError('missing explicit cost component/stage receipt')
    totals['_known_lower_bounds'] = lower
    return totals


def _add(*totals):
    result = {k: None if any(t[k] is None for t in totals) else sum((t[k] for t in totals), Fraction(0))
              for k in METRICS}
    result['_known_lower_bounds'] = {
        k: sum((t['_known_lower_bounds'][k] for t in totals), Fraction(0)) for k in METRICS}
    return result


def _component_totals(events, *, measurement):
    """Private grading is physical evaluation overhead, not deployment input."""
    selected = [e for e in events if (e['component'] == 'privatecheck') == measurement]
    result = {k: (None if any(e[k] is None for e in selected) else sum(
        (_number(e[k], k, integer=k in ('calls', 'input_tokens', 'completion_tokens')) for e in selected), Fraction(0)))
              for k in METRICS}
    result['_known_lower_bounds'] = {k: sum(
        (_number(e[k], k, integer=k in ('calls', 'input_tokens', 'completion_tokens')) for e in selected if e[k] is not None), Fraction(0))
                                     for k in METRICS}
    return result


def _check_caps(totals, caps):
    verified = True
    for k in CAP_METRICS:
        if totals['_known_lower_bounds'][k] > _number(caps[k], 'cap'):
            raise ValueError('known deployment cost exceeds frozen ' + k + ' cap')
        if totals[k] is None:
            verified = False
        elif totals[k] > _number(caps[k], 'cap'):
            raise ValueError('actual deployment cost exceeds frozen ' + k + ' cap')
    return verified


def reconcile(design, initial_receipts, strategy_receipts, observations):
    """Return all-assigned direct contrasts/costs without executing strategies.

    Primitive sharing is explicit and allowed only inside the same root/vector
    for the exact artifact, source, observer and endpoint. Hash identity alone
    does not prove a legitimate shared grade; raw observer provenance remains
    necessary. Unavailable qualities retain [0,1]; configured operational
    fallback is reported separately from the failed raw continuation outcome.
    """
    _design(design)
    expected_initial = {r['initial_execution_id']: r for r in design['initial_ledger']}
    expected = {r['assignment_id']: r for r in design['ledger']}
    if (type(initial_receipts) is not list or type(strategy_receipts) is not list or
            len(initial_receipts) != len(expected_initial) or len(strategy_receipts) != len(expected)):
        raise ValueError('all assigned initial/strategy receipts required')
    physical_ids, initials, initial_costs, initial_physical_costs, measurement_costs = set(), {}, {}, {}, []
    for e in initial_receipts:
        fields = {'initial_execution_id', 'family_id', 'root', 'replicate', 'config_sha256',
                  'receiver_sha256', 'status', 'artifact_sha256', 'costs'}
        if type(e) is not dict or set(e) != fields:
            raise ValueError('initial exact schema')
        iid = e['initial_execution_id']
        if iid not in expected_initial or iid in initials:
            raise ValueError('duplicate/unassigned initial execution')
        if (any(e[k] != expected_initial[iid][k] for k in ('family_id', 'root', 'replicate')) or
                e['config_sha256'] != design['config_sha256'] or
                e['receiver_sha256'] != design['versions']['receiver_sha256']):
            raise ValueError('initial source/receiver/assignment drift')
        if e['status'] == 'RETURNED':
            digest(e['artifact_sha256'])
        elif e['status'] in ('SERVICE_MISSING', 'UNATTEMPTED') and e['artifact_sha256'] is None:
            pass
        else:
            raise ValueError('initial service missing is not an answer')
        costs = _costs(e['costs'], ('initial',), physical_ids)
        receiver_calls = next(c['calls'] for c in e['costs'] if c['component'] == 'receiver')
        if receiver_calls != (0 if e['status'] == 'UNATTEMPTED' else 1):
            raise ValueError('initial receiver attempt count')
        initials[iid] = e
        initial_physical_costs[iid] = costs
        initial_costs[iid] = _component_totals(e['costs'], measurement=False)
        measurement_costs.append(_component_totals(e['costs'], measurement=True))
    grades = {}
    if type(observations) is not list:
        raise ValueError('observation ledger')
    for o in observations:
        fields = {'primitive_id', 'family_id', 'root', 'replicate', 'artifact_sha256',
                  'root_source_sha256', 'observer_sha256', 'endpoint_sha256', 'status', 'reason', 'bounds'}
        if type(o) is not dict or set(o) != fields:
            raise ValueError('source-separated observation schema')
        pid = o['primitive_id']; _text(pid, 'primitive ID')
        if pid in grades:
            raise ValueError('duplicate/aliased primitive ID')
        for k in ('artifact_sha256', 'root_source_sha256', 'observer_sha256', 'endpoint_sha256'):
            digest(o[k])
        if type(o['bounds']) is not list or len(o['bounds']) != 2:
            raise ValueError('quality interval')
        lo, hi = map(_exact, o['bounds'])
        if not 0 <= lo <= hi <= 1:
            raise ValueError('quality in [0,1]')
        if o['status'] == 'UNAVAILABLE':
            _text(o['reason'], 'explicit unavailable observation reason')
        elif o['status'] == 'OBSERVED' and o['reason'] is not None:
            raise ValueError('observed grade has no missingness reason')
        if (o['status'] == 'OBSERVED' and lo == hi) or (o['status'] == 'UNAVAILABLE' and (lo, hi) == (0, 1)):
            grades[pid] = (o, lo, hi)
        else:
            raise ValueError('observed/missing outcome interval mismatch')
    used, rows, physical_strategy_costs, seen = set(), [], [], set()
    policies = {s['id']: s for s in design['strategies']}
    def grade(pid, artifact, assignment):
        if pid is None:
            if artifact is not None:
                raise ValueError('known artifact requires an observed/unavailable instrument receipt')
            return 'missing-' + assignment['assignment_id'], Fraction(0), Fraction(1)
        if pid not in grades or artifact is None:
            raise ValueError('undeclared score/grade without artifact')
        o, lo, hi = grades[pid]
        if (any(o[k] != assignment[k] for k in ('family_id', 'root', 'replicate')) or
                o['artifact_sha256'] != artifact or
                o['root_source_sha256'] != design['root_source_sha256'][assignment['root']] or
                any(o[k] != design['versions'][k] for k in ('observer_sha256', 'endpoint_sha256'))):
            raise ValueError('false primitive alias: source/artifact/observer/endpoint/vector differs')
        used.add(pid)
        return pid, lo, hi
    for e in strategy_receipts:
        fields = {'assignment_id', 'family_id', 'root', 'replicate', 'strategy_id', 'initial_execution_id',
                  'config_sha256', 'strategy_artifact_sha256', 'execution_status', 'raw_artifact_sha256',
                  'deployed_artifact_sha256', 'fallback_applied', 'raw_primitive_id', 'deployed_primitive_id',
                  'terminal_reason', 'terminal_stage', 'retained_artifact_sha256', 'failure_reason', 'costs'}
        if type(e) is not dict or set(e) != fields:
            raise ValueError('strategy exact schema')
        aid = e['assignment_id']
        if aid not in expected or aid in seen:
            raise ValueError('duplicate/unassigned strategy receipt')
        assignment = expected[aid]; seen.add(aid)
        if (any(e[k] != assignment[k] for k in assignment) or e['config_sha256'] != design['config_sha256'] or
                e['strategy_artifact_sha256'] != policies[e['strategy_id']]['artifact_sha256']):
            raise ValueError('strategy lock/assignment drift')
        initial = initials[e['initial_execution_id']]
        if type(e['fallback_applied']) is not bool:
            raise ValueError('explicit fallback application record')
        status = e['execution_status']
        terminal, stage = e['terminal_reason'], e['terminal_stage']
        if stage is not None and (type(stage) is not int or stage not in (0, 1)):
            raise ValueError('terminal decision stage')
        if status == 'COMPLETE':
            digest(e['raw_artifact_sha256'])
            if (initial['status'] != 'RETURNED' or e['fallback_applied'] or
                    e['deployed_artifact_sha256'] != e['raw_artifact_sha256'] or
                    e['deployed_primitive_id'] != e['raw_primitive_id']):
                raise ValueError('complete strategy must deploy its recorded selected artifact')
            if (terminal not in ('STOP', 'HORIZON') or stage is None or
                    (terminal == 'HORIZON' and stage != 1) or e['failure_reason'] is not None or
                    e['retained_artifact_sha256'] != e['raw_artifact_sha256'] or
                    (terminal == 'STOP' and stage == 0 and e['retained_artifact_sha256'] != initial['artifact_sha256'])):
                raise ValueError('completed STOP/horizon artifact state')
        elif status in ('SERVICE_MISSING', 'RESOURCE_STOP', 'UNATTEMPTED'):
            if e['raw_artifact_sha256'] is not None or e['raw_primitive_id'] is not None:
                raise ValueError('missing continuation is not an observed raw outcome')
            fallback = policies[e['strategy_id']]['fallback'] == 'last-valid-initial' and initial['status'] == 'RETURNED'
            if (e['fallback_applied'] != fallback or
                    e['deployed_artifact_sha256'] != (initial['artifact_sha256'] if fallback else None) or
                    (not fallback and e['deployed_primitive_id'] is not None)):
                raise ValueError('fallback must be prospectively configured and preserve the exact initial artifact')
            _text(e['failure_reason'], 'explicit failed/unattempted deployment reason')
            if terminal != status or e['retained_artifact_sha256'] != e['deployed_artifact_sha256']:
                raise ValueError('failed terminal/fallback state')
        else:
            raise ValueError('deployment status')
        costs = _costs(e['costs'], ('0', '1', 'final'), physical_ids)
        for cost in e['costs']:
            if cost['stage'] in ('0', '1'):
                t = int(cost['stage'])
                if stage is None or t > stage:
                    if any(cost[k] != 0 for k in METRICS):
                        raise ValueError('nonzero/unknown operation after absorbing termination')
                if terminal == 'STOP' and t == stage and cost['component'] == 'receiver' and cost['calls']:
                    raise ValueError('receiver call after STOP')
        if initial['status'] != 'RETURNED' and costs['calls']:
            raise ValueError('continuation after missing initial answer')
        if status == 'UNATTEMPTED' and costs['calls']:
            raise ValueError('unattempted strategy has model calls')
        continuation_cost = _component_totals(e['costs'], measurement=False)
        measurement_cost = _component_totals(e['costs'], measurement=True)
        measurement_costs.append(measurement_cost)
        logical = _add(initial_costs[e['initial_execution_id']], continuation_cost)
        verified = _check_caps(logical, policies[e['strategy_id']]['caps'])
        physical_strategy_costs.append(costs)
        raw = grade(e['raw_primitive_id'], e['raw_artifact_sha256'], assignment)
        deployed = grade(e['deployed_primitive_id'], e['deployed_artifact_sha256'], assignment)
        # Raw absence and deployed absence have identical boxes but remain
        # separately labeled whenever a fallback was deployed.
        rows.append(dict(assignment, raw_quality={'primitive_id': raw[0], 'bounds': [serialize(raw[1]), serialize(raw[2])]},
                         deployed_quality={'primitive_id': deployed[0], 'bounds': [serialize(deployed[1]), serialize(deployed[2])]},
                         raw_artifact_sha256=e['raw_artifact_sha256'], deployed_artifact_sha256=e['deployed_artifact_sha256'],
                         terminal_reason=terminal, terminal_stage=stage, failure_reason=e['failure_reason'],
                         execution_status=status, fallback_applied=e['fallback_applied'], logical_costs=logical,
                         continuation_costs=continuation_cost, private_measurement_costs=measurement_cost,
                         resource_caps_verified=verified))
        rows[-1]['equal_family_root_repetition_weight'] = serialize(Fraction(
            1, len(design['family_roots']) * len(design['family_roots'][assignment['family_id']]) * design['replicates']))
    if set(grades) != used:
        raise ValueError('unreferenced private observations refused')
    physical = _add(*initial_physical_costs.values(), *physical_strategy_costs)
    physical_measurement = _add(*measurement_costs)
    physical_verified = _check_caps(physical, design['physical_caps'])
    census_rows = []
    for f, roots in design['family_roots'].items():
        for repeat in range(design['replicates']):
            unit = [r for r in rows if r['family_id'] == f and r['replicate'] == repeat]
            bounds = {}
            for contrast, baseline in zip(CONTRASTS, design['baseline_ids']):
                primitives, plus, minus = {}, [], []
                for row in unit:
                    if row['strategy_id'] not in (design['learned_id'], baseline):
                        continue
                    score = row['deployed_quality']; pid = score['primitive_id']
                    box = tuple(_exact(x) for x in score['bounds'])
                    if pid in primitives and primitives[pid] != box:
                        raise ValueError('shared primitive inconsistent observation interval')
                    primitives[pid] = box
                    side = plus if row['strategy_id'] == design['learned_id'] else minus
                    side.append((pid, Fraction(1, len(roots))))
                lo, hi = policy_contrast_bounds(plus, minus, [(pid, *box) for pid, box in primitives.items()])
                bounds[contrast] = [serialize(lo), serialize(hi)]
            ids = sorted({r['initial_execution_id'] for r in unit})
            census_rows.append({'family_id': f, 'replicate': repeat,
                                'initial_execution_id': 'vector-' + sha256(ids), 'bounds': bounds})
    # Ensure numeric cost summaries are exact, serializable and distinguish
    # unknown telemetry from known zero. Summed durations are not queue/wall time.
    def cost_json(t):
        return {**{k: None if t[k] is None else serialize(t[k]) for k in METRICS},
                'known_lower_bounds': {k: serialize(v) for k, v in t['_known_lower_bounds'].items()}}
    strategy_summary = {}
    for sid in policies:
        selected = [r for r in rows if r['strategy_id'] == sid]
        mean = {k: (None if any(r['logical_costs'][k] is None for r in selected) else sum(
            (_exact(r['equal_family_root_repetition_weight']) * r['logical_costs'][k] for r in selected), Fraction(0)))
                for k in METRICS}
        mean['_known_lower_bounds'] = {k: sum(
            (_exact(r['equal_family_root_repetition_weight']) * r['logical_costs']['_known_lower_bounds'][k] for r in selected), Fraction(0))
                                      for k in METRICS}
        strategy_summary[sid] = {'assigned_rows': len(selected), 'roots': len({r['root'] for r in selected}),
            'fallback_rows': sum(r['fallback_applied'] for r in selected),
            'raw_unavailable_rows': sum(_exact(r['raw_quality']['bounds'][0]) != _exact(r['raw_quality']['bounds'][1]) for r in selected),
            'deployed_unavailable_rows': sum(_exact(r['deployed_quality']['bounds'][0]) != _exact(r['deployed_quality']['bounds'][1]) for r in selected),
            'execution_status_counts': {s: sum(r['execution_status'] == s for r in selected)
                                        for s in ('COMPLETE', 'SERVICE_MISSING', 'RESOURCE_STOP', 'UNATTEMPTED')},
            'logical_cost_total': cost_json(_add(*(r['logical_costs'] for r in selected))),
            'equal_family_mean_logical_cost': cost_json(mean)}
    for row in rows:
        row['logical_costs'] = cost_json(row['logical_costs'])
        row['continuation_costs'] = cost_json(row['continuation_costs'])
        row['private_measurement_costs'] = cost_json(row['private_measurement_costs'])
    result = {'schema': 'direct-strategy-reconciliation-v1', 'config_sha256': design['config_sha256'],
            'n_families': len(design['family_roots']), 'replicates_per_family': design['replicates'],
            'n_roots': len(design['root_source_sha256']), 'roots_per_family': {f: len(rs) for f, rs in design['family_roots'].items()},
            'n_strategies': len(policies), 'n_assigned_strategy_rows': len(rows),
            'n_fresh_initial_assignments': len(initials),
            'initial_status_counts': {s: sum(e['status'] == s for e in initials.values())
                                     for s in ('RETURNED', 'SERVICE_MISSING', 'UNATTEMPTED')},
            'n_assigned_execution_vectors': len(census_rows),
            'strategy_summary': strategy_summary, 'rows': rows, 'census_rows': census_rows,
            'physical_costs': cost_json(physical), 'physical_caps_verified': physical_verified,
            'physical_private_measurement_costs': cost_json(physical_measurement),
            'all_logical_caps_verified': all(r['resource_caps_verified'] for r in rows),
            'cost_benefit_claim_permitted': False,
            'complete_cost_telemetry': all(physical[k] is not None for k in METRICS),
            'scope': 'conditional-finite-family-census', 'admitted_families': 0,
            'limits': 'IDs/hashes do not certify fresh execution, independence, tuning pedigree or measurement; '
                      'latency is summed operation duration, not total job wall/queue time; no cost-benefit inference performed'}
    def normalized(value):
        if type(value) is Fraction:
            return serialize(value)
        if type(value) is list:
            return [normalized(v) for v in value]
        if type(value) is dict:
            return {k: normalized(v) for k, v in value.items()}
        return value
    result['input_ledger_sha256'] = sha256(normalized({
        'initial_receipts': initial_receipts, 'strategy_receipts': strategy_receipts, 'observations': observations}))
    result['reconciliation_sha256'] = sha256(result)
    return result


def census_bundle(design, reconciliation, *, alpha=None):
    """Bind exact direct family-repetition contrasts to the new census adapter."""
    _design(design)
    if reconciliation['config_sha256'] != design['config_sha256']:
        raise ValueError('reconciliation design drift')
    if sha256({k: v for k, v in reconciliation.items() if k != 'reconciliation_sha256'}) != reconciliation['reconciliation_sha256']:
        raise ValueError('reconciliation bound/accounting drift')
    value = _exact(design['inference']['alpha'])
    if alpha is not None and _exact(alpha) != value:
        raise ValueError('prospectively pinned alpha cannot change after reconciliation')
    plan = {'version': census.VERSION, 'scope': census.SCOPE,
            'family_ids': sorted(design['family_roots']), 'replicates': design['replicates'],
            'alpha': serialize(value), 'useful_gain': design['inference']['useful_gain'],
            'roster_sha256': sha256(design['family_roots']),
            'policies_sha256': sha256({'strategies': design['strategies'], 'learned_id': design['learned_id'],
                                      'baseline_ids': design['baseline_ids'], 'choice_lock': design['choice_lock']}),
            'execution_law_sha256': design['versions']['execution_law_sha256'],
            'receiver_sha256': design['versions']['receiver_sha256'],
            'observer_sha256': design['versions']['observer_sha256']}
    census.validate_plan(plan)
    rows = copy.deepcopy(reconciliation['census_rows'])
    for row in rows:
        row['bounds'] = {name: tuple(map(_exact, values)) for name, values in row['bounds'].items()}
    return {'plan': plan, 'rows': rows}
