"""Loads and caches the RedForge-Bench-V1 static dataset."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.dataset.benchmark_validator import validate_dataset

_DATASET_ROOT = Path(__file__).parent.parent.parent.parent / "datasets" / "redforge-bench-v1"

_CATEGORY_FILES = {
    "prompt_injection": "prompt_injection.json",
    "jailbreak": "jailbreak.json",
    "data_leakage": "data_leakage.json",
    "hallucination": "hallucination.json",
    "toxicity": "toxicity.json",
}

# Module-level cache; populated on first load
_cache: Optional[dict[str, list[dict]]] = None
_id_index: dict[str, dict] = {}


def _load() -> dict[str, list[dict]]:
    global _cache, _id_index
    if _cache is not None:
        return _cache

    entries_by_category: dict[str, list[dict]] = {}
    for cat, filename in _CATEGORY_FILES.items():
        path = _DATASET_ROOT / filename
        with open(path, encoding="utf-8") as f:
            entries_by_category[cat] = json.load(f)

    report = validate_dataset(entries_by_category)
    if not report.passed:
        raise ValueError(
            f"RedForge-Bench-V1 failed validation ({len(report.errors)} error(s)): "
            + "; ".join(report.errors[:5])
            + (" ..." if len(report.errors) > 5 else "")
        )

    _cache = entries_by_category
    _id_index = {e["id"]: e for cat_entries in entries_by_category.values() for e in cat_entries}
    return _cache


def get_all() -> dict[str, list[dict]]:
    return _load()


def get_by_id(entry_id: str) -> Optional[dict]:
    _load()
    return _id_index.get(entry_id)


def get_by_category(category: str) -> list[dict]:
    return _load().get(category, [])


def get_categories() -> list[str]:
    return list(_load().keys())


def total_count() -> int:
    return sum(len(v) for v in _load().values())
