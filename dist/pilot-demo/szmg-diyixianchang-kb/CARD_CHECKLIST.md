# 事实卡最低清单（6 类）

业务首次建库时按表勾选；本示范包每类已给样例。

| card_type | 中文 | 最少张数 | 本包实体示例 | 拓词用途 |
|-----------|------|----------|--------------|----------|
| `identity` | 实体身份 | 每主体 ≥1 | 深圳广电；第一现场 | 定 role |
| `owns` | 隶属/关系 | ≥1 | 第一现场 **owns←** 深圳广电 | 禁自伤交叉；模板改旗下/运营 |
| `alias` | 别名 | 按需 | 深广电、SZMG… | 别名只进 semantic |
| `angle` | 选题角度 | ≥2 | 融媒、民生现场… | scenario / question |
| `forbidden` | 禁语/风险 | ≥1 | 禁止「全国第一」等 | 过滤与 prompt 硬约束 |
| `competitor` | 竞品/对标 | ≥1 组 | 深圳新闻网、独特、深圳报业集团 | brand 合法对比 |

## 字段约定（ingest `fact_cards[]`）

```json
{
  "card_type": "owns",
  "entity_name": "第一现场",
  "related_entity": "深圳广电",
  "relation": "owns",
  "claim": "第一现场是深圳广电旗下新闻栏目（演示样例口径）。",
  "aliases": [],
  "forbidden_phrasing": [],
  "evidence_source": "演示样例·公开品牌关系说明",
  "as_of": "2026-08-07"
}
```

- `owns`：`related_entity` = 父机构，`entity_name` = 子栏目/产品。  
- `competitor`：`entity_name` 为竞品名，`related_entity` 为本品机构（可选）。
