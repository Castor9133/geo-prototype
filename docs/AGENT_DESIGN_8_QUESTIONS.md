# GEO Prototype：智能体设计八问（GEO 回合 MVP）

> 文档版本：2026-07-29 · 对应「GEO 回合 MVP：从演示壳到可讲通闭环」

**项目名称**：geo-prototype / GEO Suite  
**范围**：Run 总线、SEO/GEO 双 Tab、拓词→内容、分发预览、三层观测、无白号演示

---

## 一、产品需求

### 1. 产品适用场景

- **典型用户**：需要向客户讲通「诊断→内容→观测」的 GEO 顾问 / 内部演示同学。
- **任务边界（做）**：以 **GEO Run（回合）** 为作业单位；SEO 四模块真查；拓词选题真落库；知识库/正文真生成；GEO 漏斗与观测用高仿真剧本演示（Suite 观测页为**剧本高仿真监测壳**，模拟真实 AI 答案监测产品界面，**非白号采样**）；**目标 AI 侧重**（`geo-ai-focus-dji`）为演示策略表，拓词/分发生成前可提示，可选注入，**禁止写成实测引用率**。
- **任务边界（不做）**：各 AI 平台真实登录采样 / 白号池；真发公众号/抖音；多品牌自由深剧本；把 SEO+GEO 打成神秘总分。
- **成功场景**：新建 Run 后，诊断/拓词/任务/观测均可按 `run_id` 回溯；检查页 SEO Tab 真结果 + GEO Tab 演示漏斗；分发仅预览就绪。
- **失败或应拒答场景**：把演示剧本写成「实测引用率」；暗示已公开发布。
- **体验**：前台仅顶栏 Suite 回合；Admin 侧栏退出主叙事。

### 2. 用户意图识别与提示词管控

- **意图**：页面检查 / 选题扩词 / 内容草稿 / 观测解读；不把「推荐大疆吗」当作观测题面。
- **拒答与澄清**：无白号时明确「方法演示」；观测评本品出现率与证据密度。
- **注入防护**：诊断 LLM 建议口径约束（禁止把外链就绪写成答案引用率）。
- **密钥**：不进 Git；演示免登录仅限内网 demo open admin。

---

## 二、质量与工程

### 3. 结果评估与修正

- **分层**：SEO 规则分（真）/ GEO 剧本占比（演）/ 内容草稿人工复核 / 分发就绪标记（非发布）。
- **人工复核点**：内容草稿、渠道壳预览、观测解读文案；观测驾驶舱 KPI/矩阵来自剧本聚合，验收口径是「是否像监测产品」而非「是否等于实测」。
- **回归**：Run API 创建→handoff→steps；静态剧本 JSON 版本字段。
- **预算**：诊断 LLM 可降级规则建议；拓词/内容走既有配额。

### 4. 提示词标准化

- 内容引擎提示词：`ce_content_prompts` + Admin 提示词库；内置细版 **10 套**（`CHINA_PROMPTS`，含 `{{entity}}` / `{{Knowledge}}`），list/restore 时同步正文并停用非内置标题。
- 观测/GEO 检查共用：`dist/pilot-demo/geo-observe-funnel-dji-vs-autel.json`（及 `docs/pilot-demo/` 副本）。
- 变更：先改 JSON / 八问，再改前端回放。

### 5. 工具调用规范化

| 工具/API | 权限 | 失败表现 |
|----------|------|----------|
| `POST/GET /api/geo-runs` | OptionalUser / demo | 404/400 JSON |
| `PATCH /api/geo-runs/{id}/handoff` | OptionalUser | 无 run → 先 ensure |
| `POST .../tasks/from-keywords` | AdminUser（demo open） | 至少 1 词 |
| `GET .../geo-preview` / `scripts/{key}` | OptionalUser | 剧本缺失 404 |
| 诊断 `/api/diagnostics` | 既有 | 队列失败 FAILED |

- **可观测性**：`artifacts.steps` + `GET /api/geo-runs/{id}/steps`（Board）。

### 6. 状态与上下文

- **Run**：表 `geo_runs`；前端 `localStorage` 存 `runId` 作缓存，以服务端 artifacts 为准。
- **追溯**：`run_id` 贯穿 URL query 与 handoff；steps 有序事件。

### 7. 数据链路与飞轮

- **在线真**：SEO、拓词、KB、内容任务。
- **演示**：GEO 漏斗、分发就绪、观测三层回放（无白号）；平台侧重/信源偏好/标题建议同源 `geo-ai-focus-dji`。
- **样例锁死**：实体 DJI Mini 5 Pro；竞品 Autel；平台 豆包/元宝/Kimi/DeepSeek。

### 8. Workflow / 编排

线性：`CreateRun → SEO+GEO → 知识 → 拓词选题 → 内容/分发预览 → 观测`。  
降级：诊断 LLM → 规则建议；观测 API → 静态 JSON。

---

## 面向 AI 的接口三问

**Agent 接口面**：`/api/geo-runs*`、诊断报告、`/api/content-engine/tasks`。

| # | 结论 | 说明 |
|---|------|------|
| **Q1 状态可见性** | 是 | `GET /geo-runs/{id}` 与 `artifacts` 可读当前 URL、报告、选题、任务、渠道就绪 |
| **Q2 自主获取** | 是 | Agent/前端可拉 Run、剧本、报告，无需人工粘贴 |
| **Q3 运行可视化** | 是 | `GET /geo-runs/{id}/steps` 提供结构化步骤 Board；测试智能体可按 `run_id` 断言 |

### 演示免责声明（强制文案）

- 角标：**方法演示·无白号采样**
- GEO Tab / 观测：占比来自剧本聚合，**禁止写成实测引用率**
- 分发：**标记就绪 ≠ 已公开发布**；无外发 API

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-29 | GEO 回合 MVP 首版八问 + 接口三问落盘 |
