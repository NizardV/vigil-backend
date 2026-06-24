import uuid
from datetime import datetime
from sqlalchemy import (
    Integer, String, Text, Boolean, Float,
    SmallInteger, TIMESTAMP, ARRAY, ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from db.session import Base


# ── Auth ─────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    totp_secret: Mapped[str | None] = mapped_column(String(64))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    oauth_provider: Mapped[str | None] = mapped_column(String(20))
    oauth_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    themes: Mapped[list["Theme"]] = relationship(back_populates="user", cascade="all, delete")
    webhooks: Mapped[list["Webhook"]] = relationship(back_populates="user", cascade="all, delete")
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="user", cascade="all, delete")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete")
    verification_tokens: Mapped[list["EmailVerificationToken"]] = relationship(back_populates="user", cascade="all, delete")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="verification_tokens")


# ── Themes ───────────────────────────────────────────────

class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    digest_hour: Mapped[int] = mapped_column(Integer, default=7)
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="themes")
    sources: Mapped[list["Source"]] = relationship(back_populates="theme", cascade="all, delete")
    digests: Mapped[list["Digest"]] = relationship(back_populates="theme")
    webhooks: Mapped[list["Webhook"]] = relationship(back_populates="theme", cascade="all, delete")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    theme_id: Mapped[int] = mapped_column(ForeignKey("themes.id", ondelete="CASCADE"))
    name: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="rss")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    fetch_interval_hours: Mapped[int] = mapped_column(Integer, default=2)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    theme: Mapped["Theme"] = relationship(back_populates="sources")
    articles: Mapped[list["Article"]] = relationship(back_populates="source", cascade="all, delete")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    content_raw: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    source: Mapped["Source"] = relationship(back_populates="articles")
    analysis: Mapped["Analysis | None"] = relationship(back_populates="article", uselist=False, cascade="all, delete")
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="article", cascade="all, delete")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), unique=True)
    summary: Mapped[str | None] = mapped_column(Text)
    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        CheckConstraint("relevance_score BETWEEN 1 AND 10")
    )
    theme_match: Mapped[str | None] = mapped_column(String(100))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    llm_prompt_version: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    article: Mapped["Article"] = relationship(back_populates="analysis")
    key_points: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(
        SmallInteger,
        CheckConstraint("rating IN (-1, 1)")
    )
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="feedbacks")
    article: Mapped["Article"] = relationship(back_populates="feedbacks")


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    theme_id: Mapped[int] = mapped_column(ForeignKey("themes.id"))
    content: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    channel: Mapped[str] = mapped_column(String(50), default="discord")

    theme: Mapped["Theme"] = relationship(back_populates="digests")


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    theme_id: Mapped[int] = mapped_column(ForeignKey("themes.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="discord")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="webhooks")
    theme: Mapped["Theme"] = relationship(back_populates="webhooks")