from typing import Optional

from fastapi import UploadFile

from backend.app.models.schemas import AnalysisResponse, OCRResponse
from backend.app.services.analysis_service import ComplaintAnalysisService, complaint_analysis_service
from backend.app.services.ocr_service import OCRService, ocr_service


class AnalysisController:
    """Thin controller: receives API inputs and delegates all business logic to services."""

    def __init__(
        self,
        analysis_service: ComplaintAnalysisService = complaint_analysis_service,
        ocr_service_instance: OCRService = ocr_service,
    ) -> None:
        self._analysisService = analysis_service
        self._ocrService = ocr_service_instance

    async def analyzeComplaint(
        self,
        complaint_text: str,
        invoice: Optional[UploadFile] = None,
        screenshot: Optional[UploadFile] = None,
    ) -> AnalysisResponse:
        return await self._analysisService.analyzeComplaintFromUploads(complaint_text, invoice, screenshot)

    async def extractOCR(self, file: UploadFile) -> OCRResponse:
        result = await self._ocrService.processEvidence(file)
        return OCRResponse(**result)


analysis_controller = AnalysisController()
