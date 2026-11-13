"""Current-job settlement access/serialization only; not a C3 accounting redesign."""
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import select
from .conftest import register, auth, pdf_bytes


def test_viewer_can_reconcile_owned_terminal_job_and_concurrent_close_is_once(env):
    _,app,c=env
    assert app.state.ocr_mounted
    token=register(c)
    file=c.post('/api/v1/files',headers=auth(token),files={'file':('a.pdf',pdf_bytes(2),'application/pdf')}).json()
    job=c.post('/api/v1/ocr/jobs',headers=auth(token),json={'file_id':file['id']}).json()
    from ocr_service.db import Job,Page
    from backend.models import User,QuotaLedger
    with app.state.sessions() as s:
        user=s.scalar(select(User));user.role='viewer'
        s.get(Job,job['id']).status='succeeded'
        for page in s.scalars(select(Page).where(Page.job_id==job['id'])): page.status='succeeded'
        s.commit()
    def settle(_):
        with TestClient(app) as client:return client.post(f'/api/v1/ocr-host/jobs/{job["id"]}/settle',headers=auth(token))
    with ThreadPoolExecutor(max_workers=4) as pool: responses=list(pool.map(settle,range(4)))
    assert all(r.status_code==200 for r in responses)
    assert sum(r.json()['settled'] for r in responses)==1
    with app.state.sessions() as s:
        assert len(list(s.scalars(select(QuotaLedger).where(QuotaLedger.reason=='job_close',QuotaLedger.ref_id==job['id']))))==1
    quota=c.get('/api/v1/quota',headers=auth(token)).json()
    assert quota['pages_reserved']==0 and quota['pages_used']==2
    other=register(c,'other@example.com')
    assert c.post(f'/api/v1/ocr-host/jobs/{job["id"]}/settle',headers=auth(other)).status_code==404
