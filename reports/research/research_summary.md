# RedForge-Bench-V1 Research Summary — benchmark-lite,3-categories,20/category
_Generated: 2026-06-16 18:57 UTC_

> **Run**: benchmark-lite,3-categories,20/category  **Bench**: RedForge-Bench-V1  **Evaluator**: `llm-judge:qwen3:8b`  **Size**: 20/category × 3 categories = 60 cases (dataset: 800 total)  **Date**: 2026-06-16 18:57 UTC

## What is this?

RedForge-Bench-V1 is a static benchmark of 800 adversarial prompts across 5 categories (PROMPT_INJECTION, JAILBREAK, DATA_LEAKAGE, HALLUCINATION, TOXICITY). Each case has a ground truth verdict and was validated by the RedForge dataset validator.

## Run Details

| Field | Value |
|-------|-------|
| Bench version | RedForge-Bench-V1 |
| Run label | benchmark-lite,3-categories,20/category |
| Categories tested | jailbreak, prompt_injection, hallucination |
| Evaluator | `llm-judge:qwen3:8b` |
| Run size | 20 cases/category × 3 categories = 60 cases (dataset: 800 total) |
| Date | 2026-06-16 18:57 UTC |
| Models benchmarked | `qwen3:8b`, `gemma:latest`, `llama3:latest` |
| Models skipped | (none) |

> **Self-judge disclosure**: `qwen3:8b` acts as both a tested model and the judge in this run. Self-judged scores may be inflated; treat with caution.

## Findings

- **Most secure**: `qwen3:8b` — overall score 93.2/100 (3 failures out of 60 cases).
- **Most vulnerable**: `llama3:latest` — overall score 70.5/100 (16 failures out of 60 cases).
- **Score spread**: 22.7 points between best and worst model.
- **Most vulnerable category** (avg across models): PROMPT_INJECTION (27.6% weighted failure rate).
- **Fastest model**: `llama3:latest` at 8199 ms avg per case.
- **Toxicity**: Not assessed — a dedicated toxicity evaluator is planned.
- **Overall score** excludes toxicity (consistent with `WeightedScoringEngine._SCORED_CATEGORIES`).

## Files

| File | Contents |
|------|---------|
| `benchmark_results.json` | Full raw results + run_meta JSON |
| `benchmark_results.csv` | Per-case CSV (includes judge_used column) |
| `model_comparison_report.md` | Side-by-side model comparison |
| `security_leaderboard.md` | Ranked leaderboard |