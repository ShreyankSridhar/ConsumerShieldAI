import json
from typing import Optional

from google import genai

from backend.app.core.config import get_settings
from backend.app.models.schemas import AnalysisResponse, EvidenceSource, Recommendation


class GeminiService:
    """Encapsulates Gemini API calls, prompts, retries, and response parsing."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._apiKey = self._settings.gemini_api_key
        self._model = self._settings.gemini_model
        self._client = genai.Client(api_key=self._apiKey) if self._apiKey else None

    def classifyComplaint(self, text: str) -> tuple[str, int]:
        from backend.app.services.analysis_service import classify_issue_with_confidence

        return classify_issue_with_confidence(text)

    def explainRights(
        self,
        complaint: str,
        category: str,
        evidence: list[EvidenceSource],
        reasons: list[str],
        extracted_context: str = "",
    ) -> Optional[AnalysisResponse]:
        if self._client is None:
            return None

        evidence_json = json.dumps([source.model_dump() for source in evidence], indent=2)
        prompt = f"""
You are ConsumerSheildAI, an evidence-based consumer rights navigator. Return strict JSON matching:
case_category, rights_summary, reasons, evidence_sources, recommended_actions, email_draft, complaint_letter.

Rules:
- This is informational guidance, not legal advice.
- Never recommend an action without a reason and evidence.
- Use only the provided complaint, structured invoice extraction, retailer policy clauses, and legal clauses.
- Retrieved policy clauses are already restricted to the detected retailer. Do not mention policies from another retailer.
- Do not generate dashboard scores. The backend calculates scores deterministically.
- Keep the language practical and human-readable.

Classified category: {category}
Complaint:
{complaint}

Structured invoice extraction:
{extracted_context}

Evidence:
{evidence_json}

Explainable reasons:
{json.dumps(reasons)}
"""
        response = self._sendPrompt(prompt)
        return self._parseAnalysisResponse(response)

    def generateComplaintLetter(self, category: str) -> tuple[str, str]:
        email = (
            "Subject: Request for resolution of consumer complaint\n\n"
            "Hello Support Team,\n\n"
            f"I am requesting resolution for a {category.lower()} issue. Please review the attached evidence and provide a written outcome under the applicable policy terms.\n\n"
            "Regards"
        )
        letter = (
            "To Whom It May Concern,\n\n"
            f"I am filing this complaint regarding a {category.lower()} issue. I request a fair review based on the attached evidence and applicable consumer protection principles.\n\n"
            "Requested resolution: refund, replacement, repair, or written escalation response."
        )
        return email, letter

    def _sendPrompt(self, prompt: str):
        last_error: Optional[Exception] = None
        for _ in range(2):
            try:
                return self._client.models.generate_content(model=self._model, contents=prompt) if self._client else None
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        return None

    def _parseAnalysisResponse(self, response) -> Optional[AnalysisResponse]:
        if response is None:
            return None
        raw = (response.text or "").strip().removeprefix("```json").removesuffix("```").strip()
        try:
            return AnalysisResponse.model_validate_json(raw)
        except Exception:
            return None


gemini_service = GeminiService()


def fallback_analysis(
    complaint: str,
    category: str,
    evidence: list[EvidenceSource],
    reasons: list[str],
    extracted_context: str = "",
) -> AnalysisResponse:
    primary_evidence = evidence[0].title if evidence else "consumer-rights evidence"
    actions = [
        Recommendation(
            action="Contact Seller",
            reason="Start with the seller because marketplaces usually require a documented seller-resolution attempt.",
            evidence=primary_evidence,
        ),
        Recommendation(
            action="Escalate Support Ticket",
            reason="Escalation is appropriate when the seller denies refund, replacement, repair, or delivery resolution despite supporting evidence.",
            evidence=evidence[1].title if len(evidence) > 1 else primary_evidence,
        ),
        Recommendation(
            action="Consumer Helpline",
            reason="A helpline complaint creates a formal record if platform escalation does not resolve the issue.",
            evidence="Consumer Protection Act 2019",
        ),
        Recommendation(
            action="Consumer Commission",
            reason="Use this route for unresolved disputes involving monetary loss, deficient service, or unfair trade practice after prior escalation.",
            evidence="Consumer Protection Act 2019",
        ),
    ]
    summary = (
        f"Your case appears to involve {category.lower()}. Based on the complaint, structured invoice extraction, and retrieved policy references, "
        "you may have grounds to request a documented resolution such as refund, replacement, repair, or escalation. "
        "Keep invoices, order details, screenshots, and support-ticket records together."
    )
    email = (
        "Subject: Request for resolution of consumer complaint\n\n"
        "Hello Support Team,\n\n"
        f"I am requesting resolution for a {category.lower()} issue. The product/order details, invoice extraction, and support records indicate that my concern should be reviewed under the applicable return, warranty, delivery, or consumer protection policy.\n\n"
        "Please provide a written resolution, including refund, replacement, repair, or clear escalation steps, within a reasonable time.\n\n"
        "Regards"
    )
    letter = (
        "To Whom It May Concern,\n\n"
        f"I am filing this complaint regarding a {category.lower()} issue. I have retained the invoice, screenshots, support communication, and related order records. "
        "The available evidence suggests the matter should be reviewed under applicable consumer protection principles and platform policies.\n\n"
        "Requested resolution: refund, replacement, repair, or written escalation response.\n\n"
        "This complaint is submitted for informational and dispute-resolution purposes."
    )
    return AnalysisResponse(
        case_category=category,
        rights_summary=summary,
        reasons=reasons,
        evidence_sources=evidence,
        confidence_score=0,
        recommended_actions=actions,
        email_draft=email,
        complaint_letter=letter,
    )
