# 第 03 线（黄俞富）实现与验收

原始实现于 2026-10-31；2026-11-14 审查修订见 [逐项处置与验证](line03-review-20261114.md)。本次涉及 01/02 线共享配置、JWT 解码、配额和文件生命周期，须跨线审阅；没有数据库 Schema 变更。

## 已完成

| 部分 | 行为 |
|---|---|
| OCR 锁定 | MySQL 使用 SELECT FOR UPDATE；SQLite 先获取写锁，再查询当前记录，不依赖原值更新的 rowcount。获取锁后重新检查租约，校对读取当前页与索引。 |
| 检索过滤 | 文件 ID、精确标签、上传日期（UTC，起止日均包含）；与权限和回收站过滤取交集；参数绑定防止 SQL 拼接注入。 |
| 检索页面 | 文件名建议、组合过滤、分页、当前页按文件分组、纯文本高亮、点击跳页、加载/错误/空态。 |
| 检索历史 | 当前浏览器按账号存储，最多 20 条；同一关键词及过滤组合去重；可复用、可清空；不跨设备同步。 |
| OCR 面板 | 指定页识别、线框表格开关、轮询、取消、失败页重试、当前页结果、表格预览、只读角色限制。 |
| 校对 | 编辑时固定 expected_revision；409 保留草稿并提示复制合并；显式放弃草稿后重载；保存后更新表格与全文索引。 |
| 导出 | TXT/JSON/CSV/HTML/XLSX；全部或指定页；可选择部分成功页与坐标；保留公式注入和 HTML 转义保护；原文件名加时间戳。 |
| 环境与测试 | OCR requirements 与完整 lock 统一使用 opencv-python-headless；新增后端/前端回归测试；CI 安装 OCR 轻量依赖并执行相关测试。 |
| 评测工具 | JSONL 标签/预测输入、按类别及总字符数计算 CER、准确率、已计时样本的 P95 和覆盖率；检查重复/缺失页和最小样本数；记录输入 SHA256。 |

### MySQL 原问题的准确解释

旧分工文档声称 MySQL 的 no-op UPDATE 必然返回零。当前项目使用 SQLAlchemy，其 MySQL 方言默认启用 FOUND_ROWS，通常返回匹配行数，所以不能据此断定默认配置必然失败。
本次采用显式锁定读，消除对这一驱动行为的依赖，并用 SQLite 事务测试、模拟零 rowcount 和 MySQL SQL 编译检查覆盖。
2026-11-14 已使用真实 MySQL 8.0.40、显式关闭 FOUND_ROWS 验证心跳、SKIP LOCKED、ngram 与并发结算；详见审查修订记录。
参考：[SQLAlchemy rowcount 说明](https://docs.sqlalchemy.org/en/20/dialects/mysql.html#rowcount-support)。

### 失败页重试与配额

C3 约定每个 job_id 只结算一次。主系统页面先结算原任务，再 POST /ocr/jobs 创建只含失败页的新任务，保留原识别选项。
原成功页的索引保留，不重复识别或计费；新任务有独立预留和结算。相关行为由 test_ocr_retry_flow.py 验证。
/jobs/{id}/retry 现同样创建新任务，仅含原失败页；响应 ID 会改变。worker 终态、取消/删除自动结算，前端 settle 仅作幂等补偿。
新任务结果/导出仅覆盖本次所选页，原任务结果仍可通过原 job_id 获取。

## 本地验证

历史记录（仅对应 2026-10-31 代码，不代表当前验收）：后端与 OCR 合计 114 项通过（0 跳过），前端 3 项通过，TypeScript 检查与 Vite 生产构建通过。
Edge 无界面浏览器验证了过滤参数、历史复用/清空、纯文本高亮、409 草稿保留/合并、表格更新、翻页隔离、指定页导出和失败页新任务重试；浏览器验证使用模拟 API，后端接口另由真实 SQLite 集成测试覆盖。
本机 Windows 沙箱的原生 esbuild 配置加载曾报目录访问受限，构建验证改用 Vite API 传入同等 React 配置完成；仓库正常环境仍用 npm run build。
现有依赖有一项 Starlette/AnyIO 弃用提示，现有 pdf.js 主包超过 Vite 默认 500 kB 提示阈值，均不影响本次测试通过。

以下命令在仓库根执行，使用 Python 3.12。测试无需 Paddle 或模型权重。

```powershell
python -m venv .venv-test
.\.venv-test\Scripts\python.exe -m pip install -r pdf_system/requirements.txt -r pdf_ocr_module/ocr_service/requirements.txt pypdf==5.6.0
$env:PYTHONPATH = "$PWD/pdf_system;$PWD/pdf_ocr_module"
.\.venv-test\Scripts\python.exe -m pytest pdf_system/backend/tests pdf_ocr_module/ocr_service/tests -q
cd pdf_system/frontend
npm ci
npm test
npm run build
```

主系统启动沿用 docs/team/getting-started.md；本次新增的接口参数见 docs/api-contract.yaml。
实际识别仍需独立 Python 3.12 worker、Paddle 和模型权重，且数据库、存储路径、JWT 密钥与 API 一致。

## 真实准确率评测

准备至少 200 页独立人工校对标签，每行一个 JSON 对象。file 路径相对标签文件，page_no 从 1 开始：

```json
{"id":"doc001-p001","file":"samples/doc001.pdf","page_no":1,"category":"printed_chinese","text":"这里必须填写该页人工核对的真实文字"}
```

从独立 OCR worker 环境、pdf_ocr_module 目录执行：

```powershell
python -m ocr_service.evaluate evaluation/labels.jsonl --run-ocr --output evaluation/report.json
```

也可以读取实际引擎产生的预测文件，每行含 id、text，可选 seconds：

```powershell
python -m ocr_service.evaluate evaluation/labels.jsonl --predictions evaluation/predictions.jsonl --output evaluation/report.json
```

CLI 默认最少 200 页；小样本必须显式使用 --development-sample --min-pages 1。报告记录门槛和达标状态；每页真值必须非空。人工标注独立性仍须人工审计。
默认 NFKC 规范化并去空白，保留标点；--keep-whitespace 可保留空白。CER 为编辑距离总和 / 标注字符总数，character_accuracy 为未截断的 1-CER（大量插入错误时可为负）。
各类别分别统计；模型加载不计入逐页耗时。缺失预测直接报错，部分计时也报告已测样本 P95，同时标注覆盖率与 complete=false，不能作为全量性能验收。
本次没有提供真实 200 页标注集，也没有编造 OCR 准确率或真实性能结论。

## 合并方式

基于最新 main 建立 fix/03-review-20261114 修复分支；不要用旧完整包覆盖其他人的代码。
仅通过 PR 合入 main；提交信息可用“[03] 完善 OCR 校对导出与检索过滤历史”。合并前由其他功能线审阅共享文件。
