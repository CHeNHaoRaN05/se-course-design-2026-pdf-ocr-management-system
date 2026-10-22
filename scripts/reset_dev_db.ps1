# 重建本机开发库与存储目录。
# 用于数据库模型（backend/models）发生变更后，让全组本地结构回到一致状态。
#
# 注意：会清空本机 dev.sqlite3 与 data/storage，开发期数据不可恢复。

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$System = Join-Path $Root 'pdf_system'
$Db = Join-Path $System 'data/dev.sqlite3'
$Storage = Join-Path $System 'data/storage'
$VenvPython = Join-Path $System '.venv/Scripts/python.exe'

if (!(Test-Path -LiteralPath $VenvPython)) {
    throw "未找到主系统虚拟环境：$VenvPython`n请先按 README 完成初始化。"
}

Write-Host '停止正在运行的 API / worker 进程后按任意键继续...'
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')

if (Test-Path -LiteralPath $Db) {
    Remove-Item -LiteralPath $Db -Force
    Write-Host "已删除 $Db"
}
if (Test-Path -LiteralPath $Storage) {
    Remove-Item -LiteralPath $Storage -Recurse -Force
    Write-Host "已删除 $Storage"
}

Set-Location -LiteralPath $System
& $VenvPython -m backend.scripts.init_db

Write-Host ''
Write-Host '开发库已重建。请确认输出中同时出现「主系统表已建立」与「OCR 模块表已建立」。'
