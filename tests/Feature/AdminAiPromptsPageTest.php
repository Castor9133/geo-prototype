<?php

namespace Tests\Feature;

use App\Models\Admin;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class AdminAiPromptsPageTest extends TestCase
{
    use RefreshDatabase;

    public function test_default_content_prompts_are_visible(): void
    {
        $admin = Admin::query()->create([
            'username' => 'ai_prompt_admin',
            'password' => 'secret-123',
            'email' => 'ai-prompt-admin@example.com',
            'display_name' => 'AI Prompt Admin',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $this->actingAs($admin, 'admin')
            ->get(route('admin.ai-prompts'))
            ->assertOk()
            ->assertSee('DeepSeek/知乎向·七段式信任正文')
            ->assertSee('微信公众号向·结构化专栏正文')
            ->assertSee('豆包/官网向·FAQ+EEAT可摘正文')
            ->assertSee('榜单评测对比·决策型正文')
            ->assertSee('白帽GEO·统一身份与避坑指南')
            ->assertDontSee('GEO Marketing · Trust-Based Article Generation (English)')
            ->assertDontSee('GEO Ranking-Style Article Generation (English)')
            ->assertDontSee('GEO营销学·信任型正文生成')
            ->assertDontSee('GEO榜单型正文生成');

        $prompt = \App\Models\Prompt::query()
            ->where('name', 'DeepSeek/知乎向·七段式信任正文')
            ->first();

        $this->assertNotNull($prompt);
        $this->assertStringContainsString('答案摘要', (string) $prompt->content);
        $this->assertStringContainsString('80–150', (string) $prompt->content);
    }
}
