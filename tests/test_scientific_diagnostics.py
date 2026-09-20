"""Protect scientific diagnostic contrasts, including nonadherent trajectories."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from diagnose_repair_mechanisms import episode_scores
from diagnose_matched_estimators import matched


def test_switched_episode_keeps_observed_initial_baseline():
    e=dict(success_first_candidate=1,success=0,completion_tokens=12,decisions=[
        dict(model_alias='a',validation={'passed':False},completion_tokens=5),
        dict(model_alias='b',eligible=True,completed=True,b_obs=.5,completion_tokens=7)])
    s=episode_scores(e)
    assert s['weight']==0
    assert s['baseline_augmented_final']==1
    assert s['raw_total_gain']==-1
    assert s['net_repair_gain']==0
    assert s['baseline_imbalance']==-1


def test_perfect_constant_q_makes_matched_plugin_and_dr_agree():
    n=100
    d=dict(task=np.repeat(np.arange(20),5),Y=np.ones(n),S=np.ones((n,1),int),
           A=np.tile(np.arange(5),20)[:,None],B=np.full((n,1),.2),elig=np.ones((n,1),bool))
    plugin,dr=matched(d,1,np.random.default_rng(31))
    assert plugin==pytest.approx(1)
    assert dr[0]==pytest.approx(1)
    assert dr[1]==pytest.approx(0)
