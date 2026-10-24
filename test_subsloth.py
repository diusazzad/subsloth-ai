"""
SubSloth AI - Complete Automated Test Suite
Covers:
1. Grounded Legal Policy Standards (ROSCA 15 U.S.C. § 8403, 16 CFR Part 425, CFPB 12 CFR § 1005.10)
2. Layer 1 Deterministic Parser & Dark Pattern Detection
3. Session-Scoped Cancellation Lifecycle (DRAFT_GENERATED -> REQUEST_SUBMITTED -> CANCELLATION_CONFIRMED)
4. Anti-Zombie Rebill Interception Guardrails (No false positives on draft-only state)
5. Google Gemma 2 Synthesis (Mocked Model Success & Deterministic Fallback)
6. FastAPI REST Endpoints & Zero-Click Benchmarks
"""

import pytest
from unittest.mock import patch
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
    SessionCancellationStore,
    BackboardMemoryStore,
    CancellationStatus,
    synthesize_cancellation_tiers,
    memory_store
)

client = TestClient(app)


# =====================================================================
# 1. Legal Regulatory Reference Grounding Tests
# =====================================================================
def test_ftc_policy_clauses_completeness():
    """Verifies active federal statutes and regulations are present."""
    assert "FTC_CLICK_TO_CANCEL" in FTC_POLICY_CLAUSES
    assert "FTC_NEGATIVE_OPTION_DISCLOSURE" in FTC_POLICY_CLAUSES
    assert "EFTA_REG_E_CHARGEBACK" in FTC_POLICY_CLAUSES
    assert "ROSCA_UNDISCLOSED_FEES" in FTC_POLICY_CLAUSES

    # Verify reliance on active statutes (ROSCA 15 U.S.C. § 8403 and FTC Negative Option)
    assert "15 U.S.C. § 8403" in FTC_POLICY_CLAUSES["FTC_CLICK_TO_CANCEL"]["clause_id"]
    assert "16 CFR Part 425" in FTC_POLICY_CLAUSES["FTC_NEGATIVE_OPTION_DISCLOSURE"]["clause_id"]
    assert "12 CFR § 1005.10" in FTC_POLICY_CLAUSES["EFTA_REG_E_CHARGEBACK"]["clause_id"]


def test_ftc_trigger_matching():
    """Tests keyword matching to regulatory clauses."""
    clause_gym = get_clause_by_trigger("Must cancel by in-person visit to gym")
    assert "8403" in clause_gym["clause_id"] or "425" in clause_gym["clause_id"]

    clause_trial = get_clause_by_trigger("Trial converted to full subscription")
    assert "16 CFR Part 425" in clause_trial["clause_id"]


def test_ftc_citation_formatting():
    """Ensures legal citation formatting includes authority and remedies without ungrounded penalty claims."""
    clause = FTC_POLICY_CLAUSES["FTC_CLICK_TO_CANCEL"]
    citation = format_legal_citation(clause)
    assert "Federal Trade Commission (FTC)" in citation
    assert "15 U.S.C. § 8403" in citation
    # Must NOT claim universal civil penalties
    assert "$50,120" not in citation


# =====================================================================
# 2. Layer 1 Parser & Extraction Tests
# =====================================================================
def test_extract_amount_standard():
    assert extract_amount("PLANET FITNESS $29.99/MO") == 29.99
    assert extract_amount("CLOUDSCALE AI $79.00/MO") == 79.00
    assert extract_amount("STREAMMAX $4.99") == 4.99


def test_extract_amount_edge_cases():
    assert extract_amount("NETFLIX COM RECURRING 19.99") == 19.99
    assert extract_amount("NO MONETARY VALUE HERE") == 0.0
    assert extract_amount("$0.00 FREE PROMO") == 0.0


def test_detect_cadence_patterns():
    cadence_m, mult_m = detect_cadence("PLANET FITNESS $29.99/mo")
    assert cadence_m == "monthly"
    assert mult_m == 12

    cadence_y, mult_y = detect_cadence("DOMAIN HOSTING $99.00/yr")
    assert cadence_y == "annual"
    assert mult_y == 1


def test_identify_merchant_cleaning():
    merchant = identify_merchant("2026-10-01 POS DEBIT PLANET FITNESS DALLAS TX $29.99")
    assert "Planet Fitness" in merchant


# =====================================================================
# 3. Dark Pattern Detection Heuristics Tests
# =====================================================================
def test_classify_gym_trap():
    is_dark, p_type, clause, reason = classify_dark_pattern(
        "PLANET FITNESS DALLAS TX $29.99 (In-person club visit required)",
        "Planet Fitness",
        29.99
    )
    assert is_dark is True
    assert p_type == "GYM_TRAP"
    assert "8403" in clause["clause_id"] or "425" in clause["clause_id"]


