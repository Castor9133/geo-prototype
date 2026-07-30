# 将「中文产品演示包·HUAWEI FreeBuds Pro 4」导入 GEOFlow

## 方式 A：管理后台

1. 打开 http://localhost:18080/geo_admin （请用 `localhost`）  
2. 知识库列表：http://localhost:18080/geo_admin/knowledge-bases  
3. 新建，名称：`中文产品演示包·HUAWEI FreeBuds Pro 4`  
4. 粘贴 [`fact-cards.md`](./fact-cards.md) 全文  
5. 描述建议：`HUAWEI FreeBuds Pro 4 公开规格/FAQ 事实卡演示包；非华为官方授权`  
6. 保存后详情页点击 **更新切片 / 刷新 Embedding**  
7. 任务中心绑定该 KB 生成带证据引用的文章  

## 方式 B：脚本（推荐）

```powershell
# 在 GEORank 仓库根目录；需 geoflow-app 容器运行
.\scripts\import-cn-product-demo-ec-kb.ps1
```

脚本会创建/更新同名 KB、写入 `fact-cards.md` 并调用 `KnowledgeChunkSyncService::sync`，回写 `metrics.json`。

## 验收

| 检查项 | 期望 |
|--------|------|
| 知识库列表 | 名称含「FreeBuds Pro 4」 |
| 切片数 | > 0 |
| 向量化 | embedding 尽量全部成功 |
| Suite 看板 | `/pilot-demo/cn-product-demo-ec/metrics.json` |

## 提示词

打开 [`prompts/library.md`](./prompts/library.md)，复制 P01/P06/P03。  
对比演示加 P05；安全边界加 P08。  
平行演示包：见 [`../cn-product-demo-v2/`](../cn-product-demo-v2/README.md)（DJI Mini 5 Pro）。
