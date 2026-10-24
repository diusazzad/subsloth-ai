"""
SubSloth AI - FastAPI Backend & REST API
Automating subscription dark-pattern detection & user-reviewed cancellation drafts.
Deployed on Render with native OpenAPI (/docs) integration.
"""

import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.ftc_rules import FTC_POLICY_CLAUSES
from core.subscription_detector import audit_statement
from core.backboard_client import (
    synthesize_cancellation_tiers,
    memory_store,
    CancellationStatus
)


app = FastAPI(
    title="SubSloth AI - Subscription Audit & Cancellation Drafting Engine",
    description="Automated subscription audit, deterministic regulatory citation, and Google Gemma 2 drafting.",
    version="1.0.0"
)

# CORS middleware for open interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Request Models
class AuditRequest(BaseModel):
    statement_text: str = Field(..., description="Raw statement text, credit card SMS dump, or CSV lines")
    session_id: Optional[str] = Field("demo-session", description="Session identifier for state scoping")


class EscalateRequest(BaseModel):
    merchant: str = Field(..., description="Merchant name")
    amount: float = Field(..., description="Recurring charge amount")
    cadence: str = Field("monthly", description="Recurrence frequency")
    dark_pattern_type: str = Field("STANDARD_SUBSCRIPTION", description="Detected dark pattern category")
    ftc_clause_id: str = Field("15 U.S.C. § 8403 / 16 CFR Part 425", description="Regulatory standard identifier")
    ftc_title: str = Field("Simple Cancellation Mechanism Requirement", description="Policy standard title")
    citation: str = Field(..., description="Full regulatory reference citation")
    user_name: Optional[str] = Field("Consumer", description="Consumer full name")
    account_id: Optional[str] = Field("SUB-88219", description="Subscription identifier or account number")
    session_id: Optional[str] = Field("demo-session", description="Session identifier for state scoping")


class ZombieSimulateRequest(BaseModel):
    merchant: str = Field(..., description="Previously cancelled merchant to simulate rebilling for")
    amount: float = Field(..., description="New recurring charge amount to test")
    session_id: Optional[str] = Field("demo-session", description="Session identifier")


class StatusUpdateRequest(BaseModel):
    merchant: str = Field(..., description="Merchant name to transition status for")
    session_id: Optional[str] = Field("demo-session", description="Session identifier")


