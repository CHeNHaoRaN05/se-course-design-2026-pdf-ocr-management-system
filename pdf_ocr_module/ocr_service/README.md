# PDF 文档 OCR 服务模块

面向 React + pdf.js / FastAPI + MySQL 的独立 OCR 模块，提供图片与 PDF 识别、数据库异步队列、校对、规则表格还原、五种格式导出和中文全文检索。

文档：[接口定义](docs/API.md) · [功能架构](docs/ARCHITECTURE.md) · [验证报告](docs/VALIDATION.md) · [OpenAPI](docs/openapi.json) · [MySQL DDL](docs/mysql-schema.sql)。

## 启动

在包含 ocr_service 文件夹的目录打开 PowerShell：

```powershell
.\ocr_service\run.ps1 init
# 终端一
.\ocr_service\run.ps1 api
# 终端二
.\ocr_service\run.ps1 worker
# 终端三
.\ocr_service\run.ps1 token -UserId lab-member
```

打开 http://127.0.0.1:8000/docs，在 Authorize 中填入令牌，依次调用上传、建任务、查询结果和导出接口。

脚本使用 .venv-paddle 环境，在 ocr_data/local-dev.key 创建本机随机开发密钥。生产部署设置 OCR_JWT_SECRET，由登录模块签发令牌。

## 从源码包安装

需要 Python 3.12。解压 pdf_ocr_module.zip 后，在包含 ocr_service 的目录执行：

```powershell
py -3.12 -m venv .venv-paddle
.\.venv-paddle\Scripts\python.exe -m pip install -r ocr_service\environment-service-lock.txt
.\.venv-paddle\Scripts\python.exe -m ocr_service download-models
.\ocr_service\run.ps1 init
```

源码包不含模型二进制、数据库、密钥或缓存。download-models 从官方地址下载标准 Paddle 模型，并验证 models/manifest.json 中的 SHA256。当前工作区的标准模型已就绪。依赖锁定文件覆盖 CPU 推理、API 与测试工具；GPU 环境尚未验证。

## 配置

| 环境变量 | 用途 |
|---|---|
| OCR_DATABASE_URL | 默认 SQLite；生产使用 mysql+pymysql://user:password@host/pdf_system?charset=utf8mb4 |
| OCR_STORAGE | 默认工作目录下 ocr_data；API 与 worker 共享 |
| OCR_JWT_SECRET | 至少 32 字符的随机签名密钥 |
| OCR_DET_WEIGHTS | 默认模块 models/text_detector.pdparams |
| OCR_REC_WEIGHTS | 默认模块 models/text_recognizer.pdparams |
| OCR_CUSTOM_REC_WEIGHTS | 可选、与 configs/recognizer.yml 兼容的识别权重 |
| OCR_HANDWRITING_WEIGHTS | 可选专用手写区域 YOLO 模型 |
| OCR_TORCH_PYTHON | 可选检测进程的 Python 可执行文件 |
| OCR_DEVICE | 默认 cpu |

专用手写检测和自定义识别模型未配置时，对应能力不开放；capabilities 返回实际配置情况。默认文件上限 20 MiB、100 页、单页 2000 万像素；其他参数用 Settings 注入。

MySQL 需要 8+、InnoDB 和 utf8mb4。创建数据库、设置专用应用账号与 OCR_DATABASE_URL 后运行 init-db；也可在空库执行 docs/mysql-schema.sql。初始化不会迁移已有表结构。

pdf_text_index 使用 ngram 全文索引；MySQL 长度至少为 2 的查询走 MATCH AGAINST。单字符查询及 SQLite 开发库走子串匹配。生产 MySQL 与多 worker 行为需部署环境联调。

## 测试与交付包

```powershell
.\ocr_service\run.ps1 test
.\.venv-paddle\Scripts\python.exe -m ocr_service.tests.acceptance_http
.\.venv-paddle\Scripts\python.exe -m ocr_service openapi
.\.venv-paddle\Scripts\python.exe -m ocr_service mysql-ddl
.\.venv-paddle\Scripts\python.exe -m ocr_service.build_bundle
```

测试使用 tests/documents.py 动态生成的设备登记文档，不需要外部样本。中文字体默认 Windows simhei.ttf；其他系统用 OCR_TEST_FONT 指定中文字体。运行输出位于 .verification/，不会进入交付包。

## 范围

已提供 JWT、角色、资源归属、操作日志、基础统计及配额预留钩子。注册登录、文件分类标签、分享和配额结算由主系统实现。表格支持完整规则线框，不支持无线框与合并单元格；导出支持 TXT、JSON、CSV、HTML、XLSX。

代码、推理配置、第三方实现及字典都从模块自身目录加载。第三方声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
