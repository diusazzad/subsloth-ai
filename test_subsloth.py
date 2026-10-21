"""
SubSloth AI - 20/20 Automated Test Suite
Covers Layer 1 Deterministic Engine, FTC Policy Matching,
Backboard Memory Session & Zombie Interception, and FastAPI REST Endpoints.
"""

import sys
import pytest
from fastapi.testclient import TestClient

from main import app
from core.ftc_rules import (
    FTC_POLICY_CLAUSES,
    get_clause_by_trigger,
    format_legal_citation
)
from core.subscription_detector import (
    extract_amount,
    detect_cadence,
    identify_merchant,
    classify_dark_pattern,
    audit_statement
)
from core.backboard_client import (
    BackboardMemoryStore,
    synthesize_cancellation_tiers
)

client = TestClient(app)


# 1. FTC Rules Tests
def test_ftc_policy_clauses_completeness():
    assert "FTC_CLICK_TO_CANCEL" in FTC_POLICY_CLAUSES
    assert "FTC_NEGATIVE_OPTION_DISCLOSURE" in FTC_POLICY_CLAUSES
    assert "EFTA_REG_E_CHARGEBACK" in FTC_POLICY_CLAUSES
    assert "ROSCA_UNDISCLOSED_FEES" in FTC_POLICY_CLAUSES
    assert "50,120" in FTC_POLICY_CLAUSES["FTC_CLICK_TO_CANCEL"]["penalty"]


def test_ftc_trigger_matching():
    clause = get_clause_by_trigger("Must cancel by in-person visit to gym")
    assert clause["clause_id"] == "16 CFR Part 425 § 425.6"

    clause_trial = get_clause_by_trigger("Trial converted to full subscription")
    assert clause_trial["clause_id"] == "16 CFR Part 425 § 425.4"


def test_ftc_citation_formatting():
    clause = FTC_POLICY_CLAUSES["FTC_CLICK_TO_CANCEL"]
    citation = format_legal_citation(clause)
    assert "16 CFR Part 425 § 425.6" in citation
    assert "Federal Trade Commission (FTC)" in citation
    assert "$50,120" in citation


# 2. Layer 1 Parser & Extraction Tests
def test_extract_amount_standard():
    assert extract_amount("PLANET FITNESS $29.99/MO") == 29.99
    assert extract_amount("CLOUDSCALE AI $79.00/MO") == 79.00
    assert extract_amount("STREAMMAX $4.99") == 4.99


def test_extract_amount_no_dollar_sign():
    assert extract_amount("NETFLIX COM RECURRING 19.99") == 19.99
    assert extract_amount("NO MONETARY VALUE HERE") == 0.0


def test_detect_cadence_monthly():
    cadence, mult = detect_cadence("PLANET FITNESS $29.99/mo")
    assert cadence == "monthly"
    assert mult == 12


def test_detect_cadence_annual():
    cadence, mult = detect_cadence("DOMAIN HOSTING $99.00/yr")
    assert cadence == "annual"
    assert mult == 1


def test_identify_merchant_cleaning():
    merchant = identify_merchant("2026-10-01 POS DEBIT PLANET FITNESS DALLAS TX $29.99")
    assert "Planet Fitness" in merchant


# 3. Dark Pattern Detection Heuristics Tests
def test_classify_gym_trap_planet_fitness():
    is_dark, p_type, clause, reason = classify_dark_pattern(
        "PLANET FITNESS DALLAS TX $29.99 (In-person club visit required)",
        "Planet Fitness",
        29.99
    )
    assert is_dark is True
    assert p_type == "GYM_TRAP"
    assert "425.6" in clause["clause_id"]


def test_classify_gym_trap_equinox_certified_mail():
    is_dark, p_type, clause, reason = classify_dark_pattern(
        "EQUINOX NEW YORK $280.00 (Certified mail cancellation only)",
        "Equinox",
        280.00
    )
    assert is_dark is True
    assert p_type == "GYM_TRAP"


def test_classify_sneaky_saas_trial_conversion():
    is_dark, p_type, clause, reason = classify_dark_pattern(
        "CLOUDSCALE AI PRO TRIAL CONVERTED $79.00/MO",
        "CloudScale AI",
        79.00
    )
    assert is_dark is True
    assert p_type == "SNEAKY_SAAS_TRIAL"
    assert "425.4" in clause["clause_id"]


def test_classify_ghost_micro_fee_addon():
    is_dark, p_type, clause, reason = classify_dark_pattern(
        "STREAMMAX 4K ULTRA STREAM ADDON $4.99/MO",
        "StreamMax",
        4.99
    )
    assert is_dark is True
    assert p_type == "GHOST_MICRO_FEE"
    assert "8403" in clause["clause_id"]


