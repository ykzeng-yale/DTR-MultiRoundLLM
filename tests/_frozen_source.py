"""Resolve a historical freeze against the Git blobs it was frozen at, never the current checkout."""
import hashlib, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def frozen_source_hashes(commit):
    names = subprocess.check_output(["git", "ls-tree", "--name-only", commit, "experiments/landmark/"],
                                    cwd=ROOT, text=True).split()
    return {Path(n).name: hashlib.sha256(subprocess.check_output(["git", "show", f"{commit}:{n}"], cwd=ROOT)).hexdigest()
            for n in sorted(names) if n.endswith(".py")}
