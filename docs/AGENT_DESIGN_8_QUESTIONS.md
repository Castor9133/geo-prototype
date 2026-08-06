# GEO Prototype：智能体设计八问（GEO 回合 MVP）

> 文档版本：2026-08-07 · 对应「GEO 回合 MVP」+ 拓词知识工程闭环

**项目名称**：geo-prototype / GEO Suite  
**范围**：Run 总线、SEO/GEO 双 Tab、拓词→内容、分发预览、三层观测、无白号演示；拓词可选知识库（事实卡+切片）

---

## 一、产品需求

### 1. 产品适用场景

- **典型用户**：需要向客户讲通「诊断→内容→观测」的 GEO 顾问 / 内部演示同学。
- **任务边界（做）**：以 **GEO Run（回合）** 为作业单位；SEO 四模块真查；拓词选题真落库；知识库/正文真生成；**拓词可选绑定知识库**（事实卡定实体关系 + 切片补语境）；GEO 漏斗与观测用高仿真剧本演示（Suite 观测页为**剧本高仿真监测壳**，模拟真实 AI 答案监测产品界面，**非白号采样**）；**目标 AI 侧重**（`geo-ai-focus-dji`）为演示策略表，拓词/分发生成前可提示，可选注入，**禁止写成实测引用率**。
- **任务边界（不做）**：各 AI 平台真实登录采样 / 白号池；真发公众号/抖音；多品牌自由深剧本；把 SEO+GEO 打成神秘总分；拓词强制选库；把 KB 检索写成「实测引用率」。
- **成功场景**：新建 Run 后，诊断/拓词/任务/观测均可按 `run_id` 回溯；检查页 SEO Tab 真结果 + GEO Tab 演示漏斗；分发仅预览就绪；选「深圳广电×第一现场」示范库拓词时隶属关系正确、无自伤交叉。
- **失败或应拒答场景**：把演示剧本写成「实测引用率」；暗示已公开发布；把检索命中宣传为平台实测引用。
- **体验**：前台仅顶栏 Suite 回合；Admin 侧栏退出主叙事。

### 2. 用户意图识别与提示词管控

- **意图**：页面检查 / 选题扩词 / 内容草稿 / 观测解读；不把「推荐大疆吗」当作观测题面。
- **拓词提示方法（多种子）**：先产出 `seed_map`（角色/关系/选题主线），再扩八维；种子默认**非同义并列**（常为机构×栏目/产品×属性/议题）；禁止模板粘贴与分号残留。代码侧对多种子**追加方法附录**（即使 Admin 库内旧 prompt 仍生效）。
- **拓词 × 知识库（可选）**：请求可带 `knowledge_base_id`；**双通道**——`fact_cards` → `knowledge_entity_brief`（身份/隶属/别名/角度/禁语/竞品）优先定关系；`search_chunks` 3～6 条补场景语境。不选库则保持字面启发式。Run/策略已绑库时前端预填。业务样例见 [`docs/pilot-demo/szmg-diyixianchang-kb/`](pilot-demo/szmg-diyixianchang-kb/README.md)。
- **隶属硬约束**：已知 owns(机构,栏目) 时，交叉模板改用旗下/运营/定位；过滤「怎么报道 / 联动合作 / 对…报道怎么样」等自伤句；竞品对才允许对比/替代问法。
- **标题第一关（GEO）**：问法/`platform_title_hints` 须像真人会问 AI 的完整题面（实体清晰、可答、可写证据）；禁止 Keyword Stuffing 与分号粘词。方法对照见 [`docs/GEO_METHODS_IN_PROMPTS.md`](GEO_METHODS_IN_PROMPTS.md)（Aggarwal KDD’24；结构侧 GEO-SFE）。
- **生成模板 GEO 清单**：`CHINA_PROMPTS` 强制答案前置 + Statistics/Cite/Quotation（有知识才写）+ Fluency；**禁止**堆砌与「保证被大模型引用」。
- **拒答与澄清**：无白号时明确「方法演示」；观测评本品出现率与证据密度。
- **注入防护**：诊断 LLM 建议口径约束（禁止把外链就绪写成答案引用率）。
- **密钥**：不进 Git；演示免登录仅限内网 demo open admin。

