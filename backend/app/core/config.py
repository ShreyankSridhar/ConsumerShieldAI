from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "ConsumerSheildAI"
    api_prefix: str = "/api"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    chroma_path: Path = PROJECT_ROOT / "database" / "chroma"
    sqlite_path: Path = PROJECT_ROOT / "database" / "consumersheildai.db"
    uploads_dir: Path = PROJECT_ROOT / "uploads"
    knowledge_base_dir: Path = PROJECT_ROOT / "knowledge_base"
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    allowed_origin_regex: str = (
        r"^https?://("
        r"localhost|127\.0\.0\.1|"
        r"10\.\d+\.\d+\.\d+|"
        r"192\.168\.\d+\.\d+|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+"
        r"):3000$"
    )

    class Config:
        env_file = ".env"
        env_prefix = "CONSUMERSHEILDAI_"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
