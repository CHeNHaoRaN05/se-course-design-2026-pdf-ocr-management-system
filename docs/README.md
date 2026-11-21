# 文档中心

> 项目：基于本地 OCR 的 PDF 文件显示与管理系统（FastAPI + React/pdf.js + PaddleOCR worker）
> 阅读顺序：项目根 [`README`](../README.md) → [`team/getting-started.md`](team/getting-started.md) → [`development-baseline.md`](development-baseline.md) → 阶段交付物 → 技术参考

## 目录结构

| 目录 | 内容 |
|---|---|
| [`requirements/`](requirements/) | 需求阶段交付物：需求分析文档（Markdown / Word）与一致性审查报告 |
| [`design/`](design/) | 设计阶段交付物：系统设计文档（Markdown / Word）、界面原型设计 |
| [`qa/`](qa/) | 测试审查、复测与远端推送检查报告 |
| [`archive/`](archive/) | 历史版本、订正前备份与过程素材（只读留档，不作为当前基线） |
| [`media/`](media/) | UML、E-R、状态图等建模成图（20 张 PNG） |
| [`prototype/`](prototype/index.html) | 单文件高保真 HTML 界面原型；截图原件在仓库根 `prototype_img/` |
| [`team/`](team/) | 各端开发指南（环境配置、后端、前端、数据库） |
| 根目录 | 架构、数据库、接口契约、开发基线、参考资料等技术文档 |

## 阶段交付物

| 文档 | 内容 |
|---|---|
| [`requirements/需求分析文档.md`](requirements/1/需求分析文档.md) | 需求分析文档 V1.1 源文件 |
| [`requirements/需求分析文档_V1.1.docx`](requirements/需求分析文档_V1.1.docx) | 需求分析文档 Word 正稿 |
| [`design/系统设计文档.md`](design/系统设计文档.md) | 系统设计文档源文件（架构、模块、数据、接口、运行维护） |
| [`design/系统设计文档_V1.0.docx`](design/系统设计文档_V1.0.docx) | 系统设计文档 Word 正稿 |
| [`design/界面原型设计.md`](design/界面原型设计.md) | 15 个界面、20 张原型截图与需求追溯 |
| [`prototype/index.html`](prototype/index.html) | 可离线打开的 HTML 原型 |

## 技术参考

| 文档 | 内容 |
|---|---|
| [`architecture.md`](architecture.md) | 进程视图、最小集接口总表、模块调用关系、跨进程数据流、本地运行视图 |
| [`api-contract.yaml`](api-contract.yaml) | API 契约（OpenAPI 3.0 骨架） |
| [`database-design.md`](database-design.md) / [`er-diagram.mmd`](er-diagram.mmd) | 数据库设计与全局 E-R 图（Mermaid） |
| [`features.md`](features.md) | 功能点与 FR-/NFR- 编号总表 |
| [`development-baseline.md`](development-baseline.md) | 公共限制、成员分工、优先级、验收标准 |
| [`references.md`](references.md) | 引用资料与规范依据 |
| [`../pdf_system/docs/`](../pdf_system/docs/) | 主系统详细设计、数据库设计与契约 C1–C5 原文 |
| [`../pdf_ocr_module/ocr_service/docs/`](../pdf_ocr_module/ocr_service/docs/) | OCR 模块接口与验证文档 |

## 团队、质量与归档

| 文档 | 内容 |
|---|---|
| [`team/getting-started.md`](team/getting-started.md) | 两套 Python 环境、版本矩阵、最小可运行 Demo |
| [`team/backend.md`](team/backend.md) | 三条功能线分工、跨线接口清单 |
| [`team/frontend.md`](team/frontend.md) | 前端目录、HTTP 约定、坐标口径 |
| [`team/database.md`](team/database.md) | 表所有权、schema 冻结规则 |
| [`qa/`](qa/) | 02/03 线测试审查报告、复测报告、远端推送检查 |
| [`archive/`](archive/) | 历史 Word 版本、订正前备份、需求阶段迁出的设计素材 |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 分支、PR 与评审流程 |

> 文档更新规则：阶段交付物的源文件为 Markdown，Word 正稿由 `scripts/export_*_docx.py` 生成；技术参考文档随代码变更同步更新。
