"""add projects module

Revision ID: add_projects_module
Revises: add_key_points_analysis
Create Date: 2026-07-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "add_projects_module"
down_revision: Union[str, None] = "add_key_points_analysis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS projects")

    op.create_table(
        "tracked_repos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("github_repo_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("private", sa.Boolean(), server_default="false"),
        sa.Column("notion_page_id", sa.String(64), nullable=True),
        sa.Column("webhook_id", sa.BigInteger(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("owner_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("last_synced_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now()),
        schema="projects",
    )

    op.create_table(
        "repo_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tracked_repo_id",
            sa.Integer(),
            sa.ForeignKey("projects.tracked_repos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("github_ref", sa.String(255), nullable=True),
        sa.Column("actor", sa.String(100), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.Column("notion_synced_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("discord_sent_at", sa.TIMESTAMP(), nullable=True),
        schema="projects",
    )


def downgrade() -> None:
    op.drop_table("repo_events", schema="projects")
    op.drop_table("tracked_repos", schema="projects")
    op.execute("DROP SCHEMA IF EXISTS projects CASCADE")