def test_classify_standard_subscription_spotify():
    is_dark, p_type, clause, reason = classify_dark_pattern(
        "SPOTIFY PREMIUM $11.99/MO",
        "Spotify",
        11.99
    )
    assert is_dark is False
    assert p_type == "STANDARD_SUBSCRIPTION"
    assert "1005.10" in clause["clause_id"]


# 4. Audit Statement Aggregate Calculation Tests
def test_audit_statement_empty_input():
    res = audit_statement("")
    assert res["total_items"] == 0
    assert res["total_annual_drain"] == 0.0


def test_audit_statement_multi_item_calculation():
    sample = (
        "2026-10-01 PLANET FITNESS DALLAS TX $29.99/MO (in-person cancel required)\n"
        "2026-10-02 CLOUDSCALE AI PRO TRIAL CONVERTED $79.00/MO\n"
        "2026-10-05 STREAMMAX 4K ULTRA STREAM ADDON $4.99/MO\n"
        "2026-10-10 SPOTIFY PREMIUM $11.99/MO"
    )
    res = audit_statement(sample)
    assert res["total_items"] == 4
    assert res["dark_patterns_count"] == 3
    assert res["total_monthly_drain"] == 125.97
    assert res["total_annual_drain"] == 1511.64
    assert res["lazy_payoff"]["hours_saved"] == 3.0


# 5. Backboard Memory & Zombie Interception Tests
def test_backboard_memory_record_cancellation():
    store = BackboardMemoryStore()
    record = store.record_cancellation("Crunch Fitness", 39.99, "SLOTH-101", "GYM_TRAP")
    assert record["merchant"] == "Crunch Fitness"
    assert record["notice_id"] == "SLOTH-101"
    assert len(store.list_active_cancellations()) == 1


def test_backboard_memory_zombie_rebill_interception():
    store = BackboardMemoryStore()
    store.record_cancellation("Gold's Gym", 45.00, "SLOTH-202", "GYM_TRAP")
    
    # Intercept next month charge
    zombie = store.check_zombie_rebill("Gold's Gym", 45.00)
    assert zombie is not None
    assert zombie["zombie_alerts_count"] == 1
    assert zombie["last_detected_charge"]["amount"] == 45.00


def test_synthesize_cancellation_tiers_structure():
    res = synthesize_cancellation_tiers(
        merchant="Planet Fitness",
        amount=29.99,
        cadence="monthly",
        dark_pattern_type="GYM_TRAP",
        ftc_clause_id="16 CFR Part 425 § 425.6",
        ftc_title="Simple Cancellation Mechanism Mandate",
        citation="Enforced by FTC"
    )
    assert "tiers" in res
    assert "tier_1_diplomatic" in res["tiers"]
    assert "tier_2_ftc_legal" in res["tiers"]
    assert "tier_3_chargeback" in res["tiers"]
    assert "Click-to-Cancel" in res["tiers"]["tier_2_ftc_legal"]
    assert "Regulation E" in res["tiers"]["tier_3_chargeback"]


# 6. FastAPI REST Endpoints Contract Tests
def test_fastapi_endpoints_health_and_benchmarks():
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "healthy"

    resp_benchmarks = client.get("/api/benchmarks")
    assert resp_benchmarks.status_code == 200
    benchmarks = resp_benchmarks.json()
    assert len(benchmarks) >= 3
    assert any(b["id"] == "gym_trap" for b in benchmarks)


def test_fastapi_endpoints_audit_and_escalate():
    # Test POST /api/audit
    payload_audit = {"statement_text": "2026-10-01 PLANET FITNESS $29.99/mo (in-person required)"}
    resp_audit = client.post("/api/audit", json=payload_audit)
    assert resp_audit.status_code == 200
    data_audit = resp_audit.json()
    assert data_audit["total_items"] == 1
    assert data_audit["dark_patterns_count"] == 1

    # Test POST /api/escalate
    sub_item = data_audit["subscriptions"][0]
    payload_esc = {
        "merchant": sub_item["merchant"],
        "amount": sub_item["amount"],
        "cadence": sub_item["cadence"],
        "dark_pattern_type": sub_item["dark_pattern_type"],
        "ftc_clause_id": sub_item["ftc_clause_id"],
        "ftc_title": sub_item["ftc_title"],
        "citation": sub_item["citation"]
    }
    resp_esc = client.post("/api/escalate", json=payload_esc)
    assert resp_esc.status_code == 200
    data_esc = resp_esc.json()
    assert "tiers" in data_esc
    assert len(data_esc["tiers"]["tier_2_ftc_legal"]) > 100
