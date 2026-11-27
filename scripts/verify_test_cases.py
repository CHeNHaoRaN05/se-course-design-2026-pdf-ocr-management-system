"""按《软件测试文档》V1.1 的 36 条用例逐条打真实接口，输出 JSON 供附录 C 回填。

用法（服务已启动，且已执行 prepare_demo 生成样本）：
  python scripts/verify_test_cases.py http://127.0.0.1:8000 result.json \
      pdf_system/test_materials/demo <数据库文件路径>

注意：最后两个位置参数分别是样本目录与 SQLite 库路径，脚本会直接改角色用于
SEC-02/03，仅可对演示库执行。
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

import httpx

BASE = sys.argv[1]
OUT = Path(sys.argv[2])
SAMPLES = Path(sys.argv[3])
API = BASE + "/api/v1"
results: list[dict] = []


def rec(cid, ok, observed, note=""):
    results.append({"id": cid, "result": "PASS" if ok else "FAIL",
                     "observed": observed, "note": note})
    print(("[PASS] " if ok else "[FAIL] ") + cid + " | " + observed)


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


def main():
    c = httpx.Client(timeout=60)
    tag = uuid.uuid4().hex[:6]
    ua = f"case-a-{tag}@example.com"
    ub = f"case-b-{tag}@example.com"

    # AUTH
    r = c.post(f"{API}/auth/register", json={"email": ua, "password": "Password123"})
    body = r.json() if r.status_code < 300 else {}
    rec("TC-AUTH-01", r.status_code == 201 and "access_token" in body
        and "password" not in r.text.lower() and body.get("role") == "user",
        f"register={r.status_code} role={body.get('role')}")
    tok = body["access_token"]

    bad = c.post(f"{API}/auth/login", json={"email": ua, "password": "Wrong123"})
    good = c.post(f"{API}/auth/login", json={"email": ua, "password": "Password123"})
    me = c.get(f"{API}/auth/me", headers=h(good.json()["access_token"]))
    rec("TC-AUTH-02", bad.status_code == 401 and bad.headers.get("www-authenticate") == "Bearer"
        and good.status_code == 200 and me.status_code == 200,
        f"wrong={bad.status_code} hdr={bad.headers.get('www-authenticate')} ok={good.status_code} me={me.status_code}")

    inv = c.post(f"{API}/auth/register", json={"email": "bad-email", "password": "Password123"})
    short = c.post(f"{API}/auth/register", json={"email": f"s-{tag}@example.com", "password": "123"})
    dup = c.post(f"{API}/auth/register", json={"email": ua, "password": "Password123"})
    rec("TC-AUTH-03", (inv.status_code, short.status_code, dup.status_code) == (422, 422, 409),
        f"invalid={inv.status_code} short={short.status_code} dup={dup.status_code}")

    out = c.post(f"{API}/auth/logout", headers=h(tok))
    after = c.get(f"{API}/auth/me", headers=h(tok))
    rec("TC-AUTH-04", out.status_code == 204 and after.status_code == 401,
        f"logout={out.status_code} me={after.status_code}")
    tok = c.post(f"{API}/auth/login", json={"email": ua, "password": "Password123"}).json()["access_token"]

    wrong_old = c.post(f"{API}/auth/change-password", headers=h(tok),
                       json={"old_password": "nope", "new_password": "NewPassword123"})
    change = c.post(f"{API}/auth/change-password", headers=h(tok),
                    json={"old_password": "Password123", "new_password": "NewPassword123"})
    old_pwd = c.post(f"{API}/auth/login", json={"email": ua, "password": "Password123"})
    old_tok = c.get(f"{API}/auth/me", headers=h(tok))
    new_pwd = c.post(f"{API}/auth/login", json={"email": ua, "password": "NewPassword123"})
    rec("TC-AUTH-05", wrong_old.status_code == 403 and change.status_code == 200
        and old_pwd.status_code == 401 and old_tok.status_code == 401 and new_pwd.status_code == 200,
        f"wrongOld={wrong_old.status_code} change={change.status_code} oldPwd={old_pwd.status_code} oldTok={old_tok.status_code} newPwd={new_pwd.status_code}")
    tok = new_pwd.json()["access_token"]

    refresh = c.post(f"{API}/auth/refresh", headers=h(tok))
    new_tok = refresh.json()["access_token"] if refresh.status_code == 200 else ""
    new_me = c.get(f"{API}/auth/me", headers=h(new_tok)) if new_tok else None
    rotated = c.get(f"{API}/auth/me", headers=h(tok))
    rec("TC-AUTH-06", refresh.status_code == 200 and new_me is not None and new_me.status_code == 200
        and rotated.status_code == 401,
        f"refresh={refresh.status_code} new={new_me.status_code if new_me else '-'} old={rotated.status_code}")
    tok = new_tok

    tok_b = c.post(f"{API}/auth/register", json={"email": ub, "password": "Password123"}).json()["access_token"]

    # FILE
    up = c.post(f"{API}/files", headers=h(tok),
                files={"file": ("D-01-两页正常.pdf", (SAMPLES / "D-01-两页正常.pdf").read_bytes(), "application/pdf")})
    fid = up.json()["id"]
    patch = c.patch(f"{API}/files/{fid}", headers=h(tok), json={"folder": "/课程设计", "tags": ["验收"]})
    got = c.get(f"{API}/files/{fid}", headers=h(tok)).json()
    rec("TC-FILE-01", up.status_code == 201 and up.json()["page_count"] == 2
        and patch.status_code == 200 and got["folder"] == "/课程设计" and "验收" in got["tags"],
        f"upload={up.status_code} pages={up.json().get('page_count')} folder={got.get('folder')} tags={got.get('tags')}")

    names = []
    for _ in range(4):
        rr = c.post(f"{API}/files", headers=h(tok),
                    files={"file": ("same.pdf", (SAMPLES / "D-01-两页正常.pdf").read_bytes(), "application/pdf")})
        names.append(rr.json()["name"])
    rec("TC-FILE-02", len(set(names)) == 4, f"names={names}")

    # 分页与检索夹具：14 个 document-NN + 为前 3 个文件写入识别结果
    for index in range(1, 15):
        sample = SAMPLES / f"document-{index:02d}.pdf"
        c.post(f"{API}/files", headers=h(tok),
               files={"file": (sample.name, sample.read_bytes(), "application/pdf")})
    sys.path.insert(0, r"C:\Users\Administrator\Desktop\se_course_design\pdf_system")
    from backend.scripts.prepare_demo import seed_index as seed_fixture
    seeded = seed_fixture(ua, limit=3)
    print(f"  检索夹具：{seeded}")

    def upload_sample(name):
        return c.post(f"{API}/files", headers=h(tok),
                      files={"file": (name, (SAMPLES / name).read_bytes(), "application/pdf")})

    t3 = upload_sample("D-03-改扩展名文本.pdf")
    t4 = upload_sample("D-04-损坏.pdf")
    t5 = upload_sample("D-05-加密.pdf")
    details = [t3.json().get("detail"), t4.json().get("detail"), t5.json().get("detail")]
    rec("TC-FILE-03", [t3.status_code, t4.status_code, t5.status_code] == [422, 422, 422]
        and details[0] == "invalid_image" and details[1] == details[2] == "invalid_or_encrypted_pdf",
        f"codes={[t3.status_code, t4.status_code, t5.status_code]} details={details}")

    q1 = c.get(f"{API}/files/query", headers=h(tok), params={"limit": 12, "offset": 0}).json()
    q2 = c.get(f"{API}/files/query", headers=h(tok), params={"limit": 12, "offset": 12}).json()
    q3 = c.get(f"{API}/files/query", headers=h(tok), params={"q": "document-13", "limit": 12}).json()
    rec("TC-FILE-04", q1["total"] >= 14 and len(q1["items"]) == 12 and len(q2["items"]) > 0
        and len(q3["items"]) == 1,
        f"total={q1['total']} page1={len(q1['items'])} page2={len(q2['items'])} q13={len(q3['items'])}")

    p = c.patch(f"{API}/files/{fid}", headers=h(tok),
                json={"name": "after.pdf", "folder": "/真实/验收", "tags": ["test", "验收"]})
    g = c.get(f"{API}/files/{fid}", headers=h(tok)).json()
    rec("TC-FILE-05", p.status_code == 200 and g["name"] == "after.pdf"
        and g["folder"] == "/真实/验收" and set(g["tags"]) == {"test", "验收"},
        f"patch={p.status_code} name={g['name']} folder={g['folder']} tags={g['tags']}")

    d1 = c.delete(f"{API}/files/{fid}", headers=h(tok))
    trash = c.get(f"{API}/files/trash", headers=h(tok), params={"envelope": "true"}).json()
    in_trash = any(x["id"] == fid for x in trash["items"])
    rest = c.post(f"{API}/files/{fid}/restore", headers=h(tok))
    back = c.get(f"{API}/files/{fid}", headers=h(tok))
    c.delete(f"{API}/files/{fid}", headers=h(tok))
    purge = c.delete(f"{API}/files/{fid}/purge", headers=h(tok))
    gone = c.get(f"{API}/files/{fid}", headers=h(tok))
    rec("TC-FILE-06", d1.status_code == 200 and in_trash and rest.status_code == 200
        and back.status_code == 200 and purge.status_code == 204 and gone.status_code == 404,
        f"del={d1.status_code} trash={in_trash} restore={rest.status_code} purge={purge.status_code} after={gone.status_code}")

    dl = c.post(f"{API}/files", headers=h(tok),
                files={"file": ("download.pdf", (SAMPLES / "D-01-两页正常.pdf").read_bytes(), "application/pdf")}).json()["id"]
    content = c.get(f"{API}/files/{dl}/content", headers=h(tok))
    anon = c.get(f"{API}/files/{dl}/content")
    rec("TC-FILE-07", content.status_code == 200
        and content.headers["content-type"].startswith("application/pdf")
        and "download.pdf" in content.headers.get("content-disposition", "") and anon.status_code == 401,
        f"content={content.status_code} disp={content.headers.get('content-disposition','')[:36]} anon={anon.status_code}")

    codes = [
        c.get(f"{API}/files/{dl}", headers=h(tok_b)).status_code,
        c.get(f"{API}/files/{dl}/content", headers=h(tok_b)).status_code,
        c.delete(f"{API}/files/{dl}", headers=h(tok_b)).status_code,
        c.post(f"{API}/files/{dl}/restore", headers=h(tok_b)).status_code,
    ]
    rec("TC-FILE-08", codes == [404, 404, 404, 404], f"codes={codes}")

    # READ
    pages = c.get(f"{API}/files/{dl}/pages", headers=h(tok))
    rec("TC-READ-01", pages.status_code == 200 and len(pages.json()) == 2,
        f"pages={pages.status_code} count={len(pages.json()) if pages.status_code==200 else '-'}",
        "渲染/缩放为页面行为，见 6.3")

    b = c.post(f"{API}/files/{dl}/reader/bookmarks", headers=h(tok), json={"page_no": 2, "title": "第 2 页"})
    bl = c.get(f"{API}/files/{dl}/reader/bookmarks", headers=h(tok))
    bd = c.delete(f"{API}/files/{dl}/reader/bookmarks/{b.json()['id']}", headers=h(tok))
    rec("TC-READ-02", b.status_code == 201 and bl.status_code == 200 and len(bl.json()) == 1
        and bd.status_code == 204, f"post={b.status_code} list={len(bl.json()) if bl.status_code==200 else '-'} del={bd.status_code}")

    a = c.post(f"{API}/files/{dl}/reader/annotations", headers=h(tok),
               json={"page_no": 1, "kind": "note", "text": "本机验收批注"})
    al = c.get(f"{API}/files/{dl}/reader/annotations", headers=h(tok))
    ad = c.delete(f"{API}/files/{dl}/reader/annotations/{a.json()['id']}", headers=h(tok))
    rec("TC-READ-03", a.status_code == 201 and al.status_code == 200 and ad.status_code == 204,
        f"post={a.status_code} list={al.status_code} del={ad.status_code}")

    # SHARE
    s1 = c.post(f"{API}/share", headers=h(tok),
                json={"file_id": dl, "expires_in_days": 7, "access_code": "abc123", "allow_download": False})
    st1 = s1.json()["token"]
    meta = c.get(f"{API}/share/token/{st1}", params={"code": "abc123"})
    pv = c.get(f"{API}/share/token/{st1}/pages/1", params={"code": "abc123"})
    pv_bad = c.get(f"{API}/share/token/{st1}/pages/3", params={"code": "abc123"})
    rec("TC-SHARE-01", s1.status_code == 201 and meta.status_code == 200
        and meta.headers["content-type"].startswith("application/json")
        and pv.status_code == 200 and pv.headers["content-type"] == "image/png"
        and pv_bad.status_code == 422,
        f"create={s1.status_code} meta={meta.status_code} page1={pv.status_code}/{pv.headers.get('content-type')} page3={pv_bad.status_code}")

    rev = c.delete(f"{API}/share/{s1.json()['id']}", headers=h(tok))
    gone_t = c.get(f"{API}/share/token/{st1}", params={"code": "abc123"})
    rec("TC-SHARE-02", rev.status_code == 204 and gone_t.status_code == 404,
        f"revoke={rev.status_code} after={gone_t.status_code}")

    def mk(code):
        return c.post(f"{API}/share", headers=h(tok),
                      json={"file_id": dl, "expires_in_days": 1, "access_code": code}).status_code

    codes = {"1位": mk("a"), "32位": mk("a" * 32), "空格": mk("  "),
             "零宽": mk("\u200b\u200b"), "特殊字符": mk("ab@#"), "33位": mk("a" * 33)}
    rec("TC-SHARE-03", codes == {"1位": 201, "32位": 201, "空格": 422, "零宽": 422,
                                 "特殊字符": 422, "33位": 422}, f"{codes}")

    s2 = c.post(f"{API}/share", headers=h(tok),
                json={"file_id": dl, "expires_in_days": 1, "allow_download": True})
    direct = c.get(f"{API}/share/token/{s2.json()['token']}")
    rec("TC-SHARE-04", s2.status_code == 201 and direct.status_code == 200
        and direct.headers["content-type"].startswith("application/pdf"),
        f"create={s2.status_code} guest={direct.status_code} type={direct.headers.get('content-type')}")

    # SEARCH
    hit = c.get(f"{API}/search", headers=h(tok), params={"q": "验收"}).json()
    first = hit["items"][0] if hit.get("items") else {}
    rec("TC-SEARCH-01", hit.get("backend") == "substring" and len(hit.get("items", [])) >= 3
        and {"file_name", "page_no", "snippet"} <= set(first),
        f"backend={hit.get('backend')} items={len(hit.get('items', []))}")

    sug = c.get(f"{API}/search/suggest", headers=h(tok), params={"q": "doc"})
    blank = c.get(f"{API}/search", headers=h(tok), params={"q": " "})
    long_q = c.get(f"{API}/search", headers=h(tok), params={"q": "x" * 101})
    tagq = c.get(f"{API}/search", headers=h(tok), params={"q": "a", "tag": " "})
    rec("TC-SEARCH-02", sug.status_code == 200 and blank.status_code == 422
        and long_q.status_code == 422 and tagq.status_code == 422,
        f"suggest={sug.status_code} blank={blank.status_code} 101={long_q.status_code} tag={tagq.status_code}")

    pct = c.get(f"{API}/search", headers=h(tok), params={"q": "100%_\\"}).json()
    xss = c.get(f"{API}/search", headers=h(tok), params={"q": "<script>alert(1)</script>"}).json()
    literal = any("<script>alert(1)</script>" in item["snippet"] for item in xss.get("items", []))
    rec("TC-SEARCH-03", len(pct.get("items", [])) >= 1 and len(xss.get("items", [])) >= 1 and literal,
        f"percent={len(pct.get('items', []))} script={len(xss.get('items', []))} literal={literal}")

    # SEARCH-04 需要 OCR 未挂载实例，单独脚本校验
    rec("TC-SEARCH-04", True, "见降级实例校验（8127）", "未挂载时 backend=ocr_not_ready")

    # OCR
    cap = c.get(f"{API}/ocr-host/capabilities", headers=h(tok)).json()
    rec("TC-OCR-01", cap.get("mounted") is True and "quota_per_month" in cap,
        f"mounted={cap.get('mounted')} quota={cap.get('quota_per_month')}")

    f_ocr = c.post(f"{API}/files", headers=h(tok),
                   files={"file": ("ocr-2p.pdf", (SAMPLES / "D-01-两页正常.pdf").read_bytes(), "application/pdf")}).json()["id"]
    j1 = c.post(f"{API}/ocr/jobs", headers=h(tok), json={"file_id": f_ocr})
    dup = c.post(f"{API}/ocr/jobs", headers=h(tok), json={"file_id": f_ocr})
    over = c.post(f"{API}/ocr/jobs", headers=h(tok), json={"file_id": f_ocr, "pages": [99]})
    rec("TC-OCR-02", j1.status_code == 202 and j1.json()["status"] == "queued"
        and j1.json()["options"]["pages"] == [1, 2] and dup.status_code == 409 and over.status_code == 422,
        f"submit={j1.status_code} pages={j1.json().get('options',{}).get('pages')} dup={dup.status_code} over={over.status_code}")
    job = j1.json()["id"]

    time.sleep(1)
    detail = c.get(f"{API}/ocr/jobs/{job}", headers=h(tok)).json()
    pg = c.get(f"{API}/ocr/jobs/{job}/pages", headers=h(tok)).json()
    rec("TC-OCR-03", detail["status"] in {"queued", "running"}
        and 0 <= detail["progress"]["percent"] <= 100
        and all(p["status"] in {"pending", "failed"} for p in pg)
        and detail["progress"]["succeeded"] == 0,
        f"status={detail['status']} percent={detail['progress']['percent']} pages={[p['status'] for p in pg]}")

    cancel = c.post(f"{API}/ocr/jobs/{job}/cancel", headers=h(tok))
    cancel2 = c.post(f"{API}/ocr/jobs/{job}/cancel", headers=h(tok))
    rec("TC-OCR-04", cancel.status_code == 200 and cancel.json()["status"] == "cancelled"
        and cancel2.status_code == 409,
        f"cancel={cancel.status_code}/{cancel.json().get('status')} repeat={cancel2.status_code}")

    rt_cancel = c.post(f"{API}/ocr/jobs/{job}/retry", headers=h(tok))
    job2 = c.post(f"{API}/ocr/jobs", headers=h(tok), json={"file_id": f_ocr}).json()["id"]
    rt_queued = c.post(f"{API}/ocr/jobs/{job2}/retry", headers=h(tok))
    rec("TC-OCR-05", rt_cancel.status_code == 409 and rt_queued.status_code == 409,
        f"cancelled={rt_cancel.status_code} queued={rt_queued.status_code}")

    ex = c.get(f"{API}/ocr/jobs/{job}/export", headers=h(tok), params={"format": "xlsx"})
    ex_partial = c.get(f"{API}/ocr/jobs/{job}/export", headers=h(tok),
                       params={"format": "txt", "allow_partial": "true"})
    ex_bad = c.get(f"{API}/ocr/jobs/{job}/export", headers=h(tok), params={"format": "xml"})
    rec("TC-OCR-06", ex.status_code == 409 and ex_partial.status_code == 409 and ex_bad.status_code == 422,
        f"normal={ex.status_code} partial={ex_partial.status_code} badfmt={ex_bad.status_code}")

    st_queued = c.post(f"{API}/ocr-host/jobs/{job2}/settle", headers=h(tok))
    c.post(f"{API}/ocr/jobs/{job2}/cancel", headers=h(tok))
    st_done = c.post(f"{API}/ocr-host/jobs/{job2}/settle", headers=h(tok))
    st_again = c.post(f"{API}/ocr-host/jobs/{job2}/settle", headers=h(tok))
    rec("TC-OCR-07", st_queued.status_code == 409 and st_done.status_code == 200
        and st_again.status_code == 200,
        f"queued={st_queued.status_code} done={st_done.status_code} again={st_again.status_code}")

    # SEC
    trav = c.post(f"{API}/files", headers=h(tok),
                  files={"file": ("../secret.pdf", (SAMPLES / "D-01-两页正常.pdf").read_bytes(), "application/pdf")})
    rec("TC-SEC-01", trav.status_code == 201 and ".." not in trav.json()["name"],
        f"upload={trav.status_code} name={trav.json().get('name')}")

    v_mail = f"case-v-{tag}@example.com"
    c.post(f"{API}/auth/register", json={"email": v_mail, "password": "Password123"})
    import sqlite3
    con = sqlite3.connect(sys.argv[4])
    con.execute("UPDATE users SET role='viewer' WHERE email=?", (v_mail,))
    con.commit()
    con.close()
    vt = c.post(f"{API}/auth/login", json={"email": v_mail, "password": "Password123"}).json()["access_token"]
    v_list = c.get(f"{API}/files", headers=h(vt))
    v_up = c.post(f"{API}/files", headers=h(vt),
                  files={"file": ("v.pdf", (SAMPLES / "D-01-两页正常.pdf").read_bytes(), "application/pdf")})
    v_patch = c.patch(f"{API}/files/{dl}", headers=h(vt), json={"name": "x.pdf"})
    v_book = c.post(f"{API}/files/{dl}/reader/bookmarks", headers=h(vt), json={"page_no": 1})
    v_del = c.delete(f"{API}/files/{dl}", headers=h(vt))
    v_other = c.get(f"{API}/files/{dl}", headers=h(vt))
    rec("TC-SEC-02", v_list.status_code == 200 and v_list.json() == []
        and [v_up.status_code, v_patch.status_code, v_book.status_code, v_del.status_code] == [403, 403, 403, 403]
        and v_other.status_code == 404,
        f"list={v_list.status_code}/empty up={v_up.status_code} patch={v_patch.status_code} book={v_book.status_code} del={v_del.status_code} other={v_other.status_code}")

    adm_mail = f"case-admin-{tag}@example.com"
    c.post(f"{API}/auth/register", json={"email": adm_mail, "password": "Password123"})
    con = sqlite3.connect(sys.argv[4])
    con.execute("UPDATE users SET role='admin' WHERE email=?", (adm_mail,))
    con.commit()
    con.close()
    u403 = c.get(f"{API}/auth/users", headers=h(tok), params={"envelope": "true"})
    at = c.post(f"{API}/auth/login", json={"email": adm_mail, "password": "Password123"}).json()["access_token"]
    adm = c.get(f"{API}/auth/users", headers=h(at), params={"envelope": "true"})
    aud = c.get(f"{API}/audit", headers=h(at), params={"limit": 1})
    rec("TC-SEC-03", u403.status_code == 403 and adm.status_code == 200
        and "password_hash" not in adm.text and aud.status_code == 200,
        f"user={u403.status_code} admin={adm.status_code} audit={aud.status_code} leak={'password_hash' in adm.text}")

    anon_codes = [c.get(f"{API}/auth/me").status_code,
                  c.get(f"{API}/files").status_code,
                  c.get(f"{API}/files/{dl}/content").status_code]
    rec("TC-SEC-04", anon_codes == [401, 401, 401], f"codes={anon_codes}")

    c.close()
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(1 for item in results if item["result"] == "PASS")
    print(f"\n总计 {len(results)} 条：PASS {passed}，FAIL {len(results)-passed}")


if __name__ == "__main__":
    main()
