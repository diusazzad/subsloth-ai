"""
SubSloth AI - Empirical Benchmark Evaluation Engine
Provides reproducible evaluation metrics for Layer 1 deterministic regex parsing,
dark pattern classification heuristics, and statutory guardrail verification.

NOTE: This is a curated 6-case regression test set designed for automated sanity
and regression checking, NOT a statistical representative population study.
Latency measurements reflect local CPU deterministic parser execution only
(excluding remote Gemma 2 model inference, network roundtrips, and browser DOM rendering).
"""

import time
from typing import Dict, Any, List, Optional
from core.subscription_detector import audit_statement
from core.backboard_client import synthesize_cancellation_tiers


BENCHMARK_TEST_SET = [
    {
        "id": "case_1_gym_trap",
        "input": "2026-10-01 ACH DEBIT PLANET FITNESS DALLAS TX $29.99/MO (In-person club visit required)",
        "expected_merchant": "Planet Fitness",
        "expected_amount": 29.99,
        "expected_cadence": "monthly",
        "expected_dark_pattern": True,
        "expected_pattern_type": "GYM_TRAP"
    },
    {
        "id": "case_2_equinox_certified_mail",
        "input": "2026-10-02 EQUINOX NEW YORK $280.00/MO (Certified mail cancellation only)",
        "expected_merchant": "Equinox",
        "expected_amount": 280.00,
        "expected_cadence": "monthly",
        "expected_dark_pattern": True,
        "expected_pattern_type": "GYM_TRAP"
    },
    {
        "id": "case_3_saas_trial_jump",
        "input": "2026-10-03 CLOUDSCALE AI PRO TRIAL CONVERTED $79.00/MO",
        "expected_merchant": "Cloudscale Ai",
        "expected_amount": 79.00,
        "expected_cadence": "monthly",
        "expected_dark_pattern": True,
        "expected_pattern_type": "SNEAKY_SAAS_TRIAL"
    },
    {
        "id": "case_4_ghost_micro_addon",
        "input": "2026-10-04 STREAMMAX 4K ULTRA STREAM ADDON $4.99/MO",
        "expected_merchant": "Streammax",
        "expected_amount": 4.99,
        "expected_cadence": "monthly",
        "expected_dark_pattern": True,
        "expected_pattern_type": "GHOST_MICRO_FEE"
    },
    {
        "id": "case_5_standard_subscription",
        "input": "2026-10-05 SPOTIFY PREMIUM $11.99/MO",
        "expected_merchant": "Spotify",
        "expected_amount": 11.99,
        "expected_cadence": "monthly",
        "expected_dark_pattern": False,
        "expected_pattern_type": "STANDARD_SUBSCRIPTION"
    },
    {
        "id": "case_6_annual_hosting",
        "input": "2026-10-06 DOMAIN HOSTING RENEWAL $99.00/YR",
        "expected_merchant": "Domain Hosting",
        "expected_amount": 99.00,
        "expected_cadence": "annual",
        "expected_dark_pattern": False,
        "expected_pattern_type": "STANDARD_SUBSCRIPTION"
    }
]


def verify_deterministic_guardrails(merchant: str, amount: float, dark_pattern_type: str) -> bool:
    """
    Actively synthesizes cancellation drafts and verifies that:
    1. Statutory citations (ROSCA or EFTA) are present.
    2. Exact amount is accurately preserved in drafts.
    3. No hallucinated civil penalty figures ($50,120) or unverified claims exist.
    """
    tiers_res = synthesize_cancellation_tiers(
        merchant=merchant,
        amount=amount,
        cadence="monthly",
        dark_pattern_type=dark_pattern_type,
        ftc_clause_id="15 U.S.C. § 8403",
        ftc_title="Simple Cancellation Mechanism Requirement",
        citation="ROSCA (15 U.S.C. § 8403)",
        session_id="benchmark-guardrail-audit"
    )
    t2 = tiers_res["tiers"]["tier_2_ftc_legal"]
    t3 = tiers_res["tiers"]["tier_3_chargeback"]

    # Statutory references must be present
    has_statutes = ("15 U.S.C. § 8403" in t2) and ("12 CFR § 1005.10" in t3)
    # Amount must match
    has_amount = f"{amount:.2f}" in t2
    # No unverified penalty claim
    clean_penalties = ("$50,120" not in t2) and ("$50,120" not in t3)

    return has_statutes and has_amount and clean_penalties


