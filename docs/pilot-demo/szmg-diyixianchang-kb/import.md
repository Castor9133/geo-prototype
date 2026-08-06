# 导入本示范知识库

KB slug：`szmg-diyixianchang-demo`

## 一键（推荐）

```bash
cd backend
../backend/.venv/Scripts/python.exe ../scripts/import-szmg-diyixianchang-kb.py
```

脚本会：创建/复用知识库 → `ingest-tagged` 写入卡片文档与 L2 故事 → 打印 `knowledge_base_id`。

## 手工 API

1. `POST /api/content-engine/knowledge-bases` 创建库（name/slug 如上）。
2. 对 `ingest/*.json` 各发一次：  
   `POST /api/content-engine/knowledge-bases/{kb_id}/ingest-tagged`
3. 本包卡片文档使用 **L2 + approved**，无需 L1 确认即可进检索（便于演示）。若改为 L1，须再调 `confirm-l1`。
4. 打开 `/keywords`，下拉选择该库，种子填 `深圳广电;第一现场`，生成词包验收。

## 验收

- 响应 `knowledge_meta.cards_used` > 0、`chunks_used` ≥ 0。
- 词包中**不应**出现「深圳广电怎么报道第一现场」「联动合作」等自伤交叉。
- **应**出现「旗下/运营/定位」类，以及与竞品对照的 brand 词。
