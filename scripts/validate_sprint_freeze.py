"""Validate a full immutable Git commit before staging any experiment."""
import re
import subprocess

def full_commit(repo='.'):
    value=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if re.fullmatch(r'[0-9a-f]{40}',value) is None:
        raise ValueError('full 40-character immutable commit required')
    return value

if __name__=='__main__':
    print(full_commit())
