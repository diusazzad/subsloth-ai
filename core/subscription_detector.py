"""
SubSloth AI - Deterministic Subscription & Dark Pattern Detection Engine (Layer 1)
Parses raw bank statements, credit card SMS logs, or CSV lines.
Extracts recurring frequencies, flags dark patterns without LLM hallucination,
and calculates the exact 'Lazy Payoff' metrics.
"""

import re
from typing import List, Dict, Any, Tuple
from core.ftc_rules import FTC_POLICY_CLAUSES, get_clause_by_trigger, format_legal_citation


# Known subscription cadence keywords
CADENCE_PATTERNS = [
    (r"(?i)(/mo|monthly|per month|every month)", "monthly", 12),
    (r"(?i)(/yr|yearly|annual|annually|per year)", "annual", 1),
    (r"(?i)(/wk|weekly|per week)", "weekly", 52),
    (r"(?i)(sub|subscription|membership|recurring|auto-renew)", "recurring", 12)
]

# Known gym trap merchants that notoriously enforce cancellation friction
GYM_MERCHANT_PATTERNS = [
    r"(?i)\b(planet\s*fitness|equinox|gold'?s\s*gym|la\s*fitness|anytime\s*fitness|blink\s*fitness|crunch\s*fitness|nysc|clubcorp)\b"
]

# Dark pattern heuristic indicators
DARK_PATTERN_REGEX = {
    "GYM_TRAP": [
        r"(?i)(in-person|visit\s*(your\s*)?home\s*gym|certified\s*mail|certified\s*letter|cancel\s*in\s*club|no\s*online\s*cancel)",
        r"(?i)(annual\s*membership\s*fee|club\s*maintenance\s*fee|facility\s*fee)"
    ],
    "SNEAKY_SAAS_TRIAL": [
        r"(?i)(trial\s*converted|trial\s*ended|free\s*trial\s*expired|auto-converted|introductory\s*rate\s*ended)",
        r"(?i)(cloudscale|saas|workspace|cloud\s*pro|enterprise\s*tier)"
    ],
    "GHOST_MICRO_FEE": [
        r"(?i)(addon|add-on|micro\s*fee|streaming\s*pass|vip\s*boost|convenience\s*fee|priority\s*support\s*fee|4k\s*ultra\s*stream)",
        r"(?i)(ghost\s*charge|undisclosed)"
    ]
}


