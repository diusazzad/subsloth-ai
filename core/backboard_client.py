"""
SubSloth AI - Cancellation Synthesis Engine & Session State Tracking
Layer 2 of SubSloth architecture.

Handles:
1. Google Gemma 2 natural-language cancellation drafting via Backboard completion endpoint.
2. Deterministic regulatory citation guardrails (ROSCA 15 U.S.C. § 8403, FTC Act Section 5, EFTA Reg E).
3. Session-scoped in-process lifecycle state tracking (DRAFT_GENERATED -> REQUEST_SUBMITTED -> CANCELLATION_CONFIRMED).
4. Reliable deterministic fallback when model endpoint is unavailable or returns invalid responses.
"""

import os
import json
import time
import re
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone


BACKBOARD_API_KEY = os.environ.get("BACKBOARD_API_KEY", "")
BACKBOARD_BASE_URL = os.environ.get("BACKBOARD_BASE_URL", "https://api.backboard.io/v1")
GEMMA_MODEL = os.environ.get("GEMMA_MODEL", "google/gemma-2-9b-it")


class CancellationStatus:
    DRAFT_GENERATED = "DRAFT_GENERATED"
    REQUEST_SUBMITTED = "REQUEST_SUBMITTED"
    CANCELLATION_CONFIRMED = "CANCELLATION_CONFIRMED"


