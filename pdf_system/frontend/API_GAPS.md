# 管理前端接口接入状态（2026-11-11）

此前列为“未实现”的 files/trash、auth/users、audit 已在本地修复分支实现，页面不再把404/405转换成“未实现”或展示本地缓存。需要同批部署前后端。

- `GET /files/query`：服务端分页、total、类型/日期/状态筛选、稳定排序、状态可用性与最新代次。
- `GET /files/trash`：真实 deleted_at 的回收站清单，权限过滤。
- `POST /files/bulk`：归属预检、逐项事务和明确的部分成功结果。
- `POST /files/merge`、`POST /files/{id}/split`：服务端PDFium生成、内容/加密/页数/像素/输出大小校验，失败清理新文件。
- `GET /auth/users`、`GET /audit`：后端require_admin保护。
- `POST /share`：相对有效期由服务端计算，提取码只允许ASCII字母数字。
- `GET /search`：新增media_type精确过滤。

准确参数与事务边界见 [增量契约](../../../docs/reviews/02-api-additions.md)（仓库根 docs/reviews）；运行时 `/openapi.json` 为完整结构。

仍未实现的独立需求：存储配额及写接口、每日趋势/平均耗时、独立目录CRUD/空节点/标签颜色、回收站30天清理、审计保留、禁止下载模式的安全文档渲染、文件历史版本管理、阅读器高级功能、生产MySQL和Paddle模型验收。
