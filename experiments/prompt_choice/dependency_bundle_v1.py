"""Hash-bound dependency inventory. Data-only validation; no package import."""
import hashlib
import json
from pathlib import Path
import stat

MAX_BYTES=512<<20
MAX_FILES=20000


def inventory(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('bundle must be a real directory')
    root=root.resolve()
    files=[];total=0
    for p in sorted(root.rglob('*')):
        st=p.lstat()
        if stat.S_ISLNK(st.st_mode):raise ValueError('bundle symlink refused')
        if stat.S_ISDIR(st.st_mode):continue
        if not stat.S_ISREG(st.st_mode):raise ValueError('nonregular bundle member')
        rel=p.relative_to(root).as_posix()
        if p.suffix=='.pth':raise ValueError('site hook refused')
        total+=st.st_size
        if total>MAX_BYTES or len(files)>=MAX_FILES:raise ValueError('bundle cap exceeded')
        files.append({'path':rel,'bytes':st.st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    if not files:raise ValueError('empty bundle')
    payload={'files':files,'total_bytes':total}
    h=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {**payload,'tree_sha256':h}


def verify(root,expected):
    if type(expected) is not str or len(expected)!=64:raise ValueError('invalid tree hash')
    actual=inventory(root)
    if actual['tree_sha256']!=expected:raise ValueError('dependency tree mismatch')
    return actual
