# GEO 论文方法 → 提示词对照

> 供评审与 Admin「重置拓词/同步内置模板」时对照。  
> **禁止**把文中实验数字写成产品「实测引用率」。

## 主要文献

| 文献 | 要点 |
|------|------|
| Aggarwal et al., *GEO: Generative Engine Optimization* (KDD 2024 / arXiv:2311.09735) | 九种改写法；Statistics / Cite Sources / Quotation 最强；Keyword Stuffing 无效甚至有害；Fluency+Statistics 组合更优；领域差异明显 |
| GEO-SFE（结构特征工程，arXiv:2603.29979 等） | Macro/Meso/Micro：答案前置、层级清晰、可摘块、FAQ=真实检索句、实体与数字靠前 |

## 产品映射

| 论文方法 | 产品落点 | 提示词条款 |
|----------|----------|------------|
| Statistics Addition | 正文模板 + 参数/决策类 | `_GEO_METHOD_RULES`：有知识才写可核验数字，无则声明缺口 |
| Cite Sources | 全文证据口径 | `_EVIDENCE_RULES` + Cite：指向【知识】/官方口径 |
| Quotation Addition | FAQ / 摘要 / 种草证据句 | 可摘短句；不编造名人语录 |
| Fluency / Easy-to-Understand | 排版与口播/种草 | `_PLAIN_PROSE_RULES` + Fluency |
| Authoritative | 合规/限制类 | 克制权威口径，禁恐吓式承诺 |
| Keyword Stuffing（禁止） | 拓词标题门 + 全模板 | 禁堆砌、禁分号粘词、禁「XX优化/平台」空泛串 |
| 别名勿交叉 | 拓词 `_cross_seed_items` / `_seeds_are_near_duplicates` | 中英品牌名、同款别名、产品+属性近亲不做「报道/旗下/联动」交叉；真·多实体（机构×栏目）才交叉 |
| Answer-first / 可摘块（SFE） | 七段式首段、答案摘要块 | `_GEO_STRUCTURE_RULES`：首段 40–150 字自洽 |
| 标题 = 第一关 | 拓词 `question` 维 + `platform_title_hints` | `_GEO_TITLE_GATE` / `is_geo_title_acceptable` |

## 代码锚点

- 共享块：`backend/app/services/geo_prompt_rules.py`
- 内容 10 套：`backend/app/services/content_engine_utils.py` → `CHINA_PROMPTS`
- 拓词默认：`backend/app/services/runtime_settings.py` → `DEFAULT_KEYWORD_EXPANSION_CONFIG` + `MULTI_SEED_METHOD_ADDENDUM`
- 标题过滤：`backend/app/services/keyword_expansion.py` → `_sanitize_platform_title_hints`

## Admin 操作

- 拓词：`/admin/settings` → 拓词配置 → **重置**（加载新默认 system prompt）。多种子方法附录即使未重置也会由代码追加。
- 内容模板：内置标题随 `CHINA_PROMPTS` 在 list/restore 时同步正文。
