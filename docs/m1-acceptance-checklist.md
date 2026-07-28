# M1 验收清单（去 Docker + 统一 Python + UI 优化）

范围：六大能力 MVP + 运营向内容引擎 + 全站 Soft Neubrutalism；Laravel GEOFlow 仅 F2 对照。

## 演示路径（推荐）

1. `.\scripts\start-local.ps1`（本机 Postgres + Redis）
2. 打开 `/admin/` 用管理员登录（演示账号见 README / seed）；若从 Suite 点「内容引擎」会带 `returnUrl` 回跳
3. `/admin/content-engine` → 导入 DJI → 检索 → 生成任务 → 五渠道预览 → 标记已分发
4. Suite 五步 CTA 均指向 Rank 原生（`native-python`）

## 功能门禁

| ID | 用例 | 通过标准 | 状态 |
|----|------|----------|------|
| A1 | 本机裸跑 | 不启动 Docker，`scripts/start-local.ps1` 起 API + worker + 反代静态前台 | [ ] |
| A2 | 后端模式 | `GET /api/settings/content-backend` 返回 `native-python` 或可切换 `legacy-flow` | [ ] |
| A3 | 知识库 CRUD | Admin 可建库、textarea / `.md|.txt` 上传、删文档/库 | [ ] |
| A4 | 切片向量化 | 文档可切片；chunk 有 embedding；检索 UI 返回相关片段 | [ ] |
| A5 | DJI 演示包 | `cn-product-demo-v2` 一键导入成功 | [ ] |
| A6 | 提示词 | 中国生态提示词可列表 / 新建 / 编辑 / 停用 | [ ] |
| A7 | 任务生成 | 绑定 KB + 提示词 → **同步**生成草稿可读（非 Celery 异步） | [ ] |
| A8 | 分发薄实现 | 五渠道壳预览 + 模板清单对照 GEOFlow theme key；可标记已分发 | [ ] |
| A9 | Suite | `native-python` 下知识库/分发/拓词 CTA 不依赖 `:18080` | [ ] |
| A10 | 观测/诊断/拓词 | 仍走现有 Rank 能力；拓词 native 指向内容引擎 | [ ] |
| A11 | 登录回跳 | 未登录打开内容引擎 → `/admin/?returnUrl=…` → 登录后回到内容引擎 | [ ] |
| A12 | 全站视觉 | 首页六能力 + Suite/诊断/拓词/登录/admin 列表手机竖屏可用 | [ ] |

## 对标 Flow 最小集（行为等价，非 UI 像素级）

- materials / 知识资产中枢 → `/admin/content-engine`（中枢）
- knowledge-bases → 同页「知识库」
- ai-prompts → 同页「提示词」
- tasks → 同页「任务」+ 渠道预览
- distribution → 同页「渠道」+ `dist/data/channel-templates.json`

## 明确不做

- 真 webhook / 外网发布
- 内容任务改 Celery 异步
- Suite 五步自动检测完成
- Laravel 主题编译管线 / 全表迁移 / 生产 K8s
