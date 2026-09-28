"""Offline wheel install and trusted object observation; no candidate release."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path('experiments/containment').resolve()))
from bouchet_probe_v3 import command
from stress_v1 import BOOT

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 start=time.monotonic();plan=json.loads(Path('native-plan.json').read_text())
 for f,h in plan['files'].items():
  if sha(f)!=h:raise ValueError('source drift '+f)
 for w in plan['wheels']:
  if sha(Path('wheels')/w['file'])!=w['sha256']:raise ValueError('wheel drift')
 out=Path('native-results');out.mkdir(exist_ok=False)
 rec={'job_id':os.environ['SLURM_JOB_ID'],'freeze':Path('freeze.txt').read_text().strip(),'plan_sha256':sha('native-plan.json'),'candidate_execution_released':False,'benchmark_executed':False,'paid_usd':0}
 try:
  env={k:v for k,v in os.environ.items() if not k.startswith('PIP_')};env['PIP_CONFIG_FILE']='/dev/null'
  with (out/'install.log').open('x') as log:
   p=subprocess.run(['/usr/bin/python3','-m','pip','--disable-pip-version-check','install','--no-index','--no-deps','--no-compile','--require-hashes','--target','runtime','--find-links','wheels','-r','wheel-lock.txt'],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=300)
  rec['install_returncode']=p.returncode
  if p.returncode:raise RuntimeError('offline installation failed')
  rec['runtime_bytes']=sum(f.stat().st_size for f in Path('runtime').rglob('*') if f.is_file())
  if rec['runtime_bytes']>1536*1024**2:raise RuntimeError('runtime storage cap')
  # Same deny filter, new declared trusted-fixture resource envelope; not a
  # general candidate runner. No inherited project/home or network namespace.
  boot=BOOT.replace('256*1024*1024','1024*1024*1024').replace('(1,2)','(30,35)')
  base=command('/absent-canary','unused','unused');i=base.index('-c')
  base[1:1]=['--ro-bind',str(Path('runtime').resolve()),'/runtime']
  i=base.index('-c');cmd=base[:i+1]+[boot,Path('experiments/native_runtime/native_object_fixture_v1.py').read_text()]
  e=cmd.index('/usr/bin/env')
  cmd[e+3:e+3]=['OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','MPLCONFIGDIR=/tmp/mpl','HOME=/tmp']
  p=subprocess.run(cmd,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=60,env={'PATH':'/usr/bin'})
  (out/'observation.stdout').write_text(p.stdout);(out/'observation.stderr').write_text(p.stderr)
  rec['observation_returncode']=p.returncode
  observed=json.loads(p.stdout) if p.returncode==0 else None
  rec['observation']=observed
  rec['checks']={k:observed is not None and observed.get(k)==v for k,v in plan['expected'].items()}
  rec['passed']=p.returncode==0 and all(rec['checks'].values())
  if not rec['passed']:raise RuntimeError('trusted native observation qualification failed')
 except BaseException as e:rec['error']=repr(e);raise
 finally:
  rec['seconds']=time.monotonic()-start
  (out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__':main()
