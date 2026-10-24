# 文档中心

> 项目：基于本地 OCR 的 PDF 文件显示与管理系统（FastAPI + React/pdf.js + PaddleOCR worker）
> 新成员阅读顺序：[`README`](../README.md) → [`team/getting-started.md`](team/getting-started.md) → [`development-baseline.md`](development-baseline.md) → 本线指南（[`team/`](team/)）

## 文档地图

| 文档 | 内容 |
|---|---|
| [`architecture.md`](architecture.md) | 系统架构：进程视图、48 个接口总表、模块调用关系、契约 C1–C5、数据流 |
| [`api-contract.yaml`](api-contract.yaml) | API 契约（OpenAPI 3.0 骨架，与 architecture.md 第 3 节对应） |
| [`database-design.md`](database-design.md) | 数据库设计：14 张表、约束、容量与保留策略 |
| [`er-diagram.mmd`](er-diagram.mmd) | 全局 E-R 图（Mermaid，GitHub 可直接渲染） |
| [`features.md`](features.md) | 需求分析文档大纲与功能点编号总表（FR-*/NFR-*） |
| [`development-baseline.md`](development-baseline.md) | 开发基线：公共限制、成员分工、优先级、时间节点、验收标准 |
| [`references.md`](references.md) | 参考资料：仓库内文档索引与外部资料 |

## team/ —— 各端开发指南

| 文档 | 内容 |
|---|---|
| [`team/getting-started.md`](team/getting-started.md) | 环境配置：两套 Python 环境、版本矩阵、从零配置、已踩的坑、最小 Demo |
| [`team/backend.md`](team/backend.md) | 后端：三条功能线的详细分工、待办、跨线接口清单（含精确签名） |
| [`team/frontend.md`](team/frontend.md) | 前端：目录结构、http.ts 约定、坐标口径（C4） |
| [`team/database.md`](team/database.md) | 数据库：表所有权、schema 冻结规则、跨线共享字段 |

## 其他交付物

- [`需求分析文档.docx`](../需求分析文档.docx) — 课程需求分析阶段 Word 正稿（本目录 `features.md` 是其大纲）
- [`pdf_system/docs/`](../pdf_system/docs/) — 主系统详细设计、数据库设计、契约 C1–C5 原文
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — 协作流程
