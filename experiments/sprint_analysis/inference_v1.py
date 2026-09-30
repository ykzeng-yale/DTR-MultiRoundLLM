"""Frozen finite operational-census inference, without collection or fitting.

The existing outward sign-split KL arithmetic is classical concentration, not
a new theorem. This wrapper independently reconstructs every assigned vector.
Distinct identifiers do not prove random sampling, noninterference, valid
observation or policy-freeze chronology; those remain actual design/evidence
requirements. The target is the fixed publisher-battery roster, not broad task
families or all-input algorithmic correctness.
"""
import copy
import hashlib
import json
import math
from collections import Counter
from fractions import Fraction
from pathlib import Path

from experiments.prompt_choice import census_inference_v1 as census
from experiments.prompt_choice import paired_inference as paired
from experiments.sprint import learner_v1 as learner
from experiments.sprint import pipeline_v1 as pipeline

VERSION = 'sprint-complete-operational-census-inference-v1'
COMPONENTS = 110
REPLICATES = 32
STRATEGIES = ('FULL_HISTORY_Q', 'COMPRESSED_HISTORY_Q', 'B1_LOCKED',
              'RESAMPLE_SELECT', 'STOP', 'PATCH2', 'RETHINK2',
              'SELF_REFINE_ADAPT', 'REFLEXION_ADAPT')
PRIMARY = {'d_minus_b1': 'B1_LOCKED', 'd_minus_b2': 'RESAMPLE_SELECT'}
CONDITIONING_FIELDS = {'nonrandom_protocol_sha256', 'development_info_sha256',
                       'tuning_info_sha256', 'policies_lock_sha256'}
INTENDED_TERMINALS = {'STOP', 'HORIZON', 'SERVICE_TERMINAL'}
ADMIN_TERMINALS = {'RESOURCE_TERMINAL', 'UNATTEMPTED', 'SERVICE_MISSING'}


def digest(value):
    pipeline._digest(value)
    return value


def fraction_json(value):
    return {'num': value.numerator, 'den': value.denominator}


def policy_lock(config):
    return pipeline.sha({key: config[key] for key in
                         ('model_sha256s', 'selected_b1', 'choice_lock_sha256')})


def nonrandom_law(config):
    """Remove realized evaluation random draws, even when hashes are published.

    Roster/call-order identifiers are fixed design bookkeeping; receiver seeds,
    component nonces, assignment draws and their hashes are not conditioned on.
    Development/tuning information and the fitted policy lock are conditioned on.
    """
    excluded = {'randomization', 'randomization_sha256', 'config_sha256'}
    law = copy.deepcopy({k: v for k, v in config.items() if k not in excluded})
    law['initials'] = [{k: v for k, v in row.items() if k != 'seed'}
                       for row in law['initials']]
    law['ledger'] = [{k: v for k, v in row.items() if k not in ('seeds', 'actions')}
                     for row in law['ledger']]
    law['randomization_law'] = {'version': 'sprint-independent-vector-randomization-v1',
        'sampling': 'one independently sampled OS CSPRNG nonce per component-repetition after nonrandom freeze',
        'within_vector': 'fixed hashes derive receiver seeds; arbitrary within-vector dependence permitted'}
    return law


def _source_hashes():
    modules = {'analysis': __file__, 'census': census.__file__, 'paired': paired.__file__,
               'pipeline': pipeline.__file__, 'learner': learner.__file__}
    return {name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
            for name, path in modules.items()}


def _roster(config, tasks):
    pipeline.validate_config(config, tasks)
    if config['mode'] != 'evaluation' or config['repeats'] != REPLICATES:
        raise ValueError('frozen evaluation and32balanced repetitions required')
    if len(config['strategies']) != len(STRATEGIES) or set(config['strategies']) != set(STRATEGIES):
        raise ValueError('complete prospectively frozen nine-strategy roster required')
    expected_inference = {'method': census.VERSION, 'alpha': [1, 20],
        'useful_gain': [1, 20], 'primary_baseline_ids': list(PRIMARY.values())}
    if config['inference'] != expected_inference:
        raise ValueError('primary order/alpha/five-point inference drift')
    families = {}
    selected = {t['root']: t for t in tasks if t['split'] in ('eval', 'evaluation')}
    for root, task in selected.items():
        families.setdefault(task['family_id'], []).append(root)
    if len(families) != COMPONENTS:
        raise ValueError('frozen110operational components required; no subset analysis')
    families = {f: sorted(roots) for f, roots in sorted(families.items())}
    expected = {(f, root, rep, strategy) for f, roots in families.items()
                for root in roots for rep in range(REPLICATES) for strategy in STRATEGIES}
    identities = [(r['family_id'], r['root'], r['replicate'], r['strategy'])
                  for r in config['ledger']]
    if len(identities) != len(expected) or set(identities) != expected:
        raise ValueError('whole component/root/repetition/strategy assignment required')
    nonce_records = config['randomization']['component_replicate_nonces']
    if len({r['nonce_hex'] for r in nonce_records}) != len(nonce_records):
        raise ValueError('reused component nonce: preserve evidence, never relabel fresh draws')
    return families


