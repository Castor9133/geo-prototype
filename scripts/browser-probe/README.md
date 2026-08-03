# GEOrank browser-probe

半自动「约定账号」网页端点名抽样。结果写入本仓 **real-obs** API，与 Admin `trust_obs`（API 探针）分轨。

## 口径

- 这是**固定账号 + 人工过验证码**的点名抽样，**不是**全网引用率，也**不是**模型内部检索台账。
- 强采纳（服务端判定）：本品提及 **且** 引用/外链命中自有域或指定事实源。

## 准备

1. 本地 API 已启动（例如 `http://127.0.0.1:8010`）。
2. Suite 上对某个 `geo_run` 创建真实点名快照（「内容已外发，开始点名」），记下 `run_id` 与 `snapshot_id`。
3. （可选）安装 Playwright：

```text
backend\.venv\Scripts\python.exe -m pip install playwright
backend\.venv\Scripts\python.exe -m playwright install chromium
```

登录态默认写在 `%USERPROFILE%\.georank-browser-probe\{platform}.json`，**勿提交 Git**。

## 用法

```text
# 只查看任务
backend\.venv\Scripts\python.exe scripts\browser-probe\run_probe.py --api http://127.0.0.1:8010 --run-id <RUN> --snapshot-id <SNAP> --dry-job

# 有头浏览器半自动（推荐）
backend\.venv\Scripts\python.exe scripts\browser-probe\run_probe.py --api http://127.0.0.1:8010 --run-id <RUN> --snapshot-id <SNAP> --mode playwright

# 纯粘贴答案（无浏览器）
backend\.venv\Scripts\python.exe scripts\browser-probe\run_probe.py --api http://127.0.0.1:8010 --run-id <RUN> --snapshot-id <SNAP> --mode manual

# 只跑一个平台
... --platform doubao
```

平台键：`doubao` | `yuanbao` | `deepseek`。

## 流程

1. CLI 拉取快照 job 并 `start`。
2. 按单元打开对应网页；你登录、发问、等答完。
3. 回终端按 Enter；脚本抽取可见文本与链接，POST 回 `/api/geo-runs/{id}/real-obs/snapshots/{sid}/samples`。
4. 在 Suite「真实点名」里看提及 / 自有源 / 强采纳，必要时人工改标。
