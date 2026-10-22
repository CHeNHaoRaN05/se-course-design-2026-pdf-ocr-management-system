"""统一错误出口（负责人：甲）。

对外只暴露 {"detail": "..."}；内部异常不回显路径与堆栈。
"""
from fastapi import HTTPException


def bad_request(message: str = "请求参数不合法") -> HTTPException:
    return HTTPException(422, message)


def not_found(message: str = "资源不存在或无权访问") -> HTTPException:
    return HTTPException(404, message)


def conflict(message: str) -> HTTPException:
    return HTTPException(409, message)


def quota_exceeded(message: str = "本月识别页数配额不足") -> HTTPException:
    return HTTPException(429, message)


def unsupported(message: str) -> HTTPException:
    return HTTPException(415, message)
