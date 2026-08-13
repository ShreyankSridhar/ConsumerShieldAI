from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.app.core.config import get_settings


@dataclass(frozen=True)
class KnowledgeDocument:
    title: str
    source_type: str
    retailer: Optional[str]
    path: Path
    content: str


def load_documents(base_dir: Optional[Path] = None) -> list[KnowledgeDocument]:
    settings = get_settings()
    root = base_dir or settings.knowledge_base_dir
    documents: list[KnowledgeDocument] = []
    for path in sorted(root.rglob("*.md")):
        relative_parts = path.relative_to(root).parts
        if not relative_parts or relative_parts[0] not in {"policies", "legal"}:
            continue
        text = path.read_text(encoding="utf-8")
        title = path.stem.replace("_", " ").title()
        parts = {part.lower() for part in relative_parts}
        retailer = next((name for name in ("amazon", "flipkart", "myntra") if name in parts), None)
        source_type = "Policy" if retailer else "Legal"
        documents.append(KnowledgeDocument(title=title, source_type=source_type, retailer=retailer, path=path, content=text))
    return documents
