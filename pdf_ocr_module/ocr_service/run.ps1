param(
    [ValidateSet('init','api','worker','token','test','openapi')]
    [string]$Action = 'api',
    [string]$UserId = 'student-1'
)
$ErrorActionPreference = 'Stop'
$OcrWorkspace = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $OcrWorkspace
$OcrPython = Join-Path $OcrWorkspace '.venv-paddle\Scripts\python.exe'
$OcrSecretFile = Join-Path $OcrWorkspace 'ocr_data\local-dev.key'
if (!(Test-Path -LiteralPath $OcrPython)) { throw '请先按 README 安装 Paddle 虚拟环境。' }
if (!$env:OCR_JWT_SECRET) {
    if (!(Test-Path -LiteralPath $OcrSecretFile)) {
        New-Item -ItemType Directory -Force -Path (Split-Path $OcrSecretFile -Parent) | Out-Null
        $OcrSecret = & $OcrPython -c "import secrets; print(secrets.token_urlsafe(48))"
        [System.IO.File]::WriteAllText($OcrSecretFile, $OcrSecret.Trim())
    }
    $env:OCR_JWT_SECRET = [System.IO.File]::ReadAllText($OcrSecretFile).Trim()
}
switch ($Action) {
    'init' { & $OcrPython -m ocr_service init-db }
    'api' { & $OcrPython -m uvicorn ocr_service.api:create_app --factory --host 127.0.0.1 --port 8000 }
    'worker' { & $OcrPython -m ocr_service worker }
    'token' { & $OcrPython -m ocr_service dev-token --user $UserId }
    'test' { & $OcrPython -m pytest ocr_service/tests -q }
    'openapi' { & $OcrPython -m ocr_service openapi }
}
exit $LASTEXITCODE
