# import-to-geoflow

> 来源：docs/pilot-demo/cn-product-demo/import-to-geoflow.md
> doc_type：功能说明

# 将「中文产品演示包·飞书多维表格」导入 GEOFlow

## 方式 A：管理后台（推荐演示可见）

1. 打开 http://localhost:18080/geo_admin （请用 `localhost`，勿与 `127.0.0.1` 混用 Cookie）  
2. 进入 **素材 → 知识库**：http://localhost:18080/geo_admin/knowledge-bases  
3. 点击新建，名称填：`中文产品演示包·飞书多维表格`  
4. 将 [`fact-cards.md`](./fact-cards.md) 全文粘贴为 Markdown 内容（或上传同名文件）  
5. 描述建议：`公开帮助中心摘录的产品事实卡演示包；非飞书官方授权`  
6. 保存后进入详情页，点击 **更新切片 / 刷新 Embedding**  
7. 在任务中心创建生成任务并绑定该 KB，要求输出带证据引用  

## 方式 B：容器内 Artisan（本机自动化）

GEOFlow 以 Docker 服务 `geoflow-app` 运行时可执行：

```powershell
# 在 GEORank 仓库根目录
docker exec -i geoflow-app php artisan tinker --execute="<见 scripts 或 import 脚本生成的 PHP>"
```

仓库脚本：[`../../../scripts/import-cn-product-demo-kb.ps1`](../../../scripts/import-cn-product-demo-kb.ps1)  
会创建/更新同名知识库、写入 `fact-cards.md` 正文并调用 `KnowledgeChunkSyncService::sync`（默认允许 fallback 向量；若需强制真实 embedding，在详情页再点「更新切片」）。

## 验收

| 检查项 | 期望 |
|--------|------|
| 知识库列表可见 | 名称含「飞书多维表格」 |
| 切片数 | > 0 |
| 向量化 | 有 embedding 模型时尽量全部成功；否则文档注明 demo fallback |
| Suite | 可选读 `/pilot-demo/cn-product-demo/metrics.json`；或任务中心绑定本 KB 实跑 |

## 提示词词库

不必整库导入 KB；演示时打开 [`prompts/library.md`](./prompts/library.md)，复制 P17（答案摘要）/ P22（七段式）/ P03（FAQ）等到任务指令即可。  
正文也可直接选用 GEOFlow「中国生态」5 条提示词（已强化答案摘要与证据吸收）。  
总清单：[`../../content-engineering-sop.md`](../../content-engineering-sop.md)。
