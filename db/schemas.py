from datetime import datetime
from pydantic import BaseModel, HttpUrl


# ── Themes ──────────────────────────────────────────────

class ThemeCreate(BaseModel):
    name: str
    description: str | None = None
    keywords: list[str] | None = None

class ThemeOut(ThemeCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ── Sources ─────────────────────────────────────────────

class SourceCreate(BaseModel):
    theme_id: int
    name: str | None = None
    url: str
    type: str = "rss"
    active: bool = True

class SourceOut(SourceCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ── Articles ─────────────────────────────────────────────

class AnalysisOut(BaseModel):
    summary: str | None
    relevance_score: float | None
    theme_match: str | None
    created_at: datetime
    class Config:
        from_attributes = True

class ArticleOut(BaseModel):
    id: int
    title: str
    url: str
    published_at: datetime | None
    fetched_at: datetime
    processed: bool
    analysis: AnalysisOut | None = None
    class Config:
        from_attributes = True


# ── Feedback ─────────────────────────────────────────────

class FeedbackCreate(BaseModel):
    article_id: int
    rating: int   # 1 ou -1
    comment: str | None = None

class FeedbackOut(FeedbackCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ── Digests ──────────────────────────────────────────────

class DigestOut(BaseModel):
    id: int
    theme_id: int
    content: str | None
    sent_at: datetime
    channel: str
    class Config:
        from_attributes = True


# ── Webhooks ─────────────────────────────────────────────

class WebhookCreate(BaseModel):
    theme_id: int
    url: str
    type: str = "discord"
    active: bool = True

class WebhookOut(WebhookCreate):
    id: int
    class Config:
        from_attributes = True

