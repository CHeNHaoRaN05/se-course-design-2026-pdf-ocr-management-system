# 协作规范

三人纵向功能线：**01 用户与权限（陈浩然）／02 文件管理与阅读器（岳浩睿）／03 OCR 与检索（黄俞富）**。

本文件解决两件事：共享物归谁改、分支怎么合。

---

## 一、分支模型

采用 **trunk-based + 短生命周期分支**。

```
main                    受保护，永远处于可演示状态
├── feat/01-share       陈
├── feat/01-admin-role  陈
├── feat/02-merge       岳
├── feat/02-bulk        岳
├── feat/03-correct     黄
└── fix/<线号>-<问题>    谁发现谁修
```

| 规则 | 说明 |
|---|---|
| 命名 | `feat/<线号>-<功能>`、`fix/<线号>-<问题>`、`docs/<内容>` |
| 生命周期 | **≤ 3 天**，超期必须拆分后合并 |
| 同步 | 每天开工先 `git pull --rebase origin main` |
| 合并 | 只能走 PR，**禁止直接 push main** |
| Review | 至少 1 人，且**优先跨线**（避免同线互相看不出问题） |

## 二、提交信息

```
[01] 配额退款修复
[02] 上传三重校验
[03] 覆盖层坐标换算
```

线号便于统计个人贡献（答辩会被问到）。

## 三、共享物所有权（防扯皮核心）

三个共享物：**`backend/core/`、`backend/models/`、`docs/contracts/`**。

### 3.1 `backend/core/`（陈维护）

| 情况 | 处理 |
|---|---|
| 加配置项（`config.py`） | 提 PR 给陈，**自带默认值**，不强制他人改 `.env` |
| 加错误码（`errors.py`） | 提 PR 给陈，复用现有 `bad_request / conflict / not_found` 语义 |
| 改鉴权（`principal.py`） | **仅陈可改**，其余两人不得直接修改 |

> 为什么 `principal.py` 只有陈能改：分享功能要旁路 JWT（`resolve_principal` 31-49 行），这是全局安全路径，多人改必出越权漏洞。

### 3.2 `backend/models/`（按线分，冲突集中在 `__init__.py`）

| 文件 | 归属 |
|---|---|
| `base.py`、`__init__.py` | 陈（仲裁） |
| `user.py`、`quota.py`、`audit.py` | 陈 |
| `file.py`、`reader.py` | 岳 |

**`__init__.py` 冲突预防**：按线分区，各自动手时只碰自己那一段：

```python
# ---- 01 用户与权限（陈）----
from .user import User
from .quota import QuotaAccount, QuotaLedger, current_month
from .audit import AuditLog

# ---- 02 文件管理与阅读器（岳）----
from .file import File, Tag, file_tags
from .reader import Annotation, Bookmark

from .base import Base, now, uid
```

### 3.2.1 ⚠️ 数据库 schema 变更（最大扯皮点）

`backend/scripts/init_db.py:14` 用的是 `Base.metadata.create_all()`，**不会迁移已存在的表**（脚本注释已写明）。

三人并行加字段 → 各人本地库结构不一致 → 合并后别人机器上跑出 500，且报错信息不指向根因，极难排查。

**约定**：

1. **W5 前定稿冻结** schema：陈牵头，把 `share_link` 表（`docs/DATABASE.md` 已设计但 `backend/models/` 里还没有对应模型）等缺口一次补齐，推 `main`
2. 冻结后**新增/修改字段必须走 PR**，合并人在 PR 里写明「需重建开发库」
3. 全组执行：
   ```powershell
   .\scripts\reset_dev_db.ps1
   ```
4. 开发期数据全是测试数据，**重建不心疼**；演示前停止改 schema

### 3.3 `frontend/src/shared/`（陈维护）

`types.ts` 按线分区注释，各线只在自己区段加类型。`http.ts`、`app/` 由陈维护。

## 四、契约变更规则

`docs/contracts/C1–C5` 是三人的接口合同，对应三个跨线调用：

| 契约 | 调用 |
|---|---|
| C2 | files（岳）→ `ocr.bridge.ensure_ocr_file()`（黄） |
| C3 | ocr（黄）→ `quota.reserve()`（陈） |
| C5 | files（岳）→ `ocr.lifecycle.cancel_tasks() / purge_file()`（黄） |

**铁律：先改文档，再改代码。**

1. 改 `docs/contracts/C*.md` → 单独开 PR
2. 其余两人确认
3. 再动代码

反过来的代价：黄改了 `bridge.py` 的签名，岳那边直接 500，两人各查半天。

## 五、冲突热点与预防

| 文件 | 冲突原因 | 预防 |
|---|---|---|
| `backend/models/__init__.py` | 甲乙都加导出 | 按线分区，不动别人的行 |
| `backend/core/config.py` | 三人加配置项 | 按线分区 + 都给默认值 |
| `backend/core/errors.py` | 三人加错误码 | 优先复用，新增走 PR |
| `frontend/src/shared/types.ts` | 三人加类型 | 按线分区 |
| `frontend/src/app/router.tsx` | 三人加路由 | **由陈统一加**，其余人提需求 |
| `backend/main.py` | 装配入口 | 仅陈改 |
| `pdf_ocr_module/` | OCR 引擎 | 仅黄改 |

## 六、合并顺序（按依赖排）

```
schema 定稿（陈）
      ↓
quota（陈）  ←── ocr（黄）依赖它
      ↓
ocr（黄）    ←── files（岳）依赖它
      ↓
files（岳）
      ↓
share / admin-role（陈）、merge / bulk（岳）、correct（黄）
      ↑
   独立功能，并行无依赖
```

**同一时间多个 PR 待合：先合被依赖方。** 顺序错了，后合的人要 rebase 两次。

## 七、本地启动

```powershell
# 首次
cd pdf_system
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env        # 然后改 PDF_JWT_SECRET（≥32 字符）
.\.venv\Scripts\python.exe -m backend.scripts.init_db

# 日常
.\.venv\Scripts\python.exe -m uvicorn backend.main:create_app --factory --port 8000
```

无 Python 3.12 时可用 conda 替代（见 README 第五节）。

---

## 八、仲裁规则

| 争议类型 | 仲裁人 |
|---|---|
| 本线内部 | 自己定 |
| 跨线接口/契约 | 全体讨论，陈拍板 |
| `core/` 与 `shared/` 改动 | 陈 |
| 需求范围 | 对照需求文档编号，文档为准 |
