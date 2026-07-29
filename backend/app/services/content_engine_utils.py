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

_EVIDENCE_RULES = (
    "【证据】参数、对比结论、法规表述必须来自下方【知识】检索片段；"
    "知识中没有的数字或断言写「未在资料中找到」，禁止编造。\n"
    "【禁止话术】禁止「保证上榜」「必被大模型引用」「全球第一」「永不撞机」「绝对防水」等无法溯源承诺。\n"
)

_SLOTS = "标题：{{title}}\n实体：{{entity}}\n关键词：{{keyword}}\n知识：\n{{Knowledge}}\n"

# 演示主路径 10 条细版提示词（产品通用，实体用 {{entity}}）
CHINA_PROMPTS: list[dict[str, Any]] = [
    {
        "title": "七段式产品说明·结论前置",
        "sort_order": 10,
        "body": (
            "【角色】品牌内容编辑。仅依据【知识】撰写「{{entity}}」产品说明，全中文。\n"
            "【必含七段】缺一不可，用「一、二、三…」编号：\n"
            "一、结论前置（40–80 字回答「它是什么」）\n"
            "二、核心能力分层（按知识中出现的能力维度写，无则跳过并注明）\n"
            "三、关键参数（只写知识中有数字的项，文字罗列，勿用表格语法）\n"
            "四、适用场景（2–4 个，不编造客户名）\n"
            "五、FAQ（3 问，格式「问：」「答：」）\n"
            "六、边界与条件（实验室数据、地区差异、使用限制等，有则写）\n"
            "七、行动建议（查阅官方资料，不强迫成交）\n"
            f"{_EVIDENCE_RULES}"
            f"{_PLAIN_PROSE_RULES}"
            f"{_SLOTS}"
        ),
    },
    {
        "title": "FAQ批量·可摘问答卡",
        "sort_order": 20,
        "body": (
            "【角色】产品支持文案。根据【知识】为「{{entity}}」生成 6–8 条中文 FAQ。\n"
            "【格式】每条固定为「问：……」「答：……」（两句结论 + 一条证据要点）。\n"
            "【覆盖】定位、核心参数、使用条件、限制、相对上代/竞品差异（有知识才写）。\n"
            "【验收】读者可不看上下文单独摘取一条问答；禁止编造规格。\n"
            f"{_EVIDENCE_RULES}"
            f"{_PLAIN_PROSE_RULES}"
            f"{_SLOTS}"
        ),
    },
    {
        "title": "中立对比·决策说明",
        "sort_order": 30,
        "body": (
            "【角色】评测编辑。围绕「{{entity}}」与知识中出现的对照对象写中立决策说明。\n"
            "【结构】\n"
            "一、对比结论（80 字内）\n"
            "二、分维度说明（每个维度一段：维度名 → 本品据知识 → 对照/备注/条件）\n"
            "三、适用谁选本品 / 谁更适合对照方案\n"
            "四、限制与资料缺口\n"
            "【约束】只转述知识中的对比表述；不得贬低第三方或捏造评测分；勿输出 Markdown 表格。\n"
            f"{_EVIDENCE_RULES}"
            f"{_PLAIN_PROSE_RULES}"
            f"{_SLOTS}"
        ),
    },
    {
        "title": "答案摘要块·可被引用",
        "sort_order": 40,
        "body": (
            "【角色】答案引擎友好的摘要作者。为「{{entity}}」写 120–180 字可独立摘取的答案摘要。\n"
            "【必含】开篇直接回答用户问题（关键词：{{keyword}}）；"
            "穿插知识中可核验的关键参数或事实；"
            "文末一句：「以上摘自公开资料/知识库，以官方最新说明为准。」\n"
            "【验收】单段或两段纯正文，无标题井号、无列表符号堆砌，可被直接引用。\n"
            f"{_EVIDENCE_RULES}"
            f"{_PLAIN_PROSE_RULES}"
            f"{_SLOTS}"
        ),
    },
    {
        "title": "限制与合规说明",
        "sort_order": 50,
        "body": (
            "【角色】合规顾问。单独输出「{{entity}}」的使用与宣传限制说明。\n"
            "【结构】用「1. 2. 3.」列出限制条目；每条含：限制点 → 条件/适用范围 → 建议表述。\n"
            "【覆盖】安全、防水/防护、法规/认证、地区差异、宣传禁区（有知识才写）。\n"
            "【语气】克制、可执行；禁止恐吓式营销与无法溯源承诺。\n"
            f"{_EVIDENCE_RULES}"
            f"{_PLAIN_PROSE_RULES}"
            f"{_SLOTS}"
        ),
    },
    {
        "title": "场景种草·使用故事",
        "sort_order": 60,
        "body": (
            "【角色】生活方式内容作者。围绕关键词「{{keyword}}」写「{{entity}}」的场景种草文，全中文。\n"
            "【结构】\n"
            "一、场景开场（谁、在哪、要解决什么，不编造具体客户姓名）\n"
            "二、关键能力如何落到该场景（只写知识中有的能力）\n"
            "三、体验细节 2–3 点（参数须可溯源）\n"
            "四、不适合的情况（有知识写限制；无则写「资料未覆盖」）\n"
            "五、收尾行动建议（查官方资料，不强迫下单）\n"
            "【语气】有画面感，但不夸张、不保证效果。\n"
            f"{_EVIDENCE_RULES}"
            f"{_PLAIN_PROSE_RULES}"
            f"{_SLOTS}"
        ),
    },
    {
        "title": "参数速查卡·要点罗列",
        "sort_order": 70,
        "body": (
            "【角色】产品文档编辑。为「{{entity}}」输出一页式参数速查卡，回答「{{keyword}}」。\n"
            "【结构】先用 40 字结论，再用「一、二、三…」分类罗列参数/规格；"
            "每项格式：「名称：数值或表述（来源：知识）」；知识没有的项写「未在资料中找到」。\n"
            "【禁止】编造单位换算、捏造缺失参数、输出 Markdown 表格。\n"
            "【验收】读者可快速扫读并核对数字。\n"
            f"{_EVIDENCE_RULES}"
            f"{_PLAIN_PROSE_RULES}"
            f"{_SLOTS}"
        ),
    },
    {
        "title": "购买决策·预算与套装",
        "sort_order": 80,
        "body": (
            "【角色】购前顾问。帮助读者围绕「{{entity}}」做购买决策（关键词：{{keyword}}）。\n"
            "【结构】\n"
            "一、适不适合买（结论 50 字内）\n"
            "二、预算与套装怎么选（只写知识中出现的版本/配件/服务）\n"
            "三、必看条件与隐藏成本（有则写）\n"
            "四、三问 FAQ（问：/答：）\n"
            "五、建议下一步（对比官方渠道信息，不承诺最低价）\n"
            f"{_EVIDENCE_RULES}"
            f"{_PLAIN_PROSE_RULES}"
            f"{_SLOTS}"
        ),
    },
    {
        "title": "升级换代·值不值得换",
        "sort_order": 90,
        "body": (
            "【角色】产品演进分析作者。回答「从旧款/对照方案升级到 {{entity}} 值不值得」。\n"
            "【结构】\n"
            "一、一句话结论\n"
            "二、提升点清单（仅知识中明确对比或参数差异）\n"
            "三、不变或仍需注意的点\n"
            "四、谁值得换 / 谁可暂缓\n"
            "五、资料缺口声明\n"
            "【约束】不得虚构旧款参数；知识未提对照型号时，只写本品能力并说明「对照信息不足」。\n"
            f"{_EVIDENCE_RULES}"
            f"{_PLAIN_PROSE_RULES}"
            f"{_SLOTS}"
        ),
    },
    {
        "title": "口播提纲·短视频分镜",
        "sort_order": 100,
        "body": (
            "【角色】短视频编导。为「{{entity}}」写 45–60 秒口播提纲（主题：{{keyword}}）。\n"
            "【结构】按时间轴输出：\n"
            "0–5 秒钩子（一句结论）\n"
            "5–25 秒三个证据点（每点一句口播 + 一句画面提示）\n"
            "25–45 秒限制/条件（避免夸大）\n"
            "45–60 秒收束与行动号召（引导查官方资料，不保证转化）\n"
            "【格式】纯中文；每行「口播：… / 画面：…」；禁止 Markdown 符号。\n"
            f"{_EVIDENCE_RULES}"
            f"{_PLAIN_PROSE_RULES}"
            f"{_SLOTS}"
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
