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
from app.services.geo_prompt_rules import GEO_TITLE_GATE_BRIEF, is_geo_title_acceptable

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
    """规范化种子：拆分英文/中文分号与逗号，去重，最多 8 个。"""
    normalized: list[str] = []
    seen = set()
    for item in seeds:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        if not text:
            continue
        parts = re.split(r"[;；,，\n\r\t]+", text)
        for part in parts:
            piece = re.sub(r"\s+", " ", (part or "").strip())
            if not piece or piece in seen:
                continue
            # 残留分隔符的整串不可作为种子（避免「A;B;C栏目」式拼接）
            if re.search(r"[;；]", piece):
                continue
            normalized.append(piece[:40])
            seen.add(piece)
            if len(normalized) >= 8:
                return normalized
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
    seed_label = "、".join(seeds[:5]) if seeds else ""
    return {
        "key": profile_key,
        "name": profile["name"],
        "company_hint": profile["company_hint"].format(seed=seed_label),
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
    # 分号残留 = 多种子未拆开就被模板粘在一起
    if ";" in text or "；" in text:
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


def _normalize_seed_key(text: str) -> str:
    """归一化种子便于别名判断（空格、大小写、大疆↔DJI）。"""
    compact = re.sub(r"\s+", "", (text or "").lower())
    return compact.replace("大疆", "dji")


def _seed_core_token(text: str) -> str:
    """去掉常见属性后缀后的主体串，用于识别「产品 + 续航」类近亲种子。"""
    core = _normalize_seed_key(text)
    for suffix in (
        "续航",
        "价格",
        "报价",
        "评测",
        "怎么样",
        "多少钱",
        "参数",
        "规格",
        "套装",
        "配件",
        "图传",
        "避障",
    ):
        if core.endswith(suffix) and len(core) > len(suffix) + 2:
            core = core[: -len(suffix)]
    return core


def _seeds_are_near_duplicates(a: str, b: str) -> bool:
    """中英品牌名、同款别名、或「产品+属性」近亲 → 不可做关系型交叉。"""
    ka, kb = _normalize_seed_key(a), _normalize_seed_key(b)
    if not ka or not kb:
        return False
    if ka == kb or ka in kb or kb in ka:
        return True
    ca, cb = _seed_core_token(a), _seed_core_token(b)
    if ca and cb and (ca == cb or ca in cb or cb in ca):
        return True
    return False


def _relation_seed_pairs(seeds: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for i, a in enumerate(seeds):
        for b in seeds[i + 1 :]:
            if _seeds_are_near_duplicates(a, b):
                continue
            pairs.append((a, b))
    return pairs


def _cross_templates_for(profile_key: str, dimension_key: str) -> list[str]:
    """按画像选择交叉模板；消费电子禁用「报道/栏目/旗下」等媒体硬套。"""
    media_like = profile_key in {"content_media", "enterprise_service"}
    if media_like:
        by_dim = {
            "semantic": ["{a}与{b}", "{a}·{b}"],
            "scenario": ["{a}怎么报道{b}", "{a}栏目怎么讲{b}", "围绕{a}做{b}内容"],
            "commercial": ["{a}与{b}联动合作", "{a}{b}联合投放"],
            "ranking": ["{a}相关的{b}推荐", "值得关注的{a}与{b}"],
            "review": ["{a}对{b}的报道怎么样", "{b}在{a}表现如何"],
            "brand": ["{a}旗下{b}", "{b}和{a}什么关系"],
            "question": ["{a}的{b}是什么", "{b}和{a}有什么区别", "如何理解{a}与{b}"],
            "technical": ["{a}如何沉淀{b}知识库", "{a}{b}选题怎么结构化"],
        }
    else:
        # 消费电子 / 教育 / 本地等：仅在真·不同实体时用温和交叉；别名对不会走到这里
        by_dim = {
            "semantic": ["{a}与{b}怎么区分"],
            "scenario": ["选{a}还是{b}", "{a}和{b}一起怎么用"],
            "commercial": ["{a}和{b}怎么搭配买"],
            "ranking": ["{a}和{b}哪个性价比高"],
            "review": ["{a}对比{b}怎么样"],
            "brand": ["{a}和{b}什么关系"],
            "question": ["{a}和{b}有什么区别", "如何在{a}与{b}之间选择"],
            "technical": ["{a}与{b}参数怎么对照"],
        }
    return by_dim.get(dimension_key) or by_dim["semantic"]


def _cross_seed_items(seeds: list[str], profile: dict, dimension_key: str) -> list[dict]:
    """多种子交叉：跳过别名/近亲对；模板跟画像/知识库隶属走，避免媒体话术套到消费电子。"""
    from app.services.keyword_kb_context import (
        competitor_cross_templates,
        is_competitor_pair,
        is_owns_related_pair,
        is_owns_self_harm_keyword,
        owns_cross_templates,
    )

    pairs = _relation_seed_pairs(seeds)
    if not pairs:
        return []
    brief = profile.get("knowledge_brief") if isinstance(profile.get("knowledge_brief"), dict) else None
    default_templates = _cross_templates_for(str(profile.get("key") or ""), dimension_key)
    items: list[dict] = []
    seen: set[str] = set()
    for a, b in pairs:
        if brief and is_owns_related_pair(a, b, brief):
            templates = owns_cross_templates(dimension_key)
        elif brief and is_competitor_pair(a, b, brief):
            templates = competitor_cross_templates(dimension_key)
        else:
            templates = default_templates
        for template in templates:
            keyword = template.format(a=a, b=b).strip()
            if (
                not keyword
                or keyword in seen
                or not _is_keyword_allowed(profile, keyword)
                or _is_low_quality_keyword(keyword, a, dimension_key)
                or is_owns_self_harm_keyword(keyword, brief)
            ):
                continue
            seen.add(keyword)
            items.append(_fallback_item(f"{a}+{b}", dimension_key, keyword))
            if len(items) >= 4:
                return items
    return items


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
    result: list[dict] = []
    for dim in DIMENSIONS:
        key = dim["key"]
        collected: list[dict] = []
        seen: set[str] = set()
        # 交叉短语优先占席，再按各种子模板扩，最后均衡截断
        for item in _cross_seed_items(seeds, profile, key):
            keyword = item["keyword"]
            if keyword in seen:
                continue
            seen.add(keyword)
            collected.append(item)
        for seed in seeds:
            for item in _fallback_dimension_items(seed, profile, key, limit=10):
                keyword = item["keyword"]
                if keyword in seen:
                    continue
                seen.add(keyword)
                collected.append(item)
        items = _ensure_multi_seed_coverage(collected, seeds, profile, key, limit=10)
        result.append(
            {
                **dim,
                "count": len(items),
                "items": items,
            }
        )
    return result


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def _keyword_mentions_seed(keyword: str, seed: str) -> bool:
    kw = _compact_text(keyword)
    sd = _compact_text(seed)
    if not kw or not sd:
        return False
    return sd in kw or kw in sd


def _matching_seed_for_keyword(keyword: str, seeds: list[str]) -> str:
    """优先匹配词面中出现的种子，便于多种子时的质量过滤。"""
    if not seeds:
        return ""
    for seed in seeds:
        if _keyword_mentions_seed(keyword, seed):
            return seed
    return seeds[0]


def _is_low_quality_for_seeds(
    keyword: str,
    seeds: list[str],
    dimension_key: str,
    profile: dict | None = None,
) -> bool:
    from app.services.keyword_kb_context import is_owns_self_harm_keyword

    if _is_alias_cross_nonsense(keyword, seeds):
        return True
    brief = None
    if isinstance(profile, dict) and isinstance(profile.get("knowledge_brief"), dict):
        brief = profile.get("knowledge_brief")
    if is_owns_self_harm_keyword(keyword, brief):
        return True
    seed = _matching_seed_for_keyword(keyword, seeds)
    return _is_low_quality_keyword(keyword, seed, dimension_key)


def _is_alias_cross_nonsense(keyword: str, seeds: list[str]) -> bool:
    """同一实体的别名/近亲同时出现在一条词里 → 糙词（含无标记的粘连）。"""
    text = keyword or ""
    if not text:
        return False
    for i, a in enumerate(seeds):
        for b in seeds[i + 1 :]:
            if not _seeds_are_near_duplicates(a, b):
                continue
            if a in text and b in text:
                return True
    return False


def _ensure_multi_seed_coverage(
    items: list[dict],
    seeds: list[str],
    profile: dict,
    dimension_key: str,
    *,
    limit: int = 10,
    min_per_seed: int = 2,
) -> list[dict]:
    """多种子时：若某种子在该维几乎未出现，用模板词回填，避免只扩 seeds[0]。"""
    if len(seeds) <= 1:
        return items[:limit]

    merged = list(items[:limit])
    seen = {str(item.get("keyword") or "") for item in merged}
    min_needed = min(min_per_seed, max(1, limit // len(seeds)))

    def coverage_count(seed: str) -> int:
        return sum(1 for item in merged if _keyword_mentions_seed(str(item.get("keyword") or ""), seed))

    for seed in seeds:
        if coverage_count(seed) >= min_needed:
            continue
        for fb in _fallback_dimension_items(seed, profile, dimension_key, limit=limit):
            keyword = fb["keyword"]
            if keyword in seen:
                continue
            merged.append(fb)
            seen.add(keyword)
            if coverage_count(seed) >= min_needed or len(merged) >= limit * 2:
                break

    for fb in _cross_seed_items(seeds, profile, dimension_key):
        keyword = fb["keyword"]
        if keyword in seen:
            continue
        merged.append(fb)
        seen.add(keyword)
        if len(merged) >= limit * 2:
            break

    # 均衡截断：轮询各种子，保证尽量都留下席位
    buckets: dict[str, list[dict]] = {seed: [] for seed in seeds}
    other: list[dict] = []
    for item in merged:
        keyword = str(item.get("keyword") or "")
        placed = False
        for seed in seeds:
            if _keyword_mentions_seed(keyword, seed) and len(buckets[seed]) < min_needed:
                buckets[seed].append(item)
                placed = True
                break
        if not placed:
            other.append(item)

    balanced: list[dict] = []
    seen_out: set[str] = set()
    # 先各种子保底
    for seed in seeds:
        for item in buckets[seed]:
            kw = item["keyword"]
            if kw in seen_out:
                continue
            balanced.append(item)
            seen_out.add(kw)
    # 再按原序补满
    for item in merged + other:
        kw = str(item.get("keyword") or "")
        if not kw or kw in seen_out:
            continue
        balanced.append(item)
        seen_out.add(kw)
        if len(balanced) >= limit:
            break
    return balanced[:limit]


def _sanitize_dimension_items(seeds: list[str], dimension_key: str, raw_items: list[dict], profile: dict) -> list[dict]:
    primary = seeds[0] if seeds else ""
    items: list[dict] = []
    seen = set()
    for raw in raw_items or []:
        keyword = re.sub(r"\s+", " ", str(raw.get("keyword") or raw.get("kw") or "").strip())
        if (
            not keyword
            or keyword in seen
            or not _is_keyword_allowed(profile, keyword)
            or _is_low_quality_for_seeds(keyword, seeds, dimension_key, profile)
        ):
            continue
        seen.add(keyword)
        seed_for_score = _matching_seed_for_keyword(keyword, seeds) or primary
        try:
            recommendation = int(raw.get("recommendation_score", raw.get("rec", 0)))
        except Exception:
            recommendation = 0
        try:
            business = int(raw.get("business_score", raw.get("biz", 0)))
        except Exception:
            business = 0
        recommendation = max(35, min(99, recommendation or _stable_score(seed_for_score, dimension_key, keyword, 60, 28)))
        business = max(35, min(99, business or _stable_score(seed_for_score, f"{dimension_key}-biz", keyword, 58, 26)))
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
    return _ensure_multi_seed_coverage(items, seeds, profile, dimension_key, limit=10)


def _infer_seed_role_hints(seeds: list[str]) -> list[dict]:
    """轻量角色提示；别名/属性近亲显式标出，避免模型当两个主体交叉。"""
    org_markers = ("广电", "集团", "广播", "电视台", "日报", "传媒", "通讯社", "报社", "出版社")
    product_markers = ("客户端", "栏目", "频道", "节目", "app", "号", "矩阵", "官网")
    topic_markers = ("党媒", "主流", "融媒", "短视频", "直播", "舆情", "政务", "宣传")
    aspect_markers = ("续航", "价格", "评测", "参数", "规格", "套装", "配件", "图传", "避障")
    hints: list[dict] = []
    for seed in seeds:
        role = "other"
        gloss = "待确认的业务实体"
        low = seed.lower()
        if any(marker in seed for marker in org_markers):
            role, gloss = "organization", "疑似机构/媒体主体"
        elif any(marker in low for marker in product_markers):
            role, gloss = "product_or_column", "疑似栏目/产品/客户端"
        elif any(marker in seed for marker in topic_markers):
            role, gloss = "topic_or_attribute", "疑似属性/议题/定位"
        elif any(seed.endswith(marker) or marker in seed for marker in aspect_markers):
            # 可能是「产品+属性」；若与其他种子近亲则标 aspect
            role, gloss = "aspect", "疑似规格/卖点属性词"
        hints.append({"seed": seed, "hint_role": role, "hint_gloss": gloss, "alias_group": None, "of": None})

    # 别名成组 + 属性挂靠主体
    groups: list[list[str]] = []
    for seed in seeds:
        placed = False
        for group in groups:
            if any(_seeds_are_near_duplicates(seed, member) for member in group):
                group.append(seed)
                placed = True
                break
        if not placed:
            groups.append([seed])

    seed_to_group = {}
    for idx, group in enumerate(groups):
        label = f"g{idx + 1}"
        for member in group:
            seed_to_group[member] = label

    for hint in hints:
        seed = hint["seed"]
        hint["alias_group"] = seed_to_group.get(seed)
        group = next((g for g in groups if seed in g), [seed])
        if len(group) > 1:
            # 同组多词：中英品牌等 → alias；勿当两个主体
            others = [item for item in group if item != seed]
            hint["alias_of"] = others[0]
            if hint["hint_role"] not in {"organization", "product_or_column", "topic_or_attribute"}:
                hint["hint_role"] = "alias"
                hint["hint_gloss"] = f"与「{others[0]}」同实体别名，禁止交叉成关系问法"
        # 属性挂靠：自身含属性后缀且与某主体近亲
        if hint["hint_role"] == "aspect" or any(seed.endswith(m) for m in aspect_markers):
            for other in seeds:
                if other == seed:
                    continue
                if _seeds_are_near_duplicates(seed, other) and len(_normalize_seed_key(other)) <= len(_normalize_seed_key(seed)):
                    # prefer shorter/core as parent when other is contained
                    pass
                core_self, core_other = _seed_core_token(seed), _seed_core_token(other)
                if core_self and core_other and (core_self == core_other or core_other in core_self):
                    if len(_normalize_seed_key(other)) < len(_normalize_seed_key(seed)):
                        hint["of"] = other
                        hint["hint_role"] = "aspect"
                        hint["hint_gloss"] = f"「{other}」的属性/卖点，禁止与主体做「报道/旗下/联动」交叉"
                        break
    return hints


def _build_seed_entity_graph(seeds: list[str], hints: list[dict]) -> dict:
    """给模型的实体图：canonical / aliases / aspects，减少别名互啄。"""
    groups: dict[str, list[str]] = {}
    for hint in hints:
        gid = hint.get("alias_group") or hint["seed"]
        groups.setdefault(gid, []).append(hint["seed"])
    aliases = [members for members in groups.values() if len(members) > 1]
    aspects = [
        {"seed": h["seed"], "of": h.get("of")}
        for h in hints
        if h.get("hint_role") == "aspect" and h.get("of")
    ]
    canonical = []
    seen = set()
    for members in groups.values():
        # 选最短归一化串作代表
        primary = sorted(members, key=lambda s: len(_normalize_seed_key(s)))[0]
        if primary not in seen:
            canonical.append(primary)
            seen.add(primary)
    return {
        "canonical_entities": canonical,
        "alias_groups": aliases,
        "aspects": aspects,
        "rule": "同 alias_group 内词是同一实体的别名；aspect.of 是主体。禁止别名之间、主体与自身属性写成两个主体的关系问法。",
    }


def _compose_expansion_system_prompt(base: str, seeds: list[str]) -> str:
    text = (base or "").strip()
    if len(seeds) > 1:
        from app.services.runtime_settings import MULTI_SEED_METHOD_ADDENDUM

        addendum = MULTI_SEED_METHOD_ADDENDUM.strip()
        if addendum and addendum not in text:
            text = f"{text}\n\n{addendum}"
    return text


async def _ai_expand(
    seeds: list[str],
    profile: dict,
    provider_override=None,
) -> tuple[list[dict], list[dict]]:
    from app.services.runtime_settings import get_keyword_expansion_config

    config = await get_keyword_expansion_config()
    system = _compose_expansion_system_prompt(config["system_prompt"], seeds)
    titles_per = int(config.get("titles_per_platform") or 3)
    platforms = list(config.get("platforms") or [])
    seed_label = "、".join(seeds[:5]) if seeds else "主体"
    entity = seed_label
    multi = len(seeds) > 1
    seed_role_hints = _infer_seed_role_hints(seeds)
    knowledge_brief = profile.get("knowledge_brief") if isinstance(profile.get("knowledge_brief"), dict) else None
    knowledge_snippets = profile.get("knowledge_snippets") if isinstance(profile.get("knowledge_snippets"), list) else []
    if knowledge_brief:
        from app.services.keyword_kb_context import merge_brief_into_role_hints

        seed_role_hints = merge_brief_into_role_hints(seed_role_hints, knowledge_brief)
    seed_entity_graph = _build_seed_entity_graph(seeds, seed_role_hints)

    user = json.dumps(
        {
            "task": "keyword_expansion_for_geo_content",
            "steps": [
                "根据 seed_entity_graph、seed_role_hints 与 knowledge_entity_brief 写出 seed_map（brief 优先）",
                "先过标题第一关：question 维与 platform_title_hints",
                "按真正不同的实体关系扩写其余 dimensions（别名只做 semantic 变体；owns 禁止互报/联动）",
                "按 platforms 写 platform_title_hints",
            ],
            "seeds": seeds,
            "entity": entity,
            "multi_seed": multi,
            "seed_role_hints": seed_role_hints,
            "seed_entity_graph": seed_entity_graph,
            "knowledge_entity_brief": knowledge_brief,
            "knowledge_snippets": [
                {"score": s.get("score"), "content": (s.get("content") or "")[:400]}
                for s in (knowledge_snippets or [])[:6]
            ],
            "knowledge_rules": (
                [
                    "关系以 knowledge_entity_brief 为准，可纠正字面启发式",
                    "owns 两端禁止：怎么报道/联动合作/对…报道怎么样",
                    "competitors 仅用于对比/差异/选型问法",
                    "forbidden 短语不得出现在关键词中",
                    "knowledge_snippets 只补场景，不可编造收视率或实测引用率",
                ]
                if knowledge_brief
                else None
            ),
            "title_gate": GEO_TITLE_GATE_BRIEF,
            "geo_methods_priority": [
                "statistics_addition",
                "cite_sources",
                "quotation_addition",
                "fluency",
                "avoid_keyword_stuffing",
            ],
            "coverage_rule": (
                "每个维度覆盖全部种子；至少 3 条交叉关系型问法；禁止分号粘词；禁止只扩第一个种子"
                if multi
                else "围绕唯一种子扩写，问法要像真人检索并通过标题门"
            ),
            "negative_examples": [
                "深圳广电;第一现场;党媒栏目",
                "广电媒体怎么做种子A;种子B",
                "深圳广电怎么报道第一现场",
                "深圳广电与第一现场联动合作",
                "只输出与第一种子相关的词",
                "GEO优化",
                "党媒平台",
            ],
            "positive_direction": (
                "先区分机构/栏目/属性（优先采用 knowledge_entity_brief）；"
                "owns 写「机构如何运营栏目」「旗下栏目定位」；竞品写对照；"
                "标题须能直接交给内容模板写结论前置+证据短文"
                if multi
                else "围绕实体写可检索长尾与问题式选题；优先 Statistics/Cite/Quotation 可写方向"
            ),
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
                "avoid": "空泛词、跨维度重复、把页面 citation 就绪度说成答案引用率、垂类硬套话、Keyword Stuffing",
            },
        },
        ensure_ascii=False,
    )
    try:
        raw = await ai_client.complete(
            system,
            user,
            temperature=0.35 if multi else 0.45,
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
            seeds, dim["key"], mapping.get(dim["key"]) or [], profile
        )
        if not items:
            # 整维为空：按全部种子模板合并，而不是只填 seeds[0]
            merged_fb: list[dict] = []
            seen_fb: set[str] = set()
            for seed in seeds:
                for fb in _fallback_dimension_items(seed, profile, dim["key"]):
                    if fb["keyword"] in seen_fb:
                        continue
                    seen_fb.add(fb["keyword"])
                    merged_fb.append(fb)
            items = _ensure_multi_seed_coverage(merged_fb, seeds, profile, dim["key"], limit=10)
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
                    if not is_geo_title_acceptable(text):
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
    *,
    knowledge_base_id=None,
    db=None,
) -> tuple[dict, bool]:
    from app.services.runtime_settings import get_keyword_expansion_config

    normalized = normalize_seeds(seeds)
    if not normalized:
        raise ValueError("请至少输入一个关键词")

    profile = _infer_keyword_profile(normalized)
    knowledge_meta = {
        "kb_id": None,
        "cards_used": 0,
        "chunks_used": 0,
        "owns_edges": 0,
        "competitors": [],
    }
    if knowledge_base_id and db is not None:
        try:
            import uuid as uuid_mod

            from app.services.keyword_kb_context import load_knowledge_context

            kb_uuid = (
                knowledge_base_id
                if isinstance(knowledge_base_id, uuid_mod.UUID)
                else uuid_mod.UUID(str(knowledge_base_id))
            )
            brief, snippets, meta = await load_knowledge_context(
                db,
                kb_id=kb_uuid,
                seeds=normalized,
                chunk_limit=6,
            )
            profile["knowledge_brief"] = brief
            profile["knowledge_snippets"] = snippets
            knowledge_meta = meta
        except Exception:
            # 库无效或检索失败时降级为无知识库拓词
            profile.pop("knowledge_brief", None)
            profile.pop("knowledge_snippets", None)

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
        "knowledge_meta": knowledge_meta,
    }, provider_succeeded


async def expand_keywords(seeds: list[str], provider_override=None) -> dict:
    payload, _ = await expand_keywords_with_status(
        seeds,
        provider_override=provider_override,
    )
    return payload
