"""Computes statistics over the RedForge-Bench-V1 dataset."""
from __future__ import annotations

from app.dataset.benchmark_loader import get_all


def compute_stats() -> dict:
    data = get_all()
    all_entries = [e for cat_list in data.values() for e in cat_list]

    by_category: dict[str, int] = {}
    by_difficulty: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_source: dict[str, int] = {}

    for entry in all_entries:
        cat = entry.get("category", "unknown")
        diff = entry.get("difficulty", "unknown")
        sev = entry.get("severity", "unknown")
        src = entry.get("source", "unknown")

        by_category[cat] = by_category.get(cat, 0) + 1
        by_difficulty[diff] = by_difficulty.get(diff, 0) + 1
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_source[src] = by_source.get(src, 0) + 1

    return {
        "total": len(all_entries),
        "by_category": by_category,
        "by_difficulty": by_difficulty,
        "by_severity": by_severity,
        "by_source": by_source,
    }
