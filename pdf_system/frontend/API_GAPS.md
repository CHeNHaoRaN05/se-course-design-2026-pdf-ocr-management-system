# 管理页面后端对接待办

本文件记录前端预留的三个 **当前 main 尚未实现** 的读取接口，不表示仓库 API 契约已经变更。后端成员实现时，应按团队流程更新公共接口文档并评审；前端已支持“尚未接入”和“返回数据”两种状态。

统一前缀 `/api/v1`，鉴权为 Bearer JWT，列表响应建议沿用 `/files` 的数组形式。参数 `limit` 为 1–100，`offset` 为非负整数；排序需稳定，避免分页重复。

## 1. 回收站列表

`GET /files/trash?limit=100&offset=0`

响应：`Array<FileItem & { deleted_at: string; sha256?: string }>`。FileItem 见 `src/shared/types.ts`。

- 仅返回已软删除记录。
- 非管理员按 owner 限定可见范围，管理员行为与已有 files 权限保持一致。
- 路由必须注册在 `GET /files/{file_id}` 之前，避免 `trash` 被解析为 ID。
- `deleted_at` 为真实服务端时间；不要用本地缓存时间替代。
- 前端接入点：`features/files/TrashPage.tsx`。404 / 405 才回退浏览器记录；其他错误明确显示。

## 2. 管理员用户列表

`GET /auth/users?limit=100&offset=0`

响应：`UserOut[]`，与现有 `auth/schemas.py:UserOut` 一致，字段为 id、email、display_name、role、disabled、created_at。

- 仅管理员可访问，不返回密码哈希、令牌或内部认证字段。
- 前端接入点：`features/admin/UsersPage.tsx`。
- 用户更新继续复用现有 `PATCH /auth/users/{id}/role` 和 `/disabled`。

## 3. 主系统审计日志

`GET /audit?actor_id=…&action=…&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&limit=21&offset=0`

响应：`Array<{ id: string; actor_id: string; action: string; resource_id: string | null; created_at: string; detail?: Record<string, unknown> }>`。

- 仅管理员可访问，建议按 `created_at DESC, id DESC` 稳定排序。
- 日期范围按 UTC 解释，结束日期包含当日，参数需校验。
- 前端每页展示 20 条，第 21 条仅用于判断是否还有下一页。
- 日志只读，不返回正文、认证令牌或密码。
- 前端接入点：`features/admin/AuditPage.tsx`。CSV 导出只导出当前显示页的时间、用户 ID、动作和资源 ID。

## 其他能力缺口

- 存储配额上限、配额管理写接口、日趋势与平均耗时统计。
- 禁止下载时的安全阅读页面 / 渲染接口；当前分享接口在此模式仅返回元数据。
- 独立分类树 CRUD、目录空节点及标签颜色；当前模型用文件 folder 字符串和标签名称。
- 回收站 30 天保留 / 清理机制，以及主系统审计保留策略。

以上不通过虚构前端数据或绕过既有鉴权补齐。
