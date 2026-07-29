# 演示前准备（本机最小闭环）

## 现在已可打开

| 入口 | URL |
|------|-----|
| Suite | http://localhost:3009/suite |
| 诊断 | http://localhost:3009/diagnostic |
| 拓词 | http://localhost:3009/keywords |
| 知识库（前台） | http://localhost:3009/knowledge |
| 内容引擎 Admin | http://localhost:3009/admin/content-engine |
| API Health | http://localhost:8000/api/health |

## 管理员

- 邮箱 / 账号：`admin@georank.com` 或用户名 `admin`
- 密码：`Demo@2026Geo`
- 也写在仓库根目录 `.local-admin-password.txt`（勿提交）

## 你需要补的 Key（`.env`）

补完后**重启** API / worker（再跑一次 `.\scripts\start-local.ps1 -SkipMigrate`）：

```env
LLM_API_KEY=你的大模型key
LLM_BASE_URL=https://api.deepseek.com   # 或你们内网 OpenAI 兼容网关
LLM_MODEL=deepseek-chat                 # 按实际模型名改

EMBEDDING_API_KEY=你的embedding key
EMBEDDING_BASE_URL=                     # 可与 LLM 同网关，或留空走默认
EMBEDDING_MODEL=text-embedding-3-small
```

说明：

- **无 Embedding Key** 时知识库仍可用本地哈希向量（DJI 包已导入 12 文档 / 12 切片）。
- **无 LLM Key** 时：诊断（结构爬取打分）可跑；拓词 / 内容任务草稿生成会受影响。

## 建议演示顺序（5 分钟）

1. `/suite` 看五步主路径（知识库应显示已导入）
2. `/diagnostic` 输入 `https://example.com` 跑一发诊断
3. 登录 Admin → `/admin/content-engine` 看 DJI KB、检索「续航」
4. `/keywords` 拓词（需 LLM Key）
5. 内容引擎生成任务草稿（需 LLM Key）→ 标记已分发

## 启动 / 停止

```powershell
.\scripts\start-local.ps1
# 停止：按脚本打印的 PID  Stop-Process -Id ...
```
