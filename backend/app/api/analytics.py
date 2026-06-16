from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.db.database import get_db
from app.db.models import TestRun, Attack

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_fail_expr = case((TestRun.verdict == "FAIL", 1), else_=0)
_uncertain_expr = case((TestRun.verdict == "UNCERTAIN", 1), else_=0)


class AttackEffectiveness(BaseModel):
    attack_id: int
    attack_name: str
    category: str
    severity: str
    total_runs: int
    fail_count: int
    uncertain_count: int
    fail_rate: float


class CategoryHeatmapEntry(BaseModel):
    model_name: str
    category: str
    fail_rate: float
    total: int


class ModelVulnerability(BaseModel):
    category: str
    fail_rate: float
    total: int
    fail_count: int


@router.get("/attacks", response_model=list[AttackEffectiveness])
async def attack_effectiveness(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            TestRun.attack_id,
            Attack.name,
            Attack.category,
            Attack.severity,
            func.count(TestRun.id).label("total"),
            func.sum(_fail_expr).label("fails"),
            func.sum(_uncertain_expr).label("uncertain"),
        )
        .join(Attack, TestRun.attack_id == Attack.id)
        .group_by(TestRun.attack_id, Attack.name, Attack.category, Attack.severity)
        .order_by(func.sum(_fail_expr).desc())
    )
    rows = result.all()
    return [
        AttackEffectiveness(
            attack_id=r.attack_id,
            attack_name=r.name,
            category=r.category,
            severity=r.severity,
            total_runs=r.total,
            fail_count=r.fails or 0,
            uncertain_count=r.uncertain or 0,
            fail_rate=round((r.fails or 0) / r.total, 4) if r.total else 0.0,
        )
        for r in rows
    ]


@router.get("/category-heatmap", response_model=list[CategoryHeatmapEntry])
async def category_heatmap(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            TestRun.model_name,
            Attack.category,
            func.count(TestRun.id).label("total"),
            func.sum(_fail_expr).label("fails"),
        )
        .join(Attack, TestRun.attack_id == Attack.id)
        .group_by(TestRun.model_name, Attack.category)
        .order_by(TestRun.model_name, Attack.category)
    )
    rows = result.all()
    return [
        CategoryHeatmapEntry(
            model_name=r.model_name,
            category=r.category,
            fail_rate=round((r.fails or 0) / r.total, 4) if r.total else 0.0,
            total=r.total,
        )
        for r in rows
    ]


@router.get("/models/{model_name}/vulnerabilities", response_model=list[ModelVulnerability])
async def model_vulnerabilities(model_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Attack.category,
            func.count(TestRun.id).label("total"),
            func.sum(_fail_expr).label("fails"),
        )
        .join(Attack, TestRun.attack_id == Attack.id)
        .where(TestRun.model_name == model_name)
        .group_by(Attack.category)
        .order_by(func.sum(_fail_expr).desc())
    )
    rows = result.all()
    return [
        ModelVulnerability(
            category=r.category,
            fail_rate=round((r.fails or 0) / r.total, 4) if r.total else 0.0,
            total=r.total,
            fail_count=r.fails or 0,
        )
        for r in rows
    ]
