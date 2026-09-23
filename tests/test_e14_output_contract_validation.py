"""Static validation of terminal-output-contract-v1 against the frozen instrument. No execution."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import e14_output_contract_validation as v  # noqa: E402


@pytest.fixture(scope="module")
def rec():
    return v.build()


def test_every_fixture_matches_its_predeclared_verdict(rec):
    assert rec["all_fixtures_agree"] is True, [k for k, f in rec["fixtures"].items() if not f["agrees"]]


def test_the_fence_clause_is_unenforceable_by_the_frozen_extractor(rec):
    """The load-bearing finding: unfenced output violates the contract but the instrument scores it normally."""
    unfenced = rec["fixtures"]["unfenced"]
    assert unfenced["observed_contract_compliant"] is False
    assert unfenced["observed_instrument_scoreable"] is True
    assert "NOT enforceable" in rec["enforceability_finding"]
    assert rec["instrument"]["scorer_changed"] is False


def test_ambiguous_fencing_is_what_the_instrument_actually_rejects(rec):
    assert rec["fixtures"]["two_blocks"]["clauses"]["not_ambiguously_fenced"] is False
    assert rec["fixtures"]["compliant_minimal"]["clauses"]["not_ambiguously_fenced"] is True


def test_saved_outputs_fail_only_the_fence_clause_in_the_fresh_arm(rec):
    per_clause = rec["e13a_saved_outputs_descriptive"]["per_clause"]
    fresh = per_clause["FRESH"]
    assert fresh["fenced_block_present"]["true"] == 0          # none fenced
    for clause in ("not_ambiguously_fenced", "parses_as_python", "only_function_and_imports",
                   "no_test_calls_or_asserts", "no_diagnostic_text_copied"):
        assert fresh[clause]["true"] == 30, clause              # every substantive clause satisfied
    r1 = per_clause["R1"]
    assert r1["parses_as_python"]["true"] == 17
    assert r1["no_diagnostic_text_copied"]["false"] == 6        # six echo the diagnostic report


def test_descriptive_claim_is_fenced_off_from_any_mechanism_claim(rec):
    note = rec["e13a_saved_outputs_descriptive"]["note"]
    assert "does not repair" in note and "identifies no formatting mechanism" in note
    assert any("containment run" in x for x in rec["not_validated_here"])


def test_refuses_to_overwrite(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}")
    with pytest.raises(SystemExit):
        v.main(["--out", str(p)])
