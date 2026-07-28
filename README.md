# GEOrank

**GEOrank** 是面向 **GEO / 内容工程** 的开源工作台（**GEO Suite**）：把「诊断 → 知识库 → 拓词 → 分发 → 观测 → 配置」收束到同一条主路径。  
它不是旧版「问答 / 方案生成站」，也不是公司库或专家频道门户。

本地主入口：`http://localhost:3009/suite`

---

## 六大能力

| # | 能力 | 说明 |
|---|---|---|
| 1 | **网站 SEO/GEO 诊断排查** | Schema、Meta、结构与内容就绪信号；用于发现问题，**不是** AI 答案「引用率」 |
| 2 | **内容切片 · 向量化 · 知识库** | Rank 原生内容引擎（JSONB embedding）；演示包：**DJI Mini 5 Pro** |
| 3 | **GEO 拓词 / 提示词扩词** | 从业务词扩展问题词、场景词与提示词资产 |
| 4 | **多渠道分发** | 任务草稿 + 渠道/模板 key（M1 薄实现）；Laravel GEOFlow 仅对照可选 |
| 5 | **可信观测** | **API 采样**探针（提及/引用等可审计样本）；**≠** 网页抓取 |
| 6 | **配置页** | Suite / API / 内容后端模式与模块开关 |

**Suite 路径**：诊断 → 知识库 → 拓词 → 分发 → 观测  

**已下线产品面**：公司目录、专家频道、教程频道、方案生成等（入口默认隐藏或重定向到 Suite）。

---

## 本地快速启动（默认：本机裸跑，不用 Docker）

1. 安装本机 **PostgreSQL** + **Redis**（见 [docs/本地裸跑-postgres-redis.md](docs/本地裸跑-postgres-redis.md)）
2. 复制 `.env.example` → `.env`，确认：

```env
POSTGRES_HOST=127.0.0.1
REDIS_HOST=127.0.0.1
CONTENT_BACKEND_MODE=native-python
PUBLIC_BASE_URL=http://localhost:3009
```

3. 一条脚本起 API + worker + 带 `/api` 反代的静态前台（**默认入口**是 `dist/` 静态站，不是 Next）：

```powershell
.\scripts\start-local.ps1
# 或
pnpm dev
# 或（默认同样走裸跑）
.\scripts\start-geo-suite.ps1
```

`pnpm dev:web` / `pnpm dev:admin`（Next）为 **legacy** 对照，演示主路径请用上面的裸跑。

| 服务 | 地址 |
|---|---|
| 前台（含 /api 反代） | http://localhost:3009/ |
| **GEO Suite** | http://localhost:3009/suite |
| API | http://localhost:8000/api/health |
| 内容引擎 Admin | http://localhost:3009/admin/content-engine |

内容引擎需要**管理员登录**。未登录访问会跳到 `/admin/?returnUrl=…`，登录成功后回跳。种子管理员默认邮箱 `admin@georank.com`，密码见 seed / `GEORANK_SEED_ADMIN_PASSWORD`（或本机未跟踪的 `.local-admin-password.txt`）。

验收清单：[docs/m1-acceptance-checklist.md](docs/m1-acceptance-checklist.md)

### Legacy：Docker Compose / GEOFlow

仅在需要对照 Laravel GEOFlow 时使用：

```powershell
.\scripts\start-geo-suite.ps1 -UseCompose              # 仅 Rank Compose
.\scripts\start-geo-suite.ps1 -UseCompose -WithGeoFlow  # Rank + Flow
```

并设置 `CONTENT_BACKEND_MODE=legacy-flow`。**演示默认不再需要 GEOFlow 容器。**

完整 Compose 说明仍见 [docs/本地部署操作手册.md](docs/本地部署操作手册.md)。首次请复制 `.env.example` → `.env`，自行配置模型 API，**勿提交 `.env`**。

---

## 仓库结构

```text
GEOrank/
  backend/               # FastAPI · Celery · SQLAlchemy · 内容引擎
  dist/                  # 主体验：3009 静态前台（含 /suite）
  docs/                  # 文档与演示包
  scripts/               # start-local.ps1 / serve-local-proxy.py 等
```

- **GEORank（默认）**：诊断、知识库、拓词、任务草稿、薄分发、可信观测、Suite。
- **GEOFlow（可选对照）**：Laravel 多渠道生产；独立工程，仅 `legacy-flow` 联调。

技术栈：静态前台（3009）+ FastAPI（8000）+ 本机 Postgres/Redis；Compose / GEOFlow 为 legacy。

---

## 文档与演示包

总入口：**[docs/README.md](docs/README.md)**

| 文档 | 用途 |
|---|---|
| [docs/本地裸跑-postgres-redis.md](docs/本地裸跑-postgres-redis.md) | **默认**：本机 PG/Redis + start-local |
| [docs/m1-acceptance-checklist.md](docs/m1-acceptance-checklist.md) | M1 验收门禁 |
| [docs/content-engineering-sop.md](docs/content-engineering-sop.md) | 内容工程 SOP |
| [docs/geo-suite.md](docs/geo-suite.md) | Suite 与双轨模式说明 |
| [docs/pilot-demo/cn-product-demo-v2/](docs/pilot-demo/cn-product-demo-v2/) | **推荐演示包**：DJI Mini 5 Pro |

领导汇报走查见 [docs/GEO-Suite-leadership-demo-guide.md](docs/GEO-Suite-leadership-demo-guide.md)。

---

## 口径注意

| 说法 | 正确理解 |
|---|---|
| 诊断「citation / 背书就绪」 | 页面外链与结构就绪信号，**不是** AI 答案引用率 |
| 可信观测 | 对答案引擎做 **API 采样**，可审计；不是整站爬取 |
| 爬虫 PV / 页面分 | 代理指标，**不得**改称为「引用率」 |

软件不保证任何模型一定提及或推荐某个品牌。

---

## License

软件代码采用 **Apache-2.0**。内置首页等内容的额外权利边界见 [DATA_LICENSE.md](DATA_LICENSE.md)。
