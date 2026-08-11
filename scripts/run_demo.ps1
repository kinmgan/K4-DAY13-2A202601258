<#!
.SYNOPSIS
Starts the FastAPI chat API and the Streamlit demo dashboard together.

.DESCRIPTION
The API runs in the background. Streamlit stays in the current terminal and
prints the URL to open. Press Ctrl+C in this terminal to stop both processes.
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$envFile = Join-Path $repoRoot ".env"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Không tìm thấy virtual environment. Hãy tạo .venv và chạy pip install -r requirements.txt trước."
}
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Không tìm thấy .env. Hãy copy .env.example thành .env trước."
}

$api = Start-Process `
    -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--env-file", ".env") `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -PassThru

try {
    Write-Host "API đang khởi động tại http://127.0.0.1:8000" -ForegroundColor Cyan
    Write-Host "Đang mở dashboard Streamlit..." -ForegroundColor Cyan
    & $python -m streamlit run dashboard.py
}
finally {
    if ($api -and -not $api.HasExited) {
        Stop-Process -Id $api.Id -Force
    }
}
