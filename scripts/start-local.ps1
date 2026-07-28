# GEORank local bare-metal (no Docker by default)
# Requires local Postgres + Redis; see docs/本地裸跑-postgres-redis.md
param(
    [switch]$SkipMigrate,
    [switch]$SkipWorker,
    [int]$ApiPort = 8000,
    [int]$WebPort = 3009
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> GEORank local (no Docker default)" -ForegroundColor Cyan

if (-not (Test-Path "$Root\.env")) {
    Write-Host "Missing .env; copy from .env.example and set:" -ForegroundColor Yellow
    Write-Host "  POSTGRES_HOST=127.0.0.1"
    Write-Host "  REDIS_HOST=127.0.0.1"
    Write-Host "  CONTENT_BACKEND_MODE=native-python"
    Write-Host "Docs: docs/本地裸跑-postgres-redis.md"
    exit 1
}

$venvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating venv..." -ForegroundColor Cyan
    python -m venv "$Root\backend\.venv"
    & $venvPython -m pip install -U pip
    & $venvPython -m pip install -r "$Root\backend\requirements.txt"
}

$env:PYTHONPATH = Join-Path $Root "backend"
Get-Content "$Root\.env" | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith('#')) { return }
    $i = $line.IndexOf('=')
    if ($i -lt 1) { return }
    $k = $line.Substring(0, $i).Trim()
    $v = $line.Substring($i + 1).Trim()
    if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
        $v = $v.Substring(1, $v.Length - 2)
    }
    if ($k -match '^(GEORANK_SEED_ADMIN_PASSWORD|GEORANK_FRONTEND_PORT|GEORANK_API_PORT|GEORANK_HTTP_PORT|GEORANK_HTTPS_PORT)') {
        return
    }
    Set-Item -Path "Env:$k" -Value $v
}

if (-not $SkipMigrate) {
    Write-Host "Alembic migrate..." -ForegroundColor Cyan
    Push-Location (Join-Path $Root "backend")
    & $venvPython -m alembic upgrade head
    Pop-Location
}

Write-Host "API :$ApiPort ..." -ForegroundColor Cyan
$api = Start-Process -FilePath $venvPython -ArgumentList @(
    "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort", "--reload"
) -WorkingDirectory (Join-Path $Root "backend") -PassThru -WindowStyle Minimized

$worker = $null
if (-not $SkipWorker) {
    Write-Host "Celery worker..." -ForegroundColor Cyan
    $worker = Start-Process -FilePath $venvPython -ArgumentList @(
        "-m", "celery", "-A", "app.core.celery_app.celery_app", "worker", "-c", "1", "-l", "info"
    ) -WorkingDirectory (Join-Path $Root "backend") -PassThru -WindowStyle Minimized
}

$proxyScript = Join-Path $Root "scripts\serve-local-proxy.py"
Write-Host "Static + /api proxy :$WebPort ..." -ForegroundColor Cyan
$web = Start-Process -FilePath $venvPython -ArgumentList @(
    $proxyScript, "--port", "$WebPort", "--api", "http://127.0.0.1:$ApiPort"
) -WorkingDirectory $Root -PassThru -WindowStyle Minimized

Write-Host ""
Write-Host "Started (native-python / no Docker):" -ForegroundColor Green
Write-Host "  UI     http://localhost:$WebPort/"
Write-Host "  Suite  http://localhost:$WebPort/suite"
Write-Host "  API    http://localhost:$ApiPort/api/health"
Write-Host "  Admin  http://localhost:$WebPort/admin/content-engine"
Write-Host "  PIDs   api=$($api.Id) web=$($web.Id)$(if ($worker) { " worker=$($worker.Id)" })"
$stopIds = @($api.Id, $web.Id)
if ($worker) { $stopIds += $worker.Id }
Write-Host "Stop: Stop-Process -Id $($stopIds -join ',')"
Write-Host "Note: UI proxies /api to :$ApiPort; demo does not need GEOFlow Compose."
