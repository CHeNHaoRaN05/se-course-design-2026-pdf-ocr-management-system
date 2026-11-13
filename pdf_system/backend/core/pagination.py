"""Typed optional page envelopes; legacy array clients remain compatible."""
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
