from typing import Optional
from datetime import date
import json

from fastapi import UploadFile

from backend.app.models.schemas import AnalysisResponse
from backend.app.services.database import DatabaseService, database_service
from backend.app.services.gemini_service import fallback_analysis
from backend.app.services.ocr_service import OCRService, ocr_service
from backend.app.services.scoring_service import EvaluationInput, ScoringService, extract_structured_information, scoring_service
from rag.retrieval_service import RAGService, rag_service


RETAILER_CLARIFICATION_QUESTION = "Which platform was the purchase made from? Amazon, Flipkart, or Myntra?"


CATEGORY_KEYWORDS = {
    "Wrong Product": ["wrong product", "different item", "incorrect item", "not what i ordered"],
    "Defective Product": ["defective", "damaged", "not working", "broken", "faulty"],
    "Damaged Product": ["damaged", "physical damage", "cracked", "broken", "detached"],
    "Warranty Issue": ["warranty", "repair denied", "service center", "guarantee"],
    "Delivery Issue": ["delivery", "delayed", "not delivered", "missing package", "shipment"],
    "Missing Item": ["missing item", "item missing", "part missing", "incomplete package"],
    "Refund Delay": ["refund delay", "refund pending", "refund not received", "money not credited"],
    "Return Rejected": ["return rejected", "return denied", "return refused", "pickup rejected"],
    "Counterfeit Product": ["fake", "counterfeit", "duplicate", "not genuine"],
    "Seller Misconduct": ["seller misconduct", "seller refused", "seller cheated", "seller abusive"],
    "Other": [],
}