def evaluate_test_set(test_set: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Evaluates a test set against the deterministic regex parser and heuristic classifier.
    Explicitly tracks:
    - parsing failures (omissions or unexpected item counts)
    - merchant name matching
    - pattern type matching
    - confusion matrix (TP, FP, TN, FN)
    - active guardrail verification
    - local CPU parser latencies
    """
    cases = test_set if test_set is not None else BENCHMARK_TEST_SET
    start_time = time.perf_counter()
    
    total_cases = len(cases)
    parse_failures = 0
    extraction_matches = 0
    merchant_mismatches = 0
    pattern_type_mismatches = 0
    
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0
    latencies_ms: List[float] = []

    guardrail_checks_passed = 0
    guardrail_checks_total = 0

    for case in cases:
        t0 = time.perf_counter()
        audit_res = audit_statement(case.get("input", ""))
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

        # 1. Check item extraction count
        if audit_res["total_items"] != 1:
            parse_failures += 1
            if case.get("expected_dark_pattern", False):
                false_negatives += 1
            else:
                false_positives += 1
            continue

        item = audit_res["subscriptions"][0]

        # 2. Validate amount, cadence, and merchant
        amount_match = abs(item["amount"] - case.get("expected_amount", 0.0)) < 0.01
        cadence_match = (item["cadence"] == case.get("expected_cadence", ""))
        merchant_expected = case.get("expected_merchant", "").lower()
        merchant_match = merchant_expected in item["merchant"].lower()

        if not merchant_match:
            merchant_mismatches += 1

        if amount_match and cadence_match and merchant_match:
            extraction_matches += 1

        # 3. Validate classification & pattern type
        detected_dark = item["dark_pattern_detected"]
        expected_dark = case.get("expected_dark_pattern", False)
        pattern_expected = case.get("expected_pattern_type", "")
        pattern_match = (item["dark_pattern_type"] == pattern_expected)

        if not pattern_match:
            pattern_type_mismatches += 1

        if detected_dark and expected_dark:
            if pattern_match:
                true_positives += 1
            else:
                false_positives += 1
        elif detected_dark and not expected_dark:
            false_positives += 1
        elif not detected_dark and not expected_dark:
            true_negatives += 1
        elif not detected_dark and expected_dark:
            false_negatives += 1

        # 4. Active guardrail check for dark pattern cases
        if detected_dark:
            guardrail_checks_total += 1
            if verify_deterministic_guardrails(item["merchant"], item["amount"], item["dark_pattern_type"]):
                guardrail_checks_passed += 1

    total_time_ms = (time.perf_counter() - start_time) * 1000.0
    avg_latency_ms = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0

    precision = (true_positives / (true_positives + false_positives)) * 100.0 if (true_positives + false_positives) > 0 else 0.0
    recall = (true_positives / (true_positives + false_negatives)) * 100.0 if (true_positives + false_negatives) > 0 else 0.0
    extraction_accuracy = (extraction_matches / total_cases) * 100.0 if total_cases > 0 else 0.0

    guardrails_passed = (guardrail_checks_passed == guardrail_checks_total) if guardrail_checks_total > 0 else True

    return {
        "suite_name": "SubSloth Curated Regression Suite (6 Cases)",
        "scope_description": "Curated regression test set evaluating deterministic regex parsing and dark-pattern heuristics. Hand-authored patterns for CI sanity, not a representative population study.",
        "latency_scope": "Deterministic Layer 1 CPU regex execution only (excludes network, remote LLM call, and browser rendering).",
        "total_test_cases": total_cases,
        "parse_failures": parse_failures,
        "merchant_mismatches": merchant_mismatches,
        "pattern_type_mismatches": pattern_type_mismatches,
        "extraction_accuracy_pct": round(extraction_accuracy, 1),
        "classification_precision_pct": round(precision, 1),
        "classification_recall_pct": round(recall, 1),
        "true_positives": true_positives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "guardrail_verification": {
            "checks_evaluated": guardrail_checks_total,
            "checks_passed": guardrail_checks_passed,
            "all_passed": guardrails_passed
        },
        "deterministic_guardrail_pass": guardrails_passed,
        "avg_item_latency_ms": round(avg_latency_ms, 3),
        "total_suite_runtime_ms": round(total_time_ms, 2),
        "statutory_coverage": [
            "ROSCA (15 U.S.C. § 8403) - Simple Cancellation Mechanism Requirement",
            "FTC Act Section 5 (15 U.S.C. § 45) - Unfair or Deceptive Practices",
            "FTC Negative Option Framework (16 CFR Part 425) - Prenotification Disclosures",
            "CFPB Regulation E (12 CFR § 1005.10) - Preauthorized EFT Revocation Rights"
        ]
    }


def run_benchmark_evaluation() -> Dict[str, Any]:
    """Runs default 6-case regression benchmark."""
    return evaluate_test_set(BENCHMARK_TEST_SET)
