"""Tests for red-team agent termination conditions and outcome persistence."""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.agents.red_team_agent import run_red_team_agent
from app.db.models import AgentRun, AgentFinding
from app.evaluators.judge import JudgeResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_db_factory(session):
    """Wrap a single AsyncSession so it looks like AsyncSessionLocal."""
    @asynccontextmanager
    async def _factory():
        yield session
    return _factory


def _pass_result() -> JudgeResult:
    return JudgeResult(verdict="PASS", confidence=0.9, reason="safe", risk_level="none", judge_model="mock")


def _fail_result() -> JudgeResult:
    return JudgeResult(verdict="FAIL", confidence=0.9, reason="unsafe", risk_level="high", judge_model="mock")


async def _create_run(db, max_rounds=3, max_total_tokens=20000, wall_clock_timeout_s=120) -> AgentRun:
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
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_terminates_rounds_exhausted(db_session):
    """Loop runs all max_rounds and records outcome=rounds_exhausted."""
    run = await _create_run(db_session, max_rounds=2)

    with (
        patch("app.agents.red_team_agent._generate_via_ollama", new_callable=AsyncMock) as mock_gen,
        patch("app.benchmarking.benchmark_runner.default_ollama_call", new_callable=AsyncMock) as mock_call,
        patch("app.agents.red_team_agent.judge_response", new_callable=AsyncMock) as mock_judge,
    ):
        mock_gen.return_value = "attack prompt"
        mock_call.return_value = ("safe response", 50)
        mock_judge.return_value = _pass_result()

        await run_red_team_agent(
            agent_run_id=run.id,
            model_name="test-model",
            target_category="PROMPT_INJECTION",
            max_rounds=2,
            max_total_tokens=20000,
            wall_clock_timeout_s=120.0,
            generator_model="llama3.2",
            judge_model="llama3.2",
            db_factory=make_db_factory(db_session),
        )

    await db_session.refresh(run)
    assert run.outcome == "rounds_exhausted"
    assert run.rounds_completed == 2
    assert run.status == "completed"


@pytest.mark.asyncio
async def test_agent_terminates_token_budget_exceeded(db_session):
    """Loop stops when cumulative token estimate exceeds max_total_tokens."""
    run = await _create_run(db_session, max_rounds=10, max_total_tokens=100)

    # Each response is 2000 chars → ~500 tokens; budget of 100 trips after round 1
    long_response = "x" * 2000

    with (
        patch("app.agents.red_team_agent._generate_via_ollama", new_callable=AsyncMock) as mock_gen,
        patch("app.benchmarking.benchmark_runner.default_ollama_call", new_callable=AsyncMock) as mock_call,
        patch("app.agents.red_team_agent.judge_response", new_callable=AsyncMock) as mock_judge,
    ):
        mock_gen.return_value = "attack prompt"
        mock_call.return_value = (long_response, 9999)
        mock_judge.return_value = _pass_result()

        await run_red_team_agent(
            agent_run_id=run.id,
            model_name="test-model",
            target_category="PROMPT_INJECTION",
            max_rounds=10,
            max_total_tokens=100,
            wall_clock_timeout_s=120.0,
            generator_model="llama3.2",
            judge_model="llama3.2",
            db_factory=make_db_factory(db_session),
        )

    await db_session.refresh(run)
    assert run.outcome == "token_budget_exceeded"
    # Must have run at least 1 round (budget check is at top of round, so
    # round 1 executes and accumulates; round 2 sees the exceeded budget)
    assert run.rounds_completed >= 1
    assert run.status == "completed"


