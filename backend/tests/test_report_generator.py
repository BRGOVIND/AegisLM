from app.reports.generator import generate_report, _risk_level


def test_risk_level():
    assert _risk_level(80) == "CRITICAL"
    assert _risk_level(60) == "HIGH"
    assert _risk_level(30) == "MEDIUM"
    assert _risk_level(10) == "LOW"


def test_report_with_no_test_runs():
    report = generate_report("test-model", [])
    assert report["total_tests"] == 0
    assert report["fail_rate"] == 0.0
    assert "executive_summary" in report
    assert report["executive_summary"]["risk_level"] == "LOW"


class FakeAttack:
    def __init__(self, category):
        self.category = category


class FakeRun:
    def __init__(self, verdict, category, latency=100):
        self.verdict = verdict
        self.latency_ms = latency
        self.attack = FakeAttack(category)


def test_report_high_fail_rate():
    runs = [FakeRun("FAIL", "PROMPT_INJECTION") for _ in range(8)] + \
           [FakeRun("PASS", "PROMPT_INJECTION") for _ in range(2)]
    report = generate_report("model-x", runs)
    assert report["fail_rate"] == 80.0
    assert report["executive_summary"]["risk_level"] == "CRITICAL"
    assert report["executive_summary"]["deployment_recommendation"] == "NOT RECOMMENDED"
    assert len(report["findings"]) >= 1


def test_report_low_fail_rate():
    runs = [FakeRun("PASS", "JAILBREAK") for _ in range(10)]
    report = generate_report("safe-model", runs)
    assert report["fail_rate"] == 0.0
    assert report["executive_summary"]["risk_level"] == "LOW"
    assert report["executive_summary"]["deployment_recommendation"] == "APPROVED"
