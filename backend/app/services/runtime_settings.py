"""
运行时设置解析。

先从数据库读取后台可配项，不存在时回退到环境变量。
当前主要服务于 AI / Embedding 配置。
"""
from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.models.settings import Setting
from app.services.settings_security import decrypt_setting_value

_cache_lock = asyncio.Lock()
_cache_ttl_seconds = 15
_cache_expires_at = 0.0
_settings_cache: dict[str, Any] = {}
POSTGRES_INTEGER_MAX = 2_147_483_647
DEFAULT_DIAGNOSTIC_RULE_WEIGHTS = {
    "schema": 30.0,
    "content": 30.0,
    "meta": 20.0,
    "citation": 20.0,
}
DEFAULT_SOLUTION_TEMPLATES = {
    "system_prompt": (
        "你是 GEOrank 平台的 AI 问答顾问，专注于解释 GEO（生成式引擎优化）、"
        "AI 搜索可见性、内容结构、品牌实体一致性与可执行增长动作。"
        "根据用户问题、诊断上下文和公司知识库，给出清晰、可信、可审计的回答。"
        "口径约束：诊断里的 citation/引用维是「页面外链与权威链就绪度」，"
        "不是「AI 答案引用率」；爬虫 PV、页面分也不得表述为引用结果。"
        "证据不足时明确说明不确定，不要编造数据或保证上榜/引用。"
    ),
    "response_instruction": (
        "请优先回答用户问题本身。需要科普时先解释概念，需要执行时再给可验证步骤；"
        "如果公司知识库能提供帮助，可推荐 1-3 家相关公司并说明匹配原因与依据来源。"
        "涉及效果衡量时，区分代理信号（页面就绪、分发、爬虫访问）与答案面板抽样结果。"
    ),
    "streaming_system_prompt": (
        "你是 GEOrank AI 问答顾问，基于 GEO 知识、诊断上下文和公司知识库回答用户问题。"
        "勿把页面 citation 就绪信号或爬虫 PV 说成 AI 答案引用率；少空写，结论需可执行。"
    ),
}
DEFAULT_SOLUTION_CHANNELS = {
    "default_channel_key": "geo-basics",
    "channels": [
        {
            "key": "geo-basics",
            "name": "GEO 入门科普",
            "description": "解释 GEO、AI 搜索、生成式答案引擎和品牌可见性的基础概念。",
            "icon": "school",
            "enabled": True,
            "system_hint": "用通俗语言解释概念，先给结论，再给例子，避免过度技术化。",
            "sample_questions": [
                "GEO 和 SEO 到底有什么区别？",
                "为什么 AI 搜索会影响品牌获客？",
                "一个新品牌应该先做哪些 GEO 基础动作？",
            ],
        },
        {
            "key": "diagnostic-explain",
            "name": "诊断报告解读",
            "description": "把 GEO 诊断分数、Schema、内容结构、Meta 与页面外链就绪度解释成可理解的行动建议。",
            "icon": "monitoring",
            "enabled": True,
            "system_hint": (
                "围绕诊断上下文解释问题原因、影响和优先级，输出清晰的下一步动作；"
                "明确 citation 维是页面权威链/外链就绪度，不是 AI 答案引用率。"
            ),
            "sample_questions": [
                "帮我解释这份 GEO 诊断报告里最重要的三个问题。",
                "Schema 分低会怎样影响答案引擎对页面的理解与摘取？",
                "如果只能先修一个问题，应该先修什么？",
            ],
        },
        {
            "key": "content-structure",
            "name": "内容结构优化",
            "description": "围绕官网页面、教程、FAQ、案例和结构化答案，生成适合答案引擎读取的内容建议。",
            "icon": "article",
            "enabled": True,
            "system_hint": (
                "从标题层级、首段直答、FAQ、案例、权威信源与 Schema 角度给建议；"
                "强调实体一致与可核查事实，避免空泛「提升引用率」话术。"
            ),
            "sample_questions": [
                "一个 SaaS 官网首页怎样写更容易被答案引擎摘要？",
                "帮我设计一组适合 AI 搜索的 FAQ。",
                "产品页应该如何增加可抽取的答案块与事实卡？",
            ],
        },
        {
            "key": "brand-visibility",
            "name": "品牌可见性问答",
            "description": "回答品牌在答案引擎中被正确理解、提及与推荐所需的实体与信源建设问题。",
            "icon": "travel_explore",
            "enabled": True,
            "system_hint": (
                "把品牌实体、第三方信源、权威背书、官网资料和行业语境联系起来回答；"
                "说明提及/引用需答案面板抽样验证，页面分不能代替引用率。"
            ),
            "sample_questions": [
                "AI 为什么没有推荐我的品牌？",
                "如何让 AI 更准确理解我们的公司定位？",
                "品牌提及与第三方信源应该怎么建设？",
            ],
        },
        {
            "key": "action-plan",
            "name": "行动方案拆解",
            "description": "把问答结论进一步拆成 30/60/90 天计划、任务优先级和团队分工。",
            "icon": "checklist",
            "enabled": True,
            "system_hint": (
                "输出可执行计划，按阶段、负责人、交付物和衡量指标组织；"
                "指标需区分代理信号与答案抽样，勿承诺保证引用率。"
            ),
            "sample_questions": [
                "给我一份 30/60/90 天 GEO 执行计划。",
                "市场团队和内容团队应该如何分工做 GEO？",
                "把上面的建议拆成下周可以开始做的任务。",
            ],
        },
    ],
}
DEFAULT_AI_USAGE_POLICY = {
    "access_mode": "lifetime_quota_with_byok",
    "daily_token_limit": 0,
    "lifetime_token_grant": 10000,
    "global_daily_token_limit": 1000000,
    "global_budget_enabled": True,
    "emergency_byok_only": False,
    "quota_reset_timezone": "Asia/Shanghai",
    "allow_anonymous_ai_usage": False,
    "allow_user_byok": True,
    "byok_transport_mode": "proxy_transient",
    "byok_guidance": {
        "provider": "deepseek",
        "title": "平台赠送额度已用完",
        "message": "绑定自己的 DeepSeek API Key 后，可以继续使用 AI 功能。",
        "cta_label": "配置 DeepSeek API",
        "official_url": "https://platform.deepseek.com/api_keys",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
    },
    "allowed_byok_providers": [
        {
            "key": "deepseek",
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com",
            "default_model": "deepseek-v4-flash",
        },
        {
            "key": "openai",
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
        },
    ],
    "metered_modules": ["keywords", "diagnostics", "tools"],
}
DEFAULT_LLM_PROVIDER_CONFIG = {
    "strategy": "failover",
    "providers": [],
}

