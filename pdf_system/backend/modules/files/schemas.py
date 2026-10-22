"""文件模块的输入输出（负责人：乙）。"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileOut(BaseModel):
    id: str
    name: str
    folder: str
    media_type: str
    size: int
    page_count: int
    version: int
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


class FileUpdate(StrictModel):
    name: str | None = Field(default=None, max_length=255)
    folder: str | None = Field(default=None, max_length=255)
    tags: list[str] | None = Field(default=None, max_length=20)


class PageOut(BaseModel):
    """阅读器契约 C4：前端据此渲染覆盖层。"""
    page_no: int
    width_pt: float
    height_pt: float
    rotation: int = 0
