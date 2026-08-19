from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from backend.app.controllers.analysis_controller import analysis_controller
from backend.app.models.schemas import AnalysisResponse, OCRResponse

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Small readiness endpoint for the local application."""
    return {"status": "ok"}


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_complaint(
    complaint_text: str = Form(...),
    invoice: Optional[UploadFile] = File(default=None),
    screenshot: Optional[UploadFile] = File(default=None),
) -> AnalysisResponse:
    return await analysis_controller.analyzeComplaint(complaint_text, invoice, screenshot)


@router.post("/ocr/extract", response_model=OCRResponse)
async def extract_ocr(file: UploadFile = File(...)) -> OCRResponse:
    return await analysis_controller.extractOCR(file)
