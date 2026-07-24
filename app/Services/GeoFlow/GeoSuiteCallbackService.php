<?php

namespace App\Services\GeoFlow;

use App\Models\Article;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Throwable;

/**
 * 向 GEORank 发送 GEO Suite 回调（发布等事件）。
 */
class GeoSuiteCallbackService
{
    public function notifyArticlePublished(Article $article): void
    {
        $url = trim((string) env('GEORANK_CALLBACK_URL', ''));
        $secret = trim((string) env('GEORANK_CALLBACK_SECRET', env('GEOSUITE_SSO_SECRET', '')));
        if ($url === '' || $secret === '') {
            return;
        }

        $publicBase = rtrim((string) (env('APP_URL') ?: 'http://localhost:18080'), '/');
        $slug = trim((string) ($article->slug ?? ''));
        $publicUrl = $slug !== '' ? $publicBase.'/'.$slug : $publicBase.'/geo_admin/articles';

        $companyId = null;
        // 从关联任务/知识库描述中尽力解析 georank_company_id（可选）
        if (! empty($article->task_id)) {
            $companyId = $this->guessCompanyIdFromTask((int) $article->task_id);
        }

        $payload = [
            'event' => 'article.published',
            'task_id' => $article->task_id,
            'article_id' => $article->id,
            'title' => (string) ($article->title ?? ''),
            'slug' => $slug,
            'status' => (string) ($article->status ?? 'published'),
            'public_url' => $publicUrl,
            'external_company_id' => $companyId,
            'occurred_at' => now()->toIso8601String(),
        ];

        $body = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if ($body === false) {
            return;
        }
        $signature = 'sha256='.hash_hmac('sha256', $body, $secret);

        try {
            $response = Http::timeout(8)
                ->withHeaders([
                    'Content-Type' => 'application/json',
                    'Accept' => 'application/json',
                    'X-GeoSuite-Signature' => $signature,
                ])
                ->withBody($body, 'application/json')
                ->post($url);

            if (! $response->successful()) {
                Log::warning('geo_suite.callback_failed', [
                    'status' => $response->status(),
                    'body' => mb_substr($response->body(), 0, 300),
                ]);
            }
        } catch (Throwable $exception) {
            Log::warning('geo_suite.callback_exception', [
                'message' => $exception->getMessage(),
            ]);
        }
    }

    private function guessCompanyIdFromTask(int $taskId): ?string
    {
        try {
            $task = \App\Models\Task::query()->with('knowledgeBases')->find($taskId);
            if (! $task) {
                return null;
            }
            foreach ($task->knowledgeBases ?? [] as $kb) {
                $desc = (string) ($kb->description ?? '');
                if (preg_match('/company_id=([A-Za-z0-9_-]+)/', $desc, $m)) {
                    return $m[1];
                }
                $content = (string) ($kb->content ?? '');
                if (preg_match('/georank_company_id:\s*([A-Za-z0-9_-]+)/', $content, $m)) {
                    return $m[1];
                }
            }
        } catch (Throwable) {
            return null;
        }

        return null;
    }
}
