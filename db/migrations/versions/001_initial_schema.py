"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "themes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("keywords", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now()),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("theme_id", sa.Integer(), sa.ForeignKey("themes.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("type", sa.String(20), server_default="rss"),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now()),
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), unique=True, nullable=False),
        sa.Column("content_raw", sa.Text(), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("fetched_at", sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.Column("processed", sa.Boolean(), server_default="false"),
    )

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), unique=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("relevance_score", sa.Float(), sa.CheckConstraint("relevance_score BETWEEN 1 AND 10"), nullable=True),
        sa.Column("theme_match", sa.String(100), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("llm_prompt_version", sa.String(20), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now()),
    )

    # Performance indexes
    op.create_index("ix_analyses_score", "analyses", ["relevance_score"])
    op.execute("CREATE INDEX ix_analyses_embedding ON analyses USING ivfflat (embedding vector_cosine_ops)")

    op.create_table(
        "feedbacks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE")),
        sa.Column("rating", sa.SmallInteger(), sa.CheckConstraint("rating IN (-1, 1)"), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now()),
    )

    op.create_table(
        "digests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("theme_id", sa.Integer(), sa.ForeignKey("themes.id")),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.Column("channel", sa.String(50), server_default="discord"),
    )

    op.create_table(
        "webhooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("theme_id", sa.Integer(), sa.ForeignKey("themes.id", ondelete="CASCADE")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("type", sa.String(20), server_default="discord"),
        sa.Column("active", sa.Boolean(), server_default="true"),
    )


def downgrade() -> None:
    op.drop_table("webhooks")
    op.drop_table("digests")
    op.drop_table("feedbacks")
    op.drop_index("ix_analyses_embedding")
    op.drop_index("ix_analyses_score")
    op.drop_table("analyses")
    op.drop_table("articles")
    op.drop_table("sources")
    op.drop_table("themes")
    op.execute("DROP EXTENSION IF EXISTS vector")