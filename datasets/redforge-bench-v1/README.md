# RedForge-Bench-V1

A static adversarial benchmark dataset for evaluating LLM safety and robustness. Ships with RedForge V2.1.

## Purpose

RedForge-Bench-V1 provides a reproducible, versioned set of test cases that can be run against any Ollama-compatible LLM to produce comparable security scores across models and over time. It is separate from the dynamic `DatasetEntry` table (which is populated by live test run syncs); this is a read-only static asset.

## Version

`1.0.0`

## Schema

Every entry has the following fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique ID (e.g. `RB-PI-0001`) |
| `category` | enum | `prompt_injection`, `jailbreak`, `data_leakage`, `hallucination`, `toxicity` |
| `difficulty` | enum | `easy`, `medium`, `hard` |
| `severity` | enum | `low`, `medium`, `high`, `critical` |
| `prompt` | string | The adversarial input to send to the model |
| `expected_behavior` | string | What a safe/correct model response looks like |
| `expected_verdict` | enum | `PASS` (model should refuse/handle correctly), `FAIL`, `UNCERTAIN` |
| `tags` | list[str] | Category tags + variant provenance tags |
| `source` | enum | `seed` (hand-authored) or `variant` (mutation-generated) |
| `seed_id` | string | For variants, the ID of the originating seed |
| `strategy` | string\|null | Mutation strategy applied; null for seeds |

**Hallucination entries** additionally include:

| Field | Type | Description |
|---|---|---|
| `ground_truth` | string | The factual correct answer to compare against |

## Per-Category Counts

| Category | Seeds | Total | Expansion strategies |
|---|---|---|---|
| `prompt_injection` | 50 | 200 | leet_speak, base64_wrap, hypothetical_frame, instruction_prefix, unicode_sub, suffix_append |
| `jailbreak` | 50 | 200 | leet_speak, base64_wrap, hypothetical_frame, instruction_prefix, unicode_sub, suffix_append |
| `data_leakage` | 40 | 150 | leet_speak, base64_wrap, hypothetical_frame, instruction_prefix, unicode_sub, suffix_append |
| `hallucination` | 60 | 150 | hypothetical_frame, suffix_append, instruction_prefix (light only — preserves ground_truth validity) |
| `toxicity` | 40 | 100 | suffix_append, instruction_prefix, hypothetical_frame (light only) |
| **Total** | **240** | **800** | |

## Generation Method

1. **Seed authoring:** 240 distinct seed prompts written by hand, covering diverse attack vectors per category. Seeds span all three difficulty levels and all four severity levels.

2. **Mutation expansion:** The RedForge Phase 4 mutation engine (`backend/app/mutations/mutator.py`) is applied to each seed to generate variants. `case_flip` is excluded from expansion — it produces only case-different prompts, which the validator rejects as trivial near-duplicates.

3. **Deduplication:** The generator tracks seen prompts (stripped, lowercased) and skips any mutation whose output collides with an existing entry — either a seed or a previously generated variant.

4. **Validation:** `benchmark_validator.py` enforces: required fields, valid enums, unique IDs, correct ID prefix per category, no duplicate prompts, per-category count minimums, and `ground_truth` presence on all hallucination entries. The loader refuses to serve an invalid dataset.

To regenerate:
```
python datasets/redforge-bench-v1/_generate.py
```

## How to Load and Validate

```python
from app.dataset.benchmark_loader import get_all, get_by_id, get_by_category
from app.dataset.benchmark_validator import validate_dataset
from app.dataset.benchmark_stats import compute_stats

# Load all (validates on first load; raises ValueError if invalid)
data = get_all()

# Lookup by ID
case = get_by_id("RB-PI-0001")

# By category
pi_cases = get_by_category("prompt_injection")

# Stats
stats = compute_stats()
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/dataset/benchmark/stats` | Totals and breakdowns by category/difficulty/severity/source |
| GET | `/api/dataset/benchmark/categories` | Category list with per-category counts |
| GET | `/api/dataset/benchmark/case/{id}` | Single case by ID; 404 if missing |

## Notes on Toxicity

Toxicity entries are **data-only** in this release. RedForge-Bench-V1 includes 100 toxicity cases (40 seeds + 60 variants) with `expected_verdict: "PASS"` (model should refuse). However, there is no automated toxicity *evaluator* yet. Running bench cases against a model will not produce toxicity scores until a dedicated classifier is implemented. Toxicity is excluded from the overall security score to avoid silently penalising models.
