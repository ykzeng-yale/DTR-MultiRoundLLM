from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

spec=spec_from_file_location("audit_existing_evidence",Path(__file__).resolve().parents[1]/"scripts/audit_existing_evidence.py")
audit=module_from_spec(spec)
spec.loader.exec_module(audit)


def test_paired_components_always_share_cohort():
    result=audit.paired_summary([{"a":1,"b":.5},{"a":0,"b":.2}],"a","b")
    assert result["difference"]["mean"]==pytest.approx(result["left"]["mean"]-result["right"]["mean"])
    assert result["left"]["n_tasks"]==result["right"]["n_tasks"]==2


def test_baseline_uses_visible_only_for_stopping():
    # Hidden success of the second candidate cannot override the first visible pass.
    records=[{"hidden":0,"visible":True,"tokens":2},{"hidden":1,"visible":False,"tokens":3}]
    out=audit.ordered_baseline(records,2)
    assert out["success"]==0
    assert out["calls"]==1.5
    assert out["tokens"]==3.5


def test_fixed_receiver_ipw_keeps_switchers_with_zero_weight():
    ds=[{"model_alias":"small","b_obs":.5},{"model_alias":"small","b_obs":.5},{"model_alias":"small","b_obs":.5}]
    assert audit.fixed_receiver_weight(ds)==4
    ds[1]["model_alias"]="large"
    assert audit.fixed_receiver_weight(ds)==0


def test_route_propensity_cannot_be_missing():
    with pytest.raises(ValueError):
        audit.fixed_receiver_weight([{"model_alias":"small"},{"model_alias":"small"}])
