# 管理接口接入状态（2026-11-13）

前次613be22已经推送。本轮增量仍待维护者评审，前后端需同批更新。

## 已实现

- files/query：分页total、类型/日期/状态筛选、有效排序方式与来源版本。
- files/trash、auth/users、audit：envelope=true 返回 items/total/limit/offset，旧数组客户端兼容，页面只取当前页。
- files/bulk：归属预检与文件状态分离，200全部成功/207混合/409全部失败，均带逐项结果。
- files/merge、files/{id}/split：服务端校验与生成，version取源最大值+1，replaced_from与审计记录来源；不覆盖原件。
- share：相对有效期，拒绝无时区绝对时间；可见提取码、原子访问计数、单进程限速与访问审计。
- search：类型过滤、关键词长度与空白建议校验。

准确结构见 [生成契约](../../docs/api-contract.yaml)、[复测增量](../../docs/reviews/02-retest-contract.md)、[逐项结论](../../docs/reviews/02-retest-resolution.md)。

## 仍需专项完成

完整版本历史/回滚、C3无人访问结算/跨月账务/同ID重试、阅读器高级功能、存储配额及写接口、趋势/平均耗时、独立分类树/空目录/标签颜色、30天回收站和日志保留策略、禁止下载安全渲染、生产MySQL及Paddle模型验收。

分页为实时offset分页，不是历史快照。限速器为单进程实现，多worker需共享限速基础设施。客户端取消不回滚服务端已提交的任务。
