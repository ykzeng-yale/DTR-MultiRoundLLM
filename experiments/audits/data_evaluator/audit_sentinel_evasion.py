import json, sys, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
ROOT=Path('/Users/yukangzengcmac/DTR-MultiRoundLLM'); sys.path.insert(0,str(ROOT/'experiments'/'common'))
from verify import split_tests, verify
TASKS=json.load(open(ROOT/'work/data/tasks.json')); BYUID={t['uid']:t for t in TASKS}
HACKS = {
 'shadow_set':   "class _T:\n    def __eq__(s,o): return True\n    def __hash__(s): return 0\nset = lambda *a,**k: _T()\ndef {ep}(*a,**k): return None\n",
 'shadow_many':  ("class _T:\n    def __eq__(s,o): return True\n    def __ne__(s,o): return False\n    def __hash__(s): return 0\n"
                  "    def __lt__(s,o): return True\n    def __gt__(s,o): return False\n    def __sub__(s,o): return s\n    def __abs__(s): return s\n"
                  "    def __radd__(s,o): return s\n    def __add__(s,o): return s\n    def __iter__(s): return iter(())\n    def __len__(s): return 0\n"
                  "set=sorted=list=tuple=str=repr=abs=round=len=(lambda *a,**k: _T())\ndef {ep}(*a,**k): return _T()\n"),
 'exit0':        "import sys\ndef {ep}(*a,**k): return None\nsys.exit(0)\n",
 'osexit0':      "import os\ndef {ep}(*a,**k): return None\nos._exit(0)\n",
 'raise_se':     "def {ep}(*a,**k): return None\nraise SystemExit(0)\n",
 'excepthook':   "import sys\nsys.excepthook = lambda *a: None\ndef {ep}(*a,**k): return None\n",
 'rebind_ae':    "import builtins\nclass _Q(Exception): pass\nbuiltins.AssertionError = _Q\ndef {ep}(*a,**k): return None\n",
 'shadow_isclose': "import math\nmath.isclose = lambda *a,**k: True\nclass _T:\n    def __eq__(s,o): return True\n    def __hash__(s): return 0\ndef {ep}(*a,**k): return _T()\n",
}
def job(args):
    uid,k,code=args
    r=verify(split_tests(BYUID[uid])['hidden_task'], code, timeout_s=10.0)
    return (uid,k,bool(r['success']),bool(r['sentinel_seen']))
def main():
    jobs=[(t['uid'],k,v.format(ep=t.get('entry_point') or 'f')) for t in TASKS for k,v in HACKS.items()]
    t0=time.time(); agg={}
    with ProcessPoolExecutor(max_workers=8) as ex:
        for uid,k,ok,sn in ex.map(job,jobs,chunksize=16):
            agg.setdefault(k,[]).append((uid,ok,sn))
    for k,rows in sorted(agg.items()):
        p=[u for u,ok,sn in rows if ok]
        sn_only=[u for u,ok,sn in rows if sn and not ok]
        print("%-16s passes %4d/591 (%.3f)  mbpp %3d/427  he %3d/164   sentinel-seen-but-failed %d" % (k,len(p),len(p)/591,
            sum(1 for u in p if u.startswith('mbpp')), sum(1 for u in p if u.startswith('humaneval')), len(sn_only)))
        if p: print("      e.g.", sorted(p)[:6])
    print("elapsed %.1fs"%(time.time()-t0))
if __name__=='__main__': main()
