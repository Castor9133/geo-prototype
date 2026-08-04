# 收集端 → GEO 知识库：标签与回调契约

本仓**不负责采集**。外系统打标签并通过初审后，调用本仓 API 入库。

## 入库

`POST /api/content-engine/knowledge-bases/{kb_id}/ingest-tagged`

```json
{
  "title": "通新岭党群服务中心·服务指南",
  "body": "……正文……",
  "tier": "L1",
  "external_approved": true,
  "external_id": "collector-doc-001",
  "source_url": "https://example.com/site/guide",
  "tags": {
    "site_id": "ft-tongxinling",
    "task_bajua": "社区民生",
    "doc_type": "服务指南",
    "trust_level": 1,
    "source_org": "党群",
    "geo_ready": true,
    "media_refs": ["第一现场"]
  },
  "fact_cards": [
    {
      "claim": "通新岭党群中心工作日 9:00-18:00 开放",
      "evidence_url": "https://example.com/site/guide",
      "bajua": "社区民生",
      "doc_type": "服务指南",
      "as_of": "2026-08-01",
      "quote_span": "开放时间……"
    }
  ]
}
```

### 必填标签

| 键 | 说明 |
|----|------|
| `site_id` | 党群站点数字身份 |
| `task_bajua` | 八抓八促：科研科创 / 产业链 / 新业态 / 社区民生 / 文化共富 / 青年人才 / 志愿服务 / 数字治理 |
| `doc_type` | 官网页 / 服务指南 / FAQ / 活动报道 / 课程 / 口径 / 企业共建 / 应急动员 |

### 库位 `tier`

| 值 | 外审 | 本仓 | 进 RAG |
|----|------|------|--------|
| L1 | 须 `external_approved` | **admin 再确认**（提交人≠确认人） | 确认后 |
| L2 | 信任外审 | 无 | approved 后 |
| L3 | 外审 + risk 语义 | 本仓 risk 可退役 | 仅负面策略 |
| L4 | — | 旁路 | **永不** |

## 审核回调

`POST /api/content-engine/knowledge-bases/{kb_id}/documents/{doc_id}/external-review`

```json
{ "review_state": "approved" }
```

`retired` 立即踢出检索。L1 在外审 approved 后进入 `pending_local`，再调：

`POST .../documents/{doc_id}/confirm-l1`

## 鉴权

使用本仓 JWT；平台 `admin` 或 `geo_role` ∈ editor/reviewer/risk。  
设置 GEO 角色：`PATCH /api/content-engine/geo/users/{user_id}/role`（仅 admin）`{"geo_role":"editor"}`。
