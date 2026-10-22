import logging
import threading
import time

from sqlalchemy import select

from .config import Settings
from .db import File, Job, Page, database
from .media import MediaError, render_page, safe_path
from .queue import claim, complete_attempt, heartbeat, save_page

log = logging.getLogger(__name__)


class Worker:
    def __init__(self, settings, session_factory, backend=None):
        self.cfg, self.sessions, self.backend = settings, session_factory, backend

    def run_once(self):
        lease = claim(self.sessions, self.cfg)
        if lease is None:
            return False
        job_id, token = lease
        stop, lost = threading.Event(), threading.Event()

        def keep_alive():
            while not stop.wait(max(1, self.cfg.lease_seconds // 3)):
                try:
                    if not heartbeat(self.sessions, self.cfg, job_id, token):
                        lost.set()
                        return
                except Exception:
                    log.exception("Lease heartbeat failed for %s", job_id)
                    lost.set()
                    return

        thread = threading.Thread(target=keep_alive, daemon=True)
        thread.start()
        try:
            with self.sessions() as session:
                job = session.get(Job, job_id)
                file = session.get(File, job.file_id)
                page_numbers = session.scalars(select(Page.page_no).where(Page.job_id == job_id, Page.status != "succeeded").order_by(Page.page_no)).all()
            for page_no in page_numbers:
                if lost.is_set() or not heartbeat(self.sessions, self.cfg, job_id, token):
                    break
                image = None
                try:
                    if self.backend is None:
                        from .backend import PaddleBackend
                        self.backend = PaddleBackend(self.cfg)
                    image = render_page(safe_path(self.cfg.storage, file.storage_key), file.media_type,
                                        page_no, job.options["dpi"], self.cfg.max_pixels)
                    result = self.backend.recognize(image, job.options)
                    # Token-specific filenames prevent a stale worker from overwriting a new preview.
                    key = f"pages/{job_id}/{token}-{page_no}.png"
                    target = safe_path(self.cfg.storage, key)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    image.save(target, "PNG")
                    result["image_key"] = key
                    result["coordinate_system"] = "normalized_top_left_display_page"
                    if not save_page(self.sessions, job_id, token, page_no, result=result):
                        target.unlink(missing_ok=True)
                        break
                except Exception as exc:
                    log.exception("OCR failed: job=%s page=%s", job_id, page_no)
                    error = str(exc) if isinstance(exc, MediaError) else "ocr_inference_failed"
                    if not save_page(self.sessions, job_id, token, page_no, error=error):
                        break
                finally:
                    if image is not None:
                        image.close()
            complete_attempt(self.sessions, self.cfg, job_id, token)
        finally:
            stop.set()
            thread.join(timeout=5)
        return True


def main(once=False):
    logging.basicConfig(level=logging.INFO)
    cfg = Settings()
    engine, sessions = database(cfg)
    worker = Worker(cfg, sessions)
    try:
        while True:
            worked = worker.run_once()
            if once:
                break
            if not worked:
                time.sleep(2)
    finally:
        engine.dispose()

