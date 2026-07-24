#Requires -Version 5.1
<#
.SYNOPSIS
  本地拉起 GEO Suite Phase1/2：GEORank + GEOFlow（必须同时可用）。

.DESCRIPTION
  - GEORank: docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.suite.yml
  - GEOFlow: 必须存在 ..\GEOFlow\docker-compose.yml，否则失败退出
  - 入口统一使用 localhost（勿混用 127.0.0.1，否则 GEOFlow 会 419）
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$GeoflowRoot = Join-Path (Split-Path -Parent $Root) "GEOFlow"

function Ensure-SuiteSecret([string]$EnvPath, [string]$Key) {
    if (-not (Test-Path $EnvPath)) { return }
    $line = Select-String -Path $EnvPath -Pattern "^$([regex]::Escape($Key))=" -ErrorAction SilentlyContinue
    if ($line) {
        $val = ($line.Line -split '=', 2)[1]
        if (-not [string]::IsNullOrWhiteSpace($val)) { return }
    }
    $secret = -join ((48..57 + 97..122) | Get-Random -Count 40 | ForEach-Object { [char]$_ })
    if ($line) {
        (Get-Content $EnvPath) | ForEach-Object {
            if ($_ -match "^$([regex]::Escape($Key))=") { "$Key=$secret" } else { $_ }
        } | Set-Content $EnvPath -Encoding UTF8
    } else {
        Add-Content -Path $EnvPath -Value "$Key=$secret" -Encoding UTF8
    }
    Write-Host "已写入 $Key 到 $EnvPath" -ForegroundColor Yellow
}

Write-Host "==> GEO Suite 启动 (Phase1/2)" -ForegroundColor Cyan
Write-Host "GEORank: $Root"

$GeoflowCompose = Join-Path $GeoflowRoot "docker-compose.yml"
if (-not (Test-Path $GeoflowCompose)) {
    throw "未找到 GEOFlow：$GeoflowCompose。Option B 要求兄弟目录存在 C:\Cursor local\GEOFlow"
}

# 同步 SSO / 回调密钥（两边一致）
$RankEnv = Join-Path $Root ".env"
$FlowEnv = Join-Path $GeoflowRoot ".env"
Ensure-SuiteSecret $RankEnv "GEOSUITE_SSO_SECRET"
$ssoLine = Select-String -Path $RankEnv -Pattern "^GEOSUITE_SSO_SECRET=" | Select-Object -First 1
$ssoVal = if ($ssoLine) { ($ssoLine.Line -split '=', 2)[1] } else { "" }
if ($ssoVal) {
    foreach ($pair in @(
        @{ Path = $RankEnv; Key = "GEOSUITE_CALLBACK_SECRET" },
        @{ Path = $FlowEnv; Key = "GEOSUITE_SSO_SECRET" },
        @{ Path = $FlowEnv; Key = "GEORANK_CALLBACK_SECRET" }
    )) {
        if (-not (Test-Path $pair.Path)) { continue }
        $existing = Select-String -Path $pair.Path -Pattern "^$([regex]::Escape($pair.Key))=" -ErrorAction SilentlyContinue
        if ($existing) {
            (Get-Content $pair.Path) | ForEach-Object {
                if ($_ -match "^$([regex]::Escape($pair.Key))=") { "$($pair.Key)=$ssoVal" } else { $_ }
            } | Set-Content $pair.Path -Encoding UTF8
        } else {
            Add-Content -Path $pair.Path -Value "$($pair.Key)=$ssoVal" -Encoding UTF8
        }
    }
    # Rank 回调地址（Flow → Rank）
    $callback = "http://host.docker.internal:8000/api/integrations/geoflow/callback"
    if (Test-Path $FlowEnv) {
        if (Select-String -Path $FlowEnv -Pattern "^GEORANK_CALLBACK_URL=" -Quiet) {
            (Get-Content $FlowEnv) | ForEach-Object {
                if ($_ -match "^GEORANK_CALLBACK_URL=") { "GEORANK_CALLBACK_URL=$callback" } else { $_ }
            } | Set-Content $FlowEnv -Encoding UTF8
        } else {
            Add-Content -Path $FlowEnv -Value "GEORANK_CALLBACK_URL=$callback" -Encoding UTF8
        }
        if (-not (Select-String -Path $FlowEnv -Pattern "^GEOSUITE_PUBLIC_URL=" -Quiet)) {
            Add-Content -Path $FlowEnv -Value "GEOSUITE_PUBLIC_URL=http://localhost:3009" -Encoding UTF8
        }
    }
}

Push-Location $Root
try {
    $ErrorActionPreference = "Continue"
    docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.suite.yml up -d
    $code = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($code -ne 0) { throw "GEORank compose 启动失败 (exit=$code)" }
} finally {
    Pop-Location
}

Write-Host "GEOFlow: $GeoflowRoot"
Push-Location $GeoflowRoot
try {
    $ErrorActionPreference = "Continue"
    # Windows：vendor 用 Linux 卷，避免 NTFS bind mount 导致后台每页 10–20s
    $perfCompose = Join-Path $GeoflowRoot "docker-compose.windows-perf.yml"
    $usePerf = $IsWindows -or ($env:OS -match "Windows")
    if ($usePerf -and (Test-Path $perfCompose)) {
        $vendorVol = "geoflow-laravel_geoflow-vendor-linux"
        docker volume create $vendorVol 2>$null | Out-Null
        $autoloadOk = docker run --rm --entrypoint sh -v "${vendorVol}:/out" geoflow-app:latest -c "test -f /out/autoload.php && echo ok"
        if ($autoloadOk -notmatch "ok") {
            Write-Host "填充 GEOFlow Linux vendor 卷（首次较慢）..."
            docker run --rm --entrypoint sh -v "${vendorVol}:/out" geoflow-app:latest -c "cp -a /var/www/html/vendor/. /out/"
        }
        docker compose -f docker-compose.yml -f docker-compose.windows-perf.yml up -d
    } else {
        docker compose up -d
    }
    $code = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($code -ne 0) { throw "GEOFlow compose 启动失败 (exit=$code)" }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "入口（请只用 localhost，勿用 127.0.0.1）：" -ForegroundColor Green
Write-Host "  GEORank 前台:  http://localhost:3009/"
Write-Host "  GEO Suite:    http://localhost:3009/suite"
Write-Host "  GEOFlow:      http://localhost:18080/geo_admin"
Write-Host ""
Write-Host "下一步："
Write-Host "  1) GEORank 后台「GEO Suite」启用并填写 GEOFlow API Token"
Write-Host "  2) 两边 .env 已同步 GEOSUITE_SSO_SECRET；登录 Rank 后可 SSO 进入 Flow"
Write-Host "  3) Flow 发布文章会回调 Rank /api/integrations/geoflow/callback"
