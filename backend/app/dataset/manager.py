from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import DatasetEntry, TestRun, Attack


async def export_dataset(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(DatasetEntry).order_by(DatasetEntry.created_at.desc())
    )
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "attack_name": e.attack_name,
            "category": e.category,
            "severity": e.severity,
            "prompt": e.prompt,
            "model_name": e.model_name,
            "model_response": e.model_response,
            "ground_truth_verdict": e.ground_truth_verdict,
            "source": e.source,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


async def sync_from_test_runs(db: AsyncSession) -> int:
    """Auto-populate dataset from existing TestRun records (source='auto')."""
    existing = await db.execute(
        select(DatasetEntry.prompt, DatasetEntry.model_name)
    )
    existing_keys = {(r.prompt, r.model_name) for r in existing.all()}

    runs_result = await db.execute(
        select(TestRun).options(selectinload(TestRun.attack))
        .where(TestRun.verdict.in_(["PASS", "FAIL", "UNCERTAIN"]))
    )
    runs = runs_result.scalars().all()

    added = 0
    for run in runs:
        if not run.attack:
            continue
        key = (run.prompt_sent or "", run.model_name)
        if key in existing_keys:
            continue
        entry = DatasetEntry(
            attack_name=run.attack.name,
            category=run.attack.category,
            severity=run.attack.severity,
            prompt=run.prompt_sent or run.attack.prompt,
            model_name=run.model_name,
            model_response=run.model_response,
            ground_truth_verdict=run.verdict,
            source="auto",
        )
        db.add(entry)
        existing_keys.add(key)
        added += 1

    await db.commit()
    return added


async def import_entries(db: AsyncSession, entries: list[dict]) -> int:
    added = 0
    for e in entries:
        entry = DatasetEntry(
            attack_name=e.get("attack_name", ""),
            category=e.get("category", "UNKNOWN"),
            severity=e.get("severity", "medium"),
            prompt=e.get("prompt", ""),
            model_name=e.get("model_name", ""),
            model_response=e.get("model_response"),
            ground_truth_verdict=e.get("ground_truth_verdict", "UNCERTAIN"),
            source=e.get("source", "manual"),
        )
        db.add(entry)
        added += 1
    await db.commit()
    return added
