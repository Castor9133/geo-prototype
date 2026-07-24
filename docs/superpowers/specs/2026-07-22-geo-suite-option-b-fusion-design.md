# GEO Suite Option B：加深融合设计与实施计划

> 状态：Phase 1/2 已实施（待联调验收）  
> 日期：2026-07-22  
> 范围：在现有薄集成之上，做成「看起来、用起来像一个产品」的加深融合  
> 非范围：FastAPI / Laravel 代码大一统（Option C）
> 同域策略：采用 **SSO 跨端口 + 强制 localhost**（比 `/flow/` 子路径更稳，已避开 419）

---

## 1. 目标与成功标准

### 产品目标

用户感知为 **一个 GEO Suite 产品**：

1. **一个入口**：浏览器主要只记一个地址（Rank 前台 / Suite）。  
2. **一次登录**：在 Rank 已登录的管理员，进入 Flow 后台不再二次输密（或一键换票）。  
3. **一条链路**：诊断 → 方案 → 拓词 → live 移交 → 任务深链 → 发布回写 → 再诊断回看。  
4. **两边仍独立运行**：两套进程、两套 DB，契约集成，不硬合并代码栈。

### 验收标准（DoD）

| ID | 验收项 | 通过标准 |
|----|--------|----------|
| A1 | 一键启动 | `start-geo-suite.ps1` 同时拉起 Rank+Flow；缺 GEOFlow 目录则明确失败 |
| A2 | 同域可达 | 经 Suite 网关访问 Flow 管理端，不混用 `localhost`/`127.0.0.1` 导致 419 |
| A3 | SSO 桥 | Rank 管理员会话 → 打开 Flow 时已登录（或 ≤1 次确认） |
| A4 | Live handoff | 配好 Token 后，拓词/问答一键创建 Flow 任务，并跳到 `/tasks/{id}` |
| A5 | 任务状态 | Suite「回看」能显示最近任务状态（至少：created / running / done） |
| A6 | company 绑定 | handoff 携带 Rank `company_id` ↔ Flow 侧可检索关联（site 或 metadata） |
| A7 | 发布回写 | Flow 文章 publish 后回调 Rank；Suite 回看可展示 published URL；可选触发再诊断 |
| A8 | 文档 | 更新 `geo-suite.md` + 领导手册；演示剧本改为「一体产品」口径 |

### 明确不做

- 合并成单一 Laravel 或单一 FastAPI 单体  
- 共享同一 Postgres  
- 浏览器直连 GEOFlow API Key  
- 第一期做完整 OIDC/SAML 企业 IdP（先做签名 ticket 桥）

---

## 2. 目标架构

```text
浏览器
  │
  ▼
┌─────────────────────────────────────────────┐
│  GEO Suite 入口（GEORank 前台 :3009）         │
│  /suite  ·  /diagnostic · /solutions · …    │
│  /flow/*  ──反向代理──► GEOFlow (:18080)     │  ← B1 同域网关
└─────────────────────────────────────────────┘
  │ JWT / Session（Rank）
  │ SSO ticket（短时签名）                        ← B2
  ▼
GEORank API                          GEOFlow API / Admin
  · handoff 代理                         · tasks / materials / articles
  · callback 接收                        · webhook 出站               ← B3
  · company 映射表                       · metadata / site 绑定       ← B4
```

原则：

- **产品层统一，运行时双引擎**  
- **密钥与 Token 只在服务端**  
- **同域优先**，避免 Cookie/CSRF 主机分裂（已踩过 419）

---

## 3. 工作包与排期

建议顺序：

```text
Wave 0  编排硬化 B7
Wave 1  同域网关 B1  →  SSO 桥 B2  →  深链/状态 B5
Wave 2  company 绑定 B4  →  发布回写 B3
Wave 3  统一壳导航 B6  + 文档/演示 A8
```

| Wave | 包 | 内容 | 估时 | 依赖 |
|------|----|------|------|------|
| 0 | **B7 编排硬化** | 单一 suite env；双 compose 网络/健康检查；GEOFlow 缺失则失败；统一打印入口 URL（只用 `localhost`） | S（1–2 天） | — |
| 1 | **B1 同域网关** | Nginx/Traefik 把 `/flow/` 反代到 GEOFlow；配置 `APP_URL`、静态资源前缀或子路径方案；文档强制单一主机名 | M（3–5 天） | B7 |
| 1 | **B2 SSO 登录桥** | Rank 签发 HMAC/JWT ticket（TTL≤60s）→ Flow `/geo_admin/sso/consume` 建 admin session；用户映射：邮箱或配置表 `rank_user_id↔flow_admin_id` | L（5–8 天） | B1 |
| 1 | **B5 深链+状态** | handoff 返回 task 深链；Suite 轮询 `GET /api/v1/tasks/{id}`；scope 加 `tasks:read` | S–M（2–3 天） | live Token |
| 2 | **B4 绑定** | 设置页维护 company↔site/KB；handoff payload 带 `external_company_id`；Flow task/KB metadata 可查 | M（3–4 天） | B5 |
| 2 | **B3 回写** | Flow publish webhook → Rank `POST /api/integrations/geoflow/callback`（签名校验）→ 存 URL + 可选再诊断；Suite review 读服务端 | L（5–7 天） | B4 |
| 3 | **B6 壳** | Suite 顶栏「生产台」；Flow header「回 Suite」；可选 iframe（需 Frame 策略配合） | M（3–4 天） | B1+B2 |
| 3 | **A8 文档** | 更新契约、领导手册、演示剧本 | S（1 天） | 功能就绪 |

