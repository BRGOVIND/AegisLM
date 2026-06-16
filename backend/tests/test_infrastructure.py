"""Infrastructure tests: API availability, router registration, DB accessible."""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.database import get_db


EXPECTED_ROUTE_PREFIXES = [
    "/api/models",
    "/api/attacks",
    "/api/runs",
    "/api/evaluate",
    "/api/dashboard",
    "/api/reports",
    "/api/benchmarks",
    "/api/analytics",
    "/api/mutations",
    "/api/agent",
    "/api/leaderboard",
    "/api/history",
    "/api/dataset",
    "/api/dataset/benchmark",
]


def test_all_expected_routers_registered():
    """Every expected route prefix appears in the app's route list."""
    all_paths = [route.path for route in app.routes]  # type: ignore[union-attr]
    for prefix in EXPECTED_ROUTE_PREFIXES:
        matching = [p for p in all_paths if p.startswith(prefix)]
        assert matching, f"No route found with prefix {prefix!r}. Registered: {all_paths[:20]}"


@pytest.mark.asyncio
async def test_root_endpoint_online():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"


@pytest.mark.asyncio
async def test_db_accessible_via_dependency(db_session):
    """DB session is healthy — a basic select returns without error."""
    from sqlalchemy import text
    result = await db_session.execute(text("SELECT 1"))
    row = result.scalar()
    assert row == 1


@pytest.mark.asyncio
async def test_models_endpoint_reachable(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/attacks")
    app.dependency_overrides.clear()
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_leaderboard_endpoint_reachable(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/leaderboard")
    app.dependency_overrides.clear()
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_agent_list_endpoint_reachable(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/agent")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
