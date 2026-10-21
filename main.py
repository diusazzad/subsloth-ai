"""
SubSloth AI - FastAPI Backend & REST API
Automating subscription dark-pattern detection & legal cancellation under FTC Click-to-Cancel rules.
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
from core.backboard_client import synthesize_cancellation_tiers, memory_store


app = FastAPI(
    title="SubSloth AI - Subscription & Dark Pattern Legal Defense Engine",
    description="Automated subscription audit, FTC Click-to-Cancel enforcement, and Backboard Memory tracking.",
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


class EscalateRequest(BaseModel):
    merchant: str = Field(..., description="Merchant name")
    amount: float = Field(..., description="Recurring charge amount")
    cadence: str = Field("monthly", description="Recurrence frequency")
    dark_pattern_type: str = Field("STANDARD_SUBSCRIPTION", description="Detected dark pattern category")
    ftc_clause_id: str = Field("16 CFR Part 425 § 425.6", description="Legal regulatory clause ID")
    ftc_title: str = Field("Simple Cancellation Mechanism Mandate", description="FTC policy clause title")
    citation: str = Field(..., description="Full legal citation")
    user_name: Optional[str] = Field("Consumer", description="Consumer full name")
    account_id: Optional[str] = Field("SUB-88219", description="Subscription identifier or account number")


class ZombieSimulateRequest(BaseModel):
    merchant: str = Field(..., description="Previously cancelled merchant to simulate rebilling for")
    amount: float = Field(..., description="New unauthorized charge amount")


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
    """Returns application health and Backboard memory status."""
    return {
        "status": "healthy",
        "app": "SubSloth AI",
        "version": "1.0.0",
        "active_cancellations_tracked": len(memory_store.list_active_cancellations()),
        "supported_ftc_clauses": len(FTC_POLICY_CLAUSES),
        "runtime": "Render Python 3 ASGI",
        "llm_reasoner": "Google Gemma 2 via Backboard SDK"
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
            "target_clause": "16 CFR Part 425 § 425.6 (Click-to-Cancel)",
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
            "target_clause": "16 CFR Part 425 § 425.4 (Negative Option Disclosure)",
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
            "target_clause": "15 U.S.C. § 8403 (ROSCA)",
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
            "target_clause": "All Consumer Protection Clauses",
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
    Extracts recurring items, flags dark patterns, and verifies against Backboard memory.
    """
    if not payload.statement_text or len(payload.statement_text.strip()) == 0:
        raise HTTPException(status_code=400, detail="statement_text cannot be empty.")
    
    result = audit_statement(payload.statement_text)
    
    # Intercept against Backboard memory to check for Zombie Re-charges
    for item in result["subscriptions"]:
        zombie_record = memory_store.check_zombie_rebill(item["merchant"], item["amount"])
        if zombie_record:
            item["zombie_recharge_alert"] = True
            item["zombie_details"] = zombie_record
            item["reason"] = f"CRITICAL: Merchant was cancelled on {zombie_record['cancelled_at']} (Notice ID: {zombie_record['notice_id']}). Re-billing is unauthorized under EFTA Reg E!"
    
    return result


@app.post("/api/escalate")
def escalate_cancellation(payload: EscalateRequest):
    """
    Layer 2 & 3: Backboard Memory record and Google Gemma 2 3-Tier Legal Escalation.
    Generates:
    - Tier 1: Diplomatic Request
    - Tier 2: FTC Click-to-Cancel Legal Notice
    - Tier 3: Bank Chargeback & Card Issuer Affidavit
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
        account_id=payload.account_id or "SUB-88219"
    )
    return result


@app.get("/api/memory")
def get_memory_state():
    """
    Returns active cancellations tracked in Backboard memory.
    Fulfills Hacktoberfest Backboard track demonstration.
    """
    records = memory_store.list_active_cancellations()
    return {
        "status": "success",
        "total_active_cancellations": len(records),
        "records": records,
        "description": "Backboard persistent memory preventing merchant zombie rebills."
    }


@app.post("/api/simulate-zombie-rebill")
def simulate_zombie(payload: ZombieSimulateRequest):
    """
    Simulates a cancelled merchant charging the user again to demonstrate
    Backboard Memory intercepting the charge and triggering automatic Tier 3 Chargeback.
    """
    record = memory_store.check_zombie_rebill(payload.merchant, payload.amount)
    if not record:
        # Pre-record it first then trigger
        notice_id = f"SLOTH-PREV-{int(payload.amount)}"
        memory_store.record_cancellation(payload.merchant, payload.amount, notice_id, "GYM_TRAP")
        record = memory_store.check_zombie_rebill(payload.merchant, payload.amount)
    
    return {
        "zombie_violation_intercepted": True,
        "merchant": payload.merchant,
        "unauthorized_amount": payload.amount,
        "cancellation_notice_id": record["notice_id"],
        "recommended_escalation": "TIER_3_BANK_CHARGEBACK_MANDATORY",
        "legal_basis": "12 CFR § 1005.10(b) (CFPB Regulation E)",
        "memory_details": record
    }
