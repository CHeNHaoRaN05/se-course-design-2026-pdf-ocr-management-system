# 文档管理前端

当前修复基线：已推送的 `613be22`，远端 main `8cf647f`。用户复测报告记录前次 CI 在 2026-11-11 08:13:54 UTC 成功。本轮是此后的增量修复，尚未推送；维护者评审与 PR 合并未由本任务代为完成。

[复测逐项结论](../../docs/reviews/02-retest-resolution.md) · [复测契约](../../docs/reviews/02-retest-contract.md) · [生成的 OpenAPI](../../docs/api-contract.yaml) · [验证记录](docs/VALIDATION.md)

## 启动

```bash
cd pdf_system/frontend
npm ci
npm run dev
```

访问 `http://localhost:5173`。API 默认代理到 `http://127.0.0.1:8000`，需要按上级 README 启动本分支后端。程序没有内置演示账号或假数据。前后端应同批更新。

## 页面与行为

- 文件库：服务端分页、total、名称/类型/日期/状态筛选、稳定排序、分类标签、原文件下载及来源版本。
- 上传：多文件、拖拽、内容/大小校验、名称规范化和失败重试。只对幂等元数据 PATCH 自动重试瞬时故障；上传等 POST 不自动重试。
- 文件工具：服务端 bulk/merge/split。本人已软删项逐项失败；全部成功200、混合207、全失败409。新文件版本为源最大版本+1，记录来源，原件保留。
- 回收站、用户列表、审计：使用 envelope=true 的 items/total/limit/offset，只取当前页，不靠缓存或全量扫描实现分页。稳定 offset 不是历史快照，数据改变应刷新。
- 分享：服务端计算1/7/30天有效期，绝对时间必须含Z/偏移，可见提取码、访客下载、撤销、原子访问计数。禁止下载时当前只开放文档信息。
- 账户：改密、续期、本地退出与远端吊销结果区分。事件与 BroadcastChannel 支持跨标签同步，禁用 localStorage 也可退出。
- OCR 前端：手动与自动请求取消、连续失败与结算失败有限重试。viewer可以为自己已有终态任务结算；不允许指定账务数值或访问他人任务。
- 全文检索、配额统计沿用真实接口；文件修改通过广播刷新其它已打开文件库。

SQLite 文件名分配使用真实数据库写锁，上传/重命名/还原规则一致；回收站不占用活动名称，还原冲突自动加序号。PDF 全局锁只覆盖 PDFium 操作，不包住持久化。

后端存储 UTC；页面按本地时区显示，CSV 列头明确标注 UTC 原始值。纯日期不附加时刻。客户端取消不能撤销已经提交的服务端操作。

## 验证

先准备 Python 3.12 和主系统依赖，然后：

```bash
npm test
npm run build
npx playwright install chromium-headless-shell
npm run test:e2e
npm run test:live
```

可设置 `SE_PYTHON` 指定 Python 解释器，`PLAYWRIGHT_CHANNEL=chrome` 使用系统 Chrome。

`test:e2e` 包含两个项目：

- `contract`：5174端口，故障注入与界面边界。未知或未拦截 API 请求使测试失败，不能静默穿透代理。
- `real-api`：5175前端连接8015临时真实 FastAPI/SQLite。没有 page.route/fulfill，测试真实分页、并发、PDF内容、权限和跨标签刷新。

测试自动启动服务，禁止复用残留监听。输出实际 HTML 报告 `playwright-report/index.html` 和 JSON `test-results/browser-results.json`。`test:live` 使用动态端口和临时数据，单独完成真实工作流，保存 `test-results/live-result.json`。

CI区分Linux/Windows浏览器安装，同平台运行本轮后端回归、前端单测、两个浏览器项目和独立真实工作流，上传实际产物。修复本机为macOS，复测者win32与远端Windows结果分别记录，不混淆。

完整OpenAPI由 `python -m backend.scripts.export_contract` 生成，需安装轻量OCR API依赖；CI运行 `--check` 防漂移。测试直接依赖的 esbuild 已显式声明。

## 范围与待办

管理样式和辅助代码在 features/management，原阅读器/OCR基础样式隔离保留。共享Auth/HTTP、01线用户/分享/审计、03线请求生命周期的增量修复仍需维护者review。没有把用户授权当成团队批准。

仍未完成：C3无人值守结算/同ID重试/跨月账务整体改造、完整文件版本历史与回滚、阅读器高级功能、禁止下载安全渲染、配额写接口/存储上限、每日趋势、独立分类树/空目录/标签颜色、保留清理作业、MySQL生产验收和Paddle模型质量评测。分享限速是单进程实现，多worker需要共享限速器或网关。

部署 dist 时需要 SPA history fallback 和 /api 反向代理。许可证随构建复制，见 public/THIRD_PARTY_NOTICES.txt。