def make_plan(config, tasks, *, conditioning):
    """Freeze before evaluation calls; no RNG, model/candidate execution or fit."""
    families = _roster(config, tasks)
    if type(conditioning) is not dict or set(conditioning) != CONDITIONING_FIELDS:
        raise ValueError('explicit pre-evaluation nonrandom conditioning pins required')
    for value in conditioning.values():
        digest(value)
    if conditioning['policies_lock_sha256'] != policy_lock(config):
        raise ValueError('conditioning policy lock differs from locked models/comparator')
    law_hash = pipeline.sha(nonrandom_law(config))
    roster_hash = pipeline.sha(families)
    census_plan = {'version': census.VERSION, 'scope': census.SCOPE,
        'family_ids': list(families), 'replicates': REPLICATES,
        'alpha': {'num': 1, 'den': 20}, 'useful_gain': {'num': 1, 'den': 20},
        'roster_sha256': roster_hash, 'execution_law_sha256': law_hash,
        'policies_sha256': policy_lock(config), 'receiver_sha256': config['pins']['receiver'],
        'observer_sha256': config['pins']['private_observer']}
    census.validate_plan(census_plan)
    plan = {'version': VERSION, 'classification': 'prospective finite-source operational quality test',
        'census_plan': census_plan, 'family_roots': families, 'strategies': list(STRATEGIES),
        'primary': dict(PRIMARY), 'conditioning': copy.deepcopy(conditioning),
        'conditioning_excludes': ['realized evaluation nonces', 'receiver seeds',
            'evaluation assignment/randomization-table hashes', 'evaluation outputs/outcomes'],
        'source_sha256s': _source_hashes(),
        'decision': {'useful_vs_b1': 'L1>1/20', 'excludes_five_points_vs_b1': 'U1<1/20',
                     'superior_vs_b2': 'L2>0', 'otherwise': 'inconclusive'},
        'secondary': 'full-minus-compressed and other strategies descriptive only; no selection/optional stopping',
        'model_calls': 0, 'candidate_executions': 0, 'fit_calls': 0,
        'administrative_censoring': 'unknown intended-policy outcome; retained fallback grade reported separately'}
    plan['plan_sha256'] = pipeline.sha(plan)
    return plan


def validate_plan(plan, config, tasks):
    if plan != make_plan(config, tasks, conditioning=plan['conditioning']):
        raise ValueError('frozen inference/source/roster/policy drift')


