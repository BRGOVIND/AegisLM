# AegisLM

AegisLM is a local AI red-teaming and security evaluation platform for Large Language Models running through Ollama.

It automatically tests models against prompt-injection attacks, jailbreak attempts, data-leakage probes, and hallucination benchmarks, then generates security scores, benchmark reports, and vulnerability analytics.

Everything runs locally.

No cloud APIs.
No external inference.
No model data leaves your machine.

## Why I Built This

Most AI projects stop at building a chatbot.

I wanted to understand how secure and reliable local LLMs actually are.

AegisLM attacks models, evaluates their responses, measures failure rates, and compares different models under the same benchmark conditions.

## Current Capabilities

- 28 adversarial attacks across 4 categories
- Multi-model benchmarking
- Prompt injection testing
- Jailbreak evaluation
- Hallucination assessment
- LLM-as-a-Judge scoring
- Security leaderboards
- Historical performance tracking
- Autonomous red-team agent
- PDF and JSON reporting
- AegisLM-Bench-V1 (800 benchmark cases)

## Benchmark Results

| Model | Security Score |
|---------|---------|
| Qwen3:8b | 93.2 |
| Gemma | 76.7 |
| Llama3 | 70.5 |

Most vulnerable category across tested models:

**Prompt Injection (27.6% average failure rate)**

> Benchmark configuration: 3 models, 3 categories, 20 cases per category, 60 benchmark cases per model.
