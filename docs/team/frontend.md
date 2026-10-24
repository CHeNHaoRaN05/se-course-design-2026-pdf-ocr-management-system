# 前端开发指南（结构 · 约定 · 与后端对接）

> 配套文档：[`../architecture.md`](../architecture.md)（接口总表）、[`../api-contract.yaml`](../api-contract.yaml)、[`getting-started.md`](getting-started.md)（环境配置，含 Node 安装）
> 公共限制见 [`../development-baseline.md`](../development-baseline.md)。

---

## 1. 目录结构与所有权

```
frontend/src
  app/        App.tsx / router.tsx / Layout / AuthProvider   ← 陈
  shared/     http.ts（统一 fetch 封装）/ types.ts           ← 陈
  features/   auth / files / reader / ocr / search           ← 按线划分
```

- `shared/**` 与 `app/**` 归陈，`types.ts` 按线分区
- 路由仅 4 条（`app/router.tsx`）：`/login`、`/files`、`/files/:fileId`、`/search`
- **新增页面由陈统一注册路由**，其余人提需求

## 2. 统一约定

- 组件 `PascalCase`，变量/函数 `camelCase`
- 分页参数统一 `limit` / `offset`
- `vite.config.ts` 已把 `/api` 代理到 `8000`，不用另配

## 3. 请求出口：`shared/http.ts`

`shared/http.ts` 是**唯一**的请求出口，禁止各模块自己 `fetch`：

- `api<T>(path)`：自动补 `/api/v1` 前缀、自动带 `Authorization: Bearer`，401 由 `AuthProvider` 统一跳登录
- `apiBlob(path)`：用于导出与原文件下载 —— **不能用裸 `<a href>`**，那样带不上 JWT
- `downloadBlob(blob, filename)`：触发下载

## 4. 页面 → API 对应关系

```
页面                        API 模块                  http.ts                后端
─────────────────────────────────────────────────────────────────────────
LoginPage        ──login──> （内联）        ──> api<T>() ──> POST /auth/login
FilesPage        ─────────> filesApi.ts   ──> api<T>() ──> /files/**
ReaderPage       ─────────> readerApi.ts  ──> api<T>() ──> /files/{id}/reader/**
                 ─────────> ocrApi.ts     ──> api<T>() ──> /ocr/**, /ocr-host/**
                 ──渲染───> OcrPanel / OcrOverlay（覆盖层，坐标按 C4）
SearchPage       ─────────> （内联）        ──> api<T>() ──> /search
```

完整接口清单见 [`../architecture.md`](../architecture.md) 第 3 节。

## 5. 坐标口径（契约 C4，最易踩坑）

- 批注 `payload` 与 OCR `bbox` 同口径：**左上原点、归一化**
- 批注坐标**按归一化存储**以适配缩放；旋转后坐标需变换
- FR-READ-09（OCR 文本层叠加）需 pdf.js `renderTextLayer`，与黄（03 线）按 C4 对接

## 6. 常用命令

```bash
cd pdf_system/frontend
npm install
npm run dev     # http://localhost:5173
```

Node.js 需 20 LTS（安装步骤见 [`getting-started.md`](getting-started.md) 第 6 节）。
