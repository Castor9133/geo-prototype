"""内容引擎纯函数（可离线单测，无 DB / Settings 依赖）。"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any

CHINA_PROMPTS: list[dict[str, Any]] = [
    {
        "title": "DeepSeek/知乎向·七段式信任正文",
        "sort_order": 10,
        "body": (
            "【角色】你是 GEO 内容策略专家，面向知乎/搜狐等权威平台写中文正文。\n"
            "【结构】问题→观点→方法→证据→权威标注→实体标记→回链锚点（七段式）。\n"
            "【硬要求】首屏 80–150 字答案摘要；问句化 H2；含数据/对比表或步骤；白帽，禁止伪造引用率。\n"
            "【知识】优先使用下方检索片段，勿编造产品参数。\n"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "微信公众号向·结构化专栏正文",
        "sort_order": 20,
        "body": (
            "【角色】公众号专栏作者。痛点开场→方案→3 个带数据的小标题→文末 5 条 FAQ。\n"
            "语气友好专业；可提示视频号/小程序联动，勿黑产。\n"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "豆包/官网向·FAQ+EEAT可摘正文",
        "sort_order": 30,
        "body": (
            "【角色】官网内容编辑。答案优先+Schema/FAQ 友好段落；体现经验/专业/权威/可信。\n"
            "每段可独立摘取；参数必须来自知识片段。\n"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "榜单评测对比·决策型正文",
        "sort_order": 40,
        "body": (
            "【角色】评测编辑。对比表（维度/本品/竞品）+ 适用场景 + 限制说明 + 结论。\n"
            "禁止保证「必上榜」。\n标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "白帽GEO·统一身份与避坑指南",
        "sort_order": 50,
        "body": (
            "【角色】合规顾问。写统一数字身份与避坑（禁伪演示、禁极端长尾刷榜、禁伪造截图）。\n"
            "给出可执行清单。\n标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
]


def slugify(name: str) -> str:
    base = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name.strip(), flags=re.UNICODE)
    base = re.sub(r"-+", "-", base).strip("-").lower() or "kb"
    return base[:100]


def split_chunks(text: str, *, max_chars: int = 800) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    buf = ""
    for part in parts:
        piece = part.strip()
        if not piece:
            continue
        if len(buf) + len(piece) + 2 <= max_chars:
            buf = f"{buf}\n\n{piece}".strip()
        else:
            if buf:
                chunks.append(buf)
            if len(piece) <= max_chars:
                buf = piece
            else:
                for i in range(0, len(piece), max_chars):
                    chunks.append(piece[i : i + max_chars])
                buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def local_hash_embedding(text: str, dims: int = 64) -> list[float]:
    """无 Embedding API 时的确定性降级向量。"""
    vec = [0.0] * dims
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", (text or "").lower())
    if not tokens:
        tokens = ["empty"]
    for tok in tokens:
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        for i in range(dims):
            vec[i] += (digest[i % len(digest)] / 255.0) - 0.5
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n))) or 1.0
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n))) or 1.0
    return dot / (na * nb)


def repo_root() -> Path:
    """定位仓库根（含 docs/pilot-demo）。services → app → backend → root。"""
    here = Path(__file__).resolve()
    for candidate in (here.parents[3], here.parents[2], *here.parents):
        if (candidate / "docs" / "pilot-demo" / "cn-product-demo-v2").is_dir():
            return candidate
    return here.parents[3]
