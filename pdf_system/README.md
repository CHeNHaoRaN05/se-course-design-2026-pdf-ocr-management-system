# PDF 文件显示与管理系统

基于本地 OCR 的 PDF 文件显示与管理系统。后端 FastAPI + MySQL 单体，前端 React + pdf.js，
OCR 能力来自同仓库外的独立模块 `../pdf_ocr_module/ocr_service`（PaddleOCR 本地推理）。

三人纵向分工：**01 用户与权限（甲）／02 文件管理与阅读器（乙）／03 OCR 与检索（丙）**。
详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 与 [docs/contracts/](docs/contracts/) 的 C1–C5 契约。

---

## 〇、当前状态（已实测）

在本机（Windows / Python 3.14）真实跑通：

| 项 | 结果 |
|---|---|
| `uvicorn backend.main:create_app --factory` 启动 | ✅ `/health` → `{"status":"ok","ocr_mounted":true,"database":"sqlite"}` |
| `/docs` 打开 | ✅ 200，共 **42 个端点**（主系统 21 + OCR 模块 20 + health） |
| 后端 pytest | ✅ **18 passed**（`python -m pytest backend/tests`） |
| 真实 HTTP 全链路 | ✅ 注册 → 登录 → 上传 → 列表 → 取原文 → 配额 → 检索 |
| OCR 模块挂载 | ✅ 无需 Paddle 权重即可挂载（`install()` 只建 DB 连接，推理引擎懒加载） |
| 前端 | ❌ 本机无 Node，**未实测**；需 `npm install && npm run dev` |

已固化到 `backend/tests/`：`test_main_flow.py`（甲+乙 13 项）、`test_ocr_contract.py`（丙 5 项，覆盖 C1/C2/C3/C5）。
OCR 测试在未装 `cv2` 的机器上会自动 skip，主系统测试不受影响。

## 一、启动

### 1. 后端（主系统）

```bash
cd pdf_system
python -m venv .venv && .venv/Scripts/activate      # Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                  # 至少改 PDF_JWT_SECRET（≥32 字符）
python -m backend.scripts.init_db                     # 建主系统表 + OCR 模块表
uvicorn backend.main:create_app --factory --host 127.0.0.1 --port 8000
python -m pytest backend/tests -q                     # 18 项，应全绿
```

> **Python 版本**：推荐 **3.12**（与 OCR worker 的 `.venv-paddle` 同版本）。
> Python 3.14 上 `requirements.txt` 的锁版本装不上（`pydantic-core` 无 cp314 wheel，需 Rust），
> 请改用文件末尾「Python 3.14 可用版本」那一段。

打开 http://127.0.0.1:8000/docs 查看接口（OCR 的 15 个接口在 `/api/v1/ocr` 分组下）。

### 2. OCR Worker（独立环境，负责人：丙）

```bash
cd ..                                                 # 仓库根
py -3.12 -m venv .venv-paddle
.venv-paddle/Scripts/python.exe -m pip install -r ../pdf_ocr_module/ocr_service/environment-service-lock.txt
.venv-paddle/Scripts/python.exe -m ocr_service download-models

# 与主系统共享同一个数据库和存储目录
export OCR_DATABASE_URL="mysql+pymysql://pdf_user:pdf_pwd@127.0.0.1/pdf_system?charset=utf8mb4"
export OCR_STORAGE="$(pwd)/pdf_system/data/storage"
export OCR_JWT_SECRET="<与 PDF_JWT_SECRET 相同>"
.venv-paddle/Scripts/python.exe -m ocr_service worker
```

> 未安装 Paddle 环境也能启动后端：`mount_ocr` 会降级，`/health` 返回 `ocr_mounted: false`，
> 除 OCR 外的功能全部可用。

### 3. 前端

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173，/api 已代理到 8000
```

---

## 二、目录与归属

| 路径 | 负责人 | 说明 |
|---|---|---|
| `backend/core/` | 甲 | 配置、数据库、鉴权、审计、媒体校验（共享底座，改动走 PR） |
| `backend/models/` | 甲（user/quota/audit）、乙（file/tag/reader） | ORM |
| `backend/modules/auth`、`quota` | 甲 | 功能 1–6 |
| `backend/modules/files`、`reader` | 乙 | 功能 7–12 |
| `backend/modules/ocr`、`search` | 丙 | 功能 13–18 |
| `backend/main.py` | 甲 | 装配 |
| `frontend/src/app`、`shared` | 甲 | 路由、鉴权上下文、请求封装、共享类型 |
| `frontend/src/features/auth` | 甲 | |
| `frontend/src/features/files`、`reader` | 乙 | |
| `frontend/src/features/ocr`、`search` | 丙 | |
| `docs/` | 全体 | ARCHITECTURE / DATABASE / contracts |

---

## 三、协作规则

1. **分支**：`main` 受保护；每人从 `feat/<线>-<功能>` 开分支，PR 至少 1 人 review 后合并。
2. **契约优先**：`docs/contracts/C1–C5` 是三人的接口合同，改契约必须先改文档再改代码。
3. **底座不动**：`core/` 与 `shared/` 的改动必须开 PR 说明影响面。
4. **提交信息**：`[01] 配额退款修复` / `[02] 上传校验` / `[03] 覆盖层坐标`，便于统计个人贡献。

---

## 四、W7 迭代清单

| 线 | 待补功能 |
|---|---|
| 01 | 分享链接签发与校验、管理员改角色 |
| 02 | 合并/拆分、批量操作、缩略图、页内搜索 |
| 03 | 手写模式（需专用 YOLO 权重）、OCR 准确率评测集 |
| 03 | **必修**：OCR 模块在 MySQL 下的 no-op UPDATE 缺陷（见 ARCHITECTURE 第八节） |

---

## 五、注意事项

* `PDF_JWT_SECRET` 与 `OCR_JWT_SECRET` 必须是同一把（≥32 字符），否则 OCR 接口全部 401。
* `PDF_STORAGE_DIR` 与 `OCR_STORAGE` 必须是同一目录，否则 OCR 读不到上传的文件。
* MySQL 需 8.0+ / InnoDB / utf8mb4；ngram 分词默认 `token_size=2`，单字查询退化为 LIKE。
* 当前仓库不含模型二进制、数据库、密钥与缓存，均不在交付包内。
