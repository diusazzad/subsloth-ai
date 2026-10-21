"""
SubSloth AI - Legal Policy Knowledge Base
Grounding consumer subscription cancellation in Federal Trade Commission (FTC) mandates,
Electronic Fund Transfer Act (EFTA), and Restore Online Shoppers' Confidence Act (ROSCA).
"""

from typing import Dict, Any

FTC_POLICY_CLAUSES: Dict[str, Dict[str, Any]] = {
    "FTC_CLICK_TO_CANCEL": {
        "clause_id": "16 CFR Part 425 § 425.6",
        "title": "Simple Cancellation Mechanism Mandate (Click-to-Cancel)",
        "authority": "Federal Trade Commission (FTC)",
        "effective_date": "October 2026",
        "statutory_violation": "Failure to provide a cancellation method as easy as the enrollment method",
        "penalty": "Civil penalties up to $50,120 per violation under 15 U.S.C. § 45(m)(1)(A)",
        "summary": "Sellers must provide a cancellation mechanism at least as easy to use as initiation. Forcing consumers who enrolled online to call support or submit physical mail violates federal regulations.",
        "dark_pattern_triggers": [
            "phone call required",
            "call customer support",
            "certified mail",
            "in-person cancellation",
            "visit your home gym",
            "no online cancel button",
            "speak with retention",
            "hidden cancel button",
            "multi-step cancellation maze"
        ]
    },
    "FTC_NEGATIVE_OPTION_DISCLOSURE": {
        "clause_id": "16 CFR Part 425 § 425.4",
        "title": "Clear & Conspicuous Negative Option Disclosure",
        "authority": "Federal Trade Commission (FTC)",
        "effective_date": "October 2026",
        "statutory_violation": "Stealth conversion from free trial to paid recurring billing without explicit affirmative consent",
        "penalty": "Civil penalties up to $50,120 per violation + consumer restitution",
        "summary": "Merchants must disclose all material terms prior to obtaining billing details and receive unambiguous affirmative consent before auto-converting trials into recurring charges.",
        "dark_pattern_triggers": [
            "free trial auto-renew",
            "trial ended",
            "trial converted",
            "stealth subscription",
            "did not authorize recurring",
            "price increased without notice",
            "price hike",
            "auto-enroll",
            "unauthorized renewal"
        ]
    },
    "EFTA_REG_E_CHARGEBACK": {
        "clause_id": "12 CFR § 1005.10(b) (Regulation E)",
        "title": "Revocation of Preauthorized Electronic Fund Transfers",
        "authority": "Consumer Financial Protection Bureau (CFPB) & Federal Reserve",
        "effective_date": "Codified Regulation",
        "statutory_violation": "Debiting consumer accounts after notice of revocation",
        "penalty": "Mandatory financial institution chargeback reversal and merchant debit blocking",
        "summary": "Consumers may revoke authorization for recurring automated debits by giving oral or written notice at any time up to three business days before the scheduled transfer. Refusal mandates immediate bank chargeback.",
        "dark_pattern_triggers": [
            "stop payment request",
            "unauthorized debit",
            "refused to cancel",
            "chargeback",
            "merchant refusing refund",
            "ghost charge",
            "continued billing after cancellation"
        ]
    },
    "ROSCA_UNDISCLOSED_FEES": {
        "clause_id": "15 U.S.C. § 8403",
        "title": "Restore Online Shoppers' Confidence Act (ROSCA)",
        "authority": "Federal Trade Commission (FTC)",
        "effective_date": "Federal Statute",
        "statutory_violation": "Imposing undisclosed recurring maintenance or membership addon fees",
        "penalty": "FTC enforcement action and disgorgement of illicit fees",
        "summary": "Prohibits charging consumers for goods or services sold on the internet through negative option marketing without clear disclosures and simple stopping mechanisms.",
        "dark_pattern_triggers": [
            "annual fee",
            "maintenance fee",
            "facility fee",
            "addon fee",
            "convenience fee",
            "undisclosed charge"
        ]
    }
}


def get_clause_by_trigger(trigger_phrase: str) -> Dict[str, Any]:
    """Matches a dark pattern trigger phrase against the FTC policy database."""
    trigger_lower = trigger_phrase.lower().strip()
    for key, data in FTC_POLICY_CLAUSES.items():
        for trigger in data["dark_pattern_triggers"]:
            if trigger in trigger_lower:
                return data
    return FTC_POLICY_CLAUSES["FTC_CLICK_TO_CANCEL"]


def format_legal_citation(clause: Dict[str, Any]) -> str:
    """Formats a formal legal citation block for dispute notices."""
    return (
        f"Pursuant to {clause['title']} ({clause['clause_id']}), enforced by the {clause['authority']}. "
        f"Statutory provision: {clause['summary']} (Civil penalty: {clause['penalty']})."
    )
