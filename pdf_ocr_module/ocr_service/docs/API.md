# OCR 接口文档 v1.0

统一前缀：`/api/v1/ocr`。所有接口均要求 `Authorization: Bearer <JWT>`。

在线交互文档：启动后 `/docs`；机器可读定义：`/openapi.json`；静态副本：[openapi.json](openapi.json)。请求与响应使用 UTF-8；ID 为服务端生成的 32 位十六进制字符串；页码从 **1** 开始；时间按 UTC 存储，当前响应为不含时区后缀的 ISO 字符串，前端须按 UTC 解析。

## 权限约定

JWT 必需 claims：`sub`（用户 ID 字符串）、`exp`、`iat`、`iss=pdf-system`、`aud=ocr-api`。默认算法 HS256。`role` 为 `user/viewer/admin`，缺省为 user。

- user：读取、识别、校对自己的文件。
- viewer：仅可读取自己的文件和结果，不能上传/创建/取消/重试/校对。
- admin：可处理所有用户文件；统计和用户审计查询仍返回管理员自身的数据。
- 不属于当前用户的资源统一返回 404，减少资源 ID 枚举泄漏。列表与检索也按归属过滤。

不提供注册登录接口；由主系统提供。分享链接授权需要主系统增加，不可通过省略鉴权实现。

## 接口总览

以下路径均省略统一前缀。

| 方法 | 路径 | 功能 | 成功状态 |
|---|---|---|---|
| GET | `/capabilities` | 支持模式、格式和限制 | 200 |
| POST | `/files` | 上传 PDF/PNG/JPEG | 201 |
| GET | `/files/{file_id}` | 文件元数据 | 200 |
| GET | `/files/{file_id}/content` | 受鉴权保护的原文件，供 pdf.js 阅读 | 200/206 |
| POST | `/jobs` | 创建异步识别任务 | 202 |
| GET | `/jobs` | 当前用户的任务列表，管理员可查全部 | 200 |
| GET | `/jobs/{job_id}` | 状态、进度、每页状态 | 200 |
| POST | `/jobs/{job_id}/cancel` | 取消活动任务 | 200 |
| POST | `/jobs/{job_id}/retry` | 手动重试失败页 | 202 |
| GET | `/jobs/{job_id}/pages` | 全部已选页结果 | 200 |
| GET | `/jobs/{job_id}/pages/{page_no}` | 单页结果 | 200 |
| GET | `/jobs/{job_id}/pages/{page_no}/image` | 该页 OCR 所使用的 PNG | 200 |
| PATCH | `/jobs/{job_id}/pages/{page_no}` | 校对并同步检索索引 | 200 |
| GET | `/jobs/{job_id}/export` | 下载结果文件 | 200 |
| GET | `/search` | 搜索识别/校对内容，定位文件与页面 | 200 |
| GET | `/usage` | 本用户文件量、存储量、任务与成功页结果统计 | 200 |
| GET | `/audit` | 本用户的操作记录 | 200 |

## 1. 上传文件

`POST /files`，`multipart/form-data`，字段名 **file**。只接受一个文件，默认上限 20 MiB，PDF 上限 100 页。按真实内容检查类型，客户端 MIME 和扩展名不作为唯一依据。图片自动按 EXIF 方向处理；加密或损坏 PDF 返回 422。

响应示例（ID 仅作结构示例）：

```json
{
  "id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "name": "实验报告.pdf",
  "media_type": "application/pdf",
  "size": 123456,
  "page_count": 3,
  "created_at": "2026-10-21T10:00:00"
}
```

GET 元数据返回同一结构。GET content 返回二进制正文，支持客户端 Range 请求；pdf.js 的请求也要带 JWT，可用其 `httpHeaders` 配置。

上传只是最小文件适配层。分类、标签、合并拆分、文件列表、批量删除请接入未来文件管理模块；合并拆分结果应分配新文件 ID 后再识别。

## 2. 创建异步任务

`POST /jobs`，JSON：

```json
{
  "file_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "pages": [1, 2],
  "mode": "general",
  "recognition_model": "official",
  "dpi": 144,
  "tables": true,
  "min_confidence": 0.5
}
```

| 字段 | 必填 | 约束/缺省 |
|---|---|---|
| file_id | 是 | 上传接口返回的 ID，不能传磁盘路径/URL |
| pages | 否 | 不传/null 为全部页；非空正整数数组，去重排序；不可越界 |
| mode | 否 | general：通用文字检测；handwriting：配置专用检测模型后可用；默认 general |
| recognition_model | 否 | official / custom；默认 official；custom 需要服务端配置兼容的识别权重 |
| dpi | 否 | 72–240，默认 144；只影响 PDF 渲染，图片保留尺寸 |
| tables | 否 | 默认 false；true 使用规则网格算法，非复杂表格模型 |
| min_confidence | 否 | 0–1，默认 .5；低于阈值标记 needs_review，不删除文本 |

