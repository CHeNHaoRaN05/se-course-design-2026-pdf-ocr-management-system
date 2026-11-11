"""审查回归：真实路由、数据库和PDF；不mock HTTP。"""
from datetime import timedelta, datetime
from sqlalchemy import select, func
from fastapi import HTTPException
from .conftest import make_env, auth, register, pdf_bytes
from .test_auth import _seed, _login


def upload(client, token, name="sample.pdf", content=None):
    r=client.post("/api/v1/files",headers=auth(token),files={"file":(name,content if content is not None else pdf_bytes(2),"application/pdf")})
    assert r.status_code==201,r.text
    return r.json()


def test_query_stable_total_filters_and_unavailable_status(tmp_path):
    _,app,c=make_env(tmp_path,ocr_enabled=False); token=register(c)
    ids=[upload(c,token)["id"] for _ in range(3)]
    from backend.models import File
    with app.state.sessions() as s:
        rows=list(s.scalars(select(File)))
        for row in rows: row.created_at=rows[0].created_at
        s.commit()
    r=c.get("/api/v1/files/query?limit=2&status=succeeded",headers=auth(token)).json()
    assert r["total"]==3 and r["status_available"] is False
    assert [f["id"] for f in r["items"]]==sorted(ids)[:2]
    assert c.get("/api/v1/files/query?limit=2&offset=2",headers=auth(token)).json()["items"][0]["id"]==sorted(ids)[2]
    assert c.get("/api/v1/files/query?media_type=image/png",headers=auth(token)).json()["total"]==0
    for suffix in ["offset=9223372036854775808","date_from=2026-11-12&date_to=2026-11-11","date_to=9999-12-31"]:
        assert c.get(f"/api/v1/files/query?{suffix}",headers=auth(token)).status_code==422
    assert c.get("/api/v1/files?offset=9223372036854775808",headers=auth(token)).status_code==422


def test_filename_and_invalid_upload_cleanup(tmp_path):
    settings,_,c=make_env(tmp_path,ocr_enabled=False); token=register(c)
    a=upload(c,token,"a"*300+".pdf");b=upload(c,token,"a"*300+".pdf")
    assert len(a["name"])==255 and a["name"].endswith(".pdf")
    assert len(b["name"])==255 and b["name"].endswith("(1).pdf")
    assert upload(c,token,"报告.pdf ")["name"]=="报告.pdf"
    before=set(settings.storage_dir.rglob("*.bin"))
    r=c.post("/api/v1/files",headers=auth(token),files={"file":("bad.png",b"broken","image/png")})
    assert r.status_code==422 and r.json()["detail"]=="invalid_image"
    assert set(settings.storage_dir.rglob("*.bin"))==before


def test_bulk_preflight_and_partial_results(tmp_path,monkeypatch):
    _,_,c=make_env(tmp_path,ocr_enabled=False); token=register(c); other=register(c,"other@example.com")
    a=upload(c,token);b=upload(c,token);foreign=upload(c,other)
    assert c.post("/api/v1/files/bulk",headers=auth(token),json={"file_ids":[a["id"],foreign["id"]],"action":"delete"}).status_code==404
    assert c.get(f'/api/v1/files/{a["id"]}',headers=auth(token)).status_code==200
    from backend.modules.files import service
    original=service.update
    def fail_one(s,ident,*args,**kwargs):
        if ident==b["id"]: raise HTTPException(409,"conflict")
        return original(s,ident,*args,**kwargs)
    monkeypatch.setattr(service,"update",fail_one)
    r=c.post("/api/v1/files/bulk",headers=auth(token),json={"file_ids":[a["id"],b["id"]],"action":"move","folder":"/course"})
    assert r.json()["succeeded"]==1 and r.json()["failed"]==1


