"""Bounded process adapter for prospective native measurement, not a grader.

Reuses the unchanged default-deny landmark runner. No package access extension.
A clean exit is execution completion, never proof that a test ran or passed.
"""
from experiments.landmark import sandbox
import signal

VERSION = 'native-execution-v1'


def classify(result, output_cap):
    if type(output_cap) is not int or not 1024 <= output_cap <= 262144:
        raise ValueError('invalid output cap')
    if type(result) is not dict or result.get('sandbox_kind') != 'seatbelt' or result.get('executed') is not True:
        raise ValueError('unverified execution record')
    if any(type(result.get(k)) is not str for k in ('stdout','stderr')):
        raise ValueError('missing output record')
    # Runner decodes UTF-8 with replacement; encoded length may overestimate bytes.
    # Conservative saturation is intentional and is not an exact raw-byte counter.
    saturated = any(len(result[k].encode('utf-8')) >= output_cap for k in ('stdout','stderr'))
    cap_signal = result.get('returncode') == -signal.SIGXFSZ
    timeout=result.get('timed_out')
    if type(timeout) is not bool:raise ValueError('missing timeout record')
    if timeout: disposition='timeout'
    elif saturated or cap_signal: disposition='output_limit'
    elif type(result.get('returncode')) is not int:raise ValueError('missing exit code')
    elif result['returncode'] != 0: disposition='process_error'
    else: disposition='completed_ungraded'
    return {'version':VERSION,'disposition':disposition,'output_saturated':saturated or cap_signal,
            'timed_out':timeout,'test_outcome':None,'feedback_status':None,
            'note':'No test outcome or public feedback inferred from process exit or candidate output.'}


def run(source, *, timeout_s=2.0, cpu_seconds=1, output_cap=4096, mem_bytes=256<<20):
    if type(source) is not str or len(source.encode('utf-8')) > 1048576:
        raise ValueError('invalid source size')
    if type(mem_bytes) is not int or not 1 <= mem_bytes <= 2 << 30:
        raise ValueError('invalid requested memory cap')
    if type(output_cap) is not int or not 1024 <= output_cap <= 262144:
        raise ValueError('invalid output cap')
    if type(cpu_seconds) is not int or not 1 <= cpu_seconds <= 5:
        raise ValueError('invalid CPU cap')
    if type(timeout_s) not in (int,float) or not 0 < timeout_s <= 10:
        raise ValueError('invalid wall cap')
    result=sandbox.run_program(source,timeout_s=timeout_s,cpu_seconds=cpu_seconds,output_cap=output_cap,mem_bytes=mem_bytes)
    return {'execution':classify(result,output_cap),'raw_process':result}
