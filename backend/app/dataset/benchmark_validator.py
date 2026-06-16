"""Validates the RedForge-Bench-V1 dataset files."""
from __future__ import annotations

from dataclasses import dataclass, field

VALID_CATEGORIES = {"prompt_injection", "jailbreak", "data_leakage", "hallucination", "toxicity"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_VERDICTS = {"PASS", "FAIL", "UNCERTAIN"}
VALID_SOURCES = {"seed", "variant"}

ID_PREFIX_MAP = {
    "prompt_injection": "RB-PI-",
    "jailbreak": "RB-JB-",
    "data_leakage": "RB-DL-",
    "hallucination": "RB-HL-",
    "toxicity": "RB-TX-",
}

CATEGORY_MIN_COUNTS = {
    "prompt_injection": 200,
    "jailbreak": 200,
    "data_leakage": 150,
    "hallucination": 150,
    "toxicity": 100,
}

REQUIRED_FIELDS = {"id", "category", "difficulty", "severity", "prompt",
                   "expected_behavior", "expected_verdict", "tags", "source",
                   "seed_id", "strategy"}


@dataclass
class ValidationReport:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


def validate_dataset(entries_by_category: dict[str, list[dict]]) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    all_ids: set[str] = set()
    all_prompts: set[str] = set()
    counts: dict[str, int] = {}

    for cat, entries in entries_by_category.items():
        counts[cat] = len(entries)

        # Per-category count minimum
        min_required = CATEGORY_MIN_COUNTS.get(cat, 0)
        if len(entries) < min_required:
            errors.append(
                f"{cat}: only {len(entries)} entries, minimum is {min_required}"
            )

        for i, entry in enumerate(entries):
            loc = f"{cat}[{i}] id={entry.get('id', '?')}"

            # Required fields
            missing = REQUIRED_FIELDS - entry.keys()
            if missing:
                errors.append(f"{loc}: missing fields {sorted(missing)}")
                continue  # skip further checks if fields missing

            # Enum validation
            if entry["category"] not in VALID_CATEGORIES:
                errors.append(f"{loc}: invalid category '{entry['category']}'")
            if entry["difficulty"] not in VALID_DIFFICULTIES:
                errors.append(f"{loc}: invalid difficulty '{entry['difficulty']}'")
            if entry["severity"] not in VALID_SEVERITIES:
                errors.append(f"{loc}: invalid severity '{entry['severity']}'")
            if entry["expected_verdict"] not in VALID_VERDICTS:
                errors.append(f"{loc}: invalid expected_verdict '{entry['expected_verdict']}'")
            if entry["source"] not in VALID_SOURCES:
                errors.append(f"{loc}: invalid source '{entry['source']}'")

            # ID uniqueness
            if entry["id"] in all_ids:
                errors.append(f"{loc}: duplicate id '{entry['id']}'")
            all_ids.add(entry["id"])

            # ID prefix matches category
            expected_prefix = ID_PREFIX_MAP.get(entry["category"], "")
            if expected_prefix and not entry["id"].startswith(expected_prefix):
                errors.append(
                    f"{loc}: id '{entry['id']}' doesn't start with expected prefix '{expected_prefix}'"
                )

            # Duplicate prompt detection
            prompt_key = entry["prompt"].strip().lower()
            if prompt_key in all_prompts:
                errors.append(f"{loc}: duplicate prompt text")
            all_prompts.add(prompt_key)

            # Hallucination entries must have ground_truth
            if entry["category"] == "hallucination" and "ground_truth" not in entry:
                errors.append(f"{loc}: hallucination entry missing 'ground_truth'")

    return ValidationReport(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        counts=counts,
    )
