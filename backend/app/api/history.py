from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import ModelScore, BenchmarkRun

router = APIRouter(prefix="/api/history", tags=["history"])



class ScorePoint(BaseModel):
    benchmark_id: int
    benchmark_name: str
    timestamp: datetime
    overall_score: float
    injection_rate: float
    jailbreak_rate: float
    hallucination_rate: float
    data_leakage_rate: float
    avg_latency_ms: float


class ModelHistory(BaseModel):
    model_name: str
    data_points: list[ScorePoint]


@router.get("/{model_name}", response_model=ModelHistory)
async def model_history(
    model_name: str,
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(ModelScore, BenchmarkRun.name, BenchmarkRun.completed_at)
        .join(BenchmarkRun, ModelScore.benchmark_run_id == BenchmarkRun.id)
        .where(ModelScore.model_name == model_name)
        .where(BenchmarkRun.status == "completed")
    )
    if from_date:
        q = q.where(BenchmarkRun.completed_at >= from_date)
    if to_date:
        q = q.where(BenchmarkRun.completed_at <= to_date)
    result = await db.execute(q.order_by(BenchmarkRun.completed_at.asc()))
    rows = result.all()

    points = [
        ScorePoint(
            benchmark_id=ms.id,
            benchmark_name=name,
            timestamp=completed_at or ms.created_at,
            overall_score=ms.overall_score,
            injection_rate=ms.injection_rate,
            jailbreak_rate=ms.jailbreak_rate,
            hallucination_rate=ms.hallucination_rate,
            data_leakage_rate=ms.data_leakage_rate,
            avg_latency_ms=ms.avg_latency_ms,
        )
        for ms, name, completed_at in rows
    ]
    return ModelHistory(model_name=model_name, data_points=points)


@router.get("", response_model=list[ModelHistory])
async def all_model_history(
    models: Optional[str] = Query(None, description="Comma-separated model names"),
    db: AsyncSession = Depends(get_db),
):
    model_names_filter = [m.strip() for m in models.split(",")] if models else None

    query = (
        select(ModelScore, BenchmarkRun.name, BenchmarkRun.completed_at)
        .join(BenchmarkRun, ModelScore.benchmark_run_id == BenchmarkRun.id)
        .where(BenchmarkRun.status == "completed")
        .order_by(ModelScore.model_name, BenchmarkRun.completed_at.asc())
    )
    if model_names_filter:
        query = query.where(ModelScore.model_name.in_(model_names_filter))

    result = await db.execute(query)
    rows = result.all()

    by_model: dict[str, list[ScorePoint]] = {}
    for ms, name, completed_at in rows:
        by_model.setdefault(ms.model_name, []).append(
            ScorePoint(
                benchmark_id=ms.id,
                benchmark_name=name,
                timestamp=completed_at or ms.created_at,
                overall_score=ms.overall_score,
                injection_rate=ms.injection_rate,
                jailbreak_rate=ms.jailbreak_rate,
                hallucination_rate=ms.hallucination_rate,
                data_leakage_rate=ms.data_leakage_rate,
                avg_latency_ms=ms.avg_latency_ms,
            )
        )

    return [ModelHistory(model_name=m, data_points=pts) for m, pts in by_model.items()]