def test_merge_split_order_and_atomic_rollback(tmp_path,monkeypatch):
    settings,app,c=make_env(tmp_path,ocr_enabled=False);token=register(c)
    a=upload(c,token,content=pdf_bytes(1,100,200));b=upload(c,token,content=pdf_bytes(1,300,400))
    r=c.post("/api/v1/files/merge",headers=auth(token),json={"file_ids":[b["id"],a["id"]],"name":"merged.pdf"})
    assert r.status_code==201,r.text
    ident=r.json()["id"]
    pages=c.get(f'/api/v1/files/{ident}/pages',headers=auth(token)).json()
    assert pages[0]["width_pt"]>pages[1]["width_pt"]
    split=c.post(f'/api/v1/files/{ident}/split',headers=auth(token),json={"name":"part","groups":[[2],[1]]})
    assert split.status_code==201 and len(split.json())==2
    for groups in [[[1],[1]],[[3]],[[]],[[0]],[[1]*101]]:
        assert c.post(f'/api/v1/files/{ident}/split',headers=auth(token),json={"name":"part","groups":groups}).status_code==422
    from backend.modules.files import service
    from backend.models import File
    original=service.upload;calls=0
    def fail_second(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==2: raise HTTPException(422,"injected_failure")
        return original(*args,**kwargs)
    before=set(settings.storage_dir.rglob("*.bin"))
    with app.state.sessions() as s: count=s.scalar(select(func.count(File.id)))
    monkeypatch.setattr(service,"upload",fail_second)
    r=c.post(f'/api/v1/files/{ident}/split',headers=auth(token),json={"name":"broken","every":1})
    assert r.status_code==422
    assert before==set(settings.storage_dir.rglob("*.bin"))
    with app.state.sessions() as s: assert s.scalar(select(func.count(File.id)))==count


def test_merge_limits_corruption_and_foreign_source(tmp_path):
    settings,app,c=make_env(tmp_path,ocr_enabled=False);token=register(c);other=register(c,"other@example.com")
    a=upload(c,token,content=pdf_bytes(100));b=upload(c,token)
    assert c.post("/api/v1/files/merge",headers=auth(token),json={"file_ids":[a["id"],b["id"]],"name":"big.pdf"}).json()["detail"]=="pdf_page_limit"
    foreign=upload(c,other)
    assert c.post("/api/v1/files/merge",headers=auth(token),json={"file_ids":[b["id"],foreign["id"]],"name":"foreign.pdf"}).status_code==404
    from backend.models import File
    with app.state.sessions() as s: source=settings.storage_dir/s.get(File,b["id"]).storage_key
    source.write_bytes(b"%PDF-broken")
    assert c.post(f'/api/v1/files/{b["id"]}/split',headers=auth(token),json={"name":"bad","every":1}).status_code==422


def test_server_trash_admin_only_and_self_demotion(env):
    _,_,c=env;token=register(c);item=upload(c,token)
    assert c.get("/api/v1/files/trash",headers=auth(token)).json()==[]
    c.delete(f'/api/v1/files/{item["id"]}',headers=auth(token))
    rows=c.get("/api/v1/files/trash",headers=auth(token)).json()
    assert rows[0]["id"]==item["id"] and rows[0]["deleted_at"]
    for path in ["/auth/users","/audit"]:
        assert c.get('/api/v1'+path).status_code==401
        assert c.get('/api/v1'+path,headers=auth(token)).status_code==403
    ident=_seed(env,"admin@example.com",role="admin");admin=_login(c,"admin@example.com")
    assert c.get("/api/v1/auth/users",headers=auth(admin)).status_code==200
    logs=c.get("/api/v1/audit?action=file_uploaded",headers=auth(admin)).json()
    assert logs and all("detail" not in row and row["action"]=="file_uploaded" for row in logs)
    assert c.patch(f'/api/v1/auth/users/{ident}/role',headers=auth(admin),json={"role":"viewer"}).status_code==422
    assert c.get("/api/v1/auth/_admin/check",headers=auth(admin)).status_code==200


def test_share_server_clock_and_code_validation(env):
    _,_,c=env
    from backend.models import now
    token=register(c);item=upload(c,token);before=now()
    r=c.post("/api/v1/share",headers=auth(token),json={"file_id":item["id"],"expires_in_days":7,"access_code":"Ab12"})
    assert r.status_code==201
    assert timedelta(days=7)<=datetime.fromisoformat(r.json()["expires_at"])-before<timedelta(days=7,seconds=10)
    assert r.json()["expired"] is False
    for patch in [{"expires_in_days":365},{"expires_at":(now()+timedelta(days=31)).isoformat()},{"access_code":"\u200b"},{"access_code":"a b"},{"expires_in_days":1,"expires_at":(now()+timedelta(days=1)).isoformat()}]:
        assert c.post("/api/v1/share",headers=auth(token),json={"file_id":item["id"],**patch}).status_code==422
    _seed(env,"viewer@example.com",role="viewer");viewer=_login(c,"viewer@example.com")
    assert c.post("/api/v1/share",headers=auth(viewer),json={"file_id":item["id"]}).status_code==403


def test_query_uses_real_ocr_status_and_generation(env):
    _,app,c=env
    assert app.state.ocr_mounted
    token=register(c);a=upload(c,token);upload(c,token)
    job=c.post("/api/v1/ocr/jobs",headers=auth(token),json={"file_id":a["id"]})
    assert job.status_code==202,job.text
    r=c.get("/api/v1/files/query?status=queued&sort=status",headers=auth(token))
    assert r.status_code==200,r.text
    assert r.json()["total"]==1 and r.json()["items"][0]["id"]==a["id"]
    assert r.json()["items"][0]["generation"]==1 and r.json()["status_available"] is True


def test_upload_size_boundary_distinguishes_content_from_limit(tmp_path):
    settings,_,c=make_env(tmp_path,ocr_enabled=False);token=register(c)
    for size,code in [(20*1024*1024,"invalid_image"),(20*1024*1024+1,"upload_size_limit")]:
        r=c.post("/api/v1/files",headers=auth(token),files={"file":("boundary.png",bytes(size),"image/png")})
        assert r.status_code==422 and r.json()["detail"]==code
    assert list(settings.storage_dir.rglob("*.bin"))==[]


def test_encrypted_source_is_rejected_and_new_files_are_absent(tmp_path):
    from pypdf import PdfReader, PdfWriter
    import io
    settings,app,c=make_env(tmp_path,ocr_enabled=False);token=register(c)
    item=upload(c,token)
    writer=PdfWriter();writer.append(PdfReader(io.BytesIO(pdf_bytes(1))))
    writer.encrypt(user_password="",owner_password="owner-only")
    data=io.BytesIO();writer.write(data)
    from backend.models import File
    with app.state.sessions() as s: path=settings.storage_dir/s.get(File,item["id"]).storage_key
    path.write_bytes(data.getvalue())
    r=c.post(f'/api/v1/files/{item["id"]}/split',headers=auth(token),json={"name":"encrypted","every":1})
    assert r.status_code==422 and r.json()["detail"]=="invalid_or_encrypted_pdf"
    assert len(list(settings.storage_dir.rglob("*.bin")))==1


def test_search_media_type_filter_matches_real_index(env):
    from backend.models import File
    from backend.tests.conftest import png_bytes
    from ocr_service.db import Job, TextIndex
    _,app,c=env;token=register(c)
    pdf=upload(c,token)
    image=c.post("/api/v1/files",headers=auth(token),files={"file":("image.png",png_bytes(),"image/png")}).json()
    with app.state.sessions() as s:
        owner=s.get(File,pdf["id"]).owner_id
        for item in [pdf,image]:
            job=Job(file_id=item["id"],owner_id=owner,generation=1,status="succeeded",options={})
            s.add(job);s.flush()
            s.add(TextIndex(file_id=item["id"],page_no=1,job_id=job.id,revision=1,content="验收报告"))
        s.commit()
    r=c.get("/api/v1/search?q=验收&media_type=image/png",headers=auth(token))
    assert r.status_code==200 and [row["file_id"] for row in r.json()["items"]]==[image["id"]]
    assert c.get("/api/v1/search?q=验收&media_type=video/mp4",headers=auth(token)).status_code==422


def test_new_write_routes_reject_viewer(env):
    _,_,c=env;token=register(c);item=upload(c,token)
    _seed(env,"readonly@example.com",role="viewer");viewer=_login(c,"readonly@example.com")
    for path,body in [("/files/bulk",{"file_ids":[item["id"]],"action":"delete"}),("/files/merge",{"file_ids":[item["id"],"0"*32],"name":"out.pdf"}),(f'/files/{item["id"]}/split',{"name":"part","every":1})]:
        assert c.post('/api/v1'+path,headers=auth(viewer),json=body).status_code==403
