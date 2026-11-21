"""Defer physical deletion until the owning database transaction commits."""
import logging
import shutil
from sqlalchemy import event
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


def after_commit_remove(session, path, directory=False):
    session.info.setdefault("physical_cleanup", []).append((path, directory))


@event.listens_for(Session, "after_commit")
def _committed(session):
    if session.in_nested_transaction():
        return
    for path, directory in session.info.pop("physical_cleanup", []):
        try:
            if directory:
                if path.exists():
                    shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        except OSError:
            log.exception("Committed deletion needs physical cleanup: %s", path)


@event.listens_for(Session, "after_rollback")
def _rolled_back(session):
    session.info.pop("physical_cleanup", None)
