"""Tests for history time-series API including from/to date filtering."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.db.models import BenchmarkRun, ModelScore


async def _add_run(db, name: str, model: str, score: float, completed_at: datetime) -> None:
    run = BenchmarkRun(
        name=name,
        model_list=[model],
        attack_suite=[],
        status="completed",
        completed_at=completed_at,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    db.add(ModelScore(
        benchmark_run_id=run.id,
        model_name=model,
        overall_score=score,
    ))
    await db.commit()


@pytest.mark.asyncio
async def test_history_snapshot_written_on_benchmark_complete(db_session):
    """A ModelScore row (snapshot) is accessible via the history endpoint after a run completes."""
    from app.main import app
    from app.db.database import get_db

    ts = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    await _add_run(db_session, "snap-run", "snap-model", 88.0, ts)

    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/history/snap-model")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["model_name"] == "snap-model"
    assert len(data["data_points"]) == 1
    assert data["data_points"][0]["overall_score"] == 88.0


@pytest.mark.asyncio
async def test_history_from_to_bounds(db_session):
    """Only snapshots within the from/to window are returned."""
    from app.main import app
    from app.db.database import get_db

    jan = datetime(2026, 1, 10, tzinfo=timezone.utc)
    feb = datetime(2026, 2, 10, tzinfo=timezone.utc)
    mar = datetime(2026, 3, 10, tzinfo=timezone.utc)

    for ts, score in [(jan, 50.0), (feb, 60.0), (mar, 70.0)]:
        await _add_run(db_session, f"run-{score}", "filter-model", score, ts)

    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Ask for only Jan and Feb
        resp = await client.get(
            "/api/history/filter-model",
            params={"from": "2026-01-01T00:00:00Z", "to": "2026-02-28T00:00:00Z"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    scores = [p["overall_score"] for p in data["data_points"]]
    assert 50.0 in scores
    assert 60.0 in scores
    assert 70.0 not in scores  # March excluded


@pytest.mark.asyncio
async def test_history_from_bound_only(db_session):
    """from bound alone filters out earlier snapshots."""
    from app.main import app
    from app.db.database import get_db

    jan = datetime(2026, 1, 10, tzinfo=timezone.utc)
    mar = datetime(2026, 3, 10, tzinfo=timezone.utc)

    await _add_run(db_session, "early-run", "bound-model", 40.0, jan)
    await _add_run(db_session, "late-run", "bound-model", 90.0, mar)

    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/history/bound-model",
            params={"from": "2026-02-01T00:00:00Z"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    scores = [p["overall_score"] for p in data["data_points"]]
    assert 90.0 in scores
    assert 40.0 not in scores


@pytest.mark.asyncio
async def test_history_ordering_ascending(db_session):
    """Data points are returned in ascending timestamp order."""
    from app.main import app
    from app.db.database import get_db

    dates = [
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 2, 1, tzinfo=timezone.utc),
    ]
    scores = [30.0, 10.0, 20.0]

    for ts, score in zip(dates, scores):
        await _add_run(db_session, f"ord-run-{score}", "ord-model", score, ts)

    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/history/ord-model")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    returned_scores = [p["overall_score"] for p in data["data_points"]]
    assert returned_scores == sorted(returned_scores)
