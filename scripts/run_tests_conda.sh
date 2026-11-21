#!/usr/bin/env bash
# 用 conda 环境复现主线的自动化测试（Git Bash / Windows 实测通过）
#
# 用法：
#   bash scripts/run_tests_conda.sh [仓库根目录]
# 不传参数时默认使用本脚本所在仓库的根目录。
#
# 依赖的 conda 环境：
#   ocrpaddle  Python 3.12 + 后端/OCR 测试依赖
#   se_node    Node.js 20（可用 conda create -y -n se_node nodejs=20 创建）
# 可通过 BACKEND_ENV / NODE_ENV 环境变量覆盖。
#
# 注意：Windows 的 cmd 不展开 tests/*.test.mjs，导致 npm test 失败；
# 这里由 Bash 展开通配符后交给 node --test，等价于 CI 在 Ubuntu 上的行为。

set -euo pipefail

ROOT="$(cd "${1:-$(dirname "$0")/..}" && pwd)"
BACKEND_ENV="${BACKEND_ENV:-ocrpaddle}"
NODE_ENV="${NODE_ENV:-se_node}"

export MSYS_NO_PATHCONV=1
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

echo "==> [1/4] 后端 + OCR 服务 pytest ($BACKEND_ENV)"
cd "$ROOT/pdf_system"
PYTHONPATH=../pdf_ocr_module conda run -n "$BACKEND_ENV" python -m pytest \
    backend/tests ../pdf_ocr_module/ocr_service/tests -q

echo "==> [2/4] 前端依赖安装 ($NODE_ENV)"
cd "$ROOT/pdf_system/frontend"
conda run -n "$NODE_ENV" npm ci --no-audit --no-fund

echo "==> [3/4] 前端单测 ($NODE_ENV)"
conda run -n "$NODE_ENV" node --test tests/*.test.mjs

echo "==> [4/4] 前端构建 ($NODE_ENV)"
conda run -n "$NODE_ENV" npm run build

echo "==> 全部通过"
