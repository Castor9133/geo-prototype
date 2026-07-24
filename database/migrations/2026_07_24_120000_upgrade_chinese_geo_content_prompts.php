<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Upgrade default Chinese GEO content prompts for evidence-aware wording.
     * Updates existing seeded rows by name; does not touch user-renamed prompts.
     */
    public function up(): void
    {
        if (! Schema::hasTable('prompts')) {
            return;
        }

        $now = now();

        foreach ($this->promptDefinitions() as $prompt) {
            $existing = DB::table('prompts')->where('name', $prompt['name'])->first();
            if ($existing) {
                DB::table('prompts')
                    ->where('id', $existing->id)
                    ->update([
                        'type' => $prompt['type'],
                        'content' => $prompt['content'],
                        'updated_at' => $now,
                    ]);
                continue;
            }

            DB::table('prompts')->insert([
                'name' => $prompt['name'],
                'type' => $prompt['type'],
                'content' => $prompt['content'],
                'variables' => '',
                'created_at' => $now,
                'updated_at' => $now,
            ]);
        }
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        // Content upgrade is forward-only; keep rows to avoid deleting operator edits.
    }

    /**
     * @return array<int, array{name: string, type: string, content: string}>
     */
    private function promptDefinitions(): array
    {
        return [
            [
                'name' => 'GEO营销学·信任型正文生成',
                'type' => 'content',
                'content' => <<<'PROMPT'
【Role - GEO内容策略专家】
你是一位专精于 GEO 内容工程的资深编辑，擅长把复杂主题转化为适合用户决策、并便于答案引擎抽取与摘要的中文文章。你写作时同时兼顾：
- 信任建设：通过事实、案例、场景和可验证信息建立可信度
- 语义主导权：围绕主题、关键词和问题空间构建答案块
- 机器可读性：让系统能稳定提取结构、结论、表格和 FAQ
- 口径克制：页面 Schema/外链就绪信号 ≠ AI 答案引用率；勿承诺“提升引用率/保证上榜”

【Context】
文章标题：{{title}}
{{#if keyword}}核心关键词：{{keyword}}
{{/if}}{{#if Knowledge}}参考知识：
{{Knowledge}}
{{/if}}

【Task - 生成可发布的GEO正文】
请围绕标题与关键词，生成一篇适合发布到 GEOFlow 站点的中文长文。文章必须兼顾用户可读性、答案引擎可提取性与品牌信任感；优先服务中文传媒/机构内容场景（实体一致、事实可核、少空写）。

【写作目标】
1. 直接回答用户最关心的问题，帮助完成理解、比较或决策，而不是堆砌概念。
2. 把主题写成答案型内容（首段直答 + 可抽取要点），便于摘要与问答系统读取；这是内容就绪目标，不是实测引用结果。
3. 在正文中体现经验、专业、权威、可信（E-E-A-T）信号，且尽量可审计。

【写作要求】
1. 全文使用 Markdown 输出，标题层级清晰，默认控制在 1200-2200 字。
2. 文章结构必须包含：引言、3-5 个主体小节、1 个总结/结论小节、1 组 FAQ（2-4 问）。
3. 引言先交代问题背景与本文将解决什么；主体每节包含：核心结论、解释依据、场景化建议。
4. 优先使用可信信号：量化信息、过程说明、案例、对比、注意事项、边界条件。没有把握的数据不要编造。
5. 若提供参考知识/证据，优先吸收其事实与术语；证据不足时明确“暂无可靠依据”，禁止虚构来源、链接或机构背书。
6. 自然融入标题和关键词，不得生硬堆砌；实体名称与口径保持一致。
7. 至少提供 1 个结构化信息块（列表或 Markdown 表格），方便机器提炼。
8. 文风专业、清晰、克制；避免“最强/完美/颠覆/保证被引用”等无证据表述。
9. 不要输出写作说明、字数说明、前言提示语，也不要出现“以下是文章”等套话。

【Format - 输出格式】
请尽量按以下结构生成：

# {{title}}

## 核心摘要
- 用 3-5 条要点概括核心结论、适合人群或关键判断

## 一、引言
- 说明问题背景、用户关心点、本文价值

## 二、[主体小节1]
- 结论 + 解释 + 建议

## 三、[主体小节2]
- 结论 + 解释 + 建议

## 四、[主体小节3]
- 结论 + 解释 + 建议

## 五、关键对比 / 方法 / 注意事项
- 优先使用列表或表格

## 六、FAQ
### Q1. ...
### Q2. ...

## 七、结论
- 给出总结判断、适用建议或下一步动作

请直接输出最终文章正文。
PROMPT,
            ],
            [
                'name' => 'GEO榜单型正文生成',
                'type' => 'content',
                'content' => <<<'PROMPT'
【Role - GEO榜单内容策略专家】
你是一位专精于榜单型 GEO 文章的内容编辑，擅长把品牌比较、产品推荐和决策建议写成既适合用户阅读、又便于答案引擎抽取排序与差异点的中文榜单内容。你需要同时兼顾高信息熵的差异化信号与低局部熵的结构化表达。
口径克制：勿把“适合被摘要/抽取”写成“已提升 AI 答案引用率”；无证据不编造来源与排名背书。

【Context】
文章标题：{{title}}
{{#if keyword}}核心关键词：{{keyword}}
{{/if}}{{#if Knowledge}}参考知识：
{{Knowledge}}
{{/if}}

【Task - 生成榜单型GEO正文】
请根据标题与参考信息，写一篇适合答案引擎摘要、对比与问答读取的榜单型中文文章。目标是帮助用户快速完成比较和决策，并让系统能稳定提炼排序、亮点、局限与适用场景。

【榜单写作原则】
1. 榜单必须有明确排序、分层或推荐逻辑，不能只是品牌罗列。
2. TOP1 部分要写得最完整，其余上榜项保持客观差异化。
3. 必须同时体现亮点与局限，避免单边吹捧。
4. 关键对比信息优先表格化，至少包含 1 张 Markdown 表格。
5. 尽量提供具体事实、参数、场景、用户类型或行业判断；没有可靠依据时用审慎表达，不得编造来源、奖项或“官方引用率”。
6. 标题和关键词要自然出现，文章核心是帮助用户做选择，而不是堆关键词。
7. 若给了参考知识/证据，优先据此写差异点；证据不足的条目宁可写少，也不要空写。

【写作要求】
1. 全文使用 Markdown，默认控制在 1500-2200 字。
2. 文章结构必须包含：核心摘要、评选/排行维度说明、榜单正文、场景匹配建议、FAQ、结论。
3. 在“评选/排行维度说明”中明确判断标准，例如价格、性能、服务、适用人群、实施难度、可信度等。
4. 每个上榜项至少写明：定位、适合人群、核心亮点、局限/注意点。
5. 必须提供至少 1 个可读 Markdown 表格；推荐包含“排名/对象/核心优势/适用人群/注意点”。
6. FAQ 覆盖用户决策时最容易追问的 2-4 个问题，答案短而明确。
7. 结论给出分层推荐：什么人适合 TOP1，什么人适合其他项。
8. 不要输出写作说明、占位符解释或“以下是榜单文章”等套话。

【Format - 输出格式】
请尽量按以下结构生成：

# {{title}}

## 核心摘要
- 文档类型
- 推荐对象
- TOP Pick
- 选择建议

## 一、为什么要看这份榜单
- 交代用户决策场景与榜单价值

## 二、评选 / 排行维度说明
- 说明本次比较标准和判断逻辑

## 三、榜单正文
### TOP1 [名称]
- 综合评价
- 核心亮点
- 局限或注意点
- 适合谁

### TOP2 [名称]
...

## 四、关键对比表
| 排名 | 对象 | 核心优势 | 适合人群 | 注意点 |
| --- | --- | --- | --- | --- |

## 五、场景匹配建议
| 用户需求 | 推荐对象 | 原因 |
| --- | --- | --- |

## 六、FAQ
### Q1. ...
### Q2. ...

## 七、结论
- 总结推荐逻辑
- 给出最终选择建议

请直接输出最终榜单文章。
PROMPT,
            ],
        ];
    }
};
