#!/usr/bin/env python3
"""Decompose fixed-receiver repair gains using immutable logged outcomes only.

No model calls, candidate execution, hidden-label policy, or source-log mutation.
All conditional outcome-stratum summaries are descriptive mechanisms, not
causal effects of interventions on a mediator or a deployable oracle policy.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
from itertools import permutations
import json
from pathlib import Path
import time

import numpy as np

EXPECTED_SHA256="e643ee44c7ef658fff65efb5e17763ee78c990d21184d060f5823025a100414e"
ROOT=Path(__file__).resolve().parents[1]


def mean_ci(values):
    x=np.asarray(values,float)
    se=float(x.std(ddof=1)/np.sqrt(len(x)))
    return {"mean":float(x.mean()),"se":se,"ci95":[float(x.mean()-1.96*se),float(x.mean()+1.96*se)],"n_tasks":len(x)}


def ratio_ci(numerators,denominators):
    """Ratio of root means, delta-method root-cluster uncertainty."""
    a,b=np.asarray(numerators,float),np.asarray(denominators,float)
    if b.mean()<=0:
        return None
    ratio=float(a.mean()/b.mean())
    influence=(a-ratio*b)/b.mean()
    se=float(influence.std(ddof=1)/np.sqrt(len(a)))
    return {"ratio":ratio,"se":se,"ci95":[ratio-1.96*se,ratio+1.96*se],"n_tasks":len(a),"denominator_mean":float(b.mean())}


def fixed_weight(ds):
    first_model=ds[0]["model_alias"]
    weight=1.
    for d in ds[1:]:
        if not d.get("eligible") or not d.get("completed") or d["b_obs"]!=.5:
            raise ValueError("source routing contract changed")
        if d["model_alias"]!=first_model:
            weight=0.
        else:
            weight/=d["b_obs"]
    return weight


def episode_scores(episode):
    ds=episode["decisions"]
    y0,yt=int(episode["success_first_candidate"]),int(episode["success"])
    visible=bool(ds[0]["validation"]["passed"])
    if visible and (len(ds)!=1 or y0!=yt):
        raise ValueError("initial-pass absorbing convention violated")
    if not visible and len(ds)<=1:
        raise ValueError("initial-failure continuation convention violated")
    w=fixed_weight(ds)
    repair=w*(1-y0)*yt
    damage=w*y0*(1-yt)
    net=repair-damage
    remainder=(w-1)*y0
    row={"initial_success":y0,"raw_ipw_final":w*yt,"repair":repair,"degradation":damage,
         "net_repair_gain":net,"baseline_imbalance":remainder,"raw_total_gain":w*yt-y0,
         "baseline_augmented_final":y0+net,"weight":w,
         "initial_failure":1-y0,"visible_pass":float(visible),"visible_fail":float(not visible),
         "early_false_pass":float(visible and not y0),"true_pass":float(visible and y0),
         "unnecessary_repair_entry":float(not visible and y0),"accessible_wrong":float(not visible and not y0),
         "oracle_ceiling_same_first_stop_gate":1-float(visible and not y0),
         "ipw_visible_fail_mass":w*(not visible),"ipw_accessible_wrong_mass":w*(not visible)*(1-y0),
         "ipw_unnecessary_repair_entry":w*(not visible)*y0,
         "raw_ipw_calls":w*len(ds),"augmented_calls":1+w*(len(ds)-1),
         "raw_ipw_completion_tokens":w*episode["completion_tokens"],
         "augmented_completion_tokens":ds[0]["completion_tokens"]+w*(episode["completion_tokens"]-ds[0]["completion_tokens"]),
         "final_failure_ipw":w*(1-yt),
         "same_gate_final_failure_on_accessible_wrong":w*(not visible)*(1-y0)*(1-yt)}
    for calls in (1,2,3):
        row[f"ipw_calls_{calls}_mass"]=w*(len(ds)==calls)
        row[f"ipw_calls_{calls}_repair"]=repair*(len(ds)==calls)
        row[f"ipw_calls_{calls}_degradation"]=damage*(len(ds)==calls)
    if abs(row["raw_total_gain"]-net-remainder)>1e-12:
        raise AssertionError("gain decomposition broken")
    return row


def bon_scores(episodes,k):
    """Exact ordered-distinct-draw expectation, with the same first-output anchor."""
    scores=[]
    for order in permutations(range(len(episodes)),k):
        first=episodes[order[0]]
        y0=int(first["success_first_candidate"])
        chosen=None
        tokens=0
        for position,index in enumerate(order):
            candidate=episodes[index]
            tokens+=candidate["decisions"][0]["completion_tokens"]
            if candidate["decisions"][0]["validation"]["passed"] or position==k-1:
                chosen=candidate
                break
        y=int(chosen["success_first_candidate"])
        oracle=int(any(episodes[i]["success_first_candidate"] for i in order))
        scores.append({"success":y,"repair":(1-y0)*y,"degradation":y0*(1-y),
                       "net_gain":y-y0,"calls":position+1,"tokens":tokens,
                       "oracle_bank_success":oracle,"residual_selection_headroom":oracle-y,
                       "unused_after_first_false_pass_headroom":int(first["decisions"][0]["validation"]["passed"] and not y0 and oracle),
                       "all_draws_wrong":int(not oracle),
                       "mixed_draws":int(any(episodes[i]["success_first_candidate"] for i in order) and not all(episodes[i]["success_first_candidate"] for i in order))})
    return {key:float(np.mean([row[key] for row in scores])) for key in scores[0]}


def summarize_group(rows):
    keys=[k for k,v in rows[0].items() if isinstance(v,(float,int))]
    output={"n_tasks":len(rows),"means":{k:mean_ci([r[k] for r in rows]) for k in keys},"ratios":{}}
    ratios={
        "initial_failures_stopped_by_false_pass":("early_false_pass","initial_failure"),
        "visible_failure_cases_already_correct":("unnecessary_repair_entry","visible_fail"),
        "visible_pass_cases_wrong":("early_false_pass","visible_pass"),
        "repair_rate_among_accessible_initially_wrong":("repair","accessible_wrong"),
        "degradation_rate_among_unnecessary_repair_entries":("degradation","unnecessary_repair_entry"),
        "net_gain_per_observed_first_failure":("net_repair_gain","visible_fail"),
        "observed_repair_rate_weighted_denominator":("repair","ipw_accessible_wrong_mass"),
        "observed_degradation_rate_weighted_denominator":("degradation","ipw_unnecessary_repair_entry"),
    }
    for name,(a,b) in ratios.items():
        output["ratios"][name]=ratio_ci([r[a] for r in rows],[r[b] for r in rows])
    output["decomposition_residual_max"]=max(abs(r["raw_total_gain"]-r["net_repair_gain"]-r["baseline_imbalance"]) for r in rows)
    for k in (2,3,4):
        # These compare intervention policies sharing the initial candidate law.
        output[f"augmented_repair_minus_bon{k}"]=mean_ci([r["baseline_augmented_final"]-r[f"bon{k}_success"] for r in rows])
        output[f"net_repair_minus_bon{k}_net"]=mean_ci([r["net_repair_gain"]-r[f"bon{k}_net_gain"] for r in rows])
    return output


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--episodes",type=Path,required=True)
    ap.add_argument("--output",type=Path,default=ROOT/"results/mechanism_diagnosis_20260920")
    a=ap.parse_args()
    raw=a.episodes.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=EXPECTED_SHA256:
        raise ValueError("raw log hash differs from audited source")
    a.output.mkdir(parents=True,exist_ok=True)
    if any(a.output.iterdir()):
        raise ValueError("output must be empty")
    start=time.monotonic()
    episodes=[json.loads(line) for line in raw.splitlines()]
    groups=defaultdict(list)
    for episode in episodes:
        if episode.get("error") or episode.get("mock"):
            raise ValueError("source contains failure/mock outside frozen audit assumptions")
        groups[episode["task_uid"],episode["decisions"][0]["model_alias"]].append(episode)
    root_rows=[]
    for (uid,model),records in sorted(groups.items()):
        if len(records)!=4:
            raise ValueError("expected four initial draws per root and model")
        episode_rows=[episode_scores(r) for r in records]
        row={"uid":uid,"model":model,"benchmark":records[0]["benchmark"],"split":records[0]["split"]}
        row.update({key:float(np.mean([x[key] for x in episode_rows])) for key in episode_rows[0]})
        for k in (2,3,4):
            row.update({f"bon{k}_{key}":value for key,value in bon_scores(records,k).items()})
        root_rows.append(row)
    output={"source_sha256":sha,"source_episodes":len(episodes),
            "interpretation":"exploratory benchmark-root means and ratios; families unresolved; no hidden-label policy; no mediated causal effects",
            "estimand":"fixed initial receiver and same receiver on subsequent eligible repair calls; initial model assignment conditioned on",
            "by_receiver":{},"by_receiver_benchmark":{}}
    for model in sorted({row["model"] for row in root_rows}):
        output["by_receiver"][model]=summarize_group([r for r in root_rows if r["model"]==model])
        for benchmark in sorted({row["benchmark"] for row in root_rows}):
            rows=[r for r in root_rows if r["model"]==model and r["benchmark"]==benchmark]
            output["by_receiver_benchmark"][model+":"+benchmark]=summarize_group(rows)
    (a.output/"summary.json").write_text(json.dumps(output,indent=2)+"\n")
    (a.output/"root_scores.jsonl").write_text("".join(json.dumps(r)+"\n" for r in root_rows))
    (a.output/"manifest.json").write_text(json.dumps({"source":str(a.episodes),"source_sha256":sha,
        "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"seconds":time.monotonic()-start,
        "external_model_calls":0,"candidate_executions":0,"paid_spend_usd":0,"numpy_version":np.__version__},indent=2)+"\n")
    print(json.dumps({"output":str(a.output),"seconds":time.monotonic()-start}))


if __name__=="__main__":
    main()
