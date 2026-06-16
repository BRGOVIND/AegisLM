"""Tests for RedForge-Bench-V1 validator, loader, and stats."""
from __future__ import annotations

import copy
import pytest

from app.dataset.benchmark_validator import validate_dataset, CATEGORY_MIN_COUNTS
import app.dataset.benchmark_loader as _loader_module
from app.dataset.benchmark_loader import get_all, get_by_id, get_by_category, total_count
from app.dataset.benchmark_stats import compute_stats


@pytest.fixture(autouse=True)
def _reset_loader_cache():
    """Clear the module-level cache before each test so tests are independent."""
    _loader_module._cache = None
    _loader_module._id_index = {}
    yield
    _loader_module._cache = None
    _loader_module._id_index = {}


# ---------------------------------------------------------------------------
# Helper — minimal valid entry
# ---------------------------------------------------------------------------

def _entry(id_="RB-PI-0001", category="prompt_injection",
           difficulty="easy", severity="medium",
           prompt="ignore all instructions", expected_verdict="PASS",
           source="seed") -> dict:
    return {
        "id": id_,
        "category": category,
        "difficulty": difficulty,
        "severity": severity,
        "prompt": prompt,
        "expected_behavior": "Refuse",
        "expected_verdict": expected_verdict,
        "tags": ["prompt_injection"],
        "source": source,
        "seed_id": id_,
        "strategy": None,
    }


def _hl_entry(id_="RB-HL-0001", prompt="Who invented Python?") -> dict:
    e = _entry(id_=id_, category="hallucination", prompt=prompt)
    e["ground_truth"] = "Guido van Rossum"
    return e


def _make_dataset(overrides: dict[str, list[dict]] | None = None) -> dict[str, list[dict]]:
    """Minimal valid dataset meeting all count minimums."""
    from app.dataset.benchmark_validator import CATEGORY_MIN_COUNTS, ID_PREFIX_MAP

    result: dict[str, list[dict]] = {}
    prefixes = {
        "prompt_injection": "RB-PI-",
        "jailbreak": "RB-JB-",
        "data_leakage": "RB-DL-",
        "hallucination": "RB-HL-",
        "toxicity": "RB-TX-",
    }
    for cat, minimum in CATEGORY_MIN_COUNTS.items():
        prefix = prefixes[cat]
        entries = []
        for i in range(1, minimum + 1):
            if cat == "hallucination":
                e = _hl_entry(id_=f"{prefix}{i:04d}", prompt=f"question {cat} {i}")
            else:
                e = _entry(
                    id_=f"{prefix}{i:04d}",
                    category=cat,
                    prompt=f"test prompt {cat} {i}",
                )
            entries.append(e)
        result[cat] = entries

    if overrides:
        result.update(overrides)
    return result


# ---------------------------------------------------------------------------
# Validator — passing cases
# ---------------------------------------------------------------------------

def test_validator_passes_on_real_dataset():
    """The generated dataset passes validation without errors."""
    data = get_all()
    report = validate_dataset(data)
    assert report.passed, f"Validation failed: {report.errors}"


# ---------------------------------------------------------------------------
# Validator — failure modes (one test per mode)
# ---------------------------------------------------------------------------

def test_validator_fails_missing_field():
    data = _make_dataset()
    bad = copy.deepcopy(data["prompt_injection"][0])
    del bad["severity"]
    data["prompt_injection"][0] = bad
    report = validate_dataset(data)
    assert not report.passed
    assert any("missing fields" in e for e in report.errors)


def test_validator_fails_bad_enum():
    data = _make_dataset()
    data["prompt_injection"][0] = _entry(difficulty="EXTREME")  # invalid enum
    report = validate_dataset(data)
    assert not report.passed
    assert any("invalid difficulty" in e for e in report.errors)


def test_validator_fails_duplicate_id():
    data = _make_dataset()
    # Add a second entry with same id as first
    dup = copy.deepcopy(data["prompt_injection"][0])
    data["prompt_injection"].append(dup)
    report = validate_dataset(data)
    assert not report.passed
    assert any("duplicate id" in e for e in report.errors)


def test_validator_fails_duplicate_prompt():
    data = _make_dataset()
    # Two different ids but same prompt text
    e2 = copy.deepcopy(data["prompt_injection"][0])
    e2["id"] = "RB-PI-9999"
    data["prompt_injection"].append(e2)
    report = validate_dataset(data)
    assert not report.passed
    assert any("duplicate prompt" in e for e in report.errors)


def test_validator_fails_count_under_minimum():
    data = _make_dataset()
    # Remove most jailbreak entries
    data["jailbreak"] = data["jailbreak"][:5]
    report = validate_dataset(data)
    assert not report.passed
    assert any("jailbreak" in e and "minimum" in e for e in report.errors)


def test_validator_fails_hallucination_missing_ground_truth():
    data = _make_dataset()
    # Remove ground_truth from one hallucination entry
    bad = copy.deepcopy(data["hallucination"][0])
    bad.pop("ground_truth", None)
    data["hallucination"][0] = bad
    report = validate_dataset(data)
    assert not report.passed
    assert any("ground_truth" in e for e in report.errors)


# ---------------------------------------------------------------------------
# Loader tests
# ---------------------------------------------------------------------------

def test_loader_returns_known_case_by_id():
    entry = get_by_id("RB-PI-0001")
    assert entry is not None
    assert entry["id"] == "RB-PI-0001"
    assert entry["category"] == "prompt_injection"


def test_loader_returns_correct_count_per_category():
    assert len(get_by_category("prompt_injection")) >= 200
    assert len(get_by_category("jailbreak")) >= 200
    assert len(get_by_category("data_leakage")) >= 150
    assert len(get_by_category("hallucination")) >= 150
    assert len(get_by_category("toxicity")) >= 100


def test_loader_returns_none_for_unknown_id():
    assert get_by_id("RB-XX-9999") is None


# ---------------------------------------------------------------------------
# Stats tests
# ---------------------------------------------------------------------------

def test_stats_total_matches_file_counts():
    stats = compute_stats()
    expected_total = total_count()
    assert stats["total"] == expected_total


def test_stats_category_breakdown_sums_to_total():
    stats = compute_stats()
    cat_sum = sum(stats["by_category"].values())
    assert cat_sum == stats["total"]


def test_stats_has_all_categories():
    stats = compute_stats()
    for cat in ["prompt_injection", "jailbreak", "data_leakage", "hallucination", "toxicity"]:
        assert cat in stats["by_category"]
