from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user_id: str
    role: str = "user"


def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if not credentials:
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    cfg = request.app.state.ocr_settings
    try:
        claims = jwt.decode(credentials.credentials, cfg.jwt_secret, algorithms=["HS256"],
                            issuer=cfg.jwt_issuer, audience=cfg.jwt_audience,
                            options={"require": ["sub", "exp", "iat", "iss", "aud"]})
        sub, role = claims["sub"], claims.get("role", "user")
        if not isinstance(sub, str) or not 1 <= len(sub) <= 128 or role not in {"user", "viewer", "admin"}:
            raise ValueError("Invalid principal")
        return Principal(sub, role)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})


def editor(user: Principal = Depends(current_user)):
    if user.role == "viewer":
        raise HTTPException(403, "Read-only role")
    return user


def owned(resource, user):
    if resource is None or (resource.owner_id != user.user_id and user.role != "admin"):
        raise HTTPException(404, "Resource not found")
    return resource

