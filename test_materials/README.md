# 测试素材

本目录是《软件测试文档》第 3.3 节与附录 A 所述样本的随仓库副本，供团队成员各自跑测试与现场演示时直接取用，不必现场造数据。

## 文件清单

| 文件 | 用途 |
|---|---|
| `本地OCR演示样本.pdf` | 2 页正常 PDF：上传、在线阅读、翻页、OCR 任务、导出 |
| `扫描件OCR演示.png` | 界面截图：分享链接只读访问（禁止下载）的期望形态 |
| `真实扫描件OCR.pdf` | 2 页矢量“设备登记记录”，用于贴近真实排版的 OCR 识别演示 |
| `真实扫描件OCR.png` | 上者的页面图像，作为识别结果的人工对照 |
| `损坏文件.pdf` | 29 字节截断文件：内容校验失败（invalid_or_encrypted_pdf） |
| `超出大小限制.bin` | 21 MB 定长数据：验证 20 MiB 上传上限拒绝 |
| `render/page-1.png`、`page-2.png` | 上述 2 页 PDF 的 1275×1650 渲染基准图，用于比对按页渲染结果 |

## 使用顺序

1. 先按 `docs/team/getting-started.md` 起服务，登录页出现即说明主链路可用。
2. 需要成体系的账号与样本时，用脚本一次生成，不必手工注册：

   ```powershell
   cd pdf_system
   python -m backend.scripts.prepare_demo --seed --seed-index --api http://127.0.0.1:8000
   ```

   该命令产出 D-01～D-05 样本、`document-01.pdf`～`document-14.pdf`、三个角色账号与检索夹具，落在 `pdf_system/test_materials/demo/`。
3. 本目录的文件用于脚本之外的补充场景：故意损坏、超限、真实排版扫描。

## 注意事项

- `超出大小限制.bin` 是 21 MB 垃圾数据，只为触发上限，不含任何有效内容；需要重建时用
  `fsutil file createnew 超出大小限制.bin 22020096`（Windows）或
  `truncate -s 22020096 超出大小限制.bin`（Linux / macOS）。
- `真实扫描件OCR.pdf` 与 `.png` 为合成的设备登记表，不含真实人员信息，可对外分发。
- 素材一旦替换，请同步核对《软件测试文档》附录 A 的样本编号，避免文档与文件对不上。
