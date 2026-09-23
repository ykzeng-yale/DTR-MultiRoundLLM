"""E14 roster audit: source-only checks of a proposed roster. No execution, no outcome or private data read."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import e14_roster_audit as ra  # noqa: E402


@pytest.fixture(scope="module")
def rec():
    return ra.audit()


def test_every_requirement_check_passes(rec):
    assert rec["all_checks_pass"] is True, [k for k, v in rec["checks"].items() if not v]
    assert rec["checks"]["roster_equals_e12_retained_minus_e13a_checkpoints"] is True
    assert rec["checks"]["no_e13a_checkpoint_in_roster"] is True


def test_ranks_and_families_match_the_published_proposal(rec):
    expected = {"mbpp/918": (1, "PF-918"), "mbpp/825": (2, "PF-825"), "mbpp/816": (7, "PF-816"),
                "mbpp/895": (8, "PF-895"), "mbpp/868": (9, "PF-813"), "mbpp/154": (11, "PF-49"),
                "mbpp/651": (18, "PF-651"), "mbpp/499": (19, "PF-499"), "mbpp/974": (20, "PF-147")}
    got = {r: (v["frame_rank"], v["provisional_family"]) for r, v in rec["per_root"].items()}
    assert got == expected


def test_family_multiplicity_is_descriptive_not_a_claim_of_independence(rec):
    fm = rec["family_multiplicity"]
    assert set(fm["multi_member_families"]) == {"mbpp/868", "mbpp/154", "mbpp/974"}
    assert len(fm["singleton_families"]) == 6
    assert any("not nine independently sampled families" in x for x in rec["limitations"])
    assert any("not a family-independence certificate" in x for x in rec["limitations"])


def test_untouched_policy_split_is_reserved_and_disjoint(rec):
    u = rec["untouched_policy_split"]
    assert u["n"] == 138 and u["rank_range"] == [61, 198] and u["named_by_rank_only"] is True
    assert rec["checks"]["untouched_split_disjoint_from_roster"] is True
    assert rec["checks"]["roster_ranks_all_below_untouched_split"] is True


def test_no_private_or_outcome_source_was_opened(rec):
    opened = " ".join(rec["inputs"])
    for forbidden in ("private_specs", "grades.jsonl", "analysis_report", "controls_rationale"):
        assert forbidden not in opened
    assert rec["files_deliberately_not_opened"]


def test_refuses_to_overwrite(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}")
    with pytest.raises(SystemExit):
        ra.main(["--out", str(p)])
