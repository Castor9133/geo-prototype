#Requires -Version 5.1
<#
.SYNOPSIS
  GEO Suite 启动入口。

.DESCRIPTION
  默认（推荐）：委托 scripts/start-local.ps1 本机裸跑（Postgres+Redis，无 Docker）。
  -UseCompose：legacy Compose 拉起 GEORank（可选 -WithGeoFlow 再起 Laravel GEOFlow）。
  演示默认 CONTENT_BACKEND_MODE=native-python，不再需要 GEOFlow 容器。
#>
param(
    [switch]$UseCompose,
    [switch]$WithGeoFlow,
    [switch]$SkipWorker,
    [int]$ApiPort = 8000,
    [int]$WebPort = 3009
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$GeoflowRoot = Join-Path (Split-Path -Parent $Root) "GEOFlow"

function Test-LocalPort([int]$Port) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(400)
        if ($ok -and $client.Connected) { $client.Close(); return $true }
        $client.Close()
    } catch { }
    return $false
}

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

Write-Host "==> GEO Suite" -ForegroundColor Cyan
Write-Host "GEORank: $Root"

if (-not $UseCompose) {
    if ((Test-LocalPort $ApiPort) -and (Test-LocalPort $WebPort)) {
        Write-Host "检测到本机已有服务 :$ApiPort / :$WebPort，跳过启动。" -ForegroundColor Green
        Write-Host "  Suite  http://localhost:$WebPort/suite"
        Write-Host "  Admin  http://localhost:$WebPort/admin/content-engine"
        Write-Host "若需 Compose legacy：重新运行并加 -UseCompose（可选 -WithGeoFlow）"
        exit 0
    }
    Write-Host "默认裸跑（无 Docker）。手册：docs/本地裸跑-postgres-redis.md" -ForegroundColor Cyan
    $local = Join-Path $PSScriptRoot "start-local.ps1"
    $localArgs = @()
    if ($SkipWorker) { $localArgs += "-SkipWorker" }
    $localArgs += @("-ApiPort", "$ApiPort", "-WebPort", "$WebPort")
    & $local @localArgs
    if ($WithGeoFlow) {
        Write-Host "提示：-WithGeoFlow 仅在 -UseCompose 时启动 Flow 容器。native 演示请用 /admin/content-engine。" -ForegroundColor Yellow
    }
    exit $LASTEXITCODE
}

# ----- legacy Compose 路径 -----
Write-Host "legacy：Docker Compose（CONTENT_BACKEND_MODE 建议设为 legacy-flow 才显示 Flow CTA）" -ForegroundColor Yellow

$RankEnv = Join-Path $Root ".env"
Ensure-SuiteSecret $RankEnv "GEOSUITE_SSO_SECRET"

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

if (-not $WithGeoFlow) {
    Write-Host ""
    Write-Host "已启动 GEORank Compose（未起 GEOFlow）。" -ForegroundColor Green
    Write-Host "  GEORank  http://localhost:3009/"
    Write-Host "  Suite    http://localhost:3009/suite"
    Write-Host "需要 Flow 对照时加 -WithGeoFlow，并设 CONTENT_BACKEND_MODE=legacy-flow"
    exit 0
}

$GeoflowCompose = Join-Path $GeoflowRoot "docker-compose.yml"
if (-not (Test-Path $GeoflowCompose)) {
    throw "未找到 GEOFlow：$GeoflowCompose（-WithGeoFlow 需要兄弟目录）"
}

$FlowEnv = Join-Path $GeoflowRoot ".env"
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

Write-Host "GEOFlow: $GeoflowRoot"
Push-Location $GeoflowRoot
try {
    $ErrorActionPreference = "Continue"
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
Write-Host "legacy Compose 入口（请用 localhost）：" -ForegroundColor Green
Write-Host "  GEORank 前台:  http://localhost:3009/"
Write-Host "  GEO Suite:    http://localhost:3009/suite"
Write-Host "  GEOFlow:      http://localhost:18080/geo_admin"
Write-Host "并设置 CONTENT_BACKEND_MODE=legacy-flow 以显示 Flow CTA。"
