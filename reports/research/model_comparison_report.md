# RedForge Model Comparison Report — benchmark-lite,3-categories,20/category
_Generated: 2026-06-16 18:57 UTC_

> **Run**: benchmark-lite,3-categories,20/category  **Bench**: RedForge-Bench-V1  **Evaluator**: `llm-judge:qwen3:8b`  **Size**: 20/category × 3 categories = 60 cases (dataset: 800 total)  **Date**: 2026-06-16 18:57 UTC

## Summary

| Model | Overall Score | Injection Rate | Jailbreak Rate | Hallucination Rate | Avg Latency ms | Fallbacks |
|-------|-------------|--- | --- | ---|--------------|-----------|
| qwen3:8b | 93.2 | 5.2% | 12.9% | 0.0% | 16859 ms | 0 |
| gemma:latest | 76.7 | 37.9% | 25.8% | 0.0% | 9955 ms | 0 |
| llama3:latest | 70.5 | 39.7% | 33.9% | 9.3% | 8199 ms | 0 |

## Notes

- **Overall score** uses only scored categories (PROMPT_INJECTION, JAILBREAK, HALLUCINATION, DATA_LEAKAGE). Toxicity excluded until a dedicated evaluator is available.
- **Fallbacks**: cases where the LLM judge returned an unparseable response and fell back to keyword heuristic.
- **Self-judge disclosure**: `qwen3:8b` acts as both a tested model and the judge in this run. Self-judged scores may be inflated; treat with caution.