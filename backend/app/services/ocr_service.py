from functools import lru_cache
from pathlib import Path
import re
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile

from backend.app.core.config import get_settings


SIGNIFICANT_TEXT_MIN_CHARS = 24
SIGNIFICANT_TEXT_MIN_CONFIDENCE = 0.55


class OCRService:
    """Encapsulates upload persistence, EasyOCR, cleanup, and OCR text cleaning."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def extractText(self, file: UploadFile) -> str:
        result = await self.processEvidence(file)
        return str(result["extracted_text"])

    def cleanText(self, text: str) -> str:
        corrections = {
            "tax invoce": "Tax Invoice",
            "tax inv0ice": "Tax Invoice",
            "biling adress": "Billing Address",
            "billing adress": "Billing Address",
            "shiping adress": "Shipping Address",
            "ordar numbr": "Order Number",
            "ordar number": "Order Number",
            "ordar": "Order",
            "purchse": "Purchase",
            "puchase": "Purchase",
            "order numbr": "Order Number",
            "numbr": "Number",
            "order nurnber": "Order Number",
            "orderno": "Order No",
            "orderid": "Order ID",
            "referance": "Reference",
            "invoce": "Invoice",
            "inv0ice": "Invoice",
            "invoiceno": "Invoice No",
            "invoice#": "Invoice #",
            "seller narne": "Seller Name",
            "solder by": "Sold By",
            "soid by": "Sold By",
            "merchant narne": "Merchant Name",
            "producl": "Product",
            "descriplion": "Description",
            "descriptlon": "Description",
            "quanity": "Quantity",
            "quantily": "Quantity",
            "arnount": "Amount",
            "tolal": "Total",
            "dale": "Date",
            "dste": "Date",
            "deliverv": "Delivery",
            "delived": "Delivered",
            "gstln": "GSTIN",
            "g5tin": "GSTIN",
        }
        cleaned_lines: list[str] = []
        seen: set[str] = set()
        pending_label = ""
        label_pattern = re.compile(
            r"^(order\s*(?:id|number|no)|reference\s*(?:id|number|no)|invoice\s*(?:number|no|id|#)|purchase\s*date|order\s*date|ordered\s*on|purchased\s*on|invoice\s*date|delivery\s*date|delivered\s*on|received\s*on|sold\s*by|seller|merchant|vendor|product\s*name|product|item|description|price|amount|total)\s*:?\s*$",
            re.IGNORECASE,
        )
        section_header_pattern = re.compile(
            r"^(billing address|shipping address|customer address|recipient|payment method|tax summary)\s*:?\s*$",
            re.IGNORECASE,
        )

        for raw_line in text.splitlines():
            line = re.sub(r"[ \t]+", " ", raw_line).strip(" \t|")
            if not line:
                continue
            for wrong, right in corrections.items():
                line = re.sub(re.escape(wrong), right, line, flags=re.IGNORECASE)
            line = re.sub(r"\b([A-Za-z])\s+([A-Za-z])\s+([A-Za-z])\b", r"\1\2\3", line)
            line = re.sub(r"\bOrde r\b", "Order", line, flags=re.IGNORECASE)
            line = re.sub(r"\bInvoi ce\b", "Invoice", line, flags=re.IGNORECASE)
            line = re.sub(r"\bPurcha se\b", "Purchase", line, flags=re.IGNORECASE)
            line = re.sub(r"\bNum ber\b", "Number", line, flags=re.IGNORECASE)
            line = re.sub(r"\s+([:,.])", r"\1", line)

            if pending_label and section_header_pattern.match(line):
                cleaned_lines.append(pending_label)
                pending_label = ""
            if pending_label and label_pattern.match(line):
                cleaned_lines.append(pending_label)
                pending_label = line.rstrip(":")
                continue
            if pending_label:
                line = f"{pending_label}: {line}"
                pending_label = ""
            elif label_pattern.match(line):
                pending_label = line.rstrip(":")
                continue

            normalized = re.sub(r"\s+", " ", line).lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned_lines.append(line)

        if pending_label:
            cleaned_lines.append(pending_label)
        return "\n".join(cleaned_lines)

    async def processEvidence(self, file: UploadFile) -> dict[str, object]:
        data = await file.read()
        target = self._saveUploadBytes(file.filename, data)
        try:
            if target.suffix.lower() == ".pdf":
                text = "PDF OCR is not enabled in the sample pipeline. Upload an image screenshot or add a PDF rasterization step."
                return {
                    "extracted_text": text,
                    "ocr_confidence": 0.0,
                    "contains_significant_text": False,
                }

            raw_text, ocr_confidence = self._runOcr(target)
            extracted_text = self.cleanText(raw_text)
            has_text = self._containsSignificantText(extracted_text, ocr_confidence)

            return {
                "extracted_text": extracted_text,
                "ocr_confidence": ocr_confidence,
                "contains_significant_text": has_text,
            }
        finally:
            target.unlink(missing_ok=True)

    @lru_cache
    def _reader(self):
        import easyocr

        return easyocr.Reader(["en"], gpu=False)

    def _saveUploadBytes(self, filename: Optional[str], data: bytes) -> Path:
        suffix = Path(filename or "upload.png").suffix or ".png"
        target = self._settings.uploads_dir / f"{uuid4().hex}{suffix}"
        target.write_bytes(data)
        return target

    def _runOcr(self, path: Path) -> tuple[str, float]:
        enhanced_path = self._enhanceImageForOcr(path)
        try:
            results = self._reader().readtext(
                str(enhanced_path),
                detail=1,
                paragraph=False,
                decoder="beamsearch",
                beamWidth=10,
                batch_size=1,
                contrast_ths=0.05,
                adjust_contrast=0.7,
                text_threshold=0.6,
                low_text=0.3,
                link_threshold=0.3,
                canvas_size=4096,
                mag_ratio=1.2,
                rotation_info=[90, 180, 270],
            )
        finally:
            if enhanced_path != path:
                enhanced_path.unlink(missing_ok=True)
        lines: list[str] = []
        confidences: list[float] = []
        for result in self._sortOcrResults(results):
            if len(result) >= 2:
                lines.append(str(result[1]))
            if len(result) >= 3:
                try:
                    confidences.append(float(result[2]))
                except (TypeError, ValueError):
                    pass
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return "\n".join(lines).strip(), round(confidence, 3)

    def _sortOcrResults(self, results):
        def box_metrics(result):
            box = result[0] if result else []
            xs = [point[0] for point in box] if box else [0]
            ys = [point[1] for point in box] if box else [0]
            return min(xs), min(ys), max(ys) - min(ys)

        sorted_results = sorted(results, key=lambda result: (box_metrics(result)[1], box_metrics(result)[0]))
        rows: list[list[object]] = []
        row_centers: list[float] = []
        for result in sorted_results:
            _x, y, height = box_metrics(result)
            threshold = max(10, height * 0.7)
            center_y = y + (height / 2)
            for index, row_center in enumerate(row_centers):
                if abs(center_y - row_center) <= threshold:
                    rows[index].append(result)
                    row_centers[index] = (row_center + center_y) / 2
                    break
            else:
                rows.append([result])
                row_centers.append(center_y)

        ordered = []
        for row in rows:
            ordered.extend(sorted(row, key=lambda result: box_metrics(result)[0]))
        return ordered

    def _enhanceImageForOcr(self, path: Path) -> Path:
        import cv2
        import numpy as np
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps

        image = Image.open(path)
        image = ImageOps.exif_transpose(image)
        image = image.convert("L")
        scale = 3 if min(image.size) < 1200 else 2
        image = image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
        image = ImageEnhance.Contrast(image).enhance(1.8)
        image = ImageEnhance.Sharpness(image).enhance(2.4)

        array = np.array(image)
        array = cv2.fastNlMeansDenoising(array, None, h=18, templateWindowSize=7, searchWindowSize=21)
        array = self._deskew(array)
        array = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(array)
        array = cv2.GaussianBlur(array, (3, 3), 0)
        array = cv2.adaptiveThreshold(
            array,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            35,
            13,
        )
        morphology_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        array = cv2.morphologyEx(array, cv2.MORPH_OPEN, morphology_kernel)
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        array = cv2.filter2D(array, -1, kernel)
        image = Image.fromarray(array).filter(ImageFilter.MedianFilter(size=3))
        enhanced_path = path.with_name(f"{path.stem}_enhanced.png")
        image.save(enhanced_path, dpi=(300, 300))
        return enhanced_path

    def _deskew(self, image):
        import cv2
        import numpy as np

        inverted = cv2.bitwise_not(image)
        coords = np.column_stack(np.where(inverted > 0))
        if coords.size == 0:
            return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 0.5 or abs(angle) > 15:
            return image
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    def _containsSignificantText(self, text: str, confidence: float) -> bool:
        compact_length = len("".join(text.split()))
        return compact_length >= SIGNIFICANT_TEXT_MIN_CHARS and confidence >= SIGNIFICANT_TEXT_MIN_CONFIDENCE


ocr_service = OCRService()
