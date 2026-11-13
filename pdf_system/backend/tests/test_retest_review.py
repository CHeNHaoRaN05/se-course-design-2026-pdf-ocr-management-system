"""Second review: true API and SQLite behavior, no fake transport or Paddle required."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import threading
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from .conftest import make_env, auth, register, pdf_bytes, png_bytes


@pytest.fixture
def isolated(tmp_path):
    return make_env(tmp_path,ocr_enabled=False)


def upload(client,token,name='same.pdf'):
    r=client.post('/api/v1/files',headers=auth(token),files={'file':(name,pdf_bytes(1),'application/pdf')})
    assert r.status_code==201,r.text
    return r.json()


def test_concurrent_names_and_restore_collisions(isolated):
    _,app,c=isolated;token=register(c);barrier=threading.Barrier(4)
    def send(_):
        barrier.wait()
        with TestClient(app) as client:
            return upload(client,token)
    with ThreadPoolExecutor(max_workers=4) as pool:
        values=list(pool.map(send,range(4)))
    assert sorted(row['name'] for row in values)==['same(1).pdf','same(2).pdf','same(3).pdf','same.pdf']
    original=next(row for row in values if row['name']=='same.pdf')
    c.delete(f'/api/v1/files/{original["id"]}',headers=auth(token))
    replacement=upload(c,token)
    assert replacement['name']=='same.pdf'
    restored=c.post(f'/api/v1/files/{original["id"]}/restore',headers=auth(token))
    assert restored.json()['name']=='same(4).pdf'


def test_soft_deleted_bulk_item_is_not_ownership_failure(isolated):
    _,_,c=isolated;token=register(c);a=upload(c,token);b=upload(c,token)
    c.delete(f'/api/v1/files/{a["id"]}',headers=auth(token))
    r=c.post('/api/v1/files/bulk',headers=auth(token),json={'file_ids':[a['id'],b['id']],'action':'delete'})
    assert r.status_code==207 and r.json()['succeeded']==1 and r.json()['failed']==1
    failed=c.post('/api/v1/files/bulk',headers=auth(token),json={'file_ids':[a['id']],'action':'delete'})
    assert failed.status_code==409 and failed.json()['failed']==1
    other=register(c,'other@example.com');foreign=upload(c,other);active=upload(c,token)
    r=c.post('/api/v1/files/bulk',headers=auth(token),json={'file_ids':[active['id'],foreign['id']],'action':'delete'})
    assert r.status_code==404
    assert c.get(f'/api/v1/files/{active["id"]}',headers=auth(token)).status_code==200


def test_query_lengths_blank_folder_and_suggestion(isolated):
    _,_,c=isolated;token=register(c);file=upload(c,token)
    for path,field,size in [('/files','q',50000),('/files','folder',256),('/files','tag',65),('/files/query','folder',256),('/files/query','tag',65)]:
        assert c.get('/api/v1'+path,params={field:'x'*size},headers=auth(token)).status_code==422
    assert c.get('/api/v1/search/suggest',params={'q':'   '},headers=auth(token)).status_code==422
    for folder in ['', '  ']:
        assert c.post('/api/v1/files/bulk',headers=auth(token),json={'file_ids':[file['id']],'action':'move','folder':folder}).status_code==422
    assert c.post('/api/v1/files/bulk',headers=auth(token),json={'file_ids':[file['id']],'action':'move','folder':'/'}).status_code==200


def test_page_envelopes_total_and_permissions(isolated):
    _,app,c=isolated;token=register(c)
    for _ in range(3):
        file=upload(c,token);c.delete(f'/api/v1/files/{file["id"]}',headers=auth(token))
    r=c.get('/api/v1/files/trash?envelope=true&limit=2',headers=auth(token)).json()
    assert r['total']==3 and len(r['items'])==2 and r['offset']==0
    assert len(c.get('/api/v1/files/trash?envelope=true&limit=2&offset=2',headers=auth(token)).json()['items'])==1
    from backend.models import User
    with app.state.sessions() as s:
        user=s.scalar(select(User));user.role='admin';s.commit()
    for path in ['/auth/users','/audit']:
        r=c.get('/api/v1'+path+'?envelope=true&limit=1',headers=auth(token))
        assert r.status_code==200 and r.json()['total']>=1 and len(r.json()['items'])==1
        assert c.get('/api/v1'+path).status_code==401


def test_pdf_lock_not_held_during_persistence_and_lineage(isolated,monkeypatch):
    _,_,c=isolated;token=register(c);a=upload(c,token);b=upload(c,token)
    from backend.modules.files import service
    from backend.core.media import PDFIUM_LOCK
    original=service.upload
    def checked(*args,**kwargs):
        assert not PDFIUM_LOCK._is_owned()
        return original(*args,**kwargs)
    monkeypatch.setattr(service,'upload',checked)
    r=c.post('/api/v1/files/merge',headers=auth(token),json={'file_ids':[a['id'],b['id']],'name':'merged.pdf'})
    assert r.status_code==201,r.text
    merged=r.json();assert merged['version']==2 and merged['replaced_from']==a['id']
    r=c.post(f'/api/v1/files/{merged["id"]}/split',headers=auth(token),json={'name':'part','every':1})
    assert r.status_code==201 and all(f['version']==3 and f['replaced_from']==merged['id'] for f in r.json())


def test_naive_expiry_rejected_aware_normalized(isolated):
    _,_,c=isolated;token=register(c);file=upload(c,token)
    future=datetime.now(timezone.utc)+timedelta(days=1)
    r=c.post('/api/v1/share',headers=auth(token),json={'file_id':file['id'],'expires_at':future.replace(tzinfo=None).isoformat()})
    assert r.status_code==422
    r=c.post('/api/v1/share',headers=auth(token),json={'file_id':file['id'],'expires_at':future.isoformat()})
    assert r.status_code==201
    assert datetime.fromisoformat(r.json()['expires_at'])==future.replace(tzinfo=None)


def test_filename_unicode_and_stem_space(isolated):
    _,_,c=isolated;token=register(c)
    assert upload(c,token,'报告\u200b .pdf ')['name']=='报告.pdf'
    assert upload(c,token,'报告.pdf')['name']=='报告(1).pdf'


def test_status_sort_reports_effective_behavior(isolated):
    _,_,c=isolated;token=register(c);upload(c,token)
    r=c.get('/api/v1/files/query?sort=status&status=succeeded',headers=auth(token)).json()
    assert r['effective_sort']=='newest' and r['total']==1 and not r['status_available']


def test_concurrent_share_visits_not_lost_and_failure_audited(isolated):
    _,app,c=isolated;token=register(c);file=upload(c,token)
    share=c.post('/api/v1/share',headers=auth(token),json={'file_id':file['id'],'access_code':'Ab12','allow_download':False}).json()
    barrier=threading.Barrier(4)
    def visit(_):
        barrier.wait()
        with TestClient(app) as client:return client.get(f'/api/v1/share/token/{share["token"]}?code=Ab12')
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(r.status_code==200 for r in pool.map(visit,range(4)))
    assert c.get(f'/api/v1/share/{share["id"]}/stats',headers=auth(token)).json()['visit_count']==4
    assert c.get(f'/api/v1/share/token/{share["token"]}?code=bad').status_code==404
    from backend.models.audit import AuditLog
    with app.state.sessions() as s: assert s.scalar(select(AuditLog).where(AuditLog.action=='share_denied'))


def test_throttle_has_bounded_attempts():
    from backend.modules.share.throttle import allow
    from uuid import uuid4
    key=uuid4().hex
    assert allow(key,limit=2) and allow(key,limit=2)
    assert not allow(key,limit=2)
