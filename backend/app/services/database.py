from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from backend.app.core.config import get_settings


class Base(DeclarativeBase):
    pass


class CaseRecord(Base):
    __tablename__ = "anonymous_case_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    anonymous_session_id: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(80))
    case_strength_score: Mapped[int] = mapped_column(Integer)
    evidence_score: Mapped[int] = mapped_column(Integer, default=0)
    policy_matches: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


settings = get_settings()


class DatabaseService:
    """Wraps SQLite access behind public persistence methods."""

    def __init__(self) -> None:
        self._engine = create_engine(f"sqlite:///{settings.sqlite_path}", connect_args={"check_same_thread": False})

    def initialize(self) -> None:
        Base.metadata.create_all(bind=self._engine)

    def saveCase(
        self,
        category: str,
        case_strength_score: int,
        evidence_score: int,
        policy_matches: list[str],
        anonymous_session_id: Optional[str] = None,
    ) -> None:
        self.initialize()
        with Session(self._engine) as session:
            session.add(
                CaseRecord(
                    category=category,
                    case_strength_score=case_strength_score,
                    evidence_score=evidence_score,
                    policy_matches=", ".join(policy_matches[:5]),
                    anonymous_session_id=anonymous_session_id or uuid4().hex,
                )
            )
            session.commit()


database_service = DatabaseService()


def init_db() -> None:
    database_service.initialize()
