"""Data-only binary-wheel acquisition; no install/build/package import."""
import email,hashlib,json,os,signal,subprocess,sys,threading,time,zipfile
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def directory_bytes(root):
 total=0
 for f in root.rglob('*'):
  try:
   if f.is_file():total+=f.stat().st_size
  except FileNotFoundError:pass  # pip atomically renames temporary files
 return total

def main():
 plan=json.loads(Path('acquisition-plan.json').read_bytes())
 for f,h in plan['files'].items():
  if sha(f)!=h:raise ValueError('source drift '+f)
 out=Path('acquisition');out.mkdir(exist_ok=False);wheels=out/'wheels';wheels.mkdir();start=time.monotonic();reason=[]
 cmd=[sys.executable,'-m','pip','--disable-pip-version-check','download','--no-input','--no-cache-dir','--only-binary=:all:','--implementation','cp','--python-version','39','--abi','cp39','--platform','manylinux2014_x86_64','--index-url','https://pypi.org/simple','-r','experiments/native_runtime/core_requirements_v1.txt','-c','experiments/native_runtime/publisher_constraints_v1.txt','--dest',str(wheels)]
 env={k:v for k,v in os.environ.items() if not k.startswith('PIP_')};env['PIP_CONFIG_FILE']='/dev/null';env['TMPDIR']=str((out/'tmp').resolve());Path(env['TMPDIR']).mkdir()
 p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True,env=env)
 def kill():
  if p.poll() is None:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
 def log():
  n=0
  with (out/'pip.log').open('xb') as f:
   while True:
    b=p.stdout.read1(8192)
    if not b:break
    f.write(b[:max(0,(8<<20)-n)]);n+=len(b)
    if n>8<<20:reason.append('log cap');kill();break
 t=threading.Thread(target=log);t.start()
 while p.poll() is None:
  if time.monotonic()-start>600:reason.append('600second cap');kill();break
  if directory_bytes(out)>512<<20:reason.append('512MiB cap');kill();break
  time.sleep(.5)
 p.wait();t.join(5);rows=[]
 for f in sorted(wheels.iterdir()):
  if not f.name.endswith('.whl'):raise ValueError('non-wheel retained')
  with zipfile.ZipFile(f) as z:
   names=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')]
   if len(names)!=1 or z.getinfo(names[0]).file_size>1048576:raise ValueError('metadata shape/size')
   m=email.message_from_bytes(z.read(names[0]))
  rows.append({'file':f.name,'bytes':f.stat().st_size,'sha256':sha(f),'name':m.get('Name'),'version':m.get('Version'),'requires_python':m.get('Requires-Python'),'license':m.get('License'),'license_expression':m.get('License-Expression')})
 rec={'job_id':os.environ['SLURM_JOB_ID'],'freeze':Path('freeze.txt').read_text().strip(),'plan_sha256':sha('acquisition-plan.json'),'python':sys.version,'command':cmd,'returncode':p.returncode,'cap_failures':reason,'seconds':time.monotonic()-start,'wheels':rows,'installed':False,'benchmark_executed':False,'candidate_execution_released':False,'paid_usd':0}
 (out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__':main()
