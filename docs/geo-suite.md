# GEO Suite（统一 Python / 双轨说明）

把 **诊断 → 知识库 → 拓词 → 分发 → 观测 → 配置** 收成一条 Suite 主路径。  
默认内容后端为 **GEORank Python（native-python）**；Laravel GEOFlow 仅作 F2 对照。

设计背景（历史 Option B）：[superpowers/specs/2026-07-22-geo-suite-option-b-fusion-design.md](./superpowers/specs/2026-07-22-geo-suite-option-b-fusion-design.md)

## 产品链路

入口：`/suite`

**演示主路径**：1. 诊断 → 2. 知识库（DJI Mini 5 Pro，`docs/pilot-demo/cn-product-demo-v2/`）→ 3. 拓词 → 4. 分发（内容引擎任务 + 渠道/模板 key）→ 5. 观测 → 6. 配置。

`CONTENT_BACKEND_MODE`：

| 值 | 行为 |
|---|---|
| `native-python`（默认） | Suite 知识库/分发 CTA → `/admin/content-engine`；不依赖 `:18080` |
| `legacy-flow` | Suite 仍可 handoff / 深链 GEOFlow（需 Compose + Token） |

## 本地启动（默认裸跑）

```powershell
# 先装本机 Postgres + Redis，见 本地裸跑-postgres-redis.md
.\scripts\start-local.ps1
# 等价默认：
.\scripts\start-geo-suite.ps1
```

| 服务 | URL |
|------|------|
| GEORank | http://localhost:3009/ |
| GEO Suite | http://localhost:3009/suite |
| 内容引擎 | http://localhost:3009/admin/content-engine |
| API | http://localhost:8000/api/health |

内容引擎须管理员登录；Suite CTA 会经 `/admin/?returnUrl=` 回跳。五渠道静态预览清单：`dist/data/channel-templates.json`（对照 GEOFlow theme key，无编译）。

验收：[m1-acceptance-checklist.md](./m1-acceptance-checklist.md)

## Legacy：Compose + GEOFlow

```powershell
.\scripts\start-geo-suite.ps1 -UseCompose -WithGeoFlow
```

并设置：

```env
CONTENT_BACKEND_MODE=legacy-flow
GEOFLOW_ENABLED=true
GEOFLOW_PUBLIC_BASE_URL=http://localhost:18080
GEOFLOW_API_TOKEN=你的_sanctum_token
GEOSUITE_SSO_SECRET=两边一致
```

**演示默认不再需要 GEOFlow 容器。**

## 内容引擎 API（native）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings/content-backend` | 模式开关 |
| GET | `/api/content-engine/public/demo-summary` | DJI 摘要 + 最近任务预览 |
| POST | `/api/content-engine/knowledge-bases/import-dji-demo` | 导入演示包（管理员） |
| GET/POST | `/api/content-engine/tasks` | 任务列表 / 同步生成草稿 |
| GET/POST | `/api/content-engine/channels` | 薄分发渠道 |

## GEOFlow 联调 API（仅 legacy-flow）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/integrations/geoflow/status` | 公开状态 |
| POST | `/api/integrations/geoflow/handoff` | 移交 |
| POST | `/api/integrations/geoflow/sso-ticket` | SSO |

后台：`系统设置 → GEO Suite`

## 非目标

- 不要求演示环境启动 Docker / GEOFlow
- 不像素级复刻 Laravel 管理 UI；行为等价见 M1 清单
