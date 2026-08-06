"""拓词可选知识库：事实卡 brief + 切片检索 + owns 硬过滤。"""
from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_engine import KnowledgeDocument

CARD_TYPES = frozenset({"identity", "owns", "alias", "angle", "forbidden", "competitor"})

# 隶属两端同现时，这些模式视为自伤交叉
_OWNS_SELF_HARM_PATTERNS = (
    re.compile(r"怎么报道"),
    re.compile(r"如何报道"),
    re.compile(r"联动合作"),
    re.compile(r"联合投放"),
    re.compile(r"对.{0,12}的报道怎么样"),
    re.compile(r"报道怎么样"),
)


def empty_brief() -> dict[str, Any]:
    return {
        "entities": [],
        "owns_edges": [],
        "alias_groups": [],
        "competitors": [],
        "forbidden": [],
        "angles": [],
        "cards_used": 0,
        "rule": (
            "关系以本 brief 为准；owns 表示父机构⊃子栏目/产品；"
            "禁止对 owns 两端写互报/联动合作；竞品仅用于对比/替代。"
        ),
    }


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            s = str(item or "").strip()
            if s:
                out.append(s)
        return out
    return []


def parse_fact_cards(cards: list[Any] | None) -> dict[str, Any]:
    """从 fact_cards 列表解析 knowledge_entity_brief。"""
    brief = empty_brief()
    if not cards:
        return brief

    entities: dict[str, dict[str, Any]] = {}
    owns: list[dict[str, str]] = []
    alias_groups: list[list[str]] = []
    competitors: list[str] = []
    forbidden: list[str] = []
    angles: list[str] = []
    used = 0

    def ensure_entity(name: str, *, role: str | None = None) -> None:
        key = (name or "").strip()
        if not key:
            return
        row = entities.setdefault(key, {"name": key, "role": "other", "aliases": []})
        if role and row["role"] in {"other", ""}:
            row["role"] = role

    for raw in cards:
        if not isinstance(raw, dict):
            continue
        used += 1
        ctype = str(raw.get("card_type") or "").strip().lower()
        entity = str(raw.get("entity_name") or "").strip()
        related = str(raw.get("related_entity") or "").strip()
        relation = str(raw.get("relation") or "").strip().lower()
        claim = str(raw.get("claim") or "").strip()
        aliases = _as_list(raw.get("aliases"))
        forb = _as_list(raw.get("forbidden_phrasing"))
        angle = str(raw.get("angle") or "").strip()

        if ctype not in CARD_TYPES:
            # 无 card_type 时：含「隶属/旗下」则当 owns；否则当 identity
            if entity and related and ("隶属" in claim or "旗下" in claim or relation == "owns"):
                ctype = "owns"
            elif entity:
                ctype = "identity"
            else:
                continue

        if ctype == "identity":
            role = "organization" if related == "" and ("广电" in entity or "集团" in entity or "报业" in entity) else "other"
            if "栏目" in claim or "节目" in claim or (related and "旗下" in claim):
                role = "product_or_column"
            if entity and ("广电" in entity or "集团" in entity or "报业" in entity or "新闻网" in entity):
                role = "organization"
            if entity in {"第一现场"} or "栏目" in "".join(aliases):
                role = "product_or_column"
            ensure_entity(entity, role=role)
            if aliases:
                entities[entity]["aliases"] = sorted(
                    set(entities[entity].get("aliases") or []) | set(aliases)
                )
                alias_groups.append([entity, *[a for a in aliases if a != entity]])

        elif ctype == "owns" or relation == "owns":
            child = entity
            parent = related
            if child and parent:
                owns.append({"parent": parent, "child": child})
                ensure_entity(parent, role="organization")
                ensure_entity(child, role="product_or_column")

        elif ctype == "alias":
            ensure_entity(entity, role="organization" if "广电" in entity else "other")
            if aliases:
                entities[entity]["aliases"] = sorted(
                    set(entities[entity].get("aliases") or []) | set(aliases)
                )
                alias_groups.append([entity, *[a for a in aliases if a != entity]])

        elif ctype == "angle":
            label = angle or claim
            if label:
                angles.append(label)
            if entity:
                ensure_entity(entity)

        elif ctype == "forbidden":
            forbidden.extend(forb)
            if claim and "禁止" in claim:
                # 从 claim 抽不到列表时仍保留 phrasing 字段
                pass

        elif ctype == "competitor":
            if entity:
                competitors.append(entity)
                ensure_entity(entity, role="organization")
                if aliases:
                    entities[entity]["aliases"] = sorted(
                        set(entities[entity].get("aliases") or []) | set(aliases)
                    )

        forbidden.extend(forb)

    # 去重
    uniq_owns = []
    seen_owns = set()
    for edge in owns:
        key = (edge["parent"], edge["child"])
        if key in seen_owns:
            continue
        seen_owns.add(key)
        uniq_owns.append(edge)

    brief["entities"] = list(entities.values())
    brief["owns_edges"] = uniq_owns
    brief["alias_groups"] = alias_groups
    brief["competitors"] = sorted(set(competitors))
    brief["forbidden"] = sorted(set(forbidden))
    brief["angles"] = angles[:12]
    brief["cards_used"] = used
    return brief


def owns_pair_set(brief: dict[str, Any] | None) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for edge in (brief or {}).get("owns_edges") or []:
        parent = str(edge.get("parent") or "").strip()
        child = str(edge.get("child") or "").strip()
        if parent and child:
            pairs.add((parent, child))
            pairs.add((child, parent))
    return pairs


def competitor_names(brief: dict[str, Any] | None) -> set[str]:
    return {str(x).strip() for x in ((brief or {}).get("competitors") or []) if str(x).strip()}