def test_classify_sneaky_saas_trial():
    is_dark, p_type, clause, reason = classify_dark_pattern(
        "CLOUDSCALE AI PRO TRIAL CONVERTED $79.00/MO",
        "CloudScale AI",
        79.00
    )
    assert is_dark is True
    assert p_type == "SNEAKY_SAAS_TRIAL"
    assert "16 CFR Part 425" in clause["clause_id"]


def test_classify_ghost_micro_fee():
    is_dark, p_type, clause, reason = classify_dark_pattern(
        "STREAMMAX 4K ULTRA STREAM ADDON $4.99/MO",
        "StreamMax",
        4.99
    )
    assert is_dark is True
    assert p_type == "GHOST_MICRO_FEE"
    assert "8403" in clause["clause_id"]


def test_classify_standard_subscription():
    is_dark, p_type, clause, reason = classify_dark_pattern(
        "SPOTIFY PREMIUM $11.99/MO",
        "Spotify",
        11.99
    )
    assert is_dark is False
    assert p_type == "STANDARD_SUBSCRIPTION"
    assert "1005.10" in clause["clause_id"]


# =====================================================================
# 4. Audit Statement Aggregate Calculation Tests
# =====================================================================
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


# =====================================================================
# 5. Cancellation Lifecycle & Session-Scoped Isolation Tests
# =====================================================================
def test_cancellation_store_lifecycle_transitions():
    store = SessionCancellationStore()
    sess_id = "test-session-1"

    # Step 1: Draft generated
    draft = store.record_draft("Crunch Fitness", 39.99, "SLOTH-101", "GYM_TRAP", session_id=sess_id)
    assert draft["status"] == CancellationStatus.DRAFT_GENERATED
    assert draft["submitted_at"] is None

    # Draft alone must NOT trigger zombie rebill
    zombie_premature = store.check_zombie_rebill("Crunch Fitness", 39.99, session_id=sess_id)
    assert zombie_premature is None, "Draft-only record must not trigger unauthorized rebill alert"

    # Step 2: Mark Request Submitted
    submitted = store.mark_submitted("Crunch Fitness", session_id=sess_id)
    assert submitted is not None
    assert submitted["status"] == CancellationStatus.REQUEST_SUBMITTED
    assert submitted["submitted_at"] is not None

    # Now zombie rebill DOES trigger
    zombie = store.check_zombie_rebill("Crunch Fitness", 39.99, session_id=sess_id)
    assert zombie is not None
    assert zombie["zombie_alerts_count"] == 1
    assert zombie["last_detected_charge"]["amount"] == 39.99

    # Step 3: Confirm Cancellation
    confirmed = store.confirm_cancellation("Crunch Fitness", session_id=sess_id)
    assert confirmed["status"] == CancellationStatus.CANCELLATION_CONFIRMED
    assert confirmed["confirmed_at"] is not None


def test_session_scoped_isolation():
    store = SessionCancellationStore()
    store.record_draft("Equinox", 280.00, "SLOTH-EQ-1", "GYM_TRAP", session_id="user_alice")
    store.mark_submitted("Equinox", session_id="user_alice")

    # Bob's session must be completely clean and isolated
    bob_records = store.list_cancellations(session_id="user_bob")
    assert len(bob_records) == 0

    # Bob auditing Equinox must NOT trigger a false positive zombie alert
    bob_zombie = store.check_zombie_rebill("Equinox", 280.00, session_id="user_bob")
    assert bob_zombie is None


# =====================================================================
# 6. Gemma Integration: Model Output Usage & Deterministic Fallback Tests
# =====================================================================
@patch("core.backboard_client._call_gemma_api")
def test_gemma_model_response_meaningfully_used(mock_gemma):
    """
    Verifies that when Gemma returns natural-language sections,
    they are meaningfully embedded into Tier 1 and Tier 2/3 documents.
    """
    mock_gemma.return_value = (
        "I am writing to formally request immediate cancellation of my monthly membership without retention delays.",
        "The consumer attempted to terminate online but was redirected to an in-person club visit requirement."
    )

    res = synthesize_cancellation_tiers(
        merchant="Planet Fitness",
        amount=29.99,
        cadence="monthly",
        dark_pattern_type="GYM_TRAP",
        ftc_clause_id="15 U.S.C. § 8403",
        ftc_title="Simple Cancellation Mechanism Requirement",
        citation="Enforced by FTC",
        session_id="test-gemma-session"
    )

    # 1. Check synthesis engine label
    assert "gemma-2-9b-it" in res["synthesis_engine"]
    assert res["gemma_contribution"] is not None

    # 2. Check Tier 1 contains Gemma's custom diplomatic paragraph
    assert "without retention delays" in res["tiers"]["tier_1_diplomatic"]

    # 3. Check Tier 2 and Tier 3 contain Gemma's custom factual narrative
    assert "redirected to an in-person club visit" in res["tiers"]["tier_2_ftc_legal"]
    assert "redirected to an in-person club visit" in res["tiers"]["tier_3_chargeback"]

    # 4. Check that statutory citations remain deterministic and unhallucinated
    assert "15 U.S.C. § 8403" in res["tiers"]["tier_2_ftc_legal"]
    assert "12 CFR § 1005.10" in res["tiers"]["tier_3_chargeback"]