**全量 Option B（一人全栈）**：约 **4–6 周**。  
**最小「像一套产品」切片（Wave 0+1）**：约 **2–3 周**（B7+B1+B2+B5）。

---

## 4. 关键设计细节

### 4.1 B1 同域网关（推荐路径前缀）

- 对外：`http://localhost:3009/flow/` → 上游 `http://geoflow-app:8080/` 或 `host.docker.internal:18080`  
- 风险：Laravel `APP_URL`、asset URL、`ADMIN_BASE_PATH` 对子路径敏感  
- **备选（若子路径摩擦大）**：`http://flow.localhost:3009` 或固定 `http://localhost:18080` 但 **全局禁止 127.0.0.1**，并在 Suite 用 SSO 跳转（体验略弱于真同域）

决策点（实施前确认）：**优先尝试子路径 `/flow/`；若 2 天内卡死资源路径，则降级为「单主机名 + SSO 跨端口」**。

### 4.2 B2 SSO ticket 协议（草案）

```http
GET /flow/geo_admin/sso/consume?ticket=...
```

Ticket payload（签名后）：

```json
{
  "iss": "georank",
  "aud": "geoflow",
  "exp": 1710000060,
  "rank_user_id": "uuid",
  "email": "admin@example.com",
  "role": "admin"
}
```

- 签名：`HMAC-SHA256`，共享密钥 `GEOSUITE_SSO_SECRET`（两边 `.env`）  
- Flow：校验 → 映射/创建 admin → `Auth::guard('admin')->login` → 302 dashboard  
- 安全：一次性 nonce（Redis）、短 TTL、仅 HTTPS/本地、审计日志  

### 4.3 B3 回写回调（草案）

```http
POST /api/integrations/geoflow/callback
X-GeoSuite-Signature: sha256=...
{
  "event": "article.published",
  "task_id": 123,
  "article_id": 456,
  "public_url": "https://...",
  "external_company_id": "...",
  "occurred_at": "..."
}
```

Rank：验签 → 写入 `geoflow_events`（或现有表扩展）→ Suite review API → 可选 enqueue 再诊断。

### 4.4 仓结构

- **保持双仓**：`GEORank` + `GEOFlow`  
- Suite 编排与文档以 **GEORank 为产品壳主仓**  
- 不引入强制 git submodule（可选后续 meta-repo）

---

## 5. 风险与缓解

| 风险 | 缓解 |
|------|------|
| Laravel 子路径/静态资源 | 先 spike 1–2 天；失败则改「单主机名+跨端口 SSO」 |
| 419 CSRF 主机不一致 | 文档与脚本只输出 `localhost`；禁止混用 127.0.0.1 |
| 用户模型不对齐 | 映射表 + 首期仅支持管理员角色 |
| Webhook 丢消息 | 签名 + 幂等键 + 重试；Suite 可手动「同步状态」 |
| 范围膨胀 | Wave 1 先交付「像一个产品」；Wave 2 再闭环 |

---

## 6. 建议的第一期交付（请批准）

**Phase 1（Wave 0 + Wave 1）—— 先做完再开 Wave 2**

1. B7 编排硬化  
2. B1 同域（或降级方案）  
3. B2 SSO 桥  
4. B5 任务深链与 Suite 状态  

交付后演示口径变为：「打开 Suite → 登录一次 → 拓词移交 → 直接进 Flow 任务详情 → Suite 回看状态」。

---

## 7. 批准清单

请回复确认：

- [ ] 同意 **Option B / Phase 1** 范围（B7+B1+B2+B5）  
- [ ] 同域策略偏好：**子路径 `/flow/`** 还是 **先 SSO 跨端口（更稳）**  
- [ ] 是否允许改 **GEOFlow 仓库代码**（SSO consume、webhook 出站）——加深融合必需  

批准后进入实施：按 Wave 0 → 1 逐包落地，每包可演示验收。
