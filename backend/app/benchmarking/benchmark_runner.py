from __future__ import annotations

import asyncio
from typing import Callable, Awaitable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Attack, TestRun
from app.evaluators.scoring import score_response

OllamaCallFn = Callable[[str, str], Awaitable[tuple[str, int]]]


async def default_ollama_call(model_name: str, prompt: str) -> tuple[str, int]:
    import time
    url = "http://localhost:11434/api/generate"
    payload = {"model": model_name, "prompt": prompt, "stream": False}
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return resp.json().get("response", ""), elapsed_ms


async def run_attacks_for_model(
    db: AsyncSession,
    model_name: str,
    attack_ids: list[int],
    ollama_call: OllamaCallFn = default_ollama_call,
) -> list[dict]:
    result = await db.execute(
        select(Attack).where(Attack.id.in_(attack_ids))
    )
    attacks = result.scalars().all()

    run_results: list[dict] = []
    for attack in attacks:
        try:
            response_text, latency_ms = await ollama_call(model_name, attack.prompt)
        except Exception as exc:
            response_text = f"[ERROR: {exc}]"
            latency_ms = 0

        score_result = score_response(attack.prompt, response_text)

        test_run = TestRun(
            model_name=model_name,
            attack_id=attack.id,
            prompt_sent=attack.prompt,
            model_response=response_text,
            score=score_result.score,
            verdict=score_result.verdict,
            reason=score_result.reason,
            latency_ms=latency_ms,
        )
        db.add(test_run)

        run_results.append({
            "category": attack.category,
            "severity": attack.severity,
            "verdict": score_result.verdict,
            "latency_ms": latency_ms,
            "score": score_result.score,
            "attack_name": attack.name,
        })

    await db.commit()
    return run_results


async def run_benchmark_background(
    benchmark_run_id: int,
    model_list: list[str],
    attack_ids: list[int],
    db_factory: Callable[[], AsyncSession],
    ollama_call: OllamaCallFn = default_ollama_call,
) -> None:
    from app.benchmarking.benchmark_scheduler import BENCHMARK_JOBS, update_job_status
    from app.benchmarking.benchmark_metrics import compute_and_persist_scores

    update_job_status(benchmark_run_id, "running", progress=0)

    all_model_results: dict[str, list[dict]] = {}
    total = len(model_list)

    for idx, model_name in enumerate(model_list):
        async with db_factory() as db:
            try:
                results = await run_attacks_for_model(db, model_name, attack_ids, ollama_call)
                all_model_results[model_name] = results
            except Exception as exc:
                all_model_results[model_name] = []
                update_job_status(
                    benchmark_run_id, "running",
                    progress=int((idx + 1) / total * 100),
                    error=str(exc),
                )
                continue

        update_job_status(benchmark_run_id, "running", progress=int((idx + 1) / total * 100))

    async with db_factory() as db:
        await compute_and_persist_scores(db, benchmark_run_id, all_model_results)

    update_job_status(benchmark_run_id, "completed", progress=100)
