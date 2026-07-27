# GEO Suite：GEORank × GEOFlow 加深融合（Phase 1/2）

把 **GEORank（诊断 / 拓词）** 与 **GEOFlow（内容生产 / 分发）** 连成可运营闭环。  
两边保持独立进程与数据库；Suite 做导航、SSO、handoff、回写。

设计全文：[superpowers/specs/2026-07-22-geo-suite-option-b-fusion-design.md](./superpowers/specs/2026-07-22-geo-suite-option-b-fusion-design.md)

## 产品链路

入口：`/suite`

**演示主路径（6 点）**：1. 诊断（SEO 排查）→ 2. 知识库（推荐 **DJI Mini 5 Pro / GEOFlow KB #9**，`docs/pilot-demo/cn-product-demo-v2/`）→ 3. 拓词 → 4. 分发（任务中心新建：中国生态提示词 + **绑定 KB #9** → 答案优先正文 → 渠道/模板）→ 5. 观测 → 6. 配置（`/admin/settings`）。其余入口默认隐藏。旧飞书/示范栏目包仅作对照，不作主演示。

旧长故事线（回看 / L3 样板等）已软隐藏，可通过步骤别名回落到新路径。

## 本地启动

```powershell
.\scripts\start-geo-suite.ps1
```

脚本会：

- 要求兄弟目录存在 `../GEOFlow`
- 同步 `GEOSUITE_SSO_SECRET` / 回调密钥到两边 `.env`
- 写入 `GEORANK_CALLBACK_URL`

| 服务 | URL（只用 localhost，勿用 127.0.0.1） |
|------|------|
| GEORank | http://localhost:3009/ |
| GEO Suite | http://localhost:3009/suite |
| GEOFlow | http://localhost:18080/geo_admin |

## Phase 1/2 能力

| 能力 | 说明 |
|------|------|
| SSO | `POST /api/integrations/geoflow/sso-ticket` → Flow `/geo_admin/sso/consume` |
| 任务深链 | handoff 返回 `/geo_admin/tasks/{id}/edit` |
| 任务状态 | `GET /api/integrations/geoflow/tasks/{id}` |
| company 绑定 | 设置 `default_company_id`；handoff 可传 `company_id`，写入知识库 |
| 发布回写 | Flow publish → `POST /api/integrations/geoflow/callback`（HMAC） |
| 回看 | `GET /api/integrations/geoflow/review` |

## 配置

```env
GEOFLOW_ENABLED=true
GEOFLOW_BASE_URL=http://host.docker.internal:18080
GEOFLOW_PUBLIC_BASE_URL=http://localhost:18080
GEOFLOW_API_TOKEN=你的_sanctum_token
GEOSUITE_SSO_SECRET=两边一致
GEOSUITE_CALLBACK_SECRET=两边一致
```

GEOFlow：

```env
GEOSUITE_SSO_SECRET=同上
GEOSUITE_SSO_DEFAULT_ADMIN=admin
GEORANK_CALLBACK_URL=http://host.docker.internal:8000/api/integrations/geoflow/callback
GEORANK_CALLBACK_SECRET=同上
GEOSUITE_PUBLIC_URL=http://localhost:3009
```

后台：`系统设置 → GEO Suite`

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/integrations/geoflow/status` | 公开状态 |
| GET | `/api/integrations/geoflow/review` | handoff + 回调事件 |
| POST | `/api/integrations/geoflow/handoff` | 移交 |
| POST | `/api/integrations/geoflow/sso-ticket` | 签发 SSO（需登录） |
| GET | `/api/integrations/geoflow/tasks/{id}` | 任务状态代理 |
| POST | `/api/integrations/geoflow/callback` | Flow 发布回调 |
| GET/PUT | `/api/admin/integrations/geoflow` | 后台配置 |

## 非目标

- 不合并 Laravel / FastAPI 代码栈  
- 不共享同一数据库  
- 浏览器不持有 GEOFlow API Key  