def _exact_grade(row, label, config):
    """Validate the actual primitive separately from intended-policy censoring."""
    raw, program = row['final_raw'], row['final_program']
    raw_sha = pipeline.text_sha(raw) if raw is not None else None
    program_sha = pipeline.text_sha(program) if program is not None else None
    expected = {'assignment_id': row['assignment_id'], 'grading_unit_id': row['initial_execution_id'],
        'root': row['root'], 'family_id': row['family_id'], 'config_sha256': config['config_sha256'],
        'raw_sha256': raw_sha, 'program_sha256': program_sha, 'extractor': pipeline.EXTRACTOR,
        'instrument_sha256': config['pins']['private_observer']}
    if any(label.get(k) != v for k, v in expected.items()):
        raise ValueError('grade source/artifact/vector/instrument binding drift')
    if program is not None and (raw is None or pipeline.extract_program(raw) != program):
        raise ValueError('raw response/extracted program drift')
    grade = label['grade']
    keys = {'status', 'value', 'reason', 'audit_sha256', 'primitive_id', 'elapsed_seconds', 'case_starts'}
    if type(grade) is not dict or set(grade) != keys:
        raise ValueError('complete sanitized primitive grade schema required')
    if type(grade['elapsed_seconds']) not in (int, float) or not math.isfinite(grade['elapsed_seconds']) or grade['elapsed_seconds'] < 0 or type(grade['case_starts']) is not int or grade['case_starts'] < 0:
        raise ValueError('unknown/invalid grading overhead cannot become zero')
    if raw is None:
        if grade != {'status': 'UNAVAILABLE', 'value': None, 'reason': 'missing_or_unextractable_program',
                'audit_sha256': None, 'primitive_id': None, 'elapsed_seconds': 0, 'case_starts': 0}:
            raise ValueError('no initial artifact cannot have an observed grade')
    else:
        artifact = program_sha if program is not None else raw_sha
        primitive = pipeline.primitive_id('private', row['initial_execution_id'], row['root'],
                                          artifact, config['pins']['private_observer'])
        if grade['primitive_id'] != primitive:
            raise ValueError('false shared grade primitive identity')
        digest(grade['audit_sha256'])
        if program is None:
            expected_audit = pipeline.sha({'extractor': pipeline.EXTRACTOR, 'raw_sha256': raw_sha,
                                           'disposition': 'malformed_artifact_fail_zero'})
            if grade['status'] != 'OBSERVED' or type(grade['value']) is not int or grade['value'] != 0 or grade['reason'] is not None or grade['audit_sha256'] != expected_audit or grade['case_starts'] != 0:
                raise ValueError('malformed artifact must preserve its prospective observed zero')
        elif grade['status'] == 'OBSERVED':
            if type(grade['value']) is not int or grade['value'] not in (0, 1) or grade['reason'] is not None:
                raise ValueError('observed operational binary grade required')
        elif grade['status'] == 'UNAVAILABLE':
            if grade['value'] is not None or type(grade['reason']) is not str or not grade['reason']:
                raise ValueError('unavailable primitive needs explicit reason')
        else:
            raise ValueError('unknown primitive status')
    disposition = row['disposition']
    if disposition not in INTENDED_TERMINALS | ADMIN_TERMINALS:
        raise ValueError('all assignments must be terminal, including administrative missingness')
    admin_reason = label.get('administrative_censoring_reason')
    if disposition == 'RESOURCE_TERMINAL':
        if type(row.get('censoring_reason')) is not str or not row['censoring_reason'] or admin_reason != row['censoring_reason']:
            raise ValueError('administrative terminal reason binding required')
    elif admin_reason is not None:
        raise ValueError('censoring reason inconsistent with terminal law')
    if disposition == 'SERVICE_TERMINAL':
        failed = [c['record'] for c in row['calls'] if c['record'] is not None and c['record'].get('status') != 'returned']
        if not failed or any(c.get('failure_kind') != 'isolated_service_failure' for c in failed):
            raise ValueError('fatal/administrative service failure cannot be observed intended-policy fallback')
    intended = disposition in INTENDED_TERMINALS
    actual = (Fraction(grade['value']), Fraction(grade['value'])) if grade['status'] == 'OBSERVED' else (Fraction(0), Fraction(1))
    bound = actual if intended else (Fraction(0), Fraction(1))
    return bound, actual, intended


def _same_primitive(a, b):
    row_a, label_a, _, _, intended_a = a
    row_b, label_b, _, _, intended_b = b
    same = (intended_a and intended_b and label_a['program_sha256'] is not None and
        all(label_a[k] == label_b[k] for k in ('root', 'grading_unit_id', 'program_sha256', 'instrument_sha256')) and
        label_a['grade']['primitive_id'] is not None and
        label_a['grade']['primitive_id'] == label_b['grade']['primitive_id'])
    if same and label_a['grade'] != label_b['grade']:
        raise ValueError('same primitive has inconsistent outcome/audit/overhead')
    return same


def contrast(a, b):
    if _same_primitive(a, b):
        return Fraction(0), Fraction(0)
    return a[2][0]-b[2][1], a[2][1]-b[2][0]