# 拓词 + 目标 AI 标题建议（可后台改；禁止把提示词/模板塞进前台）
KEYWORD_EXPANSION_SETTING_KEY = "keyword_expansion"
DEFAULT_KEYWORD_EXPANSION_CONFIG: dict[str, Any] = {
    "system_prompt": (
        "你是面向中文传媒与 GEO（生成式引擎优化）场景的关键词策略专家。\n"
        "先理解种子词背后的业务画像与实体，再按 8 个意图维度输出可落地、可移交内容生产的词包，"
        "并按给定平台侧重为种子实体生成标题/问法建议。\n\n"
        "严格只返回 JSON（不要 markdown，不要解释）：\n"
        "{\n"
        '  "dimensions": [\n'
        "    {\n"
        '      "key": "semantic|scenario|commercial|ranking|review|brand|question|technical",\n'
        '      "items": [\n'
        "        {\n"
        '          "keyword": "可检索、可写作的中文关键词或问题式查询",\n'
        '          "recommendation_score": 0-100整数,\n'
        '          "business_score": 0-100整数,\n'
        '          "reason": "一句可审计理由：覆盖哪类意图/场景/实体"\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ],\n"
        '  "platform_title_hints": [\n'
        "    {\n"
        '      "platform": "与输入 platforms 完全一致的平台名",\n'
        '      "titles": ["标题1", "标题2", "标题3"]\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "质量硬约束：\n"
        "1. 每个维度输出 8-10 个词；八维意图必须可区分，禁止把同一说法换皮塞进多个维度。\n"
        "2. 实体一致：词必须锚定种子实体/业务（品牌、栏目、产品、主题、机构），禁止漂移到无关行业。\n"
        "3. 少空泛：禁止「XX平台/工具/系统/引擎/优化/推荐/榜单」式无信息堆砌；优先具体场景、角色、任务与长尾。\n"
        "4. 维度细则：\n"
        "   - semantic：同义近义、行业术语、实体别名、可检索变体（可含 1 个种子原词）\n"
        "   - scenario：真实使用场景与任务语境，必须是完整人话短语；禁止「角色标签 + 空格 + 种子」硬拼接\n"
        "   - commercial：采购、报价、选型、合作、预算等转化意图\n"
        "   - ranking：推荐/对比/哪家好/清单类（需带比较对象或适用边界）\n"
        "   - review：评测、优缺点、避坑、值不值、复盘\n"
        "   - brand：品牌/栏目/竞品/替代方案关联\n"
        "   - question：必须是问题式自然语言（如何/怎么/为什么/是否/有哪些/适合谁）\n"
        "   - technical：落地方法、流程、指标、结构、工作流、实施清单\n"
        "5. 长尾优先：至少一半词应像真实用户会搜/会问的完整短语（可含 6-20 字）。\n"
        "6. 画像约束：严格遵守给定 profile。\n"
        "7. 评分口径（代理信号，非实测）：recommendation_score=选题/内容生产优先级；"
        "business_score=商业转化意图；禁止写成「AI 答案引用率」。\n"
        "8. 去重：同一词包内禁止重复、近义重复。\n"
        "9. 中文为主，自然可读。\n"
        "10. platform_title_hints：必须覆盖输入中的每一个 platform；每平台恰好 titles_per_platform 条；"
        "标题要贴合该平台的 generation_focus，并避开 avoid；围绕 entity 与 seeds 写，"
        "通用站点可用（媒体/政务/品牌/电商等），禁止绑定某一垂类硬套话（如无人机续航/禁飞）。"
        "标题可作独立选题，勿输出空串。"
    ),
    "titles_per_platform": 3,
    "timeout_seconds": 20,
    "disclaimer": "目标 AI 侧重来自后台配置 + 模型生成标题 · 非平台实测 · 禁止写成引用率",
    "platforms": [
        {
            "platform": "豆包",
            "generation_focus": "侧重结论前置与场景对照；关键事实用官方/可核对口径；适当对比同档但勿贬低竞品；段落短、可扫读。",
            "avoid": ["保证上榜", "无来源关键数字", "恐吓式法规话术"],
        },
        {
            "platform": "元宝",
            "generation_focus": "偏购买/办理/取舍决策；语气可偏导购但须标注资料缺口；避免夸张促销承诺。",
            "avoid": ["绝对最低价", "虚构用户口碑", "只推竞品不提本品"],
        },
        {
            "platform": "Kimi",
            "generation_focus": "强调分点对照与可核对证据；写清宣传与可核实信息的差异；结构完整（结论→维度→限制）。",
            "avoid": ["无出处对比表", "编造评测分数", "Markdown 表格堆砌"],
        },
        {
            "platform": "DeepSeek",
            "generation_focus": "答案摘要优先、短段落可引用；主体点名清晰；竞品可弱化但勿捏造；文末注明以官方为准。",
            "avoid": ["冗长种草故事", "无来源推荐口号", "假装已实测"],
        },
    ],
}
DEFAULT_FRONTEND_MODULES = {
    "default_module": "diagnostic",
    "modules": [
        {
            "key": "diagnostic",
            "name": "诊断",
            "path": "/diagnostic",
            "description": "GEO 诊断和诊断报告访问",
            "enabled": True,
            "protected_paths": ["/diagnostic"],
        },
        {
            "key": "keywords",
            "name": "拓词",
            "path": "/keywords",
            "description": "GEO 拓词工具",
            "enabled": True,
            "protected_paths": ["/keywords"],
        },
        {
            "key": "tools",
            "name": "工具",
            "path": "/tools",
            "description": "JSON-LD、llms.txt、标题和知识库等小工具（演示主路径默认隐藏）",
            "enabled": False,
            "protected_paths": ["/tools"],
        },
    ],
}
DEFAULT_HOMEPAGE_RUNTIME = {
    "mode": "custom",
    "active_release_id": "9fe4a087-42bc-423a-bc59-fc020018a6f9",
    "fallback_enabled": True,
    "company_list_path": "/suite",
    "updated_at": None,
    "updated_by": None,
}
DEFAULT_HOMEPAGE_RELEASE_ID = DEFAULT_HOMEPAGE_RUNTIME["active_release_id"]
DEFAULT_HOMEPAGE_RELEASE_TITLE = "GEOrank 导航与版权更新"
VALID_AI_ACCESS_MODES = {
    "platform_unlimited",
    "daily_quota",
    "quota_with_byok",
    "byok_required",
    "lifetime_quota_with_byok",
}
VALID_LLM_PROVIDER_STRATEGIES = {"failover", "round_robin"}


