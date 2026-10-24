"""密码散列与 JWT 签发（负责人：甲）。

JWT 的 claims 必须满足 OCR 模块的强制要求：sub / exp / iat / iss / aud（契约 C1）。
密码使用标准库 PBKDF2-HMAC-SHA256，避免额外依赖；生产环境可替换为 argon2/bcrypt。
"""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os

import jwt

PBKDF2_ROUNDS = 200_000


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(plain: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        algo, rounds, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(expected.hex(), digest)
    except (ValueError, TypeError):
        return False


def create_access_token(*, user_id: str, role: str, secret: str, issuer: str, audience: str,
                        expire_minutes: int, jti: str | None = None,
                        token_version: int | None = None) -> str:
    issued = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "role": role,
        "iss": issuer,
        "aud": audience,
        "iat": issued,
        "exp": issued + timedelta(minutes=expire_minutes),
    }
    if jti is not None:
        claims["jti"] = jti
    if token_version is not None:
        claims["tv"] = token_version
    return jwt.encode(claims, secret, algorithm="HS256")


def decode_token(token: str, *, secret: str, issuer: str, audience: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"], issuer=issuer, audience=audience,
                      options={"require": ["sub", "exp", "iat", "iss", "aud"]})