def extract_amount(text: str) -> float:
    """Extracts dollar monetary value from line text safely."""
    match = re.search(r"\$\s*([0-9]+(?:\.[0-9]{2})?)", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    
    # Fallback: look for naked floats with 2 decimals
    fallback = re.search(r"\b([0-9]+\.[0-9]{2})\b", text)
    if fallback:
        try:
            return float(fallback.group(1))
        except ValueError:
            return 0.0
    return 0.0


def detect_cadence(text: str) -> Tuple[str, int]:
    """Detects recurring cadence and returns (cadence_str, annual_multiplier)."""
    for pattern, cadence, multiplier in CADENCE_PATTERNS:
        if re.search(pattern, text):
            return cadence, multiplier
    return "monthly", 12  # Default to monthly recurring assumption


def identify_merchant(text: str) -> str:
    """Extracts cleaned merchant name from statement line."""
    # Remove dates, monetary values, and noisy transaction prefixes
    cleaned = re.sub(r"\b\d{4}[-/]\d{2}[-/]\d{2}\b|\b\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?\b", "", text)
    cleaned = re.sub(r"\$\s*[0-9]+(?:\.[0-9]{2})?|\b[0-9]+\.[0-9]{2}\b", "", cleaned)
    cleaned = re.sub(r"(?i)\b(pos\s*debit|ach\s*debit|recurring\s*pymt|autopay|card\s*purchase|debit)\b", "", cleaned)
    cleaned = re.sub(r"[#*_\-:,;()]+", " ", cleaned)
    cleaned = " ".join(cleaned.split()).strip()
    
    # Extract first 4 significant words as merchant identifier
    tokens = [t for t in cleaned.split() if len(t) > 1 and not t.isdigit()]
    if tokens:
        return " ".join(tokens[:4]).title()
    return "Unknown Subscription Merchant"


def classify_dark_pattern(line_text: str, merchant: str, amount: float) -> Tuple[bool, str, Dict[str, Any], str]:
    """
    Evaluates statement line against deterministic dark pattern rules.
    Returns: (is_dark_pattern, pattern_type, ftc_clause, reason)
    """
    # 1. Test for Gym Trap
    is_gym = any(re.search(p, merchant) for p in GYM_MERCHANT_PATTERNS) or any(re.search(p, line_text) for p in GYM_MERCHANT_PATTERNS)
    for p in DARK_PATTERN_REGEX["GYM_TRAP"]:
        if re.search(p, line_text) or (is_gym and re.search(p, line_text)):
            return (
                True,
                "GYM_TRAP",
                FTC_POLICY_CLAUSES["FTC_CLICK_TO_CANCEL"],
                "Burdensome cancellation requirement (in-person or certified mail) flagged for review under ROSCA (15 U.S.C. § 8403) simple stopping mechanism standards."
            )
    if is_gym and amount > 0:
        return (
            True,
            "GYM_TRAP",
            FTC_POLICY_CLAUSES["FTC_CLICK_TO_CANCEL"],
            "Gym membership with documented retention barriers. Flagged for review under ROSCA (15 U.S.C. § 8403) simple cancellation standards."
        )

    # 2. Test for Sneaky SaaS Trial Conversion
    for p in DARK_PATTERN_REGEX["SNEAKY_SAAS_TRIAL"]:
        if re.search(p, line_text):
            return (
                True,
                "SNEAKY_SAAS_TRIAL",
                FTC_POLICY_CLAUSES["FTC_NEGATIVE_OPTION_DISCLOSURE"],
                "Trial-to-paid auto-conversion scenario flagged for review under Section 5 pre-consent disclosure standards."
            )

    # 3. Test for Ghost Micro-Fee
    for p in DARK_PATTERN_REGEX["GHOST_MICRO_FEE"]:
        if re.search(p, line_text):
            return (
                True,
                "GHOST_MICRO_FEE",
                FTC_POLICY_CLAUSES["ROSCA_UNDISCLOSED_FEES"],
                "Potential undisclosed recurring micro-fee or stealth addon flagged for review under ROSCA (15 U.S.C. § 8403)."
            )
    
    # Check for micro-fee by amount heuristic ($1.00 - $9.99 with 'fee' or 'addon' context)
    if 1.00 <= amount <= 9.99 and re.search(r"(?i)\b(fee|addon|pass|protection|insurance|charge)\b", line_text):
        return (
            True,
            "GHOST_MICRO_FEE",
            FTC_POLICY_CLAUSES["ROSCA_UNDISCLOSED_FEES"],
            "Potential unsolicited micro-charge flagged matching drip pricing heuristics."
        )

    # 4. Standard recurring subscription (Protected under EFTA Reg E)
    return (
        False,
        "STANDARD_SUBSCRIPTION",
        FTC_POLICY_CLAUSES["EFTA_REG_E_CHARGEBACK"],
        "Preauthorized electronic debit covered by CFPB Regulation E revocation rights (12 CFR § 1005.10)."
    )


def audit_statement(raw_input: str) -> Dict[str, Any]:
    """
    Main Layer 1 Audit Entrypoint.
    Parses full raw statement or text dump, identifies all recurring items,
    detects dark patterns, and calculates exact financial drain.
    """
    lines = [line.strip() for line in raw_input.strip().split("\n") if line.strip()]
    if not lines:
        return {
            "total_items": 0,
            "subscriptions": [],
            "total_monthly_drain": 0.0,
            "total_annual_drain": 0.0,
            "dark_patterns_count": 0,
            "lazy_payoff": {
                "hours_saved": 0.0,
                "money_rescued_annual": 0.0,
                "sloth_rating": "Zero Subscriptions Found"
            }
        }

    detected_items: List[Dict[str, Any]] = []
    total_monthly = 0.0
    total_annual = 0.0
    dark_pattern_count = 0

    for idx, line in enumerate(lines):
        amount = extract_amount(line)
        if amount <= 0:
            continue

        cadence, multiplier = detect_cadence(line)
        merchant = identify_merchant(line)
        is_dark_pattern, pattern_type, ftc_clause, reason = classify_dark_pattern(line, merchant, amount)

        if is_dark_pattern:
            dark_pattern_count += 1

        annual_cost = round(amount * multiplier, 2)
        monthly_cost = round(annual_cost / 12.0, 2)

        total_annual += annual_cost
        total_monthly += monthly_cost

        detected_items.append({
            "id": f"sub_{idx + 1}",
            "raw_text": line,
            "merchant": merchant,
            "amount": amount,
            "cadence": cadence,
            "annual_drain": annual_cost,
            "monthly_drain": monthly_cost,
            "dark_pattern_detected": is_dark_pattern,
            "dark_pattern_type": pattern_type,
            "reason": reason,
            "ftc_clause_id": ftc_clause["clause_id"],
            "ftc_title": ftc_clause["title"],
            "citation": format_legal_citation(ftc_clause)
        })

    # The Lazy Payoff Metrics (Reward laziness by showing exact hours and dollars saved)
    # Average cancellation phone maze takes ~45 minutes (0.75 hours) per dark-pattern merchant
    hours_saved = round(len(detected_items) * 0.75, 1)

    return {
        "total_items": len(detected_items),
        "subscriptions": detected_items,
        "total_monthly_drain": round(total_monthly, 2),
        "total_annual_drain": round(total_annual, 2),
        "dark_patterns_count": dark_pattern_count,
        "lazy_payoff": {
            "hours_saved": hours_saved,
            "money_rescued_annual": round(total_annual, 2),
            "sloth_rating": "Master Sloth Level (Maximum Laziness Achieved)" if len(detected_items) > 0 else "Clean Slate"
        },
        "disclaimer": "SubSloth AI provides automated heuristic screening for consumer review. Outputs are informational drafts and do not constitute formal legal conclusions or guarantees."
    }
