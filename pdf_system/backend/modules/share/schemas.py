"""分享链接视图模型（负责人：甲）。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShareCreate(StrictModel):
    file_id: str
    expires_at: datetime | None = None
    access_code: str | None = Field(default=None, max_length=32)
    allow_download: bool = True


class ShareOut(BaseModel):
    id: str
    file_id: str
    token: str
    share_url: str
    expires_at: datetime | None
    access_code: str | None
    allow_download: bool
    visit_count: int
    created_at: datetime


class ShareStats(BaseModel):
    id: str
    file_id: str
    visit_count: int
    allow_download: bool
    expires_at: datetime | None
    created_at: datetime
