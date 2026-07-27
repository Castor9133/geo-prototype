# GEO Suite 领导汇报与演示手册

> 面向：业务负责人 / 技术负责人 / 投资或上级汇报  
> 口径：整合原型（共识版）— 合成栏目「GEO 示范栏目」一条故事线  
> 更新日期：2026-07-24

---

## 1. 一句话讲清

**GEO Suite** 把「被找到 → 被引用 → 被信任」连成可演示闭环：

**诊断（就绪信号）→ 拓词 → live 移交 GEOFlow → 回看 → 事实卡看板 → L3 信任素材 → 可信观测抽样。**

它不是把两套系统揉成一个大单体，而是用薄集成做成**可运营的内容工程链路**；测量与生产解耦。

---

## 2. 为什么现在要做（业务背景）

| 变化 | 对品牌的影响 |
|------|----------------|
| 用户越来越多直接问 AI，而不是点十条蓝链 | 流量入口从「排名」扩展到「答案层」 |
| AI 可能不提你、提错你 | 等于搜索结果里没有你，或品牌叙事失真 |
| 内容生产若靠空写 | 审核成本高、无法稳定引用事实 |

**GEO（Generative Engine Optimization，生成式引擎优化）**：结构化内容与在线存在，提升品牌在 ChatGPT / Perplexity / Gemini / AI Overview 等生成式回答中的可见度与准确性。  
相近说法：AEO、AIO、LLMO。实务上常互换使用。

与传统 SEO 的关系：技术 SEO、内容质量、结构化数据仍然重要；评估指标需加上 **AI 是否提到、提得对不对**。

---

## 3. 产品架构（给领导的图）

```text
                    GEO Suite（统一入口 /suite）
                               │
          ┌────────────────────┼────────────────────┐
          ▼                                         ▼
   GEORank（规划侧）                          GEOFlow（生产侧）
   · 诊断                                      · 知识库 / 素材库
   · 拓词                                      · 内容任务 / 文章
   · 拓词                                      · 审核 / 发布 / 分发
          │                                         ▲
          └──── handoff（服务端代理） ───────────────┘
```

### 设计原则（汇报时强调）

1. **两引擎、一闭环**：职责清晰，可独立演进。  
2. **薄契约**：状态查询 + 移交 handoff + 后台配置，不共享数据库。  
3. **密钥不进浏览器**：浏览器只打 GEORank；Token 只在服务端。  
4. **可演示降级**：未配 GEOFlow Token 时进入 preview，仍能演示载荷。

---

## 4. 价值主张（对领导的收益）

1. **看得见**：诊断结果把「AI 可见性缺口」讲清楚。  
2. **做得动**：拓词可一键变成 GEOFlow 内容任务。  
3. **控得住**：知识库约束生成，人工审核后再发布。  
4. **算得清**：先用 DeepSeek Flash 验证链路与成本，再按需升级模型。

---

## 5. 本地演示入口（当前环境）

| 入口 | URL | 说明 |
|------|-----|------|
| 套件中枢 | http://localhost:3009/suite | 诊断→拓词→live移交→回看→事实卡→信任素材→观测 |
| 可信观测后台 | http://localhost:3009/admin/trust-obs | 一键跑探针 / 看样本 / 导出 |
| L3 样板 | http://localhost:3009/pilot-demo/geo-demo-column/trust-asset.html | 模型可读图文 |
| GEORank 首页 | http://localhost:3009/ | 诊断 / 拓词入口 |
| GEOFlow 后台 | http://localhost:18080/geo_admin | 知识库、文章、AI 模型、任务 |
| GEOFlow 登录 | http://localhost:18080/geo_admin/login | 账号见本机 `.env`：`GEOFLOW_ADMIN_USERNAME` / `GEOFLOW_ADMIN_PASSWORD` |

启动脚本（GEORank 仓库根目录）：

```powershell
.\scripts\start-geo-suite.ps1
```

GEOFlow 单独启动（GEOFlow 仓库）：

```powershell
docker compose up -d
```

---

## 6. 建议演示剧本（约 10–15 分钟）

### 开场 60 秒

