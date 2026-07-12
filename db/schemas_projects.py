from datetime import datetime
from pydantic import BaseModel


# ── Tracked repos ──────────────────────────────────────────

class TrackedRepoOut(BaseModel):
    id: int
    full_name: str
    private: bool
    notion_page_id: str | None
    active: bool
    last_synced_at: datetime | None
    created_at: datetime
    class Config:
        from_attributes = True


class TrackedRepoUpdate(BaseModel):
    active: bool | None = None
    notion_page_id: str | None = None


# ── Repo events ─────────────────────────────────────────────

class RepoEventOut(BaseModel):
    id: int
    tracked_repo_id: int
    event_type: str
    github_ref: str | None
    summary: str
    url: str | None
    detected_at: datetime
    class Config:
        from_attributes = True