def reconcile(plan, state, joined, config, tasks):
    """Rebuild every balanced vector; no pipeline floating-average reuse."""
    validate_plan(plan, config, tasks)
    if state['config_sha256'] != config['config_sha256'] or state['phase'] != 3 or state['requests'] or joined['config_sha256'] != config['config_sha256'] or joined['state_sha256'] != pipeline.sha(state):
        raise ValueError('terminal state and full label join hashes required')
    models = state['models']
    if set(models) != {'FULL_HISTORY_Q', 'COMPRESSED_HISTORY_Q'}:
        raise ValueError('both actual prospectively locked models required')
    eval_families = set(plan['family_roots'])
    for sid, mode in (('FULL_HISTORY_Q', 'full'), ('COMPRESSED_HISTORY_Q', 'compressed')):
        model = models[sid]
        if learner.artifact_sha256(model) != config['model_sha256s'][sid] or model['version'] != learner.VERSION or model['mode'] != mode:
            raise ValueError('locked model artifact/mode drift')
        if tuple(model['versions']) != tuple(config['pins'][k] for k in ('receiver', 'generator', 'public_observer')):
            raise ValueError('locked model trained for different public receiver/generator/observer')
        coefficients = model['coefficients']
        if (type(coefficients) is not list or len(coefficients) != 2 or
                any(type(stage) is not list or len(stage) != 3 or
                    any(type(beta) is not list or len(beta) != learner.DIM or
                        any(type(x) not in (int, float) or not math.isfinite(x) for x in beta)
                        for beta in stage) for stage in coefficients)):
            raise ValueError('actual finite two-stage70feature fitted artifact required')
        if not model['training_families'] or eval_families & set(model['training_families']):
            raise ValueError('no evaluation-family fitting permitted')
    ledger = {r['assignment_id']: r for r in config['ledger']}
    rows = {r['assignment_id']: r for r in state['rows']}
    labels = {r['assignment_id']: r for r in joined['labels']}
    if len(rows) != len(state['rows']) or len(labels) != len(joined['labels']) or set(rows) != set(ledger) or set(labels) != set(ledger):
        raise ValueError('every assigned row and label retained exactly once')
    indexed, primitive_registry, counts = {}, {}, {s: Counter() for s in STRATEGIES}
    starts = {}
    for identity, assignment in ledger.items():
        row, label = rows[identity], labels[identity]
        if any(row.get(k) != v for k, v in assignment.items()) or pipeline.sha(row['base_messages']) != config['public_prefix_sha256'][row['root']]:
            raise ValueError('assignment or original public source prefix drift')
        bound, actual, intended = _exact_grade(row, label, config)
        grade = label['grade']; primitive = grade['primitive_id']
        if primitive is not None:
            evidence = (row['root'], label['grading_unit_id'], label['instrument_sha256'],
                        label['program_sha256'], label['raw_sha256'] if label['program_sha256'] is None else None, grade)
            if primitive in primitive_registry and primitive_registry[primitive] != evidence:
                raise ValueError('shared primitive source/outcome/audit contradiction')
            primitive_registry[primitive] = evidence
        key = (row['family_id'], row['root'], row['replicate'], row['strategy'])
        indexed[key] = (row, label, bound, actual, intended)
        start_key = key[:3]
        start = row['initial_execution_id']
        if start_key in starts and starts[start_key] != start:
            raise ValueError('matched strategies have different initial execution')
        starts[start_key] = start
        c = counts[row['strategy']]
        c['assigned'] += 1
        c['actual_'+('unavailable' if grade['status'] != 'OBSERVED' else 'pass' if grade['value'] else 'fail')] += 1
        c['intended_unavailable'] += bound != (bound[0], bound[0])
        c['administrative_terminal'] += not intended
        c['fallback'] += bool(row.get('fallback_applied'))
        c['termination_'+row['disposition']] += 1
    if len(set(starts.values())) != len(starts):
        raise ValueError('initial execution reused across roots or repetition vectors')
    vector_rows, exact_vectors, secondary = [], [], []
    aggregate = {name: [Fraction(0), Fraction(0)] for name in PRIMARY}
    qualities = {s: [Fraction(0), Fraction(0)] for s in STRATEGIES}
    actual_qualities = {s: [Fraction(0), Fraction(0)] for s in STRATEGIES}
    total = COMPONENTS*REPLICATES
    for family, roots in plan['family_roots'].items():
        weight = Fraction(1, len(roots))
        for rep in range(REPLICATES):
            initial_ids = sorted(starts[(family, root, rep)] for root in roots)
            vector_id = 'vector-'+pipeline.sha(initial_ids)
            bounds = {name: [Fraction(0), Fraction(0)] for name in PRIMARY}
            ablation = [Fraction(0), Fraction(0)]
            for root in roots:
                full = indexed[(family, root, rep, 'FULL_HISTORY_Q')]
                for name, comparator in PRIMARY.items():
                    pair = contrast(full, indexed[(family, root, rep, comparator)])
                    for j in (0, 1):
                        bounds[name][j] += weight*pair[j]
                pair = contrast(full, indexed[(family, root, rep, 'COMPRESSED_HISTORY_Q')])
                for j in (0, 1):
                    ablation[j] += weight*pair[j]
                for sid in STRATEGIES:
                    record = indexed[(family, root, rep, sid)]
                    for j in (0, 1):
                        qualities[sid][j] += record[2][j]*weight/total
                        actual_qualities[sid][j] += record[3][j]*weight/total
            vector_rows.append({'family_id': family, 'replicate': rep,
                'initial_execution_id': vector_id, 'bounds': {k: tuple(v) for k, v in bounds.items()}})
            exact_vectors.append({'family_id': family, 'replicate': rep, 'vector_id': vector_id,
                'root_initial_execution_ids': initial_ids,
                'bounds': {k: list(map(fraction_json, v)) for k, v in bounds.items()}})
            secondary.append({'family_id': family, 'replicate': rep,
                              'full_minus_compressed': list(map(fraction_json, ablation))})
            for name in PRIMARY:
                for j in (0, 1):
                    aggregate[name][j] += bounds[name][j]/total
    return {'version': VERSION, 'plan_sha256': plan['plan_sha256'],
        'provenance_not_conditioning': {'config_sha256': config['config_sha256'],
            'state_sha256': pipeline.sha(state), 'joined_sha256': pipeline.sha(joined),
            'evaluation_randomization_sha256': config['randomization_sha256']},
        'components': COMPONENTS, 'replicates': REPLICATES, 'vectors': total,
        'roots': sum(map(len, plan['family_roots'].values())), 'assigned': len(ledger),
        'counts': {s: dict(c) for s, c in counts.items()}, 'exact_vectors': exact_vectors,
        'contrast_completion_envelopes': {k: list(map(fraction_json, v)) for k, v in aggregate.items()},
        'intended_quality_envelopes': {k: list(map(fraction_json, v)) for k, v in qualities.items()},
        'actual_artifact_quality_envelopes': {k: list(map(fraction_json, v)) for k, v in actual_qualities.items()},
        'secondary_descriptive': secondary, '_census_rows': vector_rows,
        'limits': 'metadata reconciliation, not fresh-RNG/receiver-independence or observation certification'}


