import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from backend.app.models.schemas import (
    CaseStrengthExplanation,
    EvidenceAssessmentItem,
    EvidenceSource,
    InvestigationFacts,
    PolicyMatchAnalysis,
    Recommendation,
    ScoreComponent,
    TimelineAnalysis,
)


logger = logging.getLogger("consumersheildai.scoring")


ORDER_PATTERNS = [
    re.compile(r"\border\s*(?:id|number|no\.?|#)\s*[:#-]?\s*[a-z0-9-]{4,}\b", re.IGNORECASE),
    re.compile(r"\binvoice\s*(?:id|number|no\.?|#)?\s*[:#-]?\s*[a-z0-9-]{4,}\b", re.IGNORECASE),
    re.compile(r"\b#[a-z0-9-]{5,}\b", re.IGNORECASE),
]
SUPPORT_PATTERN = re.compile(r"\b(?:support|ticket|chat|email|customer care|helpline|complaint|escalat(?:e|ed|ion)|acknowledged?)\b", re.IGNORECASE)
ISSUE_PATTERN = re.compile(r"\b(?:denied|defective|damaged|broken|wrong|fake|counterfeit|not working|missing|delayed|not delivered|cracked|faulty|detached)\b", re.IGNORECASE)
DEFECT_PATTERN = re.compile(r"\b(?:defective|damaged|broken|not working|cracked|faulty|detached|stitching defect|physical damage)\b", re.IGNORECASE)
WRONG_PRODUCT_PATTERN = re.compile(r"\b(?:wrong product|wrong item|different item|incorrect item|not what i ordered|mismatch)\b", re.IGNORECASE)
DENIAL_PATTERN = re.compile(r"\b(?:denied|refused|rejected|closed ticket|no refund|not replacing|replacement denied)\b", re.IGNORECASE)
RESOLUTION_PATTERN = re.compile(r"\b(?:refund|replacement|replace|return|repair|warranty|compensation|exchange)\b", re.IGNORECASE)
WARRANTY_PATTERN = re.compile(r"\b(?:warranty|guarantee|service center|repair)\b", re.IGNORECASE)
RETURN_WINDOW_PATTERN = re.compile(r"\b(?:return window|within\s+\d+\s+days?|delivered yesterday|today|yesterday)\b", re.IGNORECASE)
SIGNIFICANT_TEXT_MIN_CONFIDENCE = 0.55
PRICE_PATTERN = re.compile(r"(?:rs\.?|inr|₹)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", re.IGNORECASE)
SELLER_PATTERN = re.compile(r"\b(?:seller|sold by|fulfilled by)\s*[:#-]?\s*([a-z0-9 &._-]{3,60})", re.IGNORECASE)
PRODUCT_PATTERN = re.compile(r"\b(?:bought|purchased|ordered|received)\s+(?:a|an|the)?\s*([a-z0-9 &._-]{3,50}?)(?:\s+from|\s+on|\s+for|\.|,|$)", re.IGNORECASE)
DELIVERY_DATE_PATTERN = re.compile(r"\b(?:delivered|delivery date)\D{0,20}((?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)|(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{4}))", re.IGNORECASE)
COMPLAINT_DATE_PATTERN = re.compile(r"\b(?:complained|complaint date|reported|raised ticket)\D{0,20}((?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)|(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{4})|today|yesterday)", re.IGNORECASE)

NEGATIVE_FACTOR_PATTERNS = [
    ("Product used for weeks/months", re.compile(r"\b(?:used for|after)\s+(?:weeks?|months?|[2-9]\d*\s+days?)\b", re.IGNORECASE)),
    ("Customer changed mind", re.compile(r"\b(?:changed my mind|do not like|didn't like|no longer want)\b", re.IGNORECASE)),
    ("Damage caused by customer", re.compile(r"\b(?:i damaged|i broke|dropped|accidental damage|my fault)\b", re.IGNORECASE)),
    ("Accidental damage admitted", re.compile(r"\b(?:accidentally|by mistake)\s+(?:broke|damaged|dropped)\b", re.IGNORECASE)),
    ("Wear and tear likely", re.compile(r"\b(?:wear and tear|worn out|used heavily|normal use)\b", re.IGNORECASE)),
    ("Contradictory statements", re.compile(r"\b(?:not sure|maybe|contradict|different dates|conflicting)\b", re.IGNORECASE)),
]

POSITIVE_FACTOR_PATTERNS = [
    ("Product delivered recently", re.compile(r"\b(?:today|yesterday|delivered today|delivered yesterday|within\s+\d+\s+days?)\b", re.IGNORECASE)),
    ("Complaint reported immediately", re.compile(r"\b(?:immediately|same day|within 24 hours|right away)\b", re.IGNORECASE)),
    ("Manufacturing defect likely", re.compile(r"\b(?:manufacturing defect|defective|not working|dead on arrival|doa)\b", re.IGNORECASE)),
    ("Wrong product delivered", WRONG_PRODUCT_PATTERN),
    ("Product dead on arrival", re.compile(r"\b(?:dead on arrival|doa|never worked|not turning on)\b", re.IGNORECASE)),
    ("Seller rejected despite evidence", re.compile(r"\b(?:seller|support|platform).{0,40}(?:rejected|denied|refused)\b", re.IGNORECASE)),
]

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


@dataclass(frozen=True)
class EvaluationInput:
    complaint_text: str
    category: str
    evidence_sources: list[EvidenceSource]
    retailer: Optional[str]
    invoice_uploaded: bool
    screenshot_uploaded: bool
    ocr_text: str
    ocr_confidence: float = 1.0
    extracted_facts: Optional[InvestigationFacts] = None
    current_date: date = field(default_factory=date.today)


