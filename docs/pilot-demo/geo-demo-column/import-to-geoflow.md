# 将事实卡导入 GEOFlow（演示）

1. 打开 http://localhost:18080/geo_admin （建议仅用 `localhost`）
2. 进入知识库，新建或选用「GEO 示范栏目」知识库
3. 将 [`fact-cards.md`](./fact-cards.md) 内容粘贴为知识条目（或按卡片拆条）
4. 触发切片与 Embedding，确认向量化完成
5. 创建生成任务并绑定该 KB，要求输出带证据引用
6. Suite「事实卡」步默认读 `/pilot-demo/geo-demo-column/metrics.json`；若已有真实向量化率，可改该 JSON 的 `demo_data=false` 并填入实测数字
