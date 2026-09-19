#!/usr/bin/env python3
"""Build the human-readable research package (requires Pandoc and XeLaTeX)."""
import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    "docs/research_proposal.md",
    "docs/theory.md",
    "docs/training_and_serving.md",
    "docs/experiment_protocol.md",
    "results/synthetic_reference_v1/REPORT.md",
    "docs/experiment_handoff.md",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    work = ROOT / "work" / "report"
    work.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = """---
title: 'Causal Value Models for Adaptive Prompting'
subtitle: 'Theory, statistical reference, and experimental-agent protocol'
date: '19 September 2026'
author: 'DTR-MultiRoundLLM research development package'
toc: true
toc-depth: 2
colorlinks: true
linkcolor: blue
urlcolor: blue
geometry: margin=0.8in
fontsize: 10pt
mainfont: Times New Roman
monofont: Menlo
header-includes:
  - '\\usepackage{microtype}'
  - '\\usepackage{longtable,booktabs,array}'
  - '\\setlength{\\emergencystretch}{3em}'
---

\\newpage

This package develops supported history-conditional prompt effects and policy value for repeated interaction with a fixed receiver model. It includes mathematical proofs, a reproducible synthetic statistical reference, and a concrete protocol for the next experimental agent. Real-model efficacy, trained neural calibration, and unrestricted prompt optimality remain unestablished.

The maintained repository, complete literature audit, proof-review record, code, raw synthetic results, and work-package issues are available at [DTR-MultiRoundLLM](https://github.com/ykzeng-yale/DTR-MultiRoundLLM). This PDF is a dated development snapshot.
"""
    for name in DOCS:
        source = ROOT / name
        content = source.read_text().replace("∎", r"$\square$")
        content = re.sub(r"(?m)^(uv run .{100,})$", lambda m: m.group(0).replace(" --", " \\\n  --"), content)
        def link(match):
            label, target = match.groups()
            if target.startswith(("http:", "https:", "#")):
                return match.group(0)
            relative = (source.parent / target).resolve().relative_to(ROOT)
            return f"[{label}](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/blob/theory/causal-prompt-package/{relative.as_posix()})"
        content = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, content)
        text += "\n\\clearpage\n\n" + content + "\n"
    md = work / "research_package.md"
    md.write_text(text)
    subprocess.run(["pandoc", str(md), "--from=markdown+tex_math_single_backslash", "--standalone", "--pdf-engine=xelatex", "--output", str(args.output)], check=True)
    print(args.output)


if __name__ == "__main__":
    main()
