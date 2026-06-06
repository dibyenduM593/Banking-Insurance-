import re
from src.schemas import GuardrailResult, GuardrailStatus

# PII patterns tuned for Indian banking context
PII_PATTERNS: dict[str, str] = {
    "aadhaar_number": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "pan_card": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "phone_number": r"\b(?:\+?91[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,5}[-.\s]?\d{4,6}\b",
    "email_address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "bank_account": r"\b\d{9,18}\b",
    "ifsc_code": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    "passport_number": r"\b[A-Z][1-9][0-9]{7}\b",
}

# Prompt injection signatures
INJECTION_PATTERNS: list[str] = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|directions?)",
    r"forget\s+(your|all|the)\s+(role|instructions?|training|context|persona)",
    r"you\s+(are|must\s+be|should\s+be)\s+now\s+(a\s+)?(different|new|unrestricted)",
    r"(act|pretend|behave)\s+as\s+(if\s+you\s+(are|were)\s+)?(?!a\s+banking|an?\s+insurance|a\s+customer)",
    r"\bjailbreak\b",
    r"\bDAN\s+mode\b",
    r"override\s+(safety|guardrail|content\s+filter|restriction)",
    r"disregard\s+(your|all|the)\s+(guidelines?|rules?|instructions?|policies?)",
    r"(reveal|show|print|display)\s+(your\s+)?(system\s+prompt|instructions?|prompt|configuration)",
    r"<\s*\/?\s*(system|instruction|prompt|context)\s*>",
    r"###\s*(system|instruction|new\s+prompt)",
    r"end\s+of\s+(system\s+)?prompt",
    r"assistant\s*:\s*sure",
]

# Banking/insurance domain keywords for off-topic filtering
DOMAIN_KEYWORDS: list[str] = [
    "account", "loan", "credit", "debit", "bank", "insurance", "premium",
    "interest", "rate", "emi", "mortgage", "kyc", "balance", "transaction",
    "transfer", "payment", "savings", "checking", "current", "fixed deposit",
    "fd", "rd", "recurring deposit", "complaint", "dispute", "fraud", "claim",
    "policy", "coverage", "beneficiary", "nominee", "atm", "card", "pin",
    "netbanking", "upi", "ifsc", "swift", "wire transfer", "refinance",
    "collateral", "guarantor", "neft", "rtgs", "imps", "cheque", "branch",
    "eligibility", "document", "aadhaar", "pan", "passport", "salary", "income",
    "tax", "tds", "penalty", "charge", "fee", "minimum balance", "overdraft",
    "limit", "credit score", "cibil", "experian", "term", "tenure", "principal",
    "maturity", "nomination", "joint", "minor", "nri", "forex", "gold loan",
    "personal loan", "home loan", "auto loan", "education loan", "business loan",
    "microfinance", "mudra", "pradhan mantri", "jan dhan", "atal pension",
    "ppf", "nps", "epf", "health insurance", "life insurance", "term plan",
    "endowment", "ulip", "motor insurance", "travel insurance", "fire insurance",
    "liability", "annuity", "surrender", "premium waiver", "reimbursement",
    "cashless", "network hospital", "tpa", "irda", "sebi", "rbi", "nabard",
    "sidbi", "nsdl", "depository", "demat", "mutual fund", "sip",
    "help", "support", "assist", "problem", "issue", "error", "service",
    "apply", "open", "close", "update", "change", "block", "unblock",
    "statement", "passbook", "cheque book", "demand draft", "dd",
    "lockers", "safe deposit", "remittance", "mandate", "ecs", "nach",
]

GREETING_PHRASES: list[str] = [
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
    "thanks", "thank you", "bye", "goodbye", "help me", "i need help",
    "can you help", "please help", "what can you do", "how are you",
]


def _mask_pii(text: str, pii_type: str, pattern: str) -> str:
    """Replace PII with masked placeholder."""
    replacement = f"[{pii_type.upper()}_REDACTED]"
    return re.sub(pattern, replacement, text, flags=re.IGNORECASE)


def check_guardrails(user_input: str) -> GuardrailResult:
    """
    Run all guardrail checks on user input.
    Returns a GuardrailResult describing whether the input is safe to process.
    """
    result = GuardrailResult(status=GuardrailStatus.PASSED, passed=True)
    sanitized = user_input

    # 1. Prompt injection check (highest priority)
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, user_input, re.IGNORECASE | re.DOTALL):
            result.is_injection_attempt = True
            result.passed = False
            result.status = GuardrailStatus.INJECTION_ATTEMPT
            result.reason = (
                "Security alert: Your message contains patterns that appear to be "
                "attempting to manipulate the AI assistant. This activity has been logged."
            )
            return result

    # 2. PII detection
    detected_pii: list[str] = []
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, user_input, re.IGNORECASE):
            detected_pii.append(pii_type.replace("_", " "))
            sanitized = _mask_pii(sanitized, pii_type, pattern)

    if detected_pii:
        result.pii_detected = True
        result.pii_types = detected_pii
        result.passed = False
        result.status = GuardrailStatus.PII_DETECTED
        result.reason = (
            f"Your message contains sensitive personal information "
            f"({', '.join(detected_pii)}). For your security, please do not share "
            f"personal identifiers like Aadhaar, PAN, bank account numbers, or credit "
            f"card details in this chat. Our agents will ask for verification through "
            f"secure channels only."
        )
        result.sanitized_input = sanitized
        return result

    # 3. Off-topic filtering (only apply to longer queries with context)
    input_lower = user_input.lower()
    word_count = len(user_input.split())

    is_greeting = any(phrase in input_lower for phrase in GREETING_PHRASES)
    has_domain_keyword = any(kw in input_lower for kw in DOMAIN_KEYWORDS)

    if not is_greeting and not has_domain_keyword and word_count > 8:
        result.is_off_topic = True
        result.passed = False
        result.status = GuardrailStatus.OFF_TOPIC
        result.reason = (
            "I'm specialized in banking and insurance services. I can help you with "
            "accounts, loans, insurance policies, KYC requirements, complaints, and more. "
            "Please ask a banking or insurance related question."
        )
        return result

    result.sanitized_input = sanitized
    return result