def is_owns_related_pair(a: str, b: str, brief: dict[str, Any] | None) -> bool:
    if not a or not b:
        return False
    return (a, b) in owns_pair_set(brief)


def is_competitor_pair(a: str, b: str, brief: dict[str, Any] | None) -> bool:
    comps = competitor_names(brief)
    if not comps:
        return False
    return (a in comps and b not in comps) or (b in comps and a not in comps)


def is_owns_self_harm_keyword(keyword: str, brief: dict[str, Any] | None) -> bool:
    """owns 两端同现 + 自伤模式 → True。"""
    text = keyword or ""
    if not text or not brief:
        return False
    edges = brief.get("owns_edges") or []
    for edge in edges:
        parent = str(edge.get("parent") or "")
        child = str(edge.get("child") or "")
        if not parent or not child:
            continue
        if parent in text and child in text:
            for pat in _OWNS_SELF_HARM_PATTERNS:
                if pat.search(text):
                    return True
    # 禁语字面命中
    for phrase in brief.get("forbidden") or []:
        if phrase and phrase in text:
            # 仅当禁语是完整糙词模板或强口径时过滤；短词「全国第一」等整句含则滤
            if len(phrase) >= 4 and phrase in text:
                return True
    return False


def merge_brief_into_role_hints(hints: list[dict], brief: dict[str, Any] | None) -> list[dict]:
    """用 brief 纠正/增强 seed_role_hints。"""
    if not brief or not hints:
        return hints
    by_name = {
        str(e.get("name") or ""): e
        for e in (brief.get("entities") or [])
        if e.get("name")
    }
    child_to_parent = {
        str(e.get("child") or ""): str(e.get("parent") or "")
        for e in (brief.get("owns_edges") or [])
        if e.get("child") and e.get("parent")
    }
    alias_of: dict[str, str] = {}
    for group in brief.get("alias_groups") or []:
        members = [str(x) for x in group if str(x).strip()]
        if len(members) < 2:
            continue
        primary = members[0]
        for m in members[1:]:
            alias_of[m] = primary

    out = []
    for hint in hints:
        row = dict(hint)
        seed = str(row.get("seed") or "")
        ent = by_name.get(seed)
        if ent and ent.get("role") in {"organization", "product_or_column"}:
            row["hint_role"] = ent["role"]
            row["hint_gloss"] = (
                "知识库标定：机构主体"
                if ent["role"] == "organization"
                else "知识库标定：栏目/产品"
            )
        if seed in child_to_parent:
            row["hint_role"] = "product_or_column"
            row["of"] = child_to_parent[seed]
            row["hint_gloss"] = f"知识库：隶属于「{child_to_parent[seed]}」"
        if seed in alias_of:
            row["hint_role"] = "alias"
            row["alias_of"] = alias_of[seed]
            row["hint_gloss"] = f"知识库别名，同实体「{alias_of[seed]}」"
        out.append(row)
    return out


def owns_cross_templates(dimension_key: str) -> list[str]:
    """机构×自有栏目的合法交叉模板。"""
    by_dim = {
        "semantic": ["{a}旗下{b}", "{a}·{b}栏目"],
        "scenario": ["{a}如何运营{b}", "围绕{a}做{b}内容", "{b}栏目怎么做民生现场"],
        "commercial": ["{a}{b}栏目合作报价", "{b}商业赞助怎么谈"],
        "ranking": ["{a}优质栏目{b}", "值得关注的{a}栏目{b}"],
        "review": ["{a}旗下{b}表现如何", "{b}栏目定位怎么样"],
        "brand": ["{a}旗下{b}", "{b}和{a}什么关系"],
        "question": ["{a}的{b}是什么", "如何理解{a}与{b}的隶属关系"],
        "technical": ["{a}如何沉淀{b}知识库", "{a}{b}选题怎么结构化"],
    }
    return by_dim.get(dimension_key) or by_dim["semantic"]


def competitor_cross_templates(dimension_key: str) -> list[str]:
    by_dim = {
        "semantic": ["{a}与{b}怎么区分"],
        "scenario": ["选{a}还是{b}看本地资讯"],
        "commercial": ["{a}和{b}投放怎么选"],
        "ranking": ["{a}和{b}哪个性价比高"],
        "review": ["{a}对比{b}怎么样"],
        "brand": ["{a}和{b}什么关系", "{a}相对{b}的差异"],
        "question": ["{a}和{b}有什么区别"],
        "technical": ["{a}与{b}内容矩阵怎么对照"],
    }
    return by_dim.get(dimension_key) or by_dim["semantic"]


async def load_knowledge_context(
    db: AsyncSession,
    *,
    kb_id: uuid.UUID,
    seeds: list[str],
    chunk_limit: int = 6,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """返回 (brief, snippets, meta)。"""
    docs = list(
        (
            await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)
            )
        )
        .scalars()
        .all()
    )
    cards: list[Any] = []
    for doc in docs:
        if (doc.review_state or "") == "retired":
            continue
        for card in doc.fact_cards or []:
            cards.append(card)
    brief = parse_fact_cards(cards)

    snippets: list[dict[str, Any]] = []
    try:
        from app.services.content_engine import search_chunks

        query = " ".join(seeds[:5]) or "媒体 栏目"
        snippets = await search_chunks(
            db,
            kb_id=kb_id,
            query=query,
            limit=chunk_limit,
            apply_geo_filter=True,
        )
    except Exception:
        snippets = []

    meta = {
        "kb_id": str(kb_id),
        "cards_used": int(brief.get("cards_used") or 0),
        "chunks_used": len(snippets),
        "owns_edges": len(brief.get("owns_edges") or []),
        "competitors": list(brief.get("competitors") or []),
    }
    return brief, snippets, meta
