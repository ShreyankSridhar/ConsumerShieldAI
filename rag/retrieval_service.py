import logging
import re
from dataclasses import dataclass
from typing import Optional

from backend.app.models.schemas import EvidenceSource
from backend.app.services.gemini_service import GeminiService, gemini_service
from rag.chroma_service import ChromaService, chroma_service

logger = logging.getLogger("consumersheildai.retrieval")

SUPPORTED_RETAILERS = ("amazon", "flipkart", "myntra")
RETAILER_PATTERNS = {
    "amazon": re.compile(r"(?<![a-z0-9])(?:amazon|amzn)(?![a-z0-9])", re.IGNORECASE),
    "flipkart": re.compile(r"(?<![a-z0-9])flipkart(?![a-z0-9])", re.IGNORECASE),
    "myntra": re.compile(r"(?<![a-z0-9])myntra(?![a-z0-9])", re.IGNORECASE),
}


@dataclass(frozen=True)
class RetrievalContext:
    retailer: Optional[str]
    policy_sources: list[EvidenceSource]
    legal_sources: list[EvidenceSource]

    @property
    def merged_sources(self) -> list[EvidenceSource]:
        return [*self.policy_sources, *self.legal_sources]


class RAGService:
    """Encapsulates retailer detection, vector retrieval, and Gemini context generation."""

    def __init__(
        self,
        chroma_service_instance: ChromaService = chroma_service,
        gemini_service_instance: GeminiService = gemini_service,
    ) -> None:
        self._chromaService = chroma_service_instance
        self._geminiService = gemini_service_instance
        self._retailerPatterns = RETAILER_PATTERNS

    def analyzeComplaint(
        self,
        masked_complaint: str,
        category: str,
        reasons: list[str],
        ocr_text: str = "",
        metadata_text: str = "",
    ):
        retrieval_context = "\n\n".join(part for part in [masked_complaint, ocr_text, metadata_text] if part)
        evidence = self.retrieveEvidence(retrieval_context, category=category)
        return self.generateRightsSummary(masked_complaint, category, evidence.merged_sources, reasons, ocr_text)

    def retrieveEvidence(self, query: str, retailer: Optional[str] = None, category: Optional[str] = None) -> RetrievalContext:
        detected_retailer = retailer or self.detectRetailer(query)
        if not detected_retailer:
            return RetrievalContext(retailer=None, policy_sources=[], legal_sources=[])
        policy_sources = self._retrievePolicyDocuments(query, detected_retailer, category)
        legal_sources = self._retrieveLegalDocuments(query, category)
        return RetrievalContext(retailer=detected_retailer, policy_sources=policy_sources, legal_sources=legal_sources)

    def generateRightsSummary(
        self,
        masked_complaint: str,
        category: str,
        evidence: list[EvidenceSource],
        reasons: list[str],
        ocr_text: str = "",
    ):
        return self._geminiService.explainRights(masked_complaint, category, evidence, reasons, ocr_text)

    def detectRetailer(self, *texts: str) -> Optional[str]:
        combined = "\n".join(text for text in texts if text).lower()
        matches = [retailer for retailer, pattern in self._retailerPatterns.items() if pattern.search(combined)]
        if len(matches) == 1:
            logger.info("Detected retailer: %s", matches[0])
            return matches[0]
        logger.info("Detected retailer: unknown")
        return None

    def _retrievePolicyDocuments(self, query: str, retailer: str, category: Optional[str] = None, limit: int = 3) -> list[EvidenceSource]:
        if retailer not in SUPPORTED_RETAILERS:
            raise ValueError(f"Unsupported retailer: {retailer}")
        self._chromaService.seed()
        enriched_query = f"{retailer}\n{category or ''}\n{query}".strip()
        sources = self._chromaService.searchDocuments(self._chromaService.policyCollectionName(retailer), enriched_query, limit)
        logger.info("Policy documents retrieved: %s", [source.title for source in sources])
        return sources

    def _retrieveLegalDocuments(self, query: str, category: Optional[str] = None, limit: int = 3) -> list[EvidenceSource]:
        self._chromaService.seed()
        enriched_query = f"{category or ''}\n{query}".strip()
        sources = self._chromaService.searchDocuments(self._chromaService.legalCollectionName(), enriched_query, limit)
        logger.info("Legal documents retrieved: %s", [source.title for source in sources])
        return sources

    def classifyComplaint(self, text: str) -> tuple[str, int]:
        return self._geminiService.classifyComplaint(text)


rag_service = RAGService()
