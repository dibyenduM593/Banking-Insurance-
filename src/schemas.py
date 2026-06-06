from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Dict
from enum import Enum


class IntentCategory(str, Enum):
    ACCOUNT_INQUIRY = "account_inquiry"
    LOAN_CREDIT = "loan_credit"
    COMPLAINT_RESOLUTION = "complaint_resolution"
    KYC_COMPLIANCE = "kyc_compliance"
    INSURANCE = "insurance"
    GENERAL = "general"
    OFF_TOPIC = "off_topic"
    BLOCKED = "blocked"


class GuardrailStatus(str, Enum):
    PASSED = "passed"
    PII_DETECTED = "pii_detected"
    OFF_TOPIC = "off_topic"
    INJECTION_ATTEMPT = "injection_attempt"


class GuardrailResult(BaseModel):
    status: GuardrailStatus = GuardrailStatus.PASSED
    passed: bool = True
    reason: Optional[str] = None
    pii_detected: bool = False
    pii_types: List[str] = Field(default_factory=list)
    is_off_topic: bool = False
    is_injection_attempt: bool = False
    sanitized_input: Optional[str] = None


class LoanEligibilityData(BaseModel):
    annual_income: Optional[float] = None
    monthly_income: Optional[float] = None
    loan_amount_requested: Optional[float] = None
    credit_score: Optional[int] = None
    max_eligible_amount: Optional[float] = None
    emi_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    tenure_months: Optional[int] = None
    eligible: Optional[bool] = None
    foir_ratio: Optional[float] = None
    reasoning_steps: List[str] = Field(default_factory=list)


class ComplaintData(BaseModel):
    complaint_id: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    resolution_steps: List[str] = Field(default_factory=list)
    expected_resolution_days: Optional[int] = None
    escalation_required: bool = False


class AccountInfo(BaseModel):
    account_types: List[Dict[str, Any]] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    interest_rates: Optional[Dict[str, float]] = None


class InsuranceData(BaseModel):
    policy_types: List[str] = Field(default_factory=list)
    claim_steps: List[str] = Field(default_factory=list)
    documents_required: List[str] = Field(default_factory=list)
    coverage_details: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    answer: str
    intent: IntentCategory = IntentCategory.GENERAL
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    follow_up_questions: List[str] = Field(default_factory=list)
    requires_human_agent: bool = False
    structured_data: Optional[Dict[str, Any]] = None
    loan_eligibility: Optional[LoanEligibilityData] = None
    complaint_data: Optional[ComplaintData] = None
    account_info: Optional[AccountInfo] = None
    insurance_data: Optional[InsuranceData] = None
    disclaimer: Optional[str] = None
    guardrail_result: Optional[GuardrailResult] = None

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatSession(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)
    session_id: Optional[str] = None

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(ChatMessage(role=role, content=content))

    def get_history(self) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages]
