"""Offline compute-local wheel install and trusted object observation."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,time
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
  if shutil.disk_usage('/tmp').free < 2*1024**3:raise RuntimeError('less than 2GiB local scratch free')
  with tempfile.TemporaryDirectory(prefix='dtr-mrl-native-',dir='/tmp') as scratch_name:
   scratch=Path(scratch_name)
   shutil.copytree('wheels',scratch/'wheels')
   shutil.copyfile('wheel-lock.txt',scratch/'wheel-lock.txt')
   if any(sha(scratch/'wheels'/w['file'])!=w['sha256'] for w in plan['wheels']):raise ValueError('staged wheel drift')
   rec['scratch']={'kind':'compute-local /tmp, owned temporary directory','staged_wheel_bytes':sum((scratch/'wheels'/w['file']).stat().st_size for w in plan['wheels'])}
   env={k:v for k,v in os.environ.items() if not k.startswith('PIP_')};env['PIP_CONFIG_FILE']='/dev/null';env['TMPDIR']=scratch_name
   with (out/'install.log').open('x') as log:
    p=subprocess.run(['/usr/bin/python3','-m','pip','--disable-pip-version-check','install','--no-index','--no-deps','--no-compile','--require-hashes','--target','runtime','--find-links','wheels','-r','wheel-lock.txt'],stdout=log,stderr=subprocess.STDOUT,env=env,cwd=scratch,timeout=300)
   rec['install_returncode']=p.returncode
   if p.returncode:raise RuntimeError('offline installation failed')
   rec['runtime_bytes']=sum(f.stat().st_size for f in (scratch/'runtime').rglob('*') if f.is_file())
   if rec['runtime_bytes']>1536*1024**2:raise RuntimeError('runtime storage cap')
   # Matplotlib 3.7.0 starts a timer thread only when its font cache is
   # absent. Prepare that cache using trusted library code in a namespace
   # with no network/home/project; the actual observation retains the strict
   # seccomp deny rule, including clone. No candidate code runs here.
   cache=scratch/'font-cache';cache.mkdir()
   def sandbox(cache_read_only):
    base=command('/absent-canary','unused','unused')
    base[1:1]=['--ro-bind',str(scratch/'runtime'),'/runtime']
    at=base.index('--setenv')
    base[at:at]=['--dir','/tmp/mpl',
                 '--ro-bind' if cache_read_only else '--bind',str(cache),'/tmp/mpl']
    e=base.index('/usr/bin/env')
    base[e+3:e+3]=['OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1',
                   'MPLCONFIGDIR=/tmp/mpl','HOME=/tmp']
    return base
   base=sandbox(False)
   i=base.index('-c')
   prep=base[:i+1]+["import sys;sys.path.insert(0,'/runtime');import matplotlib.font_manager as fm;print(fm.FontManager.__version__)"]
   p=subprocess.run(prep,stdin=subprocess.DEVNULL,capture_output=True,text=True,
                    timeout=45,env={'PATH':'/usr/bin'})
   (out/'font-prep.stdout').write_text(p.stdout)
   (out/'font-prep.stderr').write_text(p.stderr)
   rec['font_prep_returncode']=p.returncode
   cache_files=list(cache.glob('fontlist-v*.json'))
   rec['font_cache']=[{'file':f.name,'bytes':f.stat().st_size,'sha256':sha(f)} for f in cache_files]
   if p.returncode or len(cache_files)!=1 or cache_files[0].stat().st_size>16*1024**2:
    raise RuntimeError('trusted font cache preparation failed')
  # Same deny filter, new declared trusted-fixture resource envelope; not a
  # general candidate runner. No inherited project/home or network namespace.
   boot=BOOT.replace('256*1024*1024','1024*1024*1024').replace('(1,2)','(30,35)')
   base=sandbox(True)
   i=base.index('-c');cmd=base[:i+1]+[boot,Path('experiments/native_runtime/native_object_fixture_v1.py').read_text()]
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
