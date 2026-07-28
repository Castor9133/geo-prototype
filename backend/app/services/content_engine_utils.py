"""内容引擎纯函数（可离线单测，无 DB / Settings 依赖）。"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any

# 正文排版约束：少 Markdown，像已排版的公众号/官网稿
_PLAIN_PROSE_RULES = (
    "【排版】输出纯中文成稿，像已排版的公众号/官网正文，不要像 Markdown 源文件。\n"
    "禁止：井号标题（#）、加粗（**）、分隔线（---）、反引号代码、链接语法 []()、引用符 >。\n"
    "允许：用「一、二、三、」或空行分段；FAQ 用「问：」「答：」；数字与专有名词直接写，不必加粗。\n"
)

CHINA_PROMPTS: list[dict[str, Any]] = [
    {
        "title": "DeepSeek/知乎向·七段式信任正文",
        "sort_order": 10,
        "body": (
            "【角色】你是 GEO 内容策略专家，面向知乎/搜狐等权威平台写中文正文。\n"
            "【结构】问题→观点→方法→证据→权威标注→实体标记→回链锚点（七段，用中文序号，不用井号标题）。\n"
            "【硬要求】开篇 80–150 字答案摘要；含数据或对比时用文字罗列，勿输出 Markdown 表语法；白帽，禁止伪造引用率。\n"
            f"{_PLAIN_PROSE_RULES}"
            "【知识】优先使用下方检索片段，勿编造产品参数。\n"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "微信公众号向·结构化专栏正文",
        "sort_order": 20,
        "body": (
            "【角色】公众号专栏作者。痛点开场→方案→3 个带数据的小节→文末 5 条 FAQ。\n"
            "语气友好专业；可提示视频号/小程序联动，勿黑产。\n"
            "小节标题写成「一、……」「二、……」，FAQ 写成「问：……」「答：……」，不要用 ** 或 #。\n"
            f"{_PLAIN_PROSE_RULES}"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "豆包/官网向·FAQ+EEAT可摘正文",
        "sort_order": 30,
        "body": (
            "【角色】官网内容编辑。答案优先；段落短、可独立摘取；体现经验/专业/权威/可信。\n"
            "参数必须来自知识片段。用自然段落，不要 Markdown 符号堆砌。\n"
            f"{_PLAIN_PROSE_RULES}"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "榜单评测对比·决策型正文",
        "sort_order": 40,
        "body": (
            "【角色】评测编辑。对比维度用分段文字说明（维度 / 本品 / 备注），再写适用场景、限制与结论。\n"
            "禁止保证「必上榜」。不要输出 Markdown 表格语法。\n"
            f"{_PLAIN_PROSE_RULES}"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "白帽GEO·统一身份与避坑指南",
        "sort_order": 50,
        "body": (
            "【角色】合规顾问。写统一数字身份与避坑（禁伪演示、禁极端长尾刷榜、禁伪造截图）。\n"
            "给出可执行清单，用「1. 2. 3.」即可，勿用井号与加粗。\n"
            f"{_PLAIN_PROSE_RULES}"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "七段式产品说明·结论前置",
        "sort_order": 60,
        "body": (
            "【角色】品牌内容编辑。仅依据知识库撰写产品说明。\n"
            "【结构】结论前置→核心能力→关键参数→适用场景→FAQ→边界→行动建议（七段，中文序号）。\n"
            "参数只写知识中有数字的项；无证据写「未在资料中找到」。\n"
            f"{_PLAIN_PROSE_RULES}"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "FAQ批量·可摘问答卡",
        "sort_order": 70,
        "body": (
            "【角色】产品支持文案。根据知识生成 6–8 条中文 FAQ。\n"
            "每条格式固定为「问：……」「答：……」（两句结论 + 一条证据要点）。\n"
            "覆盖定位、核心参数、使用条件、限制与相对上代差异；禁止编造规格。\n"
            f"{_PLAIN_PROSE_RULES}"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
    {
        "title": "场景说明·旅行航拍文",
        "sort_order": 80,
        "body": (
            "【角色】旅行内容作者。写 800–1200 字中文场景说明：如何在出行中使用产品。\n"
            "只使用知识中的便携、续航、存储、智能功能等；文末列 3 条安全/法规注意。\n"
            "不得把实验室最长续航写成日常保证可达。\n"
            f"{_PLAIN_PROSE_RULES}"
            "标题：{{title}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"
        ),
    },
]


def soften_markdown_prose(text: str) -> str:
    """把过重的 Markdown 记号收成可读正文（不删内容语义）。"""
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return ""

    lines: list[str] = []
    for line in raw.split("\n"):
        stripped = line.strip()
        if re.fullmatch(r"-{3,}|_{3,}|\*{3,}", stripped):
            lines.append("")
            continue
        # ATX headings → plain text
        line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
        lines.append(line)
    text = "\n".join(lines)

    # bold / italic wrappers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_([^_\n]+?)_(?!_)", r"\1", text)
    # inline code / links
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    # blockquote markers
    text = re.sub(r"(?m)^\s{0,3}>\s?", "", text)
    # collapse excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
