"""统一错误出口（负责人：甲）。

对外只暴露 {"detail": "..."}；内部异常不回显路径与堆栈。
"""
from fastapi import HTTPException


def bad_request(message: str = "请求参数不合法") -> HTTPException:
    return HTTPException(422, message)


def unauthorized(message: str = "邮箱或密码不正确") -> HTTPException:
    """凭据无效：401，带 WWW-Authenticate；不得用 422 表示认证失败。"""
    return HTTPException(401, message, headers={"WWW-Authenticate": "Bearer"})


def forbidden(message: str = "原密码不正确") -> HTTPException:
    """已认证但动作不允许：403，避免 401 触发前端清凭据。"""
    return HTTPException(403, message)


def not_found(message: str = "资源不存在或无权访问") -> HTTPException:
    return HTTPException(404, message)


def conflict(message: str) -> HTTPException:
    return HTTPException(409, message)


def quota_exceeded(message: str = "本月识别页数配额不足") -> HTTPException:
    return HTTPException(429, message)


def unsupported(message: str) -> HTTPException:
    return HTTPException(415, message)