def get_default_solution_template_config() -> dict[str, str]:
    return dict(DEFAULT_SOLUTION_TEMPLATES)


def get_default_solution_channel_config() -> dict[str, Any]:
    return {
        "default_channel_key": DEFAULT_SOLUTION_CHANNELS["default_channel_key"],
        "channels": [dict(channel) for channel in DEFAULT_SOLUTION_CHANNELS["channels"]],
    }


def get_default_ai_usage_policy_config() -> dict[str, Any]:
    return {
        **DEFAULT_AI_USAGE_POLICY,
        "byok_guidance": dict(DEFAULT_AI_USAGE_POLICY["byok_guidance"]),
        "allowed_byok_providers": [
            dict(item) for item in DEFAULT_AI_USAGE_POLICY["allowed_byok_providers"]
        ],
        "metered_modules": list(DEFAULT_AI_USAGE_POLICY["metered_modules"]),
    }


def get_default_llm_provider_config() -> dict[str, Any]:
    return {
        "strategy": DEFAULT_LLM_PROVIDER_CONFIG["strategy"],
        "providers": [],
    }


def get_default_frontend_module_config() -> dict[str, Any]:
    return {
        "default_module": DEFAULT_FRONTEND_MODULES["default_module"],
        "modules": [dict(module) for module in DEFAULT_FRONTEND_MODULES["modules"]],
    }


