# 本机裸跑：Postgres + Redis（不用 Docker）

面向 Windows 开发机，配合 `scripts/start-local.ps1`。

## 1. PostgreSQL

推荐：官方安装包 [PostgreSQL 16+](https://www.postgresql.org/download/windows/)。

```powershell
# 安装后创建库与用户（按你的密码调整）
psql -U postgres -c "CREATE USER georank WITH PASSWORD 'georank';"
psql -U postgres -c "CREATE DATABASE georank OWNER georank;"
```

可选 pgvector（大规模检索更佳）。M1 默认用 JSONB 存向量，**无扩展也可跑通演示**。

若已装 pgvector：

```sql
\c georank
CREATE EXTENSION IF NOT EXISTS vector;
```

## 2. Redis

任选其一：

- [Memurai](https://www.memurai.com/)（Windows Redis 兼容）
- WSL2 内 `sudo apt install redis-server`
- 官方 Redis for Windows 社区构建

默认：`localhost:6379`。

## 3. GEORank `.env`（裸跑要点）

```env
DEBUG=true
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=georank
POSTGRES_USER=georank
POSTGRES_PASSWORD=georank
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
PUBLIC_BASE_URL=http://localhost:3009
CONTENT_BACKEND_MODE=native-python
GEOFLOW_ENABLED=false
GEORANK_ALLOW_ANONYMOUS_AI=true
```

LLM / Embedding Key 按现有字段配置（`LLM_*` / `EMBEDDING_*`）。无 Embedding Key 时切片仍会用本地哈希向量降级，保证演示可跑。

## 4. 启动

```powershell
cd "C:\Cursor local\GEORank"
.\scripts\start-local.ps1
# 或
pnpm dev
```

Windows 若未安装系统级 Postgres/Redis，`start-local.ps1` 会调用：

- `scripts/_bootstrap_runtime_deps.py`（便携 Redis → `~/.georank-runtime/redis`）
- `scripts/start-local-deps.py`（将 `pgembed` 拷到 `C:\georank-runtime\pgsql` 后起库，避开中文路径问题）

仍可按上文手动安装官方 PostgreSQL / Redis / Memurai。

| 服务 | URL |
|------|-----|
| 前台 | http://localhost:3009/ |
| Suite | http://localhost:3009/suite |
| API | http://localhost:8000/api/health |
| 内容引擎 Admin | http://localhost:3009/admin/content-engine |

## 5. 与 Docker 的关系

- **默认演示路径**：本手册 + `start-local.ps1`
- Compose（`start-geo-suite.ps1`）降级为 **legacy**，仅在需要对照 Laravel GEOFlow（`CONTENT_BACKEND_MODE=legacy-flow`）时使用
