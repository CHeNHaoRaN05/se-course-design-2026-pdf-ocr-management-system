"""分享链接视图模型（负责人：甲）。"""
from datetime import datetime

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShareCreate(StrictModel):
    file_id: str
    expires_at: datetime | None = None
    expires_in_days: Literal[1, 7, 30] | None = None
    access_code: str | None = Field(default=None, max_length=32)
    allow_download: bool = True

    @field_validator("access_code")
    @classmethod
    def visible_code(cls, value):
        if value is None or value == "":
            return None
        if not value.isascii() or not value.isalnum():
            raise ValueError("提取码只允许1至32位字母和数字")
        return value

    @model_validator(mode="after")
    def expiry_input(self):
        if self.expires_at is not None and self.expires_in_days is not None:
            raise ValueError("有效期不能同时使用绝对时间和相对天数")
        return self



class ShareOut(BaseModel):
    id: str
    file_id: str
    token: str
    share_url: str
    expired: bool = False
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
