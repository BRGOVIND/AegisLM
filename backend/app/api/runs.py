import time
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Attack, TestRun
from app.evaluators.scoring import score_response

router = APIRouter(prefix="/api/runs", tags=["runs"])

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 60.0

JOB_STORE: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    model_name: str
    attack_id: int


class BatchRunRequest(BaseModel):
    model_name: str
    category: Optional[str] = None


class RunResult(BaseModel):
    id: int
    model_name: str
    attack_id: int
    attack_name: str
    category: str
    prompt_sent: str
    model_response: str
    score: float
    verdict: str
    reason: str
    latency_ms: int
    timestamp: datetime


class JobStatus(BaseModel):
    job_id: str
    status: str
    total: int
    completed: int
    results: list[RunResult]


# ---------------------------------------------------------------------------
# Ollama helper
# ---------------------------------------------------------------------------

async def call_ollama(model_name: str, prompt: str) -> tuple[str, int]:
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": model_name, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            latency_ms = int((time.monotonic() - start) * 1000)
            return data.get("response", ""), latency_ms
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is offline or unreachable at {OLLAMA_BASE_URL}. "
                   f"Ensure Ollama is running. Error: {exc}",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}",
        ) from exc


# ---------------------------------------------------------------------------
# Background batch task
# ---------------------------------------------------------------------------

async def _run_batch(job_id: str, model_name: str, attacks: list[Attack]) -> None:
    from app.db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        for attack in attacks:
            try:
                response_text, latency_ms = await call_ollama(model_name, attack.prompt)
            except HTTPException as exc:
                JOB_STORE[job_id]["status"] = "failed"
                JOB_STORE[job_id]["error"] = exc.detail
                return

            result = score_response(attack.prompt, response_text)

            test_run = TestRun(
                model_name=model_name,
                attack_id=attack.id,
                prompt_sent=attack.prompt,
                model_response=response_text,
                score=result.score,
                verdict=result.verdict,
                reason=result.reason,
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc),
            )
            db.add(test_run)
            await db.commit()
            await db.refresh(test_run)

            run_result = RunResult(
                id=test_run.id,
                model_name=model_name,
                attack_id=attack.id,
                attack_name=attack.name,
                category=attack.category,
                prompt_sent=attack.prompt,
                model_response=response_text,
                score=result.score,
                verdict=result.verdict,
                reason=result.reason,
                latency_ms=latency_ms,
                timestamp=test_run.timestamp,
            )

            JOB_STORE[job_id]["results"].append(run_result.model_dump())
            JOB_STORE[job_id]["completed"] += 1

    JOB_STORE[job_id]["status"] = "completed"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=RunResult)
async def run_single_attack(
    req: RunRequest,
    db: AsyncSession = Depends(get_db),
) -> RunResult:
    result_row = await db.execute(select(Attack).where(Attack.id == req.attack_id))
    attack = result_row.scalar_one_or_none()
    if attack is None:
        raise HTTPException(status_code=404, detail=f"Attack {req.attack_id} not found")

    response_text, latency_ms = await call_ollama(req.model_name, attack.prompt)
    scored = score_response(attack.prompt, response_text)

    test_run = TestRun(
        model_name=req.model_name,
        attack_id=attack.id,
        prompt_sent=attack.prompt,
        model_response=response_text,
        score=scored.score,
        verdict=scored.verdict,
        reason=scored.reason,
        latency_ms=latency_ms,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(test_run)
    await db.commit()
    await db.refresh(test_run)

    return RunResult(
        id=test_run.id,
        model_name=req.model_name,
        attack_id=attack.id,
        attack_name=attack.name,
        category=attack.category,
        prompt_sent=attack.prompt,
        model_response=response_text,
        score=scored.score,
        verdict=scored.verdict,
        reason=scored.reason,
        latency_ms=latency_ms,
        timestamp=test_run.timestamp,
    )


@router.post("/batch")
async def run_batch(
    req: BatchRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    query = select(Attack)
    if req.category is not None:
        query = query.where(Attack.category == req.category)
    result_rows = await db.execute(query)
    attacks = list(result_rows.scalars().all())

    if not attacks:
        raise HTTPException(
            status_code=404,
            detail=f"No attacks found" + (f" for category '{req.category}'" if req.category else ""),
        )

    job_id = str(uuid4())
    JOB_STORE[job_id] = {
        "status": "running",
        "total": len(attacks),
        "completed": 0,
        "results": [],
    }

    background_tasks.add_task(_run_batch, job_id, req.model_name, attacks)

    return {"job_id": job_id, "total": len(attacks)}


@router.get("/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    job = JOB_STORE.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return JobStatus(
        job_id=job_id,
        status=job["status"],
        total=job["total"],
        completed=job["completed"],
        results=[RunResult(**r) for r in job["results"]],
    )


@router.get("", response_model=list[RunResult])
async def list_runs(
    model_name: str,
    db: AsyncSession = Depends(get_db),
) -> list[RunResult]:
    result_rows = await db.execute(
        select(TestRun, Attack)
        .join(Attack, TestRun.attack_id == Attack.id)
        .where(TestRun.model_name == model_name)
        .order_by(TestRun.timestamp.desc())
    )
    rows = result_rows.all()

    return [
        RunResult(
            id=test_run.id,
            model_name=test_run.model_name,
            attack_id=attack.id,
            attack_name=attack.name,
            category=attack.category,
            prompt_sent=test_run.prompt_sent or "",
            model_response=test_run.model_response or "",
            score=test_run.score or 0.0,
            verdict=test_run.verdict or "UNCERTAIN",
            reason=test_run.reason or "",
            latency_ms=test_run.latency_ms or 0,
            timestamp=test_run.timestamp,
        )
        for test_run, attack in rows
    ]
