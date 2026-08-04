# 党建党媒 GEO 知识库 · 试点导入包

对齐报告示范点与白板「第一现场官网证据库」叙事。

| 文件 | 用途 |
|------|------|
| [TAG_CONTRACT.md](./TAG_CONTRACT.md) | 收集端标签 / 回调契约 |
| [sample-ingest.json](./sample-ingest.json) | L1 样例（通新岭站点身份） |
| [sample-l2-story.json](./sample-l2-story.json) | L2 故事样例 |
| [sample-l3-koujing.json](./sample-l3-koujing.json) | L3 口径占位 |

## 快速导入（API 已启动时）

1. 取得知识库 id（或先建库 / 用现有 demo KB）。
2. 使用 admin 会话：

```text
POST /api/content-engine/knowledge-bases/{kb_id}/ingest-tagged
Content-Type: application/json
# body = sample-ingest.json
```

3. L1 再确认：`POST .../documents/{doc_id}/confirm-l1`

生成闭环见 Suite「内容/分发」面板：模板稿 → 平台稿 → 审核 → ready → 点名建议沉淀/剔除。
