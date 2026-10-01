"""Data-only, bounded physical inventory for an owned evidence tree.

No imports or execution of evidence files. Do not treat a partial inventory as
capacity evidence. Follow no links; count logical bytes even for hard links.
"""
import os
import stat
import time


def inventory(root, *, seconds=60, max_entries=2000000, max_bytes=100<<30):
    root=os.path.abspath(root)
    if os.path.islink(root) or not os.path.isdir(root):
        raise ValueError('regular owned directory required')
    deadline=time.monotonic()+seconds
    pending=[root];entries=files=total=0
    while pending:
        if time.monotonic()>=deadline:
            raise TimeoutError('incomplete inventory; no capacity conclusion')
        with os.scandir(pending.pop()) as scan:
            for entry in scan:
                entries+=1
                if entries>max_entries or time.monotonic()>=deadline:
                    raise TimeoutError('incomplete inventory; no capacity conclusion')
                info=entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):pending.append(entry.path)
                elif stat.S_ISREG(info.st_mode):
                    files+=1;total+=info.st_size
                    if total>max_bytes:raise ValueError('retained byte cap exceeded')
                else:raise ValueError('nonregular evidence entry refused')
    return {'complete':True,'files':files,'entries':entries,'bytes':total}
