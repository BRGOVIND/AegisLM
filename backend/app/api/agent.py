from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload

from app.db.database import get_db, AsyncSessionLocal
from app.db.models import AgentRun, AgentFinding

router = APIRouter(prefix="/api/agent", tags=["agent"])

AGENT_JOBS: dict[int, dict] = {}


class AgentRunRequest(BaseModel):
    model_name: str
    target_category: str = "PROMPT_INJECTION"
    max_rounds: int = 8
    max_total_tokens: int = 20000
    wall_clock_timeout_s: float = 120.0
    generator_model: str = "llama3.2"
    judge_model: str = "llama3.2"
    adaptive: bool = True  # True = adaptive strategy-switching agent, False = original agent


class AgentFindingOut(BaseModel):
    id: int
    round_number: int
    attack_prompt: str
    model_response: Optional[str]
    verdict: Optional[str]
    score: Optional[float]
    escalated: int
    strategy: Optional[str] = None
    failure_reason: Optional[str] = None
    escalation_tier: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRunOut(BaseModel):
    id: int
    model_name: str
    target_category: Optional[str]
    max_rounds: int
    max_total_tokens: int
    wall_clock_timeout_s: int
    status: str
    outcome: Optional[str] = None
    rounds_completed: int
    created_at: datetime
    completed_at: Optional[datetime]
    findings: list[AgentFindingOut] = []

    model_config = {"from_attributes": True}


class AgentStatusOut(BaseModel):
    agent_run_id: int
    status: str
    rounds_completed: int
    outcome: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Analytics models
# ---------------------------------------------------------------------------

class StrategySuccessRate(BaseModel):
    strategy: str
    total_attempts: int
    successes: int
    success_rate: float


class FailureReasonEntry(BaseModel):
    failure_reason: str
    count: int


class AvgRoundsData(BaseModel):
    avg_rounds: Optional[float]
    sample_size: int


# ---------------------------------------------------------------------------
# Run endpoint
# ---------------------------------------------------------------------------

@router.post("", response_model=AgentRunOut, status_code=202)
async def start_agent_run(
    req: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    run = AgentRun(
        model_name=req.model_name,
        target_category=req.target_category,
        max_rounds=req.max_rounds,
        max_total_tokens=req.max_total_tokens,
        wall_clock_timeout_s=int(req.wall_clock_timeout_s),
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    AGENT_JOBS[run.id] = {"status": "pending", "rounds_completed": 0}

    if req.adaptive:
        from app.agents.adaptive_agent import run_adaptive_agent
        background_tasks.add_task(
            run_adaptive_agent,
            run.id,
            req.model_name,
            req.target_category,
            req.max_rounds,
            req.max_total_tokens,
            req.wall_clock_timeout_s,
            req.generator_model,
            req.judge_model,
            AsyncSessionLocal,
        )
    else:
        from app.agents.red_team_agent import run_red_team_agent
        background_tasks.add_task(
            run_red_team_agent,
            run.id,
            req.model_name,
            req.target_category,
            req.max_rounds,
            req.max_total_tokens,
            req.wall_clock_timeout_s,
            req.generator_model,
            req.judge_model,
            AsyncSessionLocal,
        )

    return AgentRunOut(
        id=run.id,
        model_name=run.model_name,
        target_category=run.target_category,
        max_rounds=run.max_rounds,
        max_total_tokens=run.max_total_tokens,
        wall_clock_timeout_s=run.wall_clock_timeout_s,
        status=run.status,
        outcome=None,
        rounds_completed=0,
        created_at=run.created_at,
        completed_at=None,
        findings=[],
    )


# ---------------------------------------------------------------------------
# Status / detail endpoints
# ---------------------------------------------------------------------------

@router.get("/{agent_run_id}/status", response_model=AgentStatusOut)
async def get_agent_status(agent_run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return AgentStatusOut(
        agent_run_id=run.id,
        status=run.status,
        rounds_completed=run.rounds_completed,
        outcome=run.outcome,
    )


@router.get("/{agent_run_id}", response_model=AgentRunOut)
async def get_agent_run(agent_run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.id == agent_run_id)
        .options(selectinload(AgentRun.findings))
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run


@router.get("", response_model=list[AgentRunOut])
async def list_agent_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.findings))
        .order_by(AgentRun.created_at.desc())
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------

@router.get("/analytics/strategy-success", response_model=list[StrategySuccessRate])
async def strategy_success_rates(db: AsyncSession = Depends(get_db)):
    """Success rate per strategy across all adaptive agent sessions."""
    _success_expr = case((AgentFinding.verdict == "FAIL", 1), else_=0)
    result = await db.execute(
        select(
            AgentFinding.strategy,
            func.count(AgentFinding.id).label("total"),
            func.sum(_success_expr).label("successes"),
        )
        .where(AgentFinding.strategy.isnot(None))
        .group_by(AgentFinding.strategy)
        .order_by(func.sum(_success_expr).desc())
    )
    rows = result.all()
    return [
        StrategySuccessRate(
            strategy=r.strategy,
            total_attempts=r.total,
            successes=r.successes or 0,
            success_rate=round((r.successes or 0) / r.total, 4) if r.total else 0.0,
        )
        for r in rows
    ]


@router.get("/analytics/failure-reasons", response_model=list[FailureReasonEntry])
async def failure_reason_breakdown(db: AsyncSession = Depends(get_db)):
    """Aggregated counts of why attacks failed (judge's reason text)."""
    result = await db.execute(
        select(
            AgentFinding.failure_reason,
            func.count(AgentFinding.id).label("cnt"),
        )
        .where(AgentFinding.failure_reason.isnot(None))
        .where(AgentFinding.failure_reason != "")
        .group_by(AgentFinding.failure_reason)
        .order_by(func.count(AgentFinding.id).desc())
    )
    rows = result.all()
    return [FailureReasonEntry(failure_reason=r.failure_reason, count=r.cnt) for r in rows]


@router.get("/analytics/avg-rounds-to-compromise", response_model=AvgRoundsData)
async def avg_rounds_to_compromise(db: AsyncSession = Depends(get_db)):
    """Mean rounds_completed for sessions that ended with outcome='compromised'."""
    result = await db.execute(
        select(
            func.avg(AgentRun.rounds_completed).label("avg_r"),
            func.count(AgentRun.id).label("cnt"),
        )
        .where(AgentRun.outcome == "compromised")
    )
    row = result.one()
    return AvgRoundsData(
        avg_rounds=round(float(row.avg_r), 2) if row.avg_r is not None else None,
        sample_size=row.cnt or 0,
    )
