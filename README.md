# GEOrank

**GEOrank** 是面向 **GEO / 内容工程** 的开源工作台（**GEO Suite**）：把「诊断 → 知识库 → 拓词 → 分发 → 观测 → 配置」收束到同一条主路径。  
它不是旧版「问答 / 方案生成站」，也不是公司库或专家频道门户。

本地主入口：`http://localhost:3009/suite`

---

## 六大能力

| # | 能力 | 说明 |
|---|---|---|
| 1 | **网站 SEO/GEO 诊断排查** | Schema、Meta、结构与内容就绪信号；用于发现问题，**不是** AI 答案「引用率」 |
| 2 | **内容切片 · 向量化 · 知识库** | 事实卡 / 切片入库；演示包：**DJI Mini 5 Pro KB** |
| 3 | **GEO 拓词 / 提示词扩词** | 从业务词扩展问题词、场景词与提示词资产 |
| 4 | **多渠道分发（GEOFlow）** | 渠道 + 模板 + 提示词扩写；与 GEOFlow 联调移交与回看 |
| 5 | **可信观测** | **API 采样**探针（提及/引用等可审计样本）；**≠** 网页抓取，**≠** 诊断里的 citation/背书就绪 |
| 6 | **配置页** | Suite / API / 联调与模块开关 |

**Suite 路径**：诊断 → 知识库 → 拓词 → 分发 → 观测  

**已下线产品面**：公司目录、专家频道、教程频道、方案生成等（入口默认隐藏或重定向到 Suite）。

---

## 本地快速启动

推荐一键拉起 **GEORank + GEOFlow**（Suite 联调）：

```powershell
# 兄弟目录需存在 ..\GEOFlow（或本仓 geoflow 分支检出的 Flow 工程）
.\scripts\start-geo-suite.ps1
```

| 服务 | 常见地址 |
|---|---|
| GEORank 前台 | http://localhost:3009/ |
| **GEO Suite** | http://localhost:3009/suite |
| GEORank API | http://localhost:8000/ |
| GEOFlow | http://localhost:18080/geo_admin |

请使用 `localhost`（勿混用 `127.0.0.1`，否则 GEOFlow 可能 419）。

仅跑 GEORank（无 Flow）时，可按 [docs/本地部署操作手册.md](docs/本地部署操作手册.md) 使用 Compose / `pnpm` 常规流程。首次请复制 `.env.example` → `.env`，自行配置模型 API，**勿提交 `.env`**。

---

## 仓库结构（Rank 与 Flow）

```text
GEOrank/                 # 本仓：诊断 / Suite 前台 / 管理 / FastAPI 等
  apps/                  # Next.js 前台与管理台（迁移中）
  backend/               # FastAPI · Celery · SQLAlchemy
  dist/                  # 当前主体验：3009 静态前台（含 /suite）
  docs/                  # 文档与演示包
  scripts/               # start-geo-suite.ps1 等
```

- **GEORank**：诊断、知识库演示、拓词、可信观测、配置与 Suite 壳。
- **GEOFlow**：多渠道内容生产与分发（渠道 / 模板 / 扩写）；独立工程，与 Rank SSO / 回调联调。
- **geo-prototype**：日常推送仓。`main` 为 Rank/Suite；**GEOFlow 相关代码在 `geoflow` 分支**（勿与 `main` 产品面混淆）。

技术栈概要：静态前台（3009）+ FastAPI（8000）+ Compose（Postgres / Redis / Qdrant 等）+ 可选 GEOFlow（18080）。

---

## 文档与演示包

总入口：**[docs/README.md](docs/README.md)**

| 文档 | 用途 |
|---|---|
| [docs/content-engineering-sop.md](docs/content-engineering-sop.md) | 内容工程 SOP（双层方法 → Suite 六能力） |
| [docs/geo-suite.md](docs/geo-suite.md) | Suite 联调、端口与环境变量 |
| [docs/pilot-demo/cn-product-demo-v2/](docs/pilot-demo/cn-product-demo-v2/) | **推荐演示包**：DJI Mini 5 Pro 事实卡 / 提示词 / Flow KB |

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
