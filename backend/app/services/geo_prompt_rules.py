"""GEO 论文方法 → 提示词共享块（拓词标题门 + 内容模板共用）。

依据：Aggarwal et al. GEO (KDD 2024)；结构侧 GEO-SFE。
禁止把实验可见度数字写成产品「实测引用率」。
"""
from __future__ import annotations

import re

# 单测与文档检索锚点
GEO_METHOD_MARKER = "【GEO方法】"
GEO_STRUCTURE_MARKER = "【GEO结构】"
GEO_TITLE_GATE_MARKER = "【GEO标题门】"

_GEO_METHOD_RULES = (
    f"{GEO_METHOD_MARKER}（对齐 Aggarwal GEO；有知识才写，无则声明缺口；禁止实测引用率话术）\n"
    "1. Statistics：优先写可核验数字/比例/条件（来自【知识】）；无数字则写「资料未给出量化数据」。\n"
    "2. Cite Sources：关键断言旁标明依据来自【知识】或「以官方最新说明为准」；禁止伪造外链与期刊名。\n"
    "3. Quotation：可用知识中的原句级要点作短引用块；禁止编造名人/用户口碑语录。\n"
    "4. Fluency：句子通顺、结论先行、少空话；组合上优先「通顺表述 + 具体数据」。\n"
    "5. 禁止 Keyword Stuffing：不得为凑词重复堆砌实体名/关键词；不得输出「XX优化/平台/引擎」无信息串。\n"
    "6. 禁止承诺「保证上榜」「必被大模型引用」「答案引用率提升 X%」。\n"
)

_GEO_STRUCTURE_RULES = (
    f"{GEO_STRUCTURE_MARKER}（对齐答案引擎可摘取：Macro/Meso）\n"
    "1. 答案前置：开篇 40–150 字自洽回答题面，点名实体，读者不看后文也能摘走。\n"
    "2. 分点可摘：用「一、二、三」或「问：/答：」；每段尽量独立成块。\n"
    "3. FAQ 问句须像真实检索/问 AI 的完整题面，禁止「问题1」式空标签。\n"
    "4. 关键数字与限制条件靠前出现；资料缺口单独声明。\n"
)

_GEO_TITLE_GATE = (
    f"{GEO_TITLE_GATE_MARKER}（拓词/平台标题第一关）\n"
    "1. 像真人会问 AI 的完整题面或可点开的选题标题：含实体 + 意图（定义/对比/怎么做/值不值等）。\n"
    "2. 优先 6–28 个汉字；一条只服务一个意图。\n"
    "3. 禁止：英文/中文分号粘词、关键词堆砌、空泛「XX优化/平台/系统」、无实体的口号。\n"
    "4. 通过门的标题应能直接交给内容模板写成「结论前置 + 证据」短文。\n"
)

# 供拓词 system / user JSON 复用的短版标题门文案
GEO_TITLE_GATE_BRIEF = (
    "标题须像 AI 查询题面：实体清晰、可答、可写证据；"
    "禁分号粘词、禁 Keyword Stuffing、禁空泛优化/平台后缀；优先 6–28 字。"
)

_STUFFING_SUFFIXES = (
    "优化",
    "平台",
    "系统",
    "引擎",
    "工具",
    "解决方案",
    "赋能",
)

_EMPTY_TITLE_TOKENS = re.compile(r"^[\W_]+$", re.UNICODE)


def is_geo_title_acceptable(title: str, *, min_len: int = 4, max_len: int = 48) -> bool:
    """轻量标题门：过滤分号粘词、过短/过长、明显 stuffing 空泛串。"""
    text = re.sub(r"\s+", " ", (title or "").strip())
    if not text or _EMPTY_TITLE_TOKENS.fullmatch(text):
        return False
    if ";" in text or "；" in text:
        return False
    compact = re.sub(r"\s+", "", text)
    if len(compact) < min_len or len(compact) > max_len:
        return False
    # 「实体+空泛后缀」且总长过短：如「GEO优化」「党媒平台」
    for suffix in _STUFFING_SUFFIXES:
        if compact.endswith(suffix) and len(compact) <= len(suffix) + 4:
            return False
    # 连续重复 2+ 字片段三次以上
    if re.search(r"(.{2,})\1{2,}", compact):
        return False
    return True


def geo_prompt_blocks(*, include_title_gate: bool = True) -> str:
    """内容模板尾部共用块。"""
    parts = [_GEO_METHOD_RULES, _GEO_STRUCTURE_RULES]
    if include_title_gate:
        parts.append(_GEO_TITLE_GATE)
    return "".join(parts)