def get_default_homepage_runtime_config() -> dict[str, Any]:
    return dict(DEFAULT_HOMEPAGE_RUNTIME)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def invalidate_runtime_settings_cache() -> None:
    global _cache_expires_at, _settings_cache
    async with _cache_lock:
        _settings_cache = {}
        _cache_expires_at = 0.0


async def _load_runtime_settings() -> dict[str, Any]:
    global _cache_expires_at, _settings_cache

    now = time.monotonic()
    if _settings_cache and now < _cache_expires_at:
        return dict(_settings_cache)

    async with _cache_lock:
        now = time.monotonic()
        if _settings_cache and now < _cache_expires_at:
            return dict(_settings_cache)

        async with async_session() as db:
            result = await db.execute(select(Setting))
            items = result.scalars().all()

        _settings_cache = {
            item.key: decrypt_setting_value(item.value, item.key, item.category)
            for item in items
        }
        _cache_expires_at = time.monotonic() + _cache_ttl_seconds
        return dict(_settings_cache)


def _pick_string(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _pick_int(*values: Any, default: int) -> int:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return default


def _pick_float(value: Any, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pick_bool(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "off", "disabled"}:
            return False
    return bool(value)


def _normalize_provider_id(value: Any, index: int) -> str:
    raw = _pick_string(value).lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-_")
    if not normalized:
        normalized = f"provider-{index + 1}"
    return normalized[:50]


def _normalize_llm_provider(raw: Any, keys: dict[str, Any], index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    provider_id = _normalize_provider_id(raw.get("id") or raw.get("key"), index)
    api_key = _pick_string(raw.get("api_key"), keys.get(provider_id))
    return {
        "id": provider_id,
        "name": (_pick_string(raw.get("name")) or f"API {index + 1}")[:80],
        "base_url": _pick_string(raw.get("base_url"), raw.get("api_base_url"))[:240],
        "model": _pick_string(raw.get("model"), raw.get("default_model"))[:120],
        "enabled": _pick_bool(raw.get("enabled"), True),
        "priority": _pick_int(raw.get("priority"), index + 1, default=index + 1),
        "api_key": api_key,
        "has_api_key": bool(api_key),
    }


def _build_llm_provider_config(values: dict[str, Any]) -> dict[str, Any]:
    raw = values.get("llm_providers")
    if not isinstance(raw, dict):
        return get_default_llm_provider_config()

    strategy = _pick_string(raw.get("strategy"), DEFAULT_LLM_PROVIDER_CONFIG["strategy"])
    if strategy not in VALID_LLM_PROVIDER_STRATEGIES:
        strategy = DEFAULT_LLM_PROVIDER_CONFIG["strategy"]

    raw_keys = values.get("llm_provider_keys")
    if not isinstance(raw_keys, dict):
        raw_keys = {}

    providers: list[dict[str, Any]] = []
    seen: set[str] = set()
    raw_providers = raw.get("providers")
    if isinstance(raw_providers, list):
        for index, item in enumerate(raw_providers[:12]):
            provider = _normalize_llm_provider(item, raw_keys, index)
            if not provider or provider["id"] in seen:
                continue
            seen.add(provider["id"])
            if not (
                provider["enabled"]
                and provider["api_key"]
                and provider["base_url"]
                and provider["model"]
            ):
                continue
            providers.append(provider)

    providers.sort(key=lambda item: (int(item.get("priority") or 999), item["id"]))
    return {
        "strategy": strategy,
        "providers": providers,
    }


def _build_ai_runtime_config(values: dict[str, Any]) -> dict[str, Any]:
    llm_api_key = _pick_string(
        values.get("llm_api_key"),
        values.get("openai_api_key"),
        settings.LLM_API_KEY,
        settings.OPENAI_API_KEY,
    )
    config = {
        "llm_api_key": llm_api_key,
        "llm_base_url": _pick_string(values.get("llm_base_url"), settings.LLM_BASE_URL),
        "llm_model": _pick_string(values.get("llm_model"), settings.LLM_MODEL, settings.OPENAI_MODEL),
        "llm_fallback_model": _pick_string(
            values.get("llm_fallback_model"),
            values.get("codex_model"),
            settings.LLM_FALLBACK_MODEL,
            settings.CODEX_MODEL,
        ),
        "embedding_api_key": _pick_string(
            values.get("embedding_api_key"),
            values.get("openai_api_key"),
            settings.EMBEDDING_API_KEY,
        ),
        "embedding_base_url": _pick_string(values.get("embedding_base_url"), settings.EMBEDDING_BASE_URL),
        "embedding_model": _pick_string(values.get("embedding_model"), settings.EMBEDDING_MODEL),
        "embedding_dimensions": _pick_int(
            values.get("embedding_dimensions"),
            settings.EMBEDDING_DIMENSIONS,
            default=settings.EMBEDDING_DIMENSIONS,
        ),
        "codex_api_key": _pick_string(
            values.get("codex_api_key"),
            settings.CODEX_API_KEY,
            llm_api_key,
        ),
        "codex_base_url": _pick_string(
            values.get("codex_base_url"),
            settings.CODEX_BASE_URL,
            values.get("llm_base_url"),
            settings.LLM_BASE_URL,
        ),
        "codex_model": _pick_string(
            values.get("codex_model"),
            settings.CODEX_MODEL,
        ),
    }
    provider_config = _build_llm_provider_config(values)
    config["llm_provider_strategy"] = provider_config["strategy"]
    config["llm_providers"] = provider_config["providers"]
    return config


def _build_diagnostic_rule_config(values: dict[str, Any]) -> dict[str, Any]:
    raw = values.get("diagnostic_rule_weights")
    if not isinstance(raw, dict):
        raw = {}

    weights = {
        key: max(0.0, _pick_float(raw.get(key), default))
        for key, default in DEFAULT_DIAGNOSTIC_RULE_WEIGHTS.items()
    }
    total = round(sum(weights.values()), 2)
    if total <= 0:
        weights = dict(DEFAULT_DIAGNOSTIC_RULE_WEIGHTS)
        total = round(sum(weights.values()), 2)

    normalized_weights = {
        key: round(value / total, 4)
        for key, value in weights.items()
    }

    return {
        "weights": {key: round(value, 2) for key, value in weights.items()},
        "normalized_weights": normalized_weights,
        "total": total,
    }


def _build_solution_template_config(values: dict[str, Any]) -> dict[str, Any]:
    raw = values.get("solution_templates")
    if not isinstance(raw, dict):
        raw = {}

    config = {}
    for key, default in DEFAULT_SOLUTION_TEMPLATES.items():
        config[key] = _pick_string(raw.get(key), default) or default
    return config


def _normalize_solution_channel(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    key = _pick_string(raw.get("key"))
    name = _pick_string(raw.get("name"))
    if not key or not name:
        return None

    sample_questions = raw.get("sample_questions")
    if not isinstance(sample_questions, list):
        sample_questions = []
    cleaned_questions = [
        str(item).strip()[:160]
        for item in sample_questions
        if str(item or "").strip()
    ][:6]

    return {
        "key": key[:60],
        "name": name[:80],
        "description": _pick_string(raw.get("description"))[:240],
        "icon": (_pick_string(raw.get("icon")) or "forum")[:40],
        "enabled": bool(raw.get("enabled", True)),
        "system_hint": _pick_string(raw.get("system_hint"))[:500],
        "sample_questions": cleaned_questions,
    }


def _build_solution_channel_config(values: dict[str, Any]) -> dict[str, Any]:
    defaults = get_default_solution_channel_config()
    raw = values.get("solution_channels")
    if not isinstance(raw, dict):
        raw = {}

    raw_channels = raw.get("channels")
    channels: list[dict[str, Any]] = []
    seen: set[str] = set()
    if isinstance(raw_channels, list):
        for item in raw_channels:
            channel = _normalize_solution_channel(item)
            if not channel or channel["key"] in seen:
                continue
            channels.append(channel)
            seen.add(channel["key"])

    if not channels:
        channels = defaults["channels"]

    enabled_keys = [channel["key"] for channel in channels if channel.get("enabled", True)]
    default_channel_key = _pick_string(raw.get("default_channel_key"), defaults["default_channel_key"])
    if default_channel_key not in enabled_keys:
        default_channel_key = enabled_keys[0] if enabled_keys else channels[0]["key"]

    return {
        "default_channel_key": default_channel_key,
        "channels": channels,
    }


def _build_frontend_module_config(values: dict[str, Any]) -> dict[str, Any]:
    defaults = get_default_frontend_module_config()
    raw = values.get("frontend_modules")
    if not isinstance(raw, dict):
        raw = {}

    raw_by_key = {
        str(item.get("key", "")).strip().lower(): item
        for item in raw.get("modules") or []
        if isinstance(item, dict) and str(item.get("key", "")).strip()
    }

    modules: list[dict[str, Any]] = []
    for default_module in defaults["modules"]:
        key = default_module["key"]
        override = raw_by_key.get(key) or {}
        enabled = _pick_bool(override.get("enabled"), default_module["enabled"])
        modules.append(
            {
                **default_module,
                "enabled": enabled,
            }
        )

    if not any(module["enabled"] for module in modules):
        for module in modules:
            module["enabled"] = module["key"] == defaults["default_module"]

    enabled_keys = [module["key"] for module in modules if module["enabled"]]
    default_module_key = _pick_string(raw.get("default_module"), defaults["default_module"]).lower()
    if default_module_key not in enabled_keys:
        default_module_key = enabled_keys[0]

    return {
        "default_module": default_module_key,
        "modules": modules,
    }


def _build_homepage_runtime_config(values: dict[str, Any]) -> dict[str, Any]:
    raw = values.get("homepage_runtime")
    if not isinstance(raw, dict):
        raw = {}
    raw = {**DEFAULT_HOMEPAGE_RUNTIME, **raw}

    mode = _pick_string(raw.get("mode"), DEFAULT_HOMEPAGE_RUNTIME["mode"])
    if mode not in {"default", "custom"}:
        mode = "default"
    active_release_id = raw.get("active_release_id")
    if active_release_id is not None:
        active_release_id = _pick_string(active_release_id)
    if not active_release_id:
        active_release_id = None
        if mode == "custom":
            mode = "default"

    company_list_path = _pick_string(raw.get("company_list_path"), DEFAULT_HOMEPAGE_RUNTIME["company_list_path"])
    if not company_list_path.startswith("/"):
        company_list_path = f"/{company_list_path}"
    if company_list_path == "/" or company_list_path in {"/companies", "/company", "/submit-company", "/company-submit"}:
        company_list_path = "/suite"
    if company_list_path.startswith("/companies/") or company_list_path.startswith("/c/"):
        company_list_path = "/suite"

    updated_at = raw.get("updated_at")
    if updated_at is not None:
        updated_at = _pick_string(updated_at)
    updated_by = raw.get("updated_by")
    if updated_by is not None:
        updated_by = _pick_string(updated_by)

    return {
        "mode": mode,
        "active_release_id": active_release_id,
        "fallback_enabled": _pick_bool(raw.get("fallback_enabled"), True),
        "company_list_path": company_list_path,
        "updated_at": updated_at,
        "updated_by": updated_by,
    }


def normalize_homepage_runtime_payload(payload: dict[str, Any], current: dict[str, Any] | None = None) -> dict[str, Any]:
    base = current if isinstance(current, dict) else get_default_homepage_runtime_config()
    raw = {**base, **(payload or {})}
    if raw.get("updated_at") is None:
        raw["updated_at"] = _utc_now_iso()
    return _build_homepage_runtime_config({"homepage_runtime": raw})


def normalize_frontend_module_payload(payload: dict[str, Any], current: dict[str, Any] | None = None) -> dict[str, Any]:
    base = current if isinstance(current, dict) else get_default_frontend_module_config()
    raw_modules_by_key = {
        str(item.get("key", "")).strip().lower(): dict(item)
        for item in base.get("modules") or []
        if isinstance(item, dict) and str(item.get("key", "")).strip()
    }
    if isinstance(payload.get("modules"), list):
        for item in payload["modules"]:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip().lower()
            if not key:
                continue
            raw_modules_by_key[key] = {**raw_modules_by_key.get(key, {}), **item}

    raw = {
        "default_module": payload.get("default_module", base.get("default_module")),
        "modules": list(raw_modules_by_key.values()),
    }
    return _build_frontend_module_config({"frontend_modules": raw})


def _normalize_byok_provider(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    key = _pick_string(raw.get("key")).lower()
    name = _pick_string(raw.get("name"))
    base_url = _safe_http_url(raw.get("base_url"), "", max_length=240)
    default_model = _pick_string(raw.get("default_model"))[:100]
    if not key or not base_url or not default_model:
        return None
    return {
        "key": key[:50],
        "name": (name or key)[:80],
        "base_url": base_url,
        "default_model": default_model,
    }


def _safe_http_url(value: Any, default: str, *, max_length: int = 500) -> str:
    candidate = _pick_string(value)[:max_length]
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return default
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return default
    return candidate


def _normalize_byok_guidance(raw: Any, defaults: dict[str, Any]) -> dict[str, str]:
    value = raw if isinstance(raw, dict) else {}
    return {
        "provider": _pick_string(value.get("provider"), defaults["provider"])[:50],
        "title": _pick_string(value.get("title"), defaults["title"])[:120],
        "message": _pick_string(value.get("message"), defaults["message"])[:500],
        "cta_label": _pick_string(value.get("cta_label"), defaults["cta_label"])[:80],
        "official_url": _safe_http_url(
            value.get("official_url"),
            defaults["official_url"],
            max_length=500,
        ),
        "base_url": _safe_http_url(
            value.get("base_url"),
            defaults["base_url"],
            max_length=240,
        ),
        "model": _pick_string(value.get("model"), defaults["model"])[:100],
    }


def _build_ai_usage_policy_config(values: dict[str, Any]) -> dict[str, Any]:
    defaults = get_default_ai_usage_policy_config()
    raw = values.get("api_usage_policy")
    if not isinstance(raw, dict):
        raw = {}

    access_mode = _pick_string(raw.get("access_mode"), defaults["access_mode"])
    if access_mode not in VALID_AI_ACCESS_MODES:
        access_mode = defaults["access_mode"]
    if access_mode in {"daily_quota", "quota_with_byok"}:
        access_mode = "lifetime_quota_with_byok"

    providers = []
    seen_providers: set[str] = set()
    raw_providers = raw.get("allowed_byok_providers")
    if not isinstance(raw_providers, list):
        raw_providers = defaults["allowed_byok_providers"]
    for item in raw_providers:
        provider = _normalize_byok_provider(item)
        if not provider or provider["key"] in seen_providers:
            continue
        providers.append(provider)
        seen_providers.add(provider["key"])
    if not providers:
        providers = defaults["allowed_byok_providers"]

    modules = raw.get("metered_modules")
    if not isinstance(modules, list):
        modules = defaults["metered_modules"]
    modules = [
        str(item).strip().lower()
        for item in modules
        if str(item or "").strip()
    ]
    if not modules:
        modules = defaults["metered_modules"]

    return {
        "access_mode": access_mode,
        "daily_token_limit": min(
            POSTGRES_INTEGER_MAX,
            max(
                0,
            _pick_int(raw.get("daily_token_limit"), defaults["daily_token_limit"], default=defaults["daily_token_limit"]),
            ),
        ),
        "lifetime_token_grant": min(
            POSTGRES_INTEGER_MAX,
            max(
                0,
                _pick_int(
                    raw.get("lifetime_token_grant"),
                    defaults["lifetime_token_grant"],
                    default=defaults["lifetime_token_grant"],
                ),
            ),
        ),
        "global_daily_token_limit": min(
            POSTGRES_INTEGER_MAX,
            max(
                0,
                _pick_int(
                    raw.get("global_daily_token_limit"),
                    defaults["global_daily_token_limit"],
                    default=defaults["global_daily_token_limit"],
                ),
            ),
        ),
        "global_budget_enabled": _pick_bool(
            raw.get("global_budget_enabled"),
            defaults["global_budget_enabled"],
        ),
        "emergency_byok_only": _pick_bool(
            raw.get("emergency_byok_only"),
            defaults["emergency_byok_only"],
        ),
        "quota_reset_timezone": _pick_string(raw.get("quota_reset_timezone"), defaults["quota_reset_timezone"]),
        "allow_anonymous_ai_usage": _pick_bool(
            raw.get("allow_anonymous_ai_usage"),
            defaults["allow_anonymous_ai_usage"],
        ),
        "allow_user_byok": _pick_bool(raw.get("allow_user_byok"), defaults["allow_user_byok"]),
        "byok_transport_mode": (
            "browser_direct"
            if raw.get("byok_transport_mode") == "browser_direct"
            else "proxy_transient"
        ),
        "byok_guidance": _normalize_byok_guidance(
            raw.get("byok_guidance"),
            defaults["byok_guidance"],
        ),
        "allowed_byok_providers": providers,
        "metered_modules": modules,
    }


def get_default_keyword_expansion_config() -> dict[str, Any]:
    return {
        "system_prompt": DEFAULT_KEYWORD_EXPANSION_CONFIG["system_prompt"],
        "titles_per_platform": int(DEFAULT_KEYWORD_EXPANSION_CONFIG["titles_per_platform"]),
        "timeout_seconds": int(DEFAULT_KEYWORD_EXPANSION_CONFIG["timeout_seconds"]),
        "disclaimer": DEFAULT_KEYWORD_EXPANSION_CONFIG["disclaimer"],
        "platforms": [dict(item) for item in DEFAULT_KEYWORD_EXPANSION_CONFIG["platforms"]],
    }


def _normalize_keyword_platform(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    platform = _pick_string(raw.get("platform"), raw.get("name"))
    if not platform:
        return None
    avoid_raw = raw.get("avoid")
    avoid: list[str] = []
    if isinstance(avoid_raw, list):
        avoid = [str(item).strip()[:80] for item in avoid_raw if str(item or "").strip()][:8]
    elif isinstance(avoid_raw, str) and avoid_raw.strip():
        avoid = [part.strip()[:80] for part in avoid_raw.replace("，", ",").split(",") if part.strip()][:8]
    return {
        "platform": platform[:40],
        "generation_focus": _pick_string(raw.get("generation_focus"), raw.get("focus"))[:500]
        or "按平台习惯输出可扫读、可核对的标题与问法。",
        "avoid": avoid,
    }


def _build_keyword_expansion_config(values: dict[str, Any]) -> dict[str, Any]:
    defaults = get_default_keyword_expansion_config()
    raw = values.get(KEYWORD_EXPANSION_SETTING_KEY)
    if not isinstance(raw, dict):
        raw = {}

    system_prompt = _pick_string(raw.get("system_prompt"), defaults["system_prompt"]) or defaults["system_prompt"]
    titles_per = max(1, min(5, _pick_int(raw.get("titles_per_platform"), default=defaults["titles_per_platform"])))
    timeout_seconds = max(8, min(60, _pick_int(raw.get("timeout_seconds"), default=defaults["timeout_seconds"])))
    disclaimer = _pick_string(raw.get("disclaimer"), defaults["disclaimer"]) or defaults["disclaimer"]

    platforms: list[dict[str, Any]] = []
    seen: set[str] = set()
    raw_platforms = raw.get("platforms")
    if isinstance(raw_platforms, list):
        for item in raw_platforms[:12]:
            normalized = _normalize_keyword_platform(item)
            if not normalized or normalized["platform"] in seen:
                continue
            seen.add(normalized["platform"])
            platforms.append(normalized)
    if not platforms:
        platforms = [dict(item) for item in defaults["platforms"]]

    return {
        "system_prompt": system_prompt[:12000],
        "titles_per_platform": titles_per,
        "timeout_seconds": timeout_seconds,
        "disclaimer": disclaimer[:240],
        "platforms": platforms,
    }


async def get_keyword_expansion_config(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        await invalidate_runtime_settings_cache()
    values = await _load_runtime_settings()
    return _build_keyword_expansion_config(values)


async def get_ai_runtime_config(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        await invalidate_runtime_settings_cache()
    values = await _load_runtime_settings()
    return _build_ai_runtime_config(values)


async def get_diagnostic_rule_config(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        await invalidate_runtime_settings_cache()
    values = await _load_runtime_settings()
    return _build_diagnostic_rule_config(values)


async def get_solution_template_config(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        await invalidate_runtime_settings_cache()
    values = await _load_runtime_settings()
    return _build_solution_template_config(values)


async def get_solution_channel_config(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        await invalidate_runtime_settings_cache()
    values = await _load_runtime_settings()
    return _build_solution_channel_config(values)


async def get_frontend_module_config(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        await invalidate_runtime_settings_cache()
    values = await _load_runtime_settings()
    return _build_frontend_module_config(values)


async def get_homepage_runtime_config(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        await invalidate_runtime_settings_cache()
    values = await _load_runtime_settings()
    return _build_homepage_runtime_config(values)


async def get_ai_usage_policy_config(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        await invalidate_runtime_settings_cache()
    values = await _load_runtime_settings()
    policy = _build_ai_usage_policy_config(values)
    # 演示环境可通过环境变量强制开放匿名 AI（不改库内策略记录）
    try:
        from app.core.config import settings

        if bool(getattr(settings, "GEORANK_ALLOW_ANONYMOUS_AI", False)):
            policy = {**policy, "allow_anonymous_ai_usage": True}
    except Exception:
        pass
    return policy
