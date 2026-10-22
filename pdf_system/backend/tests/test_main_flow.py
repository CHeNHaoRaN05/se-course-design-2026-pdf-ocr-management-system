"""主系统链路测试（甲 + 乙）。不依赖 Paddle 环境。"""
from .conftest import auth, pdf_bytes, png_bytes, register


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "ocr_mounted" in body


def test_register_login_me(client):
    token = register(client, "alice@example.com")
    me = client.get("/api/v1/auth/me", headers=auth(token))
    assert me.status_code == 200 and me.json()["email"] == "alice@example.com"
    again = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "secret12345"})
    assert again.status_code == 200 and again.json()["role"] == "user"


def test_missing_token_is_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_wrong_password_is_422(client):
    register(client, "alice@example.com")
    response = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "bad"})
    assert response.status_code == 422


def test_duplicate_register_is_409(client):
    register(client, "alice@example.com")
    response = client.post("/api/v1/auth/register", json={"email": "alice@example.com", "password": "secret12345"})
    assert response.status_code == 409


def test_upload_list_and_content(client):
    token = register(client)
    upload = client.post("/api/v1/files", headers=auth(token),
                         files={"file": ("note.png", png_bytes(), "image/png")})
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["id"]

    listing = client.get("/api/v1/files", headers=auth(token))
    assert listing.status_code == 200 and len(listing.json()) == 1

    content = client.get(f"/api/v1/files/{file_id}/content", headers=auth(token))
    assert content.status_code == 200 and len(content.content) == upload.json()["size"]


def test_pdf_page_sizes(client):
    """契约 C4：PDF 每页返回点阵尺寸与旋转（pypdfium2 只有 get_rotation，勿改回 .rotation）。"""
    token = register(client)
    upload = client.post("/api/v1/files", headers=auth(token),
                         files={"file": ("doc.pdf", pdf_bytes(3), "application/pdf")})
    assert upload.status_code == 201, upload.text
    assert upload.json()["media_type"] == "application/pdf" and upload.json()["page_count"] == 3

    pages = client.get(f"/api/v1/files/{upload.json()['id']}/pages", headers=auth(token))
    assert pages.status_code == 200, pages.text
    body = pages.json()
    assert [p["page_no"] for p in body] == [1, 2, 3]
    assert all(p["width_pt"] > 0 and p["height_pt"] > 0 for p in body)
    assert all(isinstance(p["rotation"], int) for p in body)


def test_image_has_no_pages(client):
    token = register(client)
    file_id = client.post("/api/v1/files", headers=auth(token),
                          files={"file": ("n.png", png_bytes(), "image/png")}).json()["id"]
    assert client.get(f"/api/v1/files/{file_id}/pages", headers=auth(token)).status_code == 422


def test_bookmarks(client):
    token = register(client)
    file_id = client.post("/api/v1/files", headers=auth(token),
                          files={"file": ("n.png", png_bytes(), "image/png")}).json()["id"]
    base = f"/api/v1/files/{file_id}/reader"
    created = client.post(f"{base}/bookmarks", headers=auth(token), json={"page_no": 1, "title": "重点"})
    assert created.status_code == 201, created.text
    assert client.get(f"{base}/bookmarks", headers=auth(token)).json()[0]["title"] == "重点"
    # 同一页重复添加必须冲突
    assert client.post(f"{base}/bookmarks", headers=auth(token), json={"page_no": 1}).status_code == 409


def test_annotations(client):
    token = register(client)
    file_id = client.post("/api/v1/files", headers=auth(token),
                          files={"file": ("n.png", png_bytes(), "image/png")}).json()["id"]
    response = client.post(f"/api/v1/files/{file_id}/reader/annotations", headers=auth(token),
                           json={"page_no": 1, "kind": "highlight", "text": "批注",
                                 "bbox": [0.1, 0.1, 0.5, 0.2]})
    assert response.status_code == 201, response.text
    assert response.json()["payload"]["bbox"] == [0.1, 0.1, 0.5, 0.2]


def test_tags_and_folder(client):
    token = register(client)
    file_id = client.post("/api/v1/files", headers=auth(token),
                          files={"file": ("n.png", png_bytes(), "image/png")}).json()["id"]
    patched = client.patch(f"/api/v1/files/{file_id}", headers=auth(token),
                           json={"tags": ["合同"], "folder": "/work"})
    assert patched.status_code == 200 and patched.json()["tags"] == ["合同"]
    assert client.get("/api/v1/files/tags", headers=auth(token)).json() == ["合同"]
    assert client.get("/api/v1/files?folder=/work", headers=auth(token)).json()[0]["id"] == file_id


def test_quota_and_statistics(client):
    token = register(client)
    client.post("/api/v1/files", headers=auth(token), files={"file": ("n.png", png_bytes(), "image/png")})
    quota = client.get("/api/v1/quota", headers=auth(token)).json()
    assert quota["pages_reserved"] == 0 and "month" in quota
    overview = client.get("/api/v1/quota/overview", headers=auth(token)).json()
    assert overview["files"] == 1 and overview["storage_bytes"] > 0


def test_search_returns_200(client):
    token = register(client)
    response = client.get("/api/v1/search?q=合同", headers=auth(token))
    assert response.status_code == 200 and "items" in response.json()


def test_trash_restore_purge(client):
    token = register(client)
    file_id = client.post("/api/v1/files", headers=auth(token),
                          files={"file": ("n.png", png_bytes(), "image/png")}).json()["id"]
    assert client.delete(f"/api/v1/files/{file_id}", headers=auth(token)).status_code == 200
    assert client.get("/api/v1/files", headers=auth(token)).json() == []
    assert client.post(f"/api/v1/files/{file_id}/restore", headers=auth(token)).status_code == 200
    assert client.delete(f"/api/v1/files/{file_id}/purge", headers=auth(token)).status_code == 204


def test_other_users_file_is_404(client):
    token = register(client, "alice@example.com")
    file_id = client.post("/api/v1/files", headers=auth(token),
                          files={"file": ("n.png", png_bytes(), "image/png")}).json()["id"]
    bob = register(client, "bob@example.com")
    # 非本人资源统一 404，不泄露资源是否存在
    assert client.get(f"/api/v1/files/{file_id}", headers=auth(bob)).status_code == 404
