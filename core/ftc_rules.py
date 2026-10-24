"""
SubSloth AI - Legal Regulatory Reference Framework
Grounding consumer subscription cancellation in active Federal Trade Commission (FTC) standards,
Restore Online Shoppers' Confidence Act (ROSCA, 15 U.S.C. § 8403), Section 5 of the FTC Act
(15 U.S.C. § 45), and Electronic Fund Transfer Act / CFPB Regulation E (12 CFR § 1005.10).
"""

from typing import Dict, Any

FTC_POLICY_CLAUSES: Dict[str, Dict[str, Any]] = {
    "FTC_CLICK_TO_CANCEL": {
        "clause_id": "15 U.S.C. § 8403 / 16 CFR Part 425",
        "title": "Simple Cancellation Mechanism Requirement (ROSCA & FTC Negative Option Framework)",
        "authority": "Federal Trade Commission (FTC)",
        "effective_date": "Active Federal Law",
        "statutory_violation": "Imposing unreasonable cancellation friction or failing to provide simple stopping mechanisms for recurring billing",
        "penalty": "FTC enforcement action, consumer restitution, and injunctive relief under 15 U.S.C. § 45",
        "summary": "Under ROSCA and FTC Negative Option principles, merchants utilizing recurring billing must provide simple, accessible mechanisms for consumers to stop recurring charges without artificial barriers or deceptive retention mazes.",
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
        "clause_id": "16 CFR Part 425 / 15 U.S.C. § 45",
        "title": "Pre-Consent Disclosure Requirement (FTC Negative Option Framework)",
        "authority": "Federal Trade Commission (FTC)",
        "effective_date": "Active Federal Law",
        "statutory_violation": "Auto-converting trial or promotional billing to recurring charges without clear pre-consent disclosure",
        "penalty": "Consumer restitution and regulatory enforcement under Section 5 of the FTC Act",
        "summary": "Merchants must clearly and conspicuously disclose material terms prior to obtaining billing information and obtain express informed consent before converting trials into recurring charges.",
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
        "authority": "Consumer Financial Protection Bureau (CFPB)",
        "effective_date": "Codified Regulation",
        "statutory_violation": "Debiting consumer accounts after written notice of authorization revocation",
        "penalty": "Bank dispute investigation, stop-payment rights, and unauthorized transfer dispute procedures",
        "summary": "Consumers may revoke authorization for recurring automated debits by giving notice to the merchant or financial institution, providing grounds for bank dispute investigation if recurring debits continue.",
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
        "statutory_violation": "Charging recurring fees without clear disclosure of all recurring material terms",
        "penalty": "FTC civil enforcement and restitution under Section 5",
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
    """Formats a formal regulatory citation block for dispute drafts."""
    return (
        f"Pursuant to {clause['title']} ({clause['clause_id']}), overseen by the {clause['authority']}. "
        f"Regulatory standard: {clause['summary']} (Remedy framework: {clause['penalty']})."
    )

