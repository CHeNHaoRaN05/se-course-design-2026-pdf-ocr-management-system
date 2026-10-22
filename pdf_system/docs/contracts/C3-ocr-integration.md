# C3 OCR 集成与配额契约（甲 ⇄ 丙）

## 挂载方式

```python
from ocr_service.api import install
install(app, ocr_settings, before_enqueue=make_before_enqueue(settings))
```

* `ocr_settings` 由主系统注入 `OCR_DATABASE_URL / OCR_STORAGE / OCR_JWT_SECRET / OCR_DEVICE` 后构造；
* OCR 路由前缀固定 `/api/v1/ocr`，前端直连，主系统不重复封装；
* 缺 Paddle 环境时 `mount_ocr` 返回 False，`app.state.ocr_mounted = False`，主系统其余功能照常启动。

## 配额钩子（唯一入口）

```python
def before_enqueue(session, user, file, page_numbers) -> None:
    # user        : OCR 模块的 Principal（只用 .user_id / .role）
    # file        : OCR 模块的 File ORM 行
    # page_numbers: 本次入队页码列表
    quota.reserve(session, user.user_id, len(page_numbers), ref_id=None, limit=settings.monthly_page_quota)
```

**铁律**

1. 在 OCR 建任务的**同一事务**内执行（OCR 已保证）；
2. 超额抛 `HTTPException(429)`；
3. **绝不自行 commit**（否则会出现"任务建了但配额没扣"）。

## 结算与退款

| 场景 | 调用 | 效果 |
|---|---|---|
| 任务终态 | `POST /api/v1/ocr-host/jobs/{id}/settle` | 成功页 `settle`（reserved→used），失败页 `release` |
| 任务取消 | `quota.release_job` | 全额退款 |

幂等：以 `quota_ledger.ref_id = job_id AND reason = 'job_close'` 为标记，重复调用无效。
前端在轮询到终态后调用一次 `settle`。

## 归属

* 配额表（`quota_accounts` / `quota_ledger`）**只由甲维护**；
* 丙只调用 `modules/quota/service.py` 暴露的 `reserve / settle / release / usage`，不得直接改表；

## 前端错误码

| 码 | 含义 | 处理 |
|---|---|---|
| 409 | 该文件已有活动任务 | 提示等待或先取消 |
| 422 | 页码越界 / 未配置的模式或模型 | 修正参数 |
| 429 | 配额不足 | 展示配额提示，引导下月或联系管理员 |
