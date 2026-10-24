"""
SubSloth AI - Legal Regulatory Reference Framework
Grounding consumer subscription cancellation in active, undisputed federal statutory standards:
1. Restore Online Shoppers' Confidence Act (ROSCA, 15 U.S.C. § 8403): Simple mechanism to stop recurring charges.
2. FTC Act Section 5 (15 U.S.C. § 45): Unfair or deceptive acts or practices.
3. 16 CFR Part 425: Rule concerning prenotification negative-option plans & FTC negative option principles.
4. Electronic Fund Transfer Act / CFPB Regulation E (12 CFR § 1005.10): Preauthorized electronic debit revocation.
"""

from typing import Dict, Any

FTC_POLICY_CLAUSES: Dict[str, Dict[str, Any]] = {
    "FTC_CLICK_TO_CANCEL": {
        "clause_id": "15 U.S.C. § 8403",
        "title": "Simple Cancellation Mechanism Requirement (ROSCA)",
        "authority": "Federal Trade Commission (FTC)",
        "effective_date": "Active Federal Statute",
        "legal_scope": (
            "Applies to internet transactions involving recurring negative options; "
            "requires clear disclosure of material terms, express informed consent, "
            "and a simple mechanism to stop recurring charges without artificial barriers."
        ),
        "review_finding": "Potential non-compliance with ROSCA simple stopping mechanism requirement due to retention friction.",
        "statutory_violation": "Potential non-compliance with ROSCA simple stopping mechanism requirement due to retention friction.",
        "remedies": "FTC enforcement action, consumer restitution, and injunctive relief under FTC Act Section 5",
        "summary": "Under ROSCA (15 U.S.C. § 8403), merchants utilizing online recurring billing must provide simple, accessible mechanisms to stop recurring charges.",
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
        "clause_id": "15 U.S.C. § 45 / 16 CFR Part 425",
        "title": "Negative Option Disclosure Standards (FTC Act Section 5)",
        "authority": "Federal Trade Commission (FTC)",
        "effective_date": "Federal Statute & Codified Rule",
        "legal_scope": (
            "FTC Act Section 5 prohibits unfair or deceptive practices; 16 CFR Part 425 "
            "covers prenotification negative-option plans with ongoing rulemaking regarding broad negative-option disclosures."
        ),
        "review_finding": "Trial-to-paid auto-conversion or recurring renewal flagged for review under Section 5 pre-consent disclosure standards.",
        "statutory_violation": "Trial-to-paid auto-conversion or recurring renewal flagged for review under Section 5 pre-consent disclosure standards.",
        "remedies": "Consumer restitution and regulatory enforcement under Section 5 of the FTC Act",
        "summary": "Merchants must clearly and conspicuously disclose material terms and obtain affirmative consent prior to converting promotional periods into recurring billing.",
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
        "title": "Revocation of Authorization for Preauthorized Electronic Fund Transfers",
        "authority": "Consumer Financial Protection Bureau (CFPB)",
        "effective_date": "Codified Federal Regulation",
        "legal_scope": (
            "Applies specifically to preauthorized electronic fund transfers (recurring bank debits/ACH); "
            "allows consumers to revoke recurring debit authorization and request stop-payment from financial institutions. "
            "Does not constitute an automatic guarantee for all credit card chargebacks."
        ),
        "review_finding": "Recurring electronic debit post-cancellation flagged for cardholder stop-payment and dispute review pursuant to 12 CFR § 1005.10.",
        "statutory_violation": "Recurring electronic debit post-cancellation flagged for cardholder stop-payment and dispute review pursuant to 12 CFR § 1005.10.",
        "remedies": "Financial institution error resolution investigation and cardholder stop-payment rights under Regulation E",
        "summary": "Consumers may revoke authorization for recurring automated debits by giving notice to the merchant or financial institution, providing grounds for bank dispute review if recurring debits continue.",
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
        "title": "Clear Disclosure of Material Recurring Terms (ROSCA)",
        "authority": "Federal Trade Commission (FTC)",
        "effective_date": "Active Federal Statute",
        "legal_scope": (
            "Prohibits charging consumers over the internet through negative option features "
            "without clear, conspicuous disclosure of all material terms prior to obtaining billing information."
        ),
        "review_finding": "Potential undisclosed recurring fee, addon charge, or drip-pricing fee flagged for review under ROSCA.",
        "statutory_violation": "Potential undisclosed recurring fee, addon charge, or drip-pricing fee flagged for review under ROSCA.",
        "remedies": "FTC civil enforcement, restitution, and injunctive proceedings under Section 5",
        "summary": "Prohibits charging consumers online through negative option marketing without clear disclosures and simple stopping mechanisms.",
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
    """Matches a dark pattern trigger phrase against the regulatory reference database."""
    trigger_lower = trigger_phrase.lower().strip()
    for key, data in FTC_POLICY_CLAUSES.items():
        for trigger in data["dark_pattern_triggers"]:
            if trigger in trigger_lower:
                return data
    return FTC_POLICY_CLAUSES["FTC_CLICK_TO_CANCEL"]


def format_legal_citation(clause: Dict[str, Any]) -> str:
    """Formats a formal regulatory citation block for dispute drafts with accurate scope."""
    scope = clause.get("legal_scope", clause.get("summary", ""))
    remedies = clause.get("remedies", "Regulatory dispute review")
    return (
        f"Pursuant to {clause['title']} ({clause['clause_id']}), overseen by the {clause['authority']}. "
        f"Scope: {scope} (Remedy framework: {remedies})."
    )
