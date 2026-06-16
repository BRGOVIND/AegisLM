"""Tests for the research benchmark harness (run_research_benchmark.py)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

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

FAKE_RUN_META = {
    "bench_version": "RedForge-Bench-V1",
    "evaluator": "llm-judge:qwen3:8b",
    "sample_size": 10,
    "total_cases_loaded": 800,
    "date": "2026-06-16 15:00 UTC",
    "heuristic_fallback_by_model": {"m1": 0},
}


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
    result = harness.score_response_standalone("toxic prompt", "I refuse to say that.", "toxicity", "high")
    assert result["verdict"] in ("PASS", "FAIL", "UNCERTAIN")


# ---------------------------------------------------------------------------
# LLM judge scorer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_judge_parses_pass_verdict():
    with patch.object(harness, "ollama_generate", new_callable=AsyncMock, return_value=("VERDICT: PASS", 50)):
        result = await harness.score_response_llm_judge("attack", "I cannot help.", "jailbreak", "qwen3:8b")
    assert result["verdict"] == "PASS"
    assert result["fallback"] is False
    assert "llm-judge" in result["judge_used"]


@pytest.mark.asyncio
async def test_llm_judge_parses_fail_verdict():
    with patch.object(harness, "ollama_generate", new_callable=AsyncMock, return_value=("VERDICT: FAIL — model complied", 50)):
        result = await harness.score_response_llm_judge("attack", "Sure here you go", "jailbreak", "qwen3:8b")
    assert result["verdict"] == "FAIL"
    assert result["fallback"] is False


@pytest.mark.asyncio
async def test_llm_judge_falls_back_on_unparseable():
    """If judge returns garbage, fall back to heuristic and set fallback=True."""
    with patch.object(harness, "ollama_generate", new_callable=AsyncMock, return_value=("I dunno", 50)):
        result = await harness.score_response_llm_judge(
            "attack", "I cannot help with that.", "jailbreak", "qwen3:8b"
        )
    assert result["verdict"] in ("PASS", "FAIL", "UNCERTAIN")
    assert result["fallback"] is True
    assert result["judge_used"] == "heuristic"


@pytest.mark.asyncio
async def test_llm_judge_falls_back_on_network_error():
    with patch.object(harness, "ollama_generate", new_callable=AsyncMock, side_effect=Exception("timeout")):
        result = await harness.score_response_llm_judge("attack", "response", "jailbreak", "qwen3:8b")
    assert result["fallback"] is True
    assert result["judge_used"] == "heuristic"


# ---------------------------------------------------------------------------
# compute_model_metrics
# ---------------------------------------------------------------------------

def test_metrics_toxicity_assessed_is_false():
    fake_results = [{"category": "toxicity", "severity": "high", "verdict": "FAIL", "score": 0.2, "latency_ms": 100}]
    metrics = harness.compute_model_metrics("m1", fake_results)
    assert metrics["toxicity_assessed"] is False


def test_metrics_overall_score_excludes_toxicity():
    fake_results = [
        {"category": "toxicity", "severity": "high", "verdict": "FAIL", "score": 0.0, "latency_ms": 50},
        {"category": "toxicity", "severity": "high", "verdict": "FAIL", "score": 0.0, "latency_ms": 50},
    ]
    metrics = harness.compute_model_metrics("m1", fake_results)
    assert metrics["overall_score"] == 100.0


def test_metrics_missing_model_returns_zero_cases():
    metrics = harness.compute_model_metrics("ghost-model", [])
    assert metrics["total_cases"] == 0
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


def test_metrics_heuristic_fallback_count():
    results = [
        {"category": "jailbreak", "severity": "medium", "verdict": "PASS", "score": 1.0,
         "latency_ms": 100, "judge_used": "heuristic", "fallback": True},
        {"category": "jailbreak", "severity": "medium", "verdict": "FAIL", "score": 0.1,
         "latency_ms": 100, "judge_used": "llm-judge:qwen3:8b", "fallback": False},
    ]
    metrics = harness.compute_model_metrics("m1", results)
    assert metrics["heuristic_fallback_count"] == 1


# ---------------------------------------------------------------------------
# load_benchmark_cases — unit tests using a fake dataset dir
# ---------------------------------------------------------------------------

def _write_fake_dataset(tmp_path: Path, n_per_cat: int = 5) -> Path:
    """Create a minimal fake dataset dir with 3 categories."""
    ds = tmp_path / "datasets" / "redforge-bench-v1"
    ds.mkdir(parents=True)
    for cat in ("prompt_injection", "jailbreak", "hallucination", "data_leakage", "toxicity"):
        cases = [{"id": f"{cat[:2]}_{i}", "prompt": f"p{i}", "category": cat,
                  "difficulty": "medium", "severity": "high"} for i in range(n_per_cat)]
        (ds / f"{cat}.json").write_text(json.dumps(cases))
    return tmp_path


def test_load_benchmark_cases_all(tmp_path, monkeypatch):
    root = _write_fake_dataset(tmp_path, n_per_cat=5)
    monkeypatch.setattr(harness, "REPO_ROOT", root)
    cases = harness.load_benchmark_cases(None)
    assert len(cases) == 25  # 5 cats × 5 each


def test_load_benchmark_cases_category_filter(tmp_path, monkeypatch):
    root = _write_fake_dataset(tmp_path, n_per_cat=5)
    monkeypatch.setattr(harness, "REPO_ROOT", root)
    cases = harness.load_benchmark_cases(None, categories=["jailbreak", "hallucination"])
    cats_seen = {c["category"] for c in cases}
    assert cats_seen == {"jailbreak", "hallucination"}
    assert len(cases) == 10


def test_load_benchmark_cases_per_category(tmp_path, monkeypatch):
    root = _write_fake_dataset(tmp_path, n_per_cat=5)
    monkeypatch.setattr(harness, "REPO_ROOT", root)
    cases = harness.load_benchmark_cases(
        None,
        categories=["jailbreak", "prompt_injection", "hallucination"],
        per_category=3,
    )
    assert len(cases) == 9  # 3 cats × 3 each
    cats = [c["category"] for c in cases]
    assert cats.count("jailbreak") == 3
    assert cats.count("prompt_injection") == 3
    assert cats.count("hallucination") == 3


def test_load_benchmark_cases_per_category_deterministic(tmp_path, monkeypatch):
    """Same per_category call returns identical case IDs every time."""
    root = _write_fake_dataset(tmp_path, n_per_cat=5)
    monkeypatch.setattr(harness, "REPO_ROOT", root)
    kwargs = dict(categories=["jailbreak", "hallucination"], per_category=2)
    run1 = [c["id"] for c in harness.load_benchmark_cases(None, **kwargs)]
    run2 = [c["id"] for c in harness.load_benchmark_cases(None, **kwargs)]
    assert run1 == run2


@pytest.mark.asyncio
async def test_run_model_benchmark_checkpoint_filtered_to_cases(tmp_path, monkeypatch):
    """Checkpoint with 5 results but only 2 match the current case list → returns 2."""
    monkeypatch.setattr(harness, "CHECKPOINT_FILE", tmp_path / "ckpt.json")
    monkeypatch.setattr(harness, "REPORTS_DIR", tmp_path)

    all_ckpt_results = [
        {"case_id": f"pi_{i}", "verdict": "PASS", "score": 1.0, "latency_ms": 10,
         "category": "prompt_injection", "difficulty": "medium", "severity": "high",
         "status": "ok", "judge_used": "heuristic"}
        for i in range(5)
    ]
    checkpoint = {"test-model": all_ckpt_results}
    # Only request 2 of those 5 cases
    cases_subset = [{"id": "pi_0", "category": "prompt_injection", "difficulty": "medium",
                     "severity": "high", "prompt": "p0"},
                    {"id": "pi_2", "category": "prompt_injection", "difficulty": "medium",
                     "severity": "high", "prompt": "p2"}]

    with patch.object(harness, "ollama_generate", new_callable=AsyncMock) as mock_gen:
        results = await harness.run_model_benchmark("test-model", cases_subset, checkpoint, verbose=False)

    mock_gen.assert_not_called()
    assert len(results) == 2
    assert {r["case_id"] for r in results} == {"pi_0", "pi_2"}


def test_load_benchmark_cases_label_in_leaderboard(tmp_path, monkeypatch):
    """write_leaderboard emits the label string when run_meta has one."""
    monkeypatch.setattr(harness, "LEADERBOARD_MD", tmp_path / "lb.md")
    meta = harness.build_run_meta(
        "llm-judge:qwen3:8b", None, 800, "2026-06-17", {},
        label="benchmark-lite,3-categories,20/category",
        categories=["jailbreak", "prompt_injection", "hallucination"],
        per_category_n=20,
    )
    metrics = [{"model": "qwen3:8b", "overall_score": 90.0, "total_cases": 60,
                "fail_count": 6, "avg_latency_ms": 500, "heuristic_fallback_count": 0}]
    harness.write_leaderboard(metrics, meta)
    text = (tmp_path / "lb.md").read_text()
    assert "benchmark-lite" in text


def test_write_summary_per_category_note(tmp_path, monkeypatch):
    """write_summary shows per-category size when per_category_n + categories set."""
    monkeypatch.setattr(harness, "SUMMARY_MD", tmp_path / "s.md")
    meta = harness.build_run_meta(
        "llm-judge:qwen3:8b", None, 800, "2026-06-17", {},
        label="benchmark-lite,3-categories,20/category",
        categories=["jailbreak", "prompt_injection", "hallucination"],
        per_category_n=20,
    )
    meta["self_judge_disclosure"] = "qwen3:8b is both tested and judge."
    metrics = [{"model": "qwen3:8b", "overall_score": 90.0, "total_cases": 60,
                "fail_count": 6, "avg_latency_ms": 500, "heuristic_fallback_count": 0,
                "prompt_injection_rate": 0.1, "jailbreak_rate": 0.2, "hallucination_rate": 0.05}]
    harness.write_summary(metrics, skipped_models=[], run_meta=meta)
    text = (tmp_path / "s.md").read_text()
    assert "20" in text and "3 categories" in text
    assert "Self-judge" in text or "self_judge" in text.lower() or "qwen3:8b is both" in text


# ---------------------------------------------------------------------------
# build_run_meta / _meta_header
# ---------------------------------------------------------------------------

def test_build_run_meta_records_evaluator():
    meta = harness.build_run_meta("llm-judge:qwen3:8b", 40, 800, "2026-06-16", {"m1": 2})
    assert meta["evaluator"] == "llm-judge:qwen3:8b"
    assert meta["bench_version"] == harness.BENCH_VERSION
    assert meta["sample_size"] == 40
    assert meta["heuristic_fallback_by_model"]["m1"] == 2


def test_meta_header_shows_evaluator():
    meta = harness.build_run_meta("heuristic", 10, 800, "2026-06-16", {})
    header = harness._meta_header(meta)
    assert any("heuristic" in line for line in header)


def test_meta_header_none_returns_legacy_note():
    header = harness._meta_header(None)
    assert any("legacy" in line or "not recorded" in line for line in header)


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
                 "severity": c["severity"], "status": "ok", "judge_used": "heuristic"}
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


@pytest.mark.asyncio
async def test_run_model_benchmark_records_judge_used(tmp_path, monkeypatch):
    """Each result row records which evaluator was used."""
    monkeypatch.setattr(harness, "CHECKPOINT_FILE", tmp_path / "ckpt.json")
    monkeypatch.setattr(harness, "REPORTS_DIR", tmp_path)

    cases = [{"id": "pi_0", "category": "prompt_injection", "difficulty": "easy",
               "severity": "medium", "prompt": "test"}]

    with patch.object(harness, "ollama_generate", new_callable=AsyncMock, return_value=("I cannot help", 50)):
        results = await harness.run_model_benchmark("test-model", cases, {}, judge_model=None, verbose=False)

    assert results[0]["judge_used"] == "heuristic"


# ---------------------------------------------------------------------------
# Output file shapes
# ---------------------------------------------------------------------------

def test_write_json_includes_run_meta(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "RESULTS_JSON", tmp_path / "r.json")
    fake_results = {"m1": [{"case_id": "x", "verdict": "PASS", "score": 1.0, "latency_ms": 10,
                             "category": "jailbreak", "difficulty": "easy", "severity": "low",
                             "status": "ok", "judge_used": "heuristic"}]}
    metrics = [harness.compute_model_metrics("m1", fake_results["m1"])]
    harness.write_json(fake_results, metrics, FAKE_RUN_META)
    data = json.loads((tmp_path / "r.json").read_text())
    assert "model_metrics" in data
    assert "raw_results" in data
    assert "run_meta" in data
    assert data["run_meta"]["evaluator"] == "llm-judge:qwen3:8b"


def test_write_json_without_run_meta_still_works(tmp_path, monkeypatch):
    """write_json with no run_meta (legacy call) must not crash."""
    monkeypatch.setattr(harness, "RESULTS_JSON", tmp_path / "r.json")
    fake_results = {"m1": []}
    harness.write_json(fake_results, [], None)
    data = json.loads((tmp_path / "r.json").read_text())
    assert "run_meta" in data


def test_write_csv_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "RESULTS_CSV", tmp_path / "r.csv")
    fake_results = {"m1": [{"case_id": "x", "verdict": "PASS", "score": 1.0, "latency_ms": 10,
                             "category": "jailbreak", "difficulty": "easy", "severity": "low",
                             "status": "ok", "judge_used": "heuristic"}]}
    harness.write_csv(fake_results)
    text = (tmp_path / "r.csv").read_text()
    assert "model" in text
    assert "verdict" in text
    assert "judge_used" in text
    assert "m1" in text


def test_write_leaderboard_contains_evaluator(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "LEADERBOARD_MD", tmp_path / "lb.md")
    metrics = [{"model": "qwen3:8b", "overall_score": 82.5, "total_cases": 10,
                "fail_count": 2, "avg_latency_ms": 300, "heuristic_fallback_count": 1}]
    harness.write_leaderboard(metrics, FAKE_RUN_META)
    text = (tmp_path / "lb.md").read_text()
    assert "qwen3:8b" in text
    assert "82.5" in text
    assert "llm-judge" in text


def test_write_leaderboard_no_meta_still_works(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "LEADERBOARD_MD", tmp_path / "lb.md")
    metrics = [{"model": "qwen3:8b", "overall_score": 82.5, "total_cases": 10,
                "fail_count": 2, "avg_latency_ms": 300, "heuristic_fallback_count": 0}]
    harness.write_leaderboard(metrics)
    text = (tmp_path / "lb.md").read_text()
    assert "qwen3:8b" in text


def test_write_summary_lists_skipped_models_and_evaluator(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "SUMMARY_MD", tmp_path / "s.md")
    metrics = [{"model": "qwen3:8b", "overall_score": 85.0, "total_cases": 5,
                "fail_count": 1, "avg_latency_ms": 200, "heuristic_fallback_count": 0,
                "prompt_injection_rate": 0.1, "jailbreak_rate": 0.2}]
    harness.write_summary(metrics, skipped_models=["mistral:7b", "llama3:8b"], run_meta=FAKE_RUN_META)
    text = (tmp_path / "s.md").read_text()
    assert "mistral:7b" in text
    assert "llama3:8b" in text
    assert "Not assessed" in text or "not assessed" in text.lower()
    assert "llm-judge" in text


def test_write_comparison_report_shows_evaluator(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "COMPARISON_MD", tmp_path / "c.md")
    metrics = [{"model": "qwen3:8b", "overall_score": 80.0, "total_cases": 5,
                "fail_count": 1, "avg_latency_ms": 200, "heuristic_fallback_count": 0,
                "prompt_injection_rate": 0.0, "jailbreak_rate": 0.0, "data_leakage_rate": 0.0,
                "toxicity_assessed": False}]
    harness.write_comparison_report(metrics, FAKE_RUN_META)
    text = (tmp_path / "c.md").read_text()
    assert "llm-judge" in text
    assert "Fallbacks" in text
