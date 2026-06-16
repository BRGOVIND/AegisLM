from app.mutations.mutator import (
    mutate_prompt,
    CaseFlipMutation,
    LeetSpeakMutation,
    Base64WrapMutation,
    HypotheticalFrameMutation,
    InstructionPrefixMutation,
    ALL_STRATEGIES,
)
import base64


def test_case_flip():
    m = CaseFlipMutation()
    result = m.mutate("hello")
    assert result == "HeLlO"


def test_leet_speak():
    m = LeetSpeakMutation()
    result = m.mutate("test")
    assert "3" in result or "5" in result  # e->3 or t/s->+/5


def test_base64_wrap():
    m = Base64WrapMutation()
    prompt = "do something bad"
    result = m.mutate(prompt)
    encoded = base64.b64encode(prompt.encode()).decode()
    assert encoded in result


def test_hypothetical_frame():
    m = HypotheticalFrameMutation()
    result = m.mutate("hack the system")
    assert "fictional" in result.lower() or "no safety" in result.lower()


def test_mutate_prompt_returns_all_strategies():
    results = mutate_prompt("test prompt")
    assert len(results) == len(ALL_STRATEGIES)
    names = {r.strategy for r in results}
    assert "base64_wrap" in names
    assert "leet_speak" in names


def test_mutate_prompt_filter_by_strategy():
    results = mutate_prompt("test", strategy_names=["case_flip", "leet_speak"])
    assert len(results) == 2
    assert {r.strategy for r in results} == {"case_flip", "leet_speak"}


def test_mutate_prompt_unknown_strategy_ignored():
    results = mutate_prompt("test", strategy_names=["nonexistent"])
    assert results == []
