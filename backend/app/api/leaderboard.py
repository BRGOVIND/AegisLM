from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.db.models import ModelScore

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


class LeaderboardEntry(BaseModel):
    rank: int
    model_name: str
    avg_overall_score: float
    avg_injection_rate: float
    avg_jailbreak_rate: float
    avg_hallucination_rate: float
    avg_data_leakage_rate: float
    avg_latency_ms: float
    benchmark_count: int


@router.get("", response_model=list[LeaderboardEntry])
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            ModelScore.model_name,
            func.avg(ModelScore.overall_score).label("avg_overall"),
            func.avg(ModelScore.injection_rate).label("avg_inj"),
            func.avg(ModelScore.jailbreak_rate).label("avg_jail"),
            func.avg(ModelScore.hallucination_rate).label("avg_hall"),
            func.avg(ModelScore.data_leakage_rate).label("avg_dl"),
            func.avg(ModelScore.avg_latency_ms).label("avg_lat"),
            func.count(ModelScore.id).label("runs"),
        )
        .group_by(ModelScore.model_name)
        .order_by(func.avg(ModelScore.overall_score).desc())
    )
    rows = result.all()
    return [
        LeaderboardEntry(
            rank=i + 1,
            model_name=r.model_name,
            avg_overall_score=round(r.avg_overall or 0.0, 2),
            avg_injection_rate=round(r.avg_inj or 0.0, 4),
            avg_jailbreak_rate=round(r.avg_jail or 0.0, 4),
            avg_hallucination_rate=round(r.avg_hall or 0.0, 4),
            avg_data_leakage_rate=round(r.avg_dl or 0.0, 4),
            avg_latency_ms=round(r.avg_lat or 0.0, 1),
            benchmark_count=r.runs,
        )
        for i, r in enumerate(rows)
    ]
