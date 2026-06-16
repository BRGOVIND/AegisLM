# RedForge-Bench-V1 Research Summary
_Generated: 2026-06-16 14:58 UTC_

## What is this?

RedForge-Bench-V1 is a static benchmark of 800 adversarial prompts across 5 categories (PROMPT_INJECTION, JAILBREAK, DATA_LEAKAGE, HALLUCINATION, TOXICITY). Each case has a ground truth verdict and was validated by the RedForge dataset validator.

## Findings

- **Best performer**: `qwen3:8b` with an overall security score of 100.0/100.
- **Score spread**: 0.0 points between best and worst model.
- **Toxicity**: Not assessed in any model — a dedicated evaluator is planned.
- **Overall score** excludes toxicity, consistent with `WeightedScoringEngine._SCORED_CATEGORIES`.

## Files

| File | Contents |
|------|---------|
| `benchmark_results.json` | Full raw results + metrics JSON |
| `benchmark_results.csv` | Per-case CSV for analysis |
| `model_comparison_report.md` | Side-by-side model comparison |
| `security_leaderboard.md` | Ranked leaderboard |

## TODO for you

1. Pull additional models: `ollama pull mistral` / `ollama pull llama3` etc.
2. Re-run with full dataset (remove `--sample`): `python scripts/run_research_benchmark.py --models <list>`
3. Enable LLM judge in `score_response_standalone` for higher-fidelity verdicts.
4. Commit reports: `git add reports/research/ && git commit -m 'research: publish benchmark results'`