不认识的字段返回 422。每文件最多一个活动任务，重复提交返回 409，并不会启动第二份识别。任务完成后可重新识别；新任务的成功页替换该页搜索索引，失败页保留旧索引。若需按点击幂等键去重，请主系统额外引入 idempotency key。

`GET /capabilities` 只列出已配置的模式和自定义模型。未配置专用手写检测权重或自定义识别权重时，请求对应选项返回 422。标准部署仅开启 general 与 official。

返回 202，任务结构：

```json
{
  "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "file_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "status": "queued",
  "options": {
    "pages": [1, 2], "mode": "general", "recognition_model": "official",
    "dpi": 144, "tables": true, "min_confidence": 0.5
  },
  "attempts": 0,
  "progress": {"total": 2, "succeeded": 0, "failed": 0, "percent": 0},
  "pages": [
    {"page_no": 1, "status": "pending", "error": null},
    {"page_no": 2, "status": "pending", "error": null}
  ],
  "created_at": "2026-10-21T10:00:01",
  "finished_at": null
}
```

`progress.percent` 是**成功页占比**，不是推理时间占比；失败终态可以小于 100。正在处理某页时该页仍为 pending（前一轮失败则仍为 failed），无需据此推断 worker 不工作。

任务状态：queued / running / retry_wait / succeeded / partial_success / failed / cancelled。终态为最后四种，轮询遇到终态即可停止，推荐轮询间隔 1–2 秒。

`GET /jobs?limit=20&offset=0` 返回任务数组；limit 为 1–100，按创建时间倒序。`GET /jobs/{id}` 返回单个上述结构。

## 3. 取消与重试

两个 POST 都无需请求体，返回更新后的任务结构。

- cancel：仅对活动任务有效。正在执行的单页模型推理不会被强杀，但它后续的结果提交将被拒绝；此前成功页保留。
- retry：仅 failed / partial_success 可重试；重新执行失败页，保留成功页。若该文件有更晚创建的任务，则返回 409，需要为目标失败页创建新任务。cancelled 任务需新建任务。
- 自动重试：最多 3 次尝试，等待 15、30 秒；本地 worker 停止后数据库中的任务仍保留。
- 页错误码包括 `ocr_inference_failed`、`worker_lease_expired`、`render_pixel_limit`。详细模型异常见 worker 日志，不经 HTTP 暴露服务器路径。

## 4. 页面结果与坐标

GET pages 返回页数组；GET pages/{page_no} 返回单页，内容包括：

```json
{
  "page_no": 1,
  "status": "succeeded",
  "revision": 1,
  "error": null,
  "result": {
    "width": 1200, "height": 1600,
    "text": "中文全文检索测试",
    "blocks": [{
      "id": 1, "text": "中文全文检索测试", "confidence": 0.97,
      "bbox": [0.1, 0.15, 0.75, 0.2], "needs_review": false
    }],
    "tables": [],
    "corrected": false,
    "mode": "general", "recognition_model": "official",
    "image_key": "pages/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb/token-1.png",
    "coordinate_system": "normalized_top_left_display_page",
    "warnings": []
  }
}
```

pending/failed 页可能 `result=null`；错误见 error。`bbox=[left,top,right,bottom]`，范围 0–1，相对应用 PDF 内置旋转/图片 EXIF 后的显示页面；返回的是轴对齐框，不是 PDF 底部原点坐标，也不是 OCR 透视四边形。

在 pdf.js 页面宽 W、高 H 的覆盖层中：x=left×W，y=top×H，宽=(right-left)×W，高=(bottom-top)×H。页面额外旋转时应旋转四角后取新包围盒。`width/height` 是 OCR 渲染图尺寸，通常与浏览器 CSS 尺寸不同。

`image_key` 是内部结果元数据，不能当静态 URL 访问；前端通过鉴权的 `.../image` 获取预览。空文字块列表可以表示空白页；不等于系统报错。所有识别结果都有可能识错，置信度也不等于准确率。

表格结构示例：

```json
{
  "id": 1, "strategy": "ruled_grid", "needs_review": true,
  "x_lines": [30, 180, 330], "y_lines": [30, 130, 230],
  "cells": [["姓名", "成绩"], ["张三", "90"]]
}
```

表格 x_lines/y_lines 使用 OCR 图像像素；cells 为二维字符串数组。要求完整闭合且规则的线框。无法可靠确定结构时返回空数组，不伪造合并单元格；复杂表格后续应接专门结构模型。

## 5. 校对

`PATCH /jobs/{job_id}/pages/{page_no}`，提交完整 blocks 列表：

