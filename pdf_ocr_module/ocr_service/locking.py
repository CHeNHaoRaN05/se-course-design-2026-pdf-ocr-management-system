"""Transactional row locking without depending on no-op UPDATE rowcount."""
from sqlalchemy import select, update


def locked_row(session, model, *conditions):
    statement = select(model).where(*conditions).execution_options(populate_existing=True)
    if session.bind.dialect.name == "sqlite":
        # SQLite has no SELECT FOR UPDATE. Acquire its write lock first, then
        # evaluate the predicate under that lock. Intentionally ignore rowcount.
        session.execute(update(model).where(*conditions).values(id=model.id)
                        .execution_options(synchronize_session=False))
    else:
        statement = statement.with_for_update()
    return session.scalar(statement)