@dataclass(frozen=True)
class EvaluationResult:
    evidence_completeness_score: int
    consumer_case_strength_score: int
    case_verdict: str
    timeline_analysis: TimelineAnalysis
    explanation: CaseStrengthExplanation
    analysis_confidence_score: int
    investigation_facts: InvestigationFacts
    evidence_assessment: list[EvidenceAssessmentItem]
    positive_factors: list[str]
    negative_factors: list[str]
    policy_match_analysis: PolicyMatchAnalysis
    recommended_actions: list[Recommendation]
    recommended_next_action: str
    email_draft: str
    complaint_letter: str


def verdict_for_score(score: int) -> str:
    if score >= 85:
        return "🟢 Strong Claim"
    if score >= 50:
        return "🟡 Moderate Claim"
    return "🔴 Weak Claim"


def _decision_text(input_data: EvaluationInput) -> str:
    """Return only evidence allowed to influence case-strength scoring."""
    return "\n".join([input_data.complaint_text, input_data.ocr_text])


def _extract_match(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return match.group(1).strip(" .,-") if match else "Unknown"


def _first_known(*values: str) -> str:
    for value in values:
        cleaned = (value or "").strip()
        if cleaned and cleaned != "Unknown":
            return cleaned
    return "Unknown"


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" .,:;-")


