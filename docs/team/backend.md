# 后端开发指南（各线详细分工与跨线接口）

> 配套文档：[`../architecture.md`](../architecture.md)（接口总表与调用关系）、[`../api-contract.yaml`](../api-contract.yaml)（接口契约）、[`database.md`](database.md)（表清单与 schema 冻结）、[`../development-baseline.md`](../development-baseline.md)（公共限制）
> 功能点编号见 [`../features.md`](../features.md)「功能模块与需求编号总表」。

---

## 线 01 用户与权限 —— 陈浩然

**编号区间**：`FR-USER-*`（2.2）、`FR-SHR-*`（2.10）、`FR-QTA-*`（2.11）

### 已实现
- 注册、登录、`/auth/me`、JWT 签发与校验
- `core/principal.py`：`current_user` / `require_editor` / `require_admin` / `owned_file`（越权 404）
- 配额预留 / 结算 / 退款、`/quota/overview`
- 审计日志 `audit.py`（已通用化，接受任意表名）

### 待办

| 编号 | 任务 | 位置 | 状态 |
|---|---|---|---|
| FR-USER-01 | 登出、令牌刷新 | `POST /auth/logout`、`POST /auth/refresh` | ✅ 已实现（阶段2） |
| FR-USER-02 | 修改密码 | `POST /auth/change-password`（改密后旧令牌整体失效） | ✅ 已实现（阶段2） |
| FR-USER-03 | 管理员改角色 | `PATCH /auth/users/{id}/role`，复用 `require_admin` | ✅ 已实现（阶段1） |
| FR-USER-04 | 账号禁用 | `User.disabled` 字段+拦截（阶段0）；`PATCH /auth/users/{id}/disabled` 管理端点（阶段2） | ✅ 已实现（阶段2） |
| FR-SHR-01/02/03 | 分享链接（有效期/提取码/允许下载）、取消分享、访问统计 | `modules/share/{router,service,schemas}.py` + `models/share.py`；`core/principal.py` 加旁路解析函数 | ✅ 已实现（阶段1） |
| FR-QTA-04 | 统计看板**前端页面** | `frontend/src/features/stats/StatsPage.tsx`，后端 `/quota/overview` 已就绪 | ✅ 已实现（阶段2） |

### 技术要点
- 分享链接做成**独立 router**，只在 `core/principal.py` 加一个旁路解析函数，不碰主路径
- 分享不复制文件实体，被分享者只读

---

## 线 02 文件管理与阅读器 —— 岳浩睿

**编号区间**：`FR-FILE-*`（2.3）、`FR-READ-*`（2.4）

### 已实现
- 上传（三重校验：扩展名 + MIME + 魔数）、列表分页、详情、内容、页数
- 文件夹（目录树）、标签（多对多）、重命名、软删除、回收站还原、彻底删除
- 书签、批注（增 / 删 / 查）

### 待办

| 编号 | 任务 | 位置 | 状态 |
|---|---|---|---|
| FR-FILE-07 | 批量操作（删 / 移动 / 打标） | `files/router.py` 新增 `POST /files/bulk` | 未开工 |
| FR-FILE-08 | 合并 / 拆分 PDF | `files/router.py:3` 已标注"W7 补"，用 `pypdfium2`（`core/media.py` 已在用） | 未开工 |
| FR-FILE-09 | 文件版本与代次 | 需新增模型字段 → **触发重建开发库** | 未开工 |
| FR-READ-04 | 缩略图侧栏 | `ReaderPage.tsx:79` 有占位文案 | 未开工 |
| FR-READ-05 | 目录大纲 | | 未开工 |
| FR-READ-06 | 页内搜索与命中高亮 | 需 pdf.js `TextLayer` + `findController` | 未开工 |
| FR-READ-08 | 批注**修改**、撤销 | `reader/service.py` 只有 add/remove/list，缺 update | 未开工 |
| FR-READ-09 | OCR 文本层叠加（可选中复制） | 需 `renderTextLayer`，与黄按 C4 对接坐标 | 未开工 |
| FR-READ-10 | 阅读位置记忆 | 前端 localStorage 或后端存 | 未开工 |

### 技术要点
- 批注坐标**按归一化存储**以适配缩放；旋转后坐标需变换（需求 2.4）
- 拆分生成新文件而非修改原文件；合并要求页数不超上限
- 删除前需先取消进行中的任务（调 C5）

---

## 线 03 OCR 与检索 —— 黄俞富

**编号区间**：`FR-OCR-*`（2.5）、`FR-COR-*`（2.6）、`FR-TBL-*`（2.7）、`FR-EXP-*`（2.8）、`FR-SEA-*`（2.9）

### 已实现
- `pdf_ocr_module/ocr_service` 引擎 1313 行，自带 15 个接口（识别、校对、表格、5 种导出、检索）
- 主系统适配层 `modules/ocr/{mount,bridge,quota,lifecycle,router}` 约 320 行
- `modules/search` 检索服务

### 待办

| 编号 | 任务 | 位置 | 状态 |
|---|---|---|---|
| **P0** | **修 MySQL no-op UPDATE 缺陷** | `ocr_service/queue.py` 的 `locked_job` 与 `api.py:223` 的 `correct` 依赖「把字段更新成原值」的 `rowcount`；MySQL 只统计真正变化的行 → worker 无法提交结果、校对恒 409 | **阻塞全组，必须最先做** |
| FR-SEA-04 | 检索过滤（按文件 / 时间 / 标签） | `search/router.py`、`SearchPage.tsx`（58 行） | 未开工 |
| FR-SEA-05 | 检索历史 | 同上 | 未开工 |
| FR-OCR-09 | 准确率评测集（200 页标注） | 需自建标注集 + 评测脚本 | W8 |
| FR-OCR-10 | 手写模式（可选） | `yolo_runner.py` 已留口，需专用 YOLO 权重 | 可选 |

