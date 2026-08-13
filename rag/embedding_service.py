import hashlib
import math

from google import genai

from backend.app.core.config import get_settings


def _hash_embedding(text: str, dimensions: int = 384) -> list[float]:
    vector = [0.0] * dimensions
    tokens = text.lower().split()
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class EmbeddingService:
    """Hides Gemini embedding calls and local fallback vector generation."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._apiKey = self._settings.gemini_api_key
        self._model = self._settings.gemini_embedding_model
        self._client = genai.Client(api_key=self._apiKey) if self._apiKey else None

    def embedTexts(self, texts: list[str]) -> list[list[float]]:
        if self._client is None:
            return [_hash_embedding(text) for text in texts]

        embeddings: list[list[float]] = []
        for text in texts:
            response = self._client.models.embed_content(model=self._model, contents=text)
            embeddings.append(response.embeddings[0].values)
        return embeddings

    def embedQuery(self, text: str) -> list[float]:
        return self.embedTexts([text])[0]


embedding_service = EmbeddingService()
