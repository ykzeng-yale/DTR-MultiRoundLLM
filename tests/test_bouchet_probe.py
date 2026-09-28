from experiments.containment.bouchet_probe_v1 import command

def test_no_project_mount_or_host_root_fallback():
 cmd=command('/private-canary','net:[1]','pid:[1]')
 assert '--unshare-all' in cmd and '--clearenv' in cmd
 assert '--unshare-user-try' not in cmd and '--share-net' not in cmd
 mounts=[cmd[i+1:i+3] for i,x in enumerate(cmd) if x=='--ro-bind']
 assert all(src in ('/usr','/lib','/lib64') for src,dst in mounts)
 assert cmd[-3:]==['/private-canary','net:[1]','pid:[1]']
