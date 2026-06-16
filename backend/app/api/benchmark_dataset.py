"""Read-only endpoints for the RedForge-Bench-V1 static dataset.

Routes are mounted under /api/dataset/benchmark to avoid clashing with the
existing /api/dataset management endpoints (export/import/sync).
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/dataset/benchmark", tags=["benchmark-dataset"])


class CategoryInfo(BaseModel):
    category: str
    count: int


class BenchmarkStats(BaseModel):
    total: int
    by_category: dict[str, int]
    by_difficulty: dict[str, int]
    by_severity: dict[str, int]
    by_source: dict[str, int]


@router.get("/stats", response_model=BenchmarkStats)
def get_benchmark_stats():
    from app.dataset.benchmark_stats import compute_stats
    return compute_stats()


@router.get("/categories", response_model=list[CategoryInfo])
def list_categories():
    from app.dataset.benchmark_loader import get_all
    data = get_all()
    return [CategoryInfo(category=cat, count=len(entries)) for cat, entries in data.items()]


@router.get("/case/{case_id}", response_model=dict)
def get_case(case_id: str):
    from app.dataset.benchmark_loader import get_by_id
    entry = get_by_id(case_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return entry