「以前优化的是搜索排名；现在用户直接问 AI。我们做的是内容工程：先被找到，再被引用，终被信任——并用可审计抽样证明有没有变好。」

### 步骤

| 步 | 操作 | 话术要点 |
|----|------|----------|
| 1 | 打开 `/suite` | 统一工作台；合成栏目「GEO 示范栏目」 |
| 2 | 诊断页 | 看就绪信号；强调「外链背书 ≠ AI 答案引用率」 |
| 3 | 拓词 | 形成可移交选题 |
| 4 | 「发送到 GEOFlow」 | **必须 live**（已配 Token）；preview 不算验收通过 |
| 5 | `/suite?step=review` | 看 mode=live、任务状态、发布回调 |
| 6 | `/suite?step=knowledge` | 事实卡覆盖率 / 向量化率看板 |
| 7 | `/suite?step=trust_asset` | L3 图文样板（人共鸣 + 模型可读，非视频管线） |
| 8 | `/admin/trust-obs` 跑一轮 → `/suite?step=measure` | API 自动采样徽章；mention/citation/absent |

### Live handoff 验收清单（L1）

1. 后台「系统设置 → GEO Suite」已填 `base_url` + API Token（或 `.env` 的 `GEOFLOW_API_TOKEN`）  
2. GEOFlow 已有可用 **content 提示词** + **chat 模型**（catalog `/api/v1/catalog` 能列出）  
3. 拓词页点移交后，Suite 最近移交显示 `mode=live`（不是 preview）  
4. 可 SSO/深链打开 Flow 任务；「刷新任务状态」有返回  
5. 若 Flow 发布回调已配，回看区可见最近回调事件  

**预览限制**：未配 Token 时 `mode=preview`，仍可演示载荷与步骤故事线，但 **不算 L1 验收通过**。Suite 顶栏会明确标出 preview / live。  

### 收尾 30 秒

「生产半程已通；测量用单一 API 探针原型说话，不做多模型网页抓取、不把爬虫 PV 叫引用率。」

---

## 7. 当前演示数据（已预置）

### 7.1 LLM

| 位置 | 配置 |
|------|------|
| GEOFlow | 后台 AI 模型：`DeepSeek V4 Flash`（`deepseek-v4-flash`） |
| GEORank | `.env`：`LLM_BASE_URL=https://api.deepseek.com/v1`，`LLM_MODEL=deepseek-v4-flash` |

说明：先用 **Flash** 验证速度与成本；需要更高质量时可升级 `deepseek-v4-pro`。  
联调验证：DeepSeek `deepseek-v4-flash` 已返回正常补全（示例回复 `OK`）。

### 7.2 知识库（GEOFlow → 素材 / 知识库）

1. KB1 · GEO 概述  
2. KB2 · GEO 落地清单  
3. KB3 · 行业信号摘录（公开报道要点，非全文转载）  
4. KB4 · GEO Suite 事实卡  
5. **KB · 中文产品演示包·DJI Mini 5 Pro（推荐）**（真实公开消费电子规格事实卡；资产见 [`pilot-demo/cn-product-demo-v2/`](./pilot-demo/cn-product-demo-v2/README.md)；详情 http://localhost:18080/geo_admin/knowledge-bases/9/detail ）  
6. ~~KB · 中文产品演示包·飞书多维表格~~（**已不推荐**；旧资产 [`pilot-demo/cn-product-demo/`](./pilot-demo/cn-product-demo/README.md)）

本地原文备份：`GEOFlow/storage/app/demo-kb/`；中文产品包 v2 导入：`.\scripts\import-cn-product-demo-v2-kb.ps1` 或 `cn-product-demo-v2/import-to-geoflow.md`。  
Suite 演示：任务中心绑定 **DJI Mini 5 Pro** KB + 使用 `cn-product-demo-v2/prompts/library.md` 中 P01/P06；探针题见 `probe-questions.md`；看板 JSON：`/pilot-demo/cn-product-demo-v2/metrics.json`。

### 7.3 文章（已发布）

1. 什么是 GEO？给业务负责人的五分钟读懂  
2. 从 SEO 到 GEO：品牌如何进入 AI 回答  
3. 用知识库驱动内容生产的 GEO 闭环  
4. GEO Suite 演示：诊断到分发一条链  

