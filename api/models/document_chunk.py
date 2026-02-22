"""
SQLAlchemy model for the chat.document_chunk table — stores embedded text
chunks for RAG vector search.
"""

from sqlalchemy import Column, DateTime, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from api.db.database import Base


class DocumentChunk(Base):
    """Embedded text chunk for RAG retrieval (lives in the 'chat' schema)."""

    __tablename__ = "document_chunk"
    __table_args__ = (
        Index("ix_document_chunk_source", "source"),
        {"schema": "chat"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    # The embedding column is vector(2000), managed via raw SQL in the migration.
    # SQLAlchemy doesn't natively support the pgvector type, so we read/write
    # it through raw SQL in the tool functions.
    metadata_ = Column("metadata_", JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
