"""add_chat_schema_and_document_chunk

Revision ID: 60e70b6b0b95
Revises: e78aaf5728f6
Create Date: 2026-02-21 20:00:00.000000

"""

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision: str = "60e70b6b0b95"
down_revision: Union[str, Sequence[str], None] = "e78aaf5728f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    logger.info("Ensured pgvector extension exists")

    conn.execute(sa.text("CREATE SCHEMA IF NOT EXISTS chat"))
    logger.info("Ensured chat schema exists")

    op.create_table(
        "document_chunk",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadata_", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="chat",
    )

    # pgvector's vector type isn't natively supported by SQLAlchemy —
    # add the embedding column and HNSW index via raw SQL.
    conn.execute(
        sa.text(
            "ALTER TABLE chat.document_chunk "
            "ADD COLUMN embedding vector(2000)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX ix_document_chunk_embedding "
            "ON chat.document_chunk USING hnsw (embedding vector_cosine_ops)"
        )
    )

    op.create_index(
        "ix_document_chunk_source",
        "document_chunk",
        ["source"],
        schema="chat",
    )

    logger.info("Created chat.document_chunk table with HNSW index")


def downgrade() -> None:
    op.drop_index(
        "ix_document_chunk_source", table_name="document_chunk", schema="chat"
    )
    op.execute("DROP INDEX IF EXISTS chat.ix_document_chunk_embedding")
    op.drop_table("document_chunk", schema="chat")
    op.execute("DROP SCHEMA IF EXISTS chat CASCADE")
    op.execute("DROP EXTENSION IF EXISTS vector")