@patch("core.backboard_client._call_gemma_api")
def test_gemma_deterministic_fallback_on_api_failure(mock_gemma):
    """
    Verifies that when Gemma is unreachable or unconfigured,
    the deterministic fallback engine produces clean, compliant drafts.
    """
    mock_gemma.return_value = None  # Simulate network timeout or missing API key

    res = synthesize_cancellation_tiers(
        merchant="Planet Fitness",
        amount=29.99,
        cadence="monthly",
        dark_pattern_type="GYM_TRAP",
        ftc_clause_id="15 U.S.C. § 8403",
        ftc_title="Simple Cancellation Mechanism Requirement",
        citation="Enforced by FTC",
        session_id="test-fallback-session"
    )

    assert res["synthesis_engine"] == "deterministic-fallback"
    assert res["gemma_contribution"] is None
    assert "tier_1_diplomatic" in res["tiers"]
    assert "tier_2_ftc_legal" in res["tiers"]
    assert "tier_3_chargeback" in res["tiers"]
    assert "ROSCA, 15 U.S.C. § 8403" in res["tiers"]["tier_2_ftc_legal"]


# =====================================================================
# 7. FastAPI REST Endpoints & Contracts Tests
# =====================================================================
def test_fastapi_endpoints_health_and_benchmarks():
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    data_health = resp_health.json()
    assert data_health["status"] == "healthy"
    assert "llm_reasoner" in data_health

    resp_benchmarks = client.get("/api/benchmarks")
    assert resp_benchmarks.status_code == 200
    benchmarks = resp_benchmarks.json()
    assert len(benchmarks) >= 3
    assert any(b["id"] == "gym_trap" for b in benchmarks)


def test_fastapi_audit_and_escalate_pipeline():
    # POST /api/audit
    payload_audit = {"statement_text": "2026-10-01 PLANET FITNESS $29.99/mo (in-person required)"}
    resp_audit = client.post("/api/audit", json=payload_audit)
    assert resp_audit.status_code == 200
    data_audit = resp_audit.json()
    assert data_audit["total_items"] == 1
    assert data_audit["dark_patterns_count"] == 1

    # POST /api/escalate
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


def test_fastapi_cancellation_lifecycle_endpoints():
    test_session = "api-lifecycle-test"
    memory_store.clear(session_id=test_session)

    # 1. Escalate (creates DRAFT_GENERATED)
    payload_esc = {
        "merchant": "Anytime Fitness",
        "amount": 49.99,
        "cadence": "monthly",
        "dark_pattern_type": "GYM_TRAP",
        "ftc_clause_id": "15 U.S.C. § 8403",
        "ftc_title": "Simple Cancellation Mechanism Requirement",
        "citation": "ROSCA",
        "session_id": test_session
    }
    resp_esc = client.post("/api/escalate", json=payload_esc)
    assert resp_esc.status_code == 200

    # 2. Check memory - status should be DRAFT_GENERATED
    resp_mem = client.get(f"/api/memory?session_id={test_session}")
    assert resp_mem.status_code == 200
    records = resp_mem.json()["records"]
    assert len(records) == 1
    assert records[0]["status"] == CancellationStatus.DRAFT_GENERATED

    # 3. Transition to REQUEST_SUBMITTED
    resp_sub = client.post("/api/cancellations/mark-submitted", json={
        "merchant": "Anytime Fitness",
        "session_id": test_session
    })
    assert resp_sub.status_code == 200
    assert resp_sub.json()["record"]["status"] == CancellationStatus.REQUEST_SUBMITTED

    # 4. Transition to CANCELLATION_CONFIRMED
    resp_conf = client.post("/api/cancellations/confirm", json={
        "merchant": "Anytime Fitness",
        "session_id": test_session
    })
    assert resp_conf.status_code == 200
    assert resp_conf.json()["record"]["status"] == CancellationStatus.CANCELLATION_CONFIRMED
