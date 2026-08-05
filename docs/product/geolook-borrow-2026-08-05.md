# GeoLook 借鉴落地（2026-08-05）

从 [aigclink/geolook](https://github.com/aigclink/geolook) 借鉴「测得清 + 写得准」，落到本仓库。

## 做了什么

1. **演示总开关** `GEORANK_DEMO_METRICS`
   - 本地 `start-local.ps1` 默认 `true`：Suite 可用剧本 KPI，须标「演示」。
   - 上线（`DEBUG=false`）必须为 `false`：无真实样本显示「未测」，禁止剧本冒充。
2. **观测答题卡 CSV**：观测页可下载/上传；API 见策略 `obs-sample-sheet` 与 real-obs `sample-sheet`。
3. **样本诊断分型**：`absent` / `competitor_dominated` / `low_ranked` / `suspected_negative`。
4. **选题硬拦门**：正式模式批准/判定须≥3 条真实样本；管理员可 `force_reason` 强开。
5. **写稿红牌体检**：过审前对照事实卡+规则；红牌拦截；管理员可强开。

## 明确不做（本轮）

领导一页交付包、百度/Google 拓词、llms.txt 自动部署、分发勾选清单、完整事实卡编辑器、独立工单系统。

## 编辑怎么用 CSV

1. 打开 `/observe`，选策略 → 「先建摸底/复测快照」。
2. 「下载答题卡 CSV」→ 在 AI 网页提问后填写 → 「上传答题卡」。
3. 也可在表格里直接勾选并提交登记。

## 上线 checklist

1. `.env`：`GEORANK_DEMO_METRICS=false`
2. `DEBUG=false` 且密钥已轮换
3. `alembic upgrade head`（含 `027_real_obs_diagnosis_type`）
