"""注册登录与用户视图（负责人：甲）。"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterIn(StrictModel):
    email: str = Field(min_length=3, max_length=190, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=64)


class LoginIn(StrictModel):
    email: str = Field(min_length=3, max_length=190)
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: Literal["user", "viewer", "admin"]


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    created_at: datetime


class RoleUpdate(StrictModel):
    role: Literal["user", "viewer", "admin"]


class ChangePasswordIn(StrictModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
