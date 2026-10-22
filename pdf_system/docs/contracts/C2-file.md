# C2 文件契约（乙 ⇄ 丙）

**背景**：OCR 模块自带 `ocr_files` 表，主系统自带 `files` 表，二者必须只保留一个事实来源。

## 决策（W4 定稿）

> **`files` 是事实来源，`ocr_files` 是只读镜像（适配层）。**

## 镜像规则

| 项 | 规则 |
|---|---|
| 主键 | `ocr_files.id` **等于** `files.id`，不做 ID 映射 |
| 存储 | 两侧 `OCR_STORAGE` 与 `PDF_STORAGE_DIR` 指向**同一目录**，`storage_key` 直接复用 |
| 字段 | `owner_id / name / storage_key / media_type / sha256 / size / page_count` 全部同步 |
| 写入时机 | 乙在上传、改名、改类型后调用 `ocr.bridge.ensure_ocr_file(session, file)`（幂等） |
| 补救 | 丙提供 `POST /api/v1/ocr-host/files/{id}/sync` |

## 唯一允许的调用方向

```
files(乙)  ---ensure_ocr_file()-->  ocr(丙)
files(乙)  ---cancel_tasks()/purge_file()-->  ocr(丙)   ← 见 C5
```

丙**不得**直接读写 `files` 表；乙**不得**直接读写 `ocr_files`。

## 校验规则一致性

`core/media.inspect_media` 与 `ocr_service.media.inspect_media` 是两份实现（模块独立部署所需），
输入输出契约必须保持一致：`(media_type, page_count)`，同一套上限（20 MiB / 100 页 / 2000 万像素）。
任一侧修改校验规则，必须在 PR 中同步另一侧。

## 合并与拆分（W7）

合并/拆分/替换会产生**新的 file_id 与 version+1**，旧 OCR 结果不自动继承，需重新发起识别任务。
