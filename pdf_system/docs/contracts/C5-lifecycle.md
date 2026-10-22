# C5 文件生命周期契约（乙 ⇄ 丙）

删除一个文件时，OCR 侧的任务、页结果、页 PNG 与全文索引必须一起处理，
否则会留下孤儿任务和无法命中的索引。

## 状态迁移

```
上传 → (未识别) → 识别中(running) → 已完成(succeeded/partial_success/failed)
                                  ↘ 取消(cancelled)
任意状态 → 回收站(deleted_at) → 彻底删除(purge)
```

## 调用矩阵

| 主系统动作 | 乙的实现 | 丙需提供的能力 | 数据后果 |
|---|---|---|---|
| 软删除（回收站） | `DELETE /files/{id}` | `ocr.lifecycle.cancel_tasks(session, file_id)` | 取消未终态任务、释放 `active_job_id`；**OCR 结果与索引保留**，可还原 |
| 还原 | `POST /files/{id}/restore` | 无 | 恢复可见；需重新发起识别才会更新结果 |
| 彻底删除 | `DELETE /files/{id}/purge` | `ocr.lifecycle.purge_file(session, settings, file_id)` | 删除 `pdf_text_index` / `ocr_pages` / `ocr_jobs` / `ocr_files`，并 `rm -rf storage/pages/{job_id}`；随后删除物理文件 |

## 约束

1. 乙**禁止**直接删 `ocr_*` 表或 `pdf_text_index`——一律走 `lifecycle`；
2. `purge` 顺序必须是：索引 → 页结果 → 任务 → 页 PNG → 镜像行 → 物理文件；
3. OCR 未挂载时，`cancel_tasks` / `purge_file` 的导入被 `ImportError` 捕获并降级为 no-op，
   乙的代码**不得**因为缺少 Paddle 环境而失败；
4. 主系统不提供分享链接的写权限，删除只影响归属者（管理员除外）。

## 待办（W7）

* 回收站自动清理策略（如 30 天）；
* 批量删除的事务边界与失败回滚；
* 合并/拆分产生的新文件必须走一次 `ensure_ocr_file`。
