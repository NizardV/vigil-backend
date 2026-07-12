import uuid
from datetime import datetime
from sqlalchemy import (
    Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.session import Base


# ── Projects : monitoring GitHub → sync Notion → digest Discord ──
# Schema dédié "projects" (Phase 1 : pas de FK cross-module,
# uniquement des références UUID "soft" vers les autres modules)

class TrackedRepo(Base):
    __tablename__ = "tracked_repos"
    __table_args__ = {"schema": "projects"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_repo_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)  # "owner/repo"
    private: Mapped[bool] = mapped_column(Boolean, default=False)
    notion_page_id: Mapped[str | None] = mapped_column(String(64))
    webhook_id: Mapped[int | None] = mapped_column(BigInteger)  # id du hook côté GitHub
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Soft ref vers un éventuel user du module Auth — jamais de FK cross-module
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    events: Mapped[list["RepoEvent"]] = relationship(back_populates="repo", cascade="all, delete")


class RepoEvent(Base):
    __tablename__ = "repo_events"
    __table_args__ = {"schema": "projects"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracked_repo_id: Mapped[int] = mapped_column(
        ForeignKey("projects.tracked_repos.id", ondelete="CASCADE")
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)  # push, pull_request, issues, release
    github_ref: Mapped[str | None] = mapped_column(String(255))  # sha court, "#12", tag...
    actor: Mapped[str | None] = mapped_column(String(100))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    notion_synced_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    discord_sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)

    repo: Mapped["TrackedRepo"] = relationship(back_populates="events")

