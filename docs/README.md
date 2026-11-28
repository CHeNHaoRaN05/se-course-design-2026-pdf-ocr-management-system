# 文档中心

> 项目：基于本地 OCR 的 PDF 文件显示与管理系统（FastAPI + React/pdf.js + PaddleOCR worker）
> 阅读顺序：项目根 [`README`](../README.md) → [`team/getting-started.md`](team/getting-started.md) → [`development-baseline.md`](development-baseline.md) → 阶段交付物 → 技术参考

## 目录结构

| 目录 | 内容 |
|---|---|
| [`requirements/`](requirements/) | 需求阶段交付物：需求分析文档（Markdown / Word）与一致性审查报告 |
| [`design/`](design/) | 设计阶段交付物：系统设计文档（Markdown / Word）、界面原型设计 |
| [`design/V2.0/`](design/V2.0/README.md) | **V2.0 裁剪后基线**（当前实施口径）：01 需求分析 ~ 09 裁剪说明共 9 篇 + 索引 |
| [`testing/`](testing/) | 软件测试文档（Word 正稿）；测试素材在仓库根 [`test_materials/`](../test_materials/README.md) |
| [`qa/`](qa/) | 仅留被《需求分析文档》正文引用的两份审查报告（证据留存） |
| [`media/`](media/) | UML、E-R、状态图等建模成图（20 张 PNG） |
| [`prototype/`](prototype/index.html) | 单文件高保真 HTML 界面原型；截图原件在仓库根 `prototype_img/` |
| [`team/`](team/) | 各端开发指南（环境配置、后端、前端、数据库） |
| 根目录 | 架构、数据库、接口契约、开发基线、路由清单、参考资料等技术文档 |

> 历史版本（V1.0 需求稿、V1.0 设计稿、各轮审查报告、交接记录）不再随仓库分发，需要追溯时查 git 历史：`git show v2.3.7:docs/archive/...`。

## 阶段交付物

| 文档 | 内容 |
|---|---|
| [`requirements/需求分析文档.md`](requirements/需求分析文档.md) | 需求分析文档 V1.1 源文件（FR-/NFR- 编号基线） |
| [`requirements/需求分析文档_V1.1.docx`](requirements/需求分析文档_V1.1.docx) | 需求分析文档 Word 正稿 |
| [`design/系统设计文档_V2.0.md`](design/系统设计文档_V2.0.md) | 系统设计文档 V2.0 源文件（当前基线） |
| [`design/系统设计文档_V2.0.docx`](design/系统设计文档_V2.0.docx) | 系统设计文档 V2.0 Word 正稿 |
| [`design/界面原型设计.md`](design/界面原型设计.md) | 15 个界面、20 张原型截图与需求追溯 |
| [`testing/软件测试文档_27组.docx`](testing/软件测试文档_27组.docx) | 测试计划、环境与 36 条用例（V1.0 提交版） |
| [`prototype/index.html`](prototype/index.html) | 可离线打开的 HTML 原型 |

## V2.0 裁剪后基线（当前实施口径）

按“最小必须功能集”裁剪后的基线文档，实施、验收与答辩均以此为准：

| 文档 | 内容 |
|---|---|
| [`design/V2.0/README.md`](design/V2.0/README.md) | 基线索引与阅读顺序 |
| [`design/V2.0/01_需求分析.md`](design/V2.0/01_需求分析.md) | 保留功能集与验收口径 |
| [`design/V2.0/02_架构与接口.md`](design/V2.0/02_架构与接口.md) | 进程视图、模块边界、接口总表 |
| [`design/V2.0/03_开发基线与验收.md`](design/V2.0/03_开发基线与验收.md) | 环境矩阵、验收标准 |
| [`design/V2.0/04_API契约.yaml`](design/V2.0/04_API契约.yaml) | 设计期接口快照 |
| [`design/V2.0/09_裁剪说明.md`](design/V2.0/09_裁剪说明.md) | 裁掉了什么、为什么、影响面 |

> 契约口径：`api-contract.yaml` 由实际路由生成（`python -m backend.scripts.export_contract`），
> 是唯一权威；`design/V2.0/04_API契约.yaml` 为设计期快照，供评审对照，不作为实现依据。

## 技术参考

| 文档 | 内容 |
|---|---|
| [`architecture.md`](architecture.md) | 进程视图、最小集接口总表、模块调用关系、跨进程数据流、本地运行视图 |
| [`api-contract.yaml`](api-contract.yaml) | API 契约（OpenAPI 3.0 骨架） |
| [`database-design.md`](database-design.md) / [`er-diagram.mmd`](er-diagram.mmd) | 数据库设计与全局 E-R 图（Mermaid） |
| [`features.md`](features.md) | 功能点与 FR-/NFR- 编号总表 |
| [`development-baseline.md`](development-baseline.md) | 公共限制、成员分工、优先级、验收标准 |
| [`route-inventory.md`](route-inventory.md) | 前后端路由与页面清单 |
| [`references.md`](references.md) | 引用资料与规范依据 |
| [`../pdf_system/docs/`](../pdf_system/docs/) | 主系统详细设计、数据库设计与契约 C1–C5 原文 |
| [`../pdf_ocr_module/ocr_service/docs/`](../pdf_ocr_module/ocr_service/docs/) | OCR 模块接口与验证文档 |

## 团队与质量

| 文档 | 内容 |
|---|---|
| [`team/getting-started.md`](team/getting-started.md) | 两套 Python 环境、版本矩阵、最小可运行 Demo |
| [`team/backend.md`](team/backend.md) | 三条功能线分工、跨线接口清单 |
| [`team/frontend.md`](team/frontend.md) | 前端目录、HTTP 约定、坐标口径 |
| [`team/database.md`](team/database.md) | 表所有权、schema 冻结规则 |
| [`测试审查报告/最小必须功能集实现状态_20261119.md`](测试审查报告/最小必须功能集实现状态_20261119.md) | 裁剪后各功能实现状态的定档依据 |
| [`测试审查报告/功能分层与裁剪建议_20261119.md`](测试审查报告/功能分层与裁剪建议_20261119.md) | 分层与裁剪的判定依据 |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 分支、PR 与评审流程 |

> 文档更新规则：阶段交付物的源文件为 Markdown，Word 正稿由 `scripts/export_*_docx.py` 与 `scripts/build_test_document.py` 生成；技术参考文档随代码变更同步更新。
