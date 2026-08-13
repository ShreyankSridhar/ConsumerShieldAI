import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Optional

from backend.app.models.schemas import EvidenceSource
from backend.app.core.config import get_settings
from rag.chunker import chunk_documents
from rag.document_loader import load_documents
from rag.embedding_service import EmbeddingService


LEGAL_COLLECTION_NAME = "legal_consumer_rights"
POLICY_COLLECTION_PREFIX = "policy"
SUPPORTED_RETAILERS = ("amazon", "flipkart", "myntra")


class ChromaService:
    """Encapsulates ChromaDB client, collections, and embedding generation."""

    def __init__(self, embedding_model: Optional[EmbeddingService] = None) -> None:
        self._settings = get_settings()
        self._client = chromadb.PersistentClient(
            path=str(self._settings.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = None
        self._embeddingModel = embedding_model or EmbeddingService()

    def addDocument(self, collection_name: str, document_id: str, content: str, metadata: dict[str, str]) -> None:
        collection = self._getCollection(collection_name)
        collection.add(
            ids=[document_id],
            documents=[content],
            embeddings=self._embeddingModel.embedTexts([content]),
            metadatas=[metadata],
        )

    def searchDocuments(self, collection_name: str, query: str, limit: int = 3) -> list[EvidenceSource]:
        collection = self._getCollection(collection_name)
        if collection.count() == 0:
            return []
        results = collection.query(query_embeddings=[self._embeddingModel.embedQuery(query)], n_results=limit)
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        return [self._toEvidenceSource(document, metadata, distance) for document, metadata, distance in zip(documents, metadatas, distances)]

    def deleteDocument(self, collection_name: str, document_id: str) -> None:
        self._getCollection(collection_name).delete(ids=[document_id])

    def getCollectionStats(self, collection_name: str) -> dict[str, object]:
        collection = self._getCollection(collection_name)
        return {"collection": collection_name, "count": collection.count()}

    def seed(self, force: bool = False) -> int:
        chunks = chunk_documents(load_documents())
        if not chunks:
            return 0

        collections = [self._legalCollectionName(), *(self._policyCollectionName(retailer) for retailer in SUPPORTED_RETAILERS)]
        if not force and all(self._getCollection(name).count() for name in collections):
            return sum(self._getCollection(name).count() for name in collections)

        total = 0
        legal_chunks = [chunk for chunk in chunks if chunk.source_type == "Legal"]
        total += self._replaceCollection(self._legalCollectionName(), legal_chunks)
        for retailer in SUPPORTED_RETAILERS:
            policy_chunks = [chunk for chunk in chunks if chunk.source_type == "Policy" and chunk.retailer == retailer]
            total += self._replaceCollection(self._policyCollectionName(retailer), policy_chunks)
        return total

    def policyCollectionName(self, retailer: str) -> str:
        return self._policyCollectionName(retailer)

    def legalCollectionName(self) -> str:
        return self._legalCollectionName()

    def _getCollection(self, name: str):
        self._collection = self._client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
        return self._collection

    def _replaceCollection(self, collection_name: str, chunks) -> int:
        collection = self._getCollection(collection_name)
        if collection.count():
            ids = collection.get()["ids"]
            if ids:
                collection.delete(ids=ids)
        if not chunks:
            return 0
        collection.add(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            embeddings=self._embeddingModel.embedTexts([chunk.content for chunk in chunks]),
            metadatas=[
                {"title": chunk.title, "source_type": chunk.source_type, "retailer": chunk.retailer or ""}
                for chunk in chunks
            ],
        )
        return collection.count()

    def _toEvidenceSource(self, document: str, metadata: dict, distance: float) -> EvidenceSource:
        relevance = max(0.0, min(1.0, 1.0 - float(distance or 0.0)))
        retailer = str(metadata.get("retailer") or "") or None
        return EvidenceSource(
            title=str(metadata.get("title", "Consumer Rights Source")),
            source_type=str(metadata.get("source_type", "Policy")),
            retailer=retailer,
            content=document,
            relevance_score=round(relevance, 3),
        )

    def _policyCollectionName(self, retailer: str) -> str:
        return f"{POLICY_COLLECTION_PREFIX}_{retailer}"

    def _legalCollectionName(self) -> str:
        return LEGAL_COLLECTION_NAME


chroma_service = ChromaService()
