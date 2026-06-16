from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import BenchmarkRun, ModelScore
from app.scoring.scoring_interface import get_scoring_engine


async def compute_and_persist_scores(
    db: AsyncSession,
    benchmark_run_id: int,
    all_model_results: dict[str, list[dict]],
) -> list[ModelScore]:
    engine = get_scoring_engine()
    saved: list[ModelScore] = []

    for model_name, results in all_model_results.items():
        scores = engine.compute_scores(model_name, results)
        ms = ModelScore(
            benchmark_run_id=benchmark_run_id,
            model_name=model_name,
            injection_rate=scores.injection_rate,
            jailbreak_rate=scores.jailbreak_rate,
            hallucination_rate=scores.hallucination_rate,
            data_leakage_rate=scores.data_leakage_rate,
            avg_latency_ms=scores.avg_latency_ms,
            overall_score=scores.overall_score,
        )
        db.add(ms)
        saved.append(ms)

    result = await db.execute(
        select(BenchmarkRun).where(BenchmarkRun.id == benchmark_run_id)
    )
    run = result.scalar_one_or_none()
    if run:
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)

    await db.commit()
    return saved
