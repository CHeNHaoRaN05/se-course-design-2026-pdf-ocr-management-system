# 文档管理前端

本地基线为 `origin/main=8cf647f`、PR #9 head `1c9971d`。2026-11-11按测试审查报告补齐必要后端接口和定点修复。原阅读器功能及OCR引擎未扩展，OCR前端仅修正轮询停止与卸载取消。

[逐项审查结论](../../../docs/reviews/02-review-resolution.md) · [增量接口](../../../docs/reviews/02-api-additions.md) · [验证记录](docs/VALIDATION.md) · [历史页面截图](docs/PREVIEW.md)

## 启动

在仓库根执行：

```bash
cd pdf_system/frontend
npm ci
npm run dev
```

访问 `http://localhost:5173`。`/api` 默认代理到 `http://127.0.0.1:8000`；按上级README启动API后注册账号使用。程序不内置演示账号或假数据。需要更新本修复分支的前后端，旧main不提供新增接口。

## 页面与行为

| 页面 | 路径 | 内容 |
|---|---|---|
| 登录 / 注册 | `/login` | 邮箱认证、表单验证、恢复目标页面、断网本地退出提示 |
| 文件库 | `/files` | 服务端分页、total、名称/类型/日期/状态筛选、稳定排序、分类标签、详情和下载 |
| 上传 | `/upload` | 多文件/拖拽、大小及文件头校验、文件名规范化、分类标签、失败重试 |
| PDF工具 | 文件库操作 | 真实服务端bulk、merge、split；原件保留；不是客户端处理后逐项上传 |
| 回收站 | `/trash` | 服务端真实删除记录、还原/彻底删除确认；不回退浏览器缓存 |
| 全文检索 | `/search` | 类型/日期/标签/文件过滤、聚合与高亮、跳页、来源任务与修订、账号隔离历史 |
| 分享 | `/shares`、`/share/:token` | 1/7/30天由服务端计时、可见提取码、原文件访问设置、访客下载、撤销 |
| 统计 | `/stats` | 当前账号文件与存储、页数配额、真实任务统计 |
| 账户 | `/account` | 账号信息、改密、手动续期；断网登出清本地凭据但不假称远端吊销成功 |
| 用户管理 | `/admin/users` | 真实列表、改角色与启用/禁用；后端拒绝管理员自降级 |
| 审计 | `/admin/audit` | 真实主系统日志、过滤分页、CSV导出原始时间与动作字段 |

文件库每页12项，服务端排序带id次级键；未挂载OCR时忽略旧状态筛选并提示，文档仍可访问。下拉列表的全量读取有重复页检测和1000页上限，避免异常无限请求。

批量操作先校验全部资源归属，再逐项事务提交，明确报告部分失败。拆分的新文件批次使用一个数据库事务，失败清理已生成文件。服务端检查真实PDF内容、加密、像素、页数及输出大小，合并最多100页。不承诺保留跨文档书签、签名和表单。

后端统一存naive UTC，前端按浏览器时区显示；北京时间相对UTC加8小时是正常转换，纯日期保持日历日期。分享请求传相对天数，页面过期标记来自服务端。

## 边界与所有权

新增的02线UI/格式化/分页实现移至 `features/management/`，`src/styles.css`恢复main原版，管理样式作用域排除reader/OCR子树。共享HTTP/Auth、路由装配、01线用户/分享/审计、03线检索和轮询定点修改均列入审查结论，需对应维护者review。没有改数据库模型、resolve_principal或C1–C5签名；本地验证不代表维护者已批准。

仍未实现：阅读器高级功能、历史文件版本、空目录CRUD/标签颜色、存储配额写接口、每日趋势/平均耗时、回收站30天清理、审计保留作业及禁止下载时的安全只读渲染。目前禁止下载分享仅返回元数据。详细状态见 [API_GAPS.md](API_GAPS.md)。

## 验证与CI

```bash
npm test
npm run build
npx playwright install chromium-headless-shell
npm run test:e2e
# Python 3.12环境安装了pdf_system/requirements.txt后：
npm run test:live
```

- 单测由Node枚举文件，不依赖shell glob。
- e2e为明确标注的契约夹具/异常测试，独立5174端口，由当前Node启动Vite，禁止复用旧服务。可设置 `PLAYWRIGHT_CHANNEL=chrome` 使用系统Chrome。
- `test:live` 无API mock，自动分配端口，启动临时随机密钥、SQLite、存储和Vite，验证注册、文件管理、服务端合并拆分、分享、删除还原和账户操作。Python可由 `SE_PYTHON`指定，默认`python`。自动停止服务并清理临时数据。
- 真实API测试不启动OCR推理。模型质量、MySQL和生产部署另行验收。
- CI增加Linux/Windows单测、Chromium测试、真实API流程和证据上传；本分支未push，远端CI本轮尚未执行。

生产构建为`dist/`。部署需配置SPA history fallback和`/api`反向代理。许可证副本位于`public/THIRD_PARTY_NOTICES.txt`。
