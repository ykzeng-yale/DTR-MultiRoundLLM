"""Execution-expectation inference conditional on a fixed finite family census.

Prospective extension, not inference for a broad task-family distribution. The
complete two-contrast execution vectors must be mutually independent, including
fresh initial answers, under the frozen law. Equal prespecified replication
counts retain equal family weights. Identifiers cannot certify independence.
"""
from fractions import Fraction

from experiments.prompt_choice import paired_inference as paired
from experiments.sequential.public_history import digest

VERSION = 'finite-family-census-execution-v1'
SCOPE = 'conditional-finite-family-census'
PIN_FIELDS = {'roster_sha256', 'execution_law_sha256', 'policies_sha256',
              'receiver_sha256', 'observer_sha256'}


def validate_plan(plan):
    if (type(plan) is not dict or set(plan) != PIN_FIELDS | {'version', 'scope', 'family_ids', 'replicates', 'alpha', 'useful_gain'}
            or plan['version'] != VERSION or plan['scope'] != SCOPE):
        raise ValueError('explicit finite-census plan required')
    families = plan['family_ids']
    if (type(families) is not list or not families
            or any(type(f) is not str or not f for f in families)
            or families != sorted(set(families))):
        raise ValueError('fixed sorted family census required')
    if type(plan['replicates']) is not int or plan['replicates'] < 1:
        raise ValueError('positive predeclared balanced replication required')
    for name in PIN_FIELDS:
        digest(plan[name])
    for name in ('alpha', 'useful_gain'):
        value = plan[name]
        if (type(value) is not dict or set(value) != {'num', 'den'}
                or type(value['num']) is not int or type(value['den']) is not int
                or value['den'] <= 0):
            raise ValueError('exact prospective inference settings required')
    if not 0 < Fraction(plan['alpha']['num'], plan['alpha']['den']) < 1:
        raise ValueError('alpha')
    if Fraction(plan['useful_gain']['num'], plan['useful_gain']['den']) != Fraction(1, 20):
        raise ValueError('five-point usefulness rule required')
    return plan


def analyze(plan, rows):
    """Retain the complete family x replicate ledger and pathwise bounds.

    Every row needs an independently created whole-run initial_execution_id.
    Reusing one initial answer across policies INSIDE a row is permitted; reusing
    it across nominally independent rows is refused. Random-service/session
    dependence can still invalidate this procedure despite distinct IDs.
    """
    validate_plan(plan)
    if type(rows) is not list:
        raise ValueError('all assigned rows required')
    expected = {(f, r) for f in plan['family_ids'] for r in range(plan['replicates'])}
    identities, initials, internal = set(), set(), []
    for row in rows:
        if type(row) is not dict or set(row) != {'family_id', 'replicate', 'initial_execution_id', 'bounds'}:
            raise ValueError('census execution row schema')
        f, r, initial = row['family_id'], row['replicate'], row['initial_execution_id']
        if type(f) is not str or type(r) is not int or (f, r) not in expected:
            raise ValueError('undeclared family/replicate')
        if (f, r) in identities:
            raise ValueError('duplicate assignment')
        if type(initial) is not str or not initial or initial in initials:
            raise ValueError('initial execution must be distinct across independent units')
        identities.add((f, r)); initials.add(initial)
        # This reuses bounded-vector arithmetic only. Its historical field name
        # family_id here identifies an execution vector, not a new task family.
        internal.append({'family_id': initial, 'bounds': row['bounds']})
    if identities != expected:
        raise ValueError('missing assigned rows: provide [-1,1] bounds, never drop assignments')
    alpha = Fraction(plan['alpha']['num'], plan['alpha']['den'])
    result = paired.paired_contrasts(internal, alpha)
    result.pop('n_families')
    result['source_method'] = result.pop('version')
    return dict(result, version=VERSION, scope=SCOPE,
                n_families=len(plan['family_ids']), replicates_per_family=plan['replicates'],
                n_assigned_execution_vectors=len(rows), pins={k: plan[k] for k in sorted(PIN_FIELDS)},
                useful_gain=plan['useful_gain'],
                assumptions='independent fresh whole-run vectors conditional on frozen roster/development; '
                            'same target law across replicates; valid fixed endpoint and pathwise bounds',
                transport='no inference beyond this fixed census; repetitions add no task families')
