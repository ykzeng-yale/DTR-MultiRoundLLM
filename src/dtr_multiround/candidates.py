"""A finite-slate logging and overlap contract, conditional on a fixed generator.

The selector probability is conditional on the realized slate. It is not the
probability that a generator emitted that slate or any candidate text. Exact
text and payload hashes distinguish treatment versions; embeddings cannot.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from math import isfinite
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    text: str
    kind: str = "PROMPT"

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SelectionRecord:
    task_id: str
    episode_id: str
    stage: int
    history_sha256: str
    receiver_version: str
    generator_version: str
    candidates: tuple[Candidate, ...]
    selected_id: str
    behavior_probabilities: Mapping[str, float]

    def validate(self) -> None:
        if not all((self.task_id, self.episode_id, self.receiver_version, self.generator_version)):
            raise ValueError("task, episode, receiver, and generator identities required")
        if self.stage < 1 or len(self.history_sha256) != 64:
            raise ValueError("positive stage and complete history SHA256 required")
        try:
            int(self.history_sha256, 16)
        except ValueError as exc:
            raise ValueError("history_sha256 must be hexadecimal") from exc
        ids = [c.candidate_id for c in self.candidates]
        if not ids or len(set(ids)) != len(ids) or any(not identifier for identifier in ids):
            raise ValueError("nonempty unique candidate IDs required")
        if any(c.kind not in ("PROMPT", "STOP") for c in self.candidates):
            raise ValueError("candidate kind must be PROMPT or STOP")
        if sum(c.kind == "STOP" for c in self.candidates) != 1:
            raise ValueError("one explicit STOP candidate required")
        if self.selected_id not in ids:
            raise ValueError("selected candidate must belong to the logged slate")
        _validate_probabilities(self.behavior_probabilities, ids)
        if self.behavior_probabilities[self.selected_id] <= 0:
            raise ValueError("selected candidate must have positive behavior probability")


def _validate_probabilities(probabilities: Mapping[str, float], ids: Sequence[str]) -> None:
    if set(probabilities) != set(ids):
        raise ValueError("one probability per candidate ID required")
    if any(not isfinite(p) or p < 0 for p in probabilities.values()):
        raise ValueError("probabilities must be finite and nonnegative")
    if abs(sum(probabilities.values()) - 1.0) > 1e-10:
        raise ValueError("probabilities must sum to one")


def selector_ratio(record: SelectionRecord, target_probabilities: Mapping[str, float], target_generator_version: str) -> float:
    record.validate()
    if target_generator_version != record.generator_version:
        raise ValueError("changed generator requires generator-density correction or fresh randomized collection")
    _validate_probabilities(target_probabilities, [c.candidate_id for c in record.candidates])
    unsupported = [key for key, p in target_probabilities.items() if p > 0 and record.behavior_probabilities[key] <= 0]
    if unsupported:
        raise ValueError(f"unsupported target candidates: {unsupported}")
    return target_probabilities[record.selected_id] / record.behavior_probabilities[record.selected_id]


def supported_greedy_selection(record: SelectionRecord, values: Mapping[str, float]) -> str:
    """Choose an ID only among behavior-supported candidates, with stable ties."""
    record.validate()
    if set(values) != {c.candidate_id for c in record.candidates} or any(not isfinite(v) for v in values.values()):
        raise ValueError("one finite value per candidate required")
    supported = [c.candidate_id for c in record.candidates if record.behavior_probabilities[c.candidate_id] > 0]
    return max(supported, key=lambda candidate: values[candidate])
