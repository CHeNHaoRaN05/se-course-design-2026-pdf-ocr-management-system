# 当前接口清单

由 scripts/export_api_contract.py 从宿主 OpenAPI 生成。按公开 method + path 计数；不含隐藏别名及框架文档路由。

共 64 个操作，其中 OCR 原生前缀 /api/v1/ocr/ 为 17 个。

| 方法 | 路径 | 摘要 |
|---|---|---|
| DELETE | `/api/v1/files/{file_id}` | Trash Endpoint |
| DELETE | `/api/v1/files/{file_id}/purge` | Purge Endpoint |
| DELETE | `/api/v1/files/{file_id}/reader/annotations/{annotation_id}` | Delete Annotation |
| DELETE | `/api/v1/files/{file_id}/reader/bookmarks/{bookmark_id}` | Delete Bookmark |
| DELETE | `/api/v1/share/{share_id}` | Cancel |
| GET | `/api/v1/audit` | Audit History |
| GET | `/api/v1/auth/_admin/check` | Admin Check |
| GET | `/api/v1/auth/me` | Me |
| GET | `/api/v1/auth/users` | List Users |
| GET | `/api/v1/files` | List Endpoint |
| GET | `/api/v1/files/folders` | List Folders |
| GET | `/api/v1/files/tags` | List Tags |
| GET | `/api/v1/files/trash` | Trash List |
| GET | `/api/v1/files/{file_id}` | Get Endpoint |
| GET | `/api/v1/files/{file_id}/content` | Content Endpoint |
| GET | `/api/v1/files/{file_id}/pages` | Pages Endpoint |
| GET | `/api/v1/files/{file_id}/reader/annotations` | Get Annotations |
| GET | `/api/v1/files/{file_id}/reader/bookmarks` | Get Bookmarks |
| GET | `/api/v1/ocr-host/capabilities` | Capabilities |
| GET | `/api/v1/ocr-host/files/{file_id}/jobs` | File Jobs |
| GET | `/api/v1/ocr-host/usage` | Usage |
| GET | `/api/v1/ocr/audit` | Audit Log |
| GET | `/api/v1/ocr/capabilities` | Capabilities |
| GET | `/api/v1/ocr/files/{file_id}` | Get File |
| GET | `/api/v1/ocr/files/{file_id}/content` | File Content |
| GET | `/api/v1/ocr/jobs` | List Jobs |
| GET | `/api/v1/ocr/jobs/{job_id}` | Get Job |
| GET | `/api/v1/ocr/jobs/{job_id}/export` | Export |
| GET | `/api/v1/ocr/jobs/{job_id}/pages` | Results |
| GET | `/api/v1/ocr/jobs/{job_id}/pages/{page_no}` | Get Page |
| GET | `/api/v1/ocr/jobs/{job_id}/pages/{page_no}/image` | Page Image |
| GET | `/api/v1/ocr/search` | Search |
| GET | `/api/v1/ocr/usage` | Usage |
| GET | `/api/v1/quota` | My Quota |
| GET | `/api/v1/quota/` | My Quota |
| GET | `/api/v1/quota/overview` | Overview |
| GET | `/api/v1/search` | Full Text |
| GET | `/api/v1/search/suggest` | Suggest |
| GET | `/api/v1/share` | List Shares |
| GET | `/api/v1/share/` | List Shares |
| GET | `/api/v1/share/token/{token}` | View Token |
| GET | `/api/v1/share/{share_id}` | Detail |
| GET | `/api/v1/share/{share_id}/stats` | Stats |
| GET | `/health` | Health |
| PATCH | `/api/v1/auth/users/{user_id}/disabled` | Set Disabled Endpoint |
| PATCH | `/api/v1/auth/users/{user_id}/role` | Set Role |
| PATCH | `/api/v1/files/{file_id}` | Update Endpoint |
| PATCH | `/api/v1/ocr/jobs/{job_id}/pages/{page_no}` | Correct |
| POST | `/api/v1/auth/change-password` | Change Password Endpoint |
| POST | `/api/v1/auth/login` | Login Endpoint |
| POST | `/api/v1/auth/logout` | Logout Endpoint |
| POST | `/api/v1/auth/refresh` | Refresh Endpoint |
| POST | `/api/v1/auth/register` | Register Endpoint |
| POST | `/api/v1/files` | Upload Endpoint |
| POST | `/api/v1/files/{file_id}/reader/annotations` | Post Annotation |
| POST | `/api/v1/files/{file_id}/reader/bookmarks` | Post Bookmark |
| POST | `/api/v1/files/{file_id}/restore` | Restore Endpoint |
| POST | `/api/v1/ocr-host/files/{file_id}/sync` | Sync File |
| POST | `/api/v1/ocr-host/jobs/{job_id}/settle` | Settle |
| POST | `/api/v1/ocr/files` | Upload |
| POST | `/api/v1/ocr/jobs` | Create Job |
| POST | `/api/v1/ocr/jobs/{job_id}/cancel` | Cancel |
| POST | `/api/v1/ocr/jobs/{job_id}/retry` | Retry |
| POST | `/api/v1/share` | Create |
