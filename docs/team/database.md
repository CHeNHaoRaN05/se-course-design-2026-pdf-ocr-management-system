# 数据库开发指南（表所有权 · Schema 冻结 · 共享字段）

> 配套文档：[`../database-design.md`](../database-design.md)（表设计总览与 E-R 图）、[`../er-diagram.mmd`](../er-diagram.mmd)、[`../../pdf_system/docs/DATABASE.md`](../../pdf_system/docs/DATABASE.md)（详细设计）、契约 C2（`../../pdf_system/docs/contracts/C2-file.md`）
> 公共限制见 [`../development-baseline.md`](../development-baseline.md)。

---

## 1. 两套 DeclarativeBase

两个 `DeclarativeBase`：主系统 `backend/models/base.py` 的 `Base`，OCR 模块 `ocr_service/db.py` 的 `Base`。
**两套 Base 不共用**，因此 OCR 表不会被主系统 `create_all` 误建，也不要把 OCR 表定义搬进 `backend/models/`。

## 2. Schema 冻结规则（最大扯皮点）

`backend/scripts/init_db.py:14` 用的是 `Base.metadata.create_all()`，**不会迁移已存在的表**（脚本注释已写明）。

三人并行加字段 → 各人本地库结构分叉 → 合并后别人机器上跑出 500，且报错不指向根因，极难排查。

**规则：**

1. **W5 结束前定稿冻结** schema，陈牵头补齐缺口（目前 `share_link` 表在 `pdf_system/docs/DATABASE.md` 已设计，但 `backend/models/` 里**没有对应模型**）
2. 冻结后新增/修改字段必须走 PR，合并人在 PR 说明中标注「需重建开发库」
3. 全组执行 `.\scripts\reset_dev_db.ps1`
4. 演示前一周停止一切 schema 变更

## 3. 主系统表（`backend/models/`）

| 表 | 主责 | 字段 | 被谁读 / 写 |
|---|---|---|---|
| `users` | 陈 | id, email, display_name, password_hash, **role**(user/viewer/admin), **disabled**, login_count, created_at, last_login_at | 黄：`resolve_principal` 校验 `disabled`；陈 |
| `files` | 岳 | id, **owner_id**, name, folder, **storage_key**, **media_type**, **sha256**, size, **page_count**, version, replaced_from, **deleted_at**, created_at | **黄镜像其中 8 个字段**；陈：`search`/`owned_file`/`visible_files` |
| `tags` | 岳 | id, owner_id, name | 岳 |
| `file_tags` | 岳 | file_id, tag_id（多对多关联表） | 岳 |
| `bookmarks` | 岳 | id, file_id→files.id, owner_id, page_no, title, created_at | 岳 |
| `annotations` | 岳 | id, file_id→files.id, owner_id, page_no, kind, **payload(JSON)**, created_at, updated_at | 岳；**payload 坐标口径须与 OCR bbox 一致（C4）** |
| `quota_accounts` | 陈 | user_id + month（复合主键）, **pages_reserved**, **pages_used**, updated_at | **黄写**（经 reserve/settle/release） |
| `quota_ledger` | 陈 | id, user_id, month, **pages**（正=占用，负=退还）, reason, **ref_id**, created_at | **黄写** |
| `audit_logs` | 陈 | id, actor_id, action, resource_id, detail(JSON), created_at | 全员写 |

## 4. OCR 模块表（`pdf_ocr_module/ocr_service/db.py`）

| 表 | 主责 | 字段 | 被谁读 |
|---|---|---|---|
| `ocr_files` | 黄 | **id（=files.id，同值）**, owner_id, name, storage_key, media_type, sha256, size, page_count, active_job_id, generation, created_at | 岳（经 `bridge`） |
| `ocr_jobs` | 黄 | id, file_id, generation, owner_id, status, options(JSON), attempts, lease_token, lease_until, available_at, created_at, finished_at | 岳（`cancel_tasks`） |
| `ocr_pages` | 黄 | id, job_id, page_no, status, revision, result(JSON), error | 黄 |
| `pdf_text_index` | 黄 | id, file_id, page_no, job_id, revision, **content**, updated_at | **陈直接 SQL join（`search/service.py:26-41`）** |
| `ocr_audit_log` | 黄 | id, actor_id, action, resource_id, detail, created_at | 陈（统计时与 `audit_logs` 合并） |

## 5. 跨线共享字段：改这些 = 契约变更

| 字段 | 归属 | 谁依赖 | 改错后的症状 |
|---|---|---|---|
| `files.id` | 岳 | 黄用它作 `ocr_files.id`（`bridge.py:33`）；bookmarks/annotations 外键 | 两边 id 对不上，OCR 建任务失败 |
| `files.storage_key` | 岳 | 黄镜像；**两边共用同一存储目录** | worker 读不到文件 |
| `files.owner_id` | 岳 | 黄镜像；陈 `search.service.py:34` 权限过滤 | 越权或检索结果为空 |
| `files.media_type` | 岳 | 黄镜像；`render_page` 按它分支 PDF/图片 | 渲染失败 |
| `files.page_count` | 岳 | 黄镜像；**决定配额预留页数** | 配额算错 |
| `files.deleted_at` | 岳 | 陈 `search`/`visible_files`/`owned_file` 均按它过滤 | 回收站文件仍被检索到 |
| `files.version`、`replaced_from` | 岳 | 合并/拆分产生新版本（FR-FILE-09） | 版本链断裂 |
| `annotations.payload` | 岳 | 与黄 OCR bbox 同口径：**左上原点、归一化** | 覆盖层错位 |
| `pdf_text_index.content` | 黄 | 陈 `MATCH AGAINST` / `LIKE` 直接查 | 检索 500 |
| `pdf_text_index.job_id`、`revision` | 黄 | 陈用于标注来源、避免展示过期文本 | 展示旧文本 |
| `quota_accounts.pages_reserved/used` | 陈 | 黄写 | 配额错乱、429 误报 |
| `QuotaLedger.ref_id` | 陈 | 黄：预留时 `ref_id=None`（拿不到 job_id），终态时按 job 回填 | 对账断链 |