def _normalize_date(raw: str, current_date: date) -> str:
    value = _clean_value(raw).lower().replace(",", " ")
    value = re.sub(r"\s+", " ", value)
    if not value or value == "unknown":
        return "Unknown"
    if value == "today":
        return current_date.isoformat()
    if value == "yesterday":
        from datetime import timedelta
        return (current_date - timedelta(days=1)).isoformat()
    numeric = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?", value)
    if numeric:
        day = int(numeric.group(1))
        month = int(numeric.group(2))
        year = current_date.year if not numeric.group(3) else int(numeric.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return "Unknown"
    iso = re.fullmatch(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", value)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3))).isoformat()
        except ValueError:
            return "Unknown"
    month_name = re.fullmatch(r"(\d{1,2})\s+(" + "|".join(MONTHS.keys()) + r")\s+(\d{4})", value)
    if month_name:
        try:
            return date(int(month_name.group(3)), MONTHS[month_name.group(2)], int(month_name.group(1))).isoformat()
        except ValueError:
            return "Unknown"
    month_name_first = re.fullmatch(r"(" + "|".join(MONTHS.keys()) + r")\s+(\d{1,2})\s+(\d{4})", value)
    if month_name_first:
        try:
            return date(int(month_name_first.group(3)), MONTHS[month_name_first.group(1)], int(month_name_first.group(2))).isoformat()
        except ValueError:
            return "Unknown"
    month_year = re.fullmatch(r"(" + "|".join(MONTHS.keys()) + r")\s+(\d{4})", value)
    if month_year:
        return date(int(month_year.group(2)), MONTHS[month_year.group(1)], 1).isoformat()
    return "Unknown"


def _extract_date(patterns: list[re.Pattern[str]], text: str, current_date: date) -> str:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            normalized = _normalize_date(match.group(1), current_date)
            if normalized != "Unknown":
                return normalized
    return "Unknown"


@dataclass(frozen=True)
class DateCandidate:
    source: str
    label: str
    raw_value: str
    normalized_value: str
    source_priority: int
    label_priority: int


def _collect_date_candidates(
    text: str,
    *,
    source: str,
    source_priority: int,
    current_date: date,
    date_token: str,
) -> list[DateCandidate]:
    candidates: list[DateCandidate] = []
    label_groups = [
        ("Purchase Date", r"purchase\s*date", 0),
        ("Order Date", r"order\s*date", 0),
        ("Purchased On", r"purchased\s*on", 0),
        ("Ordered On", r"ordered\s*on", 0),
        ("Order Placed", r"order\s*placed|placed\s*on", 0),
        ("Invoice Date", r"invoice\s*date", 1),
    ]
    for label, label_pattern, label_priority in label_groups:
        pattern = re.compile(rf"\b(?:{label_pattern})\b\s*[:#-]?\s*(?:\n|\r|\s){{0,15}}{date_token}", re.IGNORECASE)
        for match in pattern.finditer(text or ""):
            raw_value = _clean_value(match.group(1))
            normalized = _normalize_date(raw_value, current_date)
            if normalized != "Unknown":
                candidates.append(DateCandidate(source, label, raw_value, normalized, source_priority, label_priority))
    return candidates


def _collect_complaint_purchase_candidates(text: str, current_date: date, date_token: str) -> list[DateCandidate]:
    candidates = _collect_date_candidates(
        text,
        source="Complaint",
        source_priority=1,
        current_date=current_date,
        date_token=date_token,
    )
    phrase_pattern = re.compile(
        rf"\b(?:i\s+)?(?:ordered|purchased|bought)\b.{{0,80}}?\bon\s+{date_token}",
        re.IGNORECASE | re.DOTALL,
    )
    for match in phrase_pattern.finditer(text or ""):
        raw_value = _clean_value(match.group(1))
        normalized = _normalize_date(raw_value, current_date)
        if normalized != "Unknown":
            candidates.append(DateCandidate("Complaint", "Purchase Phrase", raw_value, normalized, 1, 0))
    return candidates


def _log_purchase_source_status(source: str, candidates: list[DateCandidate]) -> None:
    logger.info("%s Purchase Date: %s", source, "FOUND" if candidates else "NOT FOUND")
    if candidates:
        logger.info(
            "%s purchase date candidates found: %s",
            source,
            [
                {
                    "label": candidate.label,
                    "raw": candidate.raw_value,
                    "normalized": candidate.normalized_value,
                }
                for candidate in candidates
            ],
        )


def _select_purchase_date(
    *,
    invoice_ocr: str,
    complaint: str,
    screenshot_ocr: str,
    current_date: date,
    date_token: str,
) -> str:
    invoice_candidates = sorted(
        _collect_date_candidates(
            invoice_ocr,
            source="Invoice",
            source_priority=0,
            current_date=current_date,
            date_token=date_token,
        ),
        key=lambda candidate: candidate.label_priority,
    )
    complaint_candidates = sorted(
        _collect_complaint_purchase_candidates(complaint, current_date, date_token),
        key=lambda candidate: candidate.label_priority,
    )
    screenshot_candidates = sorted(
        _collect_date_candidates(
            screenshot_ocr,
            source="Screenshot",
            source_priority=2,
            current_date=current_date,
            date_token=date_token,
        ),
        key=lambda candidate: candidate.label_priority,
    )

    _log_purchase_source_status("Invoice", invoice_candidates)
    _log_purchase_source_status("Complaint", complaint_candidates)
    _log_purchase_source_status("Screenshot", screenshot_candidates)

    if invoice_candidates:
        selected = invoice_candidates[0]
        logger.info("Selected Purchase Date: %s", selected.normalized_value)
        logger.info("Source: Invoice")
        return selected.normalized_value
    if complaint_candidates:
        selected = complaint_candidates[0]
        logger.info("Selected Purchase Date: %s", selected.normalized_value)
        logger.info("Source: Complaint")
        return selected.normalized_value
    if screenshot_candidates:
        selected = screenshot_candidates[0]
        logger.info("Selected Purchase Date: %s", selected.normalized_value)
        logger.info("Source: Screenshot")
        return selected.normalized_value

    logger.info("No purchase date found in OCR or complaint.")
    return "Unknown"


def _extract_with_patterns(patterns: list[re.Pattern[str]], text: str) -> str:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return _clean_value(match.group(1))
    return "Unknown"


def _extract_confident(patterns: list[tuple[re.Pattern[str], float]], text: str, minimum_confidence: float = 0.8) -> str:
    for pattern, confidence in patterns:
        match = pattern.search(text)
        if match and confidence >= minimum_confidence:
            return _clean_value(match.group(1))
    return "Unknown"


def _extract_issue_category(text: str, fallback: str) -> str:
    lowered = text.lower()
    if WRONG_PRODUCT_PATTERN.search(text):
        return "Wrong Product"
    if re.search(r"\b(?:damaged|broken|cracked|detached|physical damage)\b", lowered):
        return "Damaged Product"
    if DEFECT_PATTERN.search(text):
        return "Defective Product"
    if re.search(r"\b(?:not delivered|delayed|delivery|shipment)\b", lowered):
        return "Delivery Issue"
    if re.search(r"\b(?:missing item|item missing|part missing|incomplete)\b", lowered):
        return "Missing Item"
    if re.search(r"\b(?:refund delay|refund pending|refund not received|money not credited)\b", lowered):
        return "Refund Delay"
    if re.search(r"\b(?:return rejected|return denied|return refused|pickup rejected)\b", lowered):
        return "Return Rejected"
    if WARRANTY_PATTERN.search(text):
        return "Warranty Issue"
    if re.search(r"\b(?:fake|counterfeit|duplicate|not genuine)\b", lowered):
        return "Counterfeit Product"
    if re.search(r"\b(?:seller refused|seller cheated|seller misconduct|abusive)\b", lowered):
        return "Seller Misconduct"
    return fallback or "Other"


def extract_structured_information(
    complaint_text: str,
    ocr_text: str,
    *,
    category: str,
    retailer: Optional[str],
    invoice_uploaded: bool,
    screenshot_uploaded: bool,
    current_date: date,
    invoice_ocr_text: str = "",
    screenshot_ocr_text: str = "",
) -> InvestigationFacts:
    """Phase 1 extraction. Complaint text wins; OCR fills only missing fields."""
    complaint = complaint_text or ""
    ocr = ocr_text or ""
    invoice_ocr = invoice_ocr_text or ""
    screenshot_ocr = screenshot_ocr_text or ""

    date_token = r"((?:\d{4}[./-]\d{1,2}[./-]\d{1,2})|(?:\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)|(?:\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*,?\s+\d{4})|(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4})|(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{4})|today|yesterday)"
    order_date_patterns = [
        re.compile(rf"\b(?:purchase date|order date|ordered on|purchased on|bought on|order placed|placed on)\D{{0,35}}{date_token}", re.IGNORECASE),
        re.compile(rf"\b(?:bought|purchased|ordered)\D{{0,35}}{date_token}", re.IGNORECASE),
    ]
    invoice_date_patterns = [
        re.compile(rf"\b(?:invoice date|bill date|date of invoice)\D{{0,35}}{date_token}", re.IGNORECASE),
    ]
    delivery_date_patterns = [
        re.compile(rf"\b(?:delivery date|delivered on|delivered|received on|received date)\D{{0,35}}{date_token}", re.IGNORECASE),
    ]
    complaint_date_patterns = [
        re.compile(rf"\b(?:contacted support on|customer support contacted on|complaint raised on|reported on|i contacted .*? on)\D{{0,30}}{date_token}", re.IGNORECASE),
        re.compile(rf"\bon\s+{date_token}\s+i contacted", re.IGNORECASE),
    ]

    product_patterns = [
        (
            re.compile(r"\b(?:product name|description|item|product)\s*[:#-]\s*([^\n\r]{3,140}?)(?=\s+(?:qty|quantity|price|amount|total|hsn|gst|sku|seller)\b|\n|\r|$)", re.IGNORECASE),
            0.98,
        ),
        (
            re.compile(r"\b(?:bought|purchased|ordered)\s+(?:a|an|the)?\s*([a-z0-9][a-z0-9 &._+-]{2,90}?)(?:\s+from|\s+on|\s+for|\.|,|$)", re.IGNORECASE),
            0.84,
        ),
    ]
    brand_patterns = [(re.compile(r"\bbrand\s*[:#-]\s*([^\n\r]{2,50})", re.IGNORECASE), 0.96)]
    seller_patterns = [
        (
            re.compile(r"\b(?:sold by|seller|seller name|merchant|vendor)\s*[:#-]\s*([^\n\r]{3,100}?)(?=\s+(?:billing address|shipping address|customer|recipient|gstin|phone|email)\b|\n|\r|$)", re.IGNORECASE),
            0.98,
        ),
    ]
    order_id_patterns = [
        (re.compile(r"\b(?:order id|order number|order no\.?|order #|reference id|reference number|reference no\.?)\s*[:#-]?\s*([A-Z0-9-]{4,}(?:-[A-Z0-9]{4,})*)", re.IGNORECASE), 0.99),
        (re.compile(r"\b(\d{3}-\d{7}-\d{7})\b", re.IGNORECASE), 0.98),
        (re.compile(r"\b(OD[A-Z0-9-]{5,}|ORD[A-Z0-9-]{5,}|AMZ[A-Z0-9-]{5,}|FK[A-Z0-9-]{5,}|MYN[A-Z0-9-]{5,})\b", re.IGNORECASE), 0.96),
    ]
    invoice_patterns = [
        (re.compile(r"\b(?:invoice\s*(?:number|no\.?|#|id)|inv\b\s*(?:number|no\.?|#)?)\s*[:#-]?\s*([A-Z0-9-]{4,})", re.IGNORECASE), 0.99),
    ]
    price_patterns = [
        (re.compile(r"\b(?:purchase price|price|amount|total amount|grand total|total)\s*[:#-]?\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)", re.IGNORECASE), 0.94),
        (re.compile(r"(?:rs\.?|inr|₹)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", re.IGNORECASE), 0.86),
    ]
    quantity_patterns = [(re.compile(r"\b(?:qty|quantity)\s*[:#-]?\s*(\d+)\b", re.IGNORECASE), 0.96)]
    gstin_patterns = [(re.compile(r"\bGSTIN\s*[:#-]?\s*([0-9A-Z]{15})\b", re.IGNORECASE), 0.98)]

    product_name = _first_known(_extract_confident(product_patterns, complaint), _extract_confident(product_patterns, ocr))
    seller_name = _first_known(_extract_confident(seller_patterns, complaint), _extract_confident(seller_patterns, ocr))
    price = _first_known(_extract_confident(price_patterns, complaint), _extract_confident(price_patterns, ocr)).replace(",", "")
    resolution = _first_known(_extract_resolution(complaint), _extract_resolution(ocr))
    invoice_purchase_source = invoice_ocr or (ocr if not screenshot_ocr else "")
    order_date = _select_purchase_date(
        invoice_ocr=invoice_purchase_source,
        complaint=complaint,
        screenshot_ocr=screenshot_ocr,
        current_date=current_date,
        date_token=date_token,
    )
    delivery_date = _first_known(_extract_date(delivery_date_patterns, complaint, current_date), _extract_date(delivery_date_patterns, ocr, current_date))
    complaint_date = _first_known(_extract_date(complaint_date_patterns, complaint, current_date), _extract_date(complaint_date_patterns, ocr, current_date))
    order_id = _first_known(_extract_confident(order_id_patterns, complaint), _extract_confident(order_id_patterns, ocr))
    invoice_number = _first_known(_extract_confident(invoice_patterns, complaint), _extract_confident(invoice_patterns, ocr))
    brand = _first_known(_extract_confident(brand_patterns, complaint), _extract_confident(brand_patterns, ocr))
    issue_category = _extract_issue_category(complaint or ocr, category)

    evidence = []
    if complaint.strip():
        evidence.append("Complaint text")
    if invoice_uploaded:
        evidence.append("Invoice uploaded")
    if screenshot_uploaded:
        evidence.append("Screenshot uploaded")
    if ocr.strip():
        evidence.append("OCR text extracted")
    return InvestigationFacts(
        retailer=retailer or "Unknown",
        product_name=product_name,
        brand=brand,
        order_date=order_date,
        delivery_date=delivery_date,
        complaint_date=complaint_date,
        purchase_price=price,
        seller_name=seller_name,
        order_id=order_id,
        invoice_number=invoice_number,
        quantity=_first_known(_extract_confident(quantity_patterns, complaint), _extract_confident(quantity_patterns, ocr)),
        gstin=_first_known(_extract_confident(gstin_patterns, complaint), _extract_confident(gstin_patterns, ocr)),
        resolution_requested=resolution,
        issue_category=issue_category,
        evidence=evidence,
        product=product_name,
        seller=seller_name,
        requested_resolution=resolution,
        evidence_available=evidence,
    )


def _extract_resolution(text: str) -> str:
    lowered = text.lower()
    for resolution in ["refund", "replacement", "return", "repair", "warranty", "compensation", "exchange"]:
        if resolution in lowered:
            return resolution.title()
    return "Unknown"


def _has_order_details(text: str) -> bool:
    lowered = text.lower()
    return any(pattern.search(text) for pattern in ORDER_PATTERNS) or any(term in lowered for term in ["invoice", "receipt", "order"])


def _extract_purchase_date(text: str, current_date: date) -> Optional[date]:
    lowered = text.lower()
    if "today" in lowered:
        return current_date
    if "yesterday" in lowered:
        from datetime import timedelta
        return current_date - timedelta(days=1)

    numeric = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", text)
    if numeric:
        day = int(numeric.group(1))
        month = int(numeric.group(2))
        raw_year = numeric.group(3)
        year = current_date.year if not raw_year else int(raw_year)
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            pass

    month_year = re.search(
        r"\b(" + "|".join(MONTHS.keys()) + r")\s+(\d{4})\b",
        lowered,
        re.IGNORECASE,
    )
    if month_year:
        return date(int(month_year.group(2)), MONTHS[month_year.group(1).lower()], 1)

    year_only = re.search(r"\b(?:bought|purchased|ordered|invoice|delivered)\D{0,20}((?:20)\d{2})\b", lowered)
    if year_only:
        return date(int(year_only.group(1)), 1, 1)
    return None


def analyze_timeline(text: str, current_date: date) -> TimelineAnalysis:
    purchase_date = _extract_purchase_date(text, current_date)
    findings: list[str] = []
    days_since_purchase: Optional[int] = None
    return_status = "unknown"
    warranty_status = "unknown"
    if purchase_date:
        days_since_purchase = (current_date - purchase_date).days
        if days_since_purchase <= 30:
            return_status = "valid"
            findings.append("Return window appears active based on available dates")
        else:
            return_status = "expired"
            findings.append("Return policy likely expired")
        if days_since_purchase <= 365:
            warranty_status = "valid"
            findings.append("Warranty window may still be active")
        else:
            warranty_status = "expired"
            findings.append("Warranty likely expired")
    else:
        findings.append("Purchase date not found; timeline validity cannot be verified")

    return TimelineAnalysis(
        purchase_date=purchase_date.isoformat() if purchase_date else None,
        current_date=current_date.isoformat(),
        days_since_purchase=days_since_purchase,
        return_window_status=return_status,
        warranty_window_status=warranty_status,
        findings=findings,
    )


def analyze_extracted_timeline(facts: InvestigationFacts, current_date: date) -> TimelineAnalysis:
    retailer_return_windows = {
        "amazon": 7,
        "flipkart": 7,
        "myntra": 14,
    }
    retailer_key = facts.retailer.lower()
    return_window_days = retailer_return_windows.get(retailer_key, 7)
    product_text = " ".join([facts.product_name, facts.product, facts.issue_category]).lower()
    if any(term in product_text for term in ["phone", "mobile", "laptop", "headphone", "earphone", "bluetooth", "speaker", "electronics"]):
        warranty_window_days = 365
    elif any(term in product_text for term in ["shoe", "sneaker", "sandal", "footwear"]):
        warranty_window_days = 183
    elif any(term in product_text for term in ["shirt", "t-shirt", "jeans", "dress", "clothing", "apparel"]):
        warranty_window_days = 0
    else:
        warranty_window_days = 365

    purchase_date = None
    if facts.order_date != "Unknown":
        try:
            purchase_date = date.fromisoformat(facts.order_date)
        except ValueError:
            purchase_date = None
    findings: list[str] = []
    days_since_purchase: Optional[int] = None
    return_status = "unknown"
    warranty_status = "unknown"
    if purchase_date:
        days_since_purchase = (current_date - purchase_date).days
        if days_since_purchase <= return_window_days:
            return_status = "valid"
            findings.append("Return window appears active based on extracted order date")
        else:
            return_status = "expired"
            findings.append("Return policy likely expired based on extracted order date")
        if warranty_window_days == 0:
            warranty_status = "not_applicable"
            findings.append("No manufacturer warranty is assumed for this product type")
        elif days_since_purchase <= warranty_window_days:
            warranty_status = "valid"
            findings.append("Warranty window may still be active based on extracted order date")
        else:
            warranty_status = "expired"
            findings.append("Warranty likely expired based on extracted order date")
    else:
        findings.append("Timeline will be estimated from the available details")
    return TimelineAnalysis(
        purchase_date=facts.order_date if facts.order_date != "Unknown" else None,
        current_date=current_date.isoformat(),
        return_window_days=return_window_days,
        warranty_window_days=warranty_window_days,
        days_since_purchase=days_since_purchase,
        return_window_status=return_status,
        warranty_window_status=warranty_status,
        findings=findings,
    )


def evidence_completeness(input_data: EvaluationInput, facts: InvestigationFacts) -> tuple[int, list[str], list[str]]:
    checks = [
        ("Invoice uploaded", input_data.invoice_uploaded, "Invoice uploaded", "Invoice not uploaded"),
        ("Screenshot uploaded", input_data.screenshot_uploaded, "Screenshot uploaded", "Screenshot not uploaded"),
        ("OCR extracted", bool(input_data.ocr_text.strip()), "OCR text extracted", "OCR text not extracted"),
        ("Order ID present", facts.order_id != "Unknown", "Order ID present", "Order ID missing"),
        ("Retailer identified", facts.retailer != "Unknown", "Retailer identified", "Retailer not identified"),
        ("Support communication", facts.complaint_date != "Unknown" or input_data.screenshot_uploaded, "Customer support communication available", "Customer support communication missing"),
    ]
    passed = [positive for _, ok, positive, _ in checks if ok]
    missing = [negative for _, ok, _, negative in checks if not ok]
    return round((len(passed) / len(checks)) * 100), passed, missing


def assess_evidence(input_data: EvaluationInput, timeline: TimelineAnalysis, facts: InvestigationFacts) -> list[EvidenceAssessmentItem]:
    invoice_checks = []
    invoice_score = 0
    if input_data.invoice_uploaded:
        invoice_checks.append("Invoice uploaded")
        invoice_checks.append("Purchase proof available")
        invoice_score += 40
        if facts.order_id != "Unknown" or facts.invoice_number != "Unknown" or timeline.purchase_date or facts.purchase_price != "Unknown":
            invoice_checks.append("Invoice appears authentic")
            invoice_score += 30
        if facts.product_name != "Unknown" or timeline.purchase_date or facts.purchase_price != "Unknown" or facts.seller_name != "Unknown":
            invoice_score += 20
        if input_data.ocr_text.strip():
            invoice_score += 10
    if facts.order_id != "Unknown":
        invoice_checks.append("Order ID detected")
    if facts.product_name != "Unknown":
        invoice_checks.append("Product identified")
    if timeline.purchase_date:
        invoice_checks.append("Purchase date detected")
    if facts.seller_name != "Unknown":
        invoice_checks.append("Seller identified")

    screenshot_checks = []
    screenshot_missing = []
    if input_data.screenshot_uploaded:
        screenshot_checks.append("Screenshot present")
    else:
        screenshot_missing.append("Screenshot not uploaded")
    if facts.complaint_date != "Unknown" or input_data.screenshot_uploaded:
        screenshot_checks.append("Support conversation exists")
        screenshot_checks.append("Seller response exists")
    else:
        screenshot_missing.append("Support conversation not found")
        screenshot_missing.append("Seller response not found")
    if facts.resolution_requested != "Unknown":
        screenshot_checks.append("Return or refund request exists")
    else:
        screenshot_missing.append("Return request not found")
    if timeline.purchase_date:
        screenshot_checks.append("Timeline is partially consistent")
    else:
        screenshot_missing.append("Timeline cannot be verified")

    complaint_checks = []
    complaint_missing = []
    if timeline.purchase_date or facts.delivery_date != "Unknown" or facts.complaint_date != "Unknown":
        complaint_checks.append("Timeline logical enough to evaluate")
    else:
        complaint_missing.append("Timeline details missing")
    if facts.issue_category != "Other":
        complaint_checks.append("Story appears internally consistent")
    else:
        complaint_missing.append("Possible contradictory complaint details")
    if facts.resolution_requested != "Unknown":
        complaint_checks.append("Clear resolution requested")
    else:
        complaint_missing.append("Requested resolution missing")

    def item(kind: str, checks: list[str], missing: list[str]) -> EvidenceAssessmentItem:
        total = len(checks) + len(missing)
        score = round((len(checks) / total) * 100) if total else 0
        return EvidenceAssessmentItem(evidence_type=kind, checks=checks, missing=missing, score=score)

    return [
        EvidenceAssessmentItem(
            evidence_type="Invoice",
            checks=list(dict.fromkeys(invoice_checks)),
            missing=[],
            score=min(invoice_score, 100),
        ),
        item("Screenshot", screenshot_checks, screenshot_missing),
        item("Complaint", complaint_checks, complaint_missing),
    ]


def _policy_score(evidence_sources: list[EvidenceSource]) -> tuple[float, list[str], list[str]]:
    policies = sorted(
        [source for source in evidence_sources if source.source_type.lower() == "policy"],
        key=lambda source: source.relevance_score,
        reverse=True,
    )[:3]
    if not policies:
        return 0.0, [], ["No relevant retailer policy support found"]
    score = sum(source.relevance_score * 100 for source in policies) / len(policies)
    return score, [f"{source.title} matched at {round(source.relevance_score * 100)}%" for source in policies], []


def find_negative_factors(input_data: EvaluationInput, timeline: TimelineAnalysis, facts: InvestigationFacts) -> list[str]:
    factors: list[str] = []
    if timeline.return_window_status == "expired":
        factors.append("Return window expired")
    if facts.issue_category == "Warranty Issue" and timeline.warranty_window_status == "expired":
        factors.append("Warranty expired")
    if not input_data.invoice_uploaded:
        factors.append("No invoice")
    if not input_data.screenshot_uploaded:
        factors.append("No screenshots")
    if timeline.purchase_date and timeline.days_since_purchase and timeline.days_since_purchase > 30:
        factors.append("Delayed complaint or return request")
    if facts.issue_category in {"Other", "Unknown"}:
        factors.append("Insufficient evidence of consumer-rights violation")
    return list(dict.fromkeys(factors))


def find_positive_factors(input_data: EvaluationInput, timeline: TimelineAnalysis, evidence_sources: list[EvidenceSource], facts: InvestigationFacts) -> list[str]:
    factors: list[str] = []
    if input_data.invoice_uploaded:
        factors.append("Invoice available")
    if input_data.invoice_uploaded and input_data.screenshot_uploaded:
        factors.append("Multiple supporting documents")
    if input_data.ocr_text.strip() and facts.issue_category not in {"Other", "Unknown"}:
        factors.append("OCR matches complaint")
    if timeline.return_window_status == "valid":
        factors.append("Inside likely return window")
    if facts.complaint_date != "Unknown":
        factors.append("Support or complaint date available")
    if facts.issue_category in {"Wrong Product", "Defective Product", "Damaged Product", "Counterfeit Product"}:
        factors.append(f"{facts.issue_category} issue identified")
    if any(source.source_type.lower() == "policy" for source in evidence_sources):
        factors.append("Policy supports evaluation")
    return list(dict.fromkeys(factors))


def policy_match_analysis(input_data: EvaluationInput, timeline: TimelineAnalysis, facts: InvestigationFacts) -> PolicyMatchAnalysis:
    policies = [source for source in input_data.evidence_sources if source.source_type.lower() == "policy"]
    top_policy = max(policies, key=lambda source: source.relevance_score, default=None)
    if timeline.return_window_status == "expired":
        consistency = "Retailer refusal may be consistent with standard return-window limits"
    elif timeline.return_window_status == "valid" and facts.resolution_requested != "Unknown":
        consistency = "Retailer refusal may require closer review because the return window appears active"
    elif not top_policy:
        consistency = "Unknown because no retailer policy clause was retrieved"
    else:
        consistency = "Policy relevance found, but seller response must be checked against the exact clause"
    notes = []
    if top_policy:
        notes.append(f"Top retailer policy match: {top_policy.title} at {round(top_policy.relevance_score * 100)}%")
    else:
        notes.append("No retailer policy was matched")
    notes.extend(timeline.findings)
    return PolicyMatchAnalysis(
        retailer_policy=top_policy.title if top_policy else "Unknown",
        return_window_status=timeline.return_window_status,
        warranty_status=timeline.warranty_window_status,
        retailer_response_consistency=consistency,
        notes=notes,
    )


def analysis_confidence(strength_score: int, evidence_assessments: list[EvidenceAssessmentItem], negative_factors: list[str], positive_factors: list[str]) -> int:
    avg_evidence = sum(item.score for item in evidence_assessments) / len(evidence_assessments) if evidence_assessments else 0
    certainty = 45 + (avg_evidence * 0.35)
    if strength_score <= 29 or strength_score >= 75:
        certainty += 15
    if negative_factors and positive_factors:
        certainty -= 8
    if len(negative_factors) >= 4 or len(positive_factors) >= 4:
        certainty += 8
    return max(0, min(100, round(certainty)))


def _case_strength(input_data: EvaluationInput, timeline: TimelineAnalysis, facts: InvestigationFacts) -> tuple[int, list[str], list[str], list[ScoreComponent]]:
    policy_score, policy_positive, policy_negative = _policy_score(input_data.evidence_sources)
    components: list[ScoreComponent] = []
    strong: list[str] = []
    weak: list[str] = []

    def add_component(name: str, points: float, maximum: float, explanation: str) -> None:
        bounded = max(0, min(maximum, points))
        score = round((bounded / maximum) * 100, 2) if maximum else 0
        components.append(ScoreComponent(name=name, score=score, weight=maximum / 100, contribution=round(bounded, 2), explanation=explanation))
        if bounded >= maximum * 0.70:
            strong.append(f"+{round(bounded)}% {explanation}")
        elif bounded <= maximum * 0.35:
            weak.append(f"-{round(maximum - bounded)}% {explanation}")
        else:
            strong.append(f"+{round(bounded)}% Partial support: {explanation}")

    complaint_points = 0.0
    complaint_notes: list[str] = []
    if facts.issue_category not in {"Other", "Unknown"}:
        complaint_points += 10
        complaint_notes.append("issue is clearly described")
    if facts.product_name != "Unknown" and facts.resolution_requested != "Unknown":
        complaint_points += 8
        complaint_notes.append("product and requested resolution are clear")
    if facts.resolution_requested != "Unknown":
        complaint_points += 6
        complaint_notes.append("requested resolution is stated")
    if facts.order_id != "Unknown" or facts.product_name != "Unknown":
        complaint_points += 6
        complaint_notes.append("product or order details are present")
    add_component("Complaint Quality", complaint_points, 30, ", ".join(complaint_notes) or "complaint lacks enough decision-ready facts")

    invoice_points = 0.0
    invoice_notes: list[str] = []
    if input_data.invoice_uploaded:
        invoice_points += 8
        invoice_notes.append("invoice uploaded")
    if input_data.ocr_text.strip():
        invoice_points += 4
        invoice_notes.append("OCR text extracted")
    if facts.order_id != "Unknown" or facts.invoice_number != "Unknown":
        invoice_points += 4
        invoice_notes.append("order or invoice ID found")
    if timeline.purchase_date:
        invoice_points += 2
        invoice_notes.append("order date found")
    if facts.seller_name != "Unknown" or facts.product_name != "Unknown":
        invoice_points += 2
        invoice_notes.append("seller or product can be checked")
    add_component("Invoice Verification", invoice_points, 20, ", ".join(invoice_notes) or "invoice verification is missing")

    timeline_points = 0.0
    if timeline.return_window_status == "valid":
        timeline_points = 20
        timeline_note = "return window appears active and timeline is consistent"
    elif timeline.return_window_status == "expired":
        timeline_points = 0
        timeline_note = "return window likely expired"
    elif timeline.purchase_date:
        timeline_points = 10
        timeline_note = "purchase date exists but timeline is uncertain"
    else:
        timeline_points = 5
        timeline_note = "timeline cannot be verified"
    add_component("Timeline", timeline_points, 20, timeline_note)

    support_points = 0.0
    support_notes: list[str] = []
    if input_data.screenshot_uploaded:
        support_points += 5
        support_notes.append("screenshot uploaded")
    if facts.complaint_date != "Unknown" or input_data.screenshot_uploaded:
        support_points += 5
        support_notes.append("customer support communication is mentioned")
    if facts.resolution_requested != "Unknown" and input_data.screenshot_uploaded:
        support_points += 5
        support_notes.append("seller or platform response is described")
    add_component("Customer Support Evidence", support_points, 15, ", ".join(support_notes) or "support response evidence is missing")

    if input_data.retailer and policy_score > 0:
        policy_points = min(15, policy_score * 0.15)
        policy_note = ", ".join(policy_positive)
    else:
        policy_points = 0
        policy_note = "no relevant retailer policy match found"
    add_component("Policy Match", policy_points, 15, policy_note)

    for factor in find_negative_factors(input_data, timeline, facts):
        message = f"- {factor}"
        if message not in weak:
            weak.append(message)
    weak.extend(policy_negative)
    score = max(0, min(100, round(sum(component.contribution for component in components))))
    return score, strong, weak, components


def recommended_actions_for_verdict(verdict: str, weak_factors: list[str]) -> tuple[list[Recommendation], str, str, str]:
    if verdict.startswith("🟢"):
        next_action = "Escalate with the seller or platform using the invoice, evidence, and matched policy clauses."
        actions = [
            Recommendation(action="Escalate Support Ticket", reason="The evidence and policy support indicate a strong claim.", evidence="Matched retailer policy and legal clauses"),
            Recommendation(action="Prepare Complaint Letter", reason="A formal written record is appropriate for a strong claim.", evidence="Case analysis breakdown"),
            Recommendation(action="Consider Consumer Helpline", reason="Use if platform escalation does not resolve the issue.", evidence="Consumer protection sources"),
        ]
    elif verdict.startswith("🟡"):
        next_action = "Gather missing evidence, then raise or update the platform complaint."
        actions = [
            Recommendation(action="Gather More Evidence", reason="The claim has some support but missing evidence may reduce success.", evidence=", ".join(weak_factors[:3]) or "Missing evidence list"),
            Recommendation(action="Draft Complaint", reason="A measured complaint can be sent after adding documentation.", evidence="Available complaint facts"),
        ]
    elif verdict.startswith("🟠"):
        next_action = "Review retailer policy and collect stronger proof before escalating."
        actions = [
            Recommendation(action="Review Retailer Policy", reason="Success may be difficult based on current facts.", evidence=", ".join(weak_factors[:3]) or "Weak-factor analysis"),
            Recommendation(action="Collect Proof", reason="Add invoice, order ID, support chat, product photos, and timeline details.", evidence="Missing evidence list"),
        ]
    else:
        next_action = "Review retailer return or warranty policy before pursuing escalation. Additional legal action is unlikely to succeed based on available information."
        actions = [
            Recommendation(action="Review Policy Before Escalation", reason="Based on the available information, the likelihood of a successful consumer-rights claim appears low.", evidence=", ".join(weak_factors[:4]) or "Insufficient evidence"),
        ]
    should_generate_draft = verdict.startswith("🟢") or verdict.startswith("🟡")
    email = "" if not should_generate_draft else "Subject: Consumer complaint follow-up\n\nHello Support Team,\n\nI am requesting review of my consumer complaint based on the attached evidence and applicable policy terms.\n\nRegards"
    letter = "" if not should_generate_draft else "To Whom It May Concern,\n\nI am submitting this consumer complaint with supporting evidence and request a fair review under applicable policy and consumer protection principles."
    return actions, next_action, email, letter


class ScoringService:
    """Encapsulates deterministic case-strength, evidence, verdict, and timeline rules."""

    def calculateCaseStrength(self, input_data: EvaluationInput) -> EvaluationResult:
        facts = input_data.extracted_facts or extract_structured_information(
            input_data.complaint_text,
            input_data.ocr_text,
            category=input_data.category,
            retailer=input_data.retailer,
            invoice_uploaded=input_data.invoice_uploaded,
            screenshot_uploaded=input_data.screenshot_uploaded,
            current_date=input_data.current_date,
        )
        timeline = self._evaluateTimeline(facts, input_data.current_date)
        evidence_score, evidence_positive, evidence_missing = self._evaluateEvidence(input_data, facts)
        strength_score, strong, weak, components = self._calculateStrength(input_data, timeline, facts)
        evidence_assessment = assess_evidence(input_data, timeline, facts)
        negative_factors = find_negative_factors(input_data, timeline, facts)
        positive_factors = find_positive_factors(input_data, timeline, input_data.evidence_sources, facts)
        confidence = analysis_confidence(strength_score, evidence_assessment, negative_factors, positive_factors)
        verdict = self.calculateVerdict(strength_score)
        actions, next_action, email, letter = recommended_actions_for_verdict(verdict, weak)
        explanation = CaseStrengthExplanation(
            components=components,
            strong_contributors=strong,
            weak_factors=weak,
            missing_evidence=[f"-{item}" for item in evidence_missing],
        )
        if evidence_positive:
            explanation.strong_contributors = [*evidence_positive, *explanation.strong_contributors]
        return EvaluationResult(
            evidence_completeness_score=evidence_score,
            consumer_case_strength_score=strength_score,
            case_verdict=verdict,
            timeline_analysis=timeline,
            explanation=explanation,
            analysis_confidence_score=confidence,
            investigation_facts=facts,
            evidence_assessment=evidence_assessment,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            policy_match_analysis=policy_match_analysis(input_data, timeline, facts),
            recommended_actions=actions,
            recommended_next_action=next_action,
            email_draft=email,
            complaint_letter=letter,
        )

    def calculateEvidenceScore(self, input_data: EvaluationInput) -> int:
        facts = input_data.extracted_facts or extract_structured_information(
            input_data.complaint_text,
            input_data.ocr_text,
            category=input_data.category,
            retailer=input_data.retailer,
            invoice_uploaded=input_data.invoice_uploaded,
            screenshot_uploaded=input_data.screenshot_uploaded,
            current_date=input_data.current_date,
        )
        score, _, _ = self._evaluateEvidence(input_data, facts)
        return score

    def calculateVerdict(self, score: int) -> str:
        return verdict_for_score(score)

    def _evaluateTimeline(self, facts: InvestigationFacts, current_date: date) -> TimelineAnalysis:
        return analyze_extracted_timeline(facts, current_date)

    def _evaluatePolicyMatch(self, evidence_sources: list[EvidenceSource]) -> tuple[float, list[str], list[str]]:
        return _policy_score(evidence_sources)

    def _evaluateEvidence(self, input_data: EvaluationInput, facts: InvestigationFacts) -> tuple[int, list[str], list[str]]:
        return evidence_completeness(input_data, facts)

    def _calculateStrength(self, input_data: EvaluationInput, timeline: TimelineAnalysis, facts: InvestigationFacts) -> tuple[int, list[str], list[str], list[ScoreComponent]]:
        return _case_strength(input_data, timeline, facts)


scoring_service = ScoringService()
