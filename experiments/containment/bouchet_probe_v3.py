"""Trusted, harmless compute-node namespace probe; never benchmark execution.

A passing result is prerequisite evidence only, not authorization to run
untrusted/generated candidates on Bouchet. No downloads or outbound connection.
"""
import hashlib,json,os,platform,resource,subprocess,time
from pathlib import Path

PROBE = r'''
import json,os,socket,sys
from pathlib import Path
canary,hostnet,hostpid=sys.argv[1:]
checks={}
checks['host_canary_hidden']=not Path(canary).exists()
checks['home_absent']=not Path('/home').exists() and not Path('/root').exists()
checks['project_absent']=not Path('/nfs').exists()
checks['different_network_namespace']=os.readlink('/proc/self/ns/net')!=hostnet
checks['different_pid_namespace']=os.readlink('/proc/self/ns/pid')!=hostpid
checks['environment_cleared']='DTR_PROBE_HOST_ONLY' not in os.environ
checks['working_directory_isolated']=os.getcwd()=='/work'
Path('/tmp/own-probe').write_text('test')
checks['temporary_write_works']=Path('/tmp/own-probe').read_text()=='test'
# Inspect routing metadata; never send traffic or contact a receiver/service.
lines=Path('/proc/net/route').read_text().splitlines()[1:]
checks['no_external_ipv4_route']=not any(line.split()[0]!='lo' for line in lines)
print(json.dumps({'checks':checks,'passed':all(checks.values())},sort_keys=True))
'''


def command(canary,hostnet,hostpid):
    cmd=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL']
    for path in ('/usr','/lib','/lib64'):
        if Path(path).exists():cmd+=['--ro-bind',path,path]
    cmd+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/work','--chdir','/work','--setenv','PATH','/usr/bin', '/usr/bin/env','-i','PATH=/usr/bin','/usr/bin/python3','-I','-S','-c',PROBE,canary,hostnet,hostpid]
    return cmd


def main():
    start=time.monotonic();out=Path('probe-results');out.mkdir(exist_ok=False)
    resource.setrlimit(resource.RLIMIT_CPU,(60,65));resource.setrlimit(resource.RLIMIT_FSIZE,(1048576,1048576))
    canary=Path('host-canary.txt').resolve();canary.write_text('owned harmless probe only\n')
    plan=json.loads(Path('probe-plan.json').read_bytes())
    for f,h in plan['files'].items():
        if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h:raise ValueError('source mismatch')
    rec={'job_id':os.environ['SLURM_JOB_ID'],'freeze':Path('freeze.txt').read_text().strip(),'plan_sha256':hashlib.sha256(Path('probe-plan.json').read_bytes()).hexdigest(),'classification':'trusted namespace capability probe only; no candidate execution authorized','platform':platform.platform(),'versions':{}}
    for name in ('bwrap','apptainer','unshare'):
        try:
            p=subprocess.run(['/usr/bin/'+name,'--version'],capture_output=True,text=True,timeout=5)
            rec['versions'][name]={'returncode':p.returncode,'stdout':p.stdout[:8192],'stderr':p.stderr[:8192]}
        except (OSError,subprocess.TimeoutExpired) as e:rec['versions'][name]={'error':repr(e)}
    try:
        cmd=command(str(canary),os.readlink('/proc/self/ns/net'),os.readlink('/proc/self/ns/pid'))
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=15,env={'PATH':'/usr/bin','DTR_PROBE_HOST_ONLY':'canary'})
        rec['namespace_probe']={'returncode':p.returncode,'stdout':p.stdout[:65536],'stderr':p.stderr[:65536]}
        rec['parsed']=json.loads(p.stdout) if p.returncode==0 else None
    except (OSError,subprocess.TimeoutExpired,ValueError) as e:rec['probe_error']=repr(e)
    rec['host_canary_unchanged']=canary.read_text()=='owned harmless probe only\n';rec['seconds']=time.monotonic()-start
    rec['candidate_execution_released']=False
    (out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__':main()
