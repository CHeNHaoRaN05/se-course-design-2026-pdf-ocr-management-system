# C4 阅读器与坐标契约（乙 ⇄ 丙）

## 坐标系（唯一口径）

> **归一化、左上原点、`[left, top, right, bottom]`，取值 0–1。**

* 相对"显示页面"（已应用 PDF 内置旋转 / 图片 EXIF 方向），**不是** PDF 底部原点，也不是 OCR 的四边形透视框；
* 阅读器额外做了 90/180/270 度用户旋转时，必须**先旋转四个角再取包围盒**。

## 渲染换算

```
x      = left   * viewportWidth
y      = top    * viewportHeight
width  = (right  - left)  * viewportWidth
height = (bottom - top)   * viewportHeight
```

实现：`frontend/src/features/ocr/OcrOverlay.tsx`（丙），由 `ReaderPage`（乙）以 props 注入
`blocks / width / height / activeId / onPick`。

## 接口

| 提供方 | 接口 | 用途 |
|---|---|---|
| 乙 | `GET /api/v1/files/{id}/content` | 原文件，支持 Range；pdf.js 用 `httpHeaders` 带 JWT |
| 乙 | `GET /api/v1/files/{id}/pages` | 每页点阵尺寸 `width_pt/height_pt` 与内置 `rotation` |
| 乙 | `GET/POST/DELETE /api/v1/files/{id}/reader/bookmarks` | 书签 |
| 乙 | `GET/POST/DELETE /api/v1/files/{id}/reader/annotations` | 批注，`payload.bbox` 与本契约同口径 |
| 丙 | `GET /api/v1/ocr/jobs/{id}/pages/{n}` | 该页 OCR blocks 与 bbox |

## 组件边界

* 乙**不渲染** OCR 框，只提供容器与尺寸；
* 丙**不操作** pdf.js 实例，只接收尺寸并渲染绝对定位层；
* 命中定位（检索 → 跳页）由丙的 `SearchPage` 通过 URL `/files/{fileId}?page={n}` 交给乙的阅读器。
