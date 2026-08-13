from dataclasses import dataclass
from typing import Optional

from rag.document_loader import KnowledgeDocument


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    title: str
    source_type: str
    retailer: Optional[str]
    content: str


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    normalized = " ".join(text.split())
    if len(normalized) <= chunk_size:
        return [normalized]
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def chunk_documents(documents: list[KnowledgeDocument]) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for document in documents:
        for index, content in enumerate(chunk_text(document.content)):
            chunks.append(
                DocumentChunk(
                    id=f"{document.path.stem}-{index}",
                    title=document.title,
                    source_type=document.source_type,
                    retailer=document.retailer,
                    content=content,
                )
            )
    return chunks
