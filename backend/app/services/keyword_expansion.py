"""
拓词服务
- 先推断关键词背后的业务画像
- 再按画像生成 8 维拓词结果
- AI 失败或输出不匹配时回退到画像化模板
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from typing import Any

from app.services.ai_client import ai_client

DIMENSIONS = [
    {
        "key": "semantic",
        "name": "语义拓展",
        "icon": "hub",
        "description": "同义/近义、行业术语、实体别名与可检索长尾变体（保持实体一致）",
    },
    {
        "key": "scenario",
        "name": "场景覆盖",
        "icon": "category",
        "description": "真实使用场景与任务语境（像用户会搜的完整说法）",
    },
    {
        "key": "commercial",
        "name": "商业意图",
        "icon": "shopping_cart",
        "description": "采购、比价、选型、报价、合作等转化向查询",
    },
    {
        "key": "ranking",
        "name": "推荐榜单",
        "icon": "emoji_events",
        "description": "推荐、排行、哪家好、选型清单类比较查询",
    },
    {
        "key": "review",
        "name": "产品评测",
        "icon": "rate_review",
        "description": "评测、对比、优缺点、值不值、避坑类查询",
    },
    {
        "key": "brand",
        "name": "品牌关联",
        "icon": "business",
        "description": "品牌/栏目/产品名、竞品与替代方案关联词",
    },
    {
        "key": "question",
        "name": "问答长尾",
        "icon": "help",
        "description": "问题式自然语言查询（如何/怎么/为什么/是否/有哪些）",
    },
    {
        "key": "technical",
        "name": "技术方案",
        "icon": "engineering",
        "description": "落地方法、流程、指标、集成与实施类专业查询",
    },
]

DIMENSION_MAP = {item["key"]: item for item in DIMENSIONS}

PROFILE_LIBRARY = {
    "enterprise_service": {
        "name": "企业服务",
        "company_hint": "提供“{seed}”相关软件、咨询或服务的企业",
        "business_model": "偏 B2B / 企业服务 / 解决方案导向",
        "target_users": ["企业负责人", "市场团队", "增长团队", "内容团队"],
        "keyword_strategy": "优先覆盖采购选型、方案对比、落地实施与可测量成效；少用空泛平台/工具堆砌。",
        "blocked_terms": [],
        "templates": {
            "semantic": [
                "{s}",
                "{s}方法论",
                "{s}策略",
                "{s}实践指南",
                "企业{s}",
                "{s}能力建设",
                "{s}内容工程",
                "{s}可见性优化",
                "{s}答案引擎优化",
                "{s}知识库建设",
            ],
            "scenario": [
                "官网怎么介绍{s}",
                "内容团队怎么写{s}",
                "市场部怎么落地{s}",
                "B2B 获客怎么用{s}",
                "{s}怎么提升 AI 搜索可见性",
                "{s}行业专题页怎么写",
                "{s} FAQ 怎么建",
                "{s}案例页写什么",
                "传媒机构怎么用{s}",
                "咨询项目怎么交付{s}",
            ],
            "commercial": [
                "{s}服务报价",
                "{s}多少钱",
                "{s}采购指南",
                "{s}选型标准",
                "{s}试用评估",
                "{s}哪个服务商好",
                "{s}实施费用",
                "{s}预算怎么定",
                "{s}合作方案",
                "{s}ROI 怎么算",
            ],
            "ranking": [
                "{s}服务商推荐",
                "{s}工具对比榜",
                "国产{s}推荐",
                "{s}哪家更适合中小企业",
                "{s}头部厂商对比",
                "{s}选型清单",
                "{s}排行怎么看",
                "适合传媒的{s}方案",
                "{s}优选名单",
                "{s}TOP 对比",
            ],
            "review": [
                "{s}实测复盘",
                "{s}优缺点",
                "{s}案例拆解",
                "{s}选型避坑",
                "{s}值不值得做",
                "{s}效果怎么验证",
                "{s}和 SEO 区别评测",
                "{s}落地难点",
                "{s}口碑怎么样",
                "{s}失败案例",
            ],
            "brand": [
                "{s}服务商",
                "{s}解决方案厂商",
                "{s}竞品对比",
                "{s}替代方案",
                "{s}官网能力",
                "{s}产品矩阵",
                "{s}合作伙伴生态",
                "{s}咨询公司",
                "{s}开源方案",
                "{s}自建还是采购",
            ],
            "question": [
                "什么是{s}",
                "如何开始做{s}",
                "{s}怎么落地",
                "为什么企业需要{s}",
                "{s}有效吗怎么验证",
                "{s}适合哪些行业",
                "{s}有哪些关键步骤",
                "{s}常见误区有哪些",
                "如何评估{s}效果",
                "{s}和 SEO 怎么配合",
            ],
            "technical": [
                "{s}实施路线图",
                "{s}内容工作流",
                "{s}知识库结构",
                "{s}Schema 清单",
                "{s}监测指标",
                "{s}与 CMS 对接",
                "{s}事实卡模板",
                "{s}发布与分发流程",
                "{s}答案抽样方法",
                "{s}自动化流水线",
            ],
        },
    },
    "consumer_education": {
        "name": "教育培训",
        "company_hint": "提供“{seed}”相关课程、辅导或教学服务的教育机构",
        "business_model": "偏 C 端教育服务 / 课程销售 / 家长决策",
        "target_users": ["学生", "家长", "老师", "教培机构运营者"],
        "keyword_strategy": "优先覆盖提分场景、家长决策、课程对比和机构口碑。",
        "blocked_terms": ["b2b", "saas", "市场部", "内容团队", "增长团队", "企业级"],
        "templates": {
            "semantic": ["{s}", "在线{s}", "一对一{s}", "{s}课程", "{s}机构", "{s}老师", "{s}培训", "{s}提分", "{s}家教", "{s}班"],
            "scenario": [
                "学生怎么选{s}",
                "家长怎么找{s}",
                "线上怎么学{s}",
                "小初高适合什么{s}",
                "培优场景用{s}",
                "提分怎么靠{s}",
                "考前冲刺学{s}",
                "寒暑假适合学{s}",
                "升学备考用{s}",
                "校内同步怎么配合{s}",
            ],
            "commercial": ["{s}价格", "{s}收费", "{s}哪家好", "{s}机构推荐", "{s}老师推荐", "{s}试听", "{s}课程报价", "{s}报名", "{s}怎么选", "{s}排名"],
            "ranking": ["最佳{s}", "{s}机构推荐", "{s}老师推荐", "{s}平台推荐", "口碑好的{s}", "{s}排行榜", "本地{s}推荐", "线上{s}推荐", "{s}优选", "{s}哪家强"],
            "review": ["{s}机构评测", "{s}平台对比", "{s}课程测评", "{s}优缺点", "{s}体验", "{s}口碑", "{s}家长评价", "{s}实测", "{s}效果怎么样", "{s}值不值"],
            "brand": ["{s}机构", "{s}老师", "{s}课程品牌", "{s}培训机构", "{s}学习平台", "{s}替代课程", "{s}品牌", "{s}官网", "{s}名师", "{s}教材"],
            "question": ["什么是{s}", "{s}适合谁", "{s}怎么选", "{s}怎么上课", "{s}有效吗", "{s}多少钱", "{s}和家教区别", "{s}有哪些方式", "{s}如何提分", "{s}多久见效"],
            "technical": ["{s}课程体系", "{s}教学方案", "{s}题库", "{s}学习计划", "{s}直播课", "{s}录播课", "{s}课后练习", "{s}测评系统", "{s}班型设计", "{s}教学工具"],
        },
    },
    "local_service": {
        "name": "本地服务",
        "company_hint": "提供“{seed}”相关上门、到店或同城服务的本地商家",
        "business_model": "偏本地线索转化 / 到店或上门服务",
        "target_users": ["本地居民", "家庭用户", "附近需求用户"],
        "keyword_strategy": "优先覆盖同城、附近、预约、价格和门店口碑。",
        "blocked_terms": ["b2b", "saas", "市场部", "内容团队", "增长团队"],
        "templates": {
            "semantic": ["{s}", "同城{s}", "上门{s}", "{s}服务", "{s}预约", "{s}方案", "{s}门店", "{s}师傅", "{s}公司", "{s}平台"],
            "scenario": [
                "附近哪里有{s}",
                "家里需要找{s}",
                "同城怎么预约{s}",
                "周末适合做{s}",
                "急用怎么找{s}",
                "到店做{s}要注意什么",
                "上门请{s}靠谱吗",
                "本地生活怎么选{s}",
                "门店咨询{s}",
                "家庭日常用不用请{s}",
            ],
            "commercial": ["{s}价格", "{s}收费", "{s}多少钱", "{s}预约", "{s}报价", "{s}哪家好", "{s}服务电话", "{s}优惠", "{s}套餐", "{s}附近推荐"],
            "ranking": ["同城{s}推荐", "{s}排行榜", "附近{s}哪家好", "{s}优选", "{s}口碑榜", "{s}门店推荐", "{s}服务商推荐", "{s}品牌推荐", "{s}Top10", "本地{s}推荐"],
            "review": ["{s}测评", "{s}对比", "{s}口碑", "{s}评价", "{s}体验", "{s}值不值", "{s}优缺点", "{s}实测", "{s}案例", "{s}避坑"],
            "brand": ["{s}门店", "{s}公司", "{s}品牌", "{s}服务商", "{s}官网", "{s}预约平台", "{s}替代商家", "{s}附近门店", "{s}加盟", "{s}联系电话"],
            "question": ["{s}怎么预约", "{s}多少钱", "{s}多久上门", "{s}适合谁", "{s}怎么选", "{s}有哪些流程", "{s}靠谱吗", "{s}注意什么", "{s}有哪些坑", "{s}哪里找"],
            "technical": ["{s}流程", "{s}服务标准", "{s}预约系统", "{s}门店管理", "{s}工单", "{s}售后方案", "{s}服务清单", "{s}操作规范", "{s}服务时效", "{s}实施步骤"],
        },
    },
    "ecommerce_brand": {
        "name": "电商品牌",
        "company_hint": "围绕“{seed}”进行销售或种草转化的品牌与电商业务",
        "business_model": "偏品牌电商 / 渠道转化 / 内容种草",
        "target_users": ["消费者", "品牌团队", "电商运营"],
        "keyword_strategy": "优先覆盖种草、转化、比价、榜单和平台场景。",
        "blocked_terms": ["b2b", "市场部", "内容团队"],
        "templates": {
            "semantic": ["{s}", "{s}品牌", "{s}产品", "{s}套装", "{s}旗舰店", "{s}好物", "{s}平替", "{s}推荐", "{s}测评", "{s}使用感受"],
            "scenario": [
                "电商详情页怎么写{s}",
                "直播间怎么讲{s}",
                "小红书怎么种草{s}",
                "抖音怎么推{s}",
                "{s}新品怎么卖",
                "{s}适合当礼物吗",
                "节日送礼选{s}",
                "{s}为什么会复购",
                "达人怎么推荐{s}",
                "开箱种草{s}",
            ],
            "commercial": ["{s}价格", "{s}多少钱", "{s}优惠", "{s}折扣", "{s}购买渠道", "{s}旗舰店", "{s}哪家便宜", "{s}怎么选", "{s}礼盒", "{s}返场"],
            "ranking": ["{s}推荐", "{s}排行榜", "最佳{s}", "{s}哪款好", "{s}榜单", "{s}平替推荐", "{s}热门款", "{s}Top10", "{s}口碑榜", "{s}优选"],
            "review": ["{s}评测", "{s}测评", "{s}开箱", "{s}对比", "{s}使用体验", "{s}真实评价", "{s}值不值", "{s}优缺点", "{s}效果", "{s}购买建议"],
            "brand": ["{s}品牌", "{s}旗舰店", "{s}官网", "{s}系列", "{s}竞品", "{s}替代款", "{s}联名", "{s}口碑", "{s}品牌故事", "{s}热卖款"],
            "question": ["{s}值得买吗", "{s}适合谁", "{s}怎么选", "{s}和竞品区别", "{s}哪个系列好", "{s}在哪里买", "{s}怎么用", "{s}会回购吗", "{s}适合什么场景", "{s}有哪些坑"],
            "technical": ["{s}成分", "{s}规格", "{s}材质", "{s}使用方法", "{s}搭配方案", "{s}开箱", "{s}渠道策略", "{s}内容打法", "{s}商品结构", "{s}评价体系"],
        },
    },
    "content_media": {
        "name": "内容媒体",
        "company_hint": "围绕“{seed}”做内容创作、栏目运营、分发或知识付费的媒体机构或创作者",
        "business_model": "偏内容生产 / 栏目运营 / 广告或知识付费 / 社群增长",
        "target_users": ["内容创作者", "媒体编辑", "栏目运营", "知识付费用户"],
        "keyword_strategy": "优先覆盖选题、栏目实体、场景词、问题式长尾与可移交内容生产的词；避免空泛涨粉话术堆砌。",
        "blocked_terms": ["b2b", "saas"],
        "templates": {
            "semantic": [
                "{s}",
                "{s}栏目",
                "{s}专题",
                "{s}解读",
                "{s}知识库",
                "{s}事实卡",
                "{s}权威问答",
                "{s}内容工程",
                "{s}选题库",
                "{s}术语表",
            ],
            "scenario": [
                "广电媒体怎么做{s}",
                "新闻栏目怎么讲{s}",
                "公众号深度稿怎么写{s}",
                "短视频怎么科普{s}",
                "小红书怎么种草{s}",
                "行业白皮书怎么写{s}",
                "突发事件怎么解读{s}",
                "品牌专访聊什么{s}",
                "社群怎么答疑{s}",
                "知识付费课怎么讲{s}",
            ],
            "commercial": [
                "{s}栏目合作报价",
                "{s}商业赞助怎么谈",
                "{s}投放合作",
                "{s}如何变现",
                "{s}课程定价",
                "{s}社群收费模式",
                "{s}品牌定制内容报价",
                "{s}账号商业价值",
                "{s}内容服务价格",
                "{s}接单标准",
            ],
            "ranking": [
                "{s}优质栏目推荐",
                "{s}创作者榜单",
                "{s}课程推荐",
                "{s}案例精选",
                "值得关注的{s}",
                "{s}资源清单",
                "{s}哪家媒体强",
                "{s}选题方向榜",
                "{s}工具推荐给媒体",
                "{s}优选账号",
            ],
            "review": [
                "{s}栏目复盘",
                "{s}内容拆解",
                "{s}值不值得做",
                "{s}优缺点",
                "{s}爆款为何失效",
                "{s}口碑怎么样",
                "{s}案例对比",
                "{s}踩坑记录",
                "{s}传播效果评估",
                "{s}可信度检查",
            ],
            "brand": [
                "{s}官方账号",
                "{s}栏目品牌",
                "{s}主创团队",
                "{s}媒体矩阵",
                "{s}竞品栏目",
                "{s}替代内容源",
                "{s}官网专栏",
                "{s}工作室定位",
                "{s}IP 人设",
                "{s}权威信源",
            ],
            "question": [
                "如何做好{s}",
                "{s}怎么选题才专业",
                "{s}怎么保证事实准确",
                "{s}适合哪些受众",
                "{s}如何持续产出",
                "{s}有哪些常见坑",
                "媒体做{s}从哪开始",
                "{s}如何写答案型文章",
                "{s}值得投入吗",
                "怎样用{s}支撑 GEO",
            ],
            "technical": [
                "{s}选题流程",
                "{s}事实核对清单",
                "{s}答案块结构",
                "{s}分发工作流",
                "{s}排期模板",
                "{s}素材与信源库",
                "{s}FAQ 生产规范",
                "{s}栏目定位方法",
                "{s}效果抽样指标",
                "{s}多平台改编流程",
            ],
        },
    },
    "consumer_electronics": {
        "name": "消费电子",
        "company_hint": "围绕“{seed}”做产品规格、场景与购买决策内容的消费电子品牌或渠道",
        "business_model": "偏 B2C / 消费电子 / 产品参数与购买决策",
        "target_users": ["旅行创作者", "航拍入门用户", "内容运营", "电商选品"],
        "keyword_strategy": "优先覆盖真实使用场景、关键参数、对比选型与购买决策；说法要像用户会搜的完整短语。",
        "blocked_terms": ["b2b", "saas", "市场部", "内容团队", "增长团队", "企业级", "服务商"],
        "templates": {
            "semantic": [
                "{s}",
                "大疆 {s}",
                "{s}航拍无人机",
                "{s}迷你航拍机",
                "{s}规格参数",
                "{s}一英寸大底",
                "{s}便携无人机",
                "{s}入门航拍机",
                "{s}系列怎么区分",
                "{s}产品定位",
            ],
            "scenario": [
                "旅行航拍选 {s}",
                "{s} 夜景航拍怎么拍",
                "{s} 运动跟拍适合吗",
                "城市轻便航拍用 {s}",
                "{s} 竖拍短视频怎么拍",
                "第一次飞 {s} 要注意什么",
                "{s} 户外创作怎么带",
                "周末郊游带 {s}",
                "{s} 人像跟拍场景",
                "便携旅行怎么带 {s}",
            ],
            "commercial": [
                "{s}多少钱",
                "{s}套装怎么选",
                "{s}哪里买靠谱",
                "{s}长续航电池要不要买",
                "{s}配件清单",
                "{s}国行价格",
                "入门航拍预算选{s}",
                "{s}以旧换新值不值",
                "{s}官方商城买还是渠道买",
                "{s}优惠怎么蹲",
            ],
            "ranking": [
                "2026 迷你航拍机推荐",
                "轻便无人机哪款好",
                "入门航拍机怎么选",
                "旅行无人机推荐榜",
                "一英寸 CMOS 迷你机推荐",
                "大疆迷你系列怎么选",
                "249g 档航拍机推荐",
                "夜景航拍机哪款强",
                "便携无人机推荐",
                "{s}在同档里排第几",
            ],
            "review": [
                "{s}评测",
                "{s} vs Mini 4 Pro",
                "{s}优缺点",
                "{s}画质实测",
                "{s}避障体验怎么样",
                "{s}续航实测",
                "{s}图传距离体验",
                "{s}值不值得买",
                "{s}开箱体验",
                "{s}新手上手难不难",
            ],
            "brand": [
                "大疆官网查{s}",
                "DJI Mini 系列对比",
                "{s}竞品对比",
                "DJI Fly 怎么连{s}",
                "DJI Care 要不要买",
                "Mini 4 Pro 升级{s}",
                "大疆迷你航拍机生态",
                "入门航拍选大疆还是竞品",
                "{s}官方配件",
                "{s}售后怎么样",
            ],
            "question": [
                "{s}是什么定位",
                "{s}续航能飞多久",
                "{s}图传能飞多远",
                "{s}晚上能不能避障",
                "{s}防水吗",
                "{s}和 Mini 4 Pro 差在哪",
                "{s}适合新手吗",
                "{s}有多重",
                "{s}内置存储多大",
                "{s}怎么选电池",
            ],
            "technical": [
                "{s}参数怎么读",
                "{s} O4+ 图传是什么",
                "{s} HDR 动态范围怎么理解",
                "{s}避障光照条件",
                "{s}云台角度有多大",
                "{s}飞行前检查清单",
                "{s} App 设置建议",
                "{s}法规与限飞要注意什么",
                "{s}存储与拷卡流程",
                "{s}夜间飞行注意事项",
            ],
        },
    },
}

PROFILE_RULES = [
    ("consumer_education", ["教育", "培训", "课程", "辅导", "数学", "英语", "家教", "提分", "考研", "高考", "留学", "题库", "老师", "小初高"]),
    ("local_service", ["家政", "搬家", "装修", "维修", "保洁", "摄影", "婚礼", "月嫂", "开锁", "搬运", "鲜花", "宠物", "律师", "牙科"]),
    (
        "consumer_electronics",
        [
            "dji",
            "大疆",
            "mini 5",
            "mini5",
            "mini 4",
            "航拍",
            "无人机",
            "云台",
            "图传",
            "避障",
            "消费电子",
            "相机",
            "耳机",
            "手机",
            "笔记本",
            "游戏机",
            "无人机",
        ],
    ),
    ("ecommerce_brand", ["电商", "护肤", "美妆", "服饰", "鞋", "箱包", "食品", "咖啡", "母婴", "礼盒", "面膜", "香水", "零食", "品牌"]),
    (
        "content_media",
        [
            "公众号",
            "短视频",
            "小红书",
            "内容创作",
            "知识付费",
            "个人ip",
            "自媒体",
            "课程博主",
            "社群",
            "涨粉",
            "选题",
            "传媒",
            "广电",
            "栏目",
            "媒体",
            "报道",
            "新闻",
            "记者",
            "编辑",
            "电视台",
            "广播",
        ],
    ),
    ("enterprise_service", ["saas", "crm", "api", "geo", "seo", "服务商", "平台", "系统", "解决方案", "营销", "增长", "运营", "企业", "咨询", "官网优化"]),
]

# 低质堆砌词根：单独出现或仅「种子+该词」时优先过滤
_LOW_QUALITY_SUFFIXES = {
    "平台",
    "工具",
    "系统",
    "引擎",
    "方案",
    "服务",
    "优化",
    "推荐",
    "榜单",
    "排行榜",
    "top10",
    "优选",
    "好物",
    "增长",
    "内容",
}


def normalize_seeds(seeds: list[str]) -> list[str]:
    normalized: list[str] = []
    seen = set()
    for item in seeds:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        if not text or text in seen:
            continue
        normalized.append(text[:40])
        seen.add(text)
        if len(normalized) >= 8:
            break
    return normalized


def _stable_score(seed: str, dimension_key: str, keyword: str, base: int, spread: int) -> int:
    digest = hashlib.md5(f"{seed}|{dimension_key}|{keyword}".encode("utf-8")).hexdigest()
    return max(35, min(99, base + (int(digest[:8], 16) % spread)))


def _infer_keyword_profile(seeds: list[str]) -> dict:
    combined = " ".join(seeds).lower()
    scores = {key: 0 for key in PROFILE_LIBRARY}
    for profile_key, markers in PROFILE_RULES:
        for marker in markers:
            if marker in combined:
                scores[profile_key] += 1

    profile_key = max(scores.items(), key=lambda item: item[1])[0]
    if scores[profile_key] == 0:
        profile_key = "enterprise_service"

    profile = PROFILE_LIBRARY[profile_key]
    primary_seed = seeds[0]
    return {
        "key": profile_key,
        "name": profile["name"],
        "company_hint": profile["company_hint"].format(seed=primary_seed),
        "business_model": profile["business_model"],
        "target_users": profile["target_users"],
        "keyword_strategy": profile["keyword_strategy"],
        "blocked_terms": profile.get("blocked_terms", []),
    }


def _templates_for(profile_key: str, dimension_key: str) -> list[str]:
    profile = PROFILE_LIBRARY.get(profile_key, PROFILE_LIBRARY["enterprise_service"])
    return profile["templates"].get(dimension_key) or PROFILE_LIBRARY["enterprise_service"]["templates"][dimension_key]


def _is_keyword_allowed(profile: dict, keyword: str) -> bool:
    lowered = keyword.lower()
    for token in profile.get("blocked_terms", []):
        if token in lowered:
            return False
    return True


def _is_low_quality_keyword(keyword: str, seed: str, dimension_key: str) -> bool:
    """过滤空泛堆砌、过短、纯符号及跨维度无区分的糙词。"""
    text = re.sub(r"\s+", " ", (keyword or "").strip())
    if len(text) < 2:
        return True
    if re.fullmatch(r"[\W_]+", text, flags=re.UNICODE):
        return True
    # 连续重复片段：如「最佳最佳」「GEOGEO」
    if re.search(r"(.{2,})\1{2,}", text):
        return True
    compact = re.sub(r"\s+", "", text).lower()
    seed_compact = re.sub(r"\s+", "", seed or "").lower()
    if not seed_compact:
        return False
    # 除 semantic 外，禁止输出与种子完全相同的词
    if dimension_key != "semantic" and compact == seed_compact:
        return True
    # 「种子+空泛后缀」且总长过短：如「GEO平台」
    for suffix in _LOW_QUALITY_SUFFIXES:
        if compact == f"{seed_compact}{suffix}" and len(compact) <= len(seed_compact) + 3:
            return True
    # 场景维：禁止「短标签 + 空格 + 种子」硬拼接（如「品牌官网 DJI Mini 5 Pro」）
    if dimension_key == "scenario" and seed and text.endswith(seed):
        prefix = text[: -len(seed)].rstrip(" \t·-—/")
        if prefix and " " in text and len(prefix) <= 12:
            if not any(token in prefix for token in ("怎么", "如何", "选", "用", "写", "拍", "带", "找", "约", "讲", "推", "学")):
                return True
    return False


def _fallback_item(seed: str, dimension_key: str, keyword: str) -> dict:
    recommendation_base = {
        "semantic": 62,
        "scenario": 60,
        "commercial": 58,
        "ranking": 64,
        "review": 61,
        "brand": 63,
        "question": 59,
        "technical": 57,
    }[dimension_key]
    business_base = {
        "semantic": 54,
        "scenario": 60,
        "commercial": 72,
        "ranking": 68,
        "review": 63,
        "brand": 66,
        "question": 52,
        "technical": 58,
    }[dimension_key]
    return {
        "keyword": keyword,
        "recommendation_score": _stable_score(seed, dimension_key, keyword, recommendation_base, 28),
        "business_score": _stable_score(seed, f"{dimension_key}-biz", keyword, business_base, 26),
        "reason": None,
    }


def _fallback_dimension_items(seed: str, profile: dict, dimension_key: str, limit: int = 10) -> list[dict]:
    items: list[dict] = []
    seen = set()
    for template in _templates_for(profile["key"], dimension_key):
        keyword = template.replace("{s}", seed).strip()
        if (
            not keyword
            or keyword in seen
            or not _is_keyword_allowed(profile, keyword)
            or _is_low_quality_keyword(keyword, seed, dimension_key)
        ):
            continue
        seen.add(keyword)
        items.append(_fallback_item(seed, dimension_key, keyword))
        if len(items) >= limit:
            break
    return items


def _fallback_expand(seeds: list[str], profile: dict) -> list[dict]:
    merged: dict[str, list[dict]] = {item["key"]: [] for item in DIMENSIONS}
    seen: dict[str, set[str]] = {item["key"]: set() for item in DIMENSIONS}
    for seed in seeds:
        for dim in DIMENSIONS:
            key = dim["key"]
            for item in _fallback_dimension_items(seed, profile, key):
                keyword = item["keyword"]
                if keyword in seen[key]:
                    continue
                merged[key].append(item)
                seen[key].add(keyword)
                if len(merged[key]) >= 10:
                    break
    return [
        {
            **dim,
            "count": len(merged[dim["key"]]),
            "items": merged[dim["key"]][:10],
        }
        for dim in DIMENSIONS
    ]


def _sanitize_dimension_items(seed: str, dimension_key: str, raw_items: list[dict], profile: dict) -> list[dict]:
    items: list[dict] = []
    seen = set()
    for raw in raw_items or []:
        keyword = re.sub(r"\s+", " ", str(raw.get("keyword") or raw.get("kw") or "").strip())
        if (
            not keyword
            or keyword in seen
            or not _is_keyword_allowed(profile, keyword)
            or _is_low_quality_keyword(keyword, seed, dimension_key)
        ):
            continue
        seen.add(keyword)
        try:
            recommendation = int(raw.get("recommendation_score", raw.get("rec", 0)))
        except Exception:
            recommendation = 0
        try:
            business = int(raw.get("business_score", raw.get("biz", 0)))
        except Exception:
            business = 0
        recommendation = max(35, min(99, recommendation or _stable_score(seed, dimension_key, keyword, 60, 28)))
        business = max(35, min(99, business or _stable_score(seed, f"{dimension_key}-biz", keyword, 58, 26)))
        reason = str(raw.get("reason") or "").strip()[:120] or None
        items.append(
            {
                "keyword": keyword[:80],
                "recommendation_score": recommendation,
                "business_score": business,
                "reason": reason,
            }
        )
        if len(items) >= 10:
            break
    return items


async def _ai_expand(
    seeds: list[str],
    profile: dict,
    provider_override=None,
) -> tuple[list[dict], list[dict]]:
    from app.services.runtime_settings import get_keyword_expansion_config

    config = await get_keyword_expansion_config()
    system = config["system_prompt"]
    titles_per = int(config.get("titles_per_platform") or 3)
    platforms = list(config.get("platforms") or [])
    entity = str(profile.get("name") or seeds[0] or "主体").strip()

    user = json.dumps(
        {
            "seeds": seeds,
            "entity": entity,
            "titles_per_platform": titles_per,
            "profile": {
                "name": profile["name"],
                "company_hint": profile["company_hint"],
                "business_model": profile["business_model"],
                "target_users": profile["target_users"],
                "keyword_strategy": profile["keyword_strategy"],
                "blocked_terms": profile["blocked_terms"],
            },
            "dimensions": [
                {"key": item["key"], "name": item["name"], "description": item["description"]}
                for item in DIMENSIONS
            ],
            "platforms": [
                {
                    "platform": row["platform"],
                    "generation_focus": row.get("generation_focus") or "",
                    "avoid": row.get("avoid") or [],
                }
                for row in platforms
            ],
            "handoff_hint": {
                "consumer": "GEOFlow",
                "expected_use": "每个关键词可独立生成知识约束正文/FAQ/榜单任务；标题建议可作选题",
                "avoid": "空泛词、跨维度重复、把页面 citation 就绪度说成答案引用率、垂类硬套话",
            },
        },
        ensure_ascii=False,
    )
    try:
        raw = await ai_client.complete(
            system,
            user,
            temperature=0.45,
            provider_override=provider_override,
        )
    except Exception as exc:
        raise KeywordProviderCallError("关键词模型调用失败") from exc
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("AI 返回的拓词结果不是有效 JSON")
    payload = json.loads(raw[start:end])
    result: list[dict] = []
    mapping = {
        item.get("key"): item.get("items")
        for item in payload.get("dimensions", [])
        if isinstance(item, dict)
    }

    for dim in DIMENSIONS:
        items = _sanitize_dimension_items(
            seeds[0], dim["key"], mapping.get(dim["key"]) or [], profile
        )
        if not items:
            items = _fallback_dimension_items(seeds[0], profile, dim["key"])
        if not items:
            raise ValueError(f"维度 {dim['key']} 没有生成有效关键词")
        result.append(
            {
                **dim,
                "count": len(items),
                "items": items,
            }
        )

    hints = _sanitize_platform_title_hints(
        payload.get("platform_title_hints"),
        platforms,
        entity=entity,
        titles_per=titles_per,
    )
    return result, hints


def _sanitize_platform_title_hints(
    raw_hints: Any,
    platforms: list[dict],
    *,
    entity: str,
    titles_per: int,
) -> list[dict]:
    by_platform: dict[str, list[str]] = {}
    if isinstance(raw_hints, list):
        for row in raw_hints:
            if not isinstance(row, dict):
                continue
            name = str(row.get("platform") or "").strip()
            if not name:
                continue
            titles_raw = row.get("titles") or row.get("title_hints") or []
            cleaned: list[str] = []
            if isinstance(titles_raw, list):
                for title in titles_raw:
                    text = str(title or "").strip()
                    if not text or text in cleaned:
                        continue
                    cleaned.append(text[:120])
                    if len(cleaned) >= titles_per:
                        break
            by_platform[name] = cleaned

    out: list[dict] = []
    for row in platforms:
        name = str(row.get("platform") or "").strip()
        if not name:
            continue
        titles = list(by_platform.get(name) or [])
        # 不足时不补模板假标题（失败策略 A）；有部分则截断到 titles_per
        titles = titles[:titles_per]
        out.append(
            {
                "platform": name,
                "generation_focus": row.get("generation_focus") or "",
                "avoid": list(row.get("avoid") or []),
                "titles": titles,
            }
        )
    return out


def _build_summary(dimensions: list[dict]) -> dict:
    all_items = [item for dim in dimensions for item in dim["items"]]
    total = len(all_items)
    if not total:
        return {
            "total_keywords": 0,
            "average_recommendation_score": 0,
            "average_business_score": 0,
            "high_recommendation_ratio": 0,
            "high_business_ratio": 0,
        }
    avg_rec = round(sum(item["recommendation_score"] for item in all_items) / total)
    avg_biz = round(sum(item["business_score"] for item in all_items) / total)
    high_rec = round(sum(1 for item in all_items if item["recommendation_score"] >= 80) / total * 100)
    high_biz = round(sum(1 for item in all_items if item["business_score"] >= 80) / total * 100)
    return {
        "total_keywords": total,
        "average_recommendation_score": avg_rec,
        "average_business_score": avg_biz,
        "high_recommendation_ratio": high_rec,
        "high_business_ratio": high_biz,
    }


class KeywordProviderCallError(RuntimeError):
    """The provider call did not return a usable response."""


async def expand_keywords_with_status(
    seeds: list[str],
    provider_override=None,
) -> tuple[dict, bool]:
    from app.services.runtime_settings import get_keyword_expansion_config

    normalized = normalize_seeds(seeds)
    if not normalized:
        raise ValueError("请至少输入一个关键词")

    profile = _infer_keyword_profile(normalized)
    config = await get_keyword_expansion_config()
    timeout = float(config.get("timeout_seconds") or 20)
    platforms_meta = [
        {
            "platform": row["platform"],
            "generation_focus": row.get("generation_focus") or "",
            "avoid": list(row.get("avoid") or []),
        }
        for row in (config.get("platforms") or [])
    ]
    provider_succeeded = True
    platform_title_hints: list[dict] = []

    try:
        dimensions, platform_title_hints = await asyncio.wait_for(
            _ai_expand(normalized, profile, provider_override=provider_override),
            timeout=timeout,
        )
    except Exception:
        if provider_override is not None:
            raise
        provider_succeeded = False
        dimensions = _fallback_expand(normalized, profile)
        # 失败策略 A：标题建议诚实为空，不回填前端模板
        platform_title_hints = [
            {
                "platform": row["platform"],
                "generation_focus": row.get("generation_focus") or "",
                "avoid": list(row.get("avoid") or []),
                "titles": [],
            }
            for row in platforms_meta
        ]

    return {
        "seeds": normalized,
        "profile": {
            "name": profile["name"],
            "company_hint": profile["company_hint"],
            "business_model": profile["business_model"],
            "target_users": profile["target_users"],
            "keyword_strategy": profile["keyword_strategy"],
        },
        "dimensions": dimensions,
        "summary": _build_summary(dimensions),
        "platform_title_hints": platform_title_hints,
        "ai_focus": {
            "disclaimer": config.get("disclaimer") or "",
            "platforms": [row["platform"] for row in platforms_meta],
            "items": platforms_meta,
        },
    }, provider_succeeded


async def expand_keywords(seeds: list[str], provider_override=None) -> dict:
    payload, _ = await expand_keywords_with_status(
        seeds,
        provider_override=provider_override,
    )
    return payload
