"""Source-freeze/qualification CLI; live execution belongs to lead dispatch."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.containment import stdio_sprint_qualification_v2 as qualification
from experiments.measurement_sprint_v2.runtime_v2 import canonical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--make-plan')
    parser.add_argument('--plan')
    parser.add_argument('--out')
    parser.add_argument('--freeze', default='freeze.txt')
    args = parser.parse_args()
    if args.make_plan:
        if args.plan or args.out:
            parser.error('source freeze is separate from execution')
        with Path(args.make_plan).open('xb') as f:
            f.write(canonical(qualification.make_plan(ROOT))+b'\n')
    elif args.plan and args.out:
        qualification.run(args.plan, args.out, root=ROOT, freeze_path=args.freeze)
    else:
        parser.error('--make-plan PATH or --plan PATH --out FRESH_DIRECTORY')


if __name__ == '__main__':
    main()
