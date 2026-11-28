# se-course-design-2026-pdf-ocr-management-system
基于 Python 的本地 PDF 文件管理与显示系统，支持上传、下载、在线阅读、文件管理，以及 OCR 识别链路跑通（提交任务、查看结果与导出、全文检索）。A software engineering course project for local PDF management, display and OCR recognition.

交付范围按最小必须功能集裁剪，范围外项见 [`docs/features.md`](docs/features.md) 1.2。

## 本机启动

准备好 Paddle Python 环境、OCR 权重以及 Node.js，在 `pdf_system/frontend` 执行一次 `npm ci`。按[环境配置指南](docs/team/getting-started.md)配置 `pdf_system/.env`，单机演示可使用 SQLite。

在仓库根目录进入主系统目录，用可导入 Paddle 的 Python 启动：

```powershell
cd pdf_system
python -m backend.scripts.run_local
```

启动器初始化数据库表，使用同一份配置启动 API 和 OCR worker，然后启动前端。看到 `Local system ready` 后访问 [本机系统](http://127.0.0.1:5173)。按 Ctrl+C 停止三项服务。

## 文档

完整文档见 [`docs/README.md`](docs/README.md)（文档中心）：

| 文档 | 内容 |
|---|---|
| [`docs/requirements/`](docs/requirements/) | 需求分析文档（Markdown 与 Word 正稿） |
| [`docs/design/系统设计文档_V2.0.md`](docs/design/系统设计文档_V2.0.md) | 系统设计文档（架构、数据、接口、运行维护） |
| [`docs/design/界面原型设计.md`](docs/design/界面原型设计.md) | 界面原型说明与截图索引 |
| [`docs/testing/软件测试文档_27组.docx`](docs/testing/软件测试文档_27组.docx) | 软件测试计划与 36 条用例（Word 正稿） |
| [`test_materials/`](test_materials/README.md) | 测试素材与使用说明（供各成员各自跑用例） |
| [`docs/architecture.md`](docs/architecture.md) | 系统架构与接口总表 |
| [`docs/api-contract.yaml`](docs/api-contract.yaml) | API 契约（OpenAPI） |
| [`docs/database-design.md`](docs/database-design.md) / [`docs/er-diagram.mmd`](docs/er-diagram.mmd) | 数据库设计与 E-R 图 |
| [`docs/features.md`](docs/features.md) | 功能点与需求编号总表 |
| [`docs/development-baseline.md`](docs/development-baseline.md) | 公共限制、分工、优先级与验收 |
| [`docs/team/`](docs/team/) | 各端开发指南（后端 / 前端 / 数据库 / 环境配置） |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 协作流程 |
