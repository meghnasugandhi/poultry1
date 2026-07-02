from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None


class RAGChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    if PGVECTOR_AVAILABLE:
        embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_rag_chunks_user_embedding", "user_id", "embedding", postgresql_using="ivfflat"),
    ) if PGVECTOR_AVAILABLE else ()