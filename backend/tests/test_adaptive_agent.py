"""Tests for the adaptive red-team agent: strategy switching, safety bounds, analytics."""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from sqlalchemy import select

from app.agents.adaptive_agent import run_adaptive_agent
from app.agents.attack_memory import AttackMemory, Attempt
from app.agents.attack_planner import AttackPlanner
from app.agents.strategy_engine import STRATEGY_REGISTRY, STRATEGIES_BY_TIER
from app.db.models import AgentRun, AgentFinding
from app.evaluators.judge import JudgeResult


# ---------------------------------------------------------------------------
# Helpers (shared with test_agent.py pattern)
# ---------------------------------------------------------------------------

def db_factory(session):
    @asynccontextmanager
    async def _factory():
        yield session
    return _factory


def _pass_result(reason: str = "model refused") -> JudgeResult:
    return JudgeResult(verdict="PASS", confidence=0.9, reason=reason, risk_level="none", judge_model="mock")


def _fail_result() -> JudgeResult:
    return JudgeResult(verdict="FAIL", confidence=0.9, reason="complied", risk_level="high", judge_model="mock")


async def _create_run(db, max_rounds=8, max_total_tokens=20000, wall_clock_timeout_s=120) -> AgentRun:
    run = AgentRun(
        model_name="test-model",
        target_category="PROMPT_INJECTION",
        max_rounds=max_rounds,
        max_total_tokens=max_total_tokens,
        wall_clock_timeout_s=wall_clock_timeout_s,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


# ---------------------------------------------------------------------------
# Strategy engine
# ---------------------------------------------------------------------------

def test_strategy_registry_has_eight_strategies():
    assert len(STRATEGY_REGISTRY) == 8


def test_strategies_sorted_by_tier():
    tiers = [s.escalation_tier for s in STRATEGIES_BY_TIER]
    assert tiers == sorted(tiers)


def test_strategy_craft_attack_uses_template():
    strat = STRATEGY_REGISTRY["direct_override"]
    result = strat.craft_attack("test goal", "PROMPT_INJECTION")
    assert "test goal" in result
    assert len(result) > 10


def test_strategy_tier_1_is_direct_override():
    tier1 = [s for s in STRATEGIES_BY_TIER if s.escalation_tier == 1]
    assert len(tier1) == 1
    assert tier1[0].name == "direct_override"


# ---------------------------------------------------------------------------
# Attack memory
# ---------------------------------------------------------------------------

def test_memory_records_attempts():
    mem = AttackMemory()
    mem.record(Attempt("roleplay", 2, "p1", "r1", "PASS", "refused due to policy"))
    assert mem.attempt_count() == 1
    assert "roleplay" in mem.tried_strategy_names()


def test_memory_last_failure_reason():
    mem = AttackMemory()
    mem.record(Attempt("direct_override", 1, "p", "r", "PASS", "safety filter activated"))
    mem.record(Attempt("roleplay", 2, "p2", "r2", "PASS", "refused hypothetical"))
    assert mem.last_failure_reason() == "refused hypothetical"


def test_memory_tried_strategies_excludes_successes():
    mem = AttackMemory()
    mem.record(Attempt("direct_override", 1, "p", "r", "FAIL", None))
    assert "direct_override" in mem.tried_strategy_names()


# ---------------------------------------------------------------------------
# Attack planner
# ---------------------------------------------------------------------------

def test_planner_picks_lowest_tier_first():
    planner = AttackPlanner()
    mem = AttackMemory()
    strat = planner.next_strategy(mem)
    assert strat is not None
    assert strat.escalation_tier == 1


def test_planner_skips_tried_strategies():
    planner = AttackPlanner()
    mem = AttackMemory()
    mem.record(Attempt("direct_override", 1, "p", "r", "PASS", "refused"))
    strat = planner.next_strategy(mem)
    assert strat is not None
    assert strat.name != "direct_override"
    assert strat.escalation_tier >= 1


def test_planner_escalates_tier():
    planner = AttackPlanner()
    mem = AttackMemory()
    # Try tier-1 strategy
    mem.record(Attempt("direct_override", 1, "p", "r", "PASS", "blocked"))
    next_s = planner.next_strategy(mem)
    assert next_s is not None
    assert next_s.escalation_tier >= 2


def test_planner_returns_none_when_all_exhausted():
    planner = AttackPlanner()
    mem = AttackMemory()
    for name in STRATEGY_REGISTRY:
        mem.record(Attempt(name, 1, "p", "r", "PASS", "blocked"))
    assert planner.next_strategy(mem) is None


# ---------------------------------------------------------------------------
# Adaptive agent integration — acceptance test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adaptive_agent_switches_strategy_on_failure(db_session):
    """
    Acceptance test: mock judge fails first two strategies (PASS = resisted),
    succeeds on third (FAIL = compromised). Assert agent used 3 distinct
    strategies in ascending escalation order, then stopped.
    """
    run = await _create_run(db_session, max_rounds=8)

    call_count = 0

    async def staged_judge(attack_prompt, model_response, judge_model="llama3.2"):
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            return _fail_result()
        return _pass_result(reason=f"blocked attempt {call_count}")

    with (
        patch("app.agents.adaptive_agent.judge_response", side_effect=staged_judge),
        patch("app.benchmarking.benchmark_runner.default_ollama_call", return_value=("response", 50)),
        # Force template fallback by making LLM unavailable
        patch("app.agents.adaptive_agent._generate_via_ollama", side_effect=Exception("no LLM")),
    ):
        await run_adaptive_agent(
            agent_run_id=run.id,
            model_name="test-model",
            target_category="PROMPT_INJECTION",
            max_rounds=8,
            max_total_tokens=20000,
            wall_clock_timeout_s=120.0,
            generator_model="llama3.2",
            judge_model="llama3.2",
            db_factory=db_factory(db_session),
        )

    await db_session.refresh(run)
    assert run.outcome == "compromised"
    assert run.rounds_completed == 3

    findings = (await db_session.execute(
        select(AgentFinding)
        .where(AgentFinding.agent_run_id == run.id)
        .order_by(AgentFinding.round_number)
    )).scalars().all()

    assert len(findings) == 3
    strategies_used = [f.strategy for f in findings]
    # All three must be distinct
    assert len(set(strategies_used)) == 3
    # Escalation tiers must be non-decreasing
    tiers = [f.escalation_tier for f in findings]
    assert tiers == sorted(tiers), f"tiers not in order: {tiers}"
    # Third finding is the success
    assert findings[2].verdict == "FAIL"


@pytest.mark.asyncio
async def test_adaptive_agent_strategies_exhausted(db_session):
    """When all 8 strategies fail, outcome is strategies_exhausted."""
    run = await _create_run(db_session, max_rounds=20)  # enough rounds

    with (
        patch("app.agents.adaptive_agent.judge_response", return_value=_pass_result()),
        patch("app.benchmarking.benchmark_runner.default_ollama_call", return_value=("response", 50)),
        patch("app.agents.adaptive_agent._generate_via_ollama", side_effect=Exception()),
    ):
        await run_adaptive_agent(
            agent_run_id=run.id,
            model_name="test-model",
            target_category="JAILBREAK",
            max_rounds=20,
            max_total_tokens=200000,
            wall_clock_timeout_s=3600.0,
            generator_model="llama3.2",
            judge_model="llama3.2",
            db_factory=db_factory(db_session),
        )

    await db_session.refresh(run)
    assert run.outcome == "strategies_exhausted"

    findings = (await db_session.execute(
        select(AgentFinding).where(AgentFinding.agent_run_id == run.id)
    )).scalars().all()
    # Should have tried all 8 strategies
    assert len(findings) == 8
    assert len({f.strategy for f in findings}) == 8


# ---------------------------------------------------------------------------
# Safety bounds still work in adaptive agent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adaptive_agent_respects_round_cap(db_session):
    run = await _create_run(db_session, max_rounds=2)

    with (
        patch("app.agents.adaptive_agent.judge_response", return_value=_pass_result()),
        patch("app.benchmarking.benchmark_runner.default_ollama_call", return_value=("ok", 50)),
        patch("app.agents.adaptive_agent._generate_via_ollama", side_effect=Exception()),
    ):
        await run_adaptive_agent(
            agent_run_id=run.id,
            model_name="test-model",
            target_category="JAILBREAK",
            max_rounds=2,
            max_total_tokens=20000,
            wall_clock_timeout_s=120.0,
            generator_model="llama3.2",
            judge_model="llama3.2",
            db_factory=db_factory(db_session),
        )

    await db_session.refresh(run)
    assert run.rounds_completed <= 2
    assert run.outcome == "rounds_exhausted"


@pytest.mark.asyncio
async def test_adaptive_agent_respects_token_budget(db_session):
    run = await _create_run(db_session, max_rounds=20, max_total_tokens=50)
    long_response = "x" * 2000  # ~500 tokens

    with (
        patch("app.agents.adaptive_agent.judge_response", return_value=_pass_result()),
        patch("app.benchmarking.benchmark_runner.default_ollama_call", return_value=(long_response, 9999)),
        patch("app.agents.adaptive_agent._generate_via_ollama", side_effect=Exception()),
    ):
        await run_adaptive_agent(
            agent_run_id=run.id,
            model_name="test-model",
            target_category="JAILBREAK",
            max_rounds=20,
            max_total_tokens=50,
            wall_clock_timeout_s=120.0,
            generator_model="llama3.2",
            judge_model="llama3.2",
            db_factory=db_factory(db_session),
        )

    await db_session.refresh(run)
    assert run.outcome == "token_budget_exceeded"


@pytest.mark.asyncio
async def test_adaptive_agent_respects_timeout(db_session):
    run = await _create_run(db_session, max_rounds=20, wall_clock_timeout_s=5)

    monotonic_values = iter([0.0, 0.0, 100.0])

    with (
        patch("app.agents.adaptive_agent.time") as mock_time,
        patch("app.agents.adaptive_agent.judge_response", return_value=_pass_result()),
        patch("app.benchmarking.benchmark_runner.default_ollama_call", return_value=("ok", 50)),
        patch("app.agents.adaptive_agent._generate_via_ollama", side_effect=Exception()),
    ):
        mock_time.monotonic.side_effect = monotonic_values
        await run_adaptive_agent(
            agent_run_id=run.id,
            model_name="test-model",
            target_category="JAILBREAK",
            max_rounds=20,
            max_total_tokens=200000,
            wall_clock_timeout_s=5.0,
            generator_model="llama3.2",
            judge_model="llama3.2",
            db_factory=db_factory(db_session),
        )

    await db_session.refresh(run)
    assert run.outcome == "timeout"


# ---------------------------------------------------------------------------
# Analytics aggregations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analytics_strategy_success_rate(db_session):
    """Seeded findings produce correct success-rate aggregation via the endpoint."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.db.database import get_db

    run = await _create_run(db_session)

    # Seed: direct_override tried twice, PASS both; roleplay tried once, FAIL
    for verdict, strat, tier in [
        ("PASS", "direct_override", 1),
        ("PASS", "direct_override", 1),
        ("FAIL", "roleplay", 2),
    ]:
        db_session.add(AgentFinding(
            agent_run_id=run.id,
            round_number=1,
            attack_prompt="test",
            model_response="resp",
            verdict=verdict,
            score=0.5,
            escalated=0,
            strategy=strat,
            failure_reason="blocked" if verdict == "PASS" else None,
            escalation_tier=tier,
        ))
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/agent/analytics/strategy-success")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = {row["strategy"]: row for row in resp.json()}
    assert data["direct_override"]["total_attempts"] == 2
    assert data["direct_override"]["successes"] == 0
    assert data["roleplay"]["successes"] == 1
    assert data["roleplay"]["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_analytics_avg_rounds_to_compromise(db_session):
    """avg_rounds_to_compromise averages over compromised runs only."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.db.database import get_db

    for rounds, outcome in [(3, "compromised"), (5, "compromised"), (8, "rounds_exhausted")]:
        r = AgentRun(
            model_name="m", target_category="PI", max_rounds=8,
            max_total_tokens=20000, wall_clock_timeout_s=120,
            status="completed", outcome=outcome, rounds_completed=rounds,
        )
        db_session.add(r)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/agent/analytics/avg-rounds-to-compromise")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["sample_size"] == 2
    assert data["avg_rounds"] == 4.0  # (3 + 5) / 2
