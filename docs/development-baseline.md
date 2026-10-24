# 开发基线（公共限制 · 分工 · 优先级 · 验收）

> 项目：基于本地 OCR 的 PDF 文件显示与管理系统
> 小组成员：陈浩然（组长，2024141460570）、黄俞富（2024141460074）、岳浩睿（2024141460114）
> 配套文档：[`architecture.md`](architecture.md)（接口与调用关系）、[`api-contract.yaml`](api-contract.yaml)（接口契约）、[`team/`](team/)（各端开发指南）、[`CONTRIBUTING.md`](../CONTRIBUTING.md)（协作流程）
>
> **第 0 节是公共限制，动手写代码前必须读完。** 违反其中任何一条都会导致全组返工或联调失败。

---

# 第 0 节 公共限制（三人必读）

## 0.1 共享文件所有权

下列文件被多人依赖，**改动必须先开 PR**。CODEOWNERS 已配置，GitHub 会自动指派 reviewer。

| 路径 | 主责 | 规则 |
|---|---|---|
| `backend/core/**` | 陈 | 仅陈可合并。加配置项**必须给默认值**，不得强制他人改 `.env` |
| `backend/core/principal.py` | 陈 | **只有陈能改**。分享功能要旁路 JWT 时，新增一个解析函数，**不许改 `resolve_principal` 主路径**（第 31–49 行） |
| `backend/models/base.py`、`__init__.py` | 陈 | 仲裁。`__init__.py` 按线分区，各人只碰自己那一段 |
| `backend/models/{user,quota,audit}.py` | 陈 | |
| `backend/models/{file,reader}.py` | 岳 | 但黄的 `ocr/bridge.py:25-45` 逐字段镜像 `File`，改动视为契约变更 |
| `backend/main.py` | 陈 | 装配入口 |
| `frontend/src/shared/**` | 陈 | `types.ts` 按线分区 |
| `frontend/src/app/**` | 陈 | 路由由陈统一加，其余人提需求 |
| `pdf_ocr_module/**` | 黄 | 但 `db.py` 的 `pdf_text_index` 被陈的 `search/service.py:26-51` 直接 SQL join，改动视为契约变更 |

## 0.2 Python 版本

| 进程 | 版本 | 原因 |
|---|---|---|
| 主系统 API | 3.12 / 3.13 / 3.14 均可 | `api.py` 顶层不 import paddle |
| OCR worker | **必须 ≤ 3.13，统一用 3.12** | `paddlepaddle==3.0.0` 最高只提供 cp313 wheel，无 cp314 |

`requirements.txt` 主组锁的是 3.12 版本组；本机 `.venv` 是用文件末尾「Python 3.14 可用版本」装的备用组。**两者不是同一套版本**，交付前必须统一，否则本地与部署漂移。

## 0.3 三个环境变量必须一致

| 变量 | 必须与谁一致 |
|---|---|
| `PDF_DATABASE_URL` == `OCR_DATABASE_URL` | 同一个库 |
| `PDF_STORAGE_DIR` == `OCR_STORAGE` | 同一目录，否则 worker 读不到文件 |
| `PDF_JWT_SECRET` == `OCR_JWT_SECRET` | 同一把密钥，短于 32 字符直接抛错 |

Python 版本**允许不同**（主系统 3.14 + worker 3.12），这是原设计的进程隔离带来的好处。

## 0.4 分支与提交

- 分支：`feat/<线号>-<功能>`（如 `feat/02-merge`），生命周期 **≤ 3 天**
- 提交信息：`[01] 配额退款修复`，线号用于统计个人贡献
- 每天开工 `git pull --rebase origin main`
- 只能 PR 合入 `main`，至少 1 人 review 且**优先跨线**
- 完整流程见 [`CONTRIBUTING.md`](../CONTRIBUTING.md)

## 0.5 禁止事项

| 禁止 | 原因 |
|---|---|
| 提交 `.env`、密钥、`*.sqlite3`、模型权重 | 安全 + GitHub 单文件 100 MB 限制 |
| 修改 `resolve_principal` 主路径 | 全局安全路径，多人改必出越权漏洞 |
| 把模型权重（`*.pdparams`，204 MB）入库 | 超 GitHub 限制，push 必失败 |
| 从 GitHub 模板复制 `.gitignore` 时保留 `build/` 一行 | 根目录 `build/` 是文档生成脚本源码，会被误排除 |
| `force push main` | 会覆盖他人提交 |
| 改别人线的依赖版本 | `requirements.txt` 版本漂移，装不上 |

## 0.6 统一约定

- 后端：`snake_case`，路由前缀 `/api/v1/`
- 前端：组件 `PascalCase`，变量/函数 `camelCase`
- 所有中文文档 UTF-8
- 分页参数统一 `limit` / `offset`
- 越权统一返回 **404 而非 403**（避免资源探测，见需求 2.2）
- 错误响应统一走 `core/errors.py` 的 `bad_request / conflict / not_found`，不要自己 `raise HTTPException`

## 0.7 契约 C1–C5：先改文档，后改代码

| 契约 | 内容 | 调用方 → 被调用方 |
|---|---|---|
| C1 | JWT 走 `Authorization` 头，主系统签发、OCR 模块验签 | 陈 → 黄 |
| C2 | `ocr.bridge.ensure_ocr_file()` 镜像文件 | 岳 → 黄 |
| C3 | `quota.reserve()` 入队扣配额 | 黄 → 陈 |
| C4 | 覆盖层归一化坐标 | 黄 → 岳 |
| C5 | `ocr.lifecycle.cancel_tasks() / purge_file()` | 岳 → 黄 |

