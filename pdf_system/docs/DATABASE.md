# 数据设计

同一 MySQL 8 库（`utf8mb4` / InnoDB）中存在**两套 DeclarativeBase**，互不干扰：

* 主系统：本文件列出的表；
* OCR 模块：`ocr_files / ocr_jobs / ocr_pages / pdf_text_index / ocr_audit_log`（由 `ocr_service.db` 定义，主系统只读或按契约写入）。

主系统表前缀无 `ocr_`，OCR 表前缀 `ocr_`（`pdf_text_index` 例外，沿用模块原命名）。

---

## 一、主系统表

### users（甲）

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | VARCHAR(32) | PK | uuid4().hex |
| email | VARCHAR(190) | UNIQUE, INDEX | 登录名，统一小写 |
| display_name | VARCHAR(64) | | 昵称 |
| password_hash | VARCHAR(255) | NOT NULL | `pbkdf2_sha256$轮数$salt$digest` |
| role | VARCHAR(16) | default `user` | user / viewer / admin |
| disabled | TINYINT | default 0 | 停用后令牌立即失效 |
| token_version | INT | default 0 | 改密码时自增，使所有旧令牌失效（FR-USER-05） |
| login_count | INT | default 0 | |
| created_at / last_login_at | DATETIME | | UTC 无时区 |

### quota_accounts（甲）

| 列 | 类型 | 约束 |
|---|---|---|
| user_id + month | VARCHAR(32) + VARCHAR(7) | 复合主键，month = `YYYY-MM` |
| pages_reserved | INT | 已预留未结算 |
| pages_used | INT | 已计费 |
| updated_at | DATETIME | |

约束：`pages_reserved + pages_used ≤ PDF_MONTHLY_PAGE_QUOTA`（默认 500），由 `quota.reserve` 强制。

### quota_ledger（甲）

| 列 | 说明 |
|---|---|
| id / user_id / month | |
| pages | 正数=占用，负数=退还 |
| reason | `reserve` / `settle_reserve` / `settle_used` / `release` / `job_close` |
| ref_id | 关联 job_id（`job_close` 用于结算幂等） |

### files（乙，文件事实来源）

| 列 | 类型 | 说明 |
|---|---|---|
| id | VARCHAR(32) PK | **与 ocr_files.id 相同**（契约 C2） |
| owner_id | VARCHAR(32) INDEX | |
| name / folder | VARCHAR(255) | folder 为分类目录路径，默认 `/` |
| storage_key | VARCHAR(100) | 相对存储根目录，禁止 `..` |
| media_type | VARCHAR(40) | `application/pdf` / `image/png` / `image/jpeg` |
| sha256 | VARCHAR(64) INDEX | 秒传与去重 |
| size / page_count / version | INT | version 在合并/拆分/替换时递增 |
| replaced_from | VARCHAR(32) NULL | 指向被替换的旧文件 |
| deleted_at | DATETIME NULL | 软删除（回收站） |
| created_at | DATETIME | |

### tags / file_tags（乙）

`tags(id, owner_id, name)`；`file_tags(file_id, tag_id)` 多对多，均级联删除。

### bookmarks（乙）

`bookmarks(id, file_id, owner_id, page_no, title, created_at)`，
唯一约束 `(file_id, owner_id, page_no)`——每页最多一个书签。

### annotations（乙）

`annotations(id, file_id, owner_id, page_no, kind, payload JSON, created_at, updated_at)`；
`kind ∈ {highlight, note, ink}`，`payload = {text, bbox}`；**bbox 口径与 OCR 一致**（归一化左上原点）。

### audit_logs（甲）

`audit_logs(id, actor_id, action, resource_id, detail JSON, created_at)`；
`action ∈ {user_registered, user_logged_in, file_uploaded, file_updated, file_trashed,
file_restored, file_purged, bookmark_created, bookmark_deleted, annotation_created, annotation_deleted,
share_created, share_revoked, share_visited}`。

### share_links（甲，支撑 FR-SHR-01/02/03）

分享不复制文件实体，被分享者只读。文件被彻底删除时分享链接级联清除。

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | VARCHAR(32) | PK | uuid4().hex |
| file_id | VARCHAR(32) | FK→files.id, CASCADE, INDEX | 被分享文件 |
| owner_id | VARCHAR(32) | INDEX | 分享者 |
| token | VARCHAR(64) | UNIQUE, INDEX | 分享 URL 中的随机令牌（默认 uid()） |
| expires_at | DATETIME | NULL | 有效期；NULL=永不过期 |
| access_code | VARCHAR(32) | NULL | 提取码；NULL=无需提取码 |
| allow_download | TINYINT | default 1 | 是否允许被分享者下载 |
| visit_count | INT | default 0 | 访问统计计数器（FR-SHR-03） |
| created_at | DATETIME | | UTC 无时区 |

取消分享（FR-SHR-02）= 删除该分享链接行；访问统计直接读 `visit_count`。

### revoked_tokens（甲，支撑 FR-USER-03/04/05）

JWT 吊销黑名单；`resolve_principal` 在每个请求里用 `session.get(RevokedToken, jti)` 判断存在性。
过期行可由定时任务清理，本系统规模小暂不强制。

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| jti | VARCHAR(64) | PK | 被吊销令牌的 `jti` 声明 |
| user_id | VARCHAR(32) | INDEX | 所属用户 |
| expires_at | DATETIME | NULL | 原令牌过期时间，供清理用 |
| revoked_at | DATETIME | | UTC 无时区 |

---

## 二、OCR 模块表（只读/契约写入，负责人：丙）

| 表 | 关键列 | 主系统的使用方式 |
|---|---|---|
| ocr_files | id(=files.id), owner_id, name, storage_key, media_type, sha256, size, page_count, active_job_id, generation | 由 `ocr.bridge.ensure_ocr_file` 镜像写入 |
| ocr_jobs | id, file_id, generation, owner_id, status, options JSON, attempts, lease_token, lease_until, available_at | 只读；`/ocr-host/files/{id}/jobs` 取最近任务 |
| ocr_pages | id, job_id, page_no, status, revision, result JSON, error；唯一 (job_id, page_no) | 只读 |
| pdf_text_index | file_id, page_no, job_id, revision, content；唯一 (file_id, page_no) | 检索只读；删除时清理 |
| ocr_audit_log | OCR 侧操作记录 | 统计汇总 |

`pdf_text_index.content` 在 MySQL 上建 `FULLTEXT ... WITH PARSER ngram` 索引。

---

## 三、建表与迁移

```bash
python -m backend.scripts.init_db     # 主系统表 + OCR 模块表（同一库）
```

`create_all` 不会迁移已存在的表结构。需求/设计阶段若改表，先删开发库再建；
验收环境如需变更，另写一次性 SQL 脚本并纳入 `docs/`。