```json
{
  "expected_revision": 1,
  "blocks": [{
    "id": 1, "text": "人工校对后的文字", "confidence": 0.97,
    "bbox": [0.1, 0.15, 0.75, 0.2], "needs_review": false
  }]
}
```

允许增加、删除、改文字和框；ID 必须为互不重复的正整数。最多 2000 块、每块 10000 字、全页 200000 字。空数组表示确认将该页文本清空，也会清空全文索引。

成功返回 revision+1 的页面对象，`corrected=true`，text 按提交 blocks 顺序拼接，表格内容按框中心重新归位，检索表同步更新。置信度沿用输入值；人工校对后它不再代表新文本的模型评分，可据 corrected 区分。

任务仍活动、版本不匹配、页面已被新任务替代时返回 409。前端重新读取当前页面，提示用户合并修改，不能自动丢掉 expected_revision 重试。

## 6. 导出

`GET /jobs/{job_id}/export?format=xlsx&allow_partial=false`

format：txt / json（默认）/ csv / html / xlsx。返回附件二进制与 `Content-Disposition`；前端使用 fetch + Blob 下载，不用无法携带 JWT 的裸 `<a href>`。

| 格式 | 内容 |
|---|---|
| TXT | 按页分隔的识别/校对文本 |
| JSON | 页对象、文字块坐标、置信度、表格、修订号 |
| CSV | page、block_id、text、confidence、四个归一化坐标 |
| HTML | 按页正文与表格；文字经 HTML 转义 |
| XLSX | OCR文本 sheet + P页号_T表号 sheet；危险公式前缀按文本处理 |

默认仅允许完整 succeeded 任务导出。部分成功、取消或执行中结果必须 `allow_partial=true`，且至少有一个成功页。响应头 `X-OCR-Exported-Pages` / `X-OCR-Total-Pages` 标记已导出页数和任务总页数；总页数为任务所选页数。部分导出并不伪装成完整文档。

## 7. 全文检索

`GET /search?q=中文&limit=20&offset=0`

q 去掉首尾空格后必须非空，最多 100 字。MySQL 使用 ngram 自然语言全文查询（长度 ≥ 2），单字符和 SQLite 使用子串查询。查询参数绑定，LIKE 通配符被转义。按索引更新时间倒序，不按相关性评分排序。

```json
{
  "backend": "mysql_ngram",
  "items": [{
    "file_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "file_name": "实验报告.pdf",
    "page_no": 1, "job_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "revision": 2, "snippet": "人工校对后的中文内容"
  }]
}
```

没有命中返回空 items。前端用 file_id 打开原文件、page_no 跳页，再通过 job_id + page_no 取得 OCR 坐标。snippet 为最多 200 字的纯文本，不包含可直接执行的 HTML，也不保证全文查询词是连续子串。展示文字请用 React 文本节点，不使用未经转义的 `dangerouslySetInnerHTML`。

## 8. 统计与日志

`GET /usage` 示例：

```json
{"files": 3, "storage_bytes": 1000000, "recognized_page_results": 12,
 "jobs_by_status": {"succeeded": 2, "failed": 1}}
```

成功页结果数包含历史任务；并非去重文件页数或月度计费量。`GET /audit?limit=20&offset=0` 返回 action、resource_id、detail、created_at；按当前 actor 过滤，worker 内部记录保存在表中供管理员后续建设管理接口。

## 9. 统一错误处理

业务错误为 `{"detail": "..."}`；Pydantic 参数错误为 `{"detail": [{"loc": [...], "msg": "...", ...}]}`。

| HTTP | 含义 | 前端处理 |
|---|---|---|
| 401 | 缺少/过期/无效 JWT | 进入主系统续期或登录流程 |
| 403 | viewer 尝试写操作 | 禁用对应操作 |
| 404 | 文件/任务/页面不存在或无权查看 | 提示资源不可用 |
| 409 | 活动任务、版本冲突、旧任务重试、导出不完整 | 根据 detail 刷新状态或提示合并 |
| 413 | 文件超过配置大小 | 提示文件大小限制 |
| 422 | 参数错误、越界页码、损坏/加密/不支持的文件 | 修改输入 |
| 429 | 主系统配额钩子拒绝（默认模块没有月配额） | 展示主系统配额提示 |
| 500 | 未处理的服务端/数据库异常 | 保留操作上下文，联系维护者，勿无限重试 |

## 10. 前端联调顺序

1. 登录主系统取得 JWT；本地开发可用 `run.ps1 token`。
2. 上传 → 获取 file_id。
3. 创建任务 → 获取 job_id；创建成功只代表已入队。
4. 每 1–2 秒查询 job 状态，终态停止。
5. 加载页结果/预览，让用户校对；PATCH 携带 expected_revision。
6. 检索页跳转或下载导出。

完整调用骨架见 [client.ts](../examples/client.ts)，独立启动步骤见 [README](../README.md)。