class SessionCancellationStore:
    """
    In-process session-scoped prototype store for tracking cancellation lifecycle.
    Keeps cancellation records segregated by session to prevent cross-user contamination.
    """
    def __init__(self):
        # session_id -> { merchant_key -> record }
        self.sessions: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def _get_session(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        sid = session_id or "demo-session"
        if sid not in self.sessions:
            self.sessions[sid] = {}
        return self.sessions[sid]

    def record_draft(
        self,
        merchant: str,
        amount: float,
        notice_id: str,
        dark_pattern_type: str,
        session_id: str = "demo-session"
    ) -> Dict[str, Any]:
        """Records that a cancellation draft was prepared for user review."""
        session = self._get_session(session_id)
        key = merchant.strip().lower()
        record = {
            "merchant": merchant,
            "amount": amount,
            "notice_id": notice_id,
            "dark_pattern_type": dark_pattern_type,
            "status": CancellationStatus.DRAFT_GENERATED,
            "drafted_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "submitted_at": None,
            "confirmed_at": None,
            "zombie_alerts_count": 0
        }
        session[key] = record
        return record

    def mark_submitted(self, merchant: str, session_id: str = "demo-session") -> Optional[Dict[str, Any]]:
        """Transitions state: User confirms having sent the cancellation notice to merchant."""
        session = self._get_session(session_id)
        key = merchant.strip().lower()
        if key in session:
            record = session[key]
            record["status"] = CancellationStatus.REQUEST_SUBMITTED
            record["submitted_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            return record
        return None

    def confirm_cancellation(self, merchant: str, session_id: str = "demo-session") -> Optional[Dict[str, Any]]:
        """Transitions state: User confirms merchant acknowledged cancellation. Requires REQUEST_SUBMITTED status first."""
        session = self._get_session(session_id)
        key = merchant.strip().lower()
        if key in session:
            record = session[key]
            if record["status"] != CancellationStatus.REQUEST_SUBMITTED:
                raise ValueError("Cannot confirm cancellation before notice request has been marked submitted.")
            record["status"] = CancellationStatus.CANCELLATION_CONFIRMED
            record["confirmed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            return record
        return None

    def check_zombie_rebill(self, merchant: str, amount: float, session_id: str = "demo-session") -> Optional[Dict[str, Any]]:
        """
        Flags potential unauthorized recurring charge ONLY if the user previously
        submitted or confirmed cancellation for this merchant in this session.
        Draft-only records do NOT trigger zombie alerts.
        """
        session = self._get_session(session_id)
        key = merchant.strip().lower()
        if key in session:
            record = session[key]
            if record["status"] in [CancellationStatus.REQUEST_SUBMITTED, CancellationStatus.CANCELLATION_CONFIRMED]:
                record["zombie_alerts_count"] += 1
                record["last_detected_charge"] = {
                    "amount": amount,
                    "detected_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                }
                return record
        return None

    def list_cancellations(self, session_id: str = "demo-session") -> List[Dict[str, Any]]:
        """Returns all managed cancellation records for the given session."""
        session = self._get_session(session_id)
        return list(session.values())

    def record_cancellation(
        self,
        merchant: str,
        amount: float,
        notice_id: str,
        dark_pattern_type: str,
        session_id: str = "demo-session"
    ) -> Dict[str, Any]:
        """Convenience alias: records draft and transitions to submitted for testing."""
        self.record_draft(merchant, amount, notice_id, dark_pattern_type, session_id=session_id)
        return self.mark_submitted(merchant, session_id=session_id)

    def list_active_cancellations(self, session_id: str = "demo-session") -> List[Dict[str, Any]]:
        """Convenience alias for listing active cancellation records."""
        return self.list_cancellations(session_id=session_id)

    def clear(self, session_id: Optional[str] = None):
        """Clears records for a session, or all sessions if None."""
        if session_id:
            if session_id in self.sessions:
                self.sessions[session_id].clear()
        else:
            self.sessions.clear()


# Global in-process store singleton
memory_store = SessionCancellationStore()
BackboardMemoryStore = SessionCancellationStore


def _call_gemma_api(
    merchant: str,
    amount: float,
    cadence: str,
    dark_pattern_type: str,
    account_id: str,
    timeout_sec: float = 4.0
) -> Optional[Tuple[str, str]]:
    """
    Calls Google Gemma 2 endpoint to generate custom natural-language narrative sections.
    Returns (diplomatic_body, dispute_narrative) if successful, or None on failure.
    """
    if not BACKBOARD_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {BACKBOARD_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = (
        f"You are SubSloth AI, assisting a consumer with subscription cancellation drafting.\n"
        f"Merchant: {merchant}\n"
        f"Amount: ${amount:.2f} ({cadence})\n"
        f"Account Ref: {account_id}\n"
        f"Reported Friction / Dark Pattern: {dark_pattern_type}\n\n"
        f"Provide two concise text blocks in the following exact format:\n\n"
        f"[DIPLOMATIC_BODY]\n"
        f"(Write a polite, direct 2-3 sentence paragraph from the consumer requesting prompt subscription termination and written confirmation.)\n\n"
        f"[DISPUTE_NARRATIVE]\n"
        f"(Write a factual 2-3 sentence statement describing the cancellation difficulty or unexpected recurring billing to support a formal dispute draft.)"
    )

    payload = {
        "model": GEMMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a professional consumer protection writing assistant. Keep responses factual, direct, and free of fabricated legal citations."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }

    try:
        resp = requests.post(f"{BACKBOARD_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=timeout_sec)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            dip_match = re.search(r"\[DIPLOMATIC_BODY\]\s*(.*?)(?=\[DISPUTE_NARRATIVE\]|$)", content, re.DOTALL | re.IGNORECASE)
            narr_match = re.search(r"\[DISPUTE_NARRATIVE\]\s*(.*?)$", content, re.DOTALL | re.IGNORECASE)

            dip_text = dip_match.group(1).strip() if dip_match else ""
            narr_text = narr_match.group(1).strip() if narr_match else ""

            if dip_text and narr_text:
                return (dip_text, narr_text)
    except Exception:
        return None

    return None


def synthesize_cancellation_tiers(
    merchant: str,
    amount: float,
    cadence: str,
    dark_pattern_type: str,
    ftc_clause_id: str,
    ftc_title: str,
    citation: str,
    user_name: str = "Consumer",
    account_id: str = "SUB-88219",
    session_id: str = "demo-session"
) -> Dict[str, Any]:
    """
    Generates 3-Tier Escalation draft documents.
    If available, Google Gemma 2 synthesizes natural-language dispute statements.
    Deterministic Python logic enforces verified statutory citations and calculation integrity.
    If the remote model call is unavailable, deterministic fallback templates are used.
    """
    notice_id = f"SLOTH-{int(time.time())}"
    now_str = datetime.now(timezone.utc).strftime('%B %d, %Y')

    # Record draft generation event (Status = DRAFT_GENERATED)
    memory_store.record_draft(merchant, amount, notice_id, dark_pattern_type, session_id=session_id)

    # Attempt Gemma synthesis
    gemma_result = _call_gemma_api(merchant, amount, cadence, dark_pattern_type, account_id)

    if gemma_result:
        dip_body, narr_body = gemma_result
        engine_label = f"{GEMMA_MODEL} (hybrid-grounded)"
        gemma_contribution = {
            "diplomatic_body": dip_body,
            "dispute_narrative": narr_body
        }

        tier_1_diplomatic = (
            f"Subject: Subscription Cancellation Request - Account Ref: {account_id}\n\n"
            f"Dear {merchant} Customer Support,\n\n"
            f"{dip_body}\n\n"
            f"Subscription Details:\n"
            f"- Account / Identifier: {account_id}\n"
            f"- Billing Amount: ${amount:.2f}/{cadence}\n"
            f"- Consumer Name: {user_name}\n"
            f"- Date of Request: {now_str}\n\n"
            f"Please confirm receipt and effective termination date in writing."
        )

        tier_2_ftc_legal = (
            f"FORMAL NOTICE OF SUBSCRIPTION CANCELLATION & BILLING AUTHORIZATION REVOCATION\n"
            f"Drafted with SubSloth AI (Reference Notice ID: {notice_id})\n\n"
            f"To: {merchant} Customer Service & Billing Compliance Desk\n"
            f"Date: {now_str}\n"
            f"Account Identifier: {account_id}\n\n"
            f"CONSUMER NOTICE:\n"
            f"The undersigned consumer terminates all recurring authorizations of ${amount:.2f}/{cadence} for services provided by {merchant}.\n\n"
            f"FACTUAL STATEMENT OF DISPUTE:\n"
            f"{narr_body}\n\n"
            f"STATUTORY & REGULATORY REFERENCE STANDARDS:\n"
            f"1. Restore Online Shoppers' Confidence Act (ROSCA, 15 U.S.C. § 8403): Merchants must provide simple mechanisms to stop recurring charges.\n"
            f"2. FTC Act Section 5 (15 U.S.C. § 45): Prohibits unfair or deceptive practices, including unreasonable cancellation friction.\n"
            f"3. FTC Negative Option Framework (16 CFR Part 425): Clear disclosure of material terms before billing.\n\n"
            f"REQUESTED ACTION:\n"
            f"1. Immediately cease recurring debits for {account_id}.\n"
            f"2. Provide written confirmation of cancellation within two (2) business days.\n"
            f"3. Note that this record will be retained for potential consumer protection review if unauthorized charges persist."
        )

        tier_3_chargeback = (
            f"DRAFT CARDHOLDER DISPUTE STATEMENT & STOP-PAYMENT NOTIFICATION\n"
            f"Prepared for Consumer Review (EFTA / CFPB Regulation E, 12 CFR § 1005.10)\n\n"
            f"To: Card Issuer Dispute Department / Card Services Team\n"
            f"Date: {now_str}\n"
            f"Cardholder Name: {user_name}\n"
            f"Merchant in Dispute: {merchant}\n"
            f"Disputed Recurring Amount: ${amount:.2f} ({cadence})\n"
            f"Prior Written Cancellation Notice ID: {notice_id}\n\n"
            f"STATEMENT OF CIRCUMSTANCES:\n"
            f"{narr_body}\n\n"
            f"REGULATORY BASIS:\n"
            f"1. Pursuant to 12 CFR § 1005.10(b), cardholder has provided notice revoking recurring billing authorization.\n"
            f"2. Merchant was provided written cancellation notice (Ref: {notice_id}) and simple electronic cancellation was impeded.\n"
            f"3. Cardholder requests stop-payment on recurring debits originating from merchant descriptor: '{merchant}'.\n\n"
            f"REQUESTED ACTION: Place a merchant debit stop-block and review potential unauthorized transfers pursuant to Regulation E dispute procedures."
        )

    else:
        # Deterministic Fallback Engine (Runs when model API is unreachable or unconfigured)
        engine_label = "deterministic-fallback"
        gemma_contribution = None

        tier_1_diplomatic = (
            f"Subject: Immediate Cancellation Request - Account Ref: {account_id}\n\n"
            f"Dear {merchant} Billing Support,\n\n"
            f"Please accept this written notice to terminate my subscription for ${amount:.2f}/{cadence} effective today. "
            f"Please remove my payment card from recurring billing and send written confirmation of termination to this email.\n\n"
            f"Account / Identifier: {account_id}\n"
            f"Name: {user_name}\n"
            f"Date: {now_str}\n\n"
            f"Thank you for your prompt confirmation."
        )

        tier_2_ftc_legal = (
            f"FORMAL NOTICE OF SUBSCRIPTION CANCELLATION & BILLING AUTHORIZATION REVOCATION\n"
            f"Drafted with SubSloth AI (Reference Notice ID: {notice_id})\n\n"
            f"To: {merchant} Billing Compliance Desk\n"
            f"Date: {now_str}\n"
            f"Consumer Identifier: {account_id}\n\n"
            f"NOTICE IS HEREBY GIVEN that the undersigned consumer terminates all services and recurring debits of ${amount:.2f}/{cadence} with {merchant}.\n\n"
            f"REGULATORY REFERENCE STANDARDS:\n"
            f"1. Restore Online Shoppers' Confidence Act (ROSCA, 15 U.S.C. § 8403): Imposes simple mechanism requirement to stop recurring charges.\n"
            f"2. FTC Act Section 5 (15 U.S.C. § 45): Prohibits unfair or deceptive acts or practices in recurring subscription administration.\n"
            f"3. FTC Negative Option Framework (16 CFR Part 425): Requires conspicuous disclosure of terms and consent prior to billing.\n\n"
            f"REQUESTED ACTION: Immediately cease all recurring electronic debits. Provide written confirmation of termination within two (2) business days."
        )

        tier_3_chargeback = (
            f"DRAFT CARDHOLDER DISPUTE STATEMENT & STOP-PAYMENT NOTIFICATION\n"
            f"Prepared for Consumer Review (EFTA / CFPB Regulation E, 12 CFR § 1005.10)\n\n"
            f"To: Card Issuer Dispute Department / Card Services Resolution Team\n"
            f"Date: {now_str}\n"
            f"Cardholder: {user_name}\n"
            f"Merchant in Dispute: {merchant}\n"
            f"Disputed Recurring Amount: ${amount:.2f}\n"
            f"Prior Written Cancellation Notice ID: {notice_id}\n\n"
            f"STATEMENT OF FACTS:\n"
            f"1. Cardholder gave notice revoking recurring billing authorization pursuant to 12 CFR § 1005.10(b).\n"
            f"2. The merchant deployed documented retention friction ({dark_pattern_type}) and simple electronic cancellation was impeded.\n"
            f"3. Cardholder requests review of continued recurring charges under Regulation E error resolution rules.\n\n"
            f"REQUESTED ACTION: Place an active stop-payment block on merchant descriptor '{merchant}'."
        )

    return {
        "notice_id": notice_id,
        "merchant": merchant,
        "amount": amount,
        "cadence": cadence,
        "dark_pattern_type": dark_pattern_type,
        "ftc_clause_id": ftc_clause_id,
        "ftc_title": ftc_title,
        "synthesis_engine": engine_label,
        "gemma_contribution": gemma_contribution,
        "tiers": {
            "tier_1_diplomatic": tier_1_diplomatic,
            "tier_2_ftc_legal": tier_2_ftc_legal,
            "tier_3_chargeback": tier_3_chargeback
        },
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }
