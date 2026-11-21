"""月度识别配额：预留 / 结算 / 退款（负责人：甲）。

调用方只有一处——丙在 OCR 入队钩子（before_enqueue）里调用 reserve。
为了让"预留"与"建任务"原子生效，reserve 使用调用方传入的 session，不自行 commit。
"""
from sqlalchemy import select

from ...core.errors import quota_exceeded
from ...models import QuotaAccount, QuotaLedger, current_month, now


def _account(session, user_id: str, month: str, *, lock: bool) -> QuotaAccount:
    # Dialect UPSERT serializes first-account creation, including SQLite writers.
    table = QuotaAccount.__table__
    values = dict(user_id=user_id, month=month, pages_reserved=0, pages_used=0, updated_at=now())
    if session.bind.dialect.name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
        session.execute(insert(table).values(**values).on_conflict_do_nothing())
    elif session.bind.dialect.name == "mysql":
        from sqlalchemy.dialects.mysql import insert
        session.execute(insert(table).values(**values).on_duplicate_key_update(user_id=user_id))
    else:
        raise RuntimeError("Quota supports SQLite and MySQL")
    statement = select(QuotaAccount).where(QuotaAccount.user_id == user_id, QuotaAccount.month == month)
    return session.scalar(statement.with_for_update().execution_options(populate_existing=True))



def _ledger(session, user_id: str, month: str, pages: int, reason: str, ref_id: str | None) -> None:
    session.add(QuotaLedger(user_id=user_id, month=month, pages=pages, reason=reason, ref_id=ref_id))


def reserve(session, user_id: str, pages: int, *, ref_id: str | None, limit: int) -> None:
    """入队时预留页数；超额抛 429。必须在调用方事务内执行。"""
    if isinstance(pages, bool) or not isinstance(pages, int) or pages < 0:
        raise ValueError("pages must be a nonnegative integer")
    if pages == 0:
        return
    month = current_month()
    account = _account(session, user_id, month, lock=True)
    if account.pages_reserved + account.pages_used + pages > limit:
        raise quota_exceeded(f"本月配额 {limit} 页，已占用 {account.pages_reserved + account.pages_used} 页")
    account.pages_reserved += pages
    account.updated_at = now()
    _ledger(session, user_id, month, pages, "reserve", ref_id)


def settle(session, user_id: str, pages: int, *, ref_id: str | None) -> None:
    """任务终态：把预留转为已用（只结算成功页）。"""
    if isinstance(pages, bool) or not isinstance(pages, int) or pages < 0:
        raise ValueError("pages must be a nonnegative integer")
    if pages == 0:
        return
    month = _reservation_month(session, user_id, ref_id)
    account = _account(session, user_id, month, lock=True)
    moved = min(pages, account.pages_reserved)
    if moved == 0:
        return
    account.pages_reserved -= moved
    account.pages_used += moved
    account.updated_at = now()
    _ledger(session, user_id, month, -moved, "settle_reserve", ref_id)
    _ledger(session, user_id, month, moved, "settle_used", ref_id)


def release(session, user_id: str, pages: int, *, ref_id: str | None) -> None:
    """取消/失败退款。"""
    if isinstance(pages, bool) or not isinstance(pages, int) or pages < 0:
        raise ValueError("pages must be a nonnegative integer")
    if pages == 0:
        return
    month = _reservation_month(session, user_id, ref_id)
    account = _account(session, user_id, month, lock=True)
    moved = min(pages, account.pages_reserved)
    if moved == 0:
        return
    account.pages_reserved -= moved
    account.updated_at = now()
    _ledger(session, user_id, month, -moved, "release", ref_id)


def usage(session, user_id: str) -> dict:
    month = current_month()
    account = session.get(QuotaAccount, (user_id, month))
    reserved = account.pages_reserved if account else 0
    used = account.pages_used if account else 0
    return {"month": month, "pages_reserved": reserved, "pages_used": used, "pages_committed": reserved + used}


def _reservation_month(session, user_id, ref_id):
    if ref_id is None:
        return current_month()
    month = session.scalar(select(QuotaLedger.month).where(QuotaLedger.user_id == user_id,
        QuotaLedger.ref_id == ref_id, QuotaLedger.reason == "reserve").limit(1))
    if month is None:
        raise ValueError("Reservation not found")
    return month