# Static files mount
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_index():
    """Serves the interactive SubSloth UI Workbench."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "app": "SubSloth AI",
        "status": "Running",
        "docs_url": "/docs",
        "ui_workbench": "Static index.html not yet built"
    }


@app.get("/api/health")
def healthcheck():
    """Returns application health and session store status."""
    return {
        "status": "healthy",
        "app": "SubSloth AI",
        "version": "1.0.0",
        "active_cancellations_tracked": len(memory_store.list_cancellations()),
        "supported_ftc_clauses": len(FTC_POLICY_CLAUSES),
        "runtime": "Render Python 3 ASGI",
        "llm_reasoner": "Google Gemma 2"
    }


@app.get("/api/benchmarks")
def get_benchmarks():
    """
    Returns zero-click preset benchmarks for hackathon judges to test immediately.
    """
    return [
        {
            "id": "gym_trap",
            "title": "The Gym Trap (Planet Fitness)",
            "subtitle": "Burdensome In-Person / Certified Mail Friction",
            "expected_pattern": "GYM_TRAP",
            "target_clause": "15 U.S.C. § 8403 (ROSCA Simple Stopping Mechanism)",
            "statement_text": (
                "2026-10-01 ACH DEBIT PLANET FITNESS DALLAS TX $29.99/MO\n"
                "Note: In-person club visit or certified mail cancellation required.\n"
                "2026-10-01 PLANET FITNESS ANNUAL MAINTENANCE FEE $49.00"
            )
        },
        {
            "id": "sneaky_saas",
            "title": "The Sneaky SaaS (CloudScale AI)",
            "subtitle": "14-Day Free Trial Auto-Converted to $79/mo",
            "expected_pattern": "SNEAKY_SAAS_TRIAL",
            "target_clause": "16 CFR Part 425 / 15 U.S.C. § 45 (FTC Negative Option Framework)",
            "statement_text": (
                "2026-09-15 CLOUDSCALE AI PRO 14-DAY TRIAL $0.00\n"
                "2026-10-01 CLOUDSCALE AI PRO TRIAL CONVERTED $79.00/MO\n"
                "2026-10-01 CLOUDSCALE PRIORITY SUPPORT ADDON $19.99/MO"
            )
        },
        {
            "id": "ghost_micro_fee",
            "title": "The Hidden Ghost Fee (StreamMax 4K)",
            "subtitle": "Undisclosed Streaming Addons and Drip Pricing",
            "expected_pattern": "GHOST_MICRO_FEE",
            "target_clause": "15 U.S.C. § 8403 (ROSCA Material Terms Disclosure)",
            "statement_text": (
                "2026-10-05 STREAMMAX STANDARD STREAMING $14.99/MO\n"
                "2026-10-05 STREAMMAX 4K ULTRA STREAM ADDON $4.99/MO\n"
                "2026-10-05 STREAMMAX AD-FREE VIP BOOST $3.99/MO"
            )
        },
        {
            "id": "multi_subscription_chaos",
            "title": "The Complete Sloth Audit (Combined Dump)",
            "subtitle": "Audit Multiple Merchants with Real-World Lazy Payoff",
            "expected_pattern": "MULTIPLE_PATTERNS",
            "target_clause": "ROSCA & FTC Negative Option Reference Standards",
            "statement_text": (
                "2026-10-01 PLANET FITNESS DALLAS TX $29.99/mo (In-person cancel required)\n"
                "2026-10-02 CLOUDSCALE AI PRO TRIAL CONVERTED $79.00/mo\n"
                "2026-10-05 STREAMMAX 4K ULTRA STREAM ADDON $4.99/mo\n"
                "2026-10-10 SPOTIFY PREMIUM $11.99/mo\n"
                "2026-10-12 NY TIMES DIGITAL NEWS $4.00/mo"
            )
        }
    ]


@app.post("/api/audit")
def audit_subscriptions(payload: AuditRequest):
    """
    Layer 1: Deterministic regex and heuristic audit of bank statement text.
    Extracts recurring items, flags negative-option patterns, and checks session cancellation state.
    """
    if not payload.statement_text or len(payload.statement_text.strip()) == 0:
        raise HTTPException(status_code=400, detail="statement_text cannot be empty.")
    
    result = audit_statement(payload.statement_text)
    session_id = payload.session_id or "demo-session"
    
    # Intercept against session memory to check for potential recurring charges post-cancellation
    for item in result["subscriptions"]:
        zombie_record = memory_store.check_zombie_rebill(item["merchant"], item["amount"], session_id=session_id)
        if zombie_record:
            item["zombie_recharge_alert"] = True
            item["zombie_details"] = zombie_record
            item["reason"] = (
                f"RECURRING OUTFLOW ALERT: Merchant was previously recorded with status '{zombie_record['status']}' "
                f"(Notice Ref: {zombie_record['notice_id']}). Continued recurring charges warrant stop-payment and dispute review."
            )
    
    return result


@app.post("/api/escalate")
def escalate_cancellation(payload: EscalateRequest):
    """
    Layer 2 & 3: Session state recording and Google Gemma 2 3-Tier Escalation Drafting.
    Generates user-reviewed draft cancellation documents:
    - Tier 1: Diplomatic Request
    - Tier 2: Formal Regulatory Dispute Notice citing ROSCA / FTC Standards
    - Tier 3: Bank Cardholder Statement & Stop-Payment Draft (Regulation E)
    """
    result = synthesize_cancellation_tiers(
        merchant=payload.merchant,
        amount=payload.amount,
        cadence=payload.cadence,
        dark_pattern_type=payload.dark_pattern_type,
        ftc_clause_id=payload.ftc_clause_id,
        ftc_title=payload.ftc_title,
        citation=payload.citation,
        user_name=payload.user_name or "Consumer",
        account_id=payload.account_id or "SUB-88219",
        session_id=payload.session_id or "demo-session"
    )
    return result


@app.post("/api/cancellations/mark-submitted")
def mark_cancellation_submitted(payload: StatusUpdateRequest):
    """Transitions a cancellation draft to REQUEST_SUBMITTED status."""
    record = memory_store.mark_submitted(payload.merchant, session_id=payload.session_id or "demo-session")
    if not record:
        raise HTTPException(status_code=404, detail="No cancellation record found for this merchant.")
    return {"status": "success", "record": record}


@app.post("/api/cancellations/confirm")
def confirm_cancellation(payload: StatusUpdateRequest):
    """Transitions a cancellation draft to CANCELLATION_CONFIRMED status."""
    record = memory_store.confirm_cancellation(payload.merchant, session_id=payload.session_id or "demo-session")
    if not record:
        raise HTTPException(status_code=404, detail="No cancellation record found for this merchant.")
    return {"status": "success", "record": record}


@app.get("/api/memory")
def get_memory_state(session_id: Optional[str] = "demo-session"):
    """
    Returns session-scoped cancellation tracking records.
    """
    records = memory_store.list_cancellations(session_id=session_id or "demo-session")
    return {
        "status": "success",
        "total_active_cancellations": len(records),
        "records": records,
        "description": "Session-scoped prototype store tracking cancellation lifecycle states (DRAFT_GENERATED, REQUEST_SUBMITTED, CANCELLATION_CONFIRMED)."
    }


@app.post("/api/simulate-zombie-rebill")
def simulate_zombie(payload: ZombieSimulateRequest):
    """
    Simulates a merchant charging recurring fees after cancellation submission
    to demonstrate lifecycle detection and Tier 3 dispute escalation.
    """
    session_id = payload.session_id or "demo-session"
    record = memory_store.check_zombie_rebill(payload.merchant, payload.amount, session_id=session_id)
    if not record:
        notice_id = f"SLOTH-PREV-{int(payload.amount)}"
        memory_store.record_draft(payload.merchant, payload.amount, notice_id, "GYM_TRAP", session_id=session_id)
        memory_store.mark_submitted(payload.merchant, session_id=session_id)
        record = memory_store.check_zombie_rebill(payload.merchant, payload.amount, session_id=session_id)

    return {
        "zombie_violation_intercepted": True,
        "merchant": payload.merchant,
        "unauthorized_amount": payload.amount,
        "cancellation_notice_id": record["notice_id"],
        "status": record["status"],
        "recommended_escalation": "TIER_3_BANK_CHARGEBACK_REVIEW",
        "legal_basis": "12 CFR § 1005.10(b) (CFPB Regulation E Stop-Payment)",
        "memory_details": record
    }
