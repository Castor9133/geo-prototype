/**
 * Diagnostic Page - 真实 GEO 诊断交互
 */
(window.GEOrank?.PageLifecycle?.run?.bind(window.GEOrank.PageLifecycle)
    || ((callback) => callback()))(() => {
    'use strict';

    const API_BASE = '';
    const Routes = window.GEOrank?.Routes;
    const initialRouteState = Routes?.readDiagnosticState
        ? Routes.readDiagnosticState()
        : (() => {
            const params = new URLSearchParams(window.location.search);
            return {
                url: params.get('url') || '',
                companyId: params.get('company_id') || '',
                reportId: params.get('report') || params.get('report_id') || '',
            };
        })();
    const initialUrl = initialRouteState.url || '';
    const initialCompanyId = initialRouteState.companyId || '';
    const initialReportId = initialRouteState.reportId || '';
    const Auth = window.GEOrank?.Auth;
    const Workflow = window.GEOrank?.SuiteWorkflow;

    const urlInput = document.getElementById('url-input');
    const diagnoseBtn = document.getElementById('diagnose-btn');
    const reportShell = document.getElementById('diagnostic-report-shell');
    const resultsGrid = document.getElementById('results-grid');
    const statusNote = document.getElementById('diagnostic-status-note');
    const exportBtn = document.getElementById('diagnostic-export-btn');
    const toSolutionsBtn = document.getElementById('diagnostic-to-solutions-btn');
    const createStrategyBtn = document.getElementById('diagnostic-create-strategy-btn');
    let lastLiveReport = null;
    const reportModeEyebrow = document.getElementById('diagnostic-report-mode-eyebrow');
    const reportModeTitle = document.getElementById('diagnostic-report-mode-title');
    const reportModeCopy = document.getElementById('diagnostic-report-mode-copy');
    const reportModeChip = document.getElementById('diagnostic-report-mode-chip');
    const reportModeIcon = document.getElementById('diagnostic-report-mode-icon');
    const transitionOverlay = document.getElementById('diagnostic-transition-overlay');
    const transitionCopy = document.getElementById('diagnostic-transition-copy');
    const summaryHeadline = document.getElementById('diagnostic-summary-headline');
    const summaryOverview = document.getElementById('diagnostic-summary-overview');
    const summaryPriority = document.getElementById('diagnostic-summary-priority');
    const strengthList = document.getElementById('diagnostic-strength-list');
    const gapList = document.getElementById('diagnostic-gap-list');

    let pollTimer = null;
    let activeReportId = initialReportId;
    let activeCompanyId = initialCompanyId;
    const DEMO_REPORT = {
        report_id: 'demo-report',
        url: 'https://www.demobrand.ai',
        company_id: '',
        status: 'completed',
        overall_score: 82,
        seo_modules: [
            {
                id: 'crawlability',
                title: '可抓取与可达',
                purpose: '先确认引擎能打开页面，并读到标题、摘要、语言等第一层介绍信息。',
                score: 88,
                result: '基础摘要就绪分 88/100。标题、摘要等信号较完整，仍缺分享语言区。',
                impact: '缺「分享语言区」时，跨区转发可能推错受众；其余基础信号完整，误拦收录风险较低。',
                advice: '补齐分享语言区（og:locale）；运营继续用「主题+受众价值」写标题和摘要。',
            },
            {
                id: 'parseable_structure',
                title: '可解析结构',
                purpose: '确认机构/站点身份、标题层级和 FAQ 能否被读成实体与问答块。',
                score: 85,
                result: '结构合成分 85；H1=1 · H2=7 · FAQ 样块=2。建议补 FAQPage。',
                impact: '「问答页标记」缺失时，高频咨询问题不易被稳定摘成问答块，FAQ 文案也可能被当普通段落略过。',
                advice: '补 FAQPage；关键 H2 保持用户问句；运营验收每个高频问题都有可复制短答。',
            },
            {
                id: 'internal_discovery',
                title: '内链与发现',
                purpose: '确认栏目/专题/说明等关键页能被内链发现，并有权威外链作信任线索（≠ AI 引用率）。',
                score: 71,
                result: '外链 7 · 权威线索 2；发现/背书就绪分 71。',
                impact: '已有权威线索，发现就绪尚可；若栏目/专题页内链弱，关键内容仍可能埋在孤立页。',
                advice: '用内链串起栏目与专题/说明页，并保留权威外链；从本页 2～3 次点击应能到达。',
            },
            {
                id: 'performance_cost',
                title: '性能与成本',
                purpose: '评估正文长短是否让引擎读得贵、摘得慢；把关键话放在更好被看见的位置。',
                score: 72,
                result: '正文体量适中；优先短直答段落降低上下文成本。',
                impact: '体量压力不大；若核心结论靠后，仍可能「读到了但摘不稳」（代理信号，非测速分）。',
                advice: '把关键事实放在靠前、可独立摘录的段落，方便编辑与对外口径复用同一套答法。',
            },
        ],
        schema_analysis: {
            score: 84,
            found_types: ['WebSite', 'Organization', 'Service', 'BreadcrumbList', 'Article'],
            missing_recommended: ['FAQPage'],
            schema_count: 5,
            coverage_ratio: 80,
            has_faq: false,
            has_org: true,
            has_article: true,
            has_breadcrumb: true,
            has_product: false,
            has_website: true,
        },
        meta_analysis: {
            score: 88,
            preview_score: 91,
            checks: {
                title: true,
                title_length: 34,
                meta_description: true,
                meta_description_length: 118,
                canonical: true,
                viewport: true,
                robots: true,
                favicon: true,
                html_lang: true,
                og_title: true,
                og_description: true,
                og_image: true,
                og_type: true,
                og_locale: false,
                twitter_card: true,
            },
            missing: ['og_locale'],
        },
        content_analysis: {
            score: 86,
            h1_count: 1,
            h2_count: 7,
            h3_count: 5,
            paragraph_count: 18,
            word_count: 890,
            character_count: 3240,
            reading_time_minutes: 7,
            has_single_h1: true,
            has_h2_structure: true,
            first_para_quality: true,
            heading_hierarchy_ok: true,
            list_count: 4,
            table_count: 2,
            image_count: 12,
            image_with_alt_count: 11,
            image_alt_ratio: 92,
            faq_like_sections: 2,
            cta_count: 4,
        },
        citation_analysis: {
            score: 79,
            external_link_count: 7,
            authority_link_count: 2,
            internal_link_count: 26,
            social_link_count: 3,
            authority_links: [
                'https://developers.google.com/search/docs/fundamentals/seo-starter-guide',
                'https://www.anthropic.com/engineering/building-effective-agents',
            ],
            social_links: [
                'https://www.linkedin.com/company/demobrand',
                'https://github.com/demobrand',
            ],
        },
        recommendations: {
            summary: {
                headline: '这是一份较成熟的企业官网示例报告，已经具备不错的 GEO 基础，但仍有进一步提升可发现/可理解的背书信号的空间。',
                overview: '示例报告以一家 AI 搜索优化服务官网为蓝本，展示从结构化实体、摘要预览到权威背书的完整 GEO 诊断视角。真实诊断完成后，会沿用同一套富报告结构替换这份样例。',
                priority_action: '先补齐 FAQPage，再强化内链与权威外链。'
            },
            strengths: [
                '结构化实体较完整，品牌、服务与文章关系已经能被机器清晰识别。',
                '正文层级、FAQ 和案例表达成熟，适合被 AI 拆成多段理解与引用候选。',
                '预览信号和外部背书基础不错，具备进一步增强背书就绪信号的条件。',
            ],
            gaps: [
                'FAQ 结构化还不够完整，问答内容和页面可读块之间没有完全一一映射。',
                '多语言与地区语境标记还不充分，跨区域生成式检索场景下会损失可见度。',
                '高价值案例页的权威外链仍有增长空间，品牌背书就绪信号还能继续抬高。',
            ],
            urgent: [
                { item: '补齐 FAQPage 结构化问答', action: '将页面中已有 FAQ 问答和服务说明映射成完整 FAQPage，确保 question / acceptedAnswer 成对输出。' },
                { item: '强化服务页首屏摘要', action: '把核心服务页首段改成“适用对象 + 痛点 + 解决路径 + 结果”的答案式摘要，控制在 120-180 字。' },
                { item: '补上地区与语言语义', action: '补充 og:locale、地区语义词和对应服务覆盖范围，增强面向中文市场的 AI 检索命中。' },
            ],
            recommended: [
                { item: '放大案例证据密度', action: '在案例页增加具体数据结果、实施动作和客户原话，让 AI 能直接摘取证据型表达。' },
                { item: '扩充权威来源链接', action: '在关键页面补入搜索官方文档、模型厂商指南和行业研究链接，形成更稳的信任背书。' },
                { item: '统一开放图谱封面模板', action: '为核心页面生成统一风格的 OG 封面图与标题模板，提升摘要展示一致性。' },
            ],
            optional: [
                { item: '整理站内主题集群', action: '将教程、案例、服务和 FAQ 之间建立更紧密的内链集群，形成更强的主题网。' },
                { item: '补充多模态图片说明', action: '继续完善图示类图片的 alt 与 caption，让多模态 AI 更容易理解图文关系。' },
                { item: '增加可下载资产', action: '提供白皮书、清单或模板类资源页，方便在 AI 答案里形成更强的资源锚点。' },
            ],
            phase_plan: [
                { phase: 'P0', title: '问答结构化补齐', goal: '把现有 FAQ 和服务说明升级成机器可读的 FAQPage + Service 实体组合。', success_metric: 'Schema 覆盖率和答案模块得分同时提升到 85+。' },
                { phase: 'P1', title: '高价值页面重写', goal: '围绕首页、服务页和案例页重写首屏答案表达，让 AI 能直接摘取关键段落。', success_metric: '内容表达、预览和 CTA 模块达到优秀。'},
                { phase: 'P2', title: '权威背书扩容', goal: '增加外部研究、客户案例、社交与品牌背书，构建更稳的可引用信任层。', success_metric: '外链与背书就绪维度稳定在 80 分以上。' },
            ],
        },
    };

    if (urlInput && initialUrl) {
        urlInput.value = initialUrl;
    }

    if (diagnoseBtn) {
        diagnoseBtn.addEventListener('click', () => startDiagnosis());
    }

    if (urlInput) {
        urlInput.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                startDiagnosis();
            }
        });
    }

    exportBtn?.addEventListener('click', function () {
        if (exportBtn.disabled) return;
        window.print();
    });

    function getAuthToken() {
        return Auth?.getToken?.()
            || localStorage.getItem('georank_user_token')
            || localStorage.getItem('georank_token')
            || '';
    }

    async function request(path, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...(window.GEOrank?.DeviceIdentity?.getHeaders?.() || {}),
            ...(options.headers || {}),
        };
        const token = getAuthToken();
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE}${path}`, {
            ...options,
            headers,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const message = data.detail || `请求失败 (${response.status})`;
            throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
        }
        return data;
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function normalizeInputUrl(raw) {
        const value = String(raw || '').trim();
        if (!value) {
            throw new Error('请输入要诊断的站点地址');
        }

        let candidate = value;
        if (!/^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(candidate)) {
            candidate = `https://${candidate}`;
        }

        let parsed;
        try {
            parsed = new URL(candidate);
        } catch (_) {
            throw new Error('请输入有效的网址，例如 example.com 或 https://example.com');
        }

        if (!['http:', 'https:'].includes(parsed.protocol)) {
            throw new Error('仅支持 http 或 https 网站地址');
        }
        if (!parsed.hostname || !parsed.hostname.includes('.')) {
            throw new Error('请输入有效的网址，例如 example.com');
        }

        const normalizedPath = parsed.pathname === '/' ? '' : parsed.pathname.replace(/\/+$/, '');
        return `${parsed.protocol}//${parsed.host.toLowerCase()}${normalizedPath}`;
    }

    function setStatus(message, tone = 'info') {
        if (!statusNote) return;
        statusNote.classList.remove('hidden', 'text-slate-500', 'text-red-500', 'text-green-600');
        statusNote.classList.add(tone === 'error' ? 'text-red-500' : tone === 'success' ? 'text-green-600' : 'text-slate-500');
        statusNote.textContent = message;
    }

    function setReportMode(mode, context = {}) {
        if (reportShell) {
            reportShell.dataset.mode = mode;
        }
        if (transitionOverlay) {
            transitionOverlay.classList.toggle('hidden', mode !== 'loading');
        }
        if (transitionCopy && mode === 'loading') {
            const statusText = {
                pending: '任务已创建，正在排队…',
                crawling: '正在抓取页面…',
                analyzing: '正在汇总 SEO 四类结果…',
            };
            transitionCopy.textContent = statusText[context.step] || '正在抓取页面并生成检查结果…';
        }

        const meta = {
            demo: {
                eyebrow: '示例报告',
                title: '基础 SEO 检查示例',
                copy: '输入真实网址并开始检查后，将替换为该页的抓取结果。',
                chip: '示例',
                icon: 'visibility',
            },
            loading: {
                eyebrow: '检查进行中',
                title: '正在抓取并分析',
                copy: context.url
                    ? `正在分析 ${context.url} 的基础 SEO 就绪情况。`
                    : '正在分析基础 SEO 就绪情况。',
                chip: '分析中',
                icon: 'progress_activity',
            },
            live: {
                eyebrow: '检查结果',
                title: '基础 SEO 就绪情况',
                copy: context.url
                    ? `${context.url} 的抓取结果如下。`
                    : '抓取结果如下。',
                chip: '已完成',
                icon: 'verified',
            },
        }[mode] || {};

        if (reportModeEyebrow && meta.eyebrow) reportModeEyebrow.textContent = meta.eyebrow;
        if (reportModeTitle && meta.title) reportModeTitle.textContent = meta.title;
        if (reportModeCopy && meta.copy) reportModeCopy.textContent = meta.copy;
        if (reportModeChip && meta.chip) reportModeChip.textContent = meta.chip;
        if (reportModeIcon && meta.icon) reportModeIcon.textContent = meta.icon;

        if (exportBtn) {
            const exportEnabled = mode === 'live';
            exportBtn.disabled = !exportEnabled;
            exportBtn.classList.toggle('opacity-50', !exportEnabled);
            exportBtn.classList.toggle('cursor-not-allowed', !exportEnabled);
        }
        if (toSolutionsBtn && mode !== 'live') {
            toSolutionsBtn.href = '/keywords';
        }
    }

    function animateLiveSwap() {
        if (!resultsGrid) return;
        resultsGrid.classList.remove('diagnostic-report-swap-in');
        void resultsGrid.offsetWidth;
        resultsGrid.classList.add('diagnostic-report-swap-in');
    }

    function clearPolling() {
        if (pollTimer) {
            clearTimeout(pollTimer);
            pollTimer = null;
        }
    }

    function setLoading(loading) {
        if (!diagnoseBtn) return;
        diagnoseBtn.disabled = loading;
        diagnoseBtn.innerHTML = loading
            ? '<span class="material-symbols-outlined text-lg" style="animation:diagnostic-spin .7s linear infinite">progress_activity</span><span class="font-bold text-sm">分析中</span>'
            : '开始检查';
    }

    function updateLocation(reportId, url) {
        if (Routes?.buildDiagnosticPath) {
            window.history.replaceState(
                { reportId },
                '',
                Routes.buildDiagnosticPath({
                    reportId,
                    url,
                    companyId: activeCompanyId,
                })
            );
            return;
        }
        const next = new URL(window.location.href);
        if (reportId) next.searchParams.set('report', reportId);
        if (url) next.searchParams.set('url', url);
        if (activeCompanyId) next.searchParams.set('company_id', activeCompanyId);
        window.history.replaceState({ reportId }, '', next.toString());
    }

    function showResults() {
        resultsGrid?.classList.remove('hidden');
    }

    function hideResults() {
        resultsGrid?.classList.add('hidden');
    }

    function scoreTone(score) {
        if (score >= 80) return { label: '优秀', bar: 'diag-bar diag-bar--excellent' };
        if (score >= 60) return { label: '良好', bar: 'diag-bar diag-bar--good' };
        if (score >= 40) return { label: '待优化', bar: 'diag-bar diag-bar--ok' };
        return { label: '偏弱', bar: 'diag-bar diag-bar--weak' };
    }

    function average(values) {
        const safeValues = (Array.isArray(values) ? values : [])
            .map((value) => Number(value))
            .filter((value) => Number.isFinite(value));
        if (!safeValues.length) return 0;
        return Math.round(safeValues.reduce((sum, value) => sum + value, 0) / safeValues.length);
    }

    function metricScore(value, thresholds) {
        for (const threshold of thresholds) {
            if (value >= threshold.min) {
                return threshold.score;
            }
        }
        return thresholds[thresholds.length - 1]?.score || 0;
    }

    function boolMetric(title, passed, positiveNote, negativeNote, metricLabel) {
        return {
            title,
            score: passed ? 100 : 35,
            metric: metricLabel || (passed ? '已具备' : '待补齐'),
            note: passed ? positiveNote : negativeNote,
        };
    }

    function buildDiagnosticSections(report) {
        const schema = report.schema_analysis || {};
        const meta = report.meta_analysis || {};
        const metaChecks = meta.checks || {};
        const content = report.content_analysis || {};
        const citation = report.citation_analysis || {};
        const characterCount = Number(content.character_count || 0);

        const sections = [
            {
                key: 'access',
                title: '抓取入口',
                icon: 'travel_explore',
                summary: '确认页面是否具备被搜索引擎与 AI 抓取的基础入口信号。',
                items: [
                    boolMetric('HTTPS 协议', String(report.url || '').startsWith('https://'), '页面入口已使用 HTTPS。', '建议统一使用 HTTPS 规范入口。', String(report.url || '').startsWith('https://') ? 'HTTPS' : 'HTTP'),
                    boolMetric('Canonical 规范', !!metaChecks.canonical, '已声明 canonical，利于统一权重。', '缺少 canonical，可能造成页面权重分散。'),
                    boolMetric('Viewport 适配', !!metaChecks.viewport, '已声明 viewport，移动端抓取语义更稳定。', '缺少 viewport，移动端体验与抓取语义存在风险。'),
                    boolMetric('Lang 声明', !!metaChecks.html_lang, '已声明 HTML lang 语言。', '建议在 html 标签上声明 lang。'),
                ],
            },
            {
                key: 'preview',
                title: '预览元信息',
                icon: 'html',
                summary: '诊断标题、摘要和社交预览是否能支撑生成式摘要展示。',
                items: [
                    {
                        title: 'Title 完整度',
                        score: metaChecks.title ? metricScore(Number(metaChecks.title_length || 0), [{ min: 35, score: 96 }, { min: 20, score: 70 }, { min: 1, score: 45 }, { min: 0, score: 20 }]) : 20,
                        metric: `${metaChecks.title_length || 0} 字符`,
                        note: metaChecks.title ? '标题已存在，可继续压缩到更聚焦的实体表达。' : '缺少页面标题。',
                    },
                    {
                        title: 'Meta Description',
                        score: metaChecks.meta_description ? metricScore(Number(metaChecks.meta_description_length || 0), [{ min: 90, score: 92 }, { min: 50, score: 75 }, { min: 1, score: 45 }, { min: 0, score: 20 }]) : 20,
                        metric: `${metaChecks.meta_description_length || 0} 字符`,
                        note: metaChecks.meta_description ? '描述已存在，可继续强化可摘录摘要。' : '缺少 meta description。',
                    },
                    boolMetric('开放图谱', !!metaChecks.og_title && !!metaChecks.og_description && !!metaChecks.og_type, 'OG 标题、描述与类型基本完整。', 'OG 标题/描述/类型仍不完整。'),
                    boolMetric('社媒卡片', !!metaChecks.twitter_card && !!metaChecks.og_image, '社交预览卡片完整，可支撑摘要传播。', '缺少 twitter:card 或 og:image。'),
                ],
            },
            {
                key: 'schema',
                title: '结构化语义',
                icon: 'code_blocks',
                summary: '判断页面是否把品牌、文章和问答结构显式暴露给机器理解。',
                items: [
                    {
                        title: 'Schema 覆盖率',
                        score: Number(schema.coverage_ratio || schema.score || 0),
                        metric: `${schema.coverage_ratio || schema.score || 0}%`,
                        note: '核心推荐 Schema 类型覆盖情况。',
                    },
                    boolMetric('Organization 实体', !!schema.has_org, '组织实体已具备。', '缺少 Organization / WebSite 实体。'),
                    boolMetric('FAQ 问答', !!schema.has_faq, 'FAQPage 已具备，可提升可理解问答结构。', '建议加入 FAQPage 结构化问答。'),
                    boolMetric('面包屑导航', !!schema.has_breadcrumb, 'BreadcrumbList 已声明。', '建议补充 BreadcrumbList，增强主题链路。'),
                ],
            },
            {
                key: 'content',
                title: '内容组织',
                icon: 'article',
                summary: '从正文体量、标题层级和内容组件判断页面是否具备答案型可抽取结构。',
                items: [
                    boolMetric('H1 唯一性', !!content.has_single_h1, '页面 H1 数量合理。', `当前检测到 ${content.h1_count || 0} 个 H1，建议只保留一个。`, `${content.h1_count || 0} 个 H1`),
                    boolMetric('标题层级', !!content.heading_hierarchy_ok, 'H1/H2 结构已形成清晰层级。', 'H1/H2 层级仍需梳理。'),
                    {
                        title: '正文深度',
                        score: metricScore(characterCount, [{ min: 1800, score: 96 }, { min: 1200, score: 82 }, { min: 700, score: 64 }, { min: 300, score: 42 }, { min: 0, score: 20 }]),
                        metric: `${characterCount} 字`,
                        note: '正文体量越完整，越容易形成可摘录段落。',
                    },
                    {
                        title: '阅读时长',
                        score: metricScore(Number(content.reading_time_minutes || 0), [{ min: 4, score: 88 }, { min: 2, score: 68 }, { min: 1, score: 48 }, { min: 0, score: 24 }]),
                        metric: `${content.reading_time_minutes || 0} 分钟`,
                        note: '中等深度内容更适合被生成式搜索理解与调用。',
                    },
                ],
            },
            {
                key: 'answer',
                title: '答案表达',
                icon: 'edit_note',
                summary: '评估页面是否采用问题-回答、列表和组件化表达，便于 AI 摘录。',
                items: [
                    boolMetric('首段直答', !!content.first_para_quality, '首段已经具备较强的信息密度。', '首段仍偏口号式，缺少可直接摘录的答案。'),
                    {
                        title: '列表表达',
                        score: metricScore(Number(content.list_count || 0), [{ min: 3, score: 95 }, { min: 2, score: 82 }, { min: 1, score: 62 }, { min: 0, score: 30 }]),
                        metric: `${content.list_count || 0} 个列表`,
                        note: '列表结构越充分，越容易让 AI 拆分要点。',
                    },
                    {
                        title: 'FAQ 语气',
                        score: metricScore(Number(content.faq_like_sections || 0), [{ min: 2, score: 95 }, { min: 1, score: 78 }, { min: 0, score: 32 }]),
                        metric: `${content.faq_like_sections || 0} 个问答段`,
                        note: 'FAQ / 常见问题板块有助于被问答式结果直接调用。',
                    },
                    {
                        title: 'CTA 清晰度',
                        score: metricScore(Number(content.cta_count || 0), [{ min: 3, score: 90 }, { min: 2, score: 72 }, { min: 1, score: 52 }, { min: 0, score: 24 }]),
                        metric: `${content.cta_count || 0} 个动作点`,
                        note: '明确的行动入口更利于把内容转成下一步方案。',
                    },
                ],
            },
            {
                key: 'trust',
                title: '外链与权威背书（就绪信号)',
                icon: 'query_stats',
                summary: '衡量页面通过外链、权威来源与站内支撑建立可信度的就绪能力。注意：本维≠ AI 答案引用率。',
                items: [
                    {
                        title: '外部链接广度',
                        score: metricScore(Number(citation.external_link_count || 0), [{ min: 8, score: 96 }, { min: 4, score: 78 }, { min: 1, score: 52 }, { min: 0, score: 24 }]),
                        metric: `${citation.external_link_count || 0} 个外链`,
                        note: '外部信号越丰富，越利于建立可发现的背书网络（此为就绪信号，≠ AI 答案引用率）。',
                    },
                    {
                        title: '权威外链',
                        score: metricScore(Number(citation.authority_link_count || 0), [{ min: 3, score: 100 }, { min: 2, score: 86 }, { min: 1, score: 66 }, { min: 0, score: 26 }]),
                        metric: `${citation.authority_link_count || 0} 个权威源`,
                        note: '学术、官方或行业权威来源是生成式引擎偏好的信号。',
                    },
                    {
                        title: '站内支撑链接',
                        score: metricScore(Number(citation.internal_link_count || 0), [{ min: 16, score: 92 }, { min: 10, score: 76 }, { min: 5, score: 58 }, { min: 0, score: 28 }]),
                        metric: `${citation.internal_link_count || 0} 个内链`,
                        note: '站内主题链路越完整，越利于 AI 形成上下文理解。',
                    },
                    {
                        title: '社交背书',
                        score: metricScore(Number(citation.social_link_count || 0), [{ min: 3, score: 90 }, { min: 2, score: 74 }, { min: 1, score: 54 }, { min: 0, score: 26 }]),
                        metric: `${citation.social_link_count || 0} 个社交源`,
                        note: '品牌在外部平台的公开存在，有助于提升可信信号。',
                    },
                ],
            },
        ];

        return sections.map((section) => ({
            ...section,
            score: average(section.items.map((item) => item.score)),
        }));
    }

    function buildReadinessStages(sections, overallScore) {
        const sectionMap = Object.fromEntries(sections.map((section) => [section.key, section]));
        return [
            { label: '抓取可达', score: average([sectionMap.access?.score, sectionMap.preview?.score]) },
            { label: '实体理解', score: sectionMap.schema?.score || 0 },
            { label: '答案表达', score: average([sectionMap.content?.score, sectionMap.answer?.score]) },
            { label: '信任构建', score: sectionMap.trust?.score || 0 },
            { label: '答案就绪准备', score: average([overallScore, sectionMap.schema?.score, sectionMap.answer?.score, sectionMap.trust?.score]) },
        ];
    }

    function buildSignalMix(report) {
        return [
            { label: 'Schema', value: Number(report.schema_analysis?.score || 0), color: '#8FB8E8' },
            { label: '内容', value: Number(report.content_analysis?.score || 0), color: '#A8C5A0' },
            { label: 'Meta', value: Number(report.meta_analysis?.score || 0), color: '#C4B0E0' },
            { label: '背书信号', value: Number(report.citation_analysis?.score || 0), color: '#E8A07A' },
        ];
    }

    function buildRoadmap(report) {
        const plans = Array.isArray(report?.recommendations?.phase_plan)
            ? report.recommendations.phase_plan.filter(Boolean)
            : [];
        if (plans.length) {
            return plans.slice(0, 3);
        }

        const urgent = Array.isArray(report?.recommendations?.urgent) ? report.recommendations.urgent : [];
        const recommended = Array.isArray(report?.recommendations?.recommended) ? report.recommendations.recommended : [];
        return [
            {
                phase: 'P0',
                title: urgent[0]?.item || '先补结构化信号',
                goal: urgent[0]?.action || '优先修复 Organization、FAQPage 和 canonical 等基础信号。',
                success_metric: '核心机器可读信号完整。',
            },
            {
                phase: 'P1',
                title: recommended[0]?.item || '优化答案表达',
                goal: recommended[0]?.action || '将首屏摘要和问答段落改写成更适合 AI 摘录的内容。',
                success_metric: '答案表达得分提升。',
            },
            {
                phase: 'P2',
                title: '补充证据与案例',
                goal: '扩充外部权威来源、客户案例和站内内容支撑链路。',
                success_metric: '外链与背书就绪维度进入良好以上。',
            },
        ];
    }

    function buildEvidenceCards(report) {
        const schema = report.schema_analysis || {};
        const meta = report.meta_analysis || {};
        const content = report.content_analysis || {};
        const citation = report.citation_analysis || {};

        return [
            {
                title: '已识别 Schema',
                value: `${(schema.found_types || []).length} 项`,
                note: (schema.found_types || []).join('、') || '暂无',
            },
            {
                title: '待补结构化',
                value: `${(schema.missing_recommended || []).length} 项`,
                note: (schema.missing_recommended || []).join('、') || '已覆盖核心推荐类型',
            },
            {
                title: 'Meta 缺口',
                value: `${(meta.missing || []).length} 项`,
                note: (meta.missing || []).join('、') || 'Meta / OG 基本完整',
            },
            {
                title: '内容快照',
                value: `${content.character_count || 0} 字`,
                note: `${content.paragraph_count || 0} 段 · ${content.list_count || 0} 列表 · ${content.image_count || 0} 图片`,
            },
            {
                title: '背书就绪信号',
                value: `${citation.authority_link_count || 0} 权威源`,
                note: `${citation.external_link_count || 0} 外链 · ${citation.internal_link_count || 0} 内链 · ${citation.social_link_count || 0} 社交链接`,
            },
        ];
    }

    function renderScore(score) {
        const scoreValue = document.getElementById('geo-score-value');
        const scoreLabel = document.getElementById('geo-score-label');
        const scoreSummary = document.getElementById('geo-score-summary');
        const scoreRing = document.getElementById('geo-score-ring');
        const safeScore = Math.max(0, Math.min(100, Number(score || 0)));
        const tone = scoreTone(safeScore);
        const circumference = 2 * Math.PI * 80;
        const offset = circumference * (1 - safeScore / 100);

        if (scoreValue) scoreValue.textContent = String(Math.round(safeScore));
        if (scoreLabel) scoreLabel.textContent = `GEO 评分：${tone.label}`;
        if (scoreSummary) {
            scoreSummary.textContent = safeScore >= 80
                ? '页面 GEO 就绪度较好，可继续强化 Schema、问句 H2 / FAQ 与背书就绪信号。'
                : safeScore >= 60
                    ? '页面已有一定 GEO 就绪度，结构化与背书信号仍有提升空间。'
                    : '技术可访问、Schema 或权威外链偏弱，建议按报告清单优先补齐（就绪 ≠ 引用率）。';
        }
        if (scoreRing) {
            scoreRing.style.strokeDasharray = `${circumference}`;
            scoreRing.style.strokeDashoffset = `${offset}`;
        }
    }

    function renderMetric(name, score, note) {
        const root = document.querySelector(`[data-diagnostic-metric="${name}"]`);
        if (!root) return;
        const scoreEl = root.querySelector('[data-role="score"]');
        const barEl = root.querySelector('[data-role="bar"]');
        const noteEl = root.querySelector('[data-role="note"]');
        const safeScore = Math.max(0, Math.min(100, Number(score || 0)));
        const tone = scoreTone(safeScore);

        if (scoreEl) scoreEl.textContent = `${Math.round(safeScore)}%`;
        if (barEl) {
            barEl.style.width = `${safeScore}%`;
            barEl.className = `${tone.bar} h-full`;
        }
        if (noteEl) {
            noteEl.textContent = note;
        }
    }

    function renderSchemaCard(title, body, tone) {
        const toneClass = tone === 'missing' ? 'diag-schema-item--miss' : 'diag-schema-item--ok';
        return `
            <div class="diag-schema-item ${toneClass}">
                <p class="text-xs font-bold font-mono">${escapeHtml(title)}</p>
                <p class="text-[10px] text-on-surface-variant mt-1">${escapeHtml(body)}</p>
            </div>
        `;
    }

    function renderSchema(schema = {}) {
        const detectedCount = document.getElementById('schema-detected-count');
        const missingCount = document.getElementById('schema-missing-count');
        const detectedList = document.getElementById('schema-detected-list');
        const missingList = document.getElementById('schema-missing-list');
        const foundTypes = Array.isArray(schema.found_types) ? schema.found_types : [];
        const missingTypes = Array.isArray(schema.missing_recommended) ? schema.missing_recommended : [];

        if (detectedCount) detectedCount.innerHTML = '<span class="material-symbols-outlined text-sm filled">check_circle</span>已检测到 (' + foundTypes.length + '项)';
        if (missingCount) missingCount.innerHTML = '<span class="material-symbols-outlined text-sm filled">error</span>建议补充 (' + missingTypes.length + '项)';

        if (detectedList) {
            detectedList.innerHTML = foundTypes.length
                ? foundTypes.map((type) => renderSchemaCard(`@type: "${type}"`, '页面中已存在此结构化类型，可继续补充完整字段。', 'found')).join('')
                : renderSchemaCard('暂无已识别 Schema', '当前页面没有发现可用的 JSON-LD Schema 结构。', 'found');
        }
        if (missingList) {
            missingList.innerHTML = missingTypes.length
                ? missingTypes.map((type) => renderSchemaCard(`@type: "${type}"`, '建议尽快补齐该类型，提升 AI 对页面实体与结构的理解。', 'missing')).join('')
                : renderSchemaCard('结构化类型完整', '当前推荐的核心 Schema 类型已经覆盖。', 'found');
        }
    }

    function recommendationTone(kind) {
        if (kind === 'urgent') {
            return {
                iconWrap: 'diag-rec-urgent',
                iconName: 'error',
                label: '紧急',
            };
        }
        if (kind === 'recommended') {
            return {
                iconWrap: 'diag-rec-suggest',
                iconName: 'bolt',
                label: '建议',
            };
        }
        return {
            iconWrap: 'diag-rec-opt',
            iconName: 'info',
            label: '优化',
        };
    }

    function renderRecommendations(recommendations = {}) {
        const list = document.getElementById('recommendations-list');
        if (!list) return;

        const entries = ['urgent', 'recommended', 'optional']
            .flatMap((kind) => (Array.isArray(recommendations[kind]) ? recommendations[kind].map((item) => ({ kind, item })) : []));

        if (!entries.length) {
            list.innerHTML = `
                <div class="col-span-1 md:col-span-3 diag-card p-6 text-sm text-on-surface-variant">
                    暂无额外建议。可继续补 FAQPage、问句化 H2 与权威外链，稳步提升 GEO 就绪表现（≠ AI 引用率）。
                </div>
            `;
            return;
        }

        list.innerHTML = entries.slice(0, 6).map(({ kind, item }) => {
            const tone = recommendationTone(kind);
            return `
                <div class="diag-card diag-card--interactive p-6">
                    <div class="flex items-center gap-2 mb-4">
                        <span class="w-6 h-6 rounded flex items-center justify-center ${tone.iconWrap}" style="border:1.5px solid var(--border)"><span class="material-symbols-outlined text-xs filled">${tone.iconName}</span></span>
                        <span class="text-xs font-bold">${tone.label}</span>
                    </div>
                    <h4 class="text-sm font-bold mb-2">${escapeHtml(item.item || '优化项')}</h4>
                    <p class="text-xs text-on-surface-variant leading-relaxed">${escapeHtml(item.action || '建议按诊断结果补齐 Schema、问句结构与背书就绪信号。')}</p>
                </div>
            `;
        }).join('');
    }

    function renderCategoryBars(sections) {
        const root = document.getElementById('diagnostic-category-bars');
        if (!root) return;
        root.innerHTML = sections.map((section) => `
            <div>
                <div class="flex items-center justify-between text-sm mb-2">
                    <span class="font-medium flex items-center gap-2">
                        <span class="material-symbols-outlined text-base">${escapeHtml(section.icon)}</span>
                        ${escapeHtml(section.title)}
                    </span>
                    <span class="font-bold">${Math.round(section.score)}%</span>
                </div>
                <div class="h-2 diag-bar-track overflow-hidden">
                    <div class="${scoreTone(section.score).bar} h-full" style="width:${Math.round(section.score)}%"></div>
                </div>
                <p class="mt-2 text-xs leading-6 text-on-surface-variant">${escapeHtml(section.summary)}</p>
            </div>
        `).join('');
    }

    function renderReadinessFunnel(stages) {
        const root = document.getElementById('diagnostic-readiness-funnel');
        if (!root) return;
        root.innerHTML = stages.map((stage, index) => {
            const width = Math.max(24, Math.round(stage.score));
            return `
                <div class="diagnostic-funnel-stage">
                    <div class="flex items-center justify-between text-xs font-bold uppercase tracking-[0.14em] text-on-surface-variant">
                        <span>${escapeHtml(stage.label)}</span>
                        <span>${Math.round(stage.score)}%</span>
                    </div>
                    <div class="mt-2 h-11 diag-funnel-track overflow-hidden relative">
                        <div class="absolute inset-y-0 left-0 diag-funnel-fill" style="width:${width}%"></div>
                        <div class="relative h-full flex items-center px-4 text-sm font-semibold">
                            <span class="w-6 h-6 mr-3 rounded flex items-center justify-center text-xs font-black" style="border:1.5px solid var(--border);background:var(--bg-elevated)">${index + 1}</span>
                            ${escapeHtml(stage.label)}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function renderSignalMix(mix, overallScore) {
        const donut = document.getElementById('diagnostic-signal-donut');
        const donutScore = document.getElementById('diagnostic-signal-donut-score');
        const legend = document.getElementById('diagnostic-signal-legend');
        if (!donut || !legend) return;
        const total = mix.reduce((sum, item) => sum + Math.max(0, item.value), 0) || 1;
        let start = 0;
        const segments = mix.map((item) => {
            const share = (Math.max(0, item.value) / total) * 100;
            const segment = `${item.color} ${start}% ${start + share}%`;
            start += share;
            return segment;
        });
        donut.style.background = `conic-gradient(${segments.join(', ')})`;
        if (donutScore) donutScore.textContent = String(Math.round(overallScore || 0));
        legend.innerHTML = mix.map((item) => `
            <div class="diag-card flex items-center justify-between px-4 py-3">
                <div class="flex items-center gap-3">
                    <span class="w-3 h-3 rounded" style="background:${item.color};border:1.5px solid var(--border)"></span>
                    <span class="text-sm font-medium">${escapeHtml(item.label)}</span>
                </div>
                <span class="text-sm font-bold">${Math.round(item.value)}%</span>
            </div>
        `).join('');
    }

    function renderRiskGrid(sections) {
        const root = document.getElementById('diagnostic-risk-grid');
        if (!root) return;
        const risks = sections
            .flatMap((section) => section.items.map((item) => ({ ...item, sectionTitle: section.title })))
            .sort((a, b) => a.score - b.score)
            .slice(0, 6);
        root.innerHTML = risks.map((item) => `
            <div class="diag-card diag-zone-soft px-4 py-4">
                <div class="flex items-start justify-between gap-3">
                    <div>
                        <p class="diag-eyebrow text-[11px] font-extrabold uppercase tracking-[0.14em]">${escapeHtml(item.sectionTitle)}</p>
                        <h4 class="mt-2 text-sm font-bold">${escapeHtml(item.title)}</h4>
                    </div>
                    <span class="diag-rec-urgent px-2.5 py-1 text-xs font-bold" style="border:1.5px solid var(--border);border-radius:8px">${Math.round(item.score)}%</span>
                </div>
                <p class="mt-3 text-xs leading-6 text-on-surface-variant">${escapeHtml(item.note)}</p>
            </div>
        `).join('');
    }

    function renderModuleSections(sections) {
        const root = document.getElementById('diagnostic-module-sections');
        const summary = document.getElementById('diagnostic-module-summary');
        if (!root) return;
        const moduleCount = sections.reduce((count, section) => count + section.items.length, 0);
        if (summary) {
            summary.textContent = `覆盖 ${sections.length} 个章节 · ${moduleCount} 个模块`;
        }
        root.innerHTML = sections.map((section) => `
            <section class="diag-card p-5 md:p-6">
                <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div class="max-w-2xl">
                        <div class="flex items-center gap-3">
                            <span class="w-11 h-11 shrink-0 flex items-center justify-center overflow-hidden" style="border:2px solid var(--border);border-radius:8px;background:color-mix(in srgb, var(--accent-blue) 28%, white)" aria-hidden="true">
                                <span class="material-symbols-outlined text-[22px] leading-none">${escapeHtml(section.icon)}</span>
                            </span>
                            <div class="min-w-0">
                                <p class="diag-eyebrow text-[11px] font-extrabold uppercase tracking-[0.14em]">诊断章节</p>
                                <h4 class="mt-1 text-lg font-bold">${escapeHtml(section.title)}</h4>
                            </div>
                        </div>
                        <p class="mt-4 text-sm leading-7 text-on-surface-variant">${escapeHtml(section.summary)}</p>
                    </div>
                    <div class="self-start px-4 py-2 text-sm font-bold" style="border:1.5px solid var(--border);border-radius:8px;background:color-mix(in srgb, var(--accent-orange) 22%, white)">${Math.round(section.score)}%</div>
                </div>
                <div class="mt-5 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                    ${section.items.map((item) => `
                        <article class="diag-card diag-zone-soft px-4 py-4">
                            <div class="flex items-center justify-between gap-3">
                                <h5 class="text-sm font-bold">${escapeHtml(item.title)}</h5>
                                <span class="px-2.5 py-1 text-xs font-bold" style="border:1.5px solid var(--border);border-radius:8px;background:var(--bg-elevated)">${Math.round(item.score)}%</span>
                            </div>
                            <p class="mt-2 text-xs font-semibold uppercase tracking-[0.12em] text-on-surface-variant">${escapeHtml(item.metric || '')}</p>
                            <div class="mt-3 h-1.5 diag-bar-track overflow-hidden">
                                <div class="${scoreTone(item.score).bar} h-full" style="width:${Math.round(item.score)}%"></div>
                            </div>
                            <p class="mt-3 text-xs leading-6 text-on-surface-variant">${escapeHtml(item.note)}</p>
                        </article>
                    `).join('')}
                </div>
            </section>
        `).join('');
    }

    function renderRoadmap(report) {
        const root = document.getElementById('diagnostic-roadmap');
        if (!root) return;
        const plans = buildRoadmap(report);
        root.innerHTML = plans.map((plan, index) => `
            <div class="relative diag-card diag-zone-soft px-5 py-5">
                <div class="absolute left-5 top-5 bottom-5 ${index === plans.length - 1 ? 'hidden' : 'block'} w-px" style="background:var(--border)"></div>
                <div class="relative pl-12">
                    <span class="absolute left-0 top-0 flex h-8 w-8 items-center justify-center text-xs font-black" style="border:2px solid var(--border);border-radius:8px;background:var(--accent-orange)">${escapeHtml(plan.phase)}</span>
                    <h4 class="text-sm font-bold">${escapeHtml(plan.title)}</h4>
                    <p class="mt-2 text-sm leading-7 text-on-surface-variant">${escapeHtml(plan.goal)}</p>
                    <div class="mt-3 inline-flex px-3 py-1 text-xs font-medium text-on-surface-variant" style="border:1.5px solid var(--border);border-radius:8px;background:var(--bg-elevated)">
                        成功标记：${escapeHtml(plan.success_metric || '形成可执行的修复闭环')}
                    </div>
                </div>
            </div>
        `).join('');
    }

    function renderEvidence(report) {
        const root = document.getElementById('diagnostic-evidence-grid');
        if (!root) return;
        root.innerHTML = buildEvidenceCards(report).map((card) => `
            <div class="diag-card diag-zone-soft px-4 py-4">
                <div class="flex items-center justify-between gap-3">
                    <h4 class="text-sm font-bold">${escapeHtml(card.title)}</h4>
                    <span class="text-xs font-bold">${escapeHtml(card.value)}</span>
                </div>
                <p class="mt-3 text-xs leading-6 text-on-surface-variant">${escapeHtml(card.note)}</p>
            </div>
        `).join('');
    }

    function renderBulletList(root, items, emptyText, iconName, iconClass) {
        if (!root) return;
        const values = Array.isArray(items) ? items.filter(Boolean).slice(0, 3) : [];
        root.innerHTML = values.length
            ? values.map((item) => `
                <li class="flex items-start gap-3 text-sm text-on-surface-variant">
                    <span class="material-symbols-outlined text-base ${iconClass} mt-0.5">${iconName}</span>
                    <span>${escapeHtml(item)}</span>
                </li>
            `).join('')
            : `
                <li class="flex items-start gap-3 text-sm text-on-surface-variant">
                    <span class="material-symbols-outlined text-base ${iconClass} mt-0.5">${iconName}</span>
                    <span>${escapeHtml(emptyText)}</span>
                </li>
            `;
    }

    function fallbackSeoModules(report) {
        const schema = report.schema_analysis || {};
        const meta = report.meta_analysis || {};
        const content = report.content_analysis || {};
        const citation = report.citation_analysis || {};
        const structure = Math.round((Number(schema.score || 0) * 0.55) + (Number(content.score || 0) * 0.45));
        const missingMeta = (meta.missing || []).slice(0, 4);
        const missingSchema = (schema.missing_recommended || []).slice(0, 4);
        const metaLabel = {
            html_lang: '页面语言',
            canonical: '规范网址',
            viewport: '移动端适配',
            robots: '抓取许可',
            meta_description: '页面摘要',
            title: '页面标题',
            og_image: '分享配图',
            og_locale: '分享语言区',
        };
        const schemaLabel = {
            Organization: '机构/主体身份',
            WebSite: '站点实体',
            FAQPage: '问答页标记',
            Article: '文章实体',
            Product: '商品/服务实体',
        };
        const namedMeta = missingMeta.map((k) => metaLabel[k] || k);
        const namedSchema = missingSchema.map((k) => schemaLabel[k] || k);
        const crawlImpact = missingMeta.length
            ? `缺 ${namedMeta.join('、')} 不等于打不开站，但引擎打开后更难正确介绍你们：语言/收录/摘要信号不完整，结果列表和推荐易说不清主题或推错受众。`
            : '基础抓取信号较完整；仍需防止 robots 被误改导致整页不可见。';
        const structureImpactParts = [];
        if (Number(content.h1_count || 0) !== 1) {
            structureImpactParts.push(`主标题有 ${content.h1_count || 0} 个，本页重点不清晰。`);
        }
        if (Number(content.h2_count || 0) < 2) {
            structureImpactParts.push('小节标题过少，用户问题对不上段落，难被摘成「一问一答」。');
        }
        if (Number(content.faq_like_sections || 0) < 1) {
            structureImpactParts.push('缺少 FAQ 块，高频咨询问题在站内没有标准短答。');
        }
        if (namedSchema.length) {
            structureImpactParts.push(`缺 ${namedSchema.join('、')} 时，主体身份或问答更难被稳定识别（就绪 ≠ 引用率）。`);
        }
        return [
            {
                id: 'crawlability',
                title: '可抓取与可达',
                purpose: '先确认引擎能打开页面，并读到标题、摘要、语言、是否允许收录等第一层介绍信息。',
                score: Math.round(Number(meta.score || 0)),
                result: namedMeta.length
                    ? `基础摘要就绪分 ${Math.round(Number(meta.score || 0))}/100。仍缺：${namedMeta.join('、')}。`
                    : `基础摘要就绪分 ${Math.round(Number(meta.score || 0))}/100。基础信号较完整。`,
                impact: crawlImpact,
                advice: namedMeta.length
                    ? `请技术补齐 ${namedMeta.join('、')}；运营核对标题/摘要是否写清主题、受众与一句话价值。`
                    : '保持标题与摘要完整；发版前后抽查抓取许可，避免误拦。',
            },
            {
                id: 'parseable_structure',
                title: '可解析结构',
                purpose: '确认机构/站点身份、标题层级和 FAQ 能否被读成实体与问答块，对上用户真实问题。',
                score: structure,
                result: `结构合成分 ${structure}/100；H1=${content.h1_count || 0} · H2=${content.h2_count || 0} · FAQ=${content.faq_like_sections || 0}。`,
                impact: structureImpactParts.join(' ') || '结构基本可用；继续把小节写成用户问句并维护 FAQ。',
                advice: namedSchema.length
                    ? `补 ${namedSchema.join('、')}；每页 1 个 H1，关键 H2 改成用户问句（怎么联系？开放/播出时间？），并加 FAQ 短答。`
                    : '继续强化问句化 H2 / FAQ，把关键事实与规则写成可独立摘录的短段。',
            },
            {
                id: 'internal_discovery',
                title: '内链与发现',
                purpose: '确认栏目/专题/说明等关键页能被内链找到，并有权威外链作信任线索（≠ AI 引用率）。',
                score: Math.round(Number(citation.score || 0)),
                result: `外链 ${citation.external_link_count || 0} · 权威线索 ${citation.authority_link_count || 0}；就绪分 ${Math.round(Number(citation.score || 0))}/100。`,
                impact: Number(citation.authority_link_count || 0) < 1
                    ? '权威外链偏少时，外部信任线索不足；内链弱则关键内容页不易被连带发现。'
                    : '已有权威线索；注意这是页面背书就绪，不是答案面板提及率。',
                advice: '用清晰锚文字串起栏目/专题/说明页，并保留权威外链；从本页 2～3 次点击应能到达。',
            },
            {
                id: 'performance_cost',
                title: '性能与成本',
                purpose: '评估正文长短是否让引擎读得贵、摘得慢；帮助把关键话放在更好被看见的位置。',
                score: 72,
                result: '正文体量代理适中；优先短直答段落降低上下文成本（非 Lighthouse 实测）。',
                impact: '体量压力通常不大；核心结论若靠后，仍可能读到了但摘不稳。',
                advice: '把核心结论、规则、联系/入口放在靠前可摘录段落，方便编辑与对外口径复用。',
            },
        ];
    }

    function renderSeoModules(report) {
        const host = document.getElementById('seo-modules-grid');
        if (!host) return;
        const modules = (Array.isArray(report.seo_modules) && report.seo_modules.length)
            ? report.seo_modules
            : (report.recommendations && report.recommendations.seo_modules) || fallbackSeoModules(report);
        host.innerHTML = [
            '<div class="seo-modules-grid grid grid-cols-1 md:grid-cols-2 gap-4">',
            modules.map((m) => `
                <article class="seo-module-card diag-card p-4 md:p-5">
                    <div class="flex items-center justify-between gap-2">
                        <h4 class="text-sm font-bold">${escapeHtml(m.title || '')}</h4>
                        <strong class="text-xl font-black">${Math.round(Number(m.score || 0))}</strong>
                    </div>
                    <p class="mt-3 text-xs text-on-surface-variant leading-6"><span class="font-bold text-on-surface">目的</span> ${escapeHtml(m.purpose || '')}</p>
                    <p class="mt-2 text-xs leading-6"><span class="font-bold">结果</span> ${escapeHtml(m.result || '')}</p>
                    <p class="mt-2 text-xs leading-6 text-on-surface"><span class="font-bold text-primary">影响</span> ${escapeHtml(m.impact || '补齐缺口后，摘要更清晰、身份更易认、高频问题更有标准答法（就绪 ≠ 保证被引用）。')}</p>
                    <p class="mt-2 text-xs leading-6"><span class="font-bold">建议</span> ${escapeHtml(m.advice || '')}</p>
                </article>
            `).join(''),
            '</div>',
        ].join('');
        return modules;
    }

    function renderPriority(report, modules) {
        if (!summaryPriority) return;
        const fromRec = (report?.recommendations?.summary?.priority_action || '').trim();
        const list = modules || [];
        const worst = list.slice().sort((a, b) => Number(a.score || 0) - Number(b.score || 0))[0];
        const impact = (worst?.impact || '').trim();
        const advice = (worst?.advice || '').trim();
        const fromModules = impact && advice ? `${impact} → ${advice}` : (advice || impact);

        // 旧报告常只有「补字段」短句；有运营向「影响」时优先用模块文案
        const recLooksThin = fromRec && !/影响|验收|运营|引擎难以|不等于/.test(fromRec)
            && (fromRec.length < 80 || /JSON-LD|Schema|meta |og:|html_lang|canonical/.test(fromRec));
        if (fromRec && !recLooksThin) {
            summaryPriority.textContent = fromRec;
            return;
        }
        if (fromModules) {
            summaryPriority.textContent = fromModules;
            return;
        }
        if (fromRec) {
            summaryPriority.textContent = fromRec;
            return;
        }
        summaryPriority.textContent = '完成检查后将给出优先修复建议（含业务影响与验收方式）。';
    }

    function loadGeoObserve() {
        const root = document.getElementById('geo-observe-root');
        if (!root) return;
        const Extra = window.GEOrank?.SuiteExtra;
        if (!Extra?.mountGeoObserve) {
            root.innerHTML = '<p class="text-sm text-rose-600">观测组件未加载。</p>';
            return;
        }
        Extra.mountGeoObserve(root, {
            doneStep: 'diagnostic',
            doneLabel: '确认初诊观测',
        }).catch((error) => {
            root.innerHTML = `<p class="text-sm text-rose-600">观测加载失败：${escapeHtml(String(error.message || error))}</p>`;
        });
    }

    function bindDiagTabs() {
        const tabs = document.querySelectorAll('[data-diag-tab]');
        tabs.forEach((tab) => {
            tab.addEventListener('click', () => {
                const id = tab.getAttribute('data-diag-tab');
                tabs.forEach((t) => {
                    const on = t === tab;
                    t.classList.toggle('is-active', on);
                    t.setAttribute('aria-selected', on ? 'true' : 'false');
                });
                document.querySelectorAll('[data-diag-panel]').forEach((panel) => {
                    const on = panel.getAttribute('data-diag-panel') === id;
                    panel.classList.toggle('hidden', !on);
                    if (on) panel.removeAttribute('hidden');
                    else panel.setAttribute('hidden', 'hidden');
                });
                if (id === 'geo') loadGeoObserve();
            });
        });
    }

    function fallbackNarrative(report) {
        const schema = report.schema_analysis || {};
        const meta = report.meta_analysis || {};
        const content = report.content_analysis || {};
        const citation = report.citation_analysis || {};
        const overall = Math.round(Number(report.overall_score || 0));

        const strengths = [];
        if ((schema.score || 0) >= 80) strengths.push('结构化标签基础较完整，页面实体和内容关系已经具备较好的 AI 可识别性。');
        if ((meta.score || 0) >= 80) strengths.push('Meta 与 Open Graph 信号较完整，有助于抓取摘要和页面定位。');
        if ((content.score || 0) >= 70) strengths.push('正文结构和标题层级基本成型，适合继续向答案优先写法优化。');

        const gaps = [];
        if (Array.isArray(schema.missing_recommended) && schema.missing_recommended.length) {
            gaps.push(`缺少 ${schema.missing_recommended.slice(0, 3).join('、')} 等关键 Schema 类型。`);
        }
        if ((citation.authority_link_count || 0) < 1) {
            gaps.push('权威外链不足，背书就绪信号偏弱（≠ AI 答案引用率）。');
        }
        if (!content.first_para_quality) {
            gaps.push('首段缺少直答式摘要，不利于被抽取为答案候选片段。');
        }

        const headline = overall >= 80
            ? '当前页面 GEO 就绪度较强，适合继续强化 Schema 细节与背书信号。'
            : overall >= 60
                ? '当前页面已有一定 GEO 基础，但结构化与背书就绪信号仍有优化空间。'
                : '当前页面 GEO 就绪度偏弱，建议优先补齐 Schema、问句 H2 / FAQ 与技术可访问项。';
        const overview = `综合 GEO 评分为 ${overall} 分。建议优先补齐 Schema、问句化 H2 / FAQ、首段直答与权威外链（背书维 ≠ AI 答案引用率）。`;
        const priority = gaps[0] || '继续补充 FAQPage、问句化 H2 与权威外链，提升可发现/可理解的就绪信号。';

        return { headline, overview, priority, strengths, gaps };
    }

    function renderNarrative(report) {
        const summary = report?.recommendations?.summary || {};
        const fallback = fallbackNarrative(report || {});
        if (summaryHeadline) summaryHeadline.textContent = summary.headline || fallback.headline;
        if (summaryOverview) summaryOverview.textContent = summary.overview || fallback.overview;
        if (summaryPriority) summaryPriority.textContent = summary.priority_action || fallback.priority;
        renderBulletList(
            strengthList,
            report?.recommendations?.strengths || fallback.strengths,
            '当前页面还缺少明显优势信号，建议优先补齐标题、描述与基础结构化标签。',
            'check_circle',
            'text-green-500'
        );
        renderBulletList(
            gapList,
            report?.recommendations?.gaps || fallback.gaps,
            '当前未检测到额外明显缺口，可继续通过案例、FAQ 与权威外链做增强。',
            'warning',
            'text-orange-400'
        );
    }

    function authHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        try {
            const token = localStorage.getItem('georank_token') || '';
            if (token) headers.Authorization = 'Bearer ' + token;
        } catch (_) {}
        return headers;
    }

    async function createStrategyFromReport(report) {
        if (!report || report.report_id === 'demo-report') {
            alert('示例报告不能新建选题，请先检查真实网址。');
            return;
        }
        if (report.status && report.status !== 'completed') {
            alert('请等检查完成后再新建选题。');
            return;
        }
        if (Auth && !Auth.requireAuth({ reasonKey: 'auth.reasonDiagnostic' })) return;
        const platform = 'doubao';
        if (createStrategyBtn) {
            createStrategyBtn.disabled = true;
            createStrategyBtn.textContent = '正在创建…';
        }
        try {
            const res = await fetch('/api/geo-strategies/from-diagnostic', {
                method: 'POST',
                headers: authHeaders(),
                credentials: 'same-origin',
                body: JSON.stringify({
                    diagnostic_report_id: report.report_id,
                    platform: platform,
                }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data.detail || data.message || ('创建失败 ' + res.status));
            }
            const sid = data.id;
            window.location.href = '/strategies?strategy=' + encodeURIComponent(sid) + '&tab=craft';
        } catch (err) {
            alert(String(err.message || err));
            if (createStrategyBtn) {
                createStrategyBtn.disabled = false;
                createStrategyBtn.textContent = '用于新建选题';
            }
        }
    }

    function renderReport(report) {
        const modules = renderSeoModules(report);
        renderPriority(report, modules);
        lastLiveReport = report;

        const isLive = report && report.report_id !== 'demo-report' && report.status === 'completed';
        if (createStrategyBtn) {
            createStrategyBtn.hidden = !isLive;
            createStrategyBtn.disabled = false;
            createStrategyBtn.textContent = '用于新建选题';
            createStrategyBtn.onclick = function () { void createStrategyFromReport(report); };
        }
        if (toSolutionsBtn) {
            if (isLive) {
                toSolutionsBtn.href = '/strategies';
                toSolutionsBtn.textContent = '去选题策略';
            } else if (Workflow?.buildHref) {
                toSolutionsBtn.href = Workflow.buildHref('keywords', {
                    diagnostic_report_id: report.report_id || '',
                    url: report.url || '',
                });
            } else {
                toSolutionsBtn.href = '/strategies';
            }
        }
        showResults();
        setReportMode(report.report_id === 'demo-report' ? 'demo' : 'live', { url: report.url || '' });
        if (report.report_id !== 'demo-report') animateLiveSwap();
        maybeGuideSuiteNext(report);
    }

    function maybeGuideSuiteNext(report) {
        if (!Workflow || !report || report.report_id === 'demo-report') return;
        if (report.status && report.status !== 'completed') return;
        const finish = (run) => {
            Workflow.markComplete('diagnostic', {
                report_id: report.report_id,
                url: report.url || '',
                run_id: run && run.id,
            });
            const extras = {
                diagnostic_report_id: report.report_id || '',
                url: report.url || '',
                run_id: (run && run.id) || Workflow.getRunId() || '',
            };
            Workflow.mountBar({
                stepId: 'diagnostic',
                force: true,
                hint: '检查完成，可用本报告新建选题。',
                nextHref: '/strategies',
                nextLabel: '下一步：新建选题',
            });
            const host = reportShell || resultsGrid || document.querySelector('main');
            Workflow.mountNextCard?.(host, {
                stepId: 'diagnostic',
                title: '检查完成',
                copy: '可一键新建选题，报告会自动挂上。',
                primaryHref: '#diagnostic-create-strategy-btn',
                primaryLabel: '用于新建选题',
            });
            const primary = document.querySelector('#suite-wf-next-diagnostic a.suite-wf-next__btn--primary, .suite-wf-next__btn--primary');
            if (primary && createStrategyBtn) {
                primary.addEventListener('click', (event) => {
                    event.preventDefault();
                    void createStrategyFromReport(report);
                });
            }
        };
        const handoffPayload = {
            diagnostic_report_id: report.report_id,
            url: report.url || '',
            meta: { overall_score: report.overall_score },
        };
        Promise.resolve(Workflow.ensureRun({ url: report.url || '' }))
            .then((run) => Workflow.handoff('diagnostic', handoffPayload).then(() => run).catch(() => run))
            .then(finish)
            .catch(() => finish(null));
    }

    async function pollReport(reportId, attempt = 0) {
        try {
            const report = await request(`/api/diagnostics/${reportId}`);
            activeReportId = report.report_id;
            updateLocation(report.report_id, report.url);

            if (report.status === 'completed') {
                clearPolling();
                setLoading(false);
                setStatus('检查完成。', 'success');
                try {
                    renderReport(report);
                    resultsGrid?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                } catch (renderError) {
                    console.error('[diagnostic] renderReport failed', renderError);
                    setStatus(renderError?.message || '结果渲染失败，请刷新页面重试。', 'error');
                    setReportMode('live', { url: report.url || '' });
                }
                return;
            }

            if (report.status === 'failed') {
                clearPolling();
                setLoading(false);
                showResults();
                setReportMode('demo');
                renderReport(DEMO_REPORT);
                setStatus(report.error_message || '诊断失败，请稍后重试。', 'error');
                return;
            }

            const statusMessages = {
                pending: '任务已创建，正在排队…',
                crawling: '正在抓取页面…',
                analyzing: '正在汇总 SEO 四类结果…',
            };
            setStatus(statusMessages[report.status] || '正在同步检查状态…');
            setReportMode('loading', { url: report.url || '', step: report.status });
        } catch (error) {
            if (attempt >= 10) {
                clearPolling();
                setLoading(false);
                setReportMode('demo');
                setStatus(error.message, 'error');
                return;
            }
            setStatus('状态同步稍有延迟，正在重试获取最新诊断结果...');
        }

        pollTimer = window.setTimeout(() => {
            pollReport(reportId, attempt + 1);
        }, 2000);
    }

    async function startDiagnosis() {
        if (Auth && !Auth.requireAuth({ reasonKey: 'auth.reasonDiagnostic' })) {
            return;
        }

        const rawUrl = urlInput?.value?.trim();
        if (!rawUrl) {
            setStatus('请先输入要诊断的网址，例如 example.com', 'error');
            urlInput?.focus();
            urlInput?.classList.add('ring-2', 'ring-red-300');
            window.setTimeout(() => urlInput?.classList.remove('ring-2', 'ring-red-300'), 2000);
            return;
        }

        let url;
        try {
            url = normalizeInputUrl(rawUrl);
            if (urlInput) {
                urlInput.value = url;
            }
        } catch (error) {
            setStatus(error.message, 'error');
            urlInput?.focus();
            return;
        }

        clearPolling();
        showResults();
        setReportMode('loading', { url });
        setLoading(true);
        setStatus('正在创建诊断任务并同步页面分析进度...');

        try {
            const payload = { url };
            if (activeCompanyId) payload.company_id = activeCompanyId;
            const result = await request('/api/diagnostics/', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            activeReportId = result.report_id;
            updateLocation(result.report_id, url);
            await pollReport(result.report_id);
        } catch (error) {
            setLoading(false);
            setReportMode('demo');
            setStatus(error.message, 'error');
        }
    }

    Workflow?.syncFromQuery?.();
    bindDiagTabs();

    Workflow?.mountBar({
        stepId: 'diagnostic',
        nextHref: Workflow.buildHref('keywords'),
        nextLabel: '下一步：拓词',
        hint: '检查页：输入网址查看基础 SEO。',
    });

    if (initialReportId) {
        showResults();
        setReportMode('loading', { url: initialUrl });
        setLoading(true);
        setStatus('正在恢复检查结果…');
        pollReport(initialReportId);
    } else if (initialUrl) {
        showResults();
        setReportMode('loading', { url: initialUrl });
        setStatus('已带入目标 URL，正在检查…');
        startDiagnosis();
    } else {
        showResults();
        setReportMode('demo');
        renderReport(DEMO_REPORT);
    }
});
