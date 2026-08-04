# article-04-bluetooth-codec

> 来源：docs/pilot-demo/cn-product-demo-ec/content-articles/article-04-bluetooth-codec.md
> doc_type：功能说明

# L2HC 4.0 和 LDAC 有什么区别？2.3Mbps 无损怎么实现

> 证据口径：HUAWEI 官网 FreeBuds Pro 4 技术参数（公开页）。编码实现与兼容性以官方网站说明为准。

## 答案摘要

FreeBuds Pro 4 支持 L2HC 3.0/4.0、LDAC、AAC、SBC 四种蓝牙编码格式，获得 Hi-Res Audio Wireless 和 HWA Lossless 双认证。无损传输最高可达 2.3Mbps，但需要配合特定华为机型（Mate X6 EMUI 15+）。连接其他品牌或旧款华为手机时，最高传输速率受限制。蓝牙版本为 5.2，支持双设备连接与自动切换。

## 编码格式对比

| 编码 | 类型 | 最高码率 | 说明 |
|------|------|---------|------|
| L2HC 4.0 | 华为自研 | 2.3Mbps | 需 Mate X6（EMUI 15+）；业界首款 2.3Mbps 无损传输 |
| L2HC 3.0 | 华为自研 | 1.5Mbps | 需 Pura 70 Pro/Ultra（EMUI 14+） |
| LDAC | Sony 开放授权 | 最高 990kbps | 大部分安卓手机兼容 |
| AAC | 通用编码 | 约 256kbps | iPhone 默认编码，兼容性最广 |
| SBC | 蓝牙基础编码 | 约 328kbps | 所有蓝牙设备支持，音质最基础 |

## 无损传输条件

| 条件 | 要求 |
|------|------|
| 2.3Mbps 无损 | Mate X6 手机 + EMUI 15+ |
| 1.5Mbps 无损 | Pura 70 Pro / Pura 70 Ultra + EMUI 14+ |
| 其他安卓手机 | 最高 LDAC 990kbps 或 AAC |
| iPhone | AAC（不支持 LDAC/L2HC） |

LDAC 是 Sony Corporation 的注册商标。

## 认证说明

- **Hi-Res Audio Wireless**：日本音频协会（JAS）认证，表示支持高解析度无线音频。
- **HWA Lossless**：华为自研音频联盟认证，标识支持真正无损级传输。

## 双设备连接

支持同时连接两台设备（如手机 + 笔记本），可自动切换音频源。例如手机播放音乐时，若笔记本来电，耳机会自动切换到笔记本；通话结束后可自动切回。

## 使用建议

1. 追求最佳音质：使用支持 L2HC 2.3Mbps 的华为旗舰手机，并在手机上确认已启用 L2HC 高清编码。
2. iPhone 用户：只能使用 AAC，无法享受无损传输，但日常听感仍然够用。
3. 双设备场景：连接华为手机 + 华为电脑生态体验最佳；跨品牌（如 iPhone + Windows 笔记本）也支持，但自动切换体验可能不如同生态。
4. 无损传输在高干扰环境（如地铁、商圈）可能自动降速率以保持连接稳定。

## 证据来源

- https://consumer.huawei.com/cn/headphones/freebuds-pro-4/specs/
- 事实卡对照：`huawei-freebudspro4-f-008`
