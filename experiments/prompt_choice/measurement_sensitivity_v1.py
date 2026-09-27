"""Exact endpoint sensitivity, conditional on externally justified error bounds.

Does not estimate error from handpicked controls or assert semantic correctness.
Classical expectation/union-bound arithmetic; no new identification theorem.
"""
from fractions import Fraction
from experiments.prompt_choice.paired_inference import exact


def semantic_contrast_interval(grade_lower,grade_upper,*,false_positive_policy,false_negative_policy,false_positive_baseline,false_negative_baseline):
    lo=exact(grade_lower);hi=exact(grade_upper)
    if not -1<=lo<=hi<=1:raise ValueError('invalid graded contrast interval')
    bounds=[exact(x) for x in (false_positive_policy,false_negative_policy,false_positive_baseline,false_negative_baseline)]
    if any(not 0<=x<=1 for x in bounds):raise ValueError('error masses must be in [0,1]')
    up,vp,ub,vb=bounds
    return max(Fraction(-1),lo-up-vb),min(Fraction(1),hi+vp+ub)


def usefulness(interval,threshold=Fraction(1,20)):
    lo,hi=map(exact,interval);threshold=exact(threshold)
    if not -1<=lo<=hi<=1 or not 0<=threshold<=1:raise ValueError('invalid interval or threshold')
    return 'benefit' if lo>threshold else 'useful_gain_futility' if hi<threshold else 'inconclusive'
