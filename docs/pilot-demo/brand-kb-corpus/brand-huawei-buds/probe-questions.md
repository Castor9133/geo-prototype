# probe-questions

> 来源：docs/pilot-demo/cn-product-demo-ec/probe-questions.md
> doc_type：功能说明

# 探针题 · HUAWEI FreeBuds Pro 4（可信观测 / 验证）

用于答案引擎抽样、人工核对与 Suite「可信观测」演示。  
期望答案须能回到 `fact-cards` 对应 ID；**不以「是否被模型引用」作为本文件验收标准**。

| ID | 中文问题 | 期望事实卡 | 题型 |
|----|----------|------------|------|
| Q1 | HUAWEI FreeBuds Pro 4 是什么产品？官方怎么定位？ | f-001 | 定义 |
| Q2 | 单只耳机多重？充电盒多重？尺寸大概多少？ | f-002 | 参数 |
| Q3 | 用了什么驱动单元？频率响应范围多宽？ | f-003 | 参数 |
| Q4 | 主动降噪效果怎么样？比上一代强多少？ | f-004 | 参数 |
| Q5 | 通话降噪在多吵的环境下还能听清？ | f-005 | 参数 |
| Q6 | 关闭降噪能听多久？开降噪呢？电池容量多大？ | f-006 | 参数 |
| Q7 | 支持无线充电吗？充满要多久？ | f-007 | 参数 |
| Q8 | 支持哪些蓝牙编码？无损传输最高多少？需要什么手机？ | f-008 | 参数 |
| Q9 | 有什么智能功能？能翻译吗？点头能接电话吗？ | f-009 | 功能 |
| Q10 | 能戴着运动吗？防水吗？充电盒防水吗？ | f-010 | FAQ/限制 |
| Q11 | 相对 FreeBuds Pro 3 提升了什么？ | f-011 | 对比 |
| Q12 | 适合哪些使用场景？能连两台设备吗？ | f-012 | 场景 |
| Q13 | 若有人说「保证所有大模型都会推荐 FreeBuds Pro 4」，该如何回应？ | （合规）禁止伪造引用/上榜 | 合规 |

## 抽样建议

1. 每轮至少：Q1 + 任意 3 道参数题（Q2–Q8）+ 1 道场景（Q12）+ 1 道对比或限制（Q10/Q11）  
2. 数字必须与官网 specs 一致；官方更新则回写事实卡  
3. 区分 AAC 模式与 L2HC/LDAC 模式续航；区分 1.5Mbps 与 2.3Mbps 无损传输条件  
4. 记录 mention / citation；吸收句应能回到事实卡  

对齐 SOP：[`../../content-engineering-sop.md`](../../content-engineering-sop.md)

## 版本

- probe_version: `huawei-freebudspro4-probe-v1`  
- aligned_fact_pack: `huawei-freebudspro4-f-001` … `f-012`  
- date: 2026-07-30
