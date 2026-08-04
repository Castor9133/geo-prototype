# README

> 来源：docs/pilot-demo/cn-product-demo-ec/README.md
> doc_type：功能说明

# 中文产品演示包·电子消费品 · HUAWEI FreeBuds Pro 4

真实公开消费电子产品资料包，用于 GEO Suite / GEOFlow 知识库与受约束内容演示。

| 项 | 说明 |
|----|------|
| 产品 | **HUAWEI FreeBuds Pro 4** — 华为悦彰（HUAWEI SOUND）品牌 TWS 真无线降噪耳机 |
| 品类 | 电子消费品（TWS 耳机），与 DJI Mini 5 Pro（无人机/智能硬件）形成品类互补 |
| 为何选用 | ① 品类不同于 DJI 无人机，可验证跨品类知识库切换能力；② 官方参数页规格齐全（重量/驱动/ANC/编码/续航/充电均可量化）；③ 场景覆盖通勤/运动/办公/旅行，素材丰富；④ 有明确的上代对比（vs FreeBuds Pro 3）；⑤ 含合规限制（IP54/充电盒不防水），适合「参数+场景+边界」演示 |
| 口径 | 全部事实来自华为公开产品页 / 技术参数 / FAQ；**非华为官方合作素材**；不编造未公布参数 |
| 生效日期 | 2026-07-30（演示时若官方改动请回源核对） |

## 目录结构

| 路径 | 用途 |
|------|------|
| `fact-cards/*.md` | L2 事实卡（12 条，拆分版） |
| `fact-cards.md` | 合并正文，便于导入 GEOFlow |
| `prompts/library.md` | 收紧到本产品的中文提示词（10 条） |
| `probe-questions.md` | 参数 / 场景 / 对比探针题（13 道） |
| `metrics.json` | Suite「事实卡」看板数据 |
| `content-articles/*.md` | 基于事实卡的内容文章（5 篇） |
| `import-to-geoflow.md` | 导入与向量化步骤 |
| `kb-name.json` | KB 名称标识 |
| [../../content-engineering-sop.md](../../content-engineering-sop.md) | 内容工程 SOP |

运行时副本：`/pilot-demo/cn-product-demo-ec/metrics.json`。

## 主要公开来源

1. [产品介绍页](https://consumer.huawei.com/cn/headphones/freebuds-pro-4/) — 定位、卖点、场景表述  
2. [技术参数](https://consumer.huawei.com/cn/headphones/freebuds-pro-4/specs/) — 重量、驱动、ANC、编码、续航、充电等全表  
3. [FAQ / 百科页面](https://consumer.huawei.com/cn/headphones/freebuds-pro-4/) — vs FreeBuds Pro 3、防水说明、兼容性说明

## 与 DJI 演示包的关系

本包（`cn-product-demo-ec`）与 DJI Mini 5 Pro 包（`../cn-product-demo-v2/`）为**平行演示包**，用于演示：

- **跨品类知识库切换**：从无人机（智能硬件）到 TWS 耳机（电子消费品）
- **统一事实卡体系**：两个包共用同一套内容工程流水线（模板、SOP、导入脚本）
- **对比验证**：不同品类的 metric 跨包汇总、探针题对照

| 资产 | 状态 |
|------|------|
| [`../cn-product-demo-v2/`](../cn-product-demo-v2/README.md)（DJI Mini 5 Pro） | 无人机/智能硬件演示包 |
| **本包** | **电子消费品演示包（当前推荐作为第二套 KB）** |
| [`../cn-product-demo/`](../cn-product-demo/README.md)（飞书多维表格） | 已不推荐（deprecated） |

## 快速使用

1. **看事实卡**：`fact-cards.md` 或 `fact-cards/`  
2. **导入 Flow**：[`import-to-geoflow.md`](./import-to-geoflow.md)；KB 名：`中文产品演示包·HUAWEI FreeBuds Pro 4`  
3. **脚本**：仓库根执行 `.\scripts\import-cn-product-demo-ec-kb.ps1`  
4. **Suite**：绑定该 KB；提示词用 `prompts/library.md`；探针见 `probe-questions.md`  
5. **走查**：[`content-engineering-sop.md`](../../content-engineering-sop.md)

## 口径声明

1. 本包所有事实均来自 HUAWEI 官网公开页面（产品页 / 技术参数 / FAQ），**并非与华为的官方合作素材**，亦未获得华为授权或背书。  
2. 参数数字以华为官方技术参数页为准；若官方页面更新，本包应回写核对。  
3. 本包仅作为 GEO Suite 演示用途，不代表任何商业推广或评测结论。  
4. 对比表述（如 vs FreeBuds Pro 3）仅转述官方公开表述，不编造第三方评测分数或排名。  
5. 禁止在任何基于本包生成的内容中使用「保证大模型推荐」「保证上榜」「第一名」等无法证实的断言。
