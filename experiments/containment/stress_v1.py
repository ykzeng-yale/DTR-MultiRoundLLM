"""Trusted fixed-fixture Linux containment qualification; no candidate release."""
import hashlib,json,os,selectors,signal,subprocess,time
from pathlib import Path
from bouchet_probe_v3 import command

BOOT=r'''
import ctypes,errno,json,os,resource,sys
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
resource.setrlimit(resource.RLIMIT_CPU,(1,2))
resource.setrlimit(resource.RLIMIT_FSIZE,(65536,65536))
lib=ctypes.CDLL('libseccomp.so.2')
lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
lib.seccomp_load.argtypes=[ctypes.c_void_p];lib.seccomp_release.argtypes=[ctypes.c_void_p]
ctx=lib.seccomp_init(0x7fff0000)
if not ctx:raise RuntimeError('seccomp allocation')
for name in ('socket','socketpair','connect','bind','listen','accept','accept4','fork','vfork','clone','clone3','execve','execveat','unshare','setns','mount','umount2','mount_setattr','pivot_root','chroot','ptrace','process_vm_readv','process_vm_writev','pidfd_getfd','open_by_handle_at','name_to_handle_at','bpf','perf_event_open','keyctl','add_key','request_key','init_module','finit_module','delete_module','kexec_load','reboot','swapon','swapoff','setsid','setpgid'):
    number=lib.seccomp_syscall_resolve_name(name.encode())
    if number>=0 and lib.seccomp_rule_add(ctx,0x00050000|errno.EPERM,number,0)!=0:raise RuntimeError('seccomp rule '+name)
if lib.seccomp_load(ctx)!=0:raise RuntimeError('seccomp load')
lib.seccomp_release(ctx)
exec(sys.argv[1],{'__name__':'__main__'})
'''
FIXTURES={
 'arithmetic':("print('RESULT:42')",'text','RESULT:42'),
 'socket_denied':("import socket\ntry: socket.socket()\nexcept PermissionError: print('RESULT:denied')",'text','RESULT:denied'),
 'fork_denied':("import os\ntry: os.fork()\nexcept PermissionError: print('RESULT:denied')",'text','RESULT:denied'),
 'exec_denied':("import os\ntry: os.execv('/usr/bin/true',['true'])\nexcept PermissionError: print('RESULT:denied')",'text','RESULT:denied'),
 'memory_capped':("try: x=bytearray(512*1024*1024)\nexcept MemoryError: print('RESULT:capped')",'text','RESULT:capped'),
 'cpu_capped':("while True: pass",'cpu',None),
 'wall_capped':("import time; time.sleep(30)",'wall',None),
 'output_capped':("import os\nwhile True: os.write(1,b'x'*8192)",'output',None),
}


def run_one(name):
 code,kind,text=FIXTURES[name]
 base=command('/unmounted-canary','unused','unused');i=base.index('-c');cmd=base[:i+1]+[BOOT,code]
 start=time.monotonic();p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env={'PATH':'/usr/bin'})
 sel=selectors.DefaultSelector();data={'stdout':bytearray(),'stderr':bytearray()};reason=None;total=0
 for label,stream in [('stdout',p.stdout),('stderr',p.stderr)]:os.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,label)
 try:
  while sel.get_map():
   if time.monotonic()-start>2.5:reason='wall';break
   for k,_ in sel.select(.05):
    b=os.read(k.fileobj.fileno(),8192)
    if not b:sel.unregister(k.fileobj);continue
    total+=len(b);data[k.data].extend(b[:max(0,65536-len(data[k.data]))])
    if total>65536:reason='output';break
   if reason:break
 finally:
  if reason is None and p.poll() is None:
   try:p.wait(timeout=.1)
   except subprocess.TimeoutExpired:pass
  if p.poll() is None:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  p.wait(timeout=5);sel.close();p.stdout.close();p.stderr.close()
 out={k:bytes(v).decode(errors='replace') for k,v in data.items()}
 passed=(p.returncode==0 and out['stdout'].strip()==text) if kind=='text' else (reason==kind if kind in ('wall','output') else p.returncode in (-signal.SIGXCPU,-signal.SIGKILL,128+signal.SIGXCPU,128+signal.SIGKILL) and reason is None)
 return {'fixture':name,'passed':passed,'returncode':p.returncode,'limit_reason':reason,'seconds':time.monotonic()-start,'stdout':out['stdout'],'stderr':out['stderr']}


def main():
 p=json.loads(Path('stress-plan.json').read_bytes())
 for f,h in p['files'].items():
  if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h:raise ValueError('source drift')
 out=Path('stress-results');out.mkdir(exist_ok=False);start=time.monotonic();summary={'job_id':os.environ['SLURM_JOB_ID'],'freeze':Path('freeze.txt').read_text().strip(),'plan_sha256':hashlib.sha256(Path('stress-plan.json').read_bytes()).hexdigest(),'planned':len(p['assignments']),'completed':0,'failures':0,'error':None,'candidate_execution_released':False}
 try:
  with (out/'journal.jsonl').open('x') as f:
   for i,name in enumerate(p['assignments']):
    if time.monotonic()-start>540:raise TimeoutError('global wall cap')
    row=run_one(name);row['assignment']=i;f.write(json.dumps(row)+'\n');f.flush();summary['completed']+=1;summary['failures']+=not row['passed']
    if i==0 and not row['passed']:raise RuntimeError('preflight failed; no fixture repetitions')
    if summary['failures']>=2:raise RuntimeError('two failed checks; stop instead of blind repetitions')
 except BaseException as e:summary['error']=repr(e);raise
 finally:
  summary['seconds']=time.monotonic()-start;summary['unattempted']=summary['planned']-summary['completed'];(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':main()
