"""Deterministic hypothetical count scenarios, not power or receiver results."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.prompt_choice.paired_inference import kl_interval, serialize


def build():
    rows = []
    for n in (100, 200, 400, 800, 1000):
        for discordance in (Fraction(1, 10), Fraction(3, 10), Fraction(1, 2)):
            for difference in (Fraction(0), Fraction(1, 20), Fraction(1, 10), Fraction(3, 20)):
                if difference > discordance:
                    continue
                positive = (discordance + difference) / 2
                negative = (discordance - difference) / 2
                if (positive*n).denominator != 1 or (negative*n).denominator != 1:
                    continue  # only realizable integer-count scenarios
                lp, up, _ = kl_interval(positive, n, Fraction(1, 20))
                lm, um, _ = kl_interval(negative, n, Fraction(1, 20))
                lower, upper = lp-um, up-lm
                threshold = Fraction(1, 20)
                rows.append(dict(n_families=n, positive_count=int(positive*n),
                    negative_count=int(negative*n), zero_count=int((1-discordance)*n),
                    observed_difference=serialize(difference), discordance=serialize(discordance),
                    lower=serialize(lower), upper=serialize(upper),
                    display_interval=[float(lower), float(upper)],
                    decision=('useful_benefit' if lower > threshold else
                              'useful_gain_futility' if upper < threshold else 'inconclusive'),
                    maximum_research_receiver_calls=4*n))
    source = ROOT/'experiments/prompt_choice/paired_inference.py'
    return dict(classification='hypothetical observed-count arithmetic; not power, simulation, or receiver results',
        assumptions=['complete binary paired outcomes, one root per family',
                     'independent family vectors conditional on frozen development',
                     'equal family weights and target-aligned sampling law',
                     'accepted two-contrast eight-tail allocation alpha=0.05'],
        limitations=['one contrast at a time; no joint success probability',
                     'no missingness or measurement-error inflation',
                     'four calls/root excludes development and operational qualification',
                     'n is hypothetical, not an eligible-family inventory'],
        inference_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), scenarios=rows)


if __name__ == '__main__':
    print(json.dumps(build(), indent=2, sort_keys=True))
