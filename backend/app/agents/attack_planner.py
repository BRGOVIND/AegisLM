"""
Reasoning core: given AttackMemory, picks the next untried strategy in
ascending escalation-tier order. Skips already-tried strategies; returns
None when all eight strategies have been exhausted.
"""
from __future__ import annotations

from typing import Optional

from app.agents.strategy_engine import Strategy, STRATEGIES_BY_TIER
from app.agents.attack_memory import AttackMemory


class AttackPlanner:
    def __init__(self, strategies: list[Strategy] | None = None) -> None:
        self._strategies: list[Strategy] = strategies or list(STRATEGIES_BY_TIER)

    def next_strategy(self, memory: AttackMemory) -> Optional[Strategy]:
        """Return the lowest-tier untried strategy, or None if all tried."""
        tried = memory.tried_strategy_names()
        for strategy in self._strategies:
            if strategy.name not in tried:
                return strategy
        return None

    def remaining_count(self, memory: AttackMemory) -> int:
        tried = memory.tried_strategy_names()
        return sum(1 for s in self._strategies if s.name not in tried)