### 技术要点
- worker 是**独立进程 + 独立虚拟环境**（Python 3.12 + paddlepaddle 3.0.0），报错链条最长
- 页面结果与全文索引必须在**同一事务**内写入
- 识别框坐标以**左上原点归一化**返回（C4）
- 模型权重不入库，用 `python -m ocr_service download-models` 按 `models/manifest.json` 下载

---

## 跨线接口清单（含精确签名）

### 陈提供，岳 / 黄调用

| 接口 | 签名 | 实际调用点 |
|---|---|---|
| `core.media.inspect_media` | `(path, *, max_pages, max_pixels) -> (media_type, page_count)` | 岳 `files/service.py:42` |
| `core.media.save_upload` | `(*, storage, key, stream, max_upload_bytes) -> (size, sha256)` | 岳 `files/service.py:40` |
| `core.media.safe_path` | `(storage, key) -> Path`，越界抛 `MediaError` | 岳 `files/router.py:61`；黄 `render_page` |
| `core.media.render_page` | `(path, media_type, page_no, dpi, max_pixels) -> Image.Image` | 黄 worker |
| `core.audit.audit` | `(session, actor_id, action, resource_id, **detail)` | 全员 |
| `quota.reserve` | `(session, user_id, pages, *, ref_id, limit)`，超额抛 429 | 黄 `ocr/quota.py:23` |
| `quota.settle` | `(session, user_id, pages, *, ref_id)` | 黄 `ocr/quota.py:43` |
| `quota.release` | `(session, user_id, pages, *, ref_id)` | 黄 `ocr/quota.py:46,54` |
| `quota.usage` | `(session, user_id) -> dict` | 陈 `ocr/router.py:37` |
| `principal.resolve_principal` | `(request, credentials) -> Principal` | 黄经 `dependency_overrides` 复用 |
| `principal.current_user` / `require_editor` / `require_admin` | FastAPI 依赖 | 全员 |
| `principal.owned_file` | `(session, file_id, user) -> File`，越权/已删统一 404 | 岳、黄 |
| `principal.visible_files` | `(statement, user) -> statement` | 岳、陈 |
| `models.base.now()` / `uid()` | 无参 | 全员（**禁止自己用 `datetime.now()` 或 `uuid4()`**） |

`Principal` 暴露三个成员：`user_id: str`、`role: str`、`is_admin: bool`。
需要新属性（如 `is_editor`）时提 PR 给陈，**不要绕过 Principal 自己查 User 表**。

### 黄提供，陈 / 岳调用

| 接口 | 签名 | 实际调用点 |
|---|---|---|
| `ocr.bridge.ensure_ocr_file` | `(session, file: File)` 幂等写镜像，未挂载时静默返回 `None` | 岳 `files/service.py:64`；黄 `ocr/router.py:47` |
| `ocr.bridge.is_ready` | `() -> bool` | 岳 `files/service.py:62,130,141`；陈 `search/service.py:18` |
| `ocr.bridge.set_ready` | `(value: bool)` | 陈 `mount.py` |
| `ocr.bridge.ocr_file_missing` | `(session, file_id) -> bool` | — |
| `ocr.bridge.active_job_id` | `(session, file_id) -> str \| None` | 岳（删除前判断） |
| `ocr.bridge.latest_job` | `(session, file_id) -> Job` | — |
| `ocr.lifecycle.cancel_tasks` | `(session, file_id) -> int` | 岳 `files/service.py:136` |
| `ocr.lifecycle.purge_file` | `(session, settings, file_id) -> None` | 岳 `files/service.py:147` |
| `ocr.lifecycle.ocr_usage` | `(session, user_id) -> dict` | 陈 `ocr/router.py:37` |
| `ocr.lifecycle.TERMINAL` | `{"succeeded","partial_success","failed","cancelled"}` | 岳 |
| `ocr.quota.make_before_enqueue` | `(settings) -> before_enqueue(session, user, file, page_numbers)` | 陈 `mount.py` 注入 |
| `ocr.quota.settle_job` | `(session, job_id, owner_id, *, reserved_pages, succeeded_pages) -> bool` | 陈 `/ocr-host` 结算端点 |
| `ocr.quota.release_job` | `(session, job_id, owner_id, *, pages) -> bool` | 陈（任务取消时） |
| `ocr.quota.CLOSE_REASON` | `"job_close"` | 陈 |

### 共享枚举与常量（新增取值须全员同步）

| 常量 | 取值 | 位置 |
|---|---|---|
| 角色 | `user` / `viewer` / `admin` | `principal.py:16` `ROLES` |
| 任务终态 | `succeeded` / `partial_success` / `failed` / `cancelled` | `ocr/lifecycle.py:15` `TERMINAL` |
| 批注类型 | `highlight` / `note` / `ink` | `models/reader.py:29` `kind` |
| 媒体类型 | `application/pdf` / `image/png` / `image/jpeg` | `core/media.py` |
| 配额流水 reason | `reserve` / `settle_reserve` / `settle_used` / `release` / `job_close` | `quota/service.py`、`ocr/quota.py` |

### ⚠️ 两份 `media.py` 的同步义务

`backend/core/media.py` 的 docstring 明确写了：OCR 模块为了「独立可部署」自带一份 `media.py`，
**两者输入输出契约一致（media_type / page_count / sha256 / size），属有意重复**。

**任何一侧修改校验规则，都必须同步另一侧**（契约 C2）。
例如岳提高了页数上限而黄没同步 → 上传成功但 worker 渲染失败，且报错指向 OCR 侧，极难定位。
