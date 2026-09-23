"""Source-only consistency checks for the current E13a execution contract.

Read configuration/source and parse documented commands; never invoke a command,
receiver, grader, sandbox, model or reference program. Operational source-guard
behaviour is covered independently by the collector/clock/grader test modules.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import shlex
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/e13a_execution_contract_20260923.md'
STAGE = ROOT / 'experiments/landmark/e13a_stage.json'
PLAN = ROOT / 'results/e13a_request_plan_20260922.json'
RELEASE = ROOT / 'experiments/landmark/e13a_release'


def read(path):
    return json.loads(path.read_text())


@pytest.fixture(scope='module')
def text():
    return DOC.read_text()


@pytest.fixture(scope='module')
def table(text):
    rows = {}
    for line in text.splitlines():
        if line.startswith('|'):
            cells = [x.strip().replace('**', '') for x in line.strip('|').split('|')]
            if len(cells) == 2:
                rows[cells[0]] = cells[1]
    return rows


def first_number(value):
    return int(re.search(r'\d[\d,]*', value).group().replace(',', ''))


def flags(path):
    tree = ast.parse(path.read_text())
    return {a.value for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'add_argument'
            for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)
            and a.value.startswith('--')}


@pytest.fixture(scope='module')
def commands(text):
    """Return each script invocation, including an analysis command nested under the supervisor."""
    result = []
    for block in re.findall(r'```sh\n(.*?)```', text, re.S):
        for line in block.splitlines():
            words = shlex.split(line)
            for i, word in enumerate(words):
                if word.endswith('.py') and word.startswith('scripts/'):
                    args = words[i+1:]
                    if '--' in args:
                        args = args[:args.index('--')]
                    result.append((word, args))
    return result


def test_documented_numerical_caps_match_actual_release_and_clock(table):
    from scripts.e13a_stage_clock import PHASE_CAPS, OUTER_TOTAL_SECONDS
    from experiments.landmark import grade
    config = read(RELEASE / 'config.json')
    limits = read(RELEASE / 'release_manifest.json')['grading_limits']
    expected = {
        'Receiver generation attempts': config['max_calls'],
        'Reserved completion tokens': config['max_completion_tokens'],
        'Containment payload starts': len(grade.REQUIRED_CHECKS),
        'Private reference/control starts': limits['recheck_starts'],
        'Private candidate starts': limits['artifact_starts'],
        'Total isolated starts': limits['max_private_starts'],
        'Generation smoke calls': 0, 'Public-check starts': 0,
        'Setup through refreeze': PHASE_CAPS['setup'],
        'Collection': PHASE_CAPS['collection'],
        'Private grading': PHASE_CAPS['private_grading'],
        'Analysis/report preparation': PHASE_CAPS['analysis'],
        'Contiguous outer limit': OUTER_TOTAL_SECONDS,
    }
    for label, number in expected.items():
        assert first_number(table[label]) == number, label
    assert '$0' in table['Paid services, installations or downloads']
    assert config['max_tokens_per_call'] == 512
    assert config['max_calls'] * config['max_tokens_per_call'] == config['max_completion_tokens'] == 30720
    assert first_number(table['Setup metadata/template HTTP attempts']) == 50
    assert first_number(table['Collection metadata HTTP attempts']) == 31
    for label in ('Setup metadata/template HTTP attempts', 'Collection metadata HTTP attempts'):
        assert re.search(r'10\s+seconds', table[label])


def test_fixed_assignments_and_grading_budget_are_source_consistent(text):
    stage, plan, release = read(STAGE), read(PLAN), read(RELEASE / 'release_manifest.json')
    assert stage['roots'] == release['roots'] and len(stage['roots']) == 5
    assert stage['arms'] == {'R1': list(range(2, 8)), 'FRESH': list(range(6))}
    n = len(stage['roots']) * sum(map(len, stage['arms'].values()))
    limits = release['grading_limits']
    assert stage['grading_limits'] == limits
    assert n == plan['budget']['receiver_calls'] == limits['artifact_starts'] == 60
    assert plan['budget']['isolated_starts'] == limits['artifact_starts'] + limits['recheck_starts'] == 70
    assert limits['max_private_starts'] == 79 == n + limits['recheck_starts'] + limits['containment_starts']
    assert limits['containment_starts'] == 9 and limits['grading_seconds'] == 300
    assert all(f'`{root}`' in text for root in stage['roots'])
    assert stage['gating']['private_grades_are_an_input'] is False
    assert stage['branch_inclusion_probability'] == 1 and stage['order_role'] == 'scheduling_not_assignment'


def test_additive_limit_validator_preserves_existing_bounds():
    from experiments.landmark import study_adapter as sa
    assert sa.GRADING_LIMIT_KEYS == {'n_roots', 'artifact_starts', 'recheck_starts', 'max_private_starts', 'grading_seconds'}
    assert sa.OPTIONAL_GRADING_LIMIT_KEYS == {'containment_starts'}
    assert sa.MAX_GRADING_SECONDS == 600 and sa.MAX_PRIVATE_STARTS == 200
    def check(**values):
        return sa.load_grading_limits(json.dumps({'grading_limits': values}).encode())
    values = read(RELEASE / 'release_manifest.json')['grading_limits']
    assert check(**values)['max_private_starts'] == 79
    assert check(n_roots=14, artifact_starts=154, recheck_starts=28,
                 max_private_starts=182, grading_seconds=600)['containment_starts'] == 0
    for patch in ({'max_private_starts': 70}, {'grading_seconds': 601}, {'public_starts': 60},
                  {'containment_starts': -1}, {'n_roots': 0}):
        with pytest.raises(ValueError):
            check(**{**values, **patch})
    without_containment = {k: v for k, v in values.items() if k != 'containment_starts'}
    with pytest.raises(ValueError):
        check(**without_containment)


def test_all_documented_script_flags_exist_in_actual_argparse_source(commands):
    expected = {'scripts/e13a_collect.py', 'scripts/e13a_grade.py', 'scripts/e13a_stage_clock.py',
                'scripts/check_landmark_sandbox.py', 'scripts/launch_own_receiver_v31.py',
                'scripts/receiver_preflight_mrl10.py', 'scripts/diff_receiver_snapshot_v31.py',
                'scripts/e13a_analyze.py'}
    assert {p for p, _ in commands} == expected
    for path, args in commands:
        quoted = {word.split('=', 1)[0] for word in args if word.startswith('--')}
        assert quoted <= flags(ROOT / path), (path, quoted - flags(ROOT / path))


def test_commands_bind_one_run_stage_and_real_grading_inputs(commands):
    by_path = {}
    for path, args in commands:
        by_path.setdefault(path, []).append(args)
    for path in ('scripts/e13a_collect.py', 'scripts/e13a_grade.py'):
        args = by_path[path][0]
        assert '--real' in args and args[args.index('--out')+1] == '$RUN'
        assert args[args.index('--stage')+1] == str(STAGE.relative_to(ROOT))
        assert args[args.index('--plan')+1] == str(PLAN.relative_to(ROOT))
    args = by_path['scripts/e13a_grade.py'][0]
    assert args[args.index('--collect')+1] == '$RUN/collect'
    assert args[args.index('--release')+1] == str(RELEASE.relative_to(ROOT))
    assert args[args.index('--attestation')+1] == '$RUN/attestation/attestation.json'
    clock = by_path['scripts/e13a_stage_clock.py']
    assert len([a for a in clock if '--init' in a]) == 1
    assert all(a[a.index('--run-dir')+1] == '$RUN' and '--stage' in a for a in clock)
    assert {a[a.index('--supervise')+1] for a in clock if '--supervise' in a} == {'setup', 'analysis'}
    assert not any('--check' in a or '--charge' in a for a in clock)
    analysis = by_path['scripts/e13a_analyze.py'][0]
    assert analysis[analysis.index('--grades')+1] == '$RUN/grade/grades.jsonl'


def test_containment_directory_then_verify_then_preflight_then_diff(text, commands):
    containment = next(args for path, args in commands if path == 'scripts/check_landmark_sandbox.py')
    assert containment[containment.index('--output')+1] == '$RUN/attestation'
    blocks = '\n'.join(re.findall(r'```sh\n(.*?)```', text, re.S))
    assert blocks.index('scripts/check_landmark_sandbox.py') < blocks.index('verify_attestation(sys.argv[1])')
    assert blocks.index('verify_attestation(sys.argv[1])') < blocks.index('scripts/launch_own_receiver_v31.py')
    assert blocks.index('scripts/receiver_preflight_mrl10.py') < blocks.index('scripts/diff_receiver_snapshot_v31.py')
    assert blocks.index('scripts/diff_receiver_snapshot_v31.py') < blocks.index('scripts/e13a_collect.py')
    launcher_args = [args for path, args in commands if path == 'scripts/launch_own_receiver_v31.py']
    assert len(launcher_args) == 2 and '--stop' in launcher_args[-1]
    for flag in ('--owned-receiver-dir', '--cleanup-helper-sha256'):
        assert flag in text and flag in flags(ROOT / 'scripts/e13a_stage_clock.py')


def test_release_binds_authoritative_source_and_all_quoted_hashes(text):
    from scripts.build_e13a_release import EXECUTION_SOURCES
    manifest = read(RELEASE / 'release_manifest.json')
    assert set(manifest['execution_source_hashes']) == set(EXECUTION_SOURCES)
    assert manifest['stage']['descriptor_sha256'] == hashlib.sha256(STAGE.read_bytes()).hexdigest()
    assert manifest['request_plan']['sha256'] == hashlib.sha256(PLAN.read_bytes()).hexdigest()
    for path, expected in manifest['execution_source_hashes'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    model_sha = manifest['model']['model_digest']
    assert model_sha in text
    # Do not demand duplicated hash tables; verify every digest the prose actually quotes.
    known = {model_sha, manifest['model']['receiver_state_sha256_expected'],
             *manifest['execution_source_hashes'].values(), *manifest['package'].values(),
             manifest['stage']['descriptor_sha256'], manifest['request_plan']['sha256']}
    assert set(re.findall(r'\b[0-9a-f]{64}\b', text)) <= known


def test_runtime_authority_and_scientific_scope_are_explicit(text):
    normalized = ' '.join(text.replace('**', '').lower().split())
    assert '(mrl19_review_mrl20_20260923.md)' in normalized
    assert 'conditional on' in normalized and 'fresh window' in normalized
    assert 'zero-authority fields' in normalized
    assert 'no e13a model or candidate execution is claimed' in normalized
    assert 'missing assigned primary grade suppresses the primary point contrast' in normalized
    assert 'bounds are not confidence intervals' in normalized
    assert 'no interim efficacy/futility test' in normalized
    assert 'no claim of achieving a confidence-width target' in normalized
    assert 'no untouched test-set or population-policy claim' in normalized
    assert re.search(r'\bno\b[^.]*\boutcome-based stopping is allowed', normalized)
    assert 'neither isolates diagnostic information from instruction' in normalized
    assert 'maxima, not expected counts' in normalized
    assert 'outside this contract' in normalized and 'public-score supplement' in normalized
    manifest = read(RELEASE / 'release_manifest.json')
    assert manifest['authorization']['receiver_calls_authorized'] == 0
    assert read(STAGE)['receiver_calls_authorized'] == 0


def test_historical_e12_latency_arithmetic_remains_reproducible():
    """Retain the older immutable-ledger check without requiring unused numbers in current prose."""
    run = ROOT / 'results/e12_dev_v3_20260922T030255Z'
    sums = {}
    for phase in ('A', 'C'):
        rows = [json.loads(line) for line in (run / phase / 'calls.jsonl').read_text().splitlines()]
        assert all(type(row.get('seconds')) in (int, float) for row in rows)
        sums[phase] = round(sum(row['seconds'] for row in rows), 6)
    assert sums == {'A': 14.977224, 'C': 295.594775}


def test_stage_command_metadata_matches_current_interfaces(commands):
    stage_commands = read(STAGE)["exact_commands"]
    assert not {"analysis_check", "analysis_charge"} & set(stage_commands)
    contract = {path: args for path, args in commands}
    for name, line in stage_commands.items():
        if name == "note":
            continue
        words = shlex.split(line)
        for i, word in enumerate(words):
            if not word.startswith("scripts/") or not word.endswith(".py"):
                continue
            args = words[i+1:]
            if "--" in args:
                args = args[:args.index("--")]
            quoted = {a.split("=", 1)[0] for a in args if a.startswith("--")}
            assert quoted <= flags(ROOT / word), (name, word, quoted - flags(ROOT / word))
    for key, path in (("collection", "scripts/e13a_collect.py"), ("grading", "scripts/e13a_grade.py")):
        words = shlex.split(stage_commands[key])
        assert words[words.index(path)+1:] == contract[path]
    analysis = shlex.split(stage_commands["analysis"])
    assert analysis[analysis.index("--supervise")+1] == "analysis"
    assert analysis[analysis.index("scripts/e13a_analyze.py")+1:] == contract["scripts/e13a_analyze.py"]
    init = shlex.split(stage_commands["clock_init"])
    assert "--init" in init and init[init.index("--stage")+1] == str(STAGE.relative_to(ROOT))
