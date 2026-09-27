"""Versioned strict sandbox with one hash-bound read-only dependency tree.

No benchmark release; runtime qualification only. Optional interpreter must be
explicitly pinned and separately qualified by the caller before benchmark use. Does not process .pth hooks.
Parent-controlled bundle storage must not be concurrently mutated. Pre/post checks
are detection, not an OS guarantee against other same-user parent processes.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
from experiments.landmark import sandbox as strict
from experiments.prompt_choice.dependency_bundle_v1 import verify
from experiments.prompt_choice.native_execution_v1 import classify


def profile(python,run_dir,bundle):
    return strict.profile(python,run_dir)+'\n(allow file-read* (subpath '+json.dumps(str(Path(bundle).resolve()))+'))\n'


def run(source,*,bundle,tree_sha256,timeout_s=10,cpu_seconds=5,output_cap=16384,mem_bytes=1<<30,python=None):
    if type(source) is not str or len(source.encode())>1048576:raise ValueError('source cap')
    if type(timeout_s) not in (int,float) or not 0<timeout_s<=10:raise ValueError('wall cap')
    if type(cpu_seconds) is not int or not 1<=cpu_seconds<=5:raise ValueError('CPU cap')
    if type(output_cap) is not int or not 1024<=output_cap<=262144:raise ValueError('output cap')
    if type(mem_bytes) is not int or not 1<=mem_bytes<=2<<30:raise ValueError('memory cap')
    info=strict.sandbox_info(python)
    if info['kind']!='seatbelt':raise RuntimeError('Seatbelt required')
    before=verify(bundle,tree_sha256)
    bundle=Path(bundle).resolve()
    run_dir=Path(tempfile.mkdtemp(prefix='deps_',dir=info['base_dir']))
    proc=None;timed_out=False;start=time.monotonic()
    rendered=profile(info['python'],str(run_dir),bundle)
    bootstrap=('import sys,os\n'
               'sys.dont_write_bytecode=True\n'
               f'sys.path.insert(0,{str(bundle)!r})\n'
               'os.environ["MPLBACKEND"]="Agg"\n'
               'os.environ["MPLCONFIGDIR"]=os.getcwd()\n'
               'os.environ["HOME"]=os.getcwd()\n')
    try:
        (run_dir/'program.py').write_text(bootstrap+source)
        with (run_dir/'stdout').open('w+b') as out,(run_dir/'stderr').open('w+b') as err:
            proc=subprocess.Popen(['/usr/bin/sandbox-exec','-p',rendered,info['python'],'-I','-S',str(run_dir/'program.py')],cwd=run_dir,
                env={'PATH':'/usr/bin:/bin','PYTHONIOENCODING':'utf-8','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','VECLIB_MAXIMUM_THREADS':'1'},
                stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,
                preexec_fn=strict.limits(mem_bytes,cpu_seconds,output_cap))
            try:proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out=True
                try:os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                proc.wait(timeout=2)
            out.seek(0);ob=out.read(output_cap)
            err.seek(0);eb=err.read(output_cap)
        result={'sandbox_kind':'seatbelt','executed':True,'stdout':ob.decode(errors='replace'),'stderr':eb.decode(errors='replace'),
                'returncode':proc.returncode,'timed_out':timed_out,'pid':proc.pid,'seconds':time.monotonic()-start,
                'rendered_profile_sha256':hashlib.sha256(rendered.encode()).hexdigest()}
        verify(bundle,tree_sha256)
        return {'execution':classify(result,output_cap),'raw_process':result,'dependency_tree_sha256':before['tree_sha256'],
                'dependency_bytes':before['total_bytes'],'bundle_unchanged_after':True,'python':info['python']}
    finally:
        if proc is not None and proc.poll() is None:
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            proc.wait(timeout=2)
        shutil.rmtree(run_dir,ignore_errors=True)
