# Docker 开发机 CPU 优化（GEOFlow / Windows）

## 现象

Docker Desktop 里常见项目名 **`geoflow-laravel`**（来自 `docker-compose.yml` 的 `name:`），CPU 偶发到 **30%+**。  
实测：空闲时各容器多在 **<1%**；但会出现两类尖峰：

1. **`schedule:work` 每分钟 tick**：`geoflow-scheduler` + `geoflow-queue` + Postgres 合计可到十余百分点；
2. **`geoflow-assets` 跑 `npm ci` + `vite build`**：单次可持续数分钟，极易把项目组 CPU 顶到截图量级（~30%+）。

## 根因（按贡献）

1. **`php artisan serve` + CLI OPcache 曾关闭**：旧 `opcache-dev.ini` 设 `opcache.enable_cli=0`，每次请求/每次 queue tick 全量编译；Windows bind mount 放大成本。
2. **常驻四件套 + 每分钟调度**：`app` + `queue(--sleep=1)` + `scheduler` + `reverb`；`geoflow:schedule-tasks` 扫库；另有 `horizon:snapshot`（本栈默认 `queue:work` 非 Horizon，已改为需 `HORIZON_SNAPSHOT_SCHEDULE=true` 才调度）。
3. **compose `up` 误触发 `assets`/`init`**：`app` 依赖二者时，任何 recreate 都可能再跑一遍前端构建。
4. **Windows 文件共享**：代码在 NTFS bind 进 Linux 容器；请继续叠加 `docker-compose.windows-perf.yml`（vendor / bootstrap cache 用 named volume）。更彻底：仓库放 WSL2 文件系统。

GEORank 空闲 CPU 通常很低；`worker -c 4` / `crawler -c 2` 有任务时才明显，演示可用 lite 降并发并关掉 crawl/cron profile。

## 立刻见效

```powershell
cd "C:\Cursor local\GEOFlow"
docker compose -f docker-compose.yml -f docker-compose.windows-perf.yml -f docker-compose.dev.lite.yml up -d --no-deps app queue
docker stop geoflow-scheduler geoflow-reverb geoflow-assets geoflow-init 2>$null
docker stats --no-stream
```

## 开发日常（推荐）

```powershell
docker compose -f docker-compose.yml -f docker-compose.windows-perf.yml -f docker-compose.dev.lite.yml up -d --no-deps postgres redis app queue
# 实时推送
docker compose -f docker-compose.yml -f docker-compose.windows-perf.yml -f docker-compose.dev.lite.yml --profile realtime up -d reverb
# 定时入队
docker compose -f docker-compose.yml -f docker-compose.windows-perf.yml -f docker-compose.dev.lite.yml --profile cron up -d scheduler
# 前端有变更才构建
docker compose -f docker-compose.yml -f docker-compose.windows-perf.yml -f docker-compose.dev.lite.yml --profile build up assets
```

Docker Desktop：Settings → Resources 限制 CPU；关掉不用的 compose 项目。

## 演示最小集

| 栈 | 服务 |
|----|------|
| GEOFlow | `postgres` `redis` `app` `queue`（无 reverb/scheduler/assets） |
| GEORank | `traefik` `frontend` `api` `worker(-c 1)` + 依赖；`--profile crawl/cron` 再开爬虫/beat |

```powershell
cd "C:\Cursor local\GEORank"
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.dev.lite.yml up -d --no-deps api worker
docker stop georank-crawler-1 georank-beat-1 2>$null
```

## 验证

```powershell
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

预期：开发空闲 **GEOFlow 合计个位数 % 以下**（常见 app+queue+redis+postgres < 2%）；有 HTTP 请求时 app 短时升高；开启 cron 后每分钟可能小尖峰，应明显低于全开 + OPcache 关 + assets 构建时的 30%+。

## 不要做的

- 不要为省 CPU 删业务功能；用 **compose profile**（`realtime` / `cron` / `build` / `full`）按需开关。
- 日常不要对 `app` 用会拉起 `assets` 的 `up`（除非加了 lite 且 assets 已 profile 化）；优先 `--no-deps`。