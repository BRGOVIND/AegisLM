from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.db.models import DatasetEntry
from app.dataset.manager import export_dataset, sync_from_test_runs, import_entries

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


class DatasetEntryOut(BaseModel):
    id: int
    attack_name: str
    category: str
    severity: str
    prompt: str
    model_name: str
    model_response: Optional[str]
    ground_truth_verdict: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetStats(BaseModel):
    total: int
    by_verdict: dict[str, int]
    by_category: dict[str, int]
    model_count: int


class ImportRequest(BaseModel):
    entries: list[dict]


@router.get("/export")
async def export(db: AsyncSession = Depends(get_db)):
    return await export_dataset(db)


@router.post("/sync")
async def sync(db: AsyncSession = Depends(get_db)):
    added = await sync_from_test_runs(db)
    return {"added": added, "message": f"Synced {added} new entries from test runs"}


@router.post("/import")
async def import_data(req: ImportRequest, db: AsyncSession = Depends(get_db)):
    added = await import_entries(db, req.entries)
    return {"added": added}


@router.get("/stats", response_model=DatasetStats)
async def stats(db: AsyncSession = Depends(get_db)):
    total_r = await db.execute(select(func.count(DatasetEntry.id)))
    total = total_r.scalar() or 0

    by_verdict_r = await db.execute(
        select(DatasetEntry.ground_truth_verdict, func.count(DatasetEntry.id))
        .group_by(DatasetEntry.ground_truth_verdict)
    )
    by_verdict = {r[0]: r[1] for r in by_verdict_r.all()}

    by_cat_r = await db.execute(
        select(DatasetEntry.category, func.count(DatasetEntry.id))
        .group_by(DatasetEntry.category)
    )
    by_category = {r[0]: r[1] for r in by_cat_r.all()}

    model_count_r = await db.execute(
        select(func.count(func.distinct(DatasetEntry.model_name)))
    )
    model_count = model_count_r.scalar() or 0

    return DatasetStats(total=total, by_verdict=by_verdict, by_category=by_category, model_count=model_count)


@router.get("", response_model=list[DatasetEntryOut])
async def list_entries(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DatasetEntry)
        .order_by(DatasetEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()
