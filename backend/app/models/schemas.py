from pydantic import BaseModel, Field
from typing import Optional


class EvidenceSource(BaseModel):
    title: str
    source_type: str
    content: str
    relevance_score: float = Field(ge=0, le=1)
    retailer: Optional[str] = None


class Recommendation(BaseModel):
    action: str
    reason: str
    evidence: str
    confidence: int = Field(default=0, ge=0, le=100)


class ScoreComponent(BaseModel):
    name: str
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    contribution: float = Field(ge=-100, le=100)
    explanation: str


class CaseStrengthExplanation(BaseModel):
    components: list[ScoreComponent] = Field(default_factory=list)
    strong_contributors: list[str] = Field(default_factory=list)
    weak_factors: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


class TimelineAnalysis(BaseModel):
    purchase_date: Optional[str] = None
    current_date: str = ""
    return_window_days: int = 30
    warranty_window_days: int = 365
    days_since_purchase: Optional[int] = None
    return_window_status: str = "unknown"
    warranty_window_status: str = "unknown"
    findings: list[str] = Field(default_factory=list)


class InvestigationFacts(BaseModel):
    retailer: str = "Unknown"
    product_name: str = "Unknown"
    brand: str = "Unknown"
    order_id: str = "Unknown"
    invoice_number: str = "Unknown"
    quantity: str = "Unknown"
    gstin: str = "Unknown"
    resolution_requested: str = "Unknown"
    issue_category: str = "Unknown"
    seller_name: str = "Unknown"
    evidence: list[str] = Field(default_factory=list)
    product: str = "Unknown"
    order_date: str = "Unknown"
    delivery_date: str = "Unknown"
    complaint_date: str = "Unknown"
    purchase_price: str = "Unknown"
    seller: str = "Unknown"
    requested_resolution: str = "Unknown"
    evidence_available: list[str] = Field(default_factory=list)


class EvidenceAssessmentItem(BaseModel):
    evidence_type: str
    checks: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    score: int = Field(default=0, ge=0, le=100)


class PolicyMatchAnalysis(BaseModel):
    retailer_policy: str = "Unknown"
    return_window_status: str = "unknown"
    warranty_status: str = "unknown"
    retailer_response_consistency: str = "Unknown"
    notes: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    retailer: Optional[str] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    case_category: str
    rights_summary: str
    reasons: list[str]
    evidence_sources: list[EvidenceSource]
    evidence_completeness_score: int = Field(default=0, ge=0, le=100)
    consumer_case_strength_score: int = Field(default=0, ge=0, le=100)
    case_verdict: str = "Insufficient Evidence"
    timeline_analysis: TimelineAnalysis = Field(default_factory=TimelineAnalysis)
    case_strength_score: int = Field(default=0, ge=0, le=100)
    case_strength_label: str = "Insufficient Evidence"
    case_strength_explanation: CaseStrengthExplanation = Field(default_factory=CaseStrengthExplanation)
    confidence_score: int = Field(default=0, ge=0, le=100)
    analysis_confidence_score: int = Field(default=0, ge=0, le=100)
    investigation_facts: InvestigationFacts = Field(default_factory=InvestigationFacts)
    evidence_assessment: list[EvidenceAssessmentItem] = Field(default_factory=list)
    positive_factors: list[str] = Field(default_factory=list)
    negative_factors: list[str] = Field(default_factory=list)
    policy_match_analysis: PolicyMatchAnalysis = Field(default_factory=PolicyMatchAnalysis)
    recommended_actions: list[Recommendation]
    recommended_next_action: str = ""
    email_draft: str
    complaint_letter: str
    extracted_text: Optional[str] = None
    disclaimer: str = "This platform provides informational guidance and does not constitute legal advice."


class OCRResponse(BaseModel):
    extracted_text: str
    ocr_confidence: float = Field(default=0.0, ge=0, le=1)
    contains_significant_text: bool = False
