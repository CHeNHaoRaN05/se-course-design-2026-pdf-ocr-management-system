# 参考资料与相关文档

## 仓库内

| 文档 | 内容 |
|---|---|
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 协作流程：分支、PR、review 规则 |
| [`../LICENSE`](../LICENSE) | 开源许可证 |
| [`../需求分析文档.docx`](../需求分析文档.docx) | 课程交付物：需求分析文档（Word 正稿） |
| [`../pdf_system/docs/ARCHITECTURE.md`](../pdf_system/docs/ARCHITECTURE.md) | 主系统详细设计 |
| [`../pdf_system/docs/DATABASE.md`](../pdf_system/docs/DATABASE.md) | 数据库详细设计（含 `share_link` 等待建表） |
| [`../pdf_system/docs/contracts/`](../pdf_system/docs/contracts/) | 跨线契约 C1–C5 原文（改契约先改这里） |
| [`../pdf_ocr_module/`](../pdf_ocr_module/) | OCR 引擎源码（`ocr_service`，含 `models/manifest.json`） |

## 本目录

| 文档 | 内容 |
|---|---|
| [`architecture.md`](architecture.md) | 接口总表与调用关系（48 个接口） |
| [`api-contract.yaml`](api-contract.yaml) | API 契约（OpenAPI 骨架） |
| [`database-design.md`](database-design.md) / [`er-diagram.mmd`](er-diagram.mmd) | 数据库设计与 E-R 图 |
| [`features.md`](features.md) | 需求分析与功能点编号总表 |
| [`development-baseline.md`](development-baseline.md) | 公共限制、优先级、验收标准 |
| [`team/`](team/) | 各端开发指南（backend / frontend / database / getting-started） |

## 外部资料

- [FastAPI 文档](https://fastapi.tiangolo.com/zh/) — Web 框架
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/) — ORM
- [PaddleOCR 文档](https://paddlepaddle.github.io/PaddleOCR/) — 本地 OCR 引擎（paddlepaddle 3.0.0，Python ≤ 3.13）
- [pdf.js 文档](https://mozilla.github.io/pdf.js/) — 前端渲染（`TextLayer` / `findController` / `renderTextLayer`）
- [MySQL 8.0 全文索引（ngram）手册](https://dev.mysql.com/doc/refman/8.0/en/fulltext-search-ngram.html)
- [Mermaid ER 图语法](https://mermaid.js.org/syntax/entityRelationshipDiagram.html) — `er-diagram.mmd` 渲染
- [IEEE 830 / ISO-IEC 25010](https://www.iso.org/standard/35733.html) — 需求文档规范依据

## 图表与 UML

需求文档的 PlantUML 源码约定提交到 `docs/uml/`（待建），E-R 图已先以 Mermaid 形式落在 [`er-diagram.mmd`](er-diagram.mmd)。