def classify_issue_with_confidence(text: str) -> tuple[str, int]:
    lowered = text.lower()
    scores = {
        category: sum(1 for keyword in keywords if keyword in lowered)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best_category, score = max(scores.items(), key=lambda item: item[1])
    if score <= 0:
        return "Other", 50

    tied_categories = [category for category, category_score in scores.items() if category_score == score]
    if len(tied_categories) > 1:
        return best_category, 65
    if score == 1:
        return best_category, 75
    if score == 2:
        return best_category, 85
    return best_category, 90


def classify_issue(text: str) -> str:
    return classify_issue_with_confidence(text)[0]


def explain_reasons(text: str, category: str, evidence_count: int) -> list[str]:
    lowered = text.lower()
    reasons = [f"Complaint classified as {category}"]
    if any(term in lowered for term in ["invoice", "order", "receipt", "screenshot"]):
        reasons.append("Purchase evidence or support record mentioned")
    if any(term in lowered for term in ["defective", "damaged", "broken", "not working"]):
        reasons.append("Product reported defective")
    if any(term in lowered for term in ["return window", "within", "days", "warranty"]):
        reasons.append("Timeline or warranty period mentioned")
    if evidence_count:
        reasons.append("Relevant policy matched")
    return reasons[:5]


def _neutral_rights_summary(verdict: str, category: str, weak_factors: list[str]) -> Optional[str]:
    if verdict.startswith("🔴"):
        reasons = "; ".join(factor.lstrip("-") for factor in weak_factors[:3])
        return (
            "Based on the available information, the likelihood of a successful consumer-rights claim appears low. "
            f"The case was classified as {category}, but the evaluation found limiting factors"
            f"{': ' + reasons if reasons else ''}. Review the retailer policy and add stronger evidence before pursuing escalation."
        )
    if verdict.startswith("🟠"):
        reasons = "; ".join(factor.lstrip("-") for factor in weak_factors[:3])
        return (
            f"This appears to be a weak {category.lower()} claim with the current evidence. "
            f"Success may be difficult{': ' + reasons if reasons else ''}. Review the retailer policy and collect clearer proof before escalating."
        )
    if verdict.startswith("🟡"):
        return (
            f"This appears to be a moderate {category.lower()} claim. The available facts support further review, "
            "but additional evidence may be needed before escalation."
        )
    return None


def _clarification_response() -> AnalysisResponse:
    return AnalysisResponse(
        retailer=None,
        needs_clarification=True,
        clarification_question=RETAILER_CLARIFICATION_QUESTION,
        case_category="Retailer Required",
        rights_summary=RETAILER_CLARIFICATION_QUESTION,
        reasons=["Retailer could not be confidently identified"],
        evidence_sources=[],
        case_strength_score=0,
        case_strength_label="Insufficient Evidence",
        confidence_score=0,
        recommended_actions=[],
        email_draft="",
        complaint_letter="",
    )


class ComplaintAnalysisService:
    """Encapsulates the complete complaint workflow behind a single public API."""

    def __init__(
        self,
        rag: RAGService = rag_service,
        scoring: ScoringService = scoring_service,
        ocr: OCRService = ocr_service,
        database: DatabaseService = database_service,
    ) -> None:
        self._ragService = rag
        self._scoringService = scoring
        self._ocrService = ocr
        self._databaseService = database

    async def analyzeComplaintFromUploads(
        self,
        complaint_text: str,
        invoice: Optional[UploadFile] = None,
        screenshot: Optional[UploadFile] = None,
    ) -> AnalysisResponse:
        extracted_chunks: list[str] = []
        invoice_ocr_text = ""
        screenshot_ocr_text = ""
        invoice_ocr_confidence = 1.0
        try:
            for upload in [invoice, screenshot]:
                if upload and (upload.content_type or "").startswith("image/"):
                    result = await self._ocrService.processEvidence(upload)
                    extracted_text = str(result["extracted_text"])
                    if extracted_text:
                        extracted_chunks.append(extracted_text)
                        if upload is invoice:
                            invoice_ocr_text = extracted_text
                        elif upload is screenshot:
                            screenshot_ocr_text = extracted_text
                    if upload is invoice:
                        invoice_ocr_confidence = float(result.get("ocr_confidence", 0.0))
            metadata_text = " ".join(
                part
                for part in [
                    invoice.filename if invoice else "",
                    invoice.content_type if invoice else "",
                    screenshot.filename if screenshot else "",
                    screenshot.content_type if screenshot else "",
                ]
                if part
            )
            result = self.analyzeComplaint(
                complaint_text,
                ocr_text="\n\n".join(extracted_chunks),
                metadata_text=metadata_text,
                invoice_uploaded=invoice is not None,
                screenshot_uploaded=screenshot is not None,
                ocr_confidence=invoice_ocr_confidence,
                invoice_ocr_text=invoice_ocr_text,
                screenshot_ocr_text=screenshot_ocr_text,
                manage_privacy=False,
            )
            result.extracted_text = "\n\n".join(extracted_chunks) if extracted_chunks else None
            return result
        finally:
            pass

    def analyzeComplaint(
        self,
        complaint_text: str,
        ocr_text: str = "",
        metadata_text: str = "",
        invoice_uploaded: bool = False,
        screenshot_uploaded: bool = False,
        ocr_confidence: float = 1.0,
        invoice_ocr_text: str = "",
        screenshot_ocr_text: str = "",
        manage_privacy: bool = True,
    ) -> AnalysisResponse:
        return self._analyzeComplaint(
            complaint_text,
            ocr_text=ocr_text,
            metadata_text=metadata_text,
            invoice_uploaded=invoice_uploaded,
            screenshot_uploaded=screenshot_uploaded,
            ocr_confidence=ocr_confidence,
            invoice_ocr_text=invoice_ocr_text,
            screenshot_ocr_text=screenshot_ocr_text,
        )

    def _analyzeComplaint(
        self,
        complaint_text: str,
        ocr_text: str = "",
        metadata_text: str = "",
        invoice_uploaded: bool = False,
        screenshot_uploaded: bool = False,
        ocr_confidence: float = 1.0,
        invoice_ocr_text: str = "",
        screenshot_ocr_text: str = "",
    ) -> AnalysisResponse:
        retrieval_context = "\n\n".join(part for part in [complaint_text, ocr_text, metadata_text] if part)
        retailer = self._ragService.detectRetailer(complaint_text, ocr_text, metadata_text)
        if not retailer:
            return _clarification_response()

        category, _classification_confidence = self._ragService.classifyComplaint(complaint_text)
        extracted_facts = extract_structured_information(
            complaint_text,
            ocr_text,
            category=category,
            retailer=retailer,
            invoice_uploaded=invoice_uploaded,
            screenshot_uploaded=screenshot_uploaded,
            current_date=date.today(),
            invoice_ocr_text=invoice_ocr_text or ocr_text,
            screenshot_ocr_text=screenshot_ocr_text,
        )
        retrieval = self._ragService.retrieveEvidence(retrieval_context, retailer=retailer, category=category)
        evidence = retrieval.merged_sources
        reasons = explain_reasons(retrieval_context, category, len(evidence))
        structured_context = json.dumps(extracted_facts.model_dump(), indent=2)
        result = self._ragService.generateRightsSummary(complaint_text, category, evidence, reasons, structured_context) or fallback_analysis(
            complaint_text,
            category,
            evidence,
            reasons,
            structured_context,
        )
        result.retailer = retailer
        evaluation = self._scoringService.calculateCaseStrength(
            EvaluationInput(
                complaint_text=complaint_text,
                category=category,
                evidence_sources=evidence,
                retailer=retailer,
                invoice_uploaded=invoice_uploaded,
                screenshot_uploaded=screenshot_uploaded,
                ocr_text=ocr_text,
                ocr_confidence=ocr_confidence,
                extracted_facts=extracted_facts,
            )
        )
        self._applyEvaluation(result, evaluation, category)
        self._databaseService.saveCase(
            result.case_category,
            result.consumer_case_strength_score,
            result.evidence_completeness_score,
            [source.title for source in result.evidence_sources if source.source_type.lower() == "policy"],
        )
        return result

    def _applyEvaluation(self, result: AnalysisResponse, evaluation, category: str) -> None:
        result.evidence_completeness_score = evaluation.evidence_completeness_score
        result.consumer_case_strength_score = evaluation.consumer_case_strength_score
        result.case_verdict = evaluation.case_verdict
        result.timeline_analysis = evaluation.timeline_analysis
        result.case_strength_score = evaluation.consumer_case_strength_score
        result.case_strength_label = evaluation.case_verdict
        result.case_strength_explanation = evaluation.explanation
        result.confidence_score = evaluation.analysis_confidence_score
        result.analysis_confidence_score = evaluation.analysis_confidence_score
        result.investigation_facts = evaluation.investigation_facts
        result.evidence_assessment = evaluation.evidence_assessment
        result.positive_factors = evaluation.positive_factors
        result.negative_factors = evaluation.negative_factors
        result.policy_match_analysis = evaluation.policy_match_analysis
        result.recommended_actions = evaluation.recommended_actions
        result.recommended_next_action = evaluation.recommended_next_action
        neutral_summary = _neutral_rights_summary(
            evaluation.case_verdict,
            category,
            evaluation.explanation.weak_factors,
        )
        if neutral_summary:
            result.rights_summary = neutral_summary
        result.email_draft = evaluation.email_draft
        result.complaint_letter = evaluation.complaint_letter


complaint_analysis_service = ComplaintAnalysisService()
