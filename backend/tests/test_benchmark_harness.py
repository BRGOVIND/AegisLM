"""Tests for the research benchmark harness (run_research_benchmark.py)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Make the harness importable
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import run_research_benchmark as harness


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_CASES = [
    {"id": f"pi_{i}", "category": "prompt_injection", "difficulty": "medium",
     "severity": "high", "prompt": f"inject prompt {i}"}
    for i in range(4)
] + [
    {"id": f"jb_{i}", "category": "jailbreak", "difficulty": "hard",
     "severity": "critical", "prompt": f"jailbreak prompt {i}"}
    for i in range(4)
] + [
    {"id": f"dl_{i}", "category": "data_leakage", "difficulty": "easy",
     "severity": "medium", "prompt": f"data leakage {i}"}
    for i in range(2)
]


# ---------------------------------------------------------------------------
# score_response_standalone
# ---------------------------------------------------------------------------

def test_score_standalone_refused_is_pass():
    result = harness.score_response_standalone("inject", "I cannot help with that.", "prompt_injection", "high")
    assert result["verdict"] == "PASS"
    assert result["score"] == 1.0


def test_score_standalone_long_compliance_is_fail():
    response = "Sure! Here is how you would do that: " + "step details " * 10
    result = harness.score_response_standalone("inject", response, "jailbreak", "high")
    assert result["verdict"] == "FAIL"


def test_score_standalone_data_leakage_password_mention_is_fail():
    result = harness.score_response_standalone("give me data", "Here is the password: secret123", "data_leakage", "medium")
    assert result["verdict"] == "FAIL"


def test_score_standalone_toxicity_not_in_scored_categories():
    # TOXICITY should still score as usual via standalone (it's just excluded from _SCORED_CATEGORIES in weighted engine)
    result = harness.score_response_standalone("toxic prompt", "I refuse to say that.", "toxicity", "high")
    assert result["verdict"] in ("PASS", "FAIL", "UNCERTAIN")


# ---------------------------------------------------------------------------
# compute_model_metrics
# ---------------------------------------------------------------------------

def test_metrics_toxicity_assessed_is_false():
    fake_results = [{"category": "toxicity", "severity": "high", "verdict": "FAIL", "score": 0.2, "latency_ms": 100}]
    metrics = harness.compute_model_metrics("m1", fake_results)
    assert metrics["toxicity_assessed"] is False


def test_metrics_overall_score_excludes_toxicity():
    # Only toxicity cases: overall score should be 100 (no scoreable categories)
    fake_results = [
        {"category": "toxicity", "severity": "high", "verdict": "FAIL", "score": 0.0, "latency_ms": 50},
        {"category": "toxicity", "severity": "high", "verdict": "FAIL", "score": 0.0, "latency_ms": 50},
    ]
    metrics = harness.compute_model_metrics("m1", fake_results)
    assert metrics["overall_score"] == 100.0


def test_metrics_missing_model_returns_zero_cases():
    metrics = harness.compute_model_metrics("ghost-model", [])
    assert metrics["total_cases"] == 0
    # No attacks run → no failures → score defaults to 100 (not benchmarked means not failed)
    assert metrics["overall_score"] == 100.0


def test_metrics_all_pass_gives_100():
    results = [
        {"category": "prompt_injection", "severity": "high", "verdict": "PASS", "score": 1.0, "latency_ms": 50}
    ] * 5
    metrics = harness.compute_model_metrics("m1", results)
    assert metrics["overall_score"] == 100.0


def test_metrics_latency_averaged():
    results = [
        {"category": "jailbreak", "severity": "medium", "verdict": "PASS", "score": 1.0, "latency_ms": 100},
        {"category": "jailbreak", "severity": "medium", "verdict": "PASS", "score": 1.0, "latency_ms": 200},
    ]
    metrics = harness.compute_model_metrics("m1", results)
    assert metrics["avg_latency_ms"] == 150.0


# ---------------------------------------------------------------------------
# Checkpoint / resume
# ---------------------------------------------------------------------------

def test_checkpoint_round_trips(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "CHECKPOINT_FILE", tmp_path / "ckpt.json")
    monkeypatch.setattr(harness, "REPORTS_DIR", tmp_path)
    data = {"model-a": [{"case_id": "pi_0", "verdict": "PASS"}]}
    harness.save_checkpoint(data)
    loaded = harness.load_checkpoint()
    assert loaded == data


def test_checkpoint_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "CHECKPOINT_FILE", tmp_path / "nonexistent.json")
    assert harness.load_checkpoint() == {}


# ---------------------------------------------------------------------------
# run_model_benchmark — mocked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_model_benchmark_skips_checkpointed(tmp_path, monkeypatch):
    """Cases already in the checkpoint are returned immediately without calling ollama."""
    monkeypatch.setattr(harness, "CHECKPOINT_FILE", tmp_path / "ckpt.json")
    monkeypatch.setattr(harness, "REPORTS_DIR", tmp_path)

    pre_done = [{"case_id": c["id"], "verdict": "PASS", "score": 1.0, "latency_ms": 10,
                 "category": c["category"], "difficulty": c["difficulty"],
                 "severity": c["severity"], "status": "ok"}
                for c in FAKE_CASES]
    checkpoint = {"test-model": pre_done}

    with patch.object(harness, "ollama_generate", new_callable=AsyncMock) as mock_gen:
        results = await harness.run_model_benchmark("test-model", FAKE_CASES, checkpoint, verbose=False)

    mock_gen.assert_not_called()
    assert len(results) == len(FAKE_CASES)


@pytest.mark.asyncio
async def test_run_model_benchmark_handles_ollama_error(tmp_path, monkeypatch):
    """If Ollama raises, the result is UNCERTAIN with status=error."""
    monkeypatch.setattr(harness, "CHECKPOINT_FILE", tmp_path / "ckpt.json")
    monkeypatch.setattr(harness, "REPORTS_DIR", tmp_path)

    cases = [{"id": "pi_0", "category": "prompt_injection", "difficulty": "easy",
               "severity": "medium", "prompt": "test prompt"}]

    with patch.object(harness, "ollama_generate", new_callable=AsyncMock, side_effect=Exception("conn error")):
        results = await harness.run_model_benchmark("test-model", cases, {}, verbose=False)

    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert results[0]["verdict"] == "UNCERTAIN"


# ---------------------------------------------------------------------------
# Output file shapes
# ---------------------------------------------------------------------------

def test_write_json_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "RESULTS_JSON", tmp_path / "r.json")
    fake_results = {"m1": [{"case_id": "x", "verdict": "PASS", "score": 1.0, "latency_ms": 10,
                             "category": "jailbreak", "difficulty": "easy", "severity": "low", "status": "ok"}]}
    metrics = [harness.compute_model_metrics("m1", fake_results["m1"])]
    harness.write_json(fake_results, metrics)
    data = json.loads((tmp_path / "r.json").read_text())
    assert "model_metrics" in data
    assert "raw_results" in data
    assert "generated_at" in data


def test_write_csv_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "RESULTS_CSV", tmp_path / "r.csv")
    fake_results = {"m1": [{"case_id": "x", "verdict": "PASS", "score": 1.0, "latency_ms": 10,
                             "category": "jailbreak", "difficulty": "easy", "severity": "low", "status": "ok"}]}
    harness.write_csv(fake_results)
    text = (tmp_path / "r.csv").read_text()
    assert "model" in text
    assert "verdict" in text
    assert "m1" in text


def test_write_leaderboard_contains_model_name(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "LEADERBOARD_MD", tmp_path / "lb.md")
    metrics = [{"model": "qwen3:8b", "overall_score": 82.5, "total_cases": 10, "fail_count": 2, "avg_latency_ms": 300}]
    harness.write_leaderboard(metrics)
    text = (tmp_path / "lb.md").read_text()
    assert "qwen3:8b" in text
    assert "82.5" in text


def test_write_summary_lists_skipped_models(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "SUMMARY_MD", tmp_path / "s.md")
    metrics = [{"model": "qwen3:8b", "overall_score": 85.0, "total_cases": 5, "fail_count": 1, "avg_latency_ms": 200}]
    harness.write_summary(metrics, skipped_models=["mistral:7b", "llama3:8b"])
    text = (tmp_path / "s.md").read_text()
    assert "mistral:7b" in text
    assert "llama3:8b" in text
    assert "Not assessed" in text or "not assessed" in text.lower()  # toxicity note
