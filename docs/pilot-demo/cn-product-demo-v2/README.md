# 中文产品演示包 v2 · DJI Mini 5 Pro

真实公开消费电子产品资料包，用于 GEO Suite / GEOFlow 知识库与受约束内容演示。

| 项 | 说明 |
|----|------|
| 产品 | **DJI Mini 5 Pro** — 大疆一英寸大底全能迷你航拍机 |
| 为何选用（相对飞书多维表格） | 官方 **技术参数页极全**（重量/尺寸/续航/相机/图传/避障数字可量化）；有清晰 **旅行/夜景/运动跟随** 场景；FAQ 含对比与限制；实体产品感强，适合事实卡与参数探针题 |
| 为何胜过讯飞录音笔 S6 | S6 参数表完整但偏硬件清单；Mini 5 Pro 额外有场景文案、相对上代对比、图传/避障条件脚注，更适合 GEO「参数+场景+边界」演示 |
| 口径 | 全部事实来自大疆官网公开页；**非官方合作素材**；不编造未公布参数 |
| 生效日期 | 2026-07-27（演示时若官方改动请回源核对） |

## 目录结构

| 路径 | 用途 |
|------|------|
| `fact-cards/*.md` | L2 事实卡（12 条） |
| `fact-cards.md` | 合并正文，便于导入 GEOFlow |
| `prompts/library.md` | 收紧到本产品的中文提示词 |
| `probe-questions.md` | 参数 / 场景 / 对比探针题 |
| `metrics.json` | Suite「事实卡」步看板 |
| `import-to-geoflow.md` | 导入与向量化步骤 |
| [../../content-engineering-sop.md](../../content-engineering-sop.md) | 内容工程 SOP |

运行时副本：[`/pilot-demo/cn-product-demo-v2/metrics.json`](../../../dist/pilot-demo/cn-product-demo-v2/metrics.json)。

## 主要公开来源

1. [产品介绍页](https://www.dji.com/cn/mini-5-pro) — 定位、卖点、场景表述  
2. [技术参数](https://www.dji.com/cn/mini-5-pro/specs) — 重量、续航、相机、图传、感知、电池等全表  
3. [常见问题 FAQ](https://www.dji.com/cn/mini-5-pro/faq) — vs Mini 4 Pro、防水、App、增强图传限制  
4. [官方商城介绍](https://store.dji.com/cn/product/dji-mini-5-pro) — 卖点交叉核对（参数仍以 specs/FAQ 为准）

## 快速使用

1. **看事实卡**：`fact-cards.md` 或 `fact-cards/`  
2. **导入 Flow**：[`import-to-geoflow.md`](./import-to-geoflow.md)；KB 名：`中文产品演示包·DJI Mini 5 Pro`  
3. **脚本**：仓库根执行 `.\scripts\import-cn-product-demo-v2-kb.ps1`  
4. **Suite**：绑定该 KB；提示词用 `prompts/library.md`；探针见 `probe-questions.md`  
5. **走查**：[`content-engineering-sop.md`](../../content-engineering-sop.md)

## 与旧包关系

| 资产 | 状态 |
|------|------|
| [`../cn-product-demo/`](../cn-product-demo/README.md)（飞书多维表格） | **已不推荐**（deprecated），仅保留对照 |
| **本包 v2** | **当前推荐演示 KB** |
| [`../geo-demo-column/`](../geo-demo-column/README.md) | 合成栏目故事线（不变） |