def analyze(plan, state, joined, config, tasks):
    result = reconcile(plan, state, joined, config, tasks)
    inference = census.analyze(plan['census_plan'], result.pop('_census_rows'))
    # Exact arithmetic remains in the existing implementation; serialize it
    # without float conversions for immutable JSON artifacts.
    def serial(value):
        if type(value) is Fraction:
            return fraction_json(value)
        if type(value) is dict:
            return {k: serial(v) for k, v in value.items()}
        if type(value) in (list, tuple):
            return [serial(v) for v in value]
        return value
    intervals = inference['intervals']
    interval = lambda name: tuple(Fraction(x['num'], x['den']) for x in intervals[name])
    l1, u1 = interval('d_minus_b1'); l2, _ = interval('d_minus_b2')
    useful, excluded, superior = l1 > Fraction(1, 20), u1 < Fraction(1, 20), l2 > 0
    result.update(inference=serial(inference), decision={
        'useful_vs_b1': useful, 'excludes_five_points_vs_b1': excluded,
        'superior_vs_b2': superior,
        'scoped_verdict': 'GO_QUALITY' if useful and superior else 'NO_GO_FIVE_POINT_QUALITY' if excluded else 'INCONCLUSIVE',
        'cost_verdict': 'not established by quality inference; deployment telemetry/overhead reported separately'},
        conditioning=plan['conditioning'], conditioning_excludes=plan['conditioning_excludes'],
        assumptions={'by_design_if_verified': ['prospective110component census and32balanced fresh vectors',
            'fixed development/tuning/learned-policy/baseline freeze before evaluation',
            'every assigned root/strategy retained with exact equal-root/component weights'],
            'assumed_and_requires_actual_evidence': ['independent OS CSPRNG vector draws after nonrandom freeze',
                'stable receiver and no interference across whole vectors',
                'valid source-separated pinned operational observation and pathwise censoring bounds'],
            'not_proved_by_identifiers': ['freshness', 'independence', 'policy chronology', 'semantic-family transport']},
        classification='finite-source operational publisher-grade inference; not broad-family efficacy or all-input quality',
        no_optional_stopping=True, no_best_arm_selection=True)
    return result
