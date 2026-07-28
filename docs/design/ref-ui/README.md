# 参考 UI（风格学习，非布局照搬）

本目录存放产品参考图，用于抽取**视觉气质**。

**不照搬**参考产品的标题、五步假工厂文案、看板列名或无关信息架构。本仓仍使用 GEORank / Suite / 内容引擎 / 观测叙事。

## 方向铁律（必读）

**禁止再往纯白扁平 admin / 顶栏文字链风格收敛。**

纠正方向：**往本目录例图靠拢**，不是往更白的仪表盘靠。

| 允许 | 禁止 |
|------|------|
| 奶油底 `#F8F7F2` / 浅灰蓝底 `#F0F2F5` | 整页纯白 `#FFFFFF` 当主底 |
| 白卡 + 细深色描边 + 可感知轻阴影 | `box-shadow: none` 铺满内容卡 |
| 蓝/陶土橙强调、KPI/进度条/环图有重量 | 内页跟 header 一样素的文字链化 |
| 胶囊 Tab、彩色状态点、分区看板列 | 去掉一切层次只留细灰线 |

Header 可保持相对克制；**内页内容区必须比 header 更有层次与强调色。**

Admin 侧栏菜单结构保持统一，只改视觉 token，不拆菜单。Admin 主内容区同样遵守上表。

## 例图对照

| 参考图 | 文件 | 气质要点 | 本仓用法 |
|--------|------|----------|----------|
| 内容增长工厂 | [01-content-growth-factory.png](./01-content-growth-factory.png) | 浅灰蓝底、蓝主色、5 步指标卡、看板三栏、右侧环图 | Suite 概览 / cockpit |
| AI 答案监测 | [02-ai-answer-monitor.png](./02-ai-answer-monitor.png) | 暖白底、三 KPI、左问题库+中答案+右证据/环、下折线/平台对比 | **观测 = AI 答案监测布局**（`/suite?step=measure`） |
| 知识资产与证据库 | [03-knowledge-evidence-hub.png](./03-knowledge-evidence-hub.png) | 奶油底、KPI 密度、证据表 | 内容引擎 / 知识中枢 |
| 观测改版前（对照） | [00-measure-before.png](./00-measure-before.png) | 步骤卡+四格空壳驾驶舱 | **禁止回退** |

## Admin 自检提示

侧栏：仪表盘 / 诊断 / 拓词 / **可信观测** / 内容引擎 / 系统设置 / 访问前台（可 `_blank`）。

可信观测空状态必须有主 CTA（运行采样 / 加载演示 KPI），禁止仅灰字 + KPI 全 `--`。

## 本地预览（硬刷新）

```powershell
.\scripts\start-local.ps1
# http://localhost:3009/suite?step=measure
# http://localhost:3009/admin/trust-obs
# http://localhost:3009/settings
# http://localhost:3009/admin/settings
```

CSS 缓存：`?v=20260728-admin1`（Admin）/ `?v=20260728-ux1`（Suite）。改完请 **Ctrl+F5**。
