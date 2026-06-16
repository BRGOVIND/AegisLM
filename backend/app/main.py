from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import models, attacks, runs, evaluate, dashboard, reports, benchmarks, analytics, mutations, agent, leaderboard, history, dataset
from app.db.database import init_db, AsyncSessionLocal
from app.attacks.library import seed_attacks
from app.scoring.weighted_engine import WeightedScoringEngine
from app.scoring.scoring_interface import set_scoring_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_scoring_engine(WeightedScoringEngine())
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_attacks(db)
    yield


app = FastAPI(
    title="RedForge API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router)
app.include_router(attacks.router)
app.include_router(runs.router)
app.include_router(evaluate.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(benchmarks.router)
app.include_router(analytics.router)
app.include_router(mutations.router)
app.include_router(agent.router)
app.include_router(leaderboard.router)
app.include_router(history.router)
app.include_router(dataset.router)


@app.get("/")
async def root():
    return {"name": "RedForge API", "version": "2.0.0", "status": "online"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, e: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(e)},
    )