---

## 二、质量与工程

### 3. 结果评估与修正

- **分层**：SEO 规则分（真）/ GEO 剧本占比（演）/ 内容草稿人工复核 / 分发就绪标记（非发布）。
- **人工复核点**：内容草稿、渠道壳预览、观测解读文案；观测驾驶舱 KPI/矩阵来自剧本聚合，验收口径是「是否像监测产品」而非「是否等于实测」。
- **回归**：Run API 创建→handoff→steps；静态剧本 JSON 版本字段；**多种子拓词**须每个 seed 在词包中可见（模型漏覆盖时用模板回填）；输入中的 `;` 须拆成多种子，禁止整串当分词扩写。
- **拓词金样（知识工程）**：种子 `深圳广电;第一现场` + 示范库 → 禁止「深圳广电怎么报道第一现场」「…联动合作」；允许「旗下/运营/定位」及与竞品（深圳新闻网、独特、深圳报业集团）的合法对照。
- **拓词算法（简述）**：`normalize_seeds` →（可选）加载 KB brief+chunks → 画像规则 → **LLM（先 seed_map → 标题/问法门 → 八维 JSON）** → 漏覆盖/失败则模板+交叉短语回填（owns 感知）→ owns/别名糙词过滤；词面禁止分号；`platform_title_hints` 经标题门过滤（策略 A：不足不补假标题）。
- **拓词提示词**：默认 `DEFAULT_KEYWORD_EXPANSION_CONFIG.system_prompt`；库表 `keyword_expansion` 可覆盖；多种子另注 `MULTI_SEED_METHOD_ADDENDUM`；论文方法见 `docs/GEO_METHODS_IN_PROMPTS.md`。Admin：`/admin/settings` 拓词配置，可「重置」回默认。
- **预算**：诊断 LLM 可降级规则建议；拓词/内容走既有配额。

### 4. 提示词标准化

- 内容引擎提示词：`ce_content_prompts` + Admin 提示词库；内置细版 **10 套**（`CHINA_PROMPTS`，含 `{{entity}}` / `{{Knowledge}}` + `_GEO_METHOD_RULES` / `_GEO_STRUCTURE_RULES`），list/restore 时同步正文并停用非内置标题。
- **拓词**：`keyword_expansion.system_prompt`（`runtime_settings`）+ 多种子方法附录 + **标题第一关**；要求先 `seed_map` 再 `dimensions`/`platform_title_hints`；多种子须覆盖全部 `seeds`，禁止只扩 `seeds[0]` 与 Keyword Stuffing。
- 论文→条款对照：[`docs/GEO_METHODS_IN_PROMPTS.md`](GEO_METHODS_IN_PROMPTS.md)。
- 观测/GEO 检查共用：`dist/pilot-demo/geo-observe-funnel-dji-vs-autel.json`（及 `docs/pilot-demo/` 副本）。
- 变更：先改 JSON / 八问，再改前端回放。

### 5. 工具调用规范化

| 工具/API | 权限 | 失败表现 |
|----------|------|----------|
| `POST/GET /api/geo-runs` | OptionalUser / demo | 404/400 JSON |
| `PATCH /api/geo-runs/{id}/handoff` | OptionalUser | 无 run → 先 ensure |
| `POST .../tasks/from-keywords` | AdminUser（demo open） | 至少 1 词 |
| `POST /api/keywords/expand` | OptionalUser + AI 配额 | 可选 `knowledge_base_id`；无库则启发式；库无效时降级无 brief |
| `GET /api/content-engine/knowledge-bases` | 登录/Admin | 拓词下拉选库 |
| `GET .../geo-preview` / `scripts/{key}` | OptionalUser | 剧本缺失 404 |
| 诊断 `/api/diagnostics` | 既有 | 队列失败 FAILED |

