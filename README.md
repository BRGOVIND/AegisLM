# RedForge

A local red teaming tool for testing LLMs that run through Ollama. Point it at a model, throw a library of adversarial prompts at it, and see where it breaks.

Everything runs on your own machine. Nothing gets sent to a cloud API.

## Why I built this

Most LLM security testing either costs money (hosted eval platforms) or means writing attack prompts by hand every time. RedForge keeps a library of attacks ready to go, runs them against whatever Ollama models you have pulled, scores the responses, and shows you which categories the model is weak against.

## What it does

- Ships with 28 attacks across four categories: prompt injection, jailbreaks, context manipulation, and data leakage
- Scores each response as PASS, FAIL, or UNCERTAIN, with a short reason for the verdict
- Runs a whole category against a model in one go, tracked as a background job
- Shows pass/fail rates, a category breakdown, average latency, and a 7-day history per model
- Has a separate endpoint for checking hallucination / factual reliability
- Exports results to PDF or JSON if you need to share them
- Talks straight to your local Ollama instance, so no inference leaves your machine

The backend is FastAPI, the frontend is React + TypeScript. Both hot-reload, so it's easy to add your own attacks or metrics.

## Before you start

You'll need:

- Python 3.11 or newer
- Node 18 or newer
- Ollama, installed and running ([ollama.com](https://ollama.com))
- At least one model pulled, e.g. `ollama pull llama3`

## Running it

Pull a model if you haven't:

```bash
ollama pull llama3
```

Start the backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

It runs on `http://localhost:8000`. The database gets created and the attack library seeded automatically the first time it starts.

Then the frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, pick a model, run an attack or a full batch, and check the results on the dashboard.

## The attack library

| Category | What it covers | Count |
|---|---|---|
| `PROMPT_INJECTION` | Overriding system instructions, injecting fake directives, pulling out the system prompt | 8 |
| `JAILBREAK` | Persona tricks, fictional framing, emotional pressure, fake academic justifications | 7 |
| `CONTEXT_MANIPULATION` | Made-up chat history, false prior agreements, invented authority | 6 |
| `DATA_LEAKAGE` | Trying to extract the system prompt, context contents, session data, or memorized training data | 7 |

## V2 Features

RedForge V2 ships a full evaluation platform on top of the original attack runner:

- **Multi-model benchmarking** — run all attacks against multiple models in one job, stored in `benchmark_runs`/`model_scores`
- **Analytics** — attack effectiveness by category, heatmap by model×category, per-model vulnerability breakdown
- **Prompt mutation engine** — 7 strategies (leet speak, base64, hypothetical frame, etc.) to generate attack variants
- **Autonomous red-team agent** — iterative attack loop with configurable round cap, token budget, and wall-clock timeout; records outcome (`compromised` / `rounds_exhausted` / `token_budget_exceeded` / `timeout` / `strategies_exhausted`)
- **LLM-as-a-Judge** — Ollama-backed structured verdict with heuristic fallback
- **Leaderboard** — models ranked by overall security score
- **History** — per-model score time series with `from`/`to` date filtering
- **Dataset management** — export / import / sync test results to a `DatasetEntry` table
- **RedForge-Bench-V1** — 800 validated static benchmark cases across 5 categories (see below)

### RedForge-Bench-V1

A versioned static benchmark dataset shipped in `datasets/redforge-bench-v1/`.

| Category | Seeds | Total |
|---|---|---|
| `prompt_injection` | 50 | 200 |
| `jailbreak` | 50 | 200 |
| `data_leakage` | 40 | 150 |
| `hallucination` | 60 | 150 |
| `toxicity` | 40 | 100 |
| **Total** | **240** | **800** |

Seeds are hand-authored; variants are generated with the Phase 4 mutation engine and deduplicated. The validator enforces required fields, valid enums, unique IDs, no duplicate prompts, per-category minimums, and `ground_truth` on hallucination entries. Toxicity is data-only pending a dedicated evaluator.

Bench endpoints: `GET /api/dataset/benchmark/stats`, `.../categories`, `.../case/{id}`.

See `datasets/redforge-bench-v1/README.md` for full schema and generation details.

## API

| Method | Endpoint | What it does |
|---|---|---|
| `GET` | `/api/attacks` | All attacks, grouped by category |
| `GET` | `/api/attacks/{id}` | A single attack |
| `POST` | `/api/runs` | Run one attack against a model |
| `POST` | `/api/runs/batch` | Run a batch (optionally one category) as a background job |
| `GET` | `/api/runs/{job_id}/status` | Check batch progress and results |
| `GET` | `/api/runs` | Past runs for a model |
| `GET` | `/api/dashboard` | Aggregated metrics for a model |
| `GET` | `/api/models` | Models currently available in Ollama |
| `POST` | `/api/evaluate/hallucination` | Run a hallucination probe |
| `GET` | `/api/reports/{model}` | Generate a downloadable report |
| `POST` | `/api/benchmarks` | Start a multi-model benchmark run |
| `GET` | `/api/benchmarks/{id}/status` | Benchmark run status |
| `GET` | `/api/leaderboard` | Model rankings by overall score |
| `GET` | `/api/history/{model}` | Score time series for a model |
| `POST` | `/api/agent` | Start autonomous red-team agent |
| `GET` | `/api/dataset/benchmark/stats` | RedForge-Bench-V1 dataset stats |
| `GET` | `/api/dataset/benchmark/case/{id}` | Single bench case by ID |

There's interactive API docs at `http://localhost:8000/docs` once the backend is up.

## Stack

| Layer | What's used |
|---|---|
| API | FastAPI, async |
| Database | SQLite via SQLAlchemy 2.0 async, Alembic for migrations |
| Inference | Ollama REST API at `http://localhost:11434`, called with `httpx` |
| Frontend | React 18, TypeScript, Vite, Tailwind, Recharts |
| UI components | Radix UI |
| Scoring | Keyword and pattern matching, with evaluator modules you can extend |

The frontend and backend are decoupled, so you can hit the API directly or build your own UI on top of it.

## License

MIT