@pytest.mark.asyncio
async def test_agent_terminates_timeout(db_session):
    """Loop stops on wall-clock timeout; monotonic clock is patched."""
    run = await _create_run(db_session, max_rounds=10, wall_clock_timeout_s=5)

    # First call to time.monotonic() returns start_time=0;
    # second call (top of round 2) returns 100 → 100-0 > 5 → timeout.
    monotonic_values = iter([0.0, 0.0, 100.0])

    with (
        patch("app.agents.red_team_agent.time") as mock_time,
        patch("app.agents.red_team_agent._generate_via_ollama", new_callable=AsyncMock) as mock_gen,
        patch("app.benchmarking.benchmark_runner.default_ollama_call", new_callable=AsyncMock) as mock_call,
        patch("app.agents.red_team_agent.judge_response", new_callable=AsyncMock) as mock_judge,
    ):
        mock_time.monotonic.side_effect = monotonic_values
        mock_gen.return_value = "attack prompt"
        mock_call.return_value = ("safe response", 50)
        mock_judge.return_value = _pass_result()

        await run_red_team_agent(
            agent_run_id=run.id,
            model_name="test-model",
            target_category="PROMPT_INJECTION",
            max_rounds=10,
            max_total_tokens=20000,
            wall_clock_timeout_s=5.0,
            generator_model="llama3.2",
            judge_model="llama3.2",
            db_factory=make_db_factory(db_session),
        )

    await db_session.refresh(run)
    assert run.outcome == "timeout"
    assert run.status == "completed"


@pytest.mark.asyncio
async def test_agent_terminates_compromised(db_session):
    """Loop exits immediately when judge returns FAIL (model compromised)."""
    run = await _create_run(db_session, max_rounds=5)

    with (
        patch("app.agents.red_team_agent._generate_via_ollama", new_callable=AsyncMock) as mock_gen,
        patch("app.benchmarking.benchmark_runner.default_ollama_call", new_callable=AsyncMock) as mock_call,
        patch("app.agents.red_team_agent.judge_response", new_callable=AsyncMock) as mock_judge,
    ):
        mock_gen.return_value = "attack prompt"
        mock_call.return_value = ("harmful response", 50)
        mock_judge.return_value = _fail_result()  # FAIL on every round

        await run_red_team_agent(
            agent_run_id=run.id,
            model_name="test-model",
            target_category="PROMPT_INJECTION",
            max_rounds=5,
            max_total_tokens=20000,
            wall_clock_timeout_s=120.0,
            generator_model="llama3.2",
            judge_model="llama3.2",
            db_factory=make_db_factory(db_session),
        )

    await db_session.refresh(run)
    assert run.outcome == "compromised"
    assert run.rounds_completed == 1  # stopped after first FAIL
    assert run.status == "completed"

    # Confirm a finding was written for that round
    findings = (await db_session.execute(
        select(AgentFinding).where(AgentFinding.agent_run_id == run.id)
    )).scalars().all()
    assert len(findings) == 1
    assert findings[0].verdict == "FAIL"


@pytest.mark.asyncio
async def test_agent_terminates_strategies_exhausted(db_session):
    """Loop stops when the escalation generator raises an exception."""
    run = await _create_run(db_session, max_rounds=5)

    call_count = 0

    async def gen_side_effect(model, prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "initial attack prompt"
        raise RuntimeError("Ollama unavailable")

    with (
        patch("app.agents.red_team_agent._generate_via_ollama", side_effect=gen_side_effect),
        patch("app.benchmarking.benchmark_runner.default_ollama_call", new_callable=AsyncMock) as mock_call,
        patch("app.agents.red_team_agent.judge_response", new_callable=AsyncMock) as mock_judge,
    ):
        mock_call.return_value = ("safe response", 50)
        mock_judge.return_value = _pass_result()

        await run_red_team_agent(
            agent_run_id=run.id,
            model_name="test-model",
            target_category="PROMPT_INJECTION",
            max_rounds=5,
            max_total_tokens=20000,
            wall_clock_timeout_s=120.0,
            generator_model="llama3.2",
            judge_model="llama3.2",
            db_factory=make_db_factory(db_session),
        )

    await db_session.refresh(run)
    assert run.outcome == "strategies_exhausted"
    assert run.status == "completed"
