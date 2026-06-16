from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import Attack, TestRun
from app.mutations.mutator import mutate_prompt, ALL_STRATEGIES
from app.evaluators.scoring import score_response

router = APIRouter(prefix="/api/mutations", tags=["mutations"])


class MutationGenerateRequest(BaseModel):
    attack_id: int
    strategies: Optional[list[str]] = None


class MutatedPromptOut(BaseModel):
    strategy: str
    description: str
    prompt: str


class MutationRunRequest(BaseModel):
    attack_id: int
    model_name: str
    strategies: Optional[list[str]] = None


class MutationRunResult(BaseModel):
    strategy: str
    prompt: str
    response: str
    verdict: str
    score: float
    latency_ms: int


@router.get("/strategies")
async def list_strategies():
    return [{"name": s.name, "description": s.description} for s in ALL_STRATEGIES]


@router.post("/generate", response_model=list[MutatedPromptOut])
async def generate_mutations(req: MutationGenerateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Attack).where(Attack.id == req.attack_id))
    attack = result.scalar_one_or_none()
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")

    mutations = mutate_prompt(attack.prompt, req.strategies)
    return [MutatedPromptOut(strategy=m.strategy, description=m.description, prompt=m.prompt) for m in mutations]


@router.post("/run", response_model=list[MutationRunResult])
async def run_mutations(req: MutationRunRequest, db: AsyncSession = Depends(get_db)):
    import httpx, time

    result = await db.execute(select(Attack).where(Attack.id == req.attack_id))
    attack = result.scalar_one_or_none()
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")

    mutations = mutate_prompt(attack.prompt, req.strategies)
    run_results: list[MutationRunResult] = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        for m in mutations:
            start = time.monotonic()
            try:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={"model": req.model_name, "prompt": m.prompt, "stream": False},
                )
                resp.raise_for_status()
                response_text = resp.json().get("response", "")
                latency_ms = int((time.monotonic() - start) * 1000)
            except Exception as exc:
                response_text = f"[ERROR: {exc}]"
                latency_ms = 0

            scored = score_response(m.prompt, response_text)
            db.add(TestRun(
                model_name=req.model_name,
                attack_id=req.attack_id,
                prompt_sent=m.prompt,
                model_response=response_text,
                score=scored.score,
                verdict=scored.verdict,
                reason=f"[mutation:{m.strategy}] {scored.reason}",
                latency_ms=latency_ms,
            ))
            run_results.append(MutationRunResult(
                strategy=m.strategy,
                prompt=m.prompt,
                response=response_text,
                verdict=scored.verdict,
                score=scored.score,
                latency_ms=latency_ms,
            ))

    await db.commit()
    return run_results
