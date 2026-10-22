# C1 鉴权契约（甲 ⇄ 全体，含 OCR 模块）

**状态**：W4 定稿 · 变更需三人确认 + PR

## 令牌

* 算法：HS256，密钥 `PDF_JWT_SECRET`，长度 ≥ 32（OCR 模块启动时会校验，短则拒绝启动）。
* 必填 claims：

| claim | 值 |
|---|---|
| `sub` | 用户 ID（= `users.id`，32 位 hex 字符串） |
| `role` | `user` / `viewer` / `admin` |
| `iss` | `pdf-system`（硬编码，OCR 侧强制校验） |
| `aud` | `ocr-api`（硬编码，OCR 侧强制校验） |
| `iat` / `exp` | 签发/过期时间，默认 120 分钟 |

## 服务端职责

| 方 | 职责 |
|---|---|
| 甲 | 签发令牌（`core/security.create_access_token`）；维护 `users.role` |
| 甲 | 提供 `core/principal.resolve_principal`：解码 + 校验用户存在且未停用；**角色以库内为准**，不信任令牌里的 role |
| 丙 | 用 `app.dependency_overrides[ocr_service.auth.current_user]` 让 OCR 复用同一解析逻辑 |
| 乙/丙 | 业务代码只依赖 `Principal(user_id, role)`，不自行解码令牌 |

## 权限口径

* 非本人资源统一 **404**（不做 403，减少 ID 枚举面）；管理员例外。
* `viewer` 只允许 GET；写操作由 `require_editor` 拦截为 **403**。
* 统计与审计接口始终返回**调用者自身**的数据，管理员也不例外。

## 前端

* 令牌存 `localStorage["pdf_system_token"]`，统一由 `shared/http.ts` 附加 `Authorization: Bearer`。
* 401 时清空令牌并跳 `/login`。
* pdf.js 拉取原文件必须带 `httpHeaders: { Authorization }`（不能裸 `<a href>`）。