另有：演示关键词库、演示标题库、分类「GEO 方法论」。

查看路径：

- 知识库：http://localhost:18080/geo_admin/knowledge-bases  
- 文章：http://localhost:18080/geo_admin/articles  
- AI 模型：http://localhost:18080/geo_admin/ai-models  

---

## 8. 技术边界与风险（主动说清楚）

| 项 | 现状 |
|----|------|
| 集成深度 | 薄集成半成品：handoff + 配置 + Suite 导航 |
| 未做 | company↔site 强绑定；Flow 发布 URL 自动回写 Rank |
| 运行形态 | 两套 Docker / 进程，两套数据库 |
| 密钥 | 仅本机 `.env` / 后台加密存储；**勿提交 Git，勿写进汇报附件** |
| 性能 | GEOFlow 开发模式 `artisan serve` 首次请求偏慢，属演示环境正常现象 |

---

## 9. 投入与路线建议（可直接贴进 PPT）

### 已验证

- 本地双系统可启动  
- Suite 工作流可演示  
- DeepSeek Flash 可连通  
- 演示知识库 + 文章已就位  

### 建议下一阶段（2–4 周量级，视人力）

1. **Live 全链路验收**：配置 GEOFlow API Token → Rank 一键建真实任务  
2. **客户级知识库模板**：行业包 + 产品事实卡标准  
3. **回写闭环**：发布 URL / llms.txt → Rank 再诊断对比  
4. **权限与多租户**：按组织隔离素材与任务  

### 资源诉求（示例口径）

- 1 名全栈负责集成与演示稳定性  
- 1 名内容/运营准备行业知识库  
- DeepSeek（或等价）API 预算按调用量评估  

---

## 10. FAQ（领导常问）

**Q：这是不是又一个 CMS？**  
A：不是。核心是「AI 可见性诊断 + 受知识库约束的内容生产」，CMS 只是分发载体之一。

**Q：为什么不合并成一个系统？**  
A：技术栈正交（FastAPI vs Laravel），硬合并成本高、回报低；产品层统一入口即可。

**Q：效果怎么量化？**  
A：短期看任务完成率、知识库覆盖、发布量；中期需独立的「答案面板」抽样（提及/引用等），不能把页面诊断分或 AI 爬虫 PV 当成引用率。产品规划见 [GEO 可信仪表盘](./superpowers/specs/2026-07-22-geo-trust-dashboard-product.md)。

**Q：数据安全？**  
A：密钥服务端保管；演示环境本地；生产需按等保/客户要求做网络隔离与审计。

---

## 11. 附录：相关文档

| 文档 | 用途 |
|------|------|
| [geo-suite.md](./geo-suite.md) | 集成契约与 API |
| [本地部署操作手册.md](./本地部署操作手册.md) | 逐步部署 |
| [README.md](./README.md) | 文档总入口 |

---

## 12. 演示检查清单（开讲前 2 分钟）

- [ ] http://localhost:3009/suite 可打开  
- [ ] http://localhost:18080/geo_admin/login 可打开  
- [ ] GEOFlow AI 模型页存在 DeepSeek V4 Flash  
- [ ] 知识库 ≥ 4 条、文章 ≥ 4 篇  
- [ ] 勿在屏幕共享中展示完整 API Key  

---

## 13. 排障：GEOFlow 出现 `419 Page Expired`

这是 Laravel **CSRF / Session Cookie 主机不一致**，不是系统坏了。

**原因**：同一会话里混用了 `http://localhost:18080` 与 `http://127.0.0.1:18080`（Cookie 不互通）。

**正确做法**：

1. 地址栏只使用：`http://localhost:18080/geo_admin/login`（与 `.env` 的 `APP_URL` 一致）  
2. 清掉该站点 Cookie，或用无痕窗口重新打开  
3. **先刷新登录页**再点登录（不要用旧标签页里过期的表单）  
4. 不要从 `127.0.0.1` 跳到 `localhost` 再提交表单  

本地已验证：同一主机登录 → 302 进后台；跨主机提交 → 固定 419。 