- **可观测性**：`artifacts.steps` + `GET /api/geo-runs/{id}/steps`（Board）；拓词响应 `knowledge_meta`（`kb_id` / `cards_used` / `chunks_used`）。

### 6. 状态与上下文

- **Run**：表 `geo_runs`；前端 `localStorage` 存 `runId` 作缓存，以服务端 artifacts 为准。
- **追溯**：`run_id` 贯穿 URL query 与 handoff；steps 有序事件。

### 7. 数据链路与飞轮

- **在线真**：SEO、拓词、KB、内容任务；拓词可消费同一 CE KB（`fact_cards` + chunks）。
- **演示**：GEO 漏斗、分发就绪、观测三层回放（无白号）；平台侧重/信源偏好/标题建议同源 `geo-ai-focus-dji`；媒体拓词示范包 `szmg-diyixianchang-demo`。
- **样例锁死**：消费电子实体 DJI Mini 5 Pro / 竞品 Autel；媒体示范 深圳广电×第一现场 / 竞品 深圳新闻网·独特·深圳报业集团；平台 豆包/元宝/Kimi/DeepSeek。
- **知识工程口径**：卡片管关系与口径（不靠乱切长文）；L2 故事正文才 `split_chunks(~800)`；检索命中**不是**实测引用率。

### 8. Workflow / 编排

线性：`CreateRun → SEO+GEO → 知识 → 拓词选题 → 内容/分发预览 → 观测`。  
**Suite 级 Agent 可行性与全链路数据流**见 [`GEO_SUITE_AS_AGENT.md`](GEO_SUITE_AS_AGENT.md)；拓词单步加工见 [`KEYWORD_EXPAND_PIPELINE.md`](KEYWORD_EXPAND_PIPELINE.md)。  
降级：诊断 LLM → 规则建议；观测 API → 静态 JSON；拓词无 KB / 模型失败 → 启发式+模板（owns 仍可硬过滤）。

---

## 面向 AI 的接口三问

**Agent 接口面**：`/api/geo-runs*`、诊断报告、`/api/content-engine/tasks`、`POST /api/keywords/expand`（含可选 KB）。

| # | 结论 | 说明 |
|---|------|------|
| **Q1 状态可见性** | 是 | `GET /geo-runs/{id}` 与 `artifacts` 可读当前 URL、报告、选题、任务、渠道就绪、`knowledge_base_id`；KB 列表可读 |
| **Q2 自主获取** | 是 | Agent/前端可拉 Run、剧本、报告、知识库列表并自选 `knowledge_base_id` 扩词，无需人工粘贴事实 |
| **Q3 运行可视化** | 是 | `GET /geo-runs/{id}/steps` 提供结构化步骤 Board；拓词响应 `knowledge_meta` 可断言 `kb_id`/cards/chunks 用量 |

### 演示免责声明（强制文案）

- 角标：**方法演示·无白号采样**
- GEO Tab / 观测：占比来自剧本聚合，**禁止写成实测引用率**
- 分发：**标记就绪 ≠ 已公开发布**；无外发 API

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-07 | 增补 `GEO_SUITE_AS_AGENT.md`（全 Suite Agent 可行性）；拓词加工文更名为 `KEYWORD_EXPAND_PIPELINE.md` |
| 2026-08-07 | 拓词可选 KB 双通道（事实卡+切片）+ owns 硬约束；示范包 `szmg-diyixianchang-kb`；接口三问覆盖 expand meta |
| 2026-08-06 | 拓词/生成模板对齐 Aggarwal GEO + 结构 SFE；标题第一关；`GEO_METHODS_IN_PROMPTS.md` |
| 2026-07-29 | GEO 回合 MVP 首版八问 + 接口三问落盘 |