**铁律：改契约先改 `pdf_system/docs/contracts/C*.md` 并单独提 PR，其余两人确认后再动代码。**
反过来的代价：黄改了 `bridge.py` 签名，岳那边直接 500，两人各查半天。

> 数据库 Schema 冻结规则与表清单见 [`team/database.md`](team/database.md)；跨线接口清单见 [`team/backend.md`](team/backend.md)。

---

# 第 1 节 成员与职责总览

| 功能线 | 成员 | GitHub | 负责模块 | 需求章节 | 主要代码路径 |
|---|---|---|---|---|---|
| 01 | 陈浩然（组长） | `@CHeNHaoRaN05` | 用户与权限、分享与协作、配额/日志/统计 | 2.2、2.10、2.11 | `backend/modules/{auth,quota}`、`backend/core/**`、`frontend/src/features/auth` |
| 02 | 岳浩睿 | `@zhimengshusi` | 文件管理、PDF 阅读器 | 2.3、2.4 | `backend/modules/{files,reader}`、`frontend/src/features/{files,reader}` |
| 03 | 黄俞富 | `@smile1810` | OCR 识别、校对、表格还原、导出、全文检索 | 2.5、2.6、2.7、2.8、2.9 | `backend/modules/{ocr,search}`、`pdf_ocr_module/**`、`frontend/src/features/{ocr,search}` |

组长额外职责：`core/` 与 `main.py` 的维护、全组 PR review、schema 定稿、部署脚本。

各线详细任务与跨线接口见 [`team/backend.md`](team/backend.md)，前端约定见 [`team/frontend.md`](team/frontend.md)。

---

# 第 2 节 任务优先级与合并顺序

## 2.1 优先级（前两项是阻塞项）

| 优先 | 线 | 任务 | 说明 |
|---|---|---|---|
| **P0** | 03 黄 | 修 MySQL no-op UPDATE 缺陷 | 不修则所有人联调 OCR 全部卡死 |
| **P0** | 01 陈 | schema 定稿冻结（补齐 `share_link` 等模型） | 不冻结则后续改表引发全组重建 |
| P1 | 01 陈 | 分享与协作 | 唯一要动 `core/principal.py` 的需求，越晚做被卡的人越多 |
| P1 | 02 岳 | 合并 / 拆分 PDF | 纯增量，依赖已就绪的上传落盘 |
| P1 | 03 黄 | 检索过滤与历史 | |
| P2 | 02 岳 | 缩略图、页内搜索、批注修改 | 前端增量 |
| P2 | 01 陈 | 统计看板前端 | 后端已就绪，缺页面 |
| P2 | 01 陈 | 管理员改角色、登出/刷新/改密码 | |
| P2 | 02 岳 | 批量操作 | |
| P3 | 03 黄 | OCR 准确率评测集 | 需人工标注 200 页 |

## 2.2 合并顺序（按依赖排）

```
schema 定稿（陈）
      ↓
quota（陈）  ←── ocr（黄）依赖它（C3）
      ↓
ocr（黄）    ←── files（岳）依赖它（C2、C5）
      ↓
files（岳）
      ↓
share / admin-role（陈）、merge / bulk（岳）、search-filter（黄）   ← 并行，无依赖
```

**同一时间多个 PR 待合：先合被依赖方。** 顺序错了，后合的人要 rebase 两次。

---

# 第 3 节 时间节点

| 周次 | 目标 |
|---|---|
| W5 | schema 定稿冻结；黄修完 MySQL 缺陷；三人各自跑通本地环境 |
| W6 | 各线 P1 任务完成；跨线契约联调（C2 / C3 / C5） |
| W7 | P2 任务；前端页面补齐；OCR 准确率评测 |
| W8 | 测试补全（合并/拆分、分享、校对 409 冲突三块无测试）；文档定稿；部署演练 |

---

# 第 4 节 验收标准

## 4.1 每人交付前自检

- [ ] 本线所有功能点在 Swagger（http://127.0.0.1:8000/docs）中可调通
- [ ] 本地 `pytest` 通过
- [ ] 未提交 `.env` / 密钥 / 数据库文件 / 模型权重
- [ ] 若改了共享文件或 schema，已在 PR 中说明并通知全组
- [ ] 提交信息带线号 `[01]` / `[02]` / `[03]`

## 4.2 全链路验收（三人共同）

上传 → 落盘 → 镜像 → 建任务 → worker 领取 → 识别 → 回写 → 检索，全链路跑通；
`GET /health` 返回 `{"status":"ok","ocr_mounted":true,...}`。

## 4.3 需求文档追踪

分工表中的编号需与需求文档第 2 章小节对应（2.2 → `FR-USER`，2.3 → `FR-FILE`，2.4 → `FR-READ`，2.5 → `FR-OCR`，2.6 → `FR-COR`，2.7 → `FR-TBL`，2.8 → `FR-EXP`，2.9 → `FR-SEA`，2.10 → `FR-SHR`，2.11 → `FR-QTA`）。
需求编号总表见 [`features.md`](features.md) 的「功能模块与需求编号总表」。

---

# 第 5 节 仲裁规则

| 争议类型 | 仲裁人 |
|---|---|
| 本线内部 | 自己定 |
| 跨线接口 / 契约 | 全体讨论，陈拍板 |
| `core/` 与 `shared/` 改动 | 陈 |
| 需求范围 | 对照 [`features.md`](features.md) 章节编号，文档为准 |
