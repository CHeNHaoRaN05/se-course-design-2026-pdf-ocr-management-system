from typing import Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class JobCreate(StrictModel):
    file_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    pages: list[int] | None = Field(default=None, min_length=1, max_length=100)
    mode: Literal["general", "handwriting"] = "general"
    recognition_model: Literal["official", "custom"] = "official"
    dpi: int = Field(default=144, ge=72, le=240)
    tables: bool = False
    min_confidence: float = Field(default=0.5, ge=0, le=1)


class Block(StrictModel):
    id: int = Field(ge=1)
    text: str = Field(max_length=10000)
    confidence: float = Field(ge=0, le=1)
    bbox: list[float] = Field(min_length=4, max_length=4)
    needs_review: bool = True

    @model_validator(mode="after")
    def bounds(self):
        x1, y1, x2, y2 = self.bbox
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError("bbox must be normalized [left, top, right, bottom]")
        return self


class Correction(StrictModel):
    expected_revision: int = Field(ge=1)
    blocks: list[Block] = Field(max_length=2000)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({b.id for b in self.blocks}) != len(self.blocks):
            raise ValueError("block ids must be unique")
        if sum(len(b.text) for b in self.blocks) > 200000:
            raise ValueError("page text exceeds 200000 characters")
        return self


class FileOut(BaseModel):
    id: str
    name: str
    media_type: str
    size: int
    page_count: int
    created_at: datetime


class Progress(BaseModel):
    total: int
    succeeded: int
    failed: int
    percent: float


class PageStatus(BaseModel):
    page_no: int
    status: Literal["pending", "succeeded", "failed"]
    error: str | None = None


class JobOut(BaseModel):
    id: str
    file_id: str
    status: Literal["queued", "running", "retry_wait", "succeeded", "partial_success", "failed", "cancelled"]
    options: dict
    attempts: int
    progress: Progress
    pages: list[PageStatus]
    created_at: datetime
    finished_at: datetime | None


class OCRResult(BaseModel):
    width: int
    height: int
    blocks: list[Block]
    text: str
    tables: list[dict]
    corrected: bool
    image_key: str
    coordinate_system: str
    mode: str | None = None
    recognition_model: str | None = None
    warnings: list[str] = Field(default_factory=list)


class PageOut(PageStatus):
    revision: int
    result: OCRResult | None


class SearchHit(BaseModel):
    file_id: str
    file_name: str
    page_no: int
    job_id: str
    revision: int
    snippet: str


class SearchOut(BaseModel):
    backend: Literal["mysql_ngram", "substring"]
    items: list[SearchHit]

