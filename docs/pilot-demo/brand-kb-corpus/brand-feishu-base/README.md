# README

> 来源：docs/pilot-demo/cn-product-demo/README.md
> doc_type：功能说明

# 中文产品演示包 · 飞书多维表格（Base）

> **状态：已不推荐（deprecated）**  
> 领导演示与 Suite 推荐入口请改用 **v2 · DJI Mini 5 Pro**：[`../cn-product-demo-v2/`](../cn-product-demo-v2/README.md)。  
> 本目录仅保留对照与历史导入说明。

真实公开产品资料包（旧版），曾用于 GEO Suite / GEOFlow 知识库演示。

| 项 | 说明 |
|----|------|
| 产品 | **飞书多维表格（Base）** — 字节跳动飞书旗下在线数据库 / 协作表格 |
| 为何曾选用 | 中文帮助中心有配额上限；但产品感偏「协作工具虚线」，参数不如消费电子规格表直观 |
| 口径 | 全部事实来自飞书帮助中心 / 官网公开页；**非官方合作素材** |
| 生效日期 | 2026-07-27 |
| 替代包 | [`../cn-product-demo-v2/`](../cn-product-demo-v2/README.md)（DJI Mini 5 Pro） |

## 目录结构

| 路径 | 用途 |
|------|------|
| `fact-cards/*.md` | L2 事实卡（单卡一文件，共 12 条） |
| `fact-cards.md` | 合并正文，便于粘贴进 GEOFlow 知识库 |
| `prompts/library.md` | 中文 GEO / 内容提示词词库（22 条，含答案摘要/Brief/证据原子；含来源） |
| `probe-questions.md` | 可信观测 / 验证用中文探针题 |
| `metrics.json` | Suite「事实卡」步可选用的演示指标 |
| `import-to-geoflow.md` | 导入 GEOFlow KB 与向量化步骤 |
| [../../content-engineering-sop.md](../../content-engineering-sop.md) | **内容工程 SOP**（演示走查与发布门禁） |

运行时副本（看板 JSON）：[`/pilot-demo/cn-product-demo/metrics.json`](../../../dist/pilot-demo/cn-product-demo/metrics.json)。

## 主要公开来源

1. [快速上手多维表格](https://www.feishu.cn/hc/zh-CN/articles/697278684206) — 产品定义、视图、自动化概述  
2. [多维表格常见上限](https://www.feishu.cn/hc/zh-CN/articles/485779748873) — 参数与配额（文末标注更新于 2026/03/31）  
3. [入门飞书多维表格](https://www.feishu.cn/content/article/7574713887522639055) — 场景与对比表述  
4. [一文读懂多维表格](https://www.feishu.cn/content/base) — 能力升级公开介绍  

## 快速使用（旧包）

> 新演示请改用 [`../cn-product-demo-v2/`](../cn-product-demo-v2/README.md)。

1. **看事实卡**：打开本目录 `fact-cards.md` 或 `fact-cards/`  
2. **导入 Flow（不推荐）**：见 [`import-to-geoflow.md`](./import-to-geoflow.md)；知识库名：`中文产品演示包·飞书多维表格`  
3. **推荐替代**：`.\scripts\import-cn-product-demo-v2-kb.ps1` → DJI Mini 5 Pro

## 与合成栏目的关系

| 资产 | 实体 | 用途 |
|------|------|------|
| [`../geo-demo-column/`](../geo-demo-column/README.md) | GEO 示范栏目（合成） | 领导汇报主故事线 |
| [`../cn-product-demo-v2/`](../cn-product-demo-v2/README.md) | DJI Mini 5 Pro（推荐） | 客户级真实产品内容包 |
| **本包（deprecated）** | 飞书多维表格 | 仅历史对照 |
