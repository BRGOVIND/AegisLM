"""Per-session record of attack attempts and their outcomes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Attempt:
    strategy_name: str
    escalation_tier: int
    prompt: str
    response: str
    verdict: str          # PASS / FAIL / UNCERTAIN
    failure_reason: Optional[str] = None  # judge's reason when model resisted


class AttackMemory:
    """Tracks every attempt in a single agent session."""

    def __init__(self) -> None:
        self._attempts: list[Attempt] = []

    def record(self, attempt: Attempt) -> None:
        self._attempts.append(attempt)

    def tried_strategy_names(self) -> set[str]:
        return {a.strategy_name for a in self._attempts}

    def last_failure_reason(self) -> Optional[str]:
        for attempt in reversed(self._attempts):
            if attempt.failure_reason:
                return attempt.failure_reason
        return None

    def all_attempts(self) -> list[Attempt]:
        return list(self._attempts)

    def attempt_count(self) -> int:
        return len(self._attempts)
