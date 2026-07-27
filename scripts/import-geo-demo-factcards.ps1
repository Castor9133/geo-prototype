# Import GEO demo fact cards into GEOFlow (manual helper)
# Usage (from GEORank repo root):
#   .\scripts\import-geo-demo-factcards.ps1
#
# This does NOT call Flow APIs automatically (auth/CSRF vary by env).
# It opens the admin KB page and prints the markdown path to paste.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$factCards = Join-Path $root "docs\pilot-demo\geo-demo-column\fact-cards.md"
$guide = Join-Path $root "docs\pilot-demo\geo-demo-column\import-to-geoflow.md"
$flowAdmin = "http://localhost:18080/geo_admin/knowledge-bases"

if (-not (Test-Path $factCards)) {
    Write-Error "Missing fact cards: $factCards"
}

Write-Host "GEO 示范栏目 · 事实卡导入助手"
Write-Host "1) 打开 GEOFlow 知识库（仅用 localhost，勿混用 127.0.0.1）"
Write-Host "   $flowAdmin"
Write-Host "2) 新建或选用「GEO 示范栏目」知识库"
Write-Host "3) 粘贴正文："
Write-Host "   $factCards"
Write-Host "4) 触发切片 + Embedding；完成后可把 dist/pilot-demo/geo-demo-column/metrics.json 的 demo_data 改为 false"
Write-Host "步骤说明：$guide"

if (Get-Command Start-Process -ErrorAction SilentlyContinue) {
    Start-Process $flowAdmin
    Start-Process notepad.exe $factCards
}

Get-Content $factCards -Encoding UTF8 | Select-Object -First 20
Write-Host "`n... (完整内容见 fact-cards.md)"
