"""书签与批注（负责人：乙）。

坐标口径与 OCR bbox 一致：归一化左上原点 [left, top, right, bottom]（契约 C4）。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BookmarkIn(StrictModel):
    page_no: int = Field(ge=1)
    title: str = Field(default="", max_length=120)


class BookmarkOut(BaseModel):
    id: str
    page_no: int
    title: str
    created_at: datetime


class AnnotationIn(StrictModel):
    page_no: int = Field(ge=1)
    kind: str = Field(default="note", pattern="^(highlight|note|ink)$")
    text: str = Field(default="", max_length=5000)
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)


class AnnotationOut(BaseModel):
    id: str
    page_no: int
    kind: str
    payload: dict
    created_at: datetime
    updated_at: datetime
