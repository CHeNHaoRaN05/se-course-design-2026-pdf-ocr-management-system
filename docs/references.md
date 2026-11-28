# 引用资料与规范依据

## 仓库内资料

| 资料 | 内容 |
|---|---|
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 协作流程：分支、PR、评审规则 |
| [`../LICENSE`](../LICENSE) | 开源许可证 |
| [`requirements/需求分析文档_V1.1.docx`](requirements/需求分析文档_V1.1.docx) | 需求阶段 Word 正稿（FR-/NFR- 编号基线） |
| [`design/系统设计文档_V2.0.md`](design/系统设计文档_V2.0.md) | 系统设计基线（V2.0，当前交付口径） |
| [`../pdf_system/docs/ARCHITECTURE.md`](../pdf_system/docs/ARCHITECTURE.md) | 主系统详细设计 |
| [`../pdf_system/docs/DATABASE.md`](../pdf_system/docs/DATABASE.md) | 数据库详细设计 |
| [`../pdf_system/docs/contracts/`](../pdf_system/docs/contracts/) | 跨线契约 C1–C5 原文 |
| [`../pdf_ocr_module/ocr_service/docs/API.md`](../pdf_ocr_module/ocr_service/docs/API.md) | OCR 模块接口定义 |
| [`../pdf_ocr_module/`](../pdf_ocr_module/) | OCR 引擎源码（`ocr_service`，含模型清单） |

## 本目录技术文档

| 资料 | 内容 |
|---|---|
| [`architecture.md`](architecture.md) | 接口总表与调用关系 |
| [`api-contract.yaml`](api-contract.yaml) | API 契约（OpenAPI 骨架） |
| [`database-design.md`](database-design.md) / [`er-diagram.mmd`](er-diagram.mmd) | 数据库设计与全局 E-R 图 |
| [`features.md`](features.md) | 功能点与需求编号总表 |
| [`development-baseline.md`](development-baseline.md) | 公共限制、优先级、验收标准 |
| [`team/`](team/) | 各端开发指南 |
| [`media/`](media/) | UML 与 E-R 成图 |

## 标准与外部资料

- [ISO/IEC/IEEE 12207:2017](https://www.iso.org/standard/63712.html) — 软件生命周期过程，设计与维护过程依据
- [ISO/IEC 25010:2011](https://www.iso.org/standard/35733.html) — 系统与软件质量模型
- [IEEE Std 830-1998](https://standards.ieee.org/ieee/830/1235/) — 软件需求规格说明规范
- [FastAPI 文档](https://fastapi.tiangolo.com/zh/) — Web 框架
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/) — ORM
- [PaddleOCR 文档](https://paddlepaddle.github.io/PaddleOCR/) — 本地 OCR 引擎（paddlepaddle 3.0.0，Python ≤ 3.13）
- [pdf.js 文档](https://mozilla.github.io/pdf.js/) — 前端渲染（`TextLayer` / `findController` / `renderTextLayer`）
- [MySQL 8.0 全文索引（ngram）手册](https://dev.mysql.com/doc/refman/8.0/en/fulltext-search-ngram.html)
- [Mermaid ER 图语法](https://mermaid.js.org/syntax/entityRelationshipDiagram.html) — `er-diagram.mmd` 渲染

## 建模资产

UML 与 E-R 成图统一存放在 [`media/`](media/)，全局 E-R 图的 Mermaid 源码为 [`er-diagram.mmd`](er-diagram.mmd)；PlantUML 文本源码目录 `uml/` 尚未建立，当前建模资产以 PNG 成图为准。
