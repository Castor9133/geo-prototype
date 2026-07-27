# Import CN product demo fact cards into GEOFlow knowledge base
# Usage (from GEORank repo root):
#   .\scripts\import-cn-product-demo-kb.ps1
#
# Requires Docker service: geoflow-app (http://localhost:18080)
# Script body is ASCII-safe; Chinese KB name is read from UTF-8 JSON beside fact-cards.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$packDir = Join-Path $root "docs\pilot-demo\cn-product-demo"
$factCards = Join-Path $packDir "fact-cards.md"
$metricsPath = Join-Path $packDir "metrics.json"
$distMetrics = Join-Path $root "dist\pilot-demo\cn-product-demo\metrics.json"
$nameFile = Join-Path $packDir "kb-name.json"
$container = "geoflow-app"

if (-not (Test-Path $factCards)) {
    Write-Error "Missing fact cards: $factCards"
}

if (-not (Test-Path $nameFile)) {
    Write-Error "Missing kb-name.json: $nameFile"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker not found. See docs/pilot-demo/cn-product-demo/import-to-geoflow.md"
}

$running = docker ps --format "{{.Names}}" | Where-Object { $_ -eq $container }
if (-not $running) {
    Write-Error "Container $container is not running."
}

$tmpDir = Join-Path $env:TEMP "cn-product-demo-kb-import"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
$localPhp = Join-Path $tmpDir "import_kb.php"

$php = @'
<?php
$name = json_decode(file_get_contents('/tmp/cn-product-demo-kb-name.json'), true);
$path = '/tmp/cn-product-demo-fact-cards.md';
$content = file_get_contents($path);
if ($content === false || trim($content) === '') {
    throw new RuntimeException('empty fact cards');
}
$content = trim($content);
$kb = App\Models\KnowledgeBase::query()->where('name', $name)->first();
$payload = [
    'name' => $name,
    'description' => 'CN product demo fact cards from Feishu public help center (not official partnership). See GEORank docs/pilot-demo/cn-product-demo/',
    'content' => $content,
    'file_type' => 'markdown',
    'character_count' => mb_strlen($content, 'UTF-8'),
    'word_count' => mb_strlen(strip_tags($content), 'UTF-8'),
    'source_name' => 'Feishu Help Center',
    'source_url' => 'https://www.feishu.cn/hc/zh-CN/articles/697278684206',
    'source_type' => 'website',
    'business_line' => 'cn-product-demo',
    'effective_date' => '2026-07-27',
    'risk_level' => 'low',
    'review_status' => 'reviewed',
];
if ($kb) {
    $kb->update($payload);
} else {
    $kb = App\Models\KnowledgeBase::query()->create($payload);
}
$sync = app(App\Services\GeoFlow\KnowledgeChunkSyncService::class);
$chunkCount = $sync->sync((int) $kb->id, $content, false);
$vectorized = App\Models\KnowledgeChunk::query()
    ->where('knowledge_base_id', $kb->id)
    ->whereNotNull('embedding_model_id')
    ->where('embedding_dimensions', '>', 0)
    ->count();
$total = App\Models\KnowledgeChunk::query()->where('knowledge_base_id', $kb->id)->count();
echo json_encode([
    'id' => (int) $kb->id,
    'name' => $kb->name,
    'chunks' => $chunkCount,
    'chunk_total' => $total,
    'vectorized' => $vectorized,
], JSON_UNESCAPED_UNICODE) . PHP_EOL;
'@

[System.IO.File]::WriteAllText($localPhp, $php, [System.Text.UTF8Encoding]::new($false))
docker cp $factCards "${container}:/tmp/cn-product-demo-fact-cards.md" | Out-Null
docker cp $nameFile "${container}:/tmp/cn-product-demo-kb-name.json" | Out-Null
docker cp $localPhp "${container}:/tmp/import_cn_product_demo_kb.php" | Out-Null

$resultJson = docker exec $container php artisan tinker --execute="require '/tmp/import_cn_product_demo_kb.php';"
Write-Host "GEOFlow KB import result:"
Write-Host $resultJson

try {
    if ($resultJson -match '\{[^\r\n]*\}') {
        $info = $Matches[0] | ConvertFrom-Json
    } else {
        $info = $resultJson | ConvertFrom-Json
    }
    if (Test-Path $metricsPath) {
        $metrics = Get-Content $metricsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $metrics.demo_data = $false
        $metrics.kb_id = [int]$info.id
        $metrics.label = "Imported Flow KB #$($info.id); chunks vectorized"
        $metrics.embedding.chunk_total = [int]$info.chunk_total
        $metrics.embedding.chunk_embedded = [int]$info.vectorized
        if ([int]$info.chunk_total -gt 0) {
            $metrics.embedding.rate = [math]::Round(([double]$info.vectorized) / [double]$info.chunk_total, 4)
        }
        $metrics.admin_detail_url = "http://localhost:18080/geo_admin/knowledge-bases/$($info.id)/detail"
        $out = $metrics | ConvertTo-Json -Depth 8
        [System.IO.File]::WriteAllText($metricsPath, $out, [System.Text.UTF8Encoding]::new($false))
        $distDir = Split-Path $distMetrics -Parent
        if (-not (Test-Path $distDir)) { New-Item -ItemType Directory -Force -Path $distDir | Out-Null }
        Copy-Item $metricsPath $distMetrics -Force
        Write-Host "Updated metrics.json kb_id=$($info.id) chunks=$($info.chunk_total) vectorized=$($info.vectorized)"
    }
} catch {
    Write-Host "Could not parse tinker JSON; open admin UI to verify."
    Write-Host $_.Exception.Message
}

Write-Host "Open: http://localhost:18080/geo_admin/knowledge-bases"